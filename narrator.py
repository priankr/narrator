import json
import re
import shutil
import sys
import urllib.request
from pathlib import Path

import click
import yaml

from pipeline.encoder import SUPPORTED_FORMATS, encode
from pipeline.mixer import mix
from pipeline.preprocessor import preprocess
from pipeline.synthesizer import synthesize
from tts.kokoro_provider import (
    DEFAULT_MODEL_PATH, DEFAULT_VOICES_PATH,
    MULTILINGUAL_MODEL_PATH, MULTILINGUAL_VOICES_PATH,
    KNOWN_VOICES,
)
from validate import check_ffmpeg, check_post_file, check_speed, check_voice_format, validate_config

# Model files are downloaded from the kokoro-onnx GitHub releases.
# If these URLs stop working, check: https://github.com/thewh1teagle/kokoro-onnx/releases
_MODEL_DOWNLOADS = {
    DEFAULT_MODEL_PATH.name: (
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/"
        "model-files/kokoro-v0_19.onnx"
    ),
    DEFAULT_VOICES_PATH.name: (
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/"
        "model-files/voices.bin"
    ),
}

_MULTILINGUAL_DOWNLOADS = {
    MULTILINGUAL_MODEL_PATH.name: (
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/"
        "model-files-v1.0/kokoro-v1.0.int8.onnx"
    ),
    MULTILINGUAL_VOICES_PATH.name: (
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/"
        "model-files-v1.0/voices-v1.0.bin"
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_config(path: str = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_provider(config: dict):
    provider_name = config["tts"]["provider"]
    if provider_name == "kokoro":
        from tts.kokoro_provider import KokoroProvider
        return KokoroProvider(
            model_path=config["tts"].get("model_path"),
            voices_path=config["tts"].get("voices_path"),
        )
    raise ValueError(
        f"Unknown TTS provider: {provider_name!r}. "
        "Supported providers: kokoro"
    )


def _ok(data: dict) -> None:
    print(json.dumps(data))


def _err(message: str) -> None:
    print(json.dumps({"status": "error", "message": message}))
    sys.exit(1)


def _event(data: dict) -> None:
    print(json.dumps(data), flush=True)


# Voices that shipped with the v0.19 English model. Everything else requires v1.0.
_V019_VOICES = {
    "af_bella", "af_nicole", "af_sarah", "af_sky",
    "am_adam", "am_michael",
    "bf_emma", "bf_isabella",
    "bm_george", "bm_lewis",
}


def _voice_requires_model(voice_id: str) -> str:
    return "v0.19" if voice_id in _V019_VOICES else "v1.0"


def _installed_model(config: dict) -> dict:
    """Return active model version (per config) and all versions found on disk."""
    model_path = Path(config["tts"].get("model_path") or DEFAULT_MODEL_PATH)
    voices_path = Path(config["tts"].get("voices_path") or DEFAULT_VOICES_PATH)

    on_disk = []
    if DEFAULT_MODEL_PATH.exists() and DEFAULT_VOICES_PATH.exists():
        on_disk.append("v0.19")
    if MULTILINGUAL_MODEL_PATH.exists() and MULTILINGUAL_VOICES_PATH.exists():
        on_disk.append("v1.0")

    if not model_path.exists() or not voices_path.exists():
        active = None
    elif model_path == MULTILINGUAL_MODEL_PATH or "v1.0" in model_path.name:
        active = "v1.0"
    else:
        active = "v0.19"

    return {"active": active, "on_disk": on_disk}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
def cli():
    """Narrator — generate audio narrations from Markdown posts."""


@cli.command()
@click.argument("post_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--voice", default=None, help="Voice ID (overrides config.yaml)")
@click.option(
    "--format", "fmt", default=None,
    type=click.Choice(SUPPORTED_FORMATS, case_sensitive=False),
    help="Output format (overrides config.yaml)",
)
@click.option("--speed", default=None, type=float, help="Speech speed multiplier")
@click.option("--no-intro", is_flag=True, default=False, help="Skip intro audio")
@click.option("--no-outro", is_flag=True, default=False, help="Skip outro audio")
@click.option("--raw-only", is_flag=True, default=False, help="Stop after synthesis; skip encoding")
@click.option("--force", is_flag=True, default=False, help="Regenerate even if output already exists")
@click.option("--post-name", "post_name", default=None, help="Override slug derived from filename (^[a-z0-9][a-z0-9-]*$)")
@click.option("--output", "output_override", default=None, type=click.Path(), help="Exact output file path (overrides derived path)")
@click.option("--dry-run", is_flag=True, default=False, help="Validate inputs and print the resolved plan without running the pipeline")
@click.option("--progress", is_flag=True, default=False, help="Emit JSON progress events to stdout during synthesis")
@click.option("--cache-segments", "cache_segments", is_flag=True, default=False,
              help="Write segment files and manifest to disk; enables resume-on-failure")
@click.option("--workers", default=4, type=int, show_default=True,
              help="Number of parallel synthesis threads. Ignored when --cache-segments is set.")
def generate(post_path, voice, fmt, speed, no_intro, no_outro, raw_only, force, post_name, output_override, dry_run, progress, cache_segments, workers):
    """Generate a narration for POST_PATH (a Markdown file)."""
    try:
        config = _load_config()

        # --- Config validation -----------------------------------------------
        config_errors = validate_config(config)
        if config_errors:
            _err("Invalid config.yaml:\n" + "\n".join(f"  • {e}" for e in config_errors))

        voice = voice or config["tts"]["voice"]
        fmt = (fmt or config["audio"]["output_format"]).lower()
        speed = speed if speed is not None else config["tts"]["speed"]
        pause_ms = config["audio"]["paragraph_pause_ms"]

        # --- Pre-flight checks ------------------------------------------------
        ffmpeg_err = check_ffmpeg()
        if ffmpeg_err:
            _err(ffmpeg_err)

        speed_err = check_speed(speed)
        if speed_err:
            _err(speed_err)

        voice_hint = check_voice_format(voice, config["tts"]["provider"])
        if voice_hint:
            print(f"  [HINT] {voice_hint}", file=sys.stderr)

        post_path = Path(post_path)
        for issue in check_post_file(post_path):
            if issue.startswith("ERROR:"):
                _err(issue.removeprefix("ERROR: "))
            else:
                print(f"  [WARN] {issue.removeprefix('WARN: ')}", file=sys.stderr)

        post_name = post_name or post_path.stem
        if not re.match(r'^[a-z0-9][a-z0-9-]*$', post_name):
            _err(f"--post-name must match ^[a-z0-9][a-z0-9-]*$ (got {post_name!r})")

        raw_dir = Path(config["paths"]["raw_output"])
        output_dir = Path(config["paths"]["final_output"])

        if output_override:
            output_path = Path(output_override)
            if output_path.suffix:
                inferred_fmt = output_path.suffix.lstrip(".").lower()
                if inferred_fmt in SUPPORTED_FORMATS:
                    fmt = inferred_fmt
                else:
                    _err(f"Unsupported output format {inferred_fmt!r}. Supported: {', '.join(SUPPORTED_FORMATS)}")
            else:
                output_path = output_path.with_suffix(f".{fmt}")
        else:
            output_path = output_dir / f"{post_name}.{fmt}"

        if dry_run:
            _ok({
                "status": "ok",
                "dry_run": True,
                "post": str(post_path),
                "post_name": post_name,
                "voice": voice,
                "speed": speed,
                "format": fmt,
                "output_path": str(output_path),
                "would_skip": output_path.exists() and not force and not raw_only,
                "skip_intro": no_intro,
                "skip_outro": no_outro,
                "force": force,
                "cache_segments": cache_segments,
                "workers": workers,
            })
            return

        if output_path.exists() and not force and not raw_only:
            _ok({
                "status": "skipped",
                "reason": "output already exists",
                "output_path": str(output_path),
                "hint": "pass --force to regenerate",
            })
            return

        if output_path.exists() and (force or raw_only):
            print(
                f"  [WARN] Output already exists: {output_path}. "
                "Regenerating because --force/--raw-only was passed.",
                file=sys.stderr,
            )
            if progress:
                _event({"event": "warn", "message": f"Output already exists: {output_path}. Regenerating."})

        # Preprocess
        print(f"Preprocessing {post_path.name}...", file=sys.stderr)
        text = post_path.read_text(encoding="utf-8")
        paragraphs = preprocess(text)
        print(f"Found {len(paragraphs)} paragraphs.", file=sys.stderr)

        if not paragraphs:
            _err("No text found after preprocessing. Check that the file contains readable content.")

        if progress:
            _event({"event": "preprocess_done", "paragraphs": len(paragraphs)})

        # Synthesize
        provider = _load_provider(config)
        body_path = synthesize(
            paragraphs=paragraphs,
            post_name=post_name,
            provider=provider,
            voice=voice,
            speed=speed,
            pause_ms=pause_ms,
            raw_dir=raw_dir,
            force=force,
            emit_progress=progress,
            cache_segments=cache_segments,
            workers=workers,
        )

        if progress:
            _event({"event": "synthesis_done", "body_path": str(body_path)})

        if raw_only:
            _ok({
                "status": "ok",
                "post": str(post_path),
                "output_path": str(body_path),
                "voice": voice,
                "format": "wav",
            })
            return

        # Mix intro + body + outro
        print("Mixing audio...", file=sys.stderr)
        mix_input = mix(
            body_path=body_path,
            post_name=post_name,
            intro_dir=Path(config["paths"]["intro"]),
            outro_dir=Path(config["paths"]["outro"]),
            normalize=config["audio"]["normalize_loudness"],
            fade_duration_ms=config["audio"].get("fade_duration_ms", 2000),
            skip_intro=no_intro,
            skip_outro=no_outro,
            force=force,
        )

        if progress:
            _event({"event": "mix_done", "mixed_path": str(mix_input)})

        # Encode
        print(f"Encoding to {fmt}...", file=sys.stderr)
        from pydub import AudioSegment
        audio = AudioSegment.from_wav(str(mix_input))
        duration_sec = int(len(audio) / 1000)

        volume_db = config["audio"].get("volume_db", 0)
        final_path = encode(mix_input, output_path, fmt, volume_db=volume_db)
        print(f"Done: {final_path}", file=sys.stderr)

        if progress:
            _event({"event": "encode_done", "output_path": str(final_path)})

        _ok({
            "status": "ok",
            "post": str(post_path),
            "output_path": str(final_path),
            "duration_sec": duration_sec,
            "voice": voice,
            "format": fmt,
        })

    except FileNotFoundError as exc:
        _err(str(exc))
    except Exception as exc:
        _err(str(exc))


@cli.command()
@click.argument("post_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--format", "fmt", default=None,
    type=click.Choice(SUPPORTED_FORMATS, case_sensitive=False),
    help="Output format (overrides config.yaml)",
)
@click.option("--no-intro", is_flag=True, default=False, help="Skip intro audio")
@click.option("--no-outro", is_flag=True, default=False, help="Skip outro audio")
@click.option("--post-name", "post_name", default=None, help="Override slug derived from filename (^[a-z0-9][a-z0-9-]*$)")
@click.option("--output", "output_override", default=None, type=click.Path(), help="Exact output file path (overrides derived path)")
def remix(post_path, fmt, no_intro, no_outro, post_name, output_override):
    """Re-mix intro/outro with the saved body WAV without re-synthesizing."""
    try:
        config = _load_config()

        config_errors = validate_config(config)
        if config_errors:
            _err("Invalid config.yaml:\n" + "\n".join(f"  • {e}" for e in config_errors))

        ffmpeg_err = check_ffmpeg()
        if ffmpeg_err:
            _err(ffmpeg_err)

        fmt = (fmt or config["audio"]["output_format"]).lower()

        post_path = Path(post_path)
        post_name = post_name or post_path.stem
        if not re.match(r'^[a-z0-9][a-z0-9-]*$', post_name):
            _err(f"--post-name must match ^[a-z0-9][a-z0-9-]*$ (got {post_name!r})")

        raw_dir = Path(config["paths"]["raw_output"])
        output_dir = Path(config["paths"]["final_output"])

        body_path = raw_dir / post_name / f"{post_name}-body.wav"
        if not body_path.exists():
            _err(
                f"Body WAV not found at {body_path} — "
                "run `generate` first to synthesize the post."
            )

        if output_override:
            output_path = Path(output_override)
            if output_path.suffix:
                inferred_fmt = output_path.suffix.lstrip(".").lower()
                if inferred_fmt in SUPPORTED_FORMATS:
                    fmt = inferred_fmt
                else:
                    _err(f"Unsupported output format {inferred_fmt!r}. Supported: {', '.join(SUPPORTED_FORMATS)}")
            else:
                output_path = output_path.with_suffix(f".{fmt}")
        else:
            output_path = output_dir / f"{post_name}.{fmt}"

        print("Mixing audio...", file=sys.stderr)
        mix_input = mix(
            body_path=body_path,
            post_name=post_name,
            intro_dir=Path(config["paths"]["intro"]),
            outro_dir=Path(config["paths"]["outro"]),
            normalize=config["audio"]["normalize_loudness"],
            fade_duration_ms=config["audio"].get("fade_duration_ms", 2000),
            skip_intro=no_intro,
            skip_outro=no_outro,
            force=True,
        )

        print(f"Encoding to {fmt}...", file=sys.stderr)
        from pydub import AudioSegment
        audio = AudioSegment.from_wav(str(mix_input))
        duration_sec = int(len(audio) / 1000)

        volume_db = config["audio"].get("volume_db", 0)
        final_path = encode(mix_input, output_path, fmt, volume_db=volume_db)
        print(f"Done: {final_path}", file=sys.stderr)

        _ok({
            "status": "ok",
            "post": str(post_path),
            "output_path": str(final_path),
            "duration_sec": duration_sec,
            "format": fmt,
        })

    except FileNotFoundError as exc:
        _err(str(exc))
    except Exception as exc:
        _err(str(exc))


@cli.command()
def voices():
    """List available voices for the configured TTS provider."""
    try:
        config = _load_config()

        installed = _installed_model(config)

        if "v1.0" in installed["on_disk"] and installed["active"] != "v1.0":
            print(
                "  [WARN] v1.0 model is present but not active — "
                "set model_path and voices_path in config.yaml to use it.",
                file=sys.stderr,
            )

        provider = _load_provider(config)
        actual_voices = set(provider.list_voices()) if installed["active"] is not None else set()

        all_ids = sorted(set(KNOWN_VOICES) | actual_voices)
        annotated = [
            {
                "id": vid,
                "available": vid in actual_voices,
                "requires_model": _voice_requires_model(vid),
            }
            for vid in all_ids
        ]

        _ok({
            "status": "ok",
            "provider": config["tts"]["provider"],
            "installed_model": installed["active"],
            "models_on_disk": installed["on_disk"],
            "voices": annotated,
        })
    except Exception as exc:
        _err(str(exc))


@cli.command()
def check():
    """Validate setup: config, ffmpeg, model files, and Python packages."""
    issues = []
    config = None

    # Config
    try:
        config = _load_config()
        config_errors = validate_config(config)
        if config_errors:
            issues.extend(config_errors)
        else:
            print("  [OK]   config.yaml", file=sys.stderr)
    except FileNotFoundError:
        issues.append("config.yaml not found in the current directory")
    except Exception as exc:
        issues.append(f"config.yaml could not be parsed: {exc}")

    # ffmpeg
    ffmpeg_err = check_ffmpeg()
    if ffmpeg_err:
        issues.append(ffmpeg_err)
    else:
        print("  [OK]   ffmpeg", file=sys.stderr)

    # Model files
    if not DEFAULT_MODEL_PATH.exists():
        issues.append(
            f"Kokoro model not found at '{DEFAULT_MODEL_PATH}' — "
            "run 'python narrator.py setup'"
        )
    else:
        print(f"  [OK]   {DEFAULT_MODEL_PATH.name}", file=sys.stderr)

    if not DEFAULT_VOICES_PATH.exists():
        issues.append(
            f"Kokoro voices file not found at '{DEFAULT_VOICES_PATH}' — "
            "run 'python narrator.py setup'"
        )
    else:
        print(f"  [OK]   {DEFAULT_VOICES_PATH.name}", file=sys.stderr)

    # Python packages
    for pkg in ["kokoro_onnx", "pydub", "yaml", "click"]:
        try:
            __import__(pkg)
            print(f"  [OK]   {pkg}", file=sys.stderr)
        except ImportError:
            issues.append(f"Python package missing: {pkg} — run 'pip install -r requirements.txt'")

    if issues:
        for issue in issues:
            print(f"  [FAIL] {issue}", file=sys.stderr)
        _ok({"status": "error", "issues": issues})
        sys.exit(1)
    else:
        print("  [OK] All checks passed.", file=sys.stderr)
        installed = _installed_model(config) if config is not None else None
        active = installed["active"] if installed else None
        result = {"status": "ok", "ffmpeg": True, "installed_model": active}
        if installed and "v1.0" in installed["on_disk"] and active != "v1.0":
            print(
                "  [WARN] v1.0 model is present but not active — "
                "set model_path and voices_path in config.yaml to use it.",
                file=sys.stderr,
            )
            result["hint"] = (
                "v1.0 model is present but not active — "
                "set model_path and voices_path in config.yaml"
            )
        if config is not None:
            result["config"] = config
        _ok(result)


@cli.command()
@click.option(
    "--multilingual", is_flag=True, default=False,
    help=(
        "Download the Kokoro v1.0 multilingual model instead of the default v0.19 English model. "
        "Supports 9 languages and 54 voices. Use with model_path/voices_path overrides in config.yaml."
    ),
)
@click.option("--show-urls", is_flag=True, default=False, help="Print download URLs as JSON without downloading")
def setup(multilingual, show_urls):
    """Download Kokoro model files to the models/ directory."""
    if show_urls:
        _ok({
            "status": "ok",
            "models": {
                "v0.19": {
                    "onnx": _MODEL_DOWNLOADS[DEFAULT_MODEL_PATH.name],
                    "voices": _MODEL_DOWNLOADS[DEFAULT_VOICES_PATH.name],
                },
                "v1.0": {
                    "onnx": _MULTILINGUAL_DOWNLOADS[MULTILINGUAL_MODEL_PATH.name],
                    "voices": _MULTILINGUAL_DOWNLOADS[MULTILINGUAL_VOICES_PATH.name],
                },
            },
        })
        return

    downloads = _MULTILINGUAL_DOWNLOADS if multilingual else _MODEL_DOWNLOADS
    models_dir = DEFAULT_MODEL_PATH.parent
    models_dir.mkdir(exist_ok=True)

    if multilingual:
        print(
            "  [INFO] Downloading multilingual model (v1.0 int8, ~88 MB, 9 languages, 54 voices).",
            file=sys.stderr,
        )
        print(
            "  [INFO] To use it, set model_path and voices_path in config.yaml. "
            "See wiki/configuration.md.",
            file=sys.stderr,
        )

    all_ok = True
    for filename, url in downloads.items():
        dest = models_dir / filename
        if dest.exists():
            print(f"  [SKIP] {filename} already exists.", file=sys.stderr)
            continue
        print(f"  [DOWN] Downloading {filename}...", file=sys.stderr)
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"  [OK]   {filename} downloaded.", file=sys.stderr)
        except Exception as exc:
            print(f"  [FAIL] Could not download {filename}: {exc}", file=sys.stderr)
            print(
                f"         Download manually from:\n         {url}\n"
                f"         and place it at: {dest}",
                file=sys.stderr,
            )
            all_ok = False

    if all_ok:
        _ok({"status": "ok", "message": "Setup complete. Run 'python narrator.py check' to verify."})
    else:
        _err("One or more model files could not be downloaded. See above for details.")


@cli.command()
def status():
    """Show synthesis and output status for all posts."""
    try:
        config = _load_config()
        posts_dir = Path(config["paths"]["posts"])
        raw_dir = Path(config["paths"]["raw_output"])
        output_dir = Path(config["paths"]["final_output"])

        post_files = sorted(posts_dir.glob("*.md")) if posts_dir.exists() else []
        results = []

        for post_path in post_files:
            stem = post_path.stem
            manifest_path = raw_dir / stem / "manifest.json"

            synthesis = None
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    synthesis = {
                        "cached": True,
                        "segments_done": len(manifest.get("completed", [])),
                        "total_paragraphs": manifest.get("total_paragraphs", 0),
                        "voice": manifest.get("voice"),
                        "speed": manifest.get("speed"),
                    }
                except Exception:
                    synthesis = {"cached": True, "error": "manifest unreadable"}

            output_files = []
            if output_dir.exists():
                for fmt in SUPPORTED_FORMATS:
                    candidate = output_dir / f"{stem}.{fmt}"
                    if candidate.exists():
                        output_files.append({"path": str(candidate), "format": fmt})

            results.append({
                "name": stem,
                "path": str(post_path),
                "synthesis": synthesis,
                "output": output_files,
            })

        _ok({"status": "ok", "posts": results})
    except FileNotFoundError as exc:
        _err(str(exc))
    except Exception as exc:
        _err(str(exc))


@cli.command("config")
def show_config():
    """Print the resolved configuration as JSON."""
    try:
        config = _load_config()
        errors = validate_config(config)
        if errors:
            _ok({"status": "error", "issues": errors})
            sys.exit(1)
        _ok({"status": "ok", "config": config})
    except FileNotFoundError:
        _err("config.yaml not found in the current directory")
    except Exception as exc:
        _err(f"config.yaml could not be parsed: {exc}")


if __name__ == "__main__":
    cli()
