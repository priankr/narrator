# Narrator App

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Kokoro TTS](https://img.shields.io/badge/TTS-Kokoro--82M-FF6B6B?style=flat-square)
![pydub](https://img.shields.io/badge/Audio-pydub-4A90D9?style=flat-square)
![ffmpeg](https://img.shields.io/badge/Backend-ffmpeg-235A25?style=flat-square&logo=ffmpeg&logoColor=white)
![Click](https://img.shields.io/badge/CLI-Click-09B3AF?style=flat-square)
![License: MIT](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)
![Agent Ready](https://img.shields.io/badge/Agent_Use-Optimized-blueviolet?style=flat-square)

Convert written posts into narrated audio files using open-source text-to-speech.

Narrator App is built for writers who want to offer audio versions of their posts — particularly Substack writers — without needing a recording setup or a paid service. Drop in a Markdown file, run one command, get an MP3.

---

## How It Works

1. Place your post as a `.md` file in `posts/`
2. Optionally add intro/outro audio clips to `audio/intro/` and `audio/outro/`
3. Run `python narrator.py generate posts/your-post.md`
4. Find the finished audio in `audio/output/`

Narration is generated locally using [Kokoro-82M](https://github.com/hexgrad/kokoro), a lightweight open-source TTS model that runs on CPU with no GPU required.

---

## Three Ways To Use The App

**1. Terminal (CLI)**
The primary interface. One command, structured JSON output, scriptable and agent-friendly.
```bash
python narrator.py generate posts/your-post.md
```

**2. Browser UI**
Run `python narrator_ui.py` to open a local Gradio interface — voice preview, speed and pause sliders, format picker, and one-click download. No terminal required after setup.

**3. AI Agent**
The CLI is designed for agent invocation: all output is JSON on stdout, progress goes to stderr, exit codes are `0` or `1`. See the [Agent Use](#agent-use) section below.

---

## Quick Start

```bash
pip install -r requirements.txt   # install dependencies
python narrator.py setup           # download Kokoro model (~82 MB)
python narrator.py check           # verify setup
python narrator.py generate posts/your-post.md
```

See [wiki/getting-started.md](wiki/getting-started.md) for a full walkthrough including ffmpeg installation.

---

## Features

- **Paragraph pauses** — configurable silence between paragraphs for natural pacing
- **Speech speed** — adjustable playback speed multiplier (0.5–2.0×)
- **Loudness normalization** — RMS-matches intro and outro to the body audio so volume is consistent across all three segments
- **Intro/outro fades** — fades out the end of the intro and fades in the start of the outro for smooth transitions
- **Volume control** — apply a dB gain adjustment to the final output
- **Quick remix** — swap intro or outro and re-mix in seconds with `remix`, without re-running synthesis
- **Parallel synthesis** — paragraphs are synthesized concurrently (4 threads by default), reducing generation time for long posts by 2–4×; pass `--cache-segments` if you need resume-on-failure instead (that path runs sequentially)
- **Multilingual narration** — optional [Kokoro v1.0 model](wiki/configuration.md#multilingual-model) adds support for Spanish, French, Hindi, Italian, Japanese, Brazilian Portuguese, and Mandarin Chinese

All settings are controlled in `config.yaml`. See [wiki/configuration.md](wiki/configuration.md) for the full reference.

---

## Voice Samples

Sample narrations across all four accent and gender combinations:

| Voice | Accent | Gender | Sample |
|-------|--------|--------|--------|
| `af_bella` | American | Female | [sample-audio-bella.mp3](samples/sample-audio-bella.mp3) |
| `af_nicole` | American | Female | [sample-audio-nicole.mp3](samples/sample-audio-nicole.mp3) |
| `af_sarah` | American | Female | [sample-audio-sarah.mp3](samples/sample-audio-sarah.mp3) |
| `af_sky` | American | Female | [sample-audio-sky.mp3](samples/sample-audio-sky.mp3) |
| `am_adam` | American | Male | [sample-audio-adam.mp3](samples/sample-audio-adam.mp3) |
| `am_michael` | American | Male | [sample-audio-michael.mp3](samples/sample-audio-michael.mp3) |
| `bf_emma` | British | Female | [sample-audio-emma.mp3](samples/sample-audio-emma.mp3) |
| `bf_isabella` | British | Female | [sample-audio-isabella.mp3](samples/sample-audio-isabella.mp3) |
| `bm_george` | British | Male | [sample-audio-george.mp3](samples/sample-audio-george.mp3) |
| `bm_lewis` | British | Male | [sample-audio-lewis.mp3](samples/sample-audio-lewis.mp3) |

Checkout all samples at https://priankr.github.io/narrator/.

These samples cover the 10 v0.19 English voices. For voices without a sample, preview them at [Kokoro-TTS on Hugging Face](https://huggingface.co/spaces/hexgrad/Kokoro-TTS).

---

## Documentation

| File | Description |
|------|-------------|
| [wiki/getting-started.md](wiki/getting-started.md) | Step-by-step setup and first run walkthrough |
| [wiki/configuration.md](wiki/configuration.md) | Full `config.yaml` reference, all CLI flags, intro/outro setup |
| [wiki/voices.md](wiki/voices.md) | Voice list with accent and gender reference |
| [wiki/architechture.md](wiki/architechture.md) | Technical architecture and pipeline design |
| [docs/](docs/) | GitHub Pages site — rendered docs and voice sample gallery |

---

## Agent Use

Narrator App is designed to be invoked by AI agents as part of larger automation workflows. The CLI is machine-readable: all commands print a single JSON line to stdout, all progress goes to stderr, and exit codes are strictly `0` (success/skipped) or `1` (error).

Quick-start for agents:

```bash
python narrator.py check    # verify environment; parse issues[] if exit code 1
python narrator.py voices   # discover available voices before generating
python narrator.py generate posts/my-post.md --dry-run   # validate inputs without synthesizing
python narrator.py generate posts/my-post.md             # run the full pipeline
python narrator.py remix posts/my-post.md                # re-mix with updated intro/outro (skips synthesis)
```

| Reference | Purpose |
|-----------|---------|
| [AGENTS.md](AGENTS.md) | Generic agent quick-start: commands, flags, key rules |
| [CLAUDE.md](CLAUDE.md) | Claude Code-specific conventions for developer agents |
| [wiki/agent-guidelines.md](wiki/agent-guidelines.md) | Full reference: all JSON schemas, error recovery, architecture, coding conventions |

---

## License

MIT — see [LICENSE](LICENSE).
