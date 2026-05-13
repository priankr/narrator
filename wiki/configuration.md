# Configuration Guide

This guide covers everything you need to configure and run Narrator App.

---

## Prerequisites

| Requirement | Version | Install |
|-------------|---------|---------|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/) |
| ffmpeg | Any recent | [ffmpeg.org/download](https://ffmpeg.org/download.html) |

> **Python 3.13+ note:** The `audioop` module was removed from the Python standard library in 3.13. The `requirements.txt` includes `audioop-lts` as a compatibility shim for `pydub`, so `pip install -r requirements.txt` handles this automatically — no manual action needed.

---

## Installation

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Download the Kokoro TTS model files (~82 MB total)
python narrator.py setup

# 3. Confirm everything is working
python narrator.py check
```

`narrator.py check` validates config, ffmpeg, model files, and Python packages and prints a `[OK]` or `[FAIL]` for each.

---

## config.yaml Reference

All app behaviour is controlled by `config.yaml` in the project root.

```yaml
tts:
  provider: kokoro
  voice: af_sarah
  speed: 1.0

audio:
  paragraph_pause_ms: 1000
  output_format: mp3
  normalize_loudness: true

paths:
  posts: posts/
  intro: audio/intro/
  outro: audio/outro/
  raw_output: audio/raw/
  final_output: audio/output/
```

### `tts` section

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `provider` | string | `kokoro` | TTS engine to use. Currently only `kokoro` is supported. |
| `voice` | string | `af_sarah` | Voice ID. See [voices.md](voices.md) for the full list. |
| `speed` | float | `1.0` | Playback speed. Valid range: `0.5` (slower) to `2.0` (faster). |
| `model_path` | string | *(auto)* | Optional. Override the default path to the Kokoro `.onnx` model file. |
| `voices_path` | string | *(auto)* | Optional. Override the default path to the Kokoro `voices.bin` file. |

### `audio` section

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `paragraph_pause_ms` | integer | `1500` | Silence inserted between paragraphs, in milliseconds. |
| `output_format` | string | `mp3` | Default output format. Options: `mp3`, `m4a`, `wav`. |
| `normalize_loudness` | boolean | `true` | RMS-match intro and outro loudness to the body audio before mixing. Prevents volume jumps between segments. |
| `fade_duration_ms` | integer | `2000` | Fade out the last N milliseconds of the intro and fade in the first N milliseconds of the outro. Set to `0` to disable. |
| `volume_db` | float | `0` | Output volume adjustment in decibels. `0` = no change. Positive values increase volume, negative values decrease it (e.g. `3` is noticeably louder, `-3` is noticeably quieter). |

### `paths` section

| Key | Default | Description |
|-----|---------|-------------|
| `posts` | `posts/` | Where Narrator looks for `.md` input files. |
| `intro` | `audio/intro/` | Where Narrator looks for intro audio clips. |
| `outro` | `audio/outro/` | Where Narrator looks for outro audio clips. |
| `raw_output` | `audio/raw/` | Working directory for synthesis cache and assembled body audio. |
| `final_output` | `audio/output/` | Where finished audio files are saved. |

---

## Choosing a Voice

See [voices.md](voices.md) for the complete voice reference, including accent and gender breakdowns.

**Quick change in `config.yaml`:**
```yaml
tts:
  voice: am_michael   # American Male
```

**One-off via CLI:**
```bash
python narrator.py generate posts/my-essay.md --voice bf_emma
```

**List all voices available on your machine:**
```bash
python narrator.py voices
```

---

## Adding Intro and Outro Audio

Place audio files in `audio/intro/` and `audio/outro/`. Narrator supports MP3, WAV, M4A, OGG, and FLAC.

**Matching logic — Narrator looks in this order:**

1. Post-specific file: `audio/intro/{post-name}-intro.*`
   - e.g. `audio/intro/my-essay-intro.mp3` for `posts/my-essay.md`
2. Shared fallback: `audio/intro/default-intro.*`
   - Used for every post that doesn't have a specific file
3. If neither exists, intro is skipped (no error)

The same logic applies to outro files.

**Example setup for a shared intro/outro across all posts:**
```
audio/
├── intro/
│   └── default-intro.mp3
└── outro/
    └── default-outro.mp3
```

**Example with a post-specific intro:**
```
audio/
├── intro/
│   ├── default-intro.mp3        ← used for all other posts
│   └── special-edition-intro.mp3 ← used only for posts/special-edition.md
```

---

## Output Formats

| Format | Best for |
|--------|----------|
| `mp3` | **Default.** Substack, podcast hosts, universal browser support |
| `m4a` | Apple ecosystem; smaller file size than MP3 at equivalent quality |
| `wav` | Lossless; use if you plan to edit the audio further in Audacity or similar |

Override at runtime:
```bash
python narrator.py generate posts/my-essay.md --format m4a
```

---

## CLI Reference

### `generate`

```bash
python narrator.py generate <post.md> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--voice ID` | Voice ID (overrides `config.yaml`) |
| `--format mp3\|m4a\|wav` | Output format (overrides `config.yaml`) |
| `--speed FLOAT` | Speech speed, 0.5–2.0 (overrides `config.yaml`) |
| `--no-intro` | Skip intro even if a file exists |
| `--no-outro` | Skip outro even if a file exists |
| `--raw-only` | Stop after synthesis — output the body WAV without mixing or encoding |
| `--force` | Ignore cached segments and existing output; regenerate from scratch |
| `--post-name SLUG` | Override the slug used for working directories and output filenames (must match `^[a-z0-9][a-z0-9-]*$`) |
| `--output PATH` | Exact output file path; format inferred from the extension if provided |
| `--dry-run` | Validate all inputs and print the resolved plan without running the pipeline |
| `--progress` | Emit JSON progress events to stdout during synthesis |

### `voices`

```bash
python narrator.py voices
```

Returns an annotated list of all known voice IDs. Each entry includes `"available"` (whether the voice works with the currently installed model) and `"requires_model"` (`"v0.19"` or `"v1.0"`). Filter by `available: true` before selecting a voice to use.

### `check`

```bash
python narrator.py check
```

Validates your setup: `config.yaml`, ffmpeg, Kokoro model files, and Python packages. Run this first if something isn't working.

### `status`

```bash
python narrator.py status
```

Shows synthesis cache and output file state for every `.md` file in `posts/`. Useful for seeing at a glance which posts have been synthesized and which have a finished output file.

### `config`

```bash
python narrator.py config
```

Prints the fully resolved `config.yaml` as JSON. Useful for quickly reading the effective configuration without running a full `check`.

### `setup`

```bash
python narrator.py setup [--multilingual]
```

Downloads the Kokoro model files into `models/`. Only needs to be run once.

| Option | Description |
|--------|-------------|
| `--multilingual` | Download the Kokoro v1.0 model (~88 MB) for multilingual support instead of the default v0.19 English model. See [Multilingual Model](#multilingual-model) for full setup. |
| `--show-urls` | Print the download URLs for all model files as JSON without downloading anything. |

---

## Multilingual Model

By default, Narrator uses **Kokoro v0.19** — 10 English voices, ~82 MB. This is the model the [voice samples](../samples/) were recorded with.

A separate **Kokoro v1.0** model is available with support for 9 languages and 54 voices (~88 MB, int8 quantized). The English voices in v1.0 have different voice characteristics from v0.19 — they are not drop-in replacements.

**Step 1 — download the multilingual model:**
```bash
python narrator.py setup --multilingual
```

Both models can coexist in `models/` — `setup --multilingual` only adds the v1.0 files and does not replace the default ones.

**Step 2 — point `config.yaml` at the new files:**
```yaml
tts:
  voice: ef_dora           # any v1.0 voice ID
  model_path: models/kokoro-v1.0.int8.onnx
  voices_path: models/voices-v1.0.bin
```

See [voices.md](voices.md) for the full list of languages and voice IDs available in v1.0.

---

## Fault Tolerance and Resume

Narrator saves each paragraph as a numbered audio segment immediately after it is synthesized. If a run is interrupted, re-running the same command resumes from where it left off — completed paragraphs are skipped.

To start completely fresh, pass `--force`:
```bash
python narrator.py generate posts/my-essay.md --force
```

Cached segments are stored in `audio/raw/{post-name}/` and can be safely deleted at any time.
