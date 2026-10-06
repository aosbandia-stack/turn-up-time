#!/usr/bin/env python3
"""Create a schema-valid Tier C workspace without resetting an existing ledger."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("--profile", choices=["lite", "standard", "full"], default="standard")
    parser.add_argument("--objective", default="")
    parser.add_argument("--root", type=Path, default=Path.cwd() / ".claude" / "projects")
    parser.add_argument("--spawn-budget", type=int, help="whole-project ceiling, including all roles and repairs; ratified at intake")
    parser.add_argument("--force", action="store_true", help="reuse an empty directory only; never overwrite a ledger")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", args.project_id):
        parser.error("project_id must be one safe directory name, not a path")
    if args.spawn_budget is not None and args.spawn_budget < 0:
        parser.error("spawn budget cannot be negative")
    root = args.root.resolve()
    project = root / args.project_id
    if project.is_symlink():
        raise SystemExit("Project workspace must not be a symlink")
    if (project / "project-ledger.json").exists() or (project / ".runtime").exists():
        raise SystemExit(f"Existing project state is never overwritten; inspect/recover {project}")
    if project.exists() and (not args.force or any(project.iterdir())):
        raise SystemExit(f"Project workspace already exists: {project}")
    project.mkdir(parents=True, exist_ok=True)
    for name in ("evidence", "tickets", "receipts", "integration", "closeout", "release", "improvements", "requests", "approvals"):
        (project / name).mkdir(exist_ok=True)
    now = utc_now()
    # Preserve legacy profile defaults, but allow an explicitly planned total.
    budget = args.spawn_budget if args.spawn_budget is not None else {"lite": 3, "standard": 5, "full": 8}[args.profile]
    ledger = {
        "schema_version": 2, "project_id": args.project_id, "tier": "C", "profile": args.profile,
        "stage": "INTAKE", "status": "ACTIVE", "objective": args.objective,
        "spawn_budget": {"limit": budget, "used": 0}, "spawn_log": [], "decisions": [],
        "risks": [], "blockers": [], "artifacts": {}, "approvals": [],
        "stage_history": [{"stage": "INTAKE", "entered_at": now, "exited_at": None, "verdict": None, "receipt_refs": []}],
        "build_identity": None,
    }
    intake = {
        "schema_version": 1, "project_id": args.project_id, "status": "DRAFT",
        "primary_user": "", "primary_job": "", "desired_outcome": "", "product_boundary": "",
        "permitted_actions": [], "prohibited_actions": [], "critical_constraints": [],
        "non_goals": [], "human_owned_decisions": [], "deferred_risks": [],
    }
    write_json(project / "project-ledger.json", ledger)
    write_json(project / "intake-readiness.json", intake)
    print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
