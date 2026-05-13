import io
import wave
from pathlib import Path

import pytest
import yaml


def make_silent_wav(duration_ms: int = 100) -> bytes:
    sample_rate = 22050
    num_samples = int(sample_rate * duration_ms / 1000)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)
    return buf.getvalue()


class MockTTSProvider:
    def __init__(self, wav_bytes: bytes = None):
        self._wav = wav_bytes or make_silent_wav()
        self.call_count = 0
        self.calls: list[dict] = []

    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> bytes:
        self.call_count += 1
        self.calls.append({"text": text, "voice": voice, "speed": speed})
        return self._wav

    def list_voices(self) -> list[str]:
        return ["af_sarah", "am_adam"]


# Root of the project (one level above tests/)
PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture
def silent_wav() -> bytes:
    return make_silent_wav()


@pytest.fixture
def mock_provider(silent_wav) -> MockTTSProvider:
    return MockTTSProvider(silent_wav)


@pytest.fixture
def project_dir(tmp_path) -> Path:
    """Minimal project layout in a temp directory. Uses WAV output to avoid ffmpeg."""
    config = {
        "tts": {"provider": "kokoro", "voice": "af_sarah", "speed": 1.0},
        "audio": {
            "paragraph_pause_ms": 0,
            "output_format": "wav",
            "normalize_loudness": False,
            "fade_duration_ms": 0,
            "volume_db": 0,
        },
        "paths": {
            "posts": str(tmp_path / "posts"),
            "intro": str(tmp_path / "audio" / "intro"),
            "outro": str(tmp_path / "audio" / "outro"),
            "raw_output": str(tmp_path / "audio" / "raw"),
            "final_output": str(tmp_path / "audio" / "output"),
        },
    }
    (tmp_path / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    for d in ["posts", "audio/intro", "audio/outro", "audio/raw", "audio/output"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / "posts" / "test-post.md").write_text(
        "Hello world.\n\nSecond paragraph here.", encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def project_root_cwd(monkeypatch) -> Path:
    """Change CWD to the real project root for tests that use the actual config.yaml."""
    monkeypatch.chdir(PROJECT_ROOT)
    return PROJECT_ROOT
