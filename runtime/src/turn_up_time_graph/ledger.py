from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .events import utc_now
from .exceptions import TurnUpTimeGraphError
from .topology import Transition

LEDGER_NAME = "project-ledger.json"


def _ledger_path(project_dir: Path) -> Path:
    return Path(project_dir) / LEDGER_NAME


def load_ledger(project_dir: Path) -> dict[str, Any]:
    path = _ledger_path(project_dir)
    if not path.is_file():
        raise TurnUpTimeGraphError(f"project ledger not found: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TurnUpTimeGraphError(f"unable to read project ledger {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TurnUpTimeGraphError(f"project ledger must be a JSON object: {path}")
    for key in ("project_id", "profile", "stage", "status", "stage_history", "approvals"):
        if key not in value:
            raise TurnUpTimeGraphError(f"project ledger is missing {key}: {path}")
    return value


def ledger_sha256(project_dir: Path) -> str:
    path = _ledger_path(project_dir)
    if not path.is_file():
        raise TurnUpTimeGraphError(f"project ledger not found: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    data = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def apply_transition_to_ledger(
    project_dir: Path,
    transition: Transition,
    *,
    event_id: str,
    approved_by: str | None,
    receipt_refs: list[str],
) -> dict[str, Any]:
    ledger = load_ledger(project_dir)
    current = ledger.get("stage")
    if current != transition.source.value:
        raise TurnUpTimeGraphError(
            f"ledger stage drift: expected {transition.source.value}, found {current}"
        )

    now = utc_now()
    history = ledger.setdefault("stage_history", [])
    if not isinstance(history, list):
        raise TurnUpTimeGraphError("ledger stage_history must be an array")
    open_rows = [row for row in history if isinstance(row, dict) and row.get("exited_at") is None]
    if len(open_rows) != 1 or open_rows[0].get("stage") != transition.source.value:
        raise TurnUpTimeGraphError(
            f"ledger must have exactly one open history row for {transition.source.value}"
        )
    open_rows[0]["exited_at"] = now
    open_rows[0]["verdict"] = transition.verdict
    open_rows[0]["receipt_refs"] = list(receipt_refs)

    ledger["stage"] = transition.target.value
    ledger["status"] = transition.status
    history.append(
        {
            "stage": transition.target.value,
            "entered_at": now,
            "exited_at": None,
            "verdict": None,
            "receipt_refs": [],
        }
    )

    if transition.human_gate:
        approvals = ledger.setdefault("approvals", [])
        if not isinstance(approvals, list):
            raise TurnUpTimeGraphError("ledger approvals must be an array")
        approvals.append(
            {
                "gate": transition.human_gate,
                "status": "APPROVED",
                "by": approved_by,
                "at": now,
                "notes": f"graph event {event_id}",
            }
        )

    _write_atomic(_ledger_path(project_dir), ledger)
    return ledger
