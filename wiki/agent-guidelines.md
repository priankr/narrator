# Narrator App — Agent Guidelines

Canonical reference for all agents interacting with this repository. Both `CLAUDE.md` and `AGENTS.md` point here. This document covers two distinct roles:

- **Consumer agent** — invokes the CLI to produce narrated audio from Markdown posts
- **Developer agent** — extends or maintains the Python codebase

Read the section that matches your current task. If you are doing both in the same session, read both.

---

## Prerequisites

Before any CLI interaction, verify these are present on the system:

| Requirement | How to check | Install hint |
|---|---|---|
| Python 3.10+ | `python --version` | python.org |
| ffmpeg on PATH | `ffmpeg -version` | ffmpeg.org/download |
| pip packages | `python narrator.py check` | `pip install -r requirements.txt` |
| Kokoro model files | `python narrator.py check` | `python narrator.py setup` |

**Run `python narrator.py check` as the first action in any session.** If it exits with code `1`, parse the `issues` array from stdout and resolve every item before proceeding. Do not run `generate` on a broken environment.

All CLI commands must be run from the **project root** — the directory containing `narrator.py` and `config.yaml`. Never `cd` into a subdirectory before invoking.

---

## Part 1: Using the App (Consumer Agent)

### 1.1 Correct Invocation Sequence

Always follow this order:

```
1. python narrator.py check          ← verify environment; halt if exit code 1
2. python narrator.py voices         ← discover available voices if needed
3. python narrator.py generate ...   ← produce audio
```

Never skip step 1. Steps 2 and 3 may be repeated in any order after the environment is confirmed healthy.

---

### 1.2 Command Reference

#### `check`

Validates config, ffmpeg, model files, and Python packages. On success, also returns the resolved configuration and detected model version.

```bash
python narrator.py check
```

No arguments or options. Exit code `0` = all checks passed. Exit code `1` = one or more issues.

---

#### `voices`

Lists all voice IDs available for the configured TTS provider.

```bash
python narrator.py voices
```

No arguments or options. Returns a JSON list of voice ID strings. Use these IDs as the value for `--voice` in `generate`.

**Voice ID format:** `^[a-z]{2}_[a-z]+$` — first two characters encode language and gender (`af_` = American Female, `am_` = American Male, `bf_` = British Female, `bm_` = British Male, etc.). See [`wiki/voices.md`](voices.md) for the complete prefix table and full voice catalog.

Only voices supported by the **installed model** are actually usable. The default v0.19 model ships with 10 specific English voices — not all English-prefix voices; newer voices like `am_puck` were added in v1.0 and are not available in v0.19. The multilingual v1.0 model has 54 voices across 9 languages. Passing a voice ID from the wrong model will produce a runtime error during synthesis.

---

#### `generate`

Runs the full pipeline: Preprocess → Synthesize → Mix → Encode.

```bash
python narrator.py generate <post-path> [options]
```

**Required argument:**
- `<post-path>` — path to a `.md` file, relative to the project root (e.g., `posts/my-essay.md`)

**Options:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--voice` | string | config value | Voice ID (must match an available voice) |
| `--format` | `mp3` \| `m4a` \| `wav` | config value | Output audio format |
| `--speed` | float | `1.0` | Speech speed multiplier; range `0.5`–`2.0` |
| `--no-intro` | flag | off | Skip intro clip even if one exists |
| `--no-outro` | flag | off | Skip outro clip even if one exists |
| `--raw-only` | flag | off | Stop after synthesis; skip mixing and encoding |
| `--force` | flag | off | Ignore existing segments and output; regenerate from scratch |
| `--post-name` | string | derived from filename | Override the slug used for working directories and output filenames |
| `--output` | path | derived from slug + format | Exact output file path; format inferred from extension if provided |
| `--dry-run` | flag | off | Validate all inputs and print the resolved plan without running the pipeline |
| `--progress` | flag | off | Emit JSON progress events to stdout during synthesis (see section 1.3) |
| `--cache-segments` | flag | off | Write segment files and `manifest.json` to disk; enables resume-on-failure |

**Parameter validation rules:**
- Speed outside `[0.5, 2.0]` → error before synthesis begins
- Format not in `{mp3, m4a, wav}` → Click rejects the command immediately
- Voice format not matching `^[a-z]{2}_[a-z]+$` → warning to stderr (not a hard error; invalid voices fail at synthesis time)
- `--post-name` not matching `^[a-z0-9][a-z0-9-]*$` → error before synthesis begins
- `--output` extension not in `{mp3, m4a, wav}` → error before synthesis begins
- Post file must exist and be non-empty

---

#### `config`

Prints the resolved configuration as JSON without running any checks.

```bash
python narrator.py config
```

No arguments or options. Useful for quickly reading the effective config when a full `check` is unnecessary.

---

#### `status`

Shows synthesis cache and output file state for every post in the `posts/` directory.

```bash
python narrator.py status
```

No arguments or options. Returns one entry per Markdown file found. Use this to discover what posts exist and whether they have been synthesized or encoded.

---

#### `setup`

Downloads Kokoro model files to `models/`.

```bash
python narrator.py setup               # v0.19 English model (10 voices, ~82 MB)
python narrator.py setup --multilingual # v1.0 multilingual model (54 voices, ~88 MB)
```

Run this once after cloning. Re-running is safe — already-downloaded files are skipped. Requires internet access. If a download fails, the error message includes the direct URL for manual download.

---

### 1.3 JSON Response Schemas

All structured output is printed as a single JSON line to **stdout**. Progress messages go to **stderr** and can be ignored for machine parsing.

#### `check` — success
```json
{
  "status": "ok",
  "ffmpeg": true,
  "installed_model": "v0.19",
  "hint": "v1.0 model is present but not active — set model_path and voices_path in config.yaml",
  "config": {
    "tts": {"provider": "kokoro", "voice": "af_sarah", "speed": 1.0},
    "audio": {"paragraph_pause_ms": 1000, "output_format": "mp3", "normalize_loudness": true, "fade_duration_ms": 2000, "volume_db": 0},
    "paths": {"posts": "posts/", "intro": "audio/intro/", "outro": "audio/outro/", "raw_output": "audio/raw/", "final_output": "audio/output/"}
  }
}
```

`installed_model` is the **active** model version (`"v0.19"`, `"v1.0"`, or `null`). `hint` is present only when v1.0 files are on disk but config still points to v0.19 — surface it to the user.

#### `check` — failure
```json
{
  "status": "error",
  "issues": [
    "config.yaml is missing required section 'tts'",
    "ffmpeg not found. Install from https://ffmpeg.org/download.html"
  ]
}
```

#### `voices` — success
```json
{
  "status": "ok",
  "provider": "kokoro",
  "installed_model": "v0.19",
  "models_on_disk": ["v0.19", "v1.0"],
  "voices": [
    {"id": "af_sarah",  "available": true,  "requires_model": "v0.19"},
    {"id": "af_bella",  "available": true,  "requires_model": "v0.19"},
    {"id": "hf_alpha",  "available": false, "requires_model": "v1.0"},
    {"id": "af_alloy",  "available": false, "requires_model": "v1.0"}
  ]
}
```

`installed_model` is the active model version per config. `models_on_disk` lists all versions whose model + voices files are present on disk. `available: true` means the voice works with the currently active model. `requires_model` is determined per-voice: the 10 original v0.19 English voices map to `"v0.19"`; everything else (including new English voices like `am_puck`) maps to `"v1.0"`. Always filter by `available: true` before selecting a voice to use.

#### `config` — success
```json
{
  "status": "ok",
  "config": {
    "tts": {"provider": "kokoro", "voice": "af_sarah", "speed": 1.0},
    "audio": {"paragraph_pause_ms": 1000, "output_format": "mp3", "normalize_loudness": true, "fade_duration_ms": 2000, "volume_db": 0},
    "paths": {"posts": "posts/", "intro": "audio/intro/", "outro": "audio/outro/", "raw_output": "audio/raw/", "final_output": "audio/output/"}
  }
}
```

For full descriptions of every config key (defaults, types, valid ranges), see [`wiki/configuration.md`](configuration.md).

#### `status` — success
```json
{
  "status": "ok",
  "posts": [
    {
      "name": "my-essay",
      "path": "posts\\my-essay.md",
      "synthesis": {
        "cached": true,
        "segments_done": 24,
        "total_paragraphs": 24,
        "voice": "af_sarah",
        "speed": 1.0
      },
      "output": [
        {"path": "audio\\output\\my-essay.mp3", "format": "mp3"}
      ]
    }
  ]
}
```

`synthesis` is `null` if the post has never been synthesized. `output` is `[]` if no encoded file exists yet.

#### `generate` — success
```json
{
  "status": "ok",
  "post": "posts/my-essay.md",
  "output_path": "audio/output/my-essay.mp3",
  "duration_sec": 187,
  "voice": "af_sarah",
  "format": "mp3"
}
```

#### `generate` — skipped (output already exists)
```json
{
  "status": "skipped",
  "reason": "output already exists",
  "output_path": "audio/output/my-essay.mp3",
  "hint": "pass --force to regenerate"
}
```

#### `generate` — progress events (with `--progress`)

When `--progress` is passed, JSON event lines are emitted to stdout before the terminal `{"status": ...}` line. Treat any line where the root key is `"event"` as a progress notification, not a result.

```json
{"event": "preprocess_done", "paragraphs": 24}
{"event": "warn", "message": "Output already exists: audio/output/my-essay.mp3. Regenerating."}
{"event": "segment_done", "segment": 3, "total": 24, "voice": "af_sarah", "speed": 1.0}
{"event": "synthesis_done", "body_path": "audio\\raw\\my-essay\\my-essay-body.wav"}
{"event": "mix_done", "mixed_path": "audio\\raw\\my-essay\\my-essay-mixed.wav"}
{"event": "encode_done", "output_path": "audio\\output\\my-essay.mp3"}
```

The `warn` event is emitted when the output file already exists but the run will proceed anyway (via `--force` or `--raw-only`). It appears after `preprocess_done` and before the first `segment_done`.

The final `{"status": "ok", ...}` line follows immediately after `encode_done`.

---

#### `generate` — dry run
```json
{
  "status": "ok",
  "dry_run": true,
  "post": "posts\\my-essay.md",
  "post_name": "my-essay",
  "voice": "af_sarah",
  "speed": 1.0,
  "format": "mp3",
  "output_path": "audio\\output\\my-essay.mp3",
  "would_skip": false,
  "skip_intro": false,
  "skip_outro": false,
  "force": false,
  "cache_segments": false
}
```

`would_skip: true` means the output file already exists and `--force` was not passed — an actual run without `--force` would return `status: skipped`.

#### `generate` — success with `--raw-only`
```json
{
  "status": "ok",
  "post": "posts/my-essay.md",
  "output_path": "audio/raw/my-essay/my-essay-body.wav",
  "voice": "af_sarah",
  "format": "wav"
}
```

#### Any command — error
```json
{"status": "error", "message": "human-readable description of what went wrong"}
```

#### `setup` — success
```json
{"status": "ok", "message": "Setup complete. Run 'python narrator.py check' to verify."}
```

#### `setup --show-urls` — success
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

### 1.4 Exit Codes

| Code | Meaning |
|---|---|
| `0` | Command completed successfully (`status: ok` or `status: skipped`) |
| `1` | Command failed (`status: error`) |

There are no other exit codes. Always check the exit code before parsing stdout.

---

### 1.5 Error Recovery Playbook

| Error message contains | Recovery action |
|---|---|
| `ffmpeg not found` | Halt; instruct user to install ffmpeg and add it to PATH |
| `model not found` | Run `python narrator.py setup` then retry |
| `voices file not found` | Run `python narrator.py setup` then retry |
| `Invalid config.yaml` | Surface the specific issue list to the user; do not modify `config.yaml` autonomously |
| `No text found after preprocessing` | The Markdown file is empty or contains only code/images; surface to user |
| `output already exists` (status: skipped) | Not an error — file is done. Use `--force` only if regeneration was explicitly requested |
| Any other error | Surface `message` field to user verbatim; do not retry automatically |

**Never retry a failed `generate` automatically.** Synthesis writes to disk; a retry without `--force` picks up from the last checkpoint, which may be correct behaviour — but only the user can confirm this.

---

### 1.6 File Layout — What to Read vs. Never Touch

```
narrator-app/
├── posts/               ← READ: input Markdown files live here
├── audio/
│   ├── intro/           ← READ: intro audio files (user-managed)
│   ├── outro/           ← READ: outro audio files (user-managed)
│   ├── raw/             ← READ ONLY: synthesis cache; do not modify
│   └── output/          ← READ: final audio output
├── config.yaml          ← READ; only modify with explicit user instruction
├── narrator.py          ← READ; entry point for CLI invocation
├── requirements.txt     ← READ; do not modify
└── models/              ← DO NOT TOUCH: binary model files
```

**Intro/outro file naming:** For a post named `my-essay.md`, the mixer looks for:
1. `audio/intro/my-essay-intro.*` — post-specific (any audio extension)
2. `audio/intro/default-intro.*` — shared fallback used for all posts
3. If neither exists, the intro/outro is skipped silently

The same pattern applies for outro files. The post name is the filename stem without `.md` — so `posts/my-essay.md` → `my-essay`. Files that don't match either pattern are silently skipped; verify the filename before running `generate` rather than relying on the stderr warning. See [`wiki/configuration.md`](configuration.md) for setup examples.

**Never delete or modify anything inside `audio/raw/`.** The manifest and segment files are the resume mechanism. Corrupting them forces a full re-synthesis.

---

### 1.7 Rules: What Not to Do

- Do not modify `config.yaml` without explicit user instruction.
- Do not pass `--force` unless the user has confirmed the existing output is stale or incorrect.
- Do not pass an untrusted or user-supplied string directly as `--voice` without first confirming it appears in the `voices` output.
- Do not invoke `generate` on a post that takes a long time (large file) without first informing the user of the expected duration.
- Do not run any command from a subdirectory — always from the project root.
- Do not parse stderr. Progress lines on stderr are human-readable and unstructured; their format may change without notice.

---

## Part 2: Developing the App (Developer Agent)

### 2.1 Architecture Overview

The app is a **linear four-stage pipeline** wired together in `narrator.py`. Each stage has one responsibility, accepts typed inputs, and returns a typed output. Intermediate files are written to disk at each boundary to enable resume on failure.

```
posts/my-essay.md
        │
        ▼
┌───────────────┐
│ Preprocessor  │  str → list[str]           pipeline/preprocessor.py
└───────┬───────┘
        ▼
┌───────────────┐
│  Synthesizer  │  list[str] → Path (WAV)    pipeline/synthesizer.py
└───────┬───────┘
        ▼
┌───────────────┐
│    Mixer      │  Path → Path (WAV)          pipeline/mixer.py
└───────┬───────┘
        ▼
┌───────────────┐
│    Encoder    │  Path → Path (final)        pipeline/encoder.py
└───────┬───────┘
        ▼
audio/output/my-essay.mp3
```

`narrator.py` is the orchestrator: it loads config, runs validation, instantiates the provider, and calls each stage in order. Pipeline modules do not import from each other or from `narrator.py`.

For deeper component detail (preprocessor steps, mixer logic, encoder formats, fault tolerance), see [`wiki/architechture.md`](architechture.md).

---

### 2.2 Pipeline Stage Contracts

Read the full source file before editing any stage. Changing a function signature requires updating the call site in `narrator.py`.

#### `pipeline/preprocessor.py`
- **Entry:** `preprocess(text: str) -> list[str]`
- **Input:** raw Markdown file content as a string
- **Output:** list of clean plain-text paragraphs, no empty strings
- **Side effects:** none (pure function)

#### `pipeline/synthesizer.py`
- **Entry:** `synthesize(paragraphs, post_name, provider, voice, speed, pause_ms, raw_dir, force, emit_progress, cache_segments) -> Path`
- **Input:** paragraph list + config values + provider instance
- **Output:** `Path` to assembled body WAV (`audio/raw/{post-name}/{post-name}-body.wav`)
- **Side effects (default):** no segment files or manifest written; audio assembled in memory
- **Side effects (with `cache_segments=True`):** writes `segment-*.wav` and `manifest.json` to `audio/raw/{post-name}/`
- **Resume logic:** only active when `cache_segments=True`; reads manifest on startup; skips completed segments; resets if voice or speed changed

#### `pipeline/mixer.py`
- **Entry:** `mix(body_path, post_name, intro_dir, outro_dir, normalize, fade_duration_ms, skip_intro, skip_outro, force) -> Path`
- **Input:** path to body WAV + config values
- **Output:** `Path` to mixed WAV (or body WAV if no intro/outro found)
- **Side effects:** writes `{post-name}-mixed.wav` to the same directory as the body WAV
- **Intro/outro matching:** `{role_dir}/{post-name}-{role}.*` → `{role_dir}/default-{role}.*` → skip

#### `pipeline/encoder.py`
- **Entry:** `encode(body_path, output_path, fmt, volume_db) -> Path`
- **Input:** path to mixed WAV + output path + format string + optional dB gain
- **Output:** `Path` to final output file
- **Side effects:** writes final file to `audio/output/`
- **Supported formats:** `mp3` (192k), `m4a` (ipod, 192k), `wav` (lossless)

---

### 2.3 TTS Provider Pattern

The TTS engine is abstracted behind `tts/base.py`:

```python
class TTSProvider(ABC):
    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> bytes: ...
    def list_voices(self) -> list[str]: ...
```

`narrator.py` loads the provider at runtime via `_load_provider(config)`. No pipeline code imports a specific provider. This is a stable interface — do not change the method signatures without updating all implementations.

**To add a new TTS provider:**
1. Create `tts/{name}_provider.py` implementing both methods
2. Add a branch for the new name in `_load_provider()` in `narrator.py`
3. Set `tts.provider: {name}` in `config.yaml` to activate it

---

### 2.4 Where to Make Changes

| Change type | File(s) to edit |
|---|---|
| New TTS provider | `tts/{name}_provider.py` + `narrator.py` (`_load_provider`) |
| New CLI command | `narrator.py` (`@cli.command()` decorator) |
| New flag on `generate` | `narrator.py` (`@click.option`) + pass through to relevant stage |
| New pipeline stage | New file in `pipeline/` + wire in `narrator.py` |
| New config key | `config.yaml` + `validate.py` (`validate_config`) + read in `narrator.py` |
| New output format | `pipeline/encoder.py` (`SUPPORTED_FORMATS`, export logic) + `narrator.py` |
| Preprocessing rule | `pipeline/preprocessor.py` (add a new `_strip_*` function, call it in `preprocess`) |
| Pre-flight validation | `validate.py` + call site in `narrator.py` |

---

### 2.5 Coding Conventions

- **Type hints are required** on all public function signatures (parameters and return types). Use Python 3.10+ union syntax (`X | None`, not `Optional[X]`).
- **No multi-line docstrings.** A single short line is acceptable when the function name alone is insufficient. Most functions need no docstring.
- **No comments unless the WHY is non-obvious** — a hidden constraint, a workaround, a subtle invariant. Do not narrate what the code does.
- **No dead code.** Remove rather than comment out.
- **No backwards-compatibility shims** for code that hasn't shipped to external users.
- **stdout is machine-readable.** Any new command must print JSON via `_ok()`. Never print plain text to stdout.
- **stderr is human-readable.** Progress messages and hints go to stderr via `print(..., file=sys.stderr)`.
- **Errors must exit 1.** Use `_err(message)` — it prints the error JSON and calls `sys.exit(1)`.
- **Relative paths in config.** All paths in `config.yaml` are relative to the project root. Resolve them with `Path(config["paths"]["key"])` — do not hardcode paths in pipeline files.

---

### 2.6 Stable vs. Evolving Surfaces

**Stable — do not change without strong justification:**
- `TTSProvider` abstract interface (`tts/base.py`) — all providers depend on this
- stdout JSON schemas — consumer agents parse these; breaking changes require all callers to update
- Exit codes (0/1)
- `config.yaml` key names for the three core sections (`tts`, `audio`, `paths`) — changing key names is a breaking config migration

**Evolving — safe to extend:**
- Individual pipeline stage internals (e.g., preprocessing steps, mixer gain logic)
- `narrator.py` command set — new commands are additive
- CLI flags on existing commands — new optional flags are additive
- `validate.py` validation rules — tightening validation is safe; loosening requires care
- `wiki/` — always keep in sync with code changes

---

### 2.7 Testing

```bash
pytest -m "not slow"   # fast tests only (~3s, no model required)
pytest                  # all tests including end-to-end (requires Kokoro model + ffmpeg)
```

| File | Type | What it covers |
|---|---|---|
| `tests/test_preprocessor.py` | Unit | All Markdown stripping functions, paragraph splitting, edge cases |
| `tests/test_validate.py` | Unit | Config validation, ffmpeg check, file checks, voice/speed validation |
| `tests/test_synthesizer_resume.py` | Unit (mock provider) | Manifest logic, segment skipping, force reset, voice change cache clear |
| `tests/test_cli_output.py` | Integration | All command JSON shapes — real env (group A) and mocked pipeline (group B) |
| `tests/test_pipeline_smoke.py` | End-to-end (slow) | Full generate run on `posts/sample.md` with real Kokoro model |

When adding a new feature: write tests in the matching file. New CLI commands → group A in `test_cli_output.py`. New pipeline behaviour → `test_synthesizer_resume.py` or a new file. New preprocessing rule → `test_preprocessor.py`.

---

### 2.8 Future Work

These are tracked in `wiki/features/agent-use-optimizations.md`. Do not implement them speculatively — implement only what the user asks for.

- MCP server wrapper exposing `generate_narration` as a tool
- Batch processing: `generate posts/*.md`
- Additional TTS providers (Coqui XTTS v2, Piper)
