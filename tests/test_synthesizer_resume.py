import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.synthesizer import (
    _load_or_create_manifest,
    _new_manifest,
    synthesize,
)
from tests.conftest import MockTTSProvider, make_silent_wav


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def test_new_manifest_structure():
    manifest = _new_manifest("my-post", "af_sarah", 1.0, ["p1", "p2", "p3"])
    assert manifest["voice"] == "af_sarah"
    assert manifest["speed"] == 1.0
    assert manifest["total_paragraphs"] == 3
    assert manifest["completed"] == []


def test_load_or_create_creates_when_missing(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest = _load_or_create_manifest(manifest_path, "post", "af_sarah", 1.0, ["p1", "p2"])
    assert manifest["total_paragraphs"] == 2
    assert manifest["completed"] == []


def test_load_or_create_returns_existing(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    existing = _new_manifest("post", "af_sarah", 1.0, ["p1", "p2"])
    existing["completed"] = [1]
    manifest_path.write_text(json.dumps(existing), encoding="utf-8")

    manifest = _load_or_create_manifest(manifest_path, "post", "af_sarah", 1.0, ["p1", "p2"])
    assert manifest["completed"] == [1]


def test_load_or_create_resets_on_voice_change(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    # Write a segment file to verify it gets cleared
    seg = tmp_path / "segment-001.wav"
    seg.write_bytes(b"fake")

    existing = _new_manifest("post", "af_sarah", 1.0, ["p1"])
    existing["completed"] = [1]
    manifest_path.write_text(json.dumps(existing), encoding="utf-8")

    manifest = _load_or_create_manifest(manifest_path, "post", "am_adam", 1.0, ["p1"])
    assert manifest["voice"] == "am_adam"
    assert manifest["completed"] == []
    assert not seg.exists()


def test_load_or_create_resets_on_speed_change(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    existing = _new_manifest("post", "af_sarah", 1.0, ["p1"])
    existing["completed"] = [1]
    manifest_path.write_text(json.dumps(existing), encoding="utf-8")

    manifest = _load_or_create_manifest(manifest_path, "post", "af_sarah", 1.5, ["p1"])
    assert manifest["speed"] == 1.5
    assert manifest["completed"] == []


# ---------------------------------------------------------------------------
# synthesize() — segment skipping and call count
# ---------------------------------------------------------------------------

def test_fresh_run_calls_provider_for_all_paragraphs(tmp_path):
    provider = MockTTSProvider(make_silent_wav())
    paragraphs = ["First.", "Second.", "Third."]

    synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
    )

    assert provider.call_count == 3


def test_rerun_with_complete_manifest_skips_all(tmp_path):
    provider = MockTTSProvider(make_silent_wav())
    paragraphs = ["First.", "Second."]

    # First run — synthesizes everything
    synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        cache_segments=True,
    )
    first_count = provider.call_count

    # Second run — should skip all (manifest complete)
    synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        cache_segments=True,
    )

    assert provider.call_count == first_count  # no new calls


def test_rerun_after_partial_failure_synthesizes_only_missing(tmp_path):
    wav = make_silent_wav()
    provider = MockTTSProvider(wav)
    paragraphs = ["First.", "Second.", "Third."]
    work_dir = tmp_path / "test-post"
    work_dir.mkdir()

    # Simulate partial progress: segments 1 and 2 done, 3 missing
    manifest = _new_manifest("test-post", "af_sarah", 1.0, paragraphs)
    manifest["completed"] = [1, 2]
    (work_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (work_dir / "segment-001.wav").write_bytes(wav)
    (work_dir / "segment-002.wav").write_bytes(wav)

    synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        cache_segments=True,
    )

    assert provider.call_count == 1  # only segment 3


def test_force_clears_cache_and_re_synthesizes_all(tmp_path):
    provider = MockTTSProvider(make_silent_wav())
    paragraphs = ["First.", "Second."]

    # First run
    synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        cache_segments=True,
    )
    first_count = provider.call_count

    # Force re-run
    synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        force=True,
        cache_segments=True,
    )

    assert provider.call_count == first_count * 2


def test_voice_change_clears_cache(tmp_path):
    wav = make_silent_wav()
    paragraphs = ["First.", "Second."]

    provider_a = MockTTSProvider(wav)
    synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider_a,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        cache_segments=True,
    )

    provider_b = MockTTSProvider(wav)
    synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider_b,
        voice="am_adam",  # different voice
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        cache_segments=True,
    )

    assert provider_b.call_count == 2  # full re-synthesis


def test_body_wav_is_created(tmp_path):
    provider = MockTTSProvider(make_silent_wav())
    paragraphs = ["Hello.", "World."]

    body_path = synthesize(
        paragraphs=paragraphs,
        post_name="my-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
    )

    assert body_path.exists()
    assert body_path.suffix == ".wav"
    assert body_path.stat().st_size > 0


def test_emit_progress_prints_events(tmp_path, capsys):
    provider = MockTTSProvider(make_silent_wav())
    paragraphs = ["First.", "Second."]

    synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        emit_progress=True,
    )

    captured = capsys.readouterr()
    events = [json.loads(line) for line in captured.out.strip().splitlines() if line]
    segment_events = [e for e in events if e.get("event") == "segment_done"]
    assert len(segment_events) == 2
    assert segment_events[0]["segment"] == 1
    assert segment_events[0]["total"] == 2
    assert segment_events[1]["segment"] == 2


# ---------------------------------------------------------------------------
# cache_segments=False (default) — in-memory assembly
# ---------------------------------------------------------------------------

def test_default_run_writes_no_segment_files(tmp_path):
    provider = MockTTSProvider(make_silent_wav())
    paragraphs = ["First.", "Second.", "Third."]

    synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
    )

    work_dir = tmp_path / "test-post"
    assert not list(work_dir.glob("segment-*.wav"))


def test_default_run_writes_no_manifest(tmp_path):
    provider = MockTTSProvider(make_silent_wav())
    paragraphs = ["First.", "Second."]

    synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
    )

    assert not (tmp_path / "test-post" / "manifest.json").exists()


def test_default_run_body_wav_exists(tmp_path):
    provider = MockTTSProvider(make_silent_wav())
    paragraphs = ["Hello.", "World."]

    body_path = synthesize(
        paragraphs=paragraphs,
        post_name="my-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
    )

    assert body_path.exists()
    assert body_path.suffix == ".wav"


def test_default_run_body_wav_has_audio(tmp_path):
    provider = MockTTSProvider(make_silent_wav())
    paragraphs = ["Hello.", "World."]

    body_path = synthesize(
        paragraphs=paragraphs,
        post_name="my-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
    )

    assert body_path.stat().st_size > 0


# ---------------------------------------------------------------------------
# Parallel synthesis (cache_segments=False, workers > 1)
# ---------------------------------------------------------------------------

def test_parallel_run_calls_provider_n_times(tmp_path):
    provider = MockTTSProvider(make_silent_wav())
    paragraphs = ["First.", "Second.", "Third.", "Fourth."]

    synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        workers=4,
    )

    assert provider.call_count == 4


def test_parallel_run_skips_empty_paragraphs(tmp_path):
    provider = MockTTSProvider(make_silent_wav())
    paragraphs = ["First.", "", "Third.", "   ", "Fifth."]

    body_path = synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        workers=4,
    )

    assert provider.call_count == 3
    assert body_path.exists()
    assert body_path.stat().st_size > 0


def test_workers_1_matches_default_output_size(tmp_path):
    wav = make_silent_wav()
    paragraphs = ["First.", "Second.", "Third."]

    body_1 = synthesize(
        paragraphs=paragraphs,
        post_name="post-w1",
        provider=MockTTSProvider(wav),
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        workers=1,
    )
    body_4 = synthesize(
        paragraphs=paragraphs,
        post_name="post-w4",
        provider=MockTTSProvider(wav),
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        workers=4,
    )

    assert body_1.stat().st_size == body_4.stat().st_size


def test_parallel_run_body_wav_created(tmp_path):
    provider = MockTTSProvider(make_silent_wav())
    paragraphs = ["Para 1.", "Para 2.", "Para 3.", "Para 4."]

    body_path = synthesize(
        paragraphs=paragraphs,
        post_name="parallel-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        workers=4,
    )

    assert body_path.exists()
    assert body_path.suffix == ".wav"
    assert body_path.stat().st_size > 0


def test_provider_load_lock_prevents_double_init(tmp_path):
    import sys
    import threading
    from unittest.mock import MagicMock, patch
    from tts.kokoro_provider import KokoroProvider

    model_path = tmp_path / "model.onnx"
    voices_path = tmp_path / "voices.bin"
    model_path.write_bytes(b"fake")
    voices_path.write_bytes(b"fake")

    init_calls = []
    mock_model = MagicMock()

    def fake_kokoro(*args, **kwargs):
        init_calls.append(1)
        return mock_model

    mock_module = MagicMock()
    mock_module.Kokoro = fake_kokoro

    provider = KokoroProvider(str(model_path), str(voices_path))
    barrier = threading.Barrier(4)

    def load():
        barrier.wait()
        provider._ensure_loaded()

    with patch.dict(sys.modules, {"kokoro_onnx": mock_module}):
        threads = [threading.Thread(target=load) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert len(init_calls) == 1


def test_cache_segments_writes_segment_files(tmp_path):
    provider = MockTTSProvider(make_silent_wav())
    paragraphs = ["First.", "Second.", "Third."]

    synthesize(
        paragraphs=paragraphs,
        post_name="test-post",
        provider=provider,
        voice="af_sarah",
        speed=1.0,
        pause_ms=0,
        raw_dir=tmp_path,
        cache_segments=True,
    )

    work_dir = tmp_path / "test-post"
    segment_files = list(work_dir.glob("segment-*.wav"))
    assert len(segment_files) == 3
    assert (work_dir / "manifest.json").exists()
