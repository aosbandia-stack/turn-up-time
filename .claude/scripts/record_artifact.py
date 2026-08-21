#!/usr/bin/env python3
"""Hash one project artifact and record it in the authoritative ledger."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("name")
    parser.add_argument("artifact")
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    candidate = Path(args.project)
    project_root = candidate.resolve() if candidate.exists() else repo_root / ".claude" / "projects" / args.project
    ledger_path = project_root / "project-ledger.json"
    artifact_path = (project_root / args.artifact).resolve()
    try:
        artifact_path.relative_to(project_root.resolve())
    except ValueError:
        raise SystemExit("Artifact must live inside the project workspace")
    if not artifact_path.is_file():
        raise SystemExit(f"Artifact not found: {artifact_path}")

    digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger.setdefault("artifacts", {})[args.name] = {
        "path": str(artifact_path.relative_to(project_root)).replace("\\", "/"),
        "sha256": digest,
    }
    ledger["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ARTIFACT_RECORDED", "name": args.name, "sha256": digest}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
