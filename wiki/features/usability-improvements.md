# Usability Improvements

Branch: `usability-improvements-1`

Three changes: optional segment caching (off by default), a duplication warning, and a Gradio link fix.

---

## 1. Optional Segment Caching (`--cache-segments`)

### What changes

Segment caching is **off by default**. By default, `synthesize()` holds each paragraph's audio bytes in memory and assembles `{post-name}-body.wav` directly, without writing `segment-*.wav` files or `manifest.json`. Pass `--cache-segments` to opt in to disk caching, which enables resume-on-failure.

The body WAV still lands on disk in both cases so the mixer can read it via its existing `Path` contract.

### Files to edit

**`narrator.py`**

1. Add the Click option to `generate`:
   ```python
   @click.option("--cache-segments", "cache_segments", is_flag=True, default=False,
                 help="Write segment files and manifest to disk; enables resume-on-failure")
   ```

2. Pass `cache_segments` through to `synthesize()`:
   ```python
   body_path = synthesize(
       ...
       cache_segments=cache_segments,
   )
   ```

3. Add `"cache_segments"` to the dry-run JSON output:
   ```python
   "cache_segments": cache_segments,
   ```

**`pipeline/synthesizer.py`**

1. Add `cache_segments: bool = False` to the `synthesize()` signature.

2. Split `_assemble` into two private functions:
   - `_assemble_from_memory(segments, pause_ms, body_path) -> Path` — default path, takes `list[bytes]`, builds `AudioSegment` objects directly without touching disk.
   - `_assemble_from_disk(work_dir, total, pause_ms, body_path) -> Path` — opt-in path, existing logic, reads `segment-*.wav` files.

3. In `synthesize()`, branch on `cache_segments`:

   **When `cache_segments=False` (default — new behaviour):**
   - Still create `work_dir` (needed for `body_path` location).
   - Skip manifest load/create entirely.
   - Accumulate synthesized bytes in a `list[bytes]` in the loop — no disk writes per segment.
   - After the loop, call `_assemble_from_memory(segments, pause_ms, body_path)`.
   - No manifest is written at any point.

   **When `cache_segments=True` (opt-in):**
   - Create `work_dir`, load/create manifest, write each segment to disk, write manifest after each segment, call `_assemble_from_disk`.

   The `force` flag has no effect when `cache_segments=False` (nothing to clear). `_clear_work_dir` is only called in the `cache_segments=True` branch.

**`wiki/agent-guidelines.md` — section 1.3**

Update the `generate` options table and the dry-run JSON schema to document the new flag and the `cache_segments` field.

### What does NOT change

- `mix()`, `encode()` — receive the same `body_path: Path`, untouched.
- `status` command — shows `synthesis: null` when no manifest exists (the common case with default behaviour). Pass `--cache-segments` to get resumable state tracked in `status`.
- The `--progress` flag — `segment_done` events still emit in both paths.

---

## 2. Narration Duplication Warning

### What changes

When a user runs `generate` on a post whose output file already exists, print a visible warning before synthesis begins. This is distinct from the existing `status: skipped` response (which fires when output exists and `--force` is absent) — the warning targets the case where the user runs with `--force` or `--raw-only`, where synthesis proceeds regardless.

The warning surfaces in both the CLI (stderr) and the Gradio UI (progress log).

### Files to edit

**`narrator.py`**

After the existing `status: skipped` early-return block (line 198–205), add a warning that fires when output exists but the run will proceed anyway:

```python
if output_path.exists() and (force or raw_only):
    print(
        f"  [WARN] Output already exists: {output_path}. "
        "Regenerating because --force/--raw-only was passed.",
        file=sys.stderr,
    )
    if progress:
        _event({"event": "warn", "message": f"Output already exists: {output_path}. Regenerating."})
```

This emits to stderr for the CLI. When `--progress` is also active (as the Gradio UI always passes it), it additionally emits a JSON `warn` event to stdout.

**`narrator_ui.py`**

Add a handler for `event == "warn"` in the `_run_generate` loop:

```python
elif etype == "warn":
    lines.append(f"[warn]         {ev['message']}")
    yield _log_html(lines), None, None
```

This renders the warning in the terminal-style progress block in the browser UI.

### What does NOT change

- The `status: skipped` response — fires when output exists and neither `--force` nor `--raw-only` is passed. Unaffected.
- stdout JSON schema for the final result — no changes.
- stderr warning format — consistent with existing `[WARN]` lines already in `generate`.

---

## 3. Intro/Outro Naming Warning

### What changes

When `mix()` finds audio files in the intro or outro directory that don't match the expected naming pattern, it prints a warning to stderr listing the unrecognized files and the patterns they should follow. Previously, misnamed files were silently skipped with no feedback.

Expected patterns are `{post-name}-intro.*` (post-specific) and `default-intro.*` (shared fallback), and equivalently for outro. Any supported audio file in those directories that matches neither pattern triggers the warning.

### Files to edit

**`pipeline/mixer.py`** — after resolving the intro/outro directory, scan for audio files whose stems don't match either expected pattern and print a warning to stderr if any are found.

### What does NOT change

- Mix behaviour — unrecognized files are still ignored; the warning is informational only.
- stdout JSON schema — the warning goes to stderr only.

---

## 4. Remix Command

### What changes

A new `remix` CLI command re-runs mix and encode using the saved body WAV without re-synthesizing. This is useful when a user updates an intro or outro file after generation — remix completes in seconds rather than re-running the full pipeline.

`remix` requires a body WAV to already exist at `audio/raw/{post-name}/{post-name}-body.wav` (written by `generate`). If it is missing, the command errors with a clear message directing the user to run `generate` first.

Flags mirror the audio-related subset of `generate`:

| Flag | Purpose |
|---|---|
| `--format` | Output format (overrides `config.yaml`) |
| `--no-intro` | Skip intro audio |
| `--no-outro` | Skip outro audio |
| `--post-name` | Override slug derived from filename |
| `--output` | Exact output file path |

JSON response on success:

```json
{
  "status": "ok",
  "post": "<post_path>",
  "output_path": "<final_path>",
  "duration_sec": 142,
  "format": "mp3"
}
```

### Files to edit

**`narrator.py`** — add the `remix` command with the flags above. Locate the body WAV, error clearly if missing, then call `mix(force=True)` and `encode()`.

**`wiki/agent-guidelines.md`** — document the `remix` command schema in section 1.3.

**`AGENTS.md`** — add `remix` to the key commands table.

**`.claude/settings.json`** — add `remix` to the pre-approved commands list.

### What does NOT change

- `mix()` and `encode()` — called with the same arguments as `generate`; no changes to those functions.
- `generate` — unaffected.

---

## 6. Agent Configuration Files

### `.claude/commands/generate.md`

Step 3 of the guided workflow presents the resolved plan to the user. Update it to also mention `--no-cache-segments` as an available option the user can add before confirming:

> Present the plan to the user: `post_name`, `voice`, `speed`, `format`, `output_path`, whether it `would_skip`, and note that `--no-cache-segments` can be passed to skip writing segment files (disables resume-on-failure for this run).

**`.claude/settings.json`** — no change needed. The existing `"Bash(python narrator.py generate * --dry-run)"` wildcard already covers dry-runs with the new flag.

### `AGENTS.md`

The "Key `generate` flags for agent use" table needs a new row:

| Flag | Purpose |
|---|---|
| `--cache-segments` | Write segment files and manifest to disk; enables resume-on-failure (off by default) |

### `CLAUDE.md`

No change needed — it points to `wiki/agent-guidelines.md` and doesn't list flags directly.

### `.gemini/settings.json` (new file)

Gemini CLI reads `GEMINI.md` by default but can be configured to read any filename via `.gemini/settings.json`. Rather than creating a duplicate of `AGENTS.md`, add a one-line config that points Gemini at the existing `AGENTS.md`:

```json
{
  "context": {
    "fileName": ["AGENTS.md"]
  }
}
```

This means Gemini CLI autonomous agents get the same instructions as Codex, with no content to duplicate or keep in sync. No `GEMINI.md` file is needed.

**No `.gemini/commands/`, `.codex/`, or `.agents/` folders.** The slash commands in `.claude/commands/` are for human users interacting with Claude Code interactively. Autonomous agents (Gemini, Codex, and others) get their instructions from `AGENTS.md` and `wiki/agent-guidelines.md` — they do not need or invoke slash commands.

---

## 8. Abbreviation Expansion

### What changes

A YAML config file (`abbreviations.yaml`) lets users map written abbreviations to their spoken equivalents. During text preprocessing — after URL and Markdown stripping, before synthesis — any matching abbreviation is replaced with its expansion. Matching is word-boundary-aware so abbreviations embedded inside longer words or dotted sequences are never replaced.

Default entries ship with the config:

```yaml
# Map abbreviations to their spoken expansions.
# Matching is word-boundary-aware — partial matches inside longer words are ignored.

expansions:
  "e.g.": "for example"
  "i.e.": "that is"
  "et al.": "and others"
  "vs.": "versus"
  "approx.": "approximately"
```

Patterns are case-insensitive and applied longest-key-first.

### Files to edit

**`abbreviations.yaml`** (new file) — create with the default entries above.

**`pipeline/preprocessor.py`** — load the config at startup, compile each entry into a regex, and apply substitutions after URL stripping.

**`wiki/agent-guidelines.md`** — note that `abbreviations.yaml` exists and can be extended to fix any abbreviation the TTS model mispronounces.

### What does NOT change

- TTS model calls — the synthesizer receives clean expanded prose.
- All other preprocessing steps — the abbreviation pass runs after them.

---

## 7. Tests

**`tests/test_synthesizer_resume.py`** — add the following cases:

| Test | What it asserts |
|---|---|
| `test_default_run_writes_no_segment_files` | Default run (`cache_segments=False`) writes no `segment-*.wav` files |
| `test_default_run_writes_no_manifest` | Default run writes no `manifest.json` |
| `test_default_run_body_wav_exists` | Default run still returns a `body_path` that exists on disk |
| `test_default_run_body_wav_has_audio` | Returned WAV has nonzero size (in-memory assembly produced real output) |
| `test_cache_segments_writes_segment_files` | `cache_segments=True` writes `segment-*.wav` files and `manifest.json` as before |
| `test_misnamed_intro_triggers_warning` | A misnamed intro file produces a stderr warning listing the file and expected patterns |
| `test_correctly_named_intro_no_warning` | A correctly named intro file produces no warning |
| `test_remix_uses_existing_body_wav` | `remix` succeeds when a body WAV exists and produces an output file |
| `test_remix_errors_when_body_wav_missing` | `remix` errors with a clear message when no body WAV is found |
| `test_abbrev_replaced_in_prose` | `i.e.` and `e.g.` are expanded in normal prose |
| `test_embedded_abbrev_not_replaced` | Abbreviations embedded in longer dotted sequences are left untouched |
| `test_trailing_dot_abbrev_replaced` | `vs.` and `approx.` are expanded correctly |
| `test_abbrev_case_insensitive` | Capitalised forms (e.g. `I.e.`) are also expanded |
| `test_abbrev_longest_key_first` | A longer entry is not shadowed by a shorter overlapping one |

---

## Implementation Order

1. `pipeline/synthesizer.py` — add `cache_segments` parameter, split `_assemble`, add in-memory branch.
2. `narrator.py` — add `--cache-segments` flag, pass through, add duplication warning + `warn` event, add `cache_segments` to dry-run JSON.
3. `narrator_ui.py` — add `warn` event handler.
4. `tests/test_synthesizer_resume.py` — add the five new test cases.
5. `wiki/agent-guidelines.md` — update section 1.3 (generate options table + dry-run schema).
6. `AGENTS.md` — add `--cache-segments` to the generate flags table.
7. `.claude/commands/generate.md` — mention `--cache-segments` in step 3.
8. `.gemini/settings.json` — create new file pointing Gemini CLI at `AGENTS.md`.
9. `pipeline/mixer.py` — add naming pattern check and stderr warning.
10. `narrator.py` — add `remix` command.
11. `wiki/agent-guidelines.md` — document `remix` schema in section 1.3.
12. `AGENTS.md` — add `remix` to the key commands table.
13. `.claude/settings.json` — add `remix` to pre-approved commands.
14. `abbreviations.yaml` — create with default entries.
15. `pipeline/preprocessor.py` — load config, compile patterns, apply substitutions.
16. `wiki/agent-guidelines.md` — document `abbreviations.yaml`.
17. `tests/` — add all new test cases.
