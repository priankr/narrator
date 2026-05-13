/**
 * narrator.js — GitHub Pages logic for Narrator App.
 *
 * Handles:
 *   - Documentation card rendering and inline markdown fetch/render
 *   - Voice sample gallery rendering and filter chip logic
 *
 * SETUP: Update REPO_OWNER and REPO_NAME below to match your GitHub repository.
 */

// ── Configuration ─────────────────────────────────────────────────────────
const REPO_OWNER = 'priankr';
const REPO_NAME  = 'narrator';
const REPO_BRANCH = 'main';

const RAW_BASE = `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}`;
const GITHUB_BASE = `https://github.com/${REPO_OWNER}/${REPO_NAME}`;

// ── Documentation ─────────────────────────────────────────────────────────
const DOCS = [
  {
    title: 'Getting Started',
    file:  'wiki/getting-started.md',
    icon:  '→',
    desc:  'Install the app, download the TTS model, and generate your first audio file.',
  },
  {
    title: 'Configuration',
    file:  'wiki/configuration.md',
    icon:  '⚙',
    desc:  'All config.yaml settings — voices, speed, formats, paths, and audio options.',
  },
  {
    title: 'Voices',
    file:  'wiki/voices.md',
    icon:  '◎',
    desc:  'Browse all available English voices with name, accent, and gender descriptions.',
  },
  {
    title: 'Architecture',
    file:  'wiki/architechture.md',
    icon:  '◫',
    desc:  'How the four-stage pipeline works — preprocessing, synthesis, mixing, and encoding.',
  },
];

// ── Voice samples ──────────────────────────────────────────────────────────
const VOICES = [
  { id: 'af_sarah',    name: 'Sarah',    accent: 'American English', gender: 'female' },
  { id: 'af_bella',    name: 'Bella',    accent: 'American English', gender: 'female' },
  { id: 'af_nicole',   name: 'Nicole',   accent: 'American English', gender: 'female' },
  { id: 'af_sky',      name: 'Sky',      accent: 'American English', gender: 'female' },
  { id: 'am_michael',  name: 'Michael',  accent: 'American English', gender: 'male'   },
  { id: 'am_adam',     name: 'Adam',     accent: 'American English', gender: 'male'   },
  { id: 'bf_emma',     name: 'Emma',     accent: 'British English',  gender: 'female' },
  { id: 'bf_isabella', name: 'Isabella', accent: 'British English',  gender: 'female' },
  { id: 'bm_lewis',    name: 'Lewis',    accent: 'British English',  gender: 'male'   },
  { id: 'bm_george',   name: 'George',   accent: 'British English',  gender: 'male'   },
];

const SAMPLE_TEXT = 'The quick brown fox jumps over the lazy dog. She sells sea shells by the sea shore.';

// Filter definitions (label → match function)
const FILTERS = [
  { label: 'All',              match: () => true },
  { label: 'Female',           match: v => v.gender === 'female' },
  { label: 'Male',             match: v => v.gender === 'male'   },
  { label: 'American English', match: v => v.accent === 'American English' },
  { label: 'British English',  match: v => v.accent === 'British English'  },
];

// ── marked.js configuration ────────────────────────────────────────────────
function configureMarked() {
  if (typeof marked === 'undefined') return;

  function escHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // marked v9 uses string-based renderer API
  const renderer = new marked.Renderer();
  renderer.code = function(code, lang) {
    const safeCode = typeof code === 'object' ? (code.text || '') : code;
    return `<pre class="terminal-block"><code>${escHtml(safeCode)}</code></pre>`;
  };
  marked.setOptions({ renderer });
}

// ── Docs ──────────────────────────────────────────────────────────────────
function initDocs() {
  const grid  = document.getElementById('doc-grid');
  const panel = document.getElementById('doc-panel');
  const title = document.getElementById('doc-panel-title');
  const link  = document.getElementById('doc-github-link');
  const content = document.getElementById('doc-content');
  const loading = document.getElementById('doc-loading');
  const closeBtn = document.getElementById('doc-close');

  if (!grid) return;

  // Render doc cards
  DOCS.forEach((doc, i) => {
    const card = document.createElement('div');
    card.className = 'capability-card';
    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', '0');
    card.setAttribute('data-index', i);
    card.innerHTML = `
      <span class="card-icon">${doc.icon}</span>
      <span class="card-title">${doc.title}</span>
      <span class="card-desc">${doc.desc}</span>
      <span class="card-cta">Read →</span>
    `;
    card.addEventListener('click', () => openDoc(doc, card));
    card.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') openDoc(doc, card); });
    grid.appendChild(card);
  });

  // Close panel
  closeBtn.addEventListener('click', () => {
    panel.classList.add('hidden');
    document.querySelectorAll('.capability-card.active').forEach(c => c.classList.remove('active'));
  });

  async function openDoc(doc, card) {
    // Toggle: clicking the active card closes the panel
    if (card.classList.contains('active')) {
      panel.classList.add('hidden');
      card.classList.remove('active');
      return;
    }

    // Update active state
    document.querySelectorAll('.capability-card.active').forEach(c => c.classList.remove('active'));
    card.classList.add('active');

    // Show panel with loading state
    title.textContent = doc.file;
    link.href = `${GITHUB_BASE}/blob/${REPO_BRANCH}/${doc.file}`;
    content.innerHTML = '';
    content.appendChild(loading);
    loading.textContent = 'Loading…';
    panel.classList.remove('hidden');

    // Scroll panel into view
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Fetch and render
    try {
      const res = await fetch(`${RAW_BASE}/${doc.file}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const md = await res.text();
      content.innerHTML = marked.parse(md);
    } catch (err) {
      content.innerHTML = `<p style="color:#b30000;font-family:monospace">Could not load ${doc.file}: ${err.message}</p>
        <p>Make sure REPO_OWNER and REPO_NAME are set correctly in docs/js/narrator.js, and that the repository is public.</p>`;
    }
  }
}

// ── Voice gallery ──────────────────────────────────────────────────────────
function initVoiceGallery() {
  const filterRow = document.getElementById('filter-row');
  const grid = document.getElementById('voice-grid');
  if (!grid || !filterRow) return;

  // Render voice cards
  VOICES.forEach(voice => {
    const sampleUrl = `${RAW_BASE}/samples/sample-audio-${voice.name.toLowerCase()}.mp3`;

    const card = document.createElement('div');
    card.className = 'audio-player-card';
    card.dataset.gender = voice.gender;
    card.dataset.accent = voice.accent;
    card.innerHTML = `
      <div class="card-top">
        <span class="voice-tag-chip">${voice.id}</span>
        <span class="voice-accent">${voice.accent}</span>
      </div>
      <p class="card-caption">${SAMPLE_TEXT}</p>
      <audio controls preload="none">
        <source src="${sampleUrl}" type="audio/mpeg" />
        Your browser does not support the audio element.
      </audio>
    `;
    grid.appendChild(card);
  });

  // Render filter chips
  FILTERS.forEach((filter, i) => {
    const chip = document.createElement('button');
    chip.className = 'voice-filter-chip' + (i === 0 ? ' active' : '');
    chip.textContent = filter.label;
    chip.addEventListener('click', () => applyFilter(filter, chip));
    filterRow.appendChild(chip);
  });

  function applyFilter(filter, chip) {
    // Update active chip
    filterRow.querySelectorAll('.voice-filter-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');

    // Show/hide cards
    grid.querySelectorAll('.audio-player-card').forEach((card, i) => {
      const voice = VOICES[i];
      if (filter.match(voice)) {
        card.classList.remove('hidden');
      } else {
        card.classList.add('hidden');
      }
    });
  }
}

// ── GitHub links ───────────────────────────────────────────────────────────
function initGitHubLinks() {
  const ids = ['nav-github', 'hero-github', 'footer-github'];
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.href = GITHUB_BASE;
  });
}

// ── Boot ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  configureMarked();
  initDocs();
  initVoiceGallery();
  initGitHubLinks();
});
