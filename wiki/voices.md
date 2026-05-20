# Voice Reference

Narrator uses [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) as its default TTS engine. This page lists all known English voices and explains how to choose one.

> **Tip:** Once the app is set up, run `python narrator.py voices` to get the full list of voices available in the model files on your machine.

> **Tip:** Audio samples are only available for the 10 v0.19 English voices. For voices without a sample, preview them at [Kokoro-TTS on Hugging Face](https://huggingface.co/spaces/hexgrad/Kokoro-TTS) before committing to one. Because synthesis can take several minutes for long posts, test your chosen voice and speed settings with a short passage first — a few sentences is enough to get a feel for the result.

---

## Naming Convention

Voice IDs follow a two-part prefix before the underscore:

```
af_sarah
│││
││└─ name
│└── gender:  f = female, m = male
└─── accent:  a = American English, b = British English
```

| Prefix | Language | Gender |
|--------|----------|--------|
| `af_`  | American English | Female |
| `am_`  | American English | Male |
| `bf_`  | British English | Female |
| `bm_`  | British English | Male |
| `ef_`  | Spanish | Female |
| `em_`  | Spanish | Male |
| `ff_`  | French | Female |
| `hf_`  | Hindi | Female |
| `hm_`  | Hindi | Male |
| `if_`  | Italian | Female |
| `im_`  | Italian | Male |
| `jf_`  | Japanese | Female |
| `jm_`  | Japanese | Male |
| `pf_`  | Brazilian Portuguese | Female |
| `pm_`  | Brazilian Portuguese | Male |
| `zf_`  | Mandarin Chinese | Female |
| `zm_`  | Mandarin Chinese | Male |

---

## Available Voices

Voices marked with a sample link have audio previews in the `samples/` folder. The **Relative Speaking Speed** column reflects observed pace at `speed: 1.0` relative to `af_sarah`.

> **Model requirement:** Voices with a sample link are available in both the v0.19 and v1.0 models. Voices without a sample link were added in v1.0 and require the multilingual model — run `python narrator.py setup --multilingual` to install it.

### American English (Female)

| Voice ID | Relative Speaking Speed | Notes |
|----------|------------------------|-------|
| `af_alloy` | — | |
| `af_aoede` | — | |
| `af_bella` | Similar pace | Warm, expressive — good for personal essays. [Sample](../samples/sample-audio-bella.mp3) |
| `af_heart` | — | |
| `af_jessica` | — | |
| `af_kore` | — | |
| `af_nicole` | ~45% slower | Soft and calm. [Sample](../samples/sample-audio-nicole.mp3) |
| `af_nova` | — | |
| `af_river` | — | |
| `af_sarah` | Default | **Default.** Balanced, natural narration voice. [Sample](../samples/sample-audio-sarah.mp3) |
| `af_sky` | Similar pace | Light and expressive. [Sample](../samples/sample-audio-sky.mp3) |

### American English (Male)

| Voice ID | Relative Speaking Speed | Notes |
|----------|------------------------|-------|
| `am_adam` | Similar pace | Deep and authoritative. [Sample](../samples/sample-audio-adam.mp3) |
| `am_echo` | — | |
| `am_eric` | — | |
| `am_fenrir` | — | |
| `am_liam` | — | |
| `am_michael` | ~10% slower | Warm, broadcast-style voice. [Sample](../samples/sample-audio-michael.mp3) |
| `am_onyx` | — | |
| `am_puck` | — | |
| `am_santa` | — | |

### British English (Female)

| Voice ID | Relative Speaking Speed | Notes |
|----------|------------------------|-------|
| `bf_alice` | — | |
| `bf_emma` | Similar pace | Natural and expressive. [Sample](../samples/sample-audio-emma.mp3) |
| `bf_isabella` | Similar pace | Measured, formal tone. [Sample](../samples/sample-audio-isabella.mp3) |
| `bf_lily` | — | |

### British English (Male)

| Voice ID | Relative Speaking Speed | Notes |
|----------|------------------------|-------|
| `bm_daniel` | — | |
| `bm_fable` | — | |
| `bm_george` | ~5% slower | Warm, natural delivery. [Sample](../samples/sample-audio-george.mp3) |
| `bm_lewis` | ~5% slower | Clear and articulate. [Sample](../samples/sample-audio-lewis.mp3) |

---

## Additional Languages

Kokoro-82M v1.0 includes voices for 7 additional languages beyond English. These require the v1.0 model (`setup --multilingual`) — they are not available in v0.19.

| Language | Voice IDs |
|----------|-----------|
| Spanish | `ef_dora`, `em_alex`, `em_santa` |
| French | `ff_siwis` |
| Hindi | `hf_alpha`, `hf_beta`, `hm_omega`, `hm_psi` |
| Italian | `if_sara`, `im_nicola` |
| Japanese | `jf_alpha`, `jf_gongitsune`, `jf_nezumi`, `jf_tebukuro`, `jm_kumo` |
| Brazilian Portuguese | `pf_dora`, `pm_alex`, `pm_santa` |
| Mandarin Chinese | `zf_xiaobei`, `zf_xiaoni`, `zf_xiaoxiao`, `zf_xiaoyi`, `zm_yunjian`, `zm_yunxi`, `zm_yunxia`, `zm_yunyang` |

The voice ID prefix pattern is the same as English: first character = language/accent, second character = gender (`f` = female, `m` = male).

---

## How to Set a Voice

**In `config.yaml` (persistent):**
```yaml
tts:
  voice: af_bella
```

**Per-run via CLI flag:**
```bash
python narrator.py generate posts/my-essay.md --voice am_michael
```

**Preview the full list on your machine:**
```bash
python narrator.py voices
```
