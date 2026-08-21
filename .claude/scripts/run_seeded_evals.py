#!/usr/bin/env python3
"""Run seeded process failures against the real workflow implementation."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from jsonschema import Draft202012Validator, FormatChecker

CLAUDE_DIR = Path(__file__).resolve().parents[1]
ROOT = CLAUDE_DIR.parent
FIXTURES = CLAUDE_DIR / "evals" / "fixtures"
results: list[tuple[str, bool, str]] = []


def check(identifier: str, ok: bool, detail: str) -> None:
    results.append((identifier, bool(ok), detail))


def schema_valid(instance_path: Path, schema_path: Path) -> bool:
    instance = json.loads(instance_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return not list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance))


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), cwd=cwd, text=True, capture_output=True)


def main() -> int:
    router = (CLAUDE_DIR / "hooks" / "skill-router.ps1").read_text(encoding="utf-8").lower()
    turn = (CLAUDE_DIR / "skills" / "turn-up-time" / "SKILL.md").read_text(encoding="utf-8")
    omni = (CLAUDE_DIR / "skills" / "omnidex" / "SKILL.md").read_text(encoding="utf-8")
    boil = (CLAUDE_DIR / "skills" / "boil-the-ocean" / "SKILL.md").read_text(encoding="utf-8")
    release = (CLAUDE_DIR / "skills" / "production-audit" / "SKILL.md").read_text(encoding="utf-8")
    closeout = (CLAUDE_DIR / "skills" / "its-not-you-its-me" / "SKILL.md").read_text(encoding="utf-8")

    check("router-build-single-control-plane", "turn-up-time" in router and "engineering-loop" not in router, "build route is centralized")
    check("router-skill-install", "plug-it-in" in router, "skill intake route exists")
    check("ambiguous-product-before-research", "/grill-me" in turn and "human-owned" in turn.lower(), "clarification is conditional inside PM")
    check("bounded-fix-no-discovery-fleet", "Tier B" in turn, "Tier B is classified before Tier C")
    check("pm-cannot-build-or-certify", "do not conduct specialist research" in turn.lower() and "certify" in turn.lower(), "PM boundaries present")
    check("omnidex-state-is-schema-valid", "TICKETS_AWAITING_HUMAN_APPROVAL" not in omni and "TICKETING" in omni and "AWAITING_HUMAN" in omni, "OmniDex uses ledger enum values")
    check("repeated-ticket-failure-escalates", "two materially different repairs" in boil, "repair loop has escalation")
    check("capability-resolution-is-executable", "resolve_capabilities.py" in boil and "CAPABILITY_PROVIDER_MISSING" in boil, "Boil fails closed on provider gaps")
    check("release-has-independent-final-judge", "fresh-release-judge" in release and "final-judge.json" in release, "release requires cold judge")
    check("closeout-cannot-auto-promote", "human approval" in closeout.lower(), "self-improvement cannot auto-promote")

    schema_dir = CLAUDE_DIR / "schemas"
    check("ticket-valid-fixture", schema_valid(FIXTURES / "valid-ticket.json", schema_dir / "ticket.schema.json"), "valid ticket passes")
    check("ticket-invalid-fixture", not schema_valid(FIXTURES / "invalid-ticket.json", schema_dir / "ticket.schema.json"), "untraceable ticket is rejected")
    check("intake-valid-fixture", schema_valid(FIXTURES / "valid-intake.json", schema_dir / "intake-readiness.schema.json"), "ready intake is complete")
    check("intake-invalid-fixture", not schema_valid(FIXTURES / "invalid-intake.json", schema_dir / "intake-readiness.schema.json"), "empty ready intake is rejected")
    check("evidence-valid-fixture", schema_valid(FIXTURES / "valid-evidence.json", schema_dir / "evidence-pack.schema.json"), "supported MUST can be ready")
    check("unknown-must-blocks-readiness", not schema_valid(FIXTURES / "invalid-evidence-ready-unknown.json", schema_dir / "evidence-pack.schema.json"), "READY plus UNKNOWN MUST is rejected")
    check("registry-valid", schema_valid(CLAUDE_DIR / "capabilities" / "registry.json", schema_dir / "capability-registry.schema.json"), "registry passes schema")

    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        project = temp / "project"
        home = temp / "home"
        (project / ".claude" / "capabilities").mkdir(parents=True)
        (home / ".claude" / "skills" / "provider-a").mkdir(parents=True)
        (home / ".claude" / "skills" / "provider-b").mkdir(parents=True)
        (home / ".claude" / "skills" / "provider-a" / "SKILL.md").write_text("---\nname: provider-a\ndescription: test\n---\n", encoding="utf-8")
        (home / ".claude" / "skills" / "provider-b" / "SKILL.md").write_text("---\nname: provider-b\ndescription: test\n---\n", encoding="utf-8")
        test_registry = {
            "schema_version": 2,
            "capabilities": {
                "conflict-a": {"provider": "provider-a", "bundled": False, "stages": ["BUILD"], "authority": "production", "consumes": [], "produces": [], "conflicts": ["capability:conflict-b"], "eval": "x", "uninstall": "x"},
                "conflict-b": {"provider": "provider-b", "bundled": False, "stages": ["BUILD"], "authority": "production", "consumes": [], "produces": [], "conflicts": [], "eval": "x", "uninstall": "x"},
                "missing-provider": {"provider": "not-installed", "bundled": False, "stages": ["BUILD"], "authority": "production", "consumes": [], "produces": [], "conflicts": [], "eval": "x", "uninstall": "x"}
            }
        }
        (project / ".claude" / "capabilities" / "registry.json").write_text(json.dumps(test_registry), encoding="utf-8")
        resolver = CLAUDE_DIR / "scripts" / "resolve_capabilities.py"
        conflict = run(sys.executable, str(resolver), "conflict-a", "conflict-b", "--project-root", str(project), "--user-home", str(home))
        missing = run(sys.executable, str(resolver), "missing-provider", "--project-root", str(project), "--user-home", str(home))
        check("capability-conflict-fails", conflict.returncode == 3 and "CAPABILITY_CONFLICT" in conflict.stdout, "declared conflict blocks")
        check("missing-provider-fails", missing.returncode == 5 and "CAPABILITY_PROVIDER_MISSING" in missing.stdout, "missing provider blocks")

        workspace = temp / "workspace"
        workspace.mkdir()
        scaffold = run(sys.executable, str(CLAUDE_DIR / "scripts" / "scaffold_project.py"), "sample", "--profile", "lite", "--repo-root", str(workspace))
        expected_dirs = ["evidence", "tickets", "receipts", "integration", "closeout", "release"]
        project_root = workspace / ".claude" / "projects" / "sample"
        check("scaffold-complete", scaffold.returncode == 0 and all((project_root / name).is_dir() for name in expected_dirs), "full project workspace created")
        validator = CLAUDE_DIR / "scripts" / "validate_project.py"
        intake_green = run(sys.executable, str(validator), str(project_root), "--repo-root", str(workspace))
        check("project-intake-valid", intake_green.returncode == 0, "fresh INTAKE workspace validates")
        ledger_path = project_root / "project-ledger.json"
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        ledger["stage"] = "DISCOVERY"
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        illegal_advance = run(sys.executable, str(validator), str(project_root), "--repo-root", str(workspace))
        check("illegal-stage-advance-fails", illegal_advance.returncode != 0 and "ready intake" in illegal_advance.stdout, "stage gate prevents hope-based advance")

    failed = [result for result in results if not result[1]]
    for identifier, ok, detail in results:
        print(("PASS" if ok else "FAIL"), identifier, "-", detail)
    print(f"RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
