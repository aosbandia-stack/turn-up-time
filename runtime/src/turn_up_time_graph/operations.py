"""Bookkeeping operations change metadata, never stage or approval authority."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .events import utc_now
from .exceptions import TurnUpTimeGraphError
from .workspace import build_identity, project_file

OPERATIONS = frozenset({"record_artifact", "reserve_spawn", "complete_spawn", "set_build_identity",
                        "migrate_ledger_compatibility", "amend_spawn_budget"})


def _required(data: dict[str, Any], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str) or not value.strip():
        raise TurnUpTimeGraphError(f"operation requires nonempty {name}")
    return value


def _amend_budget(project: Path, ledger: dict[str, Any], data: dict[str, Any]) -> None:
    old, new = data.get("expected_limit"), data.get("new_limit")
    if (type(old) is not int or type(new) is not int or old < 0 or not old < new <= 2**31 - 1):
        raise TurnUpTimeGraphError("budget amendment requires integer limits with 0 <= old < new <= 2147483647")
    budget = ledger["spawn_budget"]
    if budget["limit"] != old or type(budget["used"]) is not int or not 0 <= budget["used"] <= old:
        raise TurnUpTimeGraphError("budget amendment expected limit or consumed count mismatch")
    _required(data, "reason")
    reference, expected = _required(data, "owner_decision_ref"), _required(data, "owner_decision_sha256")
    path = project_file(project, reference)
    if reference.startswith((".runtime/", "approvals/")) or reference == "project-ledger.json":
        raise TurnUpTimeGraphError("budget amendment requires a controlling owner decision artifact")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    registered = ledger["artifacts"].get(reference, {})
    if (actual != expected or registered.get("sha256") != actual or registered.get("path") != reference
            or registered.get("status") != "CURRENT"):
        raise TurnUpTimeGraphError("owner decision must be registered CURRENT with matching actual hash")
    try:
        decision = json.loads(path.read_text(encoding="utf-8"))
        authorization = {"project_id": ledger["project_id"], "operation": "amend_spawn_budget",
                         "old_limit": old, "new_limit": new}
        if (decision.get("status") != "OWNER_APPROVED_IN_CONVERSATION"
                or not isinstance(decision.get("ownerMessage"), str) or not decision["ownerMessage"].strip()
                or decision.get("authorization") != authorization
                or any(type(decision["authorization"].get(field)) is not int for field in ("old_limit", "new_limit"))):
            raise ValueError("owner decision does not explicitly approve this project and exact amendment")
    except (ValueError, AttributeError, TypeError) as exc:
        raise TurnUpTimeGraphError(f"invalid owner budget decision: {exc}") from exc
    # Conversation evidence is auditable metadata, never a signed stage approval.
    budget["limit"] = new


def apply_operation(repo: Path, project: Path, ledger: dict[str, Any], event: str, data: dict[str, Any]) -> dict[str, Any]:
    if event not in OPERATIONS:
        raise TurnUpTimeGraphError(f"unknown control operation: {event}")
    allowed = {
        "record_artifact": {"path", "schema"},
        "reserve_spawn": {"spawn_id", "role_class", "role", "reason"},
        "complete_spawn": {"spawn_id", "outcome", "artifact_refs"},
        "set_build_identity": set(),
        "migrate_ledger_compatibility": {"profile", "expected_ledger_sha256", "backup_ref", "backup_sha256"},
        "amend_spawn_budget": {"expected_limit", "new_limit", "reason", "owner_decision_ref", "owner_decision_sha256"},
    }
    if not isinstance(data, dict) or set(data) - allowed[event]:
        raise TurnUpTimeGraphError("unsupported control operation fields")
    if event == "migrate_ledger_compatibility":
        from .compatibility import migrate_compatibility
        for field in allowed[event]:
            _required(data, field)
        return migrate_compatibility(repo, project, ledger, data)
    if event == "amend_spawn_budget":
        _amend_budget(project, ledger, data)
    elif event == "record_artifact":
        if data.get("schema") is not None and not isinstance(data["schema"], str):
            raise TurnUpTimeGraphError("schema must be a string or null")
        relative = _required(data, "path")
        if relative == "project-ledger.json" or relative.startswith((".runtime/", "approvals/")):
            raise TurnUpTimeGraphError("runtime internals are not controlling artifacts")
        path = project_file(project, relative)
        ledger["artifacts"][relative] = {
            "path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "status": "CURRENT", "schema": data.get("schema"),
        }
    elif event == "reserve_spawn":
        spawn_id = _required(data, "spawn_id")
        if any(row["id"] == spawn_id for row in ledger["spawn_log"]):
            raise TurnUpTimeGraphError("spawn ID already reserved; retry its original event ID")
        role_class = data.get("role_class")
        if role_class not in {"production", "assurance"}:
            raise TurnUpTimeGraphError("spawn role_class must be production or assurance")
        if role_class == "production" and ledger["stage"] not in {"BUILD", "CLOSEOUT"}:
            raise TurnUpTimeGraphError("production spawn is not permitted in this stage")
        budget = ledger["spawn_budget"]
        if budget["used"] >= budget["limit"]:
            raise TurnUpTimeGraphError("spawn budget exhausted; no worker started")
        role, reason = _required(data, "role"), _required(data, "reason")
        budget["used"] += 1
        ledger["spawn_log"].append({
            "id": spawn_id, "role": role, "role_class": role_class,
            "stage": ledger["stage"], "reason": reason, "started_at": utc_now(),
            "completed_at": None, "outcome": None, "artifact_refs": [],
        })
    elif event == "complete_spawn":
        spawn_id = _required(data, "spawn_id")
        row = next((item for item in ledger["spawn_log"] if item["id"] == spawn_id), None)
        if row is None or row["completed_at"] is not None:
            raise TurnUpTimeGraphError("spawn is missing or already completed")
        outcome = _required(data, "outcome")
        if outcome not in {"SUCCEEDED", "FAILED", "CANCELLED", "TIMED_OUT", "INTERRUPTED"}:
            raise TurnUpTimeGraphError("unsupported spawn outcome")
        refs = data.get("artifact_refs", [])
        if not isinstance(refs, list):
            raise TurnUpTimeGraphError("artifact_refs must be an array")
        for reference in refs:
            project_file(project, reference)
        row.update(completed_at=utc_now(), outcome=outcome, artifact_refs=refs)
    else:
        ledger["build_identity"] = build_identity(repo)
    return ledger
