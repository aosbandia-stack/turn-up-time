import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / ".claude/scripts/scaffold_project.py"


def run(root, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *args, "--root", str(root)], capture_output=True, text=True)


def test_explicit_whole_project_budget_and_no_reset(tmp_path):
    result = run(tmp_path, "pilot", "--profile", "lite", "--spawn-budget", "12")
    assert result.returncode == 0, result.stderr
    path = tmp_path / "pilot/project-ledger.json"
    before = path.read_bytes()
    assert json.loads(before)["spawn_budget"] == {"limit": 12, "used": 0}
    result = run(tmp_path, "pilot", "--force", "--spawn-budget", "100")
    assert result.returncode != 0
    assert path.read_bytes() == before


@pytest.mark.parametrize("name", ["../outside", "nested/project", "..", "/absolute", "C:\\project"])
def test_path_project_id_is_rejected(tmp_path, name):
    assert run(tmp_path, name).returncode != 0
    assert not list(tmp_path.iterdir())


def test_negative_budget_is_rejected(tmp_path):
    assert run(tmp_path, "pilot", "--spawn-budget", "-1").returncode != 0
    assert not list(tmp_path.iterdir())
