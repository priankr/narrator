import io
import json
import sys
from pathlib import Path

from pydub import AudioSegment

from tts.base import TTSProvider


def synthesize(
    paragraphs: list[str],
    post_name: str,
    provider: TTSProvider,
    voice: str,
    speed: float,
    pause_ms: int,
    raw_dir: Path,
    force: bool = False,
    emit_progress: bool = False,
    cache_segments: bool = False,
) -> Path:
    """
    Synthesize each paragraph to WAV then assemble the full body WAV.

    When cache_segments=False (default): holds audio in memory; no segment
    files or manifest.json are written. Faster and cleaner for one-shot runs.

    When cache_segments=True: writes segment-*.wav and manifest.json to disk
    after each paragraph, enabling resume-on-failure via the status command.

    Returns the path to the assembled body WAV.
    """
    work_dir = Path(raw_dir) / post_name
    work_dir.mkdir(parents=True, exist_ok=True)

    body_path = work_dir / f"{post_name}-body.wav"
    total = len(paragraphs)

    if cache_segments:
        manifest_path = work_dir / "manifest.json"
        if force:
            _clear_work_dir(work_dir, manifest_path, body_path)
        manifest = _load_or_create_manifest(manifest_path, post_name, voice, speed, paragraphs)
        completed = set(manifest["completed"])

        for i, para in enumerate(paragraphs, start=1):
            if i in completed:
                print(f"[{i}/{total}] Paragraph {i} already synthesized, skipping.", file=sys.stderr)
                continue
            if not para.strip():
                continue
            print(f"[{i}/{total}] Synthesizing paragraph {i}...", file=sys.stderr)
            wav_bytes = provider.synthesize(para, voice, speed)
            segment_path = work_dir / f"segment-{i:03d}.wav"
            segment_path.write_bytes(wav_bytes)
            manifest["completed"].append(i)
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            if emit_progress:
                print(json.dumps({"event": "segment_done", "segment": i, "total": total, "voice": voice, "speed": speed}), flush=True)

        print("Assembling body audio...", file=sys.stderr)
        body_path = _assemble_from_disk(work_dir, total, pause_ms, body_path)
    else:
        segments: list[bytes] = []
        for i, para in enumerate(paragraphs, start=1):
            if not para.strip():
                continue
            print(f"[{i}/{total}] Synthesizing paragraph {i}...", file=sys.stderr)
            wav_bytes = provider.synthesize(para, voice, speed)
            segments.append(wav_bytes)
            if emit_progress:
                print(json.dumps({"event": "segment_done", "segment": i, "total": total, "voice": voice, "speed": speed}), flush=True)

        print("Assembling body audio...", file=sys.stderr)
        body_path = _assemble_from_memory(segments, pause_ms, body_path)

    print(f"Body assembled: {body_path}", file=sys.stderr)
    return body_path


def _assemble_from_memory(segments: list[bytes], pause_ms: int, body_path: Path) -> Path:
    if not segments:
        raise RuntimeError("No audio segments to assemble.")
    silence = AudioSegment.silent(duration=pause_ms)
    combined = None
    for wav_bytes in segments:
        seg = AudioSegment.from_wav(io.BytesIO(wav_bytes))
        combined = seg if combined is None else combined + silence + seg
    combined.export(str(body_path), format="wav")
    return body_path


def _assemble_from_disk(work_dir: Path, total: int, pause_ms: int, body_path: Path) -> Path:
    silence = AudioSegment.silent(duration=pause_ms)
    combined = None
    for i in range(1, total + 1):
        seg_path = work_dir / f"segment-{i:03d}.wav"
        if not seg_path.exists():
            continue
        seg = AudioSegment.from_wav(str(seg_path))
        combined = seg if combined is None else combined + silence + seg
    if combined is None:
        raise RuntimeError("No audio segments found to assemble.")
    combined.export(str(body_path), format="wav")
    return body_path


def _load_or_create_manifest(
    manifest_path: Path,
    post_name: str,
    voice: str,
    speed: float,
    paragraphs: list[str],
) -> dict:
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        # Reset if the voice or speed changed since the last run
        if manifest.get("voice") != voice or manifest.get("speed") != speed:
            print(
                "Voice or speed changed since last run — resetting synthesis cache.",
                file=sys.stderr,
            )
            manifest_path.unlink()
            for seg in manifest_path.parent.glob("segment-*.wav"):
                seg.unlink()
            return _new_manifest(post_name, voice, speed, paragraphs)
        return manifest
    return _new_manifest(post_name, voice, speed, paragraphs)


def _new_manifest(post_name: str, voice: str, speed: float, paragraphs: list[str]) -> dict:
    return {
        "post": f"posts/{post_name}.md",
        "voice": voice,
        "speed": speed,
        "total_paragraphs": len(paragraphs),
        "completed": [],
    }


def _clear_work_dir(work_dir: Path, manifest_path: Path, body_path: Path) -> None:
    if manifest_path.exists():
        manifest_path.unlink()
    for seg in work_dir.glob("segment-*.wav"):
        seg.unlink()
    if body_path.exists():
        body_path.unlink()
