#!/usr/bin/env python3
"""Create a schema-valid Tier C project workspace."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("--profile", choices=["lite", "standard", "full"], default="standard")
    parser.add_argument("--objective", default="")
    parser.add_argument("--root", type=Path, default=Path.cwd() / ".claude" / "projects")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project = args.root / args.project_id
    if project.exists() and not args.force:
        raise SystemExit(f"Project workspace already exists: {project}")
    project.mkdir(parents=True, exist_ok=True)
    for name in ("evidence", "tickets", "receipts", "integration", "closeout", "release", "improvements"):
        (project / name).mkdir(exist_ok=True)

    now = utc_now()
    budget = {"lite": 3, "standard": 5, "full": 8}[args.profile]
    ledger = {
        "schema_version": 2,
        "project_id": args.project_id,
        "tier": "C",
        "profile": args.profile,
        "stage": "INTAKE",
        "status": "ACTIVE",
        "objective": args.objective,
        "spawn_budget": {"limit": budget, "used": 0},
        "spawn_log": [],
        "decisions": [],
        "risks": [],
        "blockers": [],
        "artifacts": {},
        "approvals": [],
        "stage_history": [{"stage": "INTAKE", "entered_at": now, "exited_at": None, "verdict": None, "receipt_refs": []}],
        "build_identity": None,
    }
    intake = {
        "schema_version": 1,
        "project_id": args.project_id,
        "status": "DRAFT",
        "primary_user": "",
        "primary_job": "",
        "desired_outcome": "",
        "product_boundary": "",
        "permitted_actions": [],
        "prohibited_actions": [],
        "critical_constraints": [],
        "non_goals": [],
        "human_owned_decisions": [],
        "deferred_risks": [],
    }
    write_json(project / "project-ledger.json", ledger)
    write_json(project / "intake-readiness.json", intake)
    print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
