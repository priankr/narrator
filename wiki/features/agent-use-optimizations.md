# Agent-Use Optimizations — Implementation Plan

## Overview

This document tracks all changes made to improve the Narrator App's usability by AI agents, in both consumer (CLI user) and developer (code contributor) roles. It covers completed design decisions, planned new features, a test suite plan, and implementation phases.

For the current agent instruction files produced by this effort, see:
- [`CLAUDE.md`](../../CLAUDE.md) — Claude Code conventions
- [`AGENTS.md`](../../AGENTS.md) — generic agent quick-start
- [`wiki/agent-guidelines.md`](../agent-guidelines.md) — full shared reference
- [`.gemini/settings.json`](../../.gemini/settings.json) — points Gemini CLI at `AGENTS.md` (no separate GEMINI.md needed)

---

## Background: Dual-Purpose Agent Design

The app is designed to serve two distinct agent roles:

**Consumer agents** invoke the CLI to produce audio narrations as part of a larger workflow. They need predictable JSON output, clear error schemas, and safe retry semantics.

**Developer agents** (most commonly Claude Code) extend or maintain the codebase. They need architecture clarity, stable contracts, coding conventions, and a clear map of where to make changes.

These two roles have different needs. Documentation and introspection features serve consumer agents; architecture documentation and coding conventions serve developer agents. Both are addressed here.

---

## Completed: Phase 3 Agent Compatibility (from `app-implementation.md`)

These features were built as part of the original Phase 3 implementation and form the foundation for agent use:

- **`voices` command** — agents can discover available voice IDs before invoking `generate`
- **JSON stdout / stderr separation** — all structured results go to stdout; all progress goes to stderr; agents can parse stdout without noise
- **Consistent response schema** — every command uses `{"status": "ok" | "error" | "skipped", ...}`; exit code `0` for success/skipped, `1` for error
- **`validate.py` pre-flight checks** — config validation, ffmpeg check, post file checks, voice format hint, speed range check all run before synthesis begins, surfacing errors early
- **`check` command** — single command to verify environment readiness before any pipeline work
- **Segment caching + manifest** — synthesis is resumable; agents do not need to restart from scratch on failure; `--force` provides an explicit override

---

## Planned Features

### Feature 1: `status` Command

**Problem:** An agent has no way to discover what posts exist, what has been synthesized, or what output files are ready — without exploring the filesystem manually.

**Solution:** Add a `status` subcommand to `narrator.py`.

**Implementation:**
- File: `narrator.py`
- Add `@cli.command()` decorated function `status()`
- Scan `config["paths"]["posts"]` for `.md` files
- For each post, check `audio/raw/{stem}/manifest.json` for synthesis state
- Check `audio/output/` for any matching output files

**Output schema:**
```json
{
  "status": "ok",
  "posts": [
    {
      "name": "my-essay",
      "path": "posts/my-essay.md",
      "synthesis": {
        "cached": true,
        "segments_done": 24,
        "total_paragraphs": 24,
        "voice": "af_sarah",
        "speed": 1.0
      },
      "output": [
        {"path": "audio/output/my-essay.mp3", "format": "mp3"}
      ]
    }
  ]
}
```

If no manifest exists for a post, `synthesis` is `null`. If no output exists, `output` is `[]`.

---

### Feature 2: `config` Command

**Problem:** An agent cannot query the resolved configuration as structured data without parsing `config.yaml` manually. This is fragile — the agent must know the YAML schema and handle missing optional keys.

**Solution:** Add a `config` subcommand to `narrator.py`.

**Implementation:**
- File: `narrator.py`
- Add `@cli.command()` decorated function `show_config()` (command name: `config`)
- Load config via `_load_config()`, run `validate_config()`, then print the full resolved config

**Output schema:**
```json
{
  "status": "ok",
  "config": {
    "tts": {"provider": "kokoro", "voice": "af_sarah", "speed": 1.0},
    "audio": {
      "paragraph_pause_ms": 1000,
      "output_format": "mp3",
      "normalize_loudness": true,
      "fade_duration_ms": 2000,
      "volume_db": 0
    },
    "paths": {
      "posts": "posts/",
      "intro": "audio/intro/",
      "outro": "audio/outro/",
      "raw_output": "audio/raw/",
      "final_output": "audio/output/"
    }
  }
}
```

On invalid config, return `{"status": "error", "issues": [...]}` (same shape as `check` failure).

---

### Feature 3: `--dry-run` Flag on `generate`

**Problem:** An agent cannot validate inputs (voice, speed, format, post path) without actually running the pipeline. A dry run lets the agent check parameters safely before committing to a multi-minute synthesis job.

**Solution:** Add `--dry-run` flag to the `generate` command.

**Implementation:**
- File: `narrator.py`
- Add `@click.option("--dry-run", is_flag=True)` to the `generate` command
- After all pre-flight validation passes (and before calling `preprocess`), if `--dry-run` is set, print a plan and exit `0`

**Output schema:**
```json
{
  "status": "ok",
  "dry_run": true,
  "post": "posts/my-essay.md",
  "voice": "af_sarah",
  "speed": 1.0,
  "format": "mp3",
  "output_path": "audio/output/my-essay.mp3",
  "skip_intro": false,
  "skip_outro": false,
  "force": false
}
```

The resolved `output_path` is included so the agent knows where the file would land.

---

### Feature 4: Structured Progress Events on Stdout

**Problem:** Synthesis of a long post takes 3–6 minutes. An agent monitoring a subprocess has no machine-readable way to track progress — only unstructured stderr lines.

**Solution:** Emit newline-delimited JSON event lines to stdout during synthesis. The final `{"status": "ok", ...}` result line stays as-is; events precede it.

**Implementation:**
- File: `pipeline/synthesizer.py`
- After each segment synthesis, print an event line to stdout
- File: `narrator.py`
- After mix and encode, print stage-completion events

**Event schemas:**

```json
{"event": "preprocess_done", "paragraphs": 24}
{"event": "segment_done", "segment": 3, "total": 24, "voice": "af_sarah", "speed": 1.0}
{"event": "synthesis_done", "body_path": "audio/raw/my-essay/my-essay-body.wav"}
{"event": "mix_done", "mixed_path": "audio/raw/my-essay/my-essay-mixed.wav"}
{"event": "encode_done", "output_path": "audio/output/my-essay.mp3"}
```

Agents should treat any line starting with `{"event":` as a progress notification and lines with `{"status":` as the terminal result. Lines on stderr remain unstructured and should be ignored by agents.

**Opt-in consideration:** If event lines would break existing agent integrations that parse the single final JSON line, introduce a `--progress` flag to enable them. Default off until adoption is understood.

---

### Feature 5: `--output` Flag on `generate`

**Problem:** Output path is fully derived from the input filename and `config.yaml`. Agents integrating this tool into pipelines need to specify exact output locations.

**Solution:** Add `--output` option to `generate`.

**Implementation:**
- File: `narrator.py`
- Add `@click.option("--output", default=None, type=click.Path())` to `generate`
- If provided, use this path as `output_path` instead of the derived `{output_dir}/{post_name}.{fmt}`
- If the path has an extension, infer `fmt` from it (overrides `--format`)
- If the path has no extension, append `.{fmt}`

---

### Feature 6: `--post-name` Flag on `generate`

**Problem:** Post name is always derived from the input filename stem. Agents passing temp files (e.g., `/tmp/abc123.md`) get nonsensical output filenames and working directory names.

**Solution:** Add `--post-name` option to `generate`.

**Implementation:**
- File: `narrator.py`
- Add `@click.option("--post-name", default=None)` to `generate`
- If provided, use this value instead of `post_path.stem`
- Validation: slug must match `^[a-z0-9][a-z0-9-]*$`; reject with `_err()` if invalid
- Affects: `raw_dir` working subdirectory, output filename, intro/outro filename matching

---

### Feature 7: `setup --show-urls`

**Problem:** Agents (and users) cannot query the download URLs without actually triggering a download. This prevents pre-flight checks, offline planning, or manual download scripting.

**Solution:** Add `--show-urls` flag to `setup`.

**Implementation:**
- File: `narrator.py`
- Add `@click.option("--show-urls", is_flag=True)` to `setup`
- If set, print the download URL map as JSON and exit `0` without downloading anything

**Output schema:**
```json
{
  "status": "ok",
  "models": {
    "v0.19": {
      "onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx",
      "voices": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"
    },
    "v1.0": {
      "onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx",
      "voices": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
    }
  }
}
```

---

### Feature 8: `voices` Availability Annotation

**Problem:** The `voices` command returns the full known voice list including voices only available in the multilingual v1.0 model. An agent selecting a voice for an installed v0.19 model may pick one that fails at synthesis time.

**Solution:** Annotate each voice with `"available": true/false` based on which model is installed, and include `"model"` metadata.

**Implementation:**
- File: `tts/kokoro_provider.py`
- `list_voices()` already has access to `self._model_path`; check which model is loaded
- File: `narrator.py` `voices()` command
- Change output to include per-voice objects instead of bare strings

**Output schema (updated):**
```json
{
  "status": "ok",
  "provider": "kokoro",
  "installed_model": "v0.19",
  "models_on_disk": ["v0.19", "v1.0"],
  "voices": [
    {"id": "af_sarah", "available": true,  "requires_model": "v0.19"},
    {"id": "af_bella", "available": true,  "requires_model": "v0.19"},
    {"id": "am_puck",  "available": false, "requires_model": "v1.0"},
    {"id": "hf_alpha", "available": false, "requires_model": "v1.0"}
  ]
}
```

`models_on_disk` lists all model versions whose `.onnx` and voices files are both present, regardless of which is active in config. `requires_model` is determined per-voice via an explicit whitelist of the 10 v0.19 voices — not by prefix, since new English voices like `am_puck` are v1.0-only.

**Backwards compatibility note:** This is a breaking change to the `voices` schema — the `voices` array changes from `list[str]` to `list[object]`. Implement alongside a version indicator in the root object so agents can detect the new format.

---

### Feature 9: Resolved Config in `check` Output

**Problem:** The `check` command tells an agent whether config is valid, but not what the resolved values are. Agents must run a separate `config` command (Feature 2) to get the actual values, adding a round trip.

**Solution:** Include the resolved config in `check` success output.

**Implementation:**
- File: `narrator.py` `check()` function
- After all checks pass, load and include the full config in the success JSON

**Updated output schema:**
```json
{
  "status": "ok",
  "ffmpeg": true,
  "installed_model": "v0.19",
  "config": {
    "tts": {"provider": "kokoro", "voice": "af_sarah", "speed": 1.0},
    "audio": {"paragraph_pause_ms": 1000, "output_format": "mp3", "normalize_loudness": true, "fade_duration_ms": 2000, "volume_db": 0},
    "paths": {"posts": "posts/", "intro": "audio/intro/", "outro": "audio/outro/", "raw_output": "audio/raw/", "final_output": "audio/output/"}
  }
}
```

Once this is implemented, Feature 2 (`config` command) becomes optional — agents can get config from `check`. Keep the `config` command anyway for cases where a quick config read is needed without running all checks.

---

## Test Suite Plan

Place all tests in a top-level `tests/` directory. Use `pytest`. No external dependencies beyond what is in `requirements.txt` plus `pytest`.

### Test 1: `tests/test_preprocessor.py` — Unit

Target: `pipeline/preprocessor.py`

Cover each stripping function with known input → expected output pairs:
- Frontmatter stripped, body preserved
- Fenced code block removed, surrounding paragraphs preserved
- `![alt](url)` removed entirely
- `[text](url)` → `text`
- Bare URL removed
- `# Heading` → `Heading` (no `#`)
- `**bold**` → `bold`, `*italic*` → `italic`, `~~strike~~` → `strike`
- Backtick code removed
- `> blockquote` → `blockquote`
- Horizontal rule line removed
- `<html>` tags stripped
- Empty file → empty list
- Frontmatter-only file → empty list
- Mixed content → correct paragraph count

### Test 2: `tests/test_validate.py` — Unit

Target: `validate.py`

- `validate_config` with valid config → empty list
- `validate_config` missing `tts` section → error in list
- `validate_config` missing required key within section → error in list
- `check_ffmpeg` — mock `shutil.which` to return None → returns error string
- `check_post_file` with `.txt` extension → error
- `check_post_file` with empty file → error
- `check_post_file` with valid `.md` → empty list
- `check_voice_format` with `af_sarah` for kokoro → None (no error)
- `check_voice_format` with `INVALID` for kokoro → hint string
- `check_speed(0.5)` → None; `check_speed(2.0)` → None; `check_speed(0.4)` → error string; `check_speed(2.1)` → error string

### Test 3: `tests/test_cli_output.py` — Integration (mocked provider)

Target: `narrator.py` CLI command output

Use `click.testing.CliRunner` and a mock `TTSProvider` that returns a minimal silent WAV (generated with `pydub.AudioSegment.silent(100)`).

- `check` exits `0`, stdout is valid JSON with `status: ok`
- `check` with broken config exits `1`, stdout has `status: error` with `issues` array
- `voices` exits `0`, stdout has `status: ok` with `provider` and `voices` fields
- `generate` with valid post exits `0`, stdout has `status: ok` with `output_path`
- `generate` on already-existing output exits `0`, stdout has `status: skipped`
- `generate` with `--force` re-runs even when output exists
- `generate` with invalid speed exits `1`, stdout has `status: error`
- `generate` with `--raw-only` exits `0`, output_path points to WAV in `audio/raw/`

### Test 4: `tests/test_synthesizer_resume.py` — Unit (mocked provider)

Target: `pipeline/synthesizer.py`

Use a mock provider that records how many times `synthesize()` is called.

- Fresh run with N paragraphs → provider called N times, manifest shows all N complete
- Re-run with existing complete manifest → provider called 0 times (all skipped)
- Re-run with manifest missing segment 3 → provider called once (segment 3 only)
- Re-run with different voice → cache cleared, provider called N times again
- Re-run with different speed → cache cleared, provider called N times again
- `--force` with complete manifest → cache cleared, provider called N times

### Test 5: `tests/test_pipeline_smoke.py` — End-to-End

Target: full pipeline against `posts/sample.md` with real Kokoro provider

Mark with `@pytest.mark.slow` so it can be skipped in fast CI runs:
```bash
pytest -m "not slow"   # fast tests only
pytest                 # all tests including slow
```

Assertions:
- Exit code `0`
- Output file exists at the path returned in `output_path`
- `duration_sec` > 0
- Output file size > 0 bytes
- Re-running produces `status: skipped` (idempotency check)
- Re-running with `--force` produces `status: ok` again

---

## Implementation Phases

### Phase A — Documentation (Complete)
- [x] `wiki/agent-guidelines.md` — shared consumer + developer reference
- [x] `CLAUDE.md` — Claude Code conventions
- [x] `AGENTS.md` — generic agent quick-start
- [x] `wiki/features/agent-use-optimizations.md` — this file

### Phase B — Introspection Commands (Complete)
- [x] Feature 2: `config` command
- [x] Feature 1: `status` command
- [x] Feature 9: Resolved config in `check` output

These are pure additions (new commands, additive output fields). No existing behaviour changes. Implement together.

### Phase C — Input Control Flags (Complete)
- [x] Feature 6: `--post-name` on `generate`
- [x] Feature 5: `--output` on `generate`
- [x] Feature 3: `--dry-run` on `generate`
- [x] Feature 7: `setup --show-urls`

These are all new optional flags — fully backwards-compatible. Implement together.

### Phase D — Richer Output (Complete)
- [x] Feature 8: `voices` availability annotation (breaking schema change — coordinate with any existing consumers)
- [x] Feature 4: Structured progress events on stdout (implement with `--progress` flag; default off)

### Phase E — Test Suite (Complete)
- [x] Test 1: `tests/test_preprocessor.py`
- [x] Test 2: `tests/test_validate.py`
- [x] Test 3: `tests/test_cli_output.py`
- [x] Test 4: `tests/test_synthesizer_resume.py`
- [x] Test 5: `tests/test_pipeline_smoke.py`

Start with Tests 1 and 2 (pure unit tests, no I/O) to build confidence in the core logic. Then Test 4 (mocked I/O). Then Test 3 (CLI). Test 5 last (requires model files).

---

### Phase F — Usability Improvements (branch: `usability-improvements-1`)
- [x] Feature: `--cache-segments` flag on `generate` (caching off by default; opt-in writes segments and manifest)
- [x] Feature: Duplication warning on generate when output exists and `--force`/`--raw-only` is passed (stderr + `warn` JSON event)
- [x] Fix: Gradio getting-started link → GitHub URL
- [x] Agent files: `.gemini/settings.json` (points Gemini CLI at `AGENTS.md`)
- [x] Agent files: `AGENTS.md` updated with `--cache-segments` flag
- [x] Agent files: `.claude/commands/generate.md` updated to mention `--cache-segments`
- [x] Docs: `wiki/agent-guidelines.md` section 1.3 updated (options table, dry-run schema, `warn` event)
- [x] Tests: 5 new cases in `tests/test_synthesizer_resume.py` for in-memory vs. disk-cache paths

---

## Phase 4 Carryover: MCP Server

Tracked in `app-implementation.md` Phase 4. An MCP server wrapper would expose `generate_narration` as a tool, allowing agents to call it directly rather than invoking the CLI subprocess. The CLI-first design means the MCP server can be a thin wrapper around the same pipeline functions — no core changes required. Implement after Phase E.
