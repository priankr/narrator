# Lightweight UI Implementation Plan

## Overview

This document covers two non-technical user interfaces for Narrator App. Both share the visual design system defined in `wiki/design.md` — colors, typography, spacing, radius, and component tokens are applied directly.

- **App UI** — a local browser UI that exposes the full narration pipeline without requiring terminal knowledge
- **GitHub Pages** — a static site for documentation navigation and voice sample playback

Neither interface is designed for agents or power users. Simplicity and clarity take priority over feature completeness.

---

## Part 1 — App UI

### Tool

[Gradio](https://www.gradio.app/) is the implementation target. It renders a local browser UI directly on top of the existing Python pipeline with minimal boilerplate and no separate server or frontend build step.

Custom CSS will be applied via Gradio's `css=` parameter to bring the UI as close to the `design.md` token system as possible. Tokens that Gradio cannot expose (complex component shapes, pill buttons) will be overridden via injected CSS classes.

If full design fidelity becomes a requirement later, a Flask + Jinja2 app is a drop-in replacement with no pipeline changes needed.

### File

```
narrator_ui.py    # Gradio app entry point; run with: python narrator_ui.py
```

### Layout

Single-page, single-column layout. Sections stack vertically:

1. **Input** — file upload and optional paste area
2. **Voice configuration** — voice picker, preview, speed, pause
3. **Output options** — format, intro/outro toggles
4. **Synthesis and result** — run button, progress, player, download

### Design Mapping

| UI Element | design.md Token |
|---|---|
| Page background | `colors.canvas` |
| Section cards | `capability-card` |
| Primary run button | `button-primary` |
| Secondary actions (clear, reset) | `button-secondary` |
| Voice ID labels | `voice-tag-chip` + `typography.mono-label` |
| CLI-style status output | `terminal-block` |
| Progress/status text | `typography.caption`, `colors.muted` |
| Audio player card | `audio-player-card` |
| Form inputs | `config-form-card` inputs |
| Error messages | `colors.error` |

### Functional Specification

#### 1. Input

- **File upload** — drag-and-drop or click-to-browse; accepts `.md` files only
- **Paste area** — collapsible text area for users who want to paste Markdown directly rather than upload a file
- Filename is displayed as a `voice-tag-chip`-style label once loaded

#### 2. Voice Configuration

- **Voice dropdown** — populated at startup from `TTSProvider.list_voices()`; grouped by language if the multilingual model is active
- **Preview button** — plays a short pre-rendered sample for the selected voice from `samples/`; falls back to a short live synthesis of a fixed sentence if no sample file exists
- **Speed slider** — range 0.5–2.0, step 0.05, default from `config.yaml`
- **Paragraph pause slider** — range 0–3000ms, step 100ms, default from `config.yaml`

#### 3. Output Options

- **Format selector** — radio group: MP3 (default), M4A, WAV; each option includes a one-line description
- **Skip intro toggle** — shown only if at least one intro file exists in `audio/intro/`
- **Skip outro toggle** — shown only if at least one outro file exists in `audio/outro/`

#### 4. Synthesis and Result

- **Run button** — `button-primary` style; label: "Generate narration"
- **Progress display** — step indicator rendered in a `terminal-block`: "Preprocessing…", "Synthesizing paragraph N of M…", "Mixing…", "Encoding…"; driven by stderr output from the pipeline
- **Audio player** — `audio-player-card` component; shown after synthesis completes; plays the final output file
- **Download button** — `button-primary` style; triggers file download of the output
- **Error display** — shown inline below the run button in `colors.error` if the pipeline exits with a non-zero code; message sourced from the JSON stderr payload

### Wiring to the Pipeline

The UI calls the existing pipeline directly via Python imports — it does not shell out to `narrator.py`. The call path:

```
narrator_ui.py
  → validate.py (pre-flight)
  → pipeline/preprocessor.py
  → pipeline/synthesizer.py   (yields progress events)
  → pipeline/mixer.py
  → pipeline/encoder.py
```

Gradio's `gr.Progress` or a generator-based output component streams synthesis progress to the browser without blocking the UI thread.

### Implementation Phases

- [x] Scaffold `narrator_ui.py` with Gradio layout and design.md CSS variables injected
- [x] Wire file upload and paste area to preprocessor
- [x] Populate voice dropdown from `TTSProvider.list_voices()`; implement preview button
- [x] Add speed, pause, format, and intro/outro controls
- [x] Wire run button to full pipeline; stream progress to terminal-block component
- [x] Render audio player card on completion; wire download button
- [x] Apply `design.md` CSS overrides for fonts, colors, and component shapes
- [ ] Test end-to-end with a real post; verify error states display correctly

---

## Part 2 — GitHub Pages

### Approach

A single `index.html` file served from the `docs/` directory. No build step, no static site generator, no Jekyll theme to override. All styling is a plain CSS file that implements the `design.md` token system directly.

Markdown documents are fetched at runtime from the repository's raw content URLs and rendered client-side using `marked.js`. This means the documentation on the site stays in sync with the source `.md` files automatically — no separate publishing step required.

Voice samples are served as static files from the `samples/` directory, which GitHub Pages exposes directly.

### File Structure

```
docs/
├── index.html          # Single-page shell; navigation and layout
├── css/
│   └── narrator.css    # Full design.md token system as CSS custom properties
└── js/
    └── narrator.js     # Fetch + marked.js rendering; voice gallery; nav logic
```

`marked.js` is loaded from a CDN. No npm, no bundler.

### Page Structure

Single scrolling page with three sections:

#### Section 1 — Hero

- Full-width white canvas
- `hero-display` headline: "Turn your writing into audio."
- `body-large` subheading: one sentence describing what the app does
- Two CTAs side by side: `button-primary` ("Get started" → scrolls to docs section) and `button-secondary` ("View on GitHub" → repo URL)
- `app-preview-card` below the CTAs: a static screenshot of the Gradio UI or a terminal showing a `generate` command and its JSON output

#### Section 2 — Documentation

- `section-heading`: "Documentation"
- Card grid (3-column desktop, 1-column mobile) using `capability-card` tokens; one card per document:

| Card | Source file |
|---|---|
| Getting Started | `wiki/getting-started.md` |
| Configuration | `wiki/configuration.md` |
| Voices | `wiki/voices.md` |
| Architecture | `wiki/architecture.md` |

- Clicking a card opens a full-width reading panel below the grid; the selected `.md` file is fetched and rendered into the panel via `marked.js`
- The panel has a close/collapse control; only one document is open at a time
- Code blocks inside rendered markdown are styled as `terminal-block`

#### Section 3 — Voice Samples

- `dark-feature-band` wrapper (deep green background)
- `section-heading`: "Voice samples"
- `voice-filter-chip` row for filtering by language (English, Japanese, Korean, etc.) — chips populated dynamically from the voice sample filenames
- `audio-player-card` grid (3-column desktop, 1-column mobile); one card per sample file in `samples/`
- Each card contains:
  - `voice-tag-chip`: voice ID + language code (e.g. `af_sarah · EN`)
  - Caption: short fixed sample sentence
  - Native `<audio controls>` element pointing to the sample file
- Filtering hides/shows cards without a network request

#### Footer

- `footer` component: project name, MIT license note, GitHub link
- No newsletter, no external tracking

### Design Implementation

All `design.md` tokens are declared as CSS custom properties in `narrator.css`:

```css
:root {
  --color-primary: #17171c;
  --color-canvas: #ffffff;
  --color-soft-stone: #eeece7;
  --color-deep-green: #003c33;
  --color-coral: #ff7759;
  --color-ink: #212121;
  --color-hairline: #d9d9dd;
  --color-muted: #93939f;
  --color-action-blue: #1863dc;
  --color-error: #b30000;

  --font-display: 'Space Grotesk', Inter, ui-sans-serif, system-ui;
  --font-body: Inter, Arial, ui-sans-serif, system-ui;
  --font-mono: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;

  --radius-sm: 8px;
  --radius-md: 16px;
  --radius-lg: 22px;
  --radius-pill: 32px;
  --radius-full: 9999px;
}
```

Fonts are loaded from Google Fonts (Space Grotesk, Inter, JetBrains Mono). Only weights 400 and 500 are loaded.

### Markdown Rendering

`narrator.js` handles document fetching:

1. On card click, derive the raw GitHub URL from the source file path
2. `fetch()` the `.md` file
3. Pass the response text to `marked.parse()`
4. Inject the resulting HTML into the reading panel
5. Post-process code blocks to apply `terminal-block` styling

The raw content base URL is set as a constant at the top of `narrator.js` so it can be updated if the repo is renamed or forked.

### GitHub Pages Configuration

- Enable GitHub Pages in repo settings; set source to `docs/` on `main`
- No custom domain required for the initial version
- No build action needed — the site is pure static HTML/CSS/JS

> **Before deploying:** open `docs/js/narrator.js` and set `REPO_OWNER` and `REPO_NAME` to match the GitHub repository. These two constants control all raw content URLs used to fetch markdown documents and voice samples. Without them the doc panel and voice gallery will fail to load.

### Implementation Phases

- [ ] Create `docs/` directory; scaffold `index.html`, `narrator.css`, `narrator.js`
- [ ] Implement CSS custom properties from all `design.md` tokens
- [ ] Build Hero section: headline, CTAs, app-preview-card screenshot
- [ ] Build Docs section: capability-card grid + reading panel with marked.js fetch/render
- [ ] Style rendered markdown output (headings, code blocks as terminal-block, tables, lists)
- [ ] Build Voice Samples section: fetch sample filenames, render audio-player-card grid
- [ ] Implement voice-filter-chip language filtering
- [ ] Build footer
- [ ] Test responsive behavior at all breakpoints from `design.md`
- [ ] Enable GitHub Pages in repo settings; verify live deployment
