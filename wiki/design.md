---
name: narrator-design-system
description: Core UI components are stark white editorial space, deep green-black product bands, soft mineral surfaces, rounded media cards, and a distinctive type split between Space Grotesk display headlines and precise Inter UI text.

colors:
  primary: "#17171c"
  brand-black: "#000000"
  ink: "#212121"
  deep-green: "#003c33"
  dark-navy: "#071829"
  canvas: "#ffffff"
  soft-stone: "#eeece7"
  pale-green: "#edfce9"
  pale-blue: "#f1f5ff"
  hairline: "#d9d9dd"
  border-light: "#e5e7eb"
  card-border: "#f2f2f2"
  muted: "#93939f"
  slate: "#75758a"
  body-muted: "#616161"
  action-blue: "#1863dc"
  focus-blue: "#4c6ee6"
  coral: "#ff7759"
  coral-soft: "#ffad9b"
  form-focus: "#9b60aa"
  on-primary: "#ffffff"
  on-dark: "#ffffff"
  error: "#b30000"

typography:
  hero-display:
    fontFamily: Space Grotesk
    fontSize: 96px
    fontWeight: 400
    lineHeight: 1
    letterSpacing: -1.92px
  product-display:
    fontFamily: Space Grotesk
    fontSize: 72px
    fontWeight: 400
    lineHeight: 1
    letterSpacing: -1.44px
  section-display:
    fontFamily: Inter
    fontSize: 60px
    fontWeight: 400
    lineHeight: 1
    letterSpacing: -1.2px
  section-heading:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: 400
    lineHeight: 1.2
    letterSpacing: -0.48px
  card-heading:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: 400
    lineHeight: 1.2
    letterSpacing: -0.32px
  feature-heading:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: 400
    lineHeight: 1.3
    letterSpacing: 0
  body-large:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0
  body:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0
  button:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.71
    letterSpacing: 0
  caption:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0
  mono-label:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0.28px
  micro:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0

rounded:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 22px
  xl: 30px
  pill: 32px
  full: 9999px

spacing:
  xxs: 2px
  xs: 6px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  xxl: 32px
  section: 80px

components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button}"
    rounded: "{rounded.pill}"
    padding: 12px 24px
  button-secondary:
    backgroundColor: transparent
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.xs}"
    padding: 8px 0
  button-pill-outline:
    backgroundColor: transparent
    textColor: "{colors.primary}"
    typography: "{typography.button}"
    rounded: "{rounded.xl}"
    padding: 6px 12px
  announcement-bar:
    backgroundColor: "{colors.brand-black}"
    textColor: "{colors.on-dark}"
    typography: "{typography.micro}"
    height: 36px
  hero-photo-card:
    backgroundColor: "{colors.canvas}"
    rounded: "{rounded.lg}"
  app-preview-card:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-dark}"
    rounded: "{rounded.sm}"
    padding: 24px
  audio-player-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: 24px
    border: "1px solid {colors.hairline}"
  terminal-block:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.soft-stone}"
    typography: "{typography.mono-label}"
    rounded: "{rounded.sm}"
    padding: 16px 20px
  voice-tag-chip:
    backgroundColor: "{colors.soft-stone}"
    textColor: "{colors.ink}"
    typography: "{typography.mono-label}"
    rounded: "{rounded.full}"
    padding: 4px 10px
  capability-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.xs}"
    padding: 24px
  dark-feature-band:
    backgroundColor: "{colors.deep-green}"
    textColor: "{colors.on-dark}"
    rounded: "{rounded.lg}"
    padding: 80px
  product-card:
    backgroundColor: "{colors.soft-stone}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: 32px
  voice-filter-chip:
    backgroundColor: transparent
    textColor: "{colors.coral}"
    typography: "{typography.card-heading}"
    rounded: "{rounded.sm}"
    padding: 8px 14px
  voice-sample-table:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-large}"
  config-form-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: 32px
  footer:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-dark}"
    typography: "{typography.micro}"
---
# Narrator App Design System

## Overview

Narrator App's visual identity is a minimal developer tool that takes its editorial cues from clean technical publishing rather than enterprise marketing. The GitHub Pages site opens on a sharp typographic declaration over a white canvas, then uses CLI screenshots, audio player cards, and generous whitespace to make a local narration tool feel precise and trustworthy.

What makes the system work is the contrast between the austere white/stone editorial shell and the dark product surfaces: deep green pipeline-step bands, near-black terminal blocks, and soft stone voice cards. Color arrives through functional accent chips (coral voice taxonomy, blue action links, mono voice-ID labels) rather than decoration.

**Key Characteristics:**
- Monumental display headlines with very tight line height and negative tracking.
- White editorial canvases interrupted by deep green pipeline bands and near-black terminal blocks.
- Rounded media cards at 8px to 22px; terminal blocks and code surfaces at 8px.
- Pill CTAs in near-black on light surfaces; secondary actions as underlined text links.
- Voice sample tables with rule-separated rows, mono voice-ID labels, and embedded audio players.
- Audio player cards combining a voice name chip, sample text caption, and a native `<audio>` control.

## Colors

### Brand & Accent

- **Brand Black** (`#000000`): Announcement bar (optional new-release banners), highest-contrast text.
- **Near-Black Primary** (`#17171c`): Primary CTA buttons, dark footer, terminal blocks, and app-preview cards.
- **Deep Enterprise Green** (`#003c33`): Pipeline and "How it works" dark section bands.
- **Dark Navy** (`#071829`): Secondary dark surfaces where a cooler tone is needed.
- **Action Blue** (`#1863dc`): Documentation links, pagination, and secondary action emphasis.
- **Coral** (`#ff7759`): Voice category chips, taxonomy outlines, and warm accent markers.
- **Soft Coral** (`#ffad9b`): Pale chip borders and segmented voice-label details.

### Surface & Background

- **Canvas White** (`#ffffff`): Dominant page background and form/card surface.
- **Soft Stone** (`#eeece7`): Voice cards, voice-tag chips, and warm neutral surface blocks.
- **Pale Green Wash** (`#edfce9`): Section backdrop behind stacked dark capability panels.
- **Pale Blue Wash** (`#f1f5ff`): CTA surface for download and GitHub link sections.
- **Card Border** (`#f2f2f2`): Softest card containment line.

### Text & Rules

- **Ink** (`#212121`): Default body text and most link text on light backgrounds.
- **Muted Slate** (`#93939f`): Footer links, dates, metadata, and de-emphasized labels.
- **Slate** (`#75758a`): Table separators and tertiary text.
- **Hairline** (`#d9d9dd`): Standard list rules and section dividers.
- **Border Light** (`#e5e7eb`): Secondary divider and utility rule.

### Semantic

- **Focus Blue** (`#4c6ee6`): Keyboard focus and ring color.
- **Form Focus Violet** (`#9b60aa`): Focus border for text inputs.
- **Error Red** (`#b30000`): Validation and error states.

### Gradient System

Gradients are not used as generic UI fills. Reserve gradient richness for large media panels and any CTA image bands. Keep UI surfaces flat.

## Typography

### Font Family

- **Display**: `Space Grotesk`, falling back to `Inter`, `ui-sans-serif`, and `system-ui`. Free; available via Google Fonts.
- **Body/UI**: `Inter`, falling back to `Arial`, `ui-sans-serif`, and `system-ui`. Free; available via Google Fonts.
- **Technical labels**: `JetBrains Mono`, falling back to `Fira Code`, `ui-monospace`, and `monospace`. Free; available via Google Fonts. Used for voice IDs, CLI commands, and mono labels.
- **Icons**: Thin-line geometric icons (Lucide or Heroicons recommended — both free and open source).

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|---|---|---:|---:|---:|---:|---|
| Hero Display | Space Grotesk | 96px | 400 | 1.00 | -1.92px | GitHub Pages hero declaration. |
| Product Display | Space Grotesk | 72px | 400 | 1.00 | -1.44px | Section hero headlines. |
| Section Display | Inter | 60px | 400 | 1.00 | -1.2px | Large page headings. |
| Section Heading | Inter | 48px | 400 | 1.20 | -0.48px | Split hero and CTA headings. |
| Card Heading | Inter | 32px | 400 | 1.20 | -0.32px | Feature card and list section titles. |
| Feature Heading | Inter | 24px | 400 | 1.30 | 0 | Cards, filters, and voice table titles. |
| Body Large | Inter | 18px | 400 | 1.40 | 0 | Lead text and larger paragraphs. |
| Body | Inter | 16px | 400 | 1.50 | 0 | Default copy and link text. |
| Button | Inter | 14px | 500 | 1.71 | 0 | Compact CTA labels. |
| Caption | Inter | 14px | 400 | 1.40 | 0 | Metadata and small explanatory text. |
| Mono Label | JetBrains Mono | 14px | 400 | 1.40 | 0.28px | Voice IDs, CLI commands, technical labels. |
| Micro | Inter | 12px | 400 | 1.40 | 0 | Footer, nav microcopy, and small links. |

### Principles

- Use massive type sparingly; pages should have one oversized headline and then settle into restrained 16px-24px UI copy.
- Keep display type tight. Hero copy should feel compact and carved, not airy.
- Avoid heavy bold weights. Size, spacing, and surface contrast do most of the hierarchy work.
- Use JetBrains Mono for voice IDs, CLI invocations, and any system-generated labels.
- Editorial pages can use coral chips and blue links, but the base typography remains black and measured.

## Layout

### Spacing System

The system uses an 8px base with many one-off alignment values: `2px`, `6px`, `8px`, `10px`, `12px`, `16px`, `20px`, `22px`, `24px`, `28px`, `32px`, `36px`, `40px`, `56px`, `60px`, `64px`, and `80px`.

Large sections rely on dramatic vertical breathing room. Pages place voice sample galleries far below the hero. Pipeline and "how it works" sections hold dark panels inside fields of empty white space, then transition to dense voice tables or footers near the end.

### Grid & Container

- Global nav uses a three-zone layout: logo left, menu centered, GitHub/CTA right.
- Hero is centered text above an app-preview card (CLI output or audio player mockup).
- Feature sections use 3-column cards on desktop.
- Voice sample pages use full-width rule-separated tables with voice-ID chips and embedded audio players.
- The Gradio UI (local tool) uses a single-column layout with file upload at top and audio player at bottom.

### Whitespace Philosophy

Whitespace is a quality signal. Large empty intervals separate the headline claim, pipeline explanation, voice samples, and CTA. Dense content appears only where the information architecture requires it: voice tables, config option lists, and CLI reference blocks.

## Elevation & Depth

The system is mostly flat. Depth comes from surface alternation, media contrast, rounded corners, and thin borders rather than drop shadows.

| Level | Treatment | Use |
|---|---|---|
| Flat | No shadow, white or dark field | Hero copy, voice tables, editorial surfaces |
| Bordered | 1px `#d9d9dd`, `#e5e7eb`, or dark translucent rules | Voice tables, forms, pale cards, audio player cards |
| Media Lift | Rounded card over contrasting section color | App-preview cards, audio player cards, terminal blocks |
| Dark Product Field | Deep green or near-black full-width band | Pipeline steps, "How it works" sections |

## Shapes

### Radius Scale

| Token | Value | Role |
|---|---:|---|
| `xs` | 4px | Search fields, utility elements |
| `sm` | 8px | Terminal blocks, voice-tag chips, small cards |
| `md` | 16px | Audio player cards and grouped blocks |
| `lg` | 22px | Signature media-card and placeholder radius |
| `xl` | 30px | Voice filter pills |
| `pill` | 32px | Primary CTA buttons |
| `full` | 9999px | Voice-tag chips and fully pill-shaped controls |

### Image Treatment

Screenshots and mockups are not decorative backdrops for text. They sit as rounded cards with visible corners: CLI terminal screenshots, Gradio UI screenshots, and audio player mockups. The dominant radii are 8px and 22px.

## Components

### **`button-primary`**

Near-black pill CTA. Uses 14px Inter, 12px 24px padding, and a 32px pill radius. Primary action style for "Download", "View on GitHub", and hero CTAs.

### **`button-secondary`**

Text-only action link, usually underlined or rule-aligned, with no filled background. Used for "View docs", "Browse voices", and secondary hero actions.

### **`button-pill-outline`**

Outlined pill control with transparent fill, 1px dark border, and 30px radius. Used for voice language filters, format filters, and lightweight taxonomy controls.

### **`announcement-bar`**

Full-width black strip above the nav, 36px tall, centered microcopy with an underlined link (e.g. "v2.0 released — see what's new") and a close control at the far right. Optional; only shown on active releases.

### **`hero-photo-card`**

Rounded media card used in the hero section. Combines a terminal screenshot or Gradio UI screenshot with an overlaid status chip or voice-ID label. Radius is 22px on large cards and 8px on smaller thumbnails.

### **`app-preview-card`**

Dark near-black mockup panel showing CLI output, synthesis progress indicators, or Gradio UI state. Background is near-black, text is white or muted soft-stone, and small accent chips use voice-tag or status colors.

### **`audio-player-card`**

Rounded white card containing: a `voice-tag-chip` (voice ID + language), a short sample text caption in Inter body, and a native `<audio>` control. Border is 1px `#d9d9dd`. Used on the GitHub Pages voice sample gallery. Radius is 16px.

### **`terminal-block`**

Dark near-black `<pre>` block for displaying CLI commands and structured JSON output. Uses JetBrains Mono 14px, soft-stone text, 8px radius, and 16px 20px padding. This is the primary way to show usage examples on GitHub Pages.

### **`voice-tag-chip`**

Small inline chip on a soft-stone background showing a voice ID and language code in JetBrains Mono (e.g. `af_sarah · EN`). Used inside `audio-player-card`, `voice-sample-table` rows, and inline in documentation copy. Fully pill radius.

### **`capability-card`**

Content block with a thin-line icon, 24px heading, body copy, and a text link. Used in the "Features" section of GitHub Pages. On light backgrounds, cards use only a top rule or a subtle image relationship rather than full boxing.

### **`dark-feature-band`**

Deep green full-width section used for pipeline steps, "How it works" breakdowns, and feature explanations. Text turns white; inner cards use darker translucent surfaces, pale borders, and thin-line icons.

### **`product-card`**

Warm stone card used for summarizing supported voices, output formats, or TTS providers. Typically 3-column on desktop with 8px radius, generous padding, a small pill button, a divider line, and checkmark bullet rows.

### **`voice-filter-chip`**

Large coral taxonomy chip used on the voice sample gallery. Active chips invert to coral fill with dark text; inactive chips use coral outline and pale fill. Typography is oversized relative to typical filters, making the language/accent taxonomy a prominent control.

### **`voice-sample-table`**

Rule-separated voice listing with voice ID left (JetBrains Mono), language/accent chips centered, and an embedded audio player or download link right. Rows are tall, white, and border-driven; filters above use compact outlined pills.

### **`config-form-card`**

Rounded white form panel (used in Gradio theming reference and documentation). Inputs are rectangular with thin gray borders, 12px-16px padding, and compact labels. Submit uses the same near-black pill style as primary CTAs.

### **`footer`**

Dark near-black footer with white section labels (Links, License, About) and muted Inter links. No newsletter signup. Includes GitHub link, MIT license note, and project tagline.

## Do's and Don'ts

### Do

- Use white canvas as the default surface; introduce deep green as full-width pipeline bands.
- Keep primary CTAs pill-shaped and near-black on light surfaces.
- Use 22px radius on major media cards and app-preview placeholders.
- Use coral for voice taxonomy chips and small warm accents, not as the main CTA system.
- Use JetBrains Mono for all voice IDs and CLI command examples.
- Use thin-line geometric icons (Lucide or Heroicons) for feature and capability icons.
- Let terminal screenshots and audio player cards carry visual energy; keep the UI shell restrained.

### Don't

- Do not turn coral or blue into broad decorative surface colors.
- Do not add heavy drop shadows to cards.
- Do not make every section card-based; use unframed rows, rules, and open space for voice tables and documentation.
- Do not use rounded cards below 8px for major media or terminal blocks.
- Do not replace the display/body type split with one generic font voice.
- Do not use saturated gradients as normal UI backgrounds; keep gradients media-led.

## Responsive Behavior

### Breakpoints

| Name | Width | Key Changes |
|---|---:|---|
| Small Mobile | <425px | Single-column cards, compact nav, reduced hero headline scale |
| Mobile | 425-640px | Hero media stacks, card grids become one column, audio players full-width |
| Large Mobile | 640-768px | Wider one-column layouts with larger media cards |
| Tablet | 768-1024px | Two-column voice cards begin, nav spacing tightens |
| Desktop | 1024-1440px | Full nav, 3-column voice cards, split hero compositions |
| Large Desktop | 1440-2560px | Wide containers and large empty vertical intervals |

### Touch Targets

Primary CTAs and pills meet comfortable touch sizing through 12px-24px padding and pill radii. Voice filter chips and language chips are larger than standard tags, making dense taxonomy surfaces usable on touch devices. Audio player controls use the browser's native `<audio>` element, which meets platform touch standards automatically.

### Collapsing Strategy

- Nav collapses from full horizontal links to a compact mobile menu.
- Hero media moves from split cards to stacked cards.
- Voice and capability grids collapse from 3 columns to 2 and then 1.
- Voice sample tables preserve their rule-separated structure but stack the audio player below the voice ID on smaller widths.

## Iteration Guide

1. Start from a white canvas or a full-width deep green band; avoid mid-tone page backgrounds.
2. Use `button-primary` for the single highest-priority action and `button-secondary` for the companion action.
3. Use `app-preview-card` or `audio-player-card` when a section needs visual energy; avoid invented dashboard data.
4. For voice sample pages, combine `voice-filter-chip`, `button-pill-outline`, and `voice-sample-table` instead of generic marketing cards.
5. Use `terminal-block` for every CLI command example — never render shell commands in plain body text.
6. Keep component examples structurally honest: real voice IDs and real CLI flags are better than placeholder content.

## Known Gaps

- Space Grotesk, Inter, and JetBrains Mono are all available on Google Fonts; load only weights 400 and 500 to minimise page weight.
- Inter and JetBrains Mono are both available on Google Fonts — load only the weights in use (400 and 500) to minimize page weight.
- Gradio's theming system does not expose all tokens in this design system; `config-form-card`, `terminal-block`, and color tokens are the most mappable. Custom CSS overrides will be needed for the rest.
- Mobile layout for the voice sample table has not been prototyped; treat the responsive guidance as a starting point.
