"""Seeded legacy history, real journal recovery, and fail-closed metadata repair."""
import copy
import hashlib
import json
import sqlite3
from unittest.mock import patch

import pytest
from jsonschema import Draft202012Validator

from turn_up_time_graph import transactions as tx
from turn_up_time_graph.compatibility import PROFILE, backup_project, compatibility_plan, verify_backup
from turn_up_time_graph.exceptions import TurnUpTimeGraphError
from turn_up_time_graph.ledger import load_ledger
from turn_up_time_graph.operations import apply_operation

from .test_runtime_flow import _ledger


@pytest.fixture
def legacy(tmp_path):
    repo = tmp_path / "repo"
    project = repo / ".claude/projects/pilot"
    project.mkdir(parents=True)
    value = _ledger()
    value.update(stage="BUILD", spawn_budget={"limit": 75, "used": 75})
    value["stage_history"][-1]["stage"] = "BUILD"
    value["spawn_log"] = [{"id": f"work-{i}", "role": "builder", "role_class": "production",
                           "stage": "BUILD", "reason": "seeded consumed work", "started_at": None,
                           "completed_at": None, "outcome": "CANCELLED" if i % 2 else "FAILED", "artifact_refs": []}
                          for i in range(75)]
    value["decisions"] = [{"id": name, "owner": "human", "question": "prior authority",
                           "status": "WITHDRAWN" if name.startswith("HD") else "OPEN",
                           "resolution": "historical; withdrawn" if name.startswith("HD") else None,
                           "decided_at": None, "artifact_refs": []}
                          for name in ("HD-82", "HD-83", "Q-18", "Q-19")]
    value["risks"] = [{"id": f"risk-{severity}", "description": "retained risk", "severity": severity,
                       "owner": "human", "status": "OPEN", "mitigation": None}
                      for severity in ("HIGH", "MEDIUM", "LOW", "CRITICAL", "low")]
    (project / "project-ledger.json").write_text(tx.ledger_text(value))
    (project / "events.jsonl").write_text('{"event_id":"historical-failure","status":"RED"}\n')
    (project / "definition-of-good.json").write_text('{"schema_version":3,"status":"APPROVED"}\n')
    (project / "integration").mkdir()
    (project / "integration/pre-build-verdict.json").write_text('{"status":"SEAMS_BLOCKED"}\n')
    for path in (project / ".runtime/operations.sqlite", repo / ".claude/runtime/turn-up-time-checkpoints.sqlite"):
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE preserved (id INTEGER PRIMARY KEY, data TEXT)")
            connection.execute("INSERT INTO preserved VALUES (1, 'prior failure and consumption')")
    return repo, project, value


def migration_data(repo, project):
    backup = backup_project(repo, project, "before-repair")
    return {"profile": PROFILE, "expected_ledger_sha256": backup["ledger_sha256"],
            "backup_ref": backup["backup_ref"], "backup_sha256": backup["backup_sha256"]}


def decision(project, value, **overrides):
    receipt = {"status": "OWNER_APPROVED_IN_CONVERSATION", "ownerMessage": "Approved!",
               "authorization": {"project_id": "pilot", "operation": "amend_spawn_budget",
                                 "old_limit": 75, "new_limit": 85}, **overrides}
    (project / "owner.json").write_text(json.dumps(receipt))
    sha = hashlib.sha256((project / "owner.json").read_bytes()).hexdigest()
    value["artifacts"]["owner.json"] = {"path": "owner.json", "status": "CURRENT", "sha256": sha, "schema": None}
    return {"expected_limit": 75, "new_limit": 85, "reason": "owner-approved bounded continuation",
            "owner_decision_ref": "owner.json", "owner_decision_sha256": sha}


def test_plan_does_not_write_and_only_known_severities_change(legacy):
    repo, project, before = legacy
    original = (project / "project-ledger.json").read_bytes()
    plan = compatibility_plan(project)
    assert len(plan["changes"]) == 4
    assert (project / "project-ledger.json").read_bytes() == original
    data = migration_data(repo, project)
    after = apply_operation(repo, project, copy.deepcopy(before), "migrate_ledger_compatibility", data)
    expected = copy.deepcopy(before)
    for risk in expected["risks"]:
        risk["severity"] = risk["severity"].lower()
    assert after == expected
    assert after["decisions"][0]["status"] == "WITHDRAWN"
    assert [row["status"] for row in after["decisions"][2:]] == ["OPEN", "OPEN"]
    assert (project / "definition-of-good.json").read_text() == '{"schema_version":3,"status":"APPROVED"}\n'
    # Applying to a proposed in-memory ledger is still a side-effect-free preflight.
    assert (project / "project-ledger.json").read_bytes() == original


@pytest.mark.parametrize("mutation", ["ledger", "events", "artifact", "journal", "checkpoint", "backup", "inventory", "backup-symlink", "manifest-symlink"])
def test_backup_rejects_changes_and_omissions(legacy, mutation):
    repo, project, before = legacy
    data = migration_data(repo, project)
    manifest_path = project / data["backup_ref"]
    manifest = json.loads(manifest_path.read_text())
    if mutation in {"ledger", "events", "artifact"}:
        name = {"ledger": "project-ledger.json", "events": "events.jsonl", "artifact": "definition-of-good.json"}[mutation]
        with (project / name).open("a") as handle:
            handle.write(" ")
    elif mutation in {"journal", "checkpoint"}:
        source = project / ".runtime/operations.sqlite" if mutation == "journal" else repo / ".claude/runtime/turn-up-time-checkpoints.sqlite"
        with sqlite3.connect(source) as connection:
            connection.execute("INSERT INTO preserved VALUES (2, 'unbacked later state')")
    elif mutation == "backup":
        backup = project / manifest["files"][0]["path"]
        backup.chmod(0o644)
        backup.write_text("changed")
    elif mutation == "backup-symlink":
        row = next(row for row in manifest["files"] if row["source"] == "project/definition-of-good.json")
        backup = project / row["path"]
        backup.unlink()
        backup.symlink_to(project / "definition-of-good.json")
    elif mutation == "manifest-symlink":
        twin = manifest_path.parent / "twin.json"
        twin.write_bytes(manifest_path.read_bytes())
        manifest_path.unlink()
        manifest_path.symlink_to(twin)
    else:
        manifest["files"].pop()
        manifest_path.chmod(0o644)
        manifest_path.write_text(json.dumps(manifest))
        data["backup_sha256"] = tx.file_sha(manifest_path)
    with pytest.raises(TurnUpTimeGraphError):
        apply_operation(repo, project, copy.deepcopy(before), "migrate_ledger_compatibility", data)


def test_backup_never_overwrites_and_sqlite_wal_is_captured(legacy):
    repo, project, _ = legacy
    journal = project / ".runtime/operations.sqlite"
    with sqlite3.connect(journal) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("INSERT INTO preserved VALUES (2, 'committed WAL data')")
        connection.commit()
        backup = backup_project(repo, project, "wal-proof")
        manifest = verify_backup(repo, project, backup["backup_ref"], backup["backup_sha256"])
        row = next(row for row in manifest["files"] if row["source"] == "project/.runtime/operations.sqlite")
        with sqlite3.connect(project / row["path"]) as copied:
            assert copied.execute("SELECT data FROM preserved WHERE id=2").fetchone()[0] == "committed WAL data"
    with pytest.raises(TurnUpTimeGraphError, match="already exists"):
        backup_project(repo, project, "wal-proof")


@pytest.mark.parametrize("bad", ["unknown", "wrong-version", "no-changes", "extra-field", "missing-field"])
def test_compatibility_is_narrow_and_strict(legacy, bad):
    repo, project, value = legacy
    if bad in {"unknown", "wrong-version", "no-changes"}:
        if bad == "unknown":
            value["risks"][0]["severity"] = "URGENT"
        elif bad == "wrong-version":
            value["schema_version"] = 1
        else:
            for risk in value["risks"]:
                risk["severity"] = risk["severity"].lower()
        (project / "project-ledger.json").write_text(tx.ledger_text(value))
    data = migration_data(repo, project)
    if bad == "extra-field":
        data["stage"] = "RELEASE"
    if bad == "missing-field":
        del data["backup_ref"]
    with pytest.raises(TurnUpTimeGraphError):
        apply_operation(repo, project, value, "migrate_ledger_compatibility", data)


def test_budget_amendment_preserves_every_other_field(legacy):
    repo, project, value = legacy
    data = decision(project, value)
    original = copy.deepcopy(value)
    result = apply_operation(repo, project, value, "amend_spawn_budget", data)
    expected = copy.deepcopy(original)
    expected["spawn_budget"]["limit"] = 85
    assert result == expected
    assert result["spawn_budget"]["used"] == 75


@pytest.mark.parametrize("bad", ["unregistered", "not-current", "changed-bytes", "wrong-hash", "no-authorization",
                                  "pending", "wrong-project", "wrong-operation", "wrong-new", "wrong-old", "blank-message",
                                  "bool", "decrease", "same", "huge", "extra-field", "missing-field"])
def test_budget_amendment_requires_exact_explicit_authority(legacy, bad):
    repo, project, value = legacy
    data = decision(project, value)
    if bad == "unregistered":
        value["artifacts"].clear()
    elif bad == "not-current":
        value["artifacts"]["owner.json"]["status"] = "SUPERSEDED"
    elif bad == "changed-bytes":
        (project / "owner.json").write_text("{}")
    elif bad == "wrong-hash":
        data["owner_decision_sha256"] = "0" * 64
    elif bad in {"no-authorization", "pending", "wrong-project", "wrong-operation", "wrong-new", "wrong-old", "blank-message"}:
        receipt = json.loads((project / "owner.json").read_text())
        if bad == "no-authorization":
            receipt["authorization"] = None
        elif bad == "pending":
            receipt["status"] = "PROPOSED_NOT_APPROVED"
        elif bad == "blank-message":
            receipt["ownerMessage"] = " "
        else:
            field, new = {"wrong-project": ("project_id", "another"), "wrong-operation": ("operation", "release"),
                          "wrong-new": ("new_limit", 100), "wrong-old": ("old_limit", 74)}[bad]
            receipt["authorization"][field] = new
        data = decision(project, value, **receipt)
    else:
        if bad == "bool": data["expected_limit"] = True
        if bad == "decrease": data["new_limit"] = 74
        if bad == "same": data["new_limit"] = 75
        if bad == "huge": data["new_limit"] = 2**31
        if bad == "extra-field": data["used"] = 0
        if bad == "missing-field": del data["owner_decision_ref"]
    original = copy.deepcopy(value)
    with pytest.raises(TurnUpTimeGraphError):
        apply_operation(repo, project, value, "amend_spawn_budget", data)
    assert value == original


@pytest.mark.parametrize("boundary", ["atomic_text", "append_event"])
def test_budget_journal_recovery_replay_and_conflict_preserve_consumption(legacy, boundary):
    repo, project, value = legacy
    data = decision(project, value)
    (project / "project-ledger.json").write_text(tx.ledger_text(value))
    before = tx.file_sha(project / "project-ledger.json")
    request = {"event": "amend_spawn_budget", "event_id": "owner-amend", "data": data}
    def prepare():
        after = apply_operation(repo, project, load_ledger(project), request["event"], data)
        return after, {"event_id": request["event_id"], "trigger": request["event"]}, {"stage": "BUILD", "loop_counts": {}}
    with patch.object(tx, boundary, side_effect=RuntimeError("process death")):
        with pytest.raises(RuntimeError):
            tx.execute(project, request, before, None, prepare)
    update = tx.replay(project, before, None)
    assert update["stage"] == "BUILD"
    assert load_ledger(project)["spawn_budget"] == {"limit": 85, "used": 75}
    assert load_ledger(project)["spawn_log"] == value["spawn_log"]
    assert tx.lookup(project, request["event_id"], request) == update
    with pytest.raises(TurnUpTimeGraphError, match="different request"):
        tx.lookup(project, request["event_id"], dict(request, data=dict(data, new_limit=100)))
    assert len([json.loads(line) for line in (project / "events.jsonl").read_text().splitlines()
                if json.loads(line)["event_id"] == request["event_id"]]) == 1


def test_writer_lock_rejects_parallel_amendment(legacy):
    repo, project, value = legacy
    data = decision(project, value)
    with tx.writer_lock(project), pytest.raises(TurnUpTimeGraphError, match="writer is busy"):
        tx.execute(project, {"event_id": "parallel", "data": data}, tx.file_sha(project / "project-ledger.json"), None,
                   lambda: pytest.fail("parallel mutation ran"))
    assert load_ledger(project)["spawn_budget"] == {"limit": 75, "used": 75}


def test_withdrawn_is_semantically_distinct_from_resolved(legacy):
    from pathlib import Path
    schema = json.loads((Path(__file__).parents[2] / ".claude/schemas/project-ledger.schema.json").read_text())
    _, _, value = legacy
    for risk in value["risks"]: risk["severity"] = risk["severity"].lower()
    assert not list(Draft202012Validator(schema).iter_errors(value))
    assert not [row for row in value["decisions"] if row["status"] == "RESOLVED"]
    assert value["approvals"] == []
