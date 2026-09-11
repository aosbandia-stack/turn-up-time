import json
import shutil
import subprocess
from pathlib import Path

import pytest

SHELL = shutil.which("powershell.exe") or shutil.which("pwsh") or shutil.which("powershell")
GUARD = Path(__file__).resolve().parents[2] / ".claude/hooks/destructive-command-guard.ps1"
pytestmark = pytest.mark.skipif(SHELL is None, reason="PowerShell not present; covered by Windows CI")


@pytest.mark.parametrize("payload", ["", "not json", "{}", "[]", "null",
    json.dumps({"tool_input": {"command": []}}),
    json.dumps({"tool_input": {"command": "git reset --hard HEAD~1"}}),
])
def test_guard_denies_invalid_or_destructive_input(payload):
    result = subprocess.run([SHELL, "-NoProfile", "-File", str(GUARD)], input=payload,
                            text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_guard_preserves_ordinary_command():
    result = subprocess.run([SHELL, "-NoProfile", "-File", str(GUARD)],
                            input=json.dumps({"tool_input": {"command": "git status --short"}}),
                            text=True, capture_output=True, timeout=20)
    assert result.returncode == 0
    assert not result.stdout.strip()
