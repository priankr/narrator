"""
CLI output shape tests.

Group A — real environment (uses actual config.yaml and installed models):
  check, voices, config, status, generate --dry-run

Group B — isolated (uses project_dir fixture and a mocked TTS provider):
  generate success, skipped, force, raw-only, invalid speed

All tests assert only on JSON output shape; they do not assert on specific
config values so they continue passing as config.yaml evolves.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from narrator import cli
from tests.conftest import MockTTSProvider, make_silent_wav


def _parse_result(result: str) -> dict:
    """Return the last JSON line from stdout (the terminal status line)."""
    lines = [ln for ln in result.strip().splitlines() if ln.startswith("{")]
    assert lines, f"No JSON found in output:\n{result}"
    return json.loads(lines[-1])


# ---------------------------------------------------------------------------
# Group A: real environment
# ---------------------------------------------------------------------------

class TestRealEnvironment:
    """Requires config.yaml, ffmpeg, and Kokoro model in the project root."""

    @pytest.fixture(autouse=True)
    def _chdir(self, project_root_cwd):
        pass

    def test_check_exits_zero_and_returns_ok(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["check"])
        assert result.exit_code == 0
        data = _parse_result(result.output)
        assert data["status"] == "ok"
        assert "ffmpeg" in data
        assert "installed_model" in data
        assert "config" in data

    def test_voices_returns_annotated_list(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["voices"])
        assert result.exit_code == 0
        data = _parse_result(result.output)
        assert data["status"] == "ok"
        assert "provider" in data
        assert "installed_model" in data
        assert isinstance(data["voices"], list)
        assert len(data["voices"]) > 0
        first = data["voices"][0]
        assert "id" in first
        assert "available" in first
        assert "requires_model" in first

    def test_config_returns_full_config(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config"])
        assert result.exit_code == 0
        data = _parse_result(result.output)
        assert data["status"] == "ok"
        assert "config" in data
        cfg = data["config"]
        assert "tts" in cfg
        assert "audio" in cfg
        assert "paths" in cfg

    def test_status_returns_posts_list(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        data = _parse_result(result.output)
        assert data["status"] == "ok"
        assert isinstance(data["posts"], list)

    def test_generate_dry_run_returns_plan(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "posts/sample.md", "--dry-run"])
        assert result.exit_code == 0
        data = _parse_result(result.output)
        assert data["status"] == "ok"
        assert data["dry_run"] is True
        assert "post" in data
        assert "output_path" in data
        assert "would_skip" in data
        assert "voice" in data
        assert "format" in data

    def test_generate_dry_run_with_post_name_override(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["generate", "posts/sample.md", "--dry-run", "--post-name", "my-custom-slug"]
        )
        assert result.exit_code == 0
        data = _parse_result(result.output)
        assert data["post_name"] == "my-custom-slug"
        assert "my-custom-slug" in data["output_path"]

    def test_generate_dry_run_invalid_post_name_exits_one(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["generate", "posts/sample.md", "--dry-run", "--post-name", "INVALID NAME"]
        )
        assert result.exit_code == 1
        data = _parse_result(result.output)
        assert data["status"] == "error"

    def test_generate_invalid_speed_exits_one(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["generate", "posts/sample.md", "--dry-run", "--speed", "0.1"]
        )
        assert result.exit_code == 1
        data = _parse_result(result.output)
        assert data["status"] == "error"

    def test_setup_show_urls_returns_model_urls(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["setup", "--show-urls"])
        assert result.exit_code == 0
        data = _parse_result(result.output)
        assert data["status"] == "ok"
        assert "v0.19" in data["models"]
        assert "v1.0" in data["models"]
        assert "onnx" in data["models"]["v0.19"]
        assert "voices" in data["models"]["v0.19"]


# ---------------------------------------------------------------------------
# Group B: isolated with mocked provider
# ---------------------------------------------------------------------------

class TestIsolatedGenerate:
    """Full pipeline tests using a mock TTS provider and temp project dir."""

    @pytest.fixture(autouse=True)
    def _setup(self, project_dir, monkeypatch):
        self.project_dir = project_dir
        self.post_path = str(project_dir / "posts" / "test-post.md")
        self.mock = MockTTSProvider(make_silent_wav())
        monkeypatch.chdir(project_dir)

    def _invoke(self, *args):
        runner = CliRunner()
        with patch("narrator._load_provider", return_value=self.mock), \
             patch("narrator.check_ffmpeg", return_value=None):
            return runner.invoke(cli, list(args))

    def test_generate_success(self):
        result = self._invoke("generate", self.post_path)
        assert result.exit_code == 0, result.output
        data = _parse_result(result.output)
        assert data["status"] == "ok"
        assert "output_path" in data
        assert Path(data["output_path"]).exists()

    def test_generate_skipped_when_output_exists(self):
        # First run to create the output
        self._invoke("generate", self.post_path)
        # Second run should skip
        result = self._invoke("generate", self.post_path)
        assert result.exit_code == 0
        data = _parse_result(result.output)
        assert data["status"] == "skipped"
        assert "output_path" in data
        assert "force" in data["hint"]

    def test_generate_force_reruns(self):
        self._invoke("generate", self.post_path)
        calls_after_first = self.mock.call_count

        result = self._invoke("generate", self.post_path, "--force")
        assert result.exit_code == 0
        data = _parse_result(result.output)
        assert data["status"] == "ok"
        assert self.mock.call_count > calls_after_first

    def test_generate_raw_only(self):
        result = self._invoke("generate", self.post_path, "--raw-only")
        assert result.exit_code == 0
        data = _parse_result(result.output)
        assert data["status"] == "ok"
        assert data["format"] == "wav"
        assert Path(data["output_path"]).exists()

    def test_generate_with_progress_emits_events(self):
        runner = CliRunner()
        with patch("narrator._load_provider", return_value=self.mock), \
             patch("narrator.check_ffmpeg", return_value=None):
            result = runner.invoke(cli, ["generate", self.post_path, "--progress"])

        assert result.exit_code == 0, result.output
        lines = [ln for ln in result.output.strip().splitlines() if ln.startswith("{")]
        assert len(lines) > 1  # at least one event + the status line
        events = [json.loads(ln) for ln in lines]
        event_types = {e.get("event") for e in events if "event" in e}
        assert "preprocess_done" in event_types
        assert "synthesis_done" in event_types
        # Terminal line has status, not event
        assert events[-1].get("status") == "ok"
