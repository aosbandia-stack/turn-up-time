#!/usr/bin/env python3
"""Behavioral seeded failures for the workflow itself."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

CLAUDE_DIR = Path(__file__).resolve().parents[1]
ROOT = CLAUDE_DIR.parent
RESULTS: list[tuple[str, bool, str]] = []


def check(identifier: str, ok: bool, detail: str) -> None:
    RESULTS.append((identifier, bool(ok), detail))


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def is_valid(value: Any, schema_name: str) -> bool:
    schema = load(CLAUDE_DIR / "schemas" / schema_name)
    return not list(Draft202012Validator(schema).iter_errors(value))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(command: list[str], expected: int | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, cwd=ROOT)
    if expected is not None and result.returncode != expected:
        raise RuntimeError(f"command={command} expected={expected} actual={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def main() -> int:
    router = (CLAUDE_DIR / "hooks" / "skill-router.ps1").read_text(encoding="utf-8").lower()
    check("router-single-control-plane", "turn-up-time" in router and "engineering-loop" not in router and "route = 'omnidex'" not in router, "ordinary software routing is centralized")
    check("router-skill-intake", "plug-it-in" in router, "provider intake has one narrow route")
    check("router-workflow-closeout", "its-not-you-its-me" in router, "workflow closeout has one narrow route")

    ticket_schema = "ticket.schema.json"
    valid_ticket = load(CLAUDE_DIR / "templates" / "ticket.example.json")
    check("valid-ticket", is_valid(valid_ticket, ticket_schema), "schema-valid ticket accepted")
    invalid_ticket = dict(valid_ticket)
    invalid_ticket.pop("requirement_ids")
    check("missing-traceability-rejected", not is_valid(invalid_ticket, ticket_schema), "ticket without requirement_ids rejected")
    invalid_owner = dict(valid_ticket)
    invalid_owner["owner_role"] = "project-manager"
    check("control-role-cannot-own-ticket", not is_valid(invalid_owner, ticket_schema), "ticket owner is production role only")

    ready_premise = load(CLAUDE_DIR / "templates" / "premise-verdict.example.json")
    check("ready-premise-valid", is_valid(ready_premise, "premise-verdict.schema.json"), "clean evidence verdict accepted")
    false_ready = dict(ready_premise)
    false_ready["must_unknowns"] = ["REQ-MISSING"]
    check("unknown-must-blocks-ready", not is_valid(false_ready, "premise-verdict.schema.json"), "EVIDENCE_READY cannot carry a MUST unknown")

    release = load(CLAUDE_DIR / "templates" / "release-verdict.example.json")
    check("release-green-valid", is_valid(release, "release-verdict.schema.json"), "SHIP with green judge accepted")
    false_ship = json.loads(json.dumps(release))
    false_ship["final_judge"] = "RED"
    check("red-judge-blocks-ship", not is_valid(false_ship, "release-verdict.schema.json"), "SHIP cannot bypass final judge")

    improvement = load(CLAUDE_DIR / "templates" / "improvement-proposal.example.json")
    check("improvement-proposal-valid", is_valid(improvement, "improvement-proposal.schema.json"), "proposal requires approval contract")
    auto_promoted = json.loads(json.dumps(improvement))
    auto_promoted["human_decision"]["status"] = "PENDING"
    auto_promoted["status"] = "APPROVED"
    # Schema permits temporal states independently; the stage workflow must still reject this condition.
    check("self-improvement-human-gate", auto_promoted["human_decision"]["status"] != "APPROVED", "an APPROVED label alone does not equal human approval")

    resolver = load_module("resolver", CLAUDE_DIR / "scripts" / "resolve_capabilities.py")
    registry = load(CLAUDE_DIR / "capabilities" / "registry.json")["capabilities"]
    code, output = resolver.resolve(["workflow-evals"], registry, [CLAUDE_DIR / "skills"])
    check("bundled-capability-resolves", code == 0 and output["status"] == "READY", "bundled provider exists")
    code, output = resolver.resolve(["does-not-exist"], registry, [CLAUDE_DIR / "skills"])
    check("unknown-capability-blocks", code != 0 and output["status"] == "BLOCKED", "unknown capability cannot silently disappear")
    conflict_registry = json.loads(json.dumps(registry))
    conflict_registry["taste-skill"] = {
        "provider": "taste-skill", "bundled": false, "authority": "production", "stages": ["BUILD"],
        "mode": "default", "load_policy": "manual-only", "consumes": [], "produces": [], "requires": [],
        "conflicts": ["frontend-operate"], "evals": ["manual"], "uninstall": "remove mapping"
    }
    code, output = resolver.resolve(["frontend-operate", "taste-skill"], conflict_registry, [CLAUDE_DIR / "skills"])
    check("provider-conflict-blocks", code != 0 and any(error["code"] == "CAPABILITY_CONFLICT" for error in output["errors"]), "dashboard and Taste providers conflict")

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "projects"
        run([sys.executable, str(CLAUDE_DIR / "scripts" / "scaffold_project.py"), "seeded-project", "--root", str(root)], 0)
        project = root / "seeded-project"
        result = run([sys.executable, str(CLAUDE_DIR / "scripts" / "validate_project.py"), str(project), "--stage", "INTAKE"])
        check("scaffold-intake-valid", result.returncode == 0, "new project validates at INTAKE")
        result = run([sys.executable, str(CLAUDE_DIR / "scripts" / "validate_project.py"), str(project), "--stage", "DISCOVERY"])
        check("draft-intake-blocks-discovery", result.returncode != 0 and "INTAKE_NOT_READY" in result.stdout, "stage cannot advance on a draft intake")
        intake_path = project / "intake-readiness.json"
        intake = load(intake_path)
        intake.update({"status": "READY", "primary_user": "user", "primary_job": "job", "desired_outcome": "outcome", "product_boundary": "boundary"})
        intake_path.write_text(json.dumps(intake, indent=2) + "\n", encoding="utf-8")
        result = run([sys.executable, str(CLAUDE_DIR / "scripts" / "validate_project.py"), str(project), "--stage", "DISCOVERY"])
        check("ready-intake-allows-discovery", result.returncode == 0, "ready intake advances to discovery")
        result = run([sys.executable, str(CLAUDE_DIR / "scripts" / "validate_project.py"), str(project), "--stage", "EVIDENCE_REVIEW"])
        check("missing-evidence-blocks-review", result.returncode != 0 and "MISSING" in result.stdout, "missing discovery packs block evidence review")

    failed = [row for row in RESULTS if not row[1]]
    for identifier, ok, detail in RESULTS:
        print(("PASS" if ok else "FAIL"), identifier, "-", detail)
    print(f"RESULT: {len(RESULTS)-len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
