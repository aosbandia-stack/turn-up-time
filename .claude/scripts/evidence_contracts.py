"""Semantic checks beyond JSON shape. Evidence is project-local and content-addressed.

These checks establish consistency, not that an agent-supplied claim is true. The
trusted runner/verifier must own receipt production; see docs/HARDENING.md.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any


def evidence_file(project: Path, reference: str, errors: list[str]) -> Path | None:
    if not isinstance(reference, str) or not reference.strip():
        errors.append("EVIDENCE_REFERENCE_REQUIRED")
        return None
    # The contract deliberately uses portable, project-relative POSIX paths.
    relative = PurePosixPath(reference)
    if relative.is_absolute() or ".." in relative.parts or "\\" in reference or ":" in reference:
        errors.append(f"UNSAFE_EVIDENCE_PATH {reference}")
        return None
    target = project.joinpath(*relative.parts)
    try:
        target.resolve(strict=True).relative_to(project.resolve(strict=True))
        if not target.is_file():
            raise ValueError("not a regular file")
    except (OSError, ValueError, RuntimeError):
        errors.append(f"MISSING_OR_EXTERNAL_EVIDENCE {reference}")
        return None
    return target


def verify_evidence(project: Path, ref: Any, digest: Any, errors: list[str]) -> None:
    path = evidence_file(project, ref, errors)
    if path is None:
        return
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if not isinstance(digest, str) or actual != digest:
        errors.append(f"EVIDENCE_HASH_MISMATCH {ref}")


def check_ticket_evidence(project: Path, ticket: dict[str, Any], errors: list[str]) -> None:
    """Green requires exactly one independently attributed PASS per acceptance ID."""
    name = ticket.get("ticket_id", "<unknown>")
    receipt = ticket.get("build_receipt")
    if not isinstance(receipt, dict) or not receipt.get("build_identity"):
        errors.append(f"BUILD_RECEIPT_REQUIRED {name}")
        return
    checks = ticket.get("acceptance_checks", [])
    ids = [check.get("id") for check in checks if isinstance(check, dict)]
    if not ids or any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        errors.append(f"INVALID_ACCEPTANCE_IDS {name}")
        return
    results = receipt.get("check_results")
    if not isinstance(results, list) or not results:
        errors.append(f"CHECK_RESULTS_REQUIRED {name}")
        return
    by_id: dict[str, dict[str, Any]] = {}
    for result in results:
        if not isinstance(result, dict):
            errors.append(f"STRUCTURED_CHECK_RESULT_REQUIRED {name}")
            continue
        check_id = result.get("check_id")
        if not isinstance(check_id, str) or check_id not in ids or check_id in by_id:
            errors.append(f"UNKNOWN_OR_DUPLICATE_CHECK_RESULT {name}:{check_id}")
            continue
        by_id[check_id] = result
        if result.get("status") != "PASS":
            errors.append(f"CHECK_NOT_PASS {name}:{check_id}")
        if result.get("build_identity") != receipt["build_identity"]:
            errors.append(f"CHECK_BUILD_MISMATCH {name}:{check_id}")
        if result.get("evaluator_role") != "assurance" or not result.get("evaluator_id"):
            errors.append(f"INDEPENDENT_EVALUATOR_REQUIRED {name}:{check_id}")
        verify_evidence(project, result.get("evidence_ref"), result.get("evidence_sha256"), errors)
    for check in checks:
        if not isinstance(check, dict):
            continue
        result = by_id.get(check.get("id"))
        if result is None:
            errors.append(f"MISSING_CHECK_RESULT {name}:{check.get('id')}")
        elif check.get("evidence") != result.get("evidence_ref"):
            errors.append(f"ACCEPTANCE_EVIDENCE_MISMATCH {name}:{check.get('id')}")


def check_ticket_graph(tickets: list[dict[str, Any]], errors: list[str]) -> None:
    """Validate references/cycles and canonical file ownership before dispatch."""
    by_id: dict[str, dict[str, Any]] = {}
    owners: dict[str, str] = {}
    for ticket in tickets:
        ticket_id = ticket.get("ticket_id")
        if not isinstance(ticket_id, str) or not ticket_id:
            errors.append("TICKET_ID_REQUIRED")
            continue
        if ticket_id in by_id:
            errors.append(f"DUPLICATE_TICKET_ID {ticket_id}")
        by_id[ticket_id] = ticket
        for raw in ticket.get("owned_files", []):
            if not isinstance(raw, str) or not raw or ":" in raw or ".." in PurePosixPath(raw.replace("\\", "/")).parts:
                errors.append(f"UNSAFE_OWNED_FILE {ticket_id}:{raw}")
                continue
            path = PurePosixPath(raw.replace("\\", "/"))
            if path.is_absolute() or str(path) == ".":
                errors.append(f"UNSAFE_OWNED_FILE {ticket_id}:{raw}")
                continue
            # Casefold is intentionally conservative for the supported Windows host.
            canonical = str(path).casefold()
            if canonical in owners and owners[canonical] != ticket_id:
                errors.append(f"OVERLAPPING_FILE_OWNERSHIP {raw}")
            owners[canonical] = ticket_id
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(ticket_id: str) -> None:
        if ticket_id in visiting:
            errors.append(f"TICKET_DEPENDENCY_CYCLE {ticket_id}")
            return
        if ticket_id in visited:
            return
        visiting.add(ticket_id)
        for dependency in by_id[ticket_id].get("dependencies", []):
            if dependency not in by_id:
                errors.append(f"UNKNOWN_TICKET_DEPENDENCY {ticket_id}:{dependency}")
            else:
                visit(dependency)
        visiting.remove(ticket_id)
        visited.add(ticket_id)
    for ticket_id in by_id:
        visit(ticket_id)


def check_closeout(project: Path, ledger: dict[str, Any], errors: list[str]) -> dict[str, Any] | None:
    path = evidence_file(project, "closeout/terminal-state.json", errors)
    if path is None:
        return None
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        errors.append("INVALID_CLOSEOUT_JSON")
        return None
    if not isinstance(packet, dict):
        errors.append("INVALID_CLOSEOUT_PACKET")
        return None
    if packet.get("terminal_state") not in {"RELEASE_READY", "YELLOW_ACCEPTANCE_REQUIRED"}:
        errors.append("CLOSEOUT_NOT_RELEASE_COMPATIBLE")
    if not ledger.get("build_identity") or packet.get("build_identity") != ledger["build_identity"]:
        errors.append("CLOSEOUT_BUILD_MISMATCH")
    evidence = packet.get("evidence", [])
    if not isinstance(evidence, list) or not evidence:
        errors.append("CLOSEOUT_EVIDENCE_REQUIRED")
    else:
        for item in evidence:
            if not isinstance(item, dict):
                errors.append("INVALID_CLOSEOUT_EVIDENCE")
            else:
                verify_evidence(project, item.get("path"), item.get("sha256"), errors)
    if not isinstance(packet.get("open_risks"), list):
        errors.append("CLOSEOUT_RISKS_REQUIRED")
    if packet.get("terminal_state") == "RELEASE_READY" and packet.get("open_risks"):
        errors.append("CLOSEOUT_RISK_ACCEPTANCE_REQUIRED")
    return packet


def check_release(project: Path, ledger: dict[str, Any], verdict: dict[str, Any], errors: list[str]) -> None:
    if not ledger.get("build_identity") or verdict.get("build_identity") != ledger["build_identity"]:
        errors.append("RELEASE_BUILD_MISMATCH")
    approval = verdict.get("human_approval", {})
    if approval.get("required") and (approval.get("status") != "APPROVED" or not approval.get("by") or not approval.get("at")):
        errors.append("RELEASE_HUMAN_APPROVAL_REQUIRED")
    for ref in verdict.get("evidence_refs", []):
        evidence_file(project, ref, errors)
    packet = check_closeout(project, ledger, errors)
    if packet and packet.get("terminal_state") == "YELLOW_ACCEPTANCE_REQUIRED":
        if verdict.get("status") != "SHIP_WITH_ACCEPTED_RISK" or not verdict.get("accepted_risks"):
            errors.append("CLOSEOUT_RISKS_NOT_ACCEPTED")
    # Audit and judge are separate packets, not labels supplied in a summary.
    for relative, expected in (("release/production-audit.json", {"SHIP", "SHIP_WITH_ACCEPTED_RISK"}),
                               ("release/final-judge.json", {"GREEN"})):
        path = evidence_file(project, relative, errors)
        if path is None:
            continue
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(item, dict) or item.get("status") not in expected or item.get("build_identity") != verdict.get("build_identity"):
                errors.append(f"RELEASE_PACKET_MISMATCH {relative}")
        except (OSError, ValueError):
            errors.append(f"INVALID_RELEASE_PACKET {relative}")
