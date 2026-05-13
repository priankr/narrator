# App Implementation Plan

## Overview

Narrator App is a local CLI tool that converts Markdown posts into narrated MP3 audio files. Users place a `.md` file in `posts/`, run one command, and receive a finished audio file in `audio/` — optionally bookended by custom intro and outro clips.

---

## Repo Structure

```
narrator-app/
├── posts/                        # Input: user's markdown posts
├── audio/
│   ├── intro/                    # Optional intro audio clips
│   ├── outro/                    # Optional outro audio clips
│   ├── raw/
│   │   └── {post-name}/          # Working directory per post
│   │       ├── segment-001.wav   # Individual paragraph audio
│   │       ├── segment-NNN.wav
│   │       ├── manifest.json     # Synthesis progress tracker
│   │       └── {post-name}-body.wav  # Assembled body, pre-mix
│   └── output/                   # Final output audio files
├── models/                       # Kokoro model files (downloaded by setup)
├── samples/                      # Voice sample MP3s for the README
├── tts/
│   ├── base.py                   # Abstract TTSProvider interface
│   └── kokoro_provider.py        # Kokoro-82M implementation
├── pipeline/
│   ├── preprocessor.py           # Markdown → clean paragraph list
│   ├── synthesizer.py            # Paragraph list → WAV segments via TTSProvider
│   ├── mixer.py                  # Intro + body + outro → combined WAV
│   └── encoder.py                # WAV → final output format (mp3, m4a, wav)
├── narrator.py                   # CLI entry point
├── narrator_ui.py                # Gradio browser UI
├── validate.py                   # Pre-flight validation
├── config.yaml                   # User-facing configuration
├── requirements.txt
├── LICENSE                       # MIT
├── docs/                         # GitHub Pages site (HTML/CSS/JS)
└── wiki/
    ├── architechture.md
    ├── configuration.md
    ├── getting-started.md
    ├── voices.md
    └── features/
        └── app-implementation.md # This file
```

---

## Configuration

`config.yaml` is the single place users control app behavior. It is read at startup and passed through the pipeline.

```yaml
tts:
  provider: kokoro          # Swappable: "kokoro" | "coqui" | "piper"
  voice: af_sarah           # Voice ID from the selected provider
  speed: 1.0                # Playback speed multiplier (0.5–2.0)

audio:
  paragraph_pause_ms: 1000  # Silence inserted between paragraphs
  output_format: mp3        # Default output format: "mp3" | "m4a" | "wav"
  normalize_loudness: true  # Normalize intro/outro/body to same loudness level

paths:
  posts: posts/
  intro: audio/intro/
  outro: audio/outro/
  raw_output: audio/raw/
  final_output: audio/output/
```

---

## Pipeline Stages

### Stage 1 — Preprocessing (`pipeline/preprocessor.py`)

Converts a Markdown file into a clean list of plain-text paragraphs ready for TTS.

**Steps, in order:**

1. **Strip YAML frontmatter** — remove everything between opening and closing `---` delimiters
2. **Strip Markdown headings** — remove `#`, `##`, etc. markers; keep the heading text so it is still read aloud
3. **Strip formatting markers** — remove `**`, `*`, `__`, `_`, `~~` (bold, italic, strikethrough). Read the plain text.
4. **Strip URLs** — remove bare URLs and Markdown link syntax (`[text](url)` → keep `text`, drop URL entirely)
5. **Strip images** — remove `![alt](url)` entirely
6. **Strip inline code and code blocks** — remove backtick spans and fenced blocks; they are not narration-friendly
7. **Strip HTML tags** — remove any residual HTML
8. **Normalize whitespace** — collapse multiple blank lines to a single paragraph boundary
9. **Split into paragraphs** — split on double newlines; filter out empty strings

**Output:** `list[str]` — one entry per paragraph, plain text only.

**Example:**

```
Input:  "Read **this carefully** or visit https://example.com for more."
Output: "Read this carefully or visit for more."
```

---

### Stage 2 — Synthesis (`pipeline/synthesizer.py`)

Converts the paragraph list into a single assembled body WAV, with each paragraph written to disk as it completes so that a failure mid-way does not require restarting from scratch.

**Long-form note:** Substack posts typically run 2,000–3,000+ words. On CPU (no GPU), Kokoro processes roughly 500–800 words/minute, so a 3,000-word post takes approximately 3–6 minutes. The paragraph-by-paragraph architecture naturally keeps each synthesis call within Kokoro's internal character limit without any additional chunking logic.

**Segment caching and resume logic:**

Each paragraph is saved as a numbered WAV file immediately after synthesis. A `manifest.json` tracks which segments are complete. On re-run, already-completed segments are skipped — a failure at paragraph 15 of 25 resumes from paragraph 15.

`manifest.json` structure:
```json
{
  "post": "posts/my-essay.md",
  "voice": "af_sarah",
  "speed": 1.0,
  "total_paragraphs": 24,
  "completed": [1, 2, 3, 4, 5]
}
```

**Steps:**

1. Load the configured `TTSProvider` (see TTS Provider section below)
2. Create working directory `audio/raw/{post-name}/` if it does not exist
3. Load `manifest.json` if it exists; otherwise create it
4. For each paragraph (with progress printed to stderr, e.g. `[3/24] Synthesizing paragraph 3...`):
   - Skip if segment file already exists in the manifest
   - Call `provider.synthesize(text, voice, speed)` → returns raw WAV bytes
   - Write to `audio/raw/{post-name}/segment-{NNN}.wav`
   - Update `manifest.json` with the completed segment index
5. Insert a silence segment of `paragraph_pause_ms` milliseconds between each paragraph segment
6. Concatenate all segments in order → save to `audio/raw/{post-name}/{post-name}-body.wav`

**Output:** `audio/raw/{post-name}/{post-name}-body.wav`

---

### Stage 3 — Mixing (`pipeline/mixer.py`)

Combines intro, body, and outro into a single WAV file.

**Checkpointing:** If `audio/raw/{post-name}/{post-name}-body.wav` already exists, this stage is skipped on re-run. The body is only reassembled if synthesis re-runs from scratch or `--force` is passed.

**Steps:**

1. Load body audio from `audio/raw/{post-name}/{post-name}-body.wav`
2. If an intro file exists in `audio/intro/` matching the post name (or a default intro), load it — accept MP3, WAV, M4A, OGG
3. If an outro file exists in `audio/outro/` matching the post name (or a default outro), load it — same formats
4. If `normalize_loudness` is enabled, normalize all three segments to the same RMS loudness level using `pydub.effects.normalize`
5. Concatenate: `[intro] + body + [outro]` (intro and outro are optional)
6. Save as combined WAV (intermediate, not the final output)

**Intro/outro filename matching logic:**
- First look for `audio/intro/{post-name}-intro.*`
- Fall back to `audio/intro/default-intro.*`
- If neither exists, skip intro (same logic for outro)

---

### Stage 4 — Encoding (`pipeline/encoder.py`)

Exports the final mixed WAV to the user's chosen format.

**Supported output formats:**

| Format | Notes |
|--------|-------|
| `mp3` | Default. 192kbps. Universal platform support (Substack, podcast hosts, browsers) |
| `m4a` | AAC encoding. Smaller file, native iOS/macOS/Windows Voice Recorder format |
| `wav` | Lossless. Use if the user wants to edit further in Audacity or similar |

**Checkpointing:** If `audio/output/{post-name}.{format}` already exists, this stage is skipped on re-run unless `--force` is passed.

**Steps:**

1. Load the mixed WAV from Stage 3
2. Export using `pydub` with the configured format and bitrate
3. Save to `audio/output/{post-name}.{format}`
4. Print structured result to stdout (see CLI section)

**Dependency:** `ffmpeg` must be installed on the system. The app checks for it at startup and exits with a clear error message if missing.

---

## TTS Provider Pattern

The TTS engine is abstracted behind a common interface so it can be swapped without touching the pipeline.

### Abstract Base (`tts/base.py`)

```python
from abc import ABC, abstractmethod

class TTSProvider(ABC):

    @abstractmethod
    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> bytes:
        """Synthesize text to speech. Returns raw WAV bytes."""
        ...

    @abstractmethod
    def list_voices(self) -> list[str]:
        """Return all available voice IDs for this provider."""
        ...
```

### Kokoro Provider (`tts/kokoro_provider.py`)

- **Model:** Kokoro-82M v0.19 by default (pip-installable, ~82MB, no GPU required); v1.0 multilingual model available via `setup --multilingual`
- **Voices:** 10 English voices in v0.19; 54 voices across 9 languages in v1.0. Default voice: `af_sarah`
- **Long-form handling:** Kokoro has an internal character limit per call. The synthesizer already splits on paragraphs, so each call receives a short text segment — this naturally stays within limits.
- **Installation:** `pip install kokoro-onnx` (CPU-only runtime, no CUDA required)

### Adding a New Provider

1. Create `tts/{name}_provider.py`
2. Implement `TTSProvider.synthesize()` and `TTSProvider.list_voices()`
3. Register the name in `narrator.py`'s provider loader
4. Set `tts.provider: {name}` in `config.yaml`

No other code changes required.

---

## CLI Interface (`narrator.py`)

The CLI is the primary interface for all users.

### Commands

```
# Generate narration for a post
python narrator.py generate posts/my-essay.md

# Generate with options overriding config.yaml
python narrator.py generate posts/my-essay.md --voice af_bella --format m4a --speed 0.95

# List available voices for the configured provider
python narrator.py voices

# Validate setup (checks ffmpeg, TTS model, config)
python narrator.py check
```

### Flags for `generate`

| Flag | Default | Description |
|------|---------|-------------|
| `--voice` | config value | Voice ID to use |
| `--format` | config value | Output format: `mp3`, `m4a`, `wav` |
| `--speed` | `1.0` | Speech speed multiplier |
| `--no-intro` | off | Skip intro even if file exists |
| `--no-outro` | off | Skip outro even if file exists |
| `--raw-only` | off | Stop after synthesis, skip mixing and encoding |
| `--force` | off | Ignore existing segments and output; regenerate from scratch |

### Structured Output

On success, the CLI prints a JSON object to stdout and exits with code `0`:

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

On failure, exits with code `1` and prints:

```json
{
  "status": "error",
  "message": "ffmpeg not found. Install from https://ffmpeg.org/download.html"
}
```

Progress is printed to stderr (not stdout) so it does not interfere with structured output parsing.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `kokoro-onnx` | TTS synthesis engine |
| `pydub` | Audio segment manipulation, format conversion |
| `audioop-lts` | `pydub` compatibility shim for Python 3.13+ (`audioop` removed from stdlib) |
| `ffmpeg` (system) | Audio codec backend for pydub |
| `pyyaml` | Config file parsing |
| `click` | CLI framework |
| `numpy` | Audio sample conversion in Kokoro provider |

Install with: `pip install -r requirements.txt`

`ffmpeg` must be installed separately (see `wiki/getting-started.md`).

> **Note:** Markdown preprocessing uses Python's built-in `re` module (pure regex). No external markdown parsing library is required.

---

## Implementation Phases

### Phase 1 — Core Pipeline (MVP) ✓
- [x] `preprocessor.py`: strip frontmatter, URLs, markdown syntax, split to paragraphs
- [x] `tts/base.py`: abstract provider interface
- [x] `tts/kokoro_provider.py`: Kokoro-82M implementation
- [x] `synthesizer.py`: paragraph synthesis + per-segment caching + manifest + silence insertion
- [x] `encoder.py`: WAV → MP3 export
- [x] `narrator.py`: `generate` and `check` commands
- [x] `narrator.py`: `setup` command to download Kokoro model files; `--multilingual` flag for v1.0 model
- [x] Stage-level checkpointing: skip completed stages on re-run; `--force` to override
- [x] Progress output to stderr: `[N/Total] Synthesizing paragraph N...`
- [x] `config.yaml` with documented defaults
- [x] `requirements.txt`
- [x] `LICENSE` (MIT)

### Phase 2 — Mixing & Multi-Format ✓
- [x] `mixer.py`: intro/outro loading, RMS loudness matching, concatenation
- [x] Multi-format output (M4A, WAV) via `--format` flag
- [x] Intro/outro filename matching logic (post-specific → default fallback)
- [x] `volume_db` config option: dB gain applied to final output before encoding

### Phase 3 — Polish & Agent Compatibility ✓
- [x] `voices` command listing all available voices
- [x] Structured JSON stdout + stderr progress separation
- [x] `validate.py`: pre-flight checks for config, ffmpeg, post file, voice format, speed range
- [x] Input validation with clear user-facing error messages
- [x] `wiki/getting-started.md`, `configuration.md`, `voices.md`, `architechture.md`

---

## Future Updates
- [x] Lightweight UI — `narrator_ui.py` (Gradio); see `wiki/features/app-lightweight-ui.md`
- [x] GitHub Pages demo site with embedded audio players for voice samples — `docs/`
- [ ] MCP server wrapper exposing `generate_narration` as a tool
- [ ] Additional TTS providers (Coqui XTTS v2 for voice cloning, Piper for multilingual)
- [ ] SSML prosody experiments for bold/italic emphasis
- [ ] Batch processing: `narrator.py generate posts/*.md`

### Lightweight UI (Gradio)

The CLI is the primary interface and keeps the app scriptable and agent-friendly. A UI is worth adding once the core pipeline is stable, primarily to make voice browsing and selection accessible to less technical users.

**Recommended tool:** [Gradio](https://www.gradio.app/) — a Python library that renders a local browser UI with ~30 lines of code. No frontend work or separate server required. It sits directly on top of the existing pipeline.

**Proposed UI surface:**
- File upload for the post (`.md`)
- Dropdown for voice selection (populated from `TTSProvider.list_voices()`)
- Sliders for speed and paragraph pause duration
- In-browser audio playback of the result before downloading
- Download button for the final file

This is a half-day task after the core pipeline is complete. Flask/FastAPI + HTML is an alternative if more UI control is needed later.


