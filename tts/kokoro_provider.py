import io
import wave
from pathlib import Path

import numpy as np

from .base import TTSProvider

MODEL_DIR = Path(__file__).parent.parent / "models"
DEFAULT_MODEL_PATH = MODEL_DIR / "kokoro-v0_19.onnx"
DEFAULT_VOICES_PATH = MODEL_DIR / "voices.bin"
MULTILINGUAL_MODEL_PATH = MODEL_DIR / "kokoro-v1.0.int8.onnx"
MULTILINGUAL_VOICES_PATH = MODEL_DIR / "voices-v1.0.bin"

# Voice prefix → espeak language code used by Kokoro
_LANG_MAP = {
    "af": "en-us",
    "am": "en-us",
    "bf": "en-gb",
    "bm": "en-gb",
    "ef": "es",
    "em": "es",
    "ff": "fr-fr",
    "hf": "hi",
    "hm": "hi",
    "if": "it",
    "im": "it",
    "jf": "ja",
    "jm": "ja",
    "pf": "pt-br",
    "pm": "pt-br",
    "zf": "cmn",
    "zm": "cmn",
}

# Known voices bundled with Kokoro-82M v1.0.
# Run `python narrator.py voices` for the full list from the loaded model.
KNOWN_VOICES = [
    # American English (female)
    "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica",
    "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
    # American English (male)
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
    "am_michael", "am_onyx", "am_puck", "am_santa",
    # British English (female)
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    # British English (male)
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
    # Spanish
    "ef_dora", "em_alex", "em_santa",
    # French
    "ff_siwis",
    # Hindi
    "hf_alpha", "hf_beta", "hm_omega", "hm_psi",
    # Italian
    "if_sara", "im_nicola",
    # Japanese
    "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo",
    # Brazilian Portuguese
    "pf_dora", "pm_alex", "pm_santa",
    # Mandarin Chinese
    "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
    "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang",
]


class KokoroProvider(TTSProvider):
    def __init__(self, model_path: str = None, voices_path: str = None):
        self._model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self._voices_path = Path(voices_path) if voices_path else DEFAULT_VOICES_PATH
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        if not self._model_path.exists():
            raise FileNotFoundError(
                f"Kokoro model not found at '{self._model_path}'.\n"
                "Run 'python narrator.py setup' to download model files."
            )
        if not self._voices_path.exists():
            raise FileNotFoundError(
                f"Kokoro voices file not found at '{self._voices_path}'.\n"
                "Run 'python narrator.py setup' to download model files."
            )
        from kokoro_onnx import Kokoro
        self._model = Kokoro(str(self._model_path), str(self._voices_path))

    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> bytes:
        self._ensure_loaded()
        lang = _voice_lang(voice)
        samples, sample_rate = self._model.create(text, voice=voice, speed=speed, lang=lang)
        return _numpy_to_wav(samples, sample_rate)

    def list_voices(self) -> list[str]:
        try:
            self._ensure_loaded()
            return sorted(self._model.get_voices())
        except Exception:
            return KNOWN_VOICES


def _voice_lang(voice: str) -> str:
    prefix = voice[:2] if len(voice) >= 2 else ""
    return _LANG_MAP.get(prefix, "en-us")


def _numpy_to_wav(samples: np.ndarray, sample_rate: int) -> bytes:
    if samples.dtype != np.int16:
        samples = np.clip(samples, -1.0, 1.0)
        samples = (samples * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())
    return buf.getvalue()
