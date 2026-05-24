# Architecture

## Overview

Narrator App is a local CLI tool with a linear four-stage pipeline. Each stage has a single responsibility and passes its output to the next stage via a file on disk.

```
posts/my-essay.md
        │
        ▼
┌───────────────┐
│ Preprocessor  │  Markdown → clean paragraph list
└───────┬───────┘
        │  list[str]
        ▼
┌───────────────┐
│  Synthesizer  │  Paragraphs → assembled body WAV
└───────┬───────┘
        │  body.wav
        ▼
┌───────────────┐
│    Mixer      │  body + intro + outro → mixed WAV
└───────┬───────┘
        │  mixed.wav (or body.wav if no intro/outro)
        ▼
┌───────────────┐
│    Encoder    │  WAV → final output format (MP3, M4A, WAV)
└───────┬───────┘
        │
        ▼
audio/output/my-essay.mp3
```

All intermediate files are written to `audio/raw/{post-name}/`. The final output is written to `audio/output/`.

---

## Components

### `narrator.py` — CLI Entry Point

Built with [Click](https://click.palletsprojects.com/). Exposes four commands:

| Command | Purpose |
|---------|---------|
| `generate` | Run the full pipeline for a post |
| `voices` | List all known voice IDs annotated with `available` and `requires_model` |
| `check` | Validate config, ffmpeg, model files, and Python packages; return resolved config on success |
| `config` | Print the resolved configuration as JSON |
| `status` | Show synthesis cache and output file state for every post in `posts/` |
| `setup` | Download Kokoro model files to `models/`. Pass `--multilingual` for the v1.0 model with 9-language support. |

The `generate` command runs pre-flight validation before any synthesis begins, so configuration errors and missing dependencies are caught upfront rather than after minutes of processing.

All structured output (results, errors) is written as JSON to stdout. Progress messages are written to stderr. This separation makes the CLI machine-readable for agent use.

### `validate.py` — Input Validation

Pre-flight checks called at the start of `generate`:
- Config schema validation (required keys, value types and ranges)
- ffmpeg availability
- Post file checks (extension, empty file)
- Voice ID format hint for Kokoro voices

### `pipeline/preprocessor.py` — Markdown Preprocessing

Converts raw Markdown to a plain-text paragraph list before synthesis. Strips in this order:

1. YAML frontmatter
2. Fenced and indented code blocks
3. Images
4. Markdown links (keeps link text, drops URL)
5. Bare URLs
6. Heading markers (keeps heading text — it is read aloud)
7. Bold, italic, and strikethrough markers
8. Inline code
9. Blockquote markers
10. Horizontal rules
11. HTML tags
12. Abbreviation expansion (replaces entries from `abbreviations.yaml` with their spoken equivalents)

Paragraphs are split on double newlines. Internal single newlines within a paragraph are collapsed to a space so a paragraph reads as one continuous sentence.

### `pipeline/synthesizer.py` — TTS Synthesis

Synthesizes each paragraph independently via the `TTSProvider` interface and assembles all results into a single body WAV with configurable silence between paragraphs.

Key behaviours:
- **In-memory assembly (default):** Synthesized bytes are held in memory and assembled directly into `{post-name}-body.wav`. No `segment-*.wav` files or `manifest.json` are written.
- **Disk caching (opt-in, `--cache-segments`):** Each paragraph is written to `segment-NNN.wav` immediately after synthesis. `manifest.json` records completed indices and the voice/speed used. A mismatch in voice or speed resets the cache. A re-run skips already-completed segments, enabling resume-on-failure.
- **Silence insertion:** `pydub.AudioSegment.silent(duration=pause_ms)` is concatenated between paragraph segments (configurable via `audio.paragraph_pause_ms` in `config.yaml`).

### `pipeline/mixer.py` — Intro/Outro Mixing

Loads intro and outro audio files (any format supported by ffmpeg), optionally normalizes loudness, and concatenates them with the body. If no intro/outro files are found, the body WAV is returned unchanged with no extra file written.

Filename matching — for a post named `my-essay.md`, the mixer looks for:
1. `audio/intro/my-essay-intro.*` (post-specific)
2. `audio/intro/default-intro.*` (shared fallback)

### `pipeline/encoder.py` — Format Encoding

Exports the mixed WAV to the final output format using `pydub`. Supported outputs:

| Format | pydub format name | Default bitrate |
|--------|------------------|-----------------|
| `mp3` | `mp3` | 192k |
| `m4a` | `ipod` | 192k |
| `wav` | `wav` | lossless |

WAV is used as the intermediate format throughout the pipeline. Lossy encoding (MP3, M4A) is applied only at this final step to avoid stacking compression artifacts.

---

## TTS Provider Pattern

The TTS engine is hidden behind an abstract interface so it can be replaced without touching the pipeline.

```
tts/base.py          ← TTSProvider (ABC)
tts/kokoro_provider.py ← KokoroProvider(TTSProvider)
```

`TTSProvider` defines two methods:
- `synthesize(text, voice, speed) -> bytes` — returns raw WAV bytes
- `list_voices() -> list[str]` — returns available voice IDs

`narrator.py` loads the provider named in `config.yaml` and passes it to the synthesizer. No pipeline code imports a specific provider directly.

To add a new provider, implement the two methods in `tts/{name}_provider.py` and register the name in `narrator.py`'s `_load_provider()`.

### Kokoro-82M

The default provider uses [Kokoro-82M](https://github.com/hexgrad/kokoro) via the `kokoro-onnx` package. It runs entirely on CPU (ONNX Runtime) — no GPU required. Model files are stored in `models/` and downloaded by `narrator.py setup`.

Two model versions are supported:

| Model | Size | Voices | Command |
|-------|------|--------|---------|
| v0.19 (default) | ~82 MB | 10 English voices | `python narrator.py setup` |
| v1.0 (multilingual) | ~88 MB | 54 voices, 9 languages | `python narrator.py setup --multilingual` |

Voice IDs follow a prefix convention: first character = language/accent (`a` = American English, `b` = British English, `e` = Spanish, `j` = Japanese, etc.), second character = gender (`f` = female, `m` = male). See [voices.md](voices.md) for the full list.

---

## Fault Tolerance

Long-form posts (2,000–3,000+ words) can take 3–6 minutes to synthesize on CPU. Two layers of checkpointing protect against mid-run failures:

**Paragraph-level (synthesizer, opt-in with `--cache-segments`):**
Pass `--cache-segments` to write each paragraph to `audio/raw/{post-name}/segment-NNN.wav` immediately after synthesis. `manifest.json` records completed segment indices and the voice/speed used. On re-run, completed segments are skipped — a failure at paragraph 15 of 25 resumes from paragraph 15. Without `--cache-segments` (the default), synthesis runs entirely in memory and resume is not available.

**Stage-level (mixer and encoder):**
If `{post-name}-mixed.wav` or the final output file already exists, the corresponding stage is skipped. Pass `--force` to bypass all checkpoints and regenerate from scratch.

```
audio/raw/{post-name}/
├── segment-001.wav          ← paragraph 1 audio  (only with --cache-segments)
├── segment-002.wav          ←                     (only with --cache-segments)
├── ...
├── manifest.json            ← resume tracker      (only with --cache-segments)
├── {post-name}-body.wav     ← assembled body (post-synthesis checkpoint)
└── {post-name}-mixed.wav    ← body + intro/outro (post-mix checkpoint)
```

---

## Directory Structure

```
narrator-app/
├── posts/                   # Input: Markdown posts
├── audio/
│   ├── intro/               # Optional intro audio clips
│   ├── outro/               # Optional outro audio clips
│   ├── raw/
│   │   └── {post-name}/     # Per-post working directory (segments, manifest, body)
│   └── output/              # Final output audio files
├── models/                  # Kokoro model files (downloaded by setup)
├── tts/
│   ├── base.py              # TTSProvider abstract interface
│   └── kokoro_provider.py   # Kokoro-82M implementation
├── pipeline/
│   ├── preprocessor.py
│   ├── synthesizer.py
│   ├── mixer.py
│   └── encoder.py
├── narrator.py              # CLI entry point
├── validate.py              # Pre-flight validation
├── config.yaml
├── requirements.txt
└── LICENSE
```
