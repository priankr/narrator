import sys
from pathlib import Path

from pydub import AudioSegment

_SUPPORTED_EXTENSIONS = [".mp3", ".wav", ".m4a", ".ogg", ".flac"]


def mix(
    body_path: Path,
    post_name: str,
    intro_dir: Path,
    outro_dir: Path,
    normalize: bool,
    fade_duration_ms: int = 2000,
    skip_intro: bool = False,
    skip_outro: bool = False,
    force: bool = False,
) -> Path:
    """
    Combine intro + body + outro into a single WAV.

    If no intro/outro files are found (or both are skipped), returns body_path
    unchanged — no extra file is written in that case.

    Returns the path to the mixed WAV (or body_path if no mixing occurred).
    """
    mixed_path = body_path.parent / f"{post_name}-mixed.wav"

    if mixed_path.exists() and not force:
        print("Mixed audio already exists, skipping mixing.", file=sys.stderr)
        return mixed_path

    intro = None if skip_intro else _find_audio(intro_dir, post_name, "intro")
    outro = None if skip_outro else _find_audio(outro_dir, post_name, "outro")

    if intro is None and outro is None:
        return body_path

    body = AudioSegment.from_wav(str(body_path))

    if normalize:
        # RMS-match intro and outro to the body's loudness level so perceived
        # volume is consistent across all three segments.
        body_rms = body.rms
        if intro is not None:
            intro = _match_rms(intro, body_rms)
        if outro is not None:
            outro = _match_rms(outro, body_rms)

    if fade_duration_ms > 0:
        if intro is not None:
            intro = intro.fade_out(min(fade_duration_ms, len(intro)))
        if outro is not None:
            outro = outro.fade_in(min(fade_duration_ms, len(outro)))

    combined = body
    if intro is not None:
        print("Adding intro...", file=sys.stderr)
        combined = intro + body
    if outro is not None:
        print("Adding outro...", file=sys.stderr)
        combined = combined + outro

    combined.export(str(mixed_path), format="wav")
    print(f"Mixed audio saved: {mixed_path}", file=sys.stderr)
    return mixed_path


def _match_rms(segment: AudioSegment, target_rms: float) -> AudioSegment:
    """Adjust segment gain so its RMS matches target_rms."""
    if segment.rms == 0:
        return segment
    gain_db = 20 * _log10(target_rms / segment.rms)
    return segment + gain_db


def _log10(x: float) -> float:
    import math
    return math.log10(x)


def _find_audio(directory: Path, post_name: str, role: str) -> AudioSegment | None:
    """
    Look for an audio file matching the post or a shared default.

    Search order:
      1. audio/{role}/{post-name}-{role}.*   (post-specific)
      2. audio/{role}/default-{role}.*       (shared fallback)
    """
    directory = Path(directory)
    for stem in [f"{post_name}-{role}", f"default-{role}"]:
        for ext in _SUPPORTED_EXTENSIONS:
            candidate = directory / f"{stem}{ext}"
            if candidate.exists():
                print(f"Found {role}: {candidate}", file=sys.stderr)
                return AudioSegment.from_file(str(candidate))

    if directory.exists():
        expected = {f"{post_name}-{role}", f"default-{role}"}
        unrecognized = [
            f for f in directory.iterdir()
            if f.suffix.lower() in _SUPPORTED_EXTENSIONS and f.stem not in expected
        ]
        if unrecognized:
            names = ", ".join(f.name for f in unrecognized)
            print(
                f"Warning: {role} files found in {directory}/ but none match the expected "
                f"naming pattern — they will be ignored: {names}\n"
                f"  Expected: '{post_name}-{role}.*' (post-specific) or 'default-{role}.*' (shared fallback).",
                file=sys.stderr,
            )

    return None
