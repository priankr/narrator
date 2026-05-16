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

## 3. Agent Configuration Files

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

## 4. Tests

**`tests/test_synthesizer_resume.py`** — add the following cases:

| Test | What it asserts |
|---|---|
| `test_default_run_writes_no_segment_files` | Default run (`cache_segments=False`) writes no `segment-*.wav` files |
| `test_default_run_writes_no_manifest` | Default run writes no `manifest.json` |
| `test_default_run_body_wav_exists` | Default run still returns a `body_path` that exists on disk |
| `test_default_run_body_wav_has_audio` | Returned WAV has nonzero size (in-memory assembly produced real output) |
| `test_cache_segments_writes_segment_files` | `cache_segments=True` writes `segment-*.wav` files and `manifest.json` as before |

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
