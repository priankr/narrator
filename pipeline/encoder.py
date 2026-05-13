from pathlib import Path

from pydub import AudioSegment

# pydub uses "ipod" as the format name for M4A/AAC
_PYDUB_FORMAT = {
    "mp3": "mp3",
    "m4a": "ipod",
    "wav": "wav",
}

_BITRATE = {
    "mp3": "192k",
    "m4a": "192k",
}

SUPPORTED_FORMATS = list(_PYDUB_FORMAT.keys())


def encode(body_path: Path, output_path: Path, fmt: str, volume_db: float = 0) -> Path:
    """Export body WAV to the target format. Returns the output path."""
    fmt = fmt.lower()
    if fmt not in _PYDUB_FORMAT:
        raise ValueError(
            f"Unsupported format '{fmt}'. Choose from: {', '.join(SUPPORTED_FORMATS)}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio = AudioSegment.from_wav(str(body_path))
    if volume_db != 0:
        audio = audio + volume_db
    kwargs = {}
    if fmt in _BITRATE:
        kwargs["bitrate"] = _BITRATE[fmt]
    audio.export(str(output_path), format=_PYDUB_FORMAT[fmt], **kwargs)
    return output_path
