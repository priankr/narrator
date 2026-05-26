# Narrator App — Agent Guide

Full instructions are in [wiki/agent-guidelines.md](wiki/agent-guidelines.md). This file is a quick-start summary for generic agents (non-Claude).

---

## What This App Does

A local CLI tool that converts Markdown posts into narrated audio files (MP3, M4A, or WAV). Place a `.md` file in `posts/`, run one command, receive a finished audio file in `audio/output/`.

---

## Environment Requirements

- Python 3.10+
- ffmpeg installed and on PATH
- pip packages: `pip install -r requirements.txt`
- Kokoro model files: `python narrator.py setup`

---

## Mandatory First Step

Always run this before any other command:

```bash
python narrator.py check
```

Exit code `0` = environment is ready. Exit code `1` = parse the `issues` array from stdout and resolve every item before proceeding.

---

## Basic Workflow

```bash
# 1. Verify environment
python narrator.py check

# 2. List available voices (optional — skip if you already know the voice to use)
python narrator.py voices

# 3. Generate narration
python narrator.py generate posts/my-post.md

# 4. Generate with explicit options
python narrator.py generate posts/my-post.md --voice af_bella --format m4a --speed 0.95
```

All commands print a single JSON line to stdout. Parse that for results. Ignore stderr (human-readable progress only).

---

## All Commands

| Command | Purpose |
|---|---|
| `check` | Validate environment; returns resolved config on success |
| `config` | Print the resolved configuration as JSON |
| `status` | List all posts with their synthesis cache and output state |
| `voices` | List voices annotated with `available` and `requires_model` |
| `generate <post.md>` | Run the full pipeline and produce an audio file |
| `remix <post.md>` | Re-mix intro/outro with an existing body WAV without re-synthesizing |
| `setup` | Download Kokoro model files (run once after install) |
| `setup --multilingual` | Download the v1.0 model (54 voices, 9 languages) |
| `setup --show-urls` | Print download URLs as JSON without downloading |

**Key `generate` flags for agent use:**

| Flag | Purpose |
|---|---|
| `--dry-run` | Validate inputs and print resolved plan without running the pipeline |
| `--post-name <slug>` | Override the slug derived from the filename |
| `--output <path>` | Write output to an exact path (format inferred from extension) |
| `--progress` | Emit JSON progress events to stdout during synthesis |
| `--force` | Discard cached segments and regenerate from scratch |
| `--cache-segments` | Write segment files and manifest to disk; enables resume-on-failure (off by default) |

---

## Key Rules

- Run all commands from the **project root** (the directory containing `narrator.py`).
- Never modify `config.yaml` without explicit user instruction.
- Never pass `--force` without confirming the user wants to discard the cached synthesis.
- Never edit files in `audio/raw/` — these are the resume cache.
- Exit code `0` with `status: skipped` is not an error — the output file already exists.

---

See [wiki/agent-guidelines.md](wiki/agent-guidelines.md) for the full JSON response schemas, error recovery playbook, and developer guidelines.
