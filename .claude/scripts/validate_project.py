#!/usr/bin/env python3
"""Validate project artifacts and the prerequisites for a stage transition."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


CLAUDE_DIR = Path(__file__).resolve().parents[1]
SCHEMAS = CLAUDE_DIR / "schemas"


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_file(path: Path, schema_name: str, errors: list[str]) -> Any | None:
    if not path.is_file():
        errors.append(f"MISSING {path}")
        return None
    try:
        value = load(path)
        schema = load(SCHEMAS / schema_name)
        validation_errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.path))
        for error in validation_errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            errors.append(f"INVALID {path}:{location}: {error.message}")
        return value
    except Exception as exc:
        errors.append(f"UNREADABLE {path}: {exc}")
        return None


def artifact_status(project: Path, relative: str, schema: str, errors: list[str]) -> Any | None:
    return validate_file(project / relative, schema, errors)


def validate_transition(project: Path, stage: str, errors: list[str]) -> None:
    ledger = artifact_status(project, "project-ledger.json", "project-ledger.schema.json", errors)
    if not ledger:
        return
    if ledger.get("project_id") != project.name:
        errors.append(f"LEDGER project_id={ledger.get('project_id')} does not match directory {project.name}")
    if ledger.get("spawn_budget", {}).get("used", 0) > ledger.get("spawn_budget", {}).get("limit", 0):
        errors.append("SPAWN_BUDGET_EXCEEDED")

    order = ["INTAKE", "DISCOVERY", "EVIDENCE_REVIEW", "DEFINITION", "TICKETING", "SEAM_REVIEW", "BUILD", "INTEGRATION", "CLOSEOUT", "RELEASE", "WORKFLOW_CLOSEOUT", "DONE"]
    target_index = order.index(stage)

    if target_index >= order.index("DISCOVERY"):
        intake = artifact_status(project, "intake-readiness.json", "intake-readiness.schema.json", errors)
        if intake and intake.get("status") not in {"READY", "READY_WITH_DEFERRED_RISK"}:
            errors.append(f"INTAKE_NOT_READY status={intake.get('status')}")

    if target_index >= order.index("EVIDENCE_REVIEW"):
        expected = ["product.json"]
        profile = ledger.get("profile")
        expected += ["combined-engineering.json"] if profile == "lite" else ["frontend.json", "backend.json", "security.json"]
        for filename in expected:
            artifact_status(project, f"evidence/{filename}", "evidence-pack.schema.json", errors)

    if target_index >= order.index("DEFINITION"):
        verdict = artifact_status(project, "evidence/premise-verdict.json", "premise-verdict.schema.json", errors)
        if verdict and verdict.get("status") != "EVIDENCE_READY":
            errors.append("PREMISE_VERDICT_NOT_READY")

    if target_index >= order.index("TICKETING"):
        definition = artifact_status(project, "definition-of-good.json", "definition-of-good.schema.json", errors)
        if definition and definition.get("status") != "APPROVED":
            errors.append("DEFINITION_NOT_APPROVED")

    tickets: list[dict[str, Any]] = []
    if target_index >= order.index("SEAM_REVIEW"):
        paths = sorted((project / "tickets").glob("*.json"))
        if not paths:
            errors.append("NO_TICKETS")
        for path in paths:
            ticket = validate_file(path, "ticket.schema.json", errors)
            if isinstance(ticket, dict):
                tickets.append(ticket)
                if ticket.get("status") not in {"APPROVED", "IN_PROGRESS", "EVIDENCE_GREEN"}:
                    errors.append(f"TICKET_NOT_APPROVED {path.name} status={ticket.get('status')}")
        owners: dict[str, str] = {}
        for ticket in tickets:
            for filename in ticket.get("owned_files", []):
                prior = owners.get(filename)
                if prior and prior != ticket.get("ticket_id"):
                    errors.append(f"OVERLAPPING_FILE_OWNERSHIP {filename}: {prior} and {ticket.get('ticket_id')}")
                owners[filename] = str(ticket.get("ticket_id"))

    if target_index >= order.index("BUILD"):
        seam = artifact_status(project, "integration/pre-build-verdict.json", "seam-verdict.schema.json", errors)
        if seam and (seam.get("phase") != "PRE_BUILD" or seam.get("status") != "SEAMS_SOUND"):
            errors.append("PRE_BUILD_SEAMS_NOT_SOUND")

    if target_index >= order.index("INTEGRATION"):
        for ticket in tickets:
            if ticket.get("status") != "EVIDENCE_GREEN" or ticket.get("build_receipt") is None:
                errors.append(f"TICKET_NOT_EVIDENCE_GREEN {ticket.get('ticket_id')}")

    if target_index >= order.index("CLOSEOUT"):
        seam = artifact_status(project, "integration/post-build-verdict.json", "seam-verdict.schema.json", errors)
        if seam and (seam.get("phase") != "POST_BUILD" or seam.get("status") != "SEAMS_SOUND"):
            errors.append("POST_BUILD_SEAMS_NOT_SOUND")

    if target_index >= order.index("RELEASE"):
        closeout = project / "closeout" / "terminal-state.json"
        if not closeout.is_file():
            errors.append(f"MISSING {closeout}")
        verdict = artifact_status(project, "release/release-verdict.json", "release-verdict.schema.json", errors)
        if verdict and verdict.get("status") not in {"SHIP", "SHIP_WITH_ACCEPTED_RISK"}:
            errors.append("RELEASE_BLOCKED")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--stage", required=True, choices=["INTAKE", "DISCOVERY", "EVIDENCE_REVIEW", "DEFINITION", "TICKETING", "SEAM_REVIEW", "BUILD", "INTEGRATION", "CLOSEOUT", "RELEASE", "WORKFLOW_CLOSEOUT", "DONE"])
    args = parser.parse_args()
    errors: list[str] = []
    validate_transition(args.project.resolve(), args.stage, errors)
    if errors:
        print("PROJECT VALIDATION: RED")
        for error in errors:
            print(f" - {error}")
        return 1
    print(f"PROJECT VALIDATION: GREEN stage={args.stage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
