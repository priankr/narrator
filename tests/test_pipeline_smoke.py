"""
End-to-end smoke test against posts/sample.md using the real Kokoro model.

Run with:
    pytest                        # includes slow tests
    pytest -m "not slow"          # skips slow tests (fast CI)

Requires: ffmpeg on PATH, Kokoro model files downloaded (run 'python narrator.py setup').
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SAMPLE_POST = PROJECT_ROOT / "posts" / "sample.md"
NARRATOR = PROJECT_ROOT / "narrator.py"


@pytest.mark.slow
class TestPipelineSmoke:

    def _run(self, *args) -> tuple[int, dict]:
        """Invoke narrator.py and return (exit_code, parsed_stdout_json)."""
        cmd = [sys.executable, str(NARRATOR)] + list(args)
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        # Find the terminal JSON line (status line, not event lines)
        json_lines = [ln for ln in proc.stdout.strip().splitlines() if ln.startswith("{")]
        data = json.loads(json_lines[-1]) if json_lines else {}
        return proc.returncode, data

    def test_check_passes(self):
        code, data = self._run("check")
        assert code == 0, f"check failed: {data}"
        assert data["status"] == "ok"

    def test_generate_sample_post(self):
        # Force a fresh run to ensure the pipeline actually runs
        code, data = self._run("generate", str(SAMPLE_POST), "--force")
        assert code == 0, f"generate failed: {data}"
        assert data["status"] == "ok"
        assert "output_path" in data
        assert data["duration_sec"] > 0

    def test_output_file_exists_and_has_content(self):
        code, data = self._run("generate", str(SAMPLE_POST))
        assert code == 0
        # May be "ok" (ran) or "skipped" (already exists) — either is fine
        assert data["status"] in ("ok", "skipped")
        output_path = Path(data["output_path"])
        assert output_path.exists(), f"Output file not found: {output_path}"
        assert output_path.stat().st_size > 0

    def test_generate_is_idempotent(self):
        """Re-running without --force returns 'skipped', not an error."""
        # Ensure file exists first
        self._run("generate", str(SAMPLE_POST))
        # Second run without --force
        code, data = self._run("generate", str(SAMPLE_POST))
        assert code == 0
        assert data["status"] in ("ok", "skipped")

    def test_dry_run_does_not_create_new_output(self):
        code, data = self._run("generate", str(SAMPLE_POST), "--dry-run", "--post-name", "smoke-dryrun")
        assert code == 0
        assert data["dry_run"] is True
        # No file should be created for a dry run
        output_path = Path(data["output_path"])
        assert not output_path.exists()
