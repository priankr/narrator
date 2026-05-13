from pathlib import Path
from unittest.mock import patch

import pytest

from validate import (
    check_ffmpeg,
    check_post_file,
    check_speed,
    check_voice_format,
    validate_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_config(**overrides) -> dict:
    config = {
        "tts": {"provider": "kokoro", "voice": "af_sarah", "speed": 1.0},
        "audio": {
            "paragraph_pause_ms": 1000,
            "output_format": "mp3",
            "normalize_loudness": True,
        },
        "paths": {
            "posts": "posts/",
            "intro": "audio/intro/",
            "outro": "audio/outro/",
            "raw_output": "audio/raw/",
            "final_output": "audio/output/",
        },
    }
    config.update(overrides)
    return config


# ---------------------------------------------------------------------------
# validate_config — valid
# ---------------------------------------------------------------------------

def test_valid_config_returns_no_errors():
    assert validate_config(_valid_config()) == []


def test_optional_keys_absent_still_valid():
    config = _valid_config()
    # fade_duration_ms and volume_db are optional
    assert validate_config(config) == []


# ---------------------------------------------------------------------------
# validate_config — missing sections
# ---------------------------------------------------------------------------

def test_missing_tts_section():
    config = _valid_config()
    del config["tts"]
    errors = validate_config(config)
    assert any("tts" in e for e in errors)


def test_missing_audio_section():
    config = _valid_config()
    del config["audio"]
    errors = validate_config(config)
    assert any("audio" in e for e in errors)


def test_missing_paths_section():
    config = _valid_config()
    del config["paths"]
    errors = validate_config(config)
    assert any("paths" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_config — missing required keys
# ---------------------------------------------------------------------------

def test_missing_tts_voice_key():
    config = _valid_config()
    del config["tts"]["voice"]
    errors = validate_config(config)
    assert any("tts.voice" in e for e in errors)


def test_missing_tts_speed_key():
    config = _valid_config()
    del config["tts"]["speed"]
    errors = validate_config(config)
    assert any("tts.speed" in e for e in errors)


def test_missing_audio_output_format():
    config = _valid_config()
    del config["audio"]["output_format"]
    errors = validate_config(config)
    assert any("output_format" in e for e in errors)


def test_missing_paths_raw_output():
    config = _valid_config()
    del config["paths"]["raw_output"]
    errors = validate_config(config)
    assert any("raw_output" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_config — invalid values
# ---------------------------------------------------------------------------

def test_speed_too_low_in_config():
    config = _valid_config()
    config["tts"]["speed"] = 0.4
    errors = validate_config(config)
    assert any("speed" in e for e in errors)


def test_speed_too_high_in_config():
    config = _valid_config()
    config["tts"]["speed"] = 2.1
    errors = validate_config(config)
    assert any("speed" in e for e in errors)


def test_unknown_provider():
    config = _valid_config()
    config["tts"]["provider"] = "unknown_tts"
    errors = validate_config(config)
    assert any("provider" in e for e in errors)


def test_invalid_output_format():
    config = _valid_config()
    config["audio"]["output_format"] = "flac"
    errors = validate_config(config)
    assert any("output_format" in e for e in errors)


def test_negative_paragraph_pause():
    config = _valid_config()
    config["audio"]["paragraph_pause_ms"] = -1
    errors = validate_config(config)
    assert any("paragraph_pause_ms" in e for e in errors)


def test_invalid_fade_duration():
    config = _valid_config()
    config["audio"]["fade_duration_ms"] = -500
    errors = validate_config(config)
    assert any("fade_duration_ms" in e for e in errors)


def test_invalid_volume_db_type():
    config = _valid_config()
    config["audio"]["volume_db"] = "loud"
    errors = validate_config(config)
    assert any("volume_db" in e for e in errors)


# ---------------------------------------------------------------------------
# check_ffmpeg
# ---------------------------------------------------------------------------

def test_check_ffmpeg_not_found():
    with patch("validate.shutil.which", return_value=None):
        result = check_ffmpeg()
    assert result is not None
    assert "ffmpeg" in result.lower()


def test_check_ffmpeg_found():
    with patch("validate.shutil.which", return_value="/usr/bin/ffmpeg"):
        result = check_ffmpeg()
    assert result is None


# ---------------------------------------------------------------------------
# check_post_file
# ---------------------------------------------------------------------------

def test_check_post_file_valid_md(tmp_path):
    post = tmp_path / "my-post.md"
    post.write_text("Some content.", encoding="utf-8")
    assert check_post_file(post) == []


def test_check_post_file_wrong_extension(tmp_path):
    post = tmp_path / "my-post.txt"
    post.write_text("Content.", encoding="utf-8")
    issues = check_post_file(post)
    warns = [i for i in issues if i.startswith("WARN:")]
    assert len(warns) == 1


def test_check_post_file_empty_file(tmp_path):
    post = tmp_path / "empty.md"
    post.touch()
    issues = check_post_file(post)
    errors = [i for i in issues if i.startswith("ERROR:")]
    assert len(errors) == 1
    assert "empty" in errors[0].lower()


# ---------------------------------------------------------------------------
# check_voice_format
# ---------------------------------------------------------------------------

def test_valid_kokoro_voice_returns_none():
    assert check_voice_format("af_sarah", "kokoro") is None


def test_valid_kokoro_voice_am_adam():
    assert check_voice_format("am_adam", "kokoro") is None


def test_invalid_kokoro_voice_no_underscore():
    result = check_voice_format("invalid", "kokoro")
    assert result is not None
    assert "narrator.py voices" in result


def test_invalid_kokoro_voice_uppercase():
    result = check_voice_format("AF_Sarah", "kokoro")
    assert result is not None


def test_unknown_provider_returns_none():
    assert check_voice_format("anything", "unknown_provider") is None


# ---------------------------------------------------------------------------
# check_speed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("speed", [0.5, 0.75, 1.0, 1.5, 2.0])
def test_valid_speeds_return_none(speed):
    assert check_speed(speed) is None


@pytest.mark.parametrize("speed", [0.4, 0.0, -1.0, 2.1, 5.0])
def test_invalid_speeds_return_error(speed):
    result = check_speed(speed)
    assert result is not None
    assert str(speed) in result
