"""Bookkeeping operations change metadata, never stage or approval authority."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .events import utc_now
from .exceptions import TurnUpTimeGraphError
from .workspace import build_identity, project_file

OPERATIONS = frozenset({"record_artifact", "reserve_spawn", "complete_spawn", "set_build_identity"})


def _required(data: dict[str, Any], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str) or not value.strip():
        raise TurnUpTimeGraphError(f"operation requires nonempty {name}")
    return value


def apply_operation(repo: Path, project: Path, ledger: dict[str, Any], event: str, data: dict[str, Any]) -> dict[str, Any]:
    if event not in OPERATIONS:
        raise TurnUpTimeGraphError(f"unknown control operation: {event}")
    allowed = {
        "record_artifact": {"path", "schema"},
        "reserve_spawn": {"spawn_id", "role_class", "role", "reason"},
        "complete_spawn": {"spawn_id", "outcome", "artifact_refs"},
        "set_build_identity": set(),
    }
    if not isinstance(data, dict) or set(data) - allowed[event]:
        raise TurnUpTimeGraphError("unsupported control operation fields")
    if event == "record_artifact":
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
