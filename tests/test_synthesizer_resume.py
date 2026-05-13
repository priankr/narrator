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
