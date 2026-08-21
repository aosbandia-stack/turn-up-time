#!/usr/bin/env python3
"""Create a complete Tier C Turn Up Time project workspace."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


def git_value(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)
        value = result.stdout.strip()
        return value or None
    except (OSError, subprocess.CalledProcessError):
        return None


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("--profile", choices=("lite", "standard", "full"), default="standard")
    parser.add_argument("--objective", default="")
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    project_root = repo_root / ".claude" / "projects" / args.project_id
    if project_root.exists():
        raise SystemExit(f"Project already exists: {project_root}")

    project_root.mkdir(parents=True)
    for child in ("evidence", "tickets", "receipts", "integration", "closeout", "release"):
        (project_root / child).mkdir()

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    branch = git_value(repo_root, "branch", "--show-current") or "unknown"
    base_sha = git_value(repo_root, "rev-parse", "HEAD")
    budgets = {"lite": 3, "standard": 5, "full": 8}

    ledger = {
        "$schema": "../../schemas/project-ledger.schema.json",
        "schema_version": 2,
        "project_id": args.project_id,
        "repository": {"root": str(repo_root), "branch": branch, "base_sha": base_sha},
        "tier": "C",
        "profile": args.profile,
        "stage": "INTAKE",
        "status": "ACTIVE",
        "objective": args.objective,
        "created_at": now,
        "updated_at": now,
        "spawn_budget": budgets[args.profile],
        "spawn_count": 0,
        "spawn_log": [],
        "decisions": [],
        "risks": [],
        "blocked_by": [],
        "human_approvals": [],
        "artifacts": {},
        "build_identity": None,
    }
    intake = {
        "$schema": "../../schemas/intake-readiness.schema.json",
        "schema_version": 1,
        "project_id": args.project_id,
        "primary_user": None,
        "primary_job": None,
        "desired_outcome": None,
        "product_boundary": None,
        "critical_constraints": [],
        "human_owned_decisions": [],
        "non_goals": [],
        "status": "DRAFT",
    }

    write_json(project_root / "project-ledger.json", ledger)
    write_json(project_root / "intake-readiness.json", intake)
    (project_root / "PROJECT.md").write_text(
        "# Turn Up Time project\n\n"
        f"- Project ID: `{args.project_id}`\n"
        f"- Profile: `{args.profile}`\n"
        "- Current source of truth: `project-ledger.json`\n\n"
        "Artifacts are created only when their stage begins. Evidence packs go under `evidence/`; "
        "OmniDex later creates `definition-of-good.json`, `architecture.md`, `traceability.json`, "
        "and executable tickets.\n",
        encoding="utf-8",
    )

    print(project_root)
    print("Created: project-ledger.json, intake-readiness.json, six stage directories, PROJECT.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
