"""narrator_ui.py — Lightweight browser UI for Narrator App.

Run with: python narrator_ui.py
"""

import html as _html
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import gradio as gr
import yaml

# Run from the project root regardless of where the script is invoked from.
os.chdir(Path(__file__).parent)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_voices() -> list[str]:
    from tts.kokoro_provider import KNOWN_VOICES, DEFAULT_MODEL_PATH
    try:
        if DEFAULT_MODEL_PATH.exists():
            from tts.kokoro_provider import KokoroProvider
            return KokoroProvider().list_voices()
    except Exception:
        pass
    return list(KNOWN_VOICES)


def _sample_path(voice_id: str) -> str | None:
    """Return the sample audio filepath for a voice ID, or None."""
    name = voice_id.split("_")[-1] if "_" in voice_id else voice_id
    p = Path("samples") / f"sample-audio-{name}.mp3"
    return str(p.resolve()) if p.exists() else None


def _has_audio_files(directory: str) -> bool:
    d = Path(directory)
    return d.exists() and any(d.iterdir())


# ---------------------------------------------------------------------------
# Format choices (label → value)
# ---------------------------------------------------------------------------

_FMT_CHOICES = [
    ("MP3 — universal, 192 kbps", "mp3"),
    ("M4A — smaller file, native Apple format", "m4a"),
    ("WAV — lossless, use for further editing", "wav"),
]
_FMT_MAP = dict(_FMT_CHOICES)


# ---------------------------------------------------------------------------
# Progress log rendering
# ---------------------------------------------------------------------------

def _log_html(lines: list[str]) -> str:
    rows = "".join(
        f'<div class="log-line">{_html.escape(ln)}</div>'
        for ln in lines
    )
    return f'<div class="terminal-block">{rows or "&nbsp;"}</div>'


# ---------------------------------------------------------------------------
# Generation (subprocess, streams --progress JSON events)
# ---------------------------------------------------------------------------

def _run_generate(
    upload_file,
    paste_text: str,
    voice: str,
    speed: float,
    pause_ms: float,
    fmt_label: str,
    skip_intro: bool,
    skip_outro: bool,
):
    """
    Generator: yields (log_html, audio_path_or_None, dl_path_or_None).
    Calls narrator.py generate with --progress and parses the JSON event stream.
    """
    fmt = _FMT_MAP.get(fmt_label, "mp3")
    tmp_path = None

    # Resolve post file — prefer uploaded file, fall back to pasted text.
    if upload_file:
        post_path = Path(str(upload_file)).resolve()
    elif paste_text and paste_text.strip():
        tmp = tempfile.NamedTemporaryFile(
            suffix=".md", delete=False, mode="w", encoding="utf-8"
        )
        tmp.write(paste_text)
        tmp.close()
        post_path = Path(tmp.name)
        tmp_path = post_path
    else:
        yield _log_html(["[error]  No input. Upload a .md file or paste your text."]), None, None
        return

    cmd = [
        sys.executable, "narrator.py", "generate", str(post_path),
        "--voice", voice,
        "--format", fmt,
        "--speed", str(speed),
        "--progress",
    ]
    if skip_intro:
        cmd.append("--no-intro")
    if skip_outro:
        cmd.append("--no-outro")

    lines: list[str] = []

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

        for raw in iter(proc.stdout.readline, ""):
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue

            etype = ev.get("event")
            status = ev.get("status")

            if etype == "preprocess_done":
                lines.append(f"[preprocess]   {ev['paragraphs']} paragraphs")
                yield _log_html(lines), None, None

            elif etype == "segment_done":
                seg, total = ev["segment"], ev["total"]
                tag = "[synthesize]"
                lines = [l for l in lines if not l.startswith(tag)]
                lines.append(f"{tag}   paragraph {seg} / {total}")
                yield _log_html(lines), None, None

            elif etype == "synthesis_done":
                tag = "[synthesize]"
                lines = [l for l in lines if not l.startswith(tag)]
                lines.append(f"{tag}   complete")
                yield _log_html(lines), None, None

            elif etype == "mix_done":
                lines.append("[mix]          complete")
                yield _log_html(lines), None, None

            elif etype == "encode_done":
                lines.append("[encode]       complete")
                yield _log_html(lines), None, None

            elif status == "ok" and not ev.get("dry_run"):
                out = ev.get("output_path")
                dur = ev.get("duration_sec", 0)
                m, s = divmod(int(dur), 60)
                lines.append(f"[done]         {m}m {s}s  →  {out}")
                abs_out = str(Path(out).resolve()) if out else None
                yield _log_html(lines), abs_out, abs_out

            elif status == "error":
                lines.append(f"[error]        {ev['message']}")
                yield _log_html(lines), None, None

        proc.wait()

    except Exception as exc:
        lines.append(f"[error]        {exc}")
        yield _log_html(lines), None, None

    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# CSS — design.md tokens applied to Gradio 6.x
# ---------------------------------------------------------------------------

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400&display=swap');

:root {
  --c-primary:  #17171c;
  --c-canvas:   #ffffff;
  --c-stone:    #eeece7;
  --c-ink:      #212121;
  --c-hairline: #d9d9dd;
  --c-muted:    #93939f;
  --c-error:    #b30000;
  --c-coral:    #ff7759;
  --f-display:  'Space Grotesk', Inter, ui-sans-serif, system-ui;
  --f-body:     Inter, Arial, ui-sans-serif, system-ui;
  --f-mono:     'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
  --r-sm:  8px;
  --r-md:  16px;
  --r-pill: 32px;
}

/* ── Container ── */
.gradio-container {
  background: var(--c-canvas) !important;
  font-family: var(--f-body) !important;
  max-width: 780px !important;
  margin: 0 auto !important;
  padding: 2.5rem 1.5rem 4rem !important;
}

/* ── App header ── */
#app-header { margin-bottom: 2.5rem; }
#app-header h1 {
  font-family: var(--f-display);
  font-size: 2.25rem;
  font-weight: 400;
  letter-spacing: -0.05em;
  color: var(--c-primary);
  margin: 0 0 0.3rem;
  line-height: 1;
}
#app-header p {
  font-family: var(--f-body);
  font-size: 1rem;
  color: var(--c-muted);
  margin: 0;
}

/* ── Section mono labels ── */
.section-mono {
  font-family: var(--f-mono);
  font-size: 0.6875rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--c-muted);
  margin: 2rem 0 0.5rem;
  padding: 0;
}

/* ── Terminal / progress block ── */
.terminal-block {
  background: var(--c-primary);
  color: var(--c-stone);
  font-family: var(--f-mono);
  font-size: 0.8125rem;
  line-height: 1.7;
  border-radius: var(--r-sm);
  padding: 1rem 1.25rem;
  min-height: 80px;
  margin-top: 0.75rem;
}
.terminal-block .log-line {
  display: block;
  white-space: pre;
}

/* ── Primary (generate) button ── */
#run-btn button {
  background: var(--c-primary) !important;
  color: #fff !important;
  border-radius: var(--r-pill) !important;
  font-family: var(--f-body) !important;
  font-weight: 500 !important;
  font-size: 0.9rem !important;
  padding: 0.75rem 2rem !important;
  border: none !important;
  width: 100% !important;
  margin-top: 0.5rem;
  transition: opacity 0.15s;
}
#run-btn button:hover { opacity: 0.82; }

/* ── Preview button ── */
#preview-btn button {
  border-color: var(--c-hairline) !important;
  color: var(--c-ink) !important;
  font-family: var(--f-body) !important;
  font-size: 0.875rem !important;
  border-radius: var(--r-sm) !important;
}

/* ── Component labels ── */
label span, .label-wrap span {
  font-family: var(--f-body) !important;
  font-size: 0.875rem !important;
  color: var(--c-ink) !important;
  font-weight: 400 !important;
}

/* ── Inputs, selects, textareas ── */
input[type=text], textarea, select, .wrap {
  font-family: var(--f-body) !important;
  border-color: var(--c-hairline) !important;
  border-radius: var(--r-sm) !important;
}

/* ── Sliders ── */
input[type=range] { accent-color: var(--c-primary) !important; }

/* ── Checkboxes & radios ── */
input[type=checkbox] { accent-color: var(--c-primary) !important; }
input[type=radio]    { accent-color: var(--c-primary) !important; }

/* ── Tabs ── */
.tab-nav button {
  font-family: var(--f-body) !important;
  font-size: 0.875rem !important;
  color: var(--c-muted) !important;
}
.tab-nav button.selected {
  color: var(--c-primary) !important;
  border-bottom-color: var(--c-primary) !important;
}

/* ── Block borders ── */
.block, .gr-block, .form {
  border-color: var(--c-hairline) !important;
  border-radius: var(--r-md) !important;
}

/* ── Audio result card ── */
#audio-result {
  border: 1px solid var(--c-hairline) !important;
  border-radius: var(--r-md) !important;
  padding: 0.75rem !important;
  margin-top: 0.5rem;
}

/* ── File download ── */
#file-out {
  border: 1px solid var(--c-hairline) !important;
  border-radius: var(--r-sm) !important;
  margin-top: 0.5rem;
}
"""


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def build_ui() -> gr.Blocks:
    config = _load_config()
    voices = _get_voices()
    default_voice = config["tts"]["voice"]
    default_speed = float(config["tts"]["speed"])
    default_pause = int(config["audio"]["paragraph_pause_ms"])
    default_fmt_val = config["audio"]["output_format"].lower()

    fmt_labels = [label for label, _ in _FMT_CHOICES]
    default_fmt_label = next(
        (k for k, v in _FMT_MAP.items() if v == default_fmt_val),
        fmt_labels[0],
    )
    voice_val = default_voice if default_voice in voices else (voices[0] if voices else None)
    has_intro = _has_audio_files(config["paths"]["intro"])
    has_outro = _has_audio_files(config["paths"]["outro"])

    # Paths Gradio is allowed to serve (audio output + voice samples).
    allowed = [
        str(Path("audio/output").resolve()),
        str(Path("samples").resolve()),
    ]

    with gr.Blocks(css=CSS, title="Narrator App") as demo:

        # ── Header ──
        gr.HTML("""
            <div id="app-header">
                <h1>Narrator App</h1>
                <p>Convert a Markdown post into narrated audio.</p>
            </div>
        """)

        # ── Input ──
        gr.HTML('<p class="section-mono">Input</p>')
        with gr.Tabs():
            with gr.Tab("Upload file"):
                upload_file = gr.File(
                    label="Markdown file (.md)",
                    file_types=[".md"],
                    type="filepath",
                )
            with gr.Tab("Paste text"):
                paste_text = gr.Textbox(
                    label="Paste Markdown content",
                    lines=8,
                    placeholder="Paste your Markdown here...",
                )

        # ── Voice ──
        gr.HTML('<p class="section-mono">Voice</p>')
        with gr.Row():
            voice_dd = gr.Dropdown(
                choices=voices,
                value=voice_val,
                label="Voice",
                scale=4,
            )
            preview_btn = gr.Button("▶  Preview", scale=1, elem_id="preview-btn")
        preview_audio = gr.Audio(
            label="Voice preview",
            visible=False,
            interactive=False,
        )
        speed_sl = gr.Slider(0.5, 2.0, step=0.05, value=default_speed, label="Speed")
        pause_sl = gr.Slider(0, 3000, step=100, value=default_pause, label="Paragraph pause (ms)")

        # ── Output ──
        gr.HTML('<p class="section-mono">Output</p>')
        fmt_radio = gr.Radio(
            choices=fmt_labels,
            value=default_fmt_label,
            label="Format",
        )
        with gr.Row(visible=(has_intro or has_outro)):
            skip_intro = gr.Checkbox(
                label="Skip intro",
                value=False,
                visible=has_intro,
            )
            skip_outro = gr.Checkbox(
                label="Skip outro",
                value=False,
                visible=has_outro,
            )

        # ── Generate ──
        run_btn = gr.Button("Generate narration", variant="primary", elem_id="run-btn")

        progress_out = gr.HTML(visible=False)
        audio_out = gr.Audio(
            label="Result",
            visible=False,
            interactive=False,
            elem_id="audio-result",
        )
        file_out = gr.File(
            label="Download",
            visible=False,
            interactive=False,
            elem_id="file-out",
        )

        # ── Voice preview wiring ──
        def load_preview(vid: str):
            path = _sample_path(vid)
            return gr.update(value=path, visible=path is not None)

        preview_btn.click(
            fn=load_preview,
            inputs=[voice_dd],
            outputs=[preview_audio],
        )

        # ── Generate wiring ──
        def on_generate(upload, paste, voice, speed, pause, fmt_label, s_intro, s_outro):
            for log_html, audio_path, dl_path in _run_generate(
                upload, paste, voice, speed, pause, fmt_label, s_intro, s_outro
            ):
                yield (
                    gr.update(value=log_html, visible=True),
                    gr.update(value=audio_path, visible=audio_path is not None),
                    gr.update(value=dl_path,    visible=dl_path is not None),
                )

        run_btn.click(
            fn=on_generate,
            inputs=[
                upload_file, paste_text,
                voice_dd, speed_sl, pause_sl,
                fmt_radio, skip_intro, skip_outro,
            ],
            outputs=[progress_out, audio_out, file_out],
        )

    return demo


if __name__ == "__main__":
    build_ui().launch(
        inbrowser=True,
        allowed_paths=[str(Path("audio/output").resolve()), str(Path("samples").resolve())],
    )
