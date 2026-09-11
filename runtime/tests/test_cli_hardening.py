"""Real installed-CLI checks: Git workspace, schemas, signatures, SQLite, restart.

Unlike the topology-only fixture test, these tests have no approval or validator
bypass. Signing keys and Git repositories are disposable test fixtures.
"""
import base64
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from turn_up_time_graph.approvals import canonical

SOURCE = Path(__file__).resolve().parents[2]


@pytest.fixture
def installed_project(tmp_path):
    repo, home = tmp_path / "repo", tmp_path / "owner-home"
    repo.mkdir()
    (home / ".claude").mkdir(parents=True)
    shutil.copytree(SOURCE / ".claude/scripts", repo / ".claude/scripts", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(SOURCE / ".claude/schemas", repo / ".claude/schemas")
    (repo / ".gitignore").write_text("__pycache__/\n*.pyc\n.claude/projects/\n.claude/runtime/\n")
    (repo / "app.txt").write_text("fixture application")
    for args in (("init",), ("config", "user.name", "Fixture Owner"),
                 ("config", "user.email", "fixture@example.invalid"), ("add", "."), ("commit", "-m", "fixture")):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    project = repo / ".claude/projects/pilot"
    subprocess.run([sys.executable, str(repo / ".claude/scripts/scaffold_project.py"), "pilot",
                    "--profile", "lite", "--root", str(project.parent)], check=True, capture_output=True)
    intake = json.loads((project / "intake-readiness.json").read_text())
    intake.update(status="READY", primary_user="Fixture owner", primary_job="Test a change",
                  desired_outcome="Verified fixture", product_boundary="Disposable local files only")
    (project / "intake-readiness.json").write_text(json.dumps(intake))
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    trust = {"keys": {"fixture": {"public_key": base64.b64encode(public).decode(), "approver": "Fixture Owner", "gates": ["INTAKE"]}}}
    (home / ".claude/turn-up-time-trust.json").write_text(json.dumps(trust))
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), TURN_UP_TIME_CLAUDE_HOME=str(home / ".claude"), PYTHONDONTWRITEBYTECODE="1")
    return repo, project, private, env


def cli(fixture, command, *args, success=True, prefix=None):
    repo, project, _, env = fixture
    cmd = prefix or [sys.executable, "-m", "turn_up_time_graph.cli"]
    result = subprocess.run([*cmd, command, "--repo-root", str(repo), "--project-dir", str(project), *args],
                            capture_output=True, text=True, env=env, timeout=60)
    if success:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0, result.stdout
    return result


def signed_intake(fixture):
    _, project, private, _ = fixture
    args = ["--event", "intake_ready", "--event-id", "intake-1", "--approved-by", "Fixture Owner"]
    request = json.loads(cli(fixture, "request-approval", *args).stdout)
    now = datetime.now(timezone.utc)
    statement = {"request": request, "approver": "Fixture Owner", "approval_id": "fixture-approval",
                 "issued_at": now.isoformat(), "expires_at": (now + timedelta(minutes=30)).isoformat()}
    envelope = {"key_id": "fixture", "approval_id": "fixture-approval", "statement": statement,
                "signature": base64.b64encode(private.sign(canonical(statement))).decode()}
    (project / "approvals").mkdir(exist_ok=True)
    (project / "approvals/intake.json").write_text(json.dumps(envelope))
    return [*args, "--approval-ref", "approvals/intake.json"]


def test_cli_bookkeeping_signed_transition_and_retry(installed_project):
    _, project, _, _ = installed_project
    initial_history = json.loads((project / "project-ledger.json").read_text())["stage_history"]
    cli(installed_project, "signal", "--event", "record_artifact", "--event-id", "record-1",
        "--data-json", json.dumps({"path": "intake-readiness.json", "schema": "intake-readiness.schema.json"}))
    ledger = json.loads((project / "project-ledger.json").read_text())
    assert ledger["stage_history"] == initial_history
    assert ledger["artifacts"]["intake-readiness.json"]["sha256"]
    # A display name, even the correct name, is insufficient.
    result = cli(installed_project, "signal", "--event", "intake_ready", "--event-id", "intake-1",
                 "--approved-by", "Fixture Owner", success=False)
    assert "owner-signed" in result.stdout
    args = signed_intake(installed_project)
    cli(installed_project, "signal", *args)
    repeated = json.loads(cli(installed_project, "signal", *args).stdout)
    assert repeated["status"] == "ALREADY_APPLIED"
    ledger = json.loads((project / "project-ledger.json").read_text())
    assert ledger["stage"] == "DISCOVERY"
    assert len(ledger["approvals"]) == 1
    assert len(ledger["stage_history"]) == 2
    cli(installed_project, "signal", "--event", "reserve_spawn", "--event-id", "spawn-1",
        "--data-json", json.dumps({"spawn_id": "research-1", "role": "product-domain-researcher",
                                   "role_class": "assurance", "reason": "independent evidence"}))
    cli(installed_project, "signal", "--event", "complete_spawn", "--event-id", "finish-1",
        "--data-json", json.dumps({"spawn_id": "research-1", "outcome": "SUCCEEDED", "artifact_refs": ["intake-readiness.json"]}))
    ledger = json.loads((project / "project-ledger.json").read_text())
    assert ledger["spawn_budget"]["used"] == 1
    assert ledger["spawn_log"][0]["completed_at"]
    assert ledger["stage"] == "DISCOVERY"


def test_changed_code_invalidates_approval(installed_project):
    repo, _, _, _ = installed_project
    args = signed_intake(installed_project)
    (repo / "app.txt").write_text("changed after approval")
    result = cli(installed_project, "signal", *args, success=False)
    assert "does not match" in result.stdout


def test_missing_validator_cannot_advance(installed_project):
    repo, _, _, _ = installed_project
    (repo / ".claude/scripts/validate_project.py").unlink()
    result = cli(installed_project, "signal", "--event", "intake_ready", "--event-id", "intake-1",
                 "--approved-by", "Fixture Owner", success=False)
    assert "validator is missing" in result.stdout


@pytest.mark.parametrize("boundary", ["atomic_text", "append_event"])
def test_real_process_death_recovers_without_duplicate_transition(installed_project, boundary):
    _, project, _, _ = installed_project
    args = signed_intake(installed_project)
    injection = (
        "import os; from turn_up_time_graph import transactions as tx; "
        "from turn_up_time_graph.cli import main; "
        f"tx.{boundary} = lambda *a, **k: os._exit(73); main()"
    )
    result = cli(installed_project, "signal", *args, success=False,
                 prefix=[sys.executable, "-c", injection])
    assert result.returncode == 73, result.stdout + result.stderr
    cli(installed_project, "recover")
    cli(installed_project, "signal", *args)
    ledger = json.loads((project / "project-ledger.json").read_text())
    assert ledger["stage"] == "DISCOVERY"
    assert len(ledger["approvals"]) == 1
    rows = [json.loads(line) for line in (project / "events.jsonl").read_text().splitlines()]
    assert len([row for row in rows if row["event_id"] == "intake-1"]) == 1
