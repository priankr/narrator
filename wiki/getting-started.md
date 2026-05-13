# Getting Started

This guide walks you through setting up Narrator App and generating your first audio narration.

---

## Step 1 — Install Python

Narrator requires Python 3.10 or higher. Check your version:

```bash
python --version
```

If you need to install or update Python, download it from [python.org](https://www.python.org/downloads/).

> **Python 3.13+ users:** The `audioop` module was removed from the standard library in Python 3.13. The included `requirements.txt` handles this automatically via the `audioop-lts` compatibility package — no extra steps needed.

---

## Step 2 — Install ffmpeg

ffmpeg is required for audio encoding and format conversion.

**Windows:**
```bash
winget install Gyan.FFmpeg
```
Then open a new terminal window for the PATH to update.

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install ffmpeg
```

Verify the install:
```bash
ffmpeg -version
```

---

## Step 3 — Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4 — Download the TTS model

This downloads the Kokoro-82M model files (~82 MB) into the `models/` folder:

```bash
python narrator.py setup
```

> **Need non-English voices?** Pass `--multilingual` to download the Kokoro v1.0 model (~88 MB) instead, which supports Spanish, French, Hindi, Italian, Japanese, Brazilian Portuguese, and Mandarin Chinese. See [configuration.md](configuration.md#multilingual-model) for setup instructions.

---

## Step 5 — Verify your setup

```bash
python narrator.py check
```

Every item should show `[OK]`. If anything shows `[FAIL]`, follow the printed instructions before continuing.

---

## Step 6 — Add your post

Place your Markdown file in the `posts/` folder:

```
posts/
└── my-essay.md
```

Narrator accepts standard Markdown. It automatically strips formatting syntax, URLs, code blocks, and frontmatter before synthesis — only the readable text is narrated.

---

## Step 7 — Generate your first narration

```bash
python narrator.py generate posts/my-essay.md
```

Progress is printed as each paragraph is synthesized:

```
Preprocessing my-essay.md...
Found 12 paragraphs.
[1/12] Synthesizing paragraph 1...
[2/12] Synthesizing paragraph 2...
...
Done: audio/output/my-essay.mp3
```

Your finished audio file is at `audio/output/my-essay.mp3`.

---

## Step 8 — Choose a voice (optional)

The default voice is `af_sarah` (American Female). To use a different voice:

```bash
python narrator.py generate posts/my-essay.md --voice am_michael
```

To see all available voices:

```bash
python narrator.py voices
```

See [voices.md](voices.md) for the full voice list with accent and gender reference.

---

## Step 9 — Add intro and outro audio (optional)

Place audio clips in the `audio/intro/` and `audio/outro/` folders. Supported formats: MP3, WAV, M4A, OGG, FLAC.

**For a clip shared across all posts:**
```
audio/intro/default-intro.mp3
audio/outro/default-outro.mp3
```

**For a clip specific to one post** (e.g. `posts/my-essay.md`):
```
audio/intro/my-essay-intro.mp3
audio/outro/my-essay-outro.mp3
```

Post-specific files take priority over default files. Narrator automatically normalizes the loudness of all three segments before combining them.

---

## Using the UI instead of the CLI

If you prefer not to use the terminal, Narrator App includes a local browser interface. Once setup is complete (steps 1–5 above), run:

```bash
python narrator_ui.py
```

A browser window opens automatically. Here is how to use it:

**1. Add your post**

Use the **Upload file** tab to drag-and-drop or browse for your `.md` file. If you want to try it out without a file, switch to the **Paste text** tab and paste Markdown directly into the text area.

**2. Choose a voice**

Select a voice from the **Voice** dropdown. Click **Preview** to hear a short sample clip for the selected voice before committing. Use the **Speed** slider to speed up or slow down the narration (0.5× to 2.0×), and the **Paragraph pause** slider to control how long the silence between paragraphs is (0–3000 ms).

**3. Set the output format**

Choose **MP3** (default, works everywhere), **M4A** (smaller file, best for Apple devices), or **WAV** (lossless, use if you plan to edit the audio further).

If you have intro or outro audio files set up in `audio/intro/` or `audio/outro/`, checkboxes will appear to skip them for this run.

**4. Generate**

Click **Generate narration**. A progress log appears showing each stage: preprocessing, synthesis (paragraph by paragraph), mixing, and encoding. Synthesis is the slow part — a 2,000-word post takes roughly 3–5 minutes on CPU.

**5. Download the result**

Once complete, an audio player appears so you can listen in the browser. Use the **Download** button below it to save the file to your computer. The file is also saved to `audio/output/` in the project folder.

---

## Next steps

- **Adjust voice, speed, and output format** — see [configuration.md](configuration.md) for all available settings
- **Adjust volume** — set `audio.volume_db` in `config.yaml` (e.g. `3` for louder, `-3` for quieter)
- **Regenerate from scratch** — pass `--force` to clear the synthesis cache and start fresh
- **Interrupted run?** — just re-run the same command; completed paragraphs are automatically skipped
