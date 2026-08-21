#!/usr/bin/env python3
"""Validate one Turn Up Time project workspace and its stage prerequisites."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:
    raise SystemExit("jsonschema is required: python -m pip install jsonschema") from exc

CLAUDE_DIR = Path(__file__).resolve().parents[1]
SCHEMA_DIR = CLAUDE_DIR / "schemas"
STAGE_ORDER = [
    "INTAKE", "DISCOVERY", "EVIDENCE_REVIEW", "DEFINITION", "TICKETING", "SEAM_REVIEW",
    "BUILD", "INTEGRATION", "CLOSEOUT", "RELEASE", "WORKFLOW_CLOSEOUT", "DONE"
]


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_file(path: Path, schema_name: str, errors: list[str]) -> object | None:
    if not path.exists():
        errors.append(f"missing {path}")
        return None
    try:
        value = load_json(path)
    except Exception as exc:
        errors.append(f"invalid JSON {path}: {exc}")
        return None
    schema = load_json(SCHEMA_DIR / schema_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for error in sorted(validator.iter_errors(value), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{path}: {location}: {error.message}")
    return value


def at_or_after(stage: str, threshold: str) -> bool:
    if stage == "BLOCKED":
        return False
    return STAGE_ORDER.index(stage) >= STAGE_ORDER.index(threshold)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def load_verdict(path: Path, expected_kind: str, allowed: set[str], errors: list[str]) -> dict | None:
    value = validate_file(path, "stage-verdict.schema.json", errors)
    if isinstance(value, dict):
        if value.get("kind") != expected_kind:
            errors.append(f"{path}: kind must be {expected_kind}")
        if value.get("status") not in allowed:
            errors.append(f"{path}: status {value.get('status')} not in {sorted(allowed)}")
        return value
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", help="Project directory or project ID under .claude/projects")
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    candidate = Path(args.project)
    project_root = candidate.resolve() if candidate.exists() else repo_root / ".claude" / "projects" / args.project
    errors: list[str] = []

    ledger = validate_file(project_root / "project-ledger.json", "project-ledger.schema.json", errors)
    intake = validate_file(project_root / "intake-readiness.json", "intake-readiness.schema.json", errors)
    if not isinstance(ledger, dict):
        print("PROJECT VALIDATION: RED")
        for error in errors:
            print(" -", error)
        return 1

    stage = ledger["stage"]
    status = ledger["status"]

    if at_or_after(stage, "DISCOVERY") and isinstance(intake, dict):
        if intake.get("status") not in ("INTAKE_READY", "INTAKE_READY_WITH_DEFERRED_RISK"):
            errors.append(f"stage {stage} requires a ready intake card, got {intake.get('status')}")

    evidence_files = sorted(path for path in (project_root / "evidence").glob("*.json") if path.name != "premise-verdict.json")
    evidence_values: list[dict] = []
    for path in evidence_files:
        value = validate_file(path, "evidence-pack.schema.json", errors)
        if isinstance(value, dict):
            evidence_values.append(value)

    if at_or_after(stage, "EVIDENCE_REVIEW") and not evidence_files:
        errors.append(f"stage {stage} requires discovery evidence files")

    premise_path = project_root / "evidence" / "premise-verdict.json"
    if at_or_after(stage, "DEFINITION"):
        premise = load_verdict(premise_path, "premise", {"EVIDENCE_READY"}, errors)
        if premise is not None and any(pack.get("status") != "EVIDENCE_READY" for pack in evidence_values):
            errors.append("premise verdict cannot be EVIDENCE_READY while a lane is not ready")

    definition_path = project_root / "definition-of-good.json"
    definition = None
    if at_or_after(stage, "TICKETING") or definition_path.exists():
        definition = validate_file(definition_path, "definition-of-good.schema.json", errors)

    ticket_files = sorted((project_root / "tickets").glob("*.json"))
    tickets: list[dict] = []
    for path in ticket_files:
        value = validate_file(path, "ticket.schema.json", errors)
        if isinstance(value, dict):
            tickets.append(value)

    if at_or_after(stage, "SEAM_REVIEW"):
        if not isinstance(definition, dict) or definition.get("status") != "APPROVED":
            errors.append(f"stage {stage} requires an APPROVED Definition of Good")
        if not tickets:
            errors.append(f"stage {stage} requires one or more executable tickets")
        for ticket in tickets:
            if ticket.get("status") not in ("APPROVED", "IN_PROGRESS", "TICKET_EVIDENCE_GREEN", "BLOCKED"):
                errors.append(f"stage {stage} cannot consume ticket {ticket.get('ticket_id')} with status {ticket.get('status')}")

    if at_or_after(stage, "BUILD"):
        load_verdict(project_root / "integration" / "prebuild-verdict.json", "prebuild-integration", {"SEAMS_SOUND"}, errors)

    if at_or_after(stage, "INTEGRATION"):
        non_green = [ticket.get("ticket_id") for ticket in tickets if ticket.get("status") != "TICKET_EVIDENCE_GREEN"]
        if non_green:
            errors.append(f"stage {stage} requires all tickets evidence-green; not green: {non_green}")

    if at_or_after(stage, "CLOSEOUT"):
        load_verdict(project_root / "integration" / "postbuild-verdict.json", "postbuild-integration", {"SEAMS_SOUND"}, errors)

    if at_or_after(stage, "RELEASE"):
        load_verdict(
            project_root / "closeout" / "verdict.json",
            "product-closeout",
            {"RELEASE_READY", "YELLOW_ACCEPTANCE_REQUIRED"},
            errors,
        )
        load_verdict(
            project_root / "release" / "production-audit.json",
            "production-audit",
            {"SHIP", "SHIP_WITH_ACCEPTED_RISK"},
            errors,
        )
        load_verdict(project_root / "release" / "final-judge.json", "fresh-release-judge", {"GREEN"}, errors)

    if stage == "DONE":
        load_verdict(project_root / "release" / "receipt.json", "release", {"RELEASED", "NOT_RELEASED"}, errors)

    for artifact_name, receipt in ledger.get("artifacts", {}).items():
        if not isinstance(receipt, dict):
            continue
        path = project_root / receipt.get("path", "")
        expected = receipt.get("sha256")
        if not path.exists():
            errors.append(f"ledger artifact {artifact_name} points to missing {path}")
        elif expected and sha256(path) != expected:
            errors.append(f"ledger artifact hash drift: {artifact_name} ({path})")

    if ledger.get("spawn_count", 0) != len(ledger.get("spawn_log", [])):
        errors.append("spawn_count does not equal the number of spawn_log records")
    if ledger.get("spawn_count", 0) > ledger.get("spawn_budget", 0):
        errors.append("spawn budget exceeded without an increased recorded budget")

    if errors:
        print("PROJECT VALIDATION: RED")
        for error in errors:
            print(" -", error)
        return 1

    print("PROJECT VALIDATION: GREEN")
    print(f" project={ledger['project_id']} stage={stage} status={status} tickets={len(ticket_files)} evidence={len(evidence_files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
