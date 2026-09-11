"""Regression checks for plausible-looking but unproven green artifacts."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / ".claude/scripts/evidence_contracts.py"
spec = importlib.util.spec_from_file_location("evidence_contracts", SCRIPT)
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


def ticket(project):
    path = project / "checks.txt"
    path.write_text("passed actual check\n", encoding="utf-8")
    result = {"check_id": "save", "status": "PASS", "build_identity": "build-a",
              "evaluator_role": "assurance", "evaluator_id": "verifier-1",
              "evidence_ref": "checks.txt", "evidence_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return {"ticket_id": "T1", "acceptance_checks": [{"id": "save", "evidence": "checks.txt"}],
            "build_receipt": {"build_identity": "build-a", "check_results": [result]}}


def test_complete_evidence_passes(tmp_path):
    errors = []
    evidence.check_ticket_evidence(tmp_path, ticket(tmp_path), errors)
    assert errors == []


@pytest.mark.parametrize("mutation,expected", [
    (lambda t: t["build_receipt"].update(check_results=[]), "CHECK_RESULTS_REQUIRED"),
    (lambda t: t["build_receipt"].update(check_results=["passed"]), "STRUCTURED_CHECK_RESULT_REQUIRED"),
    (lambda t: t["build_receipt"]["check_results"][0].update(status="FAIL"), "CHECK_NOT_PASS"),
    (lambda t: t["build_receipt"]["check_results"][0].update(build_identity="stale"), "CHECK_BUILD_MISMATCH"),
    (lambda t: t["build_receipt"]["check_results"][0].update(evaluator_role="production"), "INDEPENDENT_EVALUATOR_REQUIRED"),
    (lambda t: t["build_receipt"]["check_results"][0].update(evidence_sha256="0" * 64), "EVIDENCE_HASH_MISMATCH"),
    (lambda t: t["acceptance_checks"][0].update(evidence=None), "ACCEPTANCE_EVIDENCE_MISMATCH"),
    (lambda t: t["build_receipt"]["check_results"].append(copy.deepcopy(t["build_receipt"]["check_results"][0])), "UNKNOWN_OR_DUPLICATE_CHECK_RESULT"),
    (lambda t: t["acceptance_checks"].append({"id": "load", "evidence": None}), "MISSING_CHECK_RESULT"),
])
def test_false_green_is_rejected(tmp_path, mutation, expected):
    value = ticket(tmp_path)
    mutation(value)
    errors = []
    evidence.check_ticket_evidence(tmp_path, value, errors)
    assert any(expected in error for error in errors), errors


@pytest.mark.parametrize("ref", ["../secret", "/etc/passwd", "C:\\secret", "a/../../secret", "https://example.com/proof"])
def test_external_evidence_denied(tmp_path, ref):
    errors = []
    assert evidence.evidence_file(tmp_path, ref, errors) is None
    assert errors


def test_missing_or_changed_evidence_denied(tmp_path):
    value = ticket(tmp_path)
    (tmp_path / "checks.txt").write_text("different output")
    errors = []
    evidence.check_ticket_evidence(tmp_path, value, errors)
    assert any("HASH_MISMATCH" in e for e in errors)
    (tmp_path / "checks.txt").unlink()
    errors = []
    evidence.check_ticket_evidence(tmp_path, value, errors)
    assert any("MISSING_OR_EXTERNAL" in e for e in errors)


def test_symlink_escape_denied(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (tmp_path / "outside").write_text("not project evidence")
    try:
        (project / "link").symlink_to(tmp_path / "outside")
    except OSError:
        pytest.skip("host lacks symlink privileges")
    errors = []
    assert evidence.evidence_file(project, "link", errors) is None


@pytest.mark.parametrize("tickets,expected", [
    ([{"ticket_id": "A", "dependencies": ["missing"]}], "UNKNOWN_TICKET_DEPENDENCY"),
    ([{"ticket_id": "A", "dependencies": ["B"]}, {"ticket_id": "B", "dependencies": ["A"]}], "TICKET_DEPENDENCY_CYCLE"),
    ([{"ticket_id": "A"}, {"ticket_id": "A"}], "DUPLICATE_TICKET_ID"),
    ([{"ticket_id": "A", "owned_files": ["./src/App.ts"]}, {"ticket_id": "B", "owned_files": ["src/app.ts"]}], "OVERLAPPING_FILE_OWNERSHIP"),
    ([{"ticket_id": "A", "owned_files": ["../outside"]}], "UNSAFE_OWNED_FILE"),
])
def test_invalid_dependency_or_ownership_graph(tickets, expected):
    errors = []
    evidence.check_ticket_graph(tickets, errors)
    assert any(expected in e for e in errors)


def test_valid_dependency_graph():
    errors = []
    evidence.check_ticket_graph([{"ticket_id": "A"}, {"ticket_id": "B", "dependencies": ["A"]}], errors)
    assert not errors


@pytest.mark.parametrize("content", ["", "not json", "{}", "[]", '{"terminal_state":"MAX_ROUNDS_REACHED"}'])
def test_closeout_existence_is_not_success(tmp_path, content):
    (tmp_path / "closeout").mkdir()
    (tmp_path / "closeout/terminal-state.json").write_text(content)
    errors = []
    evidence.check_closeout(tmp_path, {"build_identity": "build-a"}, errors)
    assert errors


def test_valid_closeout_and_stale_build(tmp_path):
    t = ticket(tmp_path)
    (tmp_path / "closeout").mkdir()
    result = t["build_receipt"]["check_results"][0]
    packet = {"terminal_state": "RELEASE_READY", "build_identity": "build-a", "open_risks": [],
              "evidence": [{"path": "checks.txt", "sha256": result["evidence_sha256"]}]}
    (tmp_path / "closeout/terminal-state.json").write_text(json.dumps(packet))
    errors = []
    evidence.check_closeout(tmp_path, {"build_identity": "build-a"}, errors)
    assert not errors
    evidence.check_closeout(tmp_path, {"build_identity": "build-b"}, errors)
    assert "CLOSEOUT_BUILD_MISMATCH" in errors


def test_release_cannot_ignore_required_pending_approval(tmp_path):
    errors = []
    evidence.check_release(tmp_path, {"build_identity": "b"}, {
        "build_identity": "b", "human_approval": {"required": True, "status": "PENDING"},
    }, errors)
    assert "RELEASE_HUMAN_APPROVAL_REQUIRED" in errors
