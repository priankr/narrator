import re
import shutil
from pathlib import Path

from pipeline.encoder import SUPPORTED_FORMATS

_REQUIRED_CONFIG_SECTIONS = ["tts", "audio", "paths"]
_REQUIRED_TTS_KEYS = ["provider", "voice", "speed"]
_REQUIRED_AUDIO_KEYS = ["paragraph_pause_ms", "output_format", "normalize_loudness"]
_REQUIRED_PATH_KEYS = ["posts", "intro", "outro", "raw_output", "final_output"]

_KNOWN_PROVIDERS = ["kokoro"]

# Kokoro voices follow the pattern: two-letter prefix, underscore, name (e.g. af_sarah)
_KOKORO_VOICE_RE = re.compile(r"^[a-z]{2}_[a-z]+$")


def validate_config(config: dict) -> list[str]:
    """Return a list of error strings. Empty list means config is valid."""
    errors = []

    for section in _REQUIRED_CONFIG_SECTIONS:
        if section not in config:
            errors.append(f"config.yaml is missing required section '{section}'")

    tts = config.get("tts", {})
    for key in _REQUIRED_TTS_KEYS:
        if key not in tts:
            errors.append(f"config.yaml: tts.{key} is required")

    speed = tts.get("speed")
    if speed is not None and not (0.5 <= float(speed) <= 2.0):
        errors.append(
            f"config.yaml: tts.speed must be between 0.5 and 2.0 (got {speed!r})"
        )

    provider = tts.get("provider", "")
    if provider and provider not in _KNOWN_PROVIDERS:
        errors.append(
            f"config.yaml: tts.provider '{provider}' is not recognised. "
            f"Known providers: {', '.join(_KNOWN_PROVIDERS)}"
        )

    audio = config.get("audio", {})
    for key in _REQUIRED_AUDIO_KEYS:
        if key not in audio:
            errors.append(f"config.yaml: audio.{key} is required")

    pause = audio.get("paragraph_pause_ms")
    if pause is not None and (not isinstance(pause, int) or pause < 0):
        errors.append(
            f"config.yaml: audio.paragraph_pause_ms must be a non-negative integer "
            f"(got {pause!r})"
        )

    fmt = audio.get("output_format", "")
    if fmt and fmt not in SUPPORTED_FORMATS:
        errors.append(
            f"config.yaml: audio.output_format '{fmt}' is not supported. "
            f"Choose from: {', '.join(SUPPORTED_FORMATS)}"
        )

    fade_ms = audio.get("fade_duration_ms")
    if fade_ms is not None and (not isinstance(fade_ms, int) or fade_ms < 0):
        errors.append(
            f"config.yaml: audio.fade_duration_ms must be a non-negative integer in milliseconds "
            f"(got {fade_ms!r})"
        )

    volume_db = audio.get("volume_db")
    if volume_db is not None and not isinstance(volume_db, (int, float)):
        errors.append(
            f"config.yaml: audio.volume_db must be a number in decibels (got {volume_db!r})"
        )

    paths = config.get("paths", {})
    for key in _REQUIRED_PATH_KEYS:
        if key not in paths:
            errors.append(f"config.yaml: paths.{key} is required")

    return errors


def check_ffmpeg() -> str | None:
    """Return an error string if ffmpeg is not on PATH, else None."""
    if shutil.which("ffmpeg") is None:
        return (
            "ffmpeg is not installed or not on PATH.\n"
            "Install it from https://ffmpeg.org/download.html, then re-run."
        )
    return None


def check_post_file(post_path: Path) -> list[str]:
    """
    Return validation issues for the post file.
    Errors (blocking) are prefixed with ERROR:, warnings with WARN:.
    """
    issues = []
    if post_path.suffix.lower() != ".md":
        issues.append(
            f"WARN: '{post_path.name}' does not have a .md extension. "
            "Narrator expects Markdown — other formats may not preprocess correctly."
        )
    try:
        if post_path.stat().st_size == 0:
            issues.append(f"ERROR: '{post_path.name}' is empty.")
    except OSError as exc:
        issues.append(f"ERROR: Cannot read '{post_path}': {exc}")
    return issues


def check_voice_format(voice: str, provider: str) -> str | None:
    """Return a hint string if the voice ID looks wrong for the provider, else None."""
    if provider == "kokoro" and not _KOKORO_VOICE_RE.match(voice):
        return (
            f"Voice '{voice}' does not match the expected Kokoro format "
            "(e.g. 'af_sarah', 'am_adam', 'bf_emma'). "
            "Run 'python narrator.py voices' for the full list."
        )
    return None


def check_speed(speed: float) -> str | None:
    """Return an error string if speed is out of range, else None."""
    if not (0.5 <= speed <= 2.0):
        return f"Speed {speed} is out of the valid range (0.5–2.0)."
    return None
