#!/usr/bin/env python3
"""Behavioral seeded failures for the workflow itself."""
from __future__ import annotations

import hashlib
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
    code, output = resolver.resolve(["frontend-operate"], registry, [])
    check("selected-unbundled-provider-blocks", code != 0 and any(error["code"] == "REQUIRED_PROVIDER_MISSING" and error["capability"] == "frontend-operate" for error in output["errors"]), "selected design provider cannot remain READY when absent")
    check("transitive-browser-provider-blocks", code != 0 and any(error["code"] == "REQUIRED_PROVIDER_MISSING" and error["capability"] == "browser-e2e" for error in output["errors"]), "browser dependency is required even though unbundled")
    code, output = resolver.resolve(["repository-cleanup"], registry, [CLAUDE_DIR / "skills"])
    check("cleanup-provider-resolves", code == 0 and output["plan"][0]["usable"] and not output["plan"][0]["used"], "readable cleanup instructions resolve without a fabricated usage claim")
    code, output = resolver.resolve(["does-not-exist"], registry, [CLAUDE_DIR / "skills"])
    check("unknown-capability-blocks", code != 0 and output["status"] == "BLOCKED", "unknown capability cannot silently disappear")
    surfaces = [{"id":"native", "platform":"native", "purpose":"operate", "stack":"swiftui", "flags":[], "verification_capabilities":[]}]
    code, output = resolver.resolve([], registry, [], ui_surfaces=surfaces)
    check("native-needs-real-assurance", code != 0 and any(error["code"] == "NATIVE_ASSURANCE_REQUIRED" for error in output["errors"]) and "browser-e2e" not in output["selected"], "native does not inherit a fictional browser adapter")
    surfaces[0].update(platform="web", flags=["unknown-provider-flag"])
    code, output = resolver.resolve([], registry, [], ui_surfaces=surfaces)
    check("unknown-ui-flag-blocks", code != 0 and any(error["code"] == "UI_SELECTOR_UNAVAILABLE" for error in output["errors"]), "an unknown optional selector cannot silently disappear")
    override_registry = json.loads(json.dumps(registry))
    override_registry["browser-e2e"].pop("ui_selector")
    override_registry["browser-e2e"]["provider_kind"] = "instruction-only"
    surfaces[0].update(stack="react-tailwind", flags=[])
    code, output = resolver.resolve([], override_registry, [], ui_surfaces=surfaces)
    check("web-assurance-cannot-be-overridden-away", "browser-e2e" in output["ui_required"] and any(error["code"] == "UI_ASSURANCE_ADAPTER_INVALID" for error in output["errors"]), "a web override cannot erase or downgrade execution assurance")
    code, output = resolver.resolve(["21st-generate"], registry, [], ui_surfaces=surfaces)
    check("selected-generation-needs-surface-binding", any(error["code"] == "UI_CAPABILITY_SURFACE_REQUIRED" for error in output["errors"]), "ticket selection cannot bypass the declared surface flag and compatibility gate")
    conflict_registry = json.loads(json.dumps(registry))
    conflict_registry["taste-skill"] = {
        "provider": "taste-skill", "bundled": False, "authority": "production", "stages": ["BUILD"],
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

    # Exercise the consumed Swiper boundary without adding a runtime-test dependency.
    contracts = load_module("project_contracts", CLAUDE_DIR / "scripts" / "project_contracts.py")
    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp) / "example-project"
        (project / "receipts").mkdir(parents=True)
        (project / "closeout").mkdir()
        packet = load(CLAUDE_DIR / "templates" / "terminal-state.example.json")
        build = packet["build_identity"]
        def receipt(identifier: str, content: bytes = b"Seeded captured output") -> str:
            output = project / "receipts" / (identifier + ".txt")
            output.write_bytes(content)
            reference = "receipts/" + identifier + ".json"
            value = {"schema_version": 1, "project_id": project.name, "build_identity": build,
                     "check_id": identifier, "status": "PASS", "checked_at": "2026-01-01T00:00:00Z",
                     "evidence_refs": [{"path": output.relative_to(project).as_posix(), "sha256": hashlib.sha256(content).hexdigest()}]}
            (project / reference).write_text(json.dumps(value), encoding="utf-8")
            return reference
        source = (CLAUDE_DIR / "skills/swiper-dont-swpe-me/SKILL.md").resolve()
        instruction = {"source_path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                       "receipt_ref": receipt("cleanup-instructions", source.read_bytes())}
        packet["evidence_refs"] = [receipt("journey")]
        packet["cleanup"].update(actions=[], instruction=instruction, evidence_refs=[receipt("cleanup")], handoff_ref=receipt("handoff"))
        def closeout_errors(value: dict[str, Any]) -> list[str]:
            (project / "closeout/terminal-state.json").write_text(json.dumps(value), encoding="utf-8")
            failures: list[str] = []
            contracts.check_closeout(project, None, build, failures)
            return failures
        check("swiper-no-change-valid", not closeout_errors(packet), "instruction-bound no-change cleanup remains valid")
        missing = json.loads(json.dumps(packet)); missing["cleanup"].pop("instruction")
        check("swiper-instructions-required", bool(closeout_errors(missing)), "unbound instruction claim blocks release entry")
        risky = json.loads(json.dumps(packet))
        action = load(CLAUDE_DIR / "templates" / "terminal-state.example.json")["cleanup"]["actions"][0]
        action.update(decision="INVESTIGATE", external_callers="UNKNOWN")
        risky["cleanup"]["actions"] = [action]
        check("swiper-risk-link-required", any("CLEANUP_RISK_LINK_REQUIRED" in error for error in closeout_errors(risky)), "unknown caller investigation cannot disappear from open risks")
        risky["cleanup"].update(outcome="CHANGED", baseline_identity="baseline-before-cleanup", reproof_refs=["receipts/cleanup.json"])
        action.update(decision="REMOVE", external_callers="VERIFIED")
        check("swiper-removal-guard-required", any("CLEANUP_ACTION_GUARD_REQUIRED" in error for error in closeout_errors(risky)), "removal cannot reuse a generic PASS or deployment guard")

        loop = {"rubric_version":"seed-v1", "rubric_sha256":"0"*64, "guide_sha256":hashlib.sha256(b"Seeded guide").hexdigest(),
                "locked_at":"2025-12-31T00:00:00Z", "criteria":[{"id":"clarity", "critical":True, "minimum":3,
                "anchors":{str(i):"Seeded project anchor "+str(i) for i in range(5)}}], "hard_gates":["keyboard"],
                "max_rounds":4, "max_elapsed_seconds":60, "max_stagnant_rounds":1, "cost_ceiling":None}
        loop["rubric_sha256"] = contracts.rubric_digest(loop)
        reference = receipt("design-evaluation")
        evaluation = load(project / reference)
        assets = evaluation["evidence_refs"]
        evaluation["design_evaluation"] = {"rubric_sha256":loop["rubric_sha256"], "guide_sha256":loop["guide_sha256"],
            "evaluator_role":"assurance", "evaluator_id":"independent-seeded-reviewer", "started_at":evaluation["checked_at"],
            "criteria":[{"id":"clarity", "score":2, "status":"FAIL", "evidence_refs":assets}],
            "hard_gates":[{"id":"keyboard", "status":"PASS", "evidence_refs":assets}],
            "cumulative_cost":None, "cost_unit":None, "cost_evidence_refs":[]}
        packet.update(round_history=[reference], design_stop_reason="THRESHOLD_MET")
        def design_errors() -> list[str]:
            (project / reference).write_text(json.dumps(evaluation), encoding="utf-8")
            failures: list[str] = []
            contracts.check_design_loop(project, {"design_loop":loop}, packet, build, failures)
            return failures
        check("critical-design-floor-blocks", any("DESIGN_FINAL_BUILD_NOT_PASS" in error for error in design_errors()), "a PASS label cannot conceal a failed critical criterion")
        evaluation["design_evaluation"]["criteria"][0].update(score=3, status="PASS")
        check("anchored-design-pass-valid", not design_errors(), "independent actual-output receipt meets every criterion and gate")

    failed = [row for row in RESULTS if not row[1]]
    for identifier, ok, detail in RESULTS:
        print(("PASS" if ok else "FAIL"), identifier, "-", detail)
    print(f"RESULT: {len(RESULTS)-len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
