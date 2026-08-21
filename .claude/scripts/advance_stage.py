#!/usr/bin/env python3
"""Advance the authoritative project ledger only after target-stage validation passes."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ALLOWED = {
    "INTAKE": {"DISCOVERY", "BLOCKED"},
    "DISCOVERY": {"EVIDENCE_REVIEW", "BLOCKED"},
    "EVIDENCE_REVIEW": {"DEFINITION", "DISCOVERY", "BLOCKED"},
    "DEFINITION": {"TICKETING", "EVIDENCE_REVIEW", "BLOCKED"},
    "TICKETING": {"SEAM_REVIEW", "DEFINITION", "BLOCKED"},
    "SEAM_REVIEW": {"BUILD", "TICKETING", "BLOCKED"},
    "BUILD": {"INTEGRATION", "TICKETING", "BLOCKED"},
    "INTEGRATION": {"CLOSEOUT", "BUILD", "DEFINITION", "BLOCKED"},
    "CLOSEOUT": {"RELEASE", "BUILD", "BLOCKED"},
    "RELEASE": {"WORKFLOW_CLOSEOUT", "DONE", "BUILD", "BLOCKED"},
    "WORKFLOW_CLOSEOUT": {"DONE", "BLOCKED"},
    "BLOCKED": {"INTAKE", "DISCOVERY", "EVIDENCE_REVIEW", "DEFINITION", "TICKETING", "SEAM_REVIEW", "BUILD", "INTEGRATION", "CLOSEOUT", "RELEASE", "WORKFLOW_CLOSEOUT"},
    "DONE": set(),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--to", required=True)
    parser.add_argument("--status", default="ACTIVE")
    parser.add_argument("--build-identity")
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    candidate = Path(args.project)
    project_root = candidate.resolve() if candidate.exists() else repo_root / ".claude" / "projects" / args.project
    ledger_path = project_root / "project-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    current = ledger["stage"]
    target = args.to.upper()
    if target not in ALLOWED.get(current, set()):
        raise SystemExit(f"Illegal stage transition: {current} -> {target}")

    original = ledger_path.read_text(encoding="utf-8")
    ledger["stage"] = target
    ledger["status"] = args.status.upper()
    if args.build_identity:
        ledger["build_identity"] = args.build_identity
    ledger["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")

    validator = Path(__file__).with_name("validate_project.py")
    result = subprocess.run([sys.executable, str(validator), str(project_root), "--repo-root", str(repo_root)], text=True, capture_output=True)
    if result.returncode != 0:
        ledger_path.write_text(original, encoding="utf-8")
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        print(f"STAGE NOT ADVANCED: {current} -> {target}")
        return result.returncode

    sys.stdout.write(result.stdout)
    print(f"STAGE ADVANCED: {current} -> {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
