import copy
import subprocess

import pytest

from turn_up_time_graph.operations import apply_operation
from turn_up_time_graph.exceptions import TurnUpTimeGraphError
from turn_up_time_graph.workspace import build_identity


def ledger():
    return {"stage": "BUILD", "spawn_budget": {"limit": 1, "used": 0}, "spawn_log": [], "artifacts": {}}


def test_budget_reserved_before_dispatch(tmp_path):
    value = ledger()
    data = {"spawn_id": "w1", "role": "implementation-engineer", "role_class": "production", "reason": "ticket A"}
    apply_operation(tmp_path, tmp_path, value, "reserve_spawn", data)
    assert value["spawn_budget"]["used"] == 1
    with pytest.raises(TurnUpTimeGraphError, match="budget exhausted"):
        apply_operation(tmp_path, tmp_path, value, "reserve_spawn", dict(data, spawn_id="w2"))
    with pytest.raises(TurnUpTimeGraphError, match="already reserved"):
        apply_operation(tmp_path, tmp_path, value, "reserve_spawn", data)
    assert value["spawn_budget"]["used"] == 1


def test_production_cannot_start_during_discovery(tmp_path):
    value = ledger()
    value["stage"] = "DISCOVERY"
    with pytest.raises(TurnUpTimeGraphError, match="production spawn"):
        apply_operation(tmp_path, tmp_path, value, "reserve_spawn", {
            "spawn_id": "w1", "role": "builder", "role_class": "production", "reason": "x"})
    assert value["spawn_budget"]["used"] == 0


def test_completion_preserves_consumed_budget(tmp_path):
    value = ledger()
    apply_operation(tmp_path, tmp_path, value, "reserve_spawn", {
        "spawn_id": "w1", "role": "builder", "role_class": "production", "reason": "x"})
    apply_operation(tmp_path, tmp_path, value, "complete_spawn", {"spawn_id": "w1", "outcome": "FAILED"})
    assert value["spawn_log"][0]["completed_at"]
    assert value["spawn_budget"]["used"] == 1
    with pytest.raises(TurnUpTimeGraphError, match="already completed"):
        apply_operation(tmp_path, tmp_path, value, "complete_spawn", {"spawn_id": "w1", "outcome": "SUCCEEDED"})


def test_artifact_registration_hashes_actual_bytes(tmp_path):
    value = ledger()
    (tmp_path / "artifact.txt").write_text("evidence")
    original = copy.deepcopy(value)
    apply_operation(tmp_path, tmp_path, value, "record_artifact", {"path": "artifact.txt"})
    assert len(value["artifacts"]["artifact.txt"]["sha256"]) == 64
    assert value["stage"] == original["stage"]
    assert value["spawn_budget"] == original["spawn_budget"]
    with pytest.raises(TurnUpTimeGraphError):
        apply_operation(tmp_path, tmp_path, value, "record_artifact", {"path": "project-ledger.json"})


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)


def test_code_identity_changes_but_project_metadata_does_not(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.name", "Disposable Test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "app.txt").write_text("v1")
    git(tmp_path, "add", "app.txt")
    git(tmp_path, "commit", "-m", "fixture")
    before = build_identity(tmp_path)
    project = tmp_path / ".claude/projects/pilot"
    project.mkdir(parents=True)
    (project / "project-ledger.json").write_text("metadata")
    assert build_identity(tmp_path) == before
    (tmp_path / "app.txt").write_text("v2")
    assert build_identity(tmp_path) != before
    (tmp_path / "app.txt").write_text("v1")
    (tmp_path / "new.txt").write_text("untracked code")
    assert build_identity(tmp_path) != before
