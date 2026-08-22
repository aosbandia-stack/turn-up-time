#!/usr/bin/env python3
"""Static contract validator for the Turn Up Time source repository."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

CLAUDE_DIR = Path(__file__).resolve().parents[1]
ROOT = CLAUDE_DIR.parent
ERRORS: list[str] = []
CORE_SKILLS = {
    "turn-up-time", "grill-me", "omnidex", "boil-the-ocean", "easily-irritated",
    "production-audit", "its-not-you-its-me", "plug-it-in", "guard-before-write", "eval-harness",
}
EXPECTED_AGENTS = {
    "architect", "backend-systems-researcher", "combined-engineering-researcher",
    "fresh-release-judge", "fresh-workflow-reviewer", "frontend-experience-researcher",
    "functional-qa", "implementation-engineer", "integration-lead", "irritated-domain-user",
    "premise-auditor", "product-domain-researcher", "security-performance-reviewer",
    "security-privacy-researcher", "ticket-verifier", "triage-lead", "ux-accessibility-reviewer",
}
ASSURANCE = EXPECTED_AGENTS - {"implementation-engineer"}
SCHEMA_EXAMPLES = {
    "intake-readiness.schema.json": "intake-readiness.json",
    "definition-of-good.schema.json": "definition-of-good.example.json",
    "evidence-pack.schema.json": "evidence-pack.example.json",
    "premise-verdict.schema.json": "premise-verdict.example.json",
    "seam-verdict.schema.json": "seam-verdict.pre-build.example.json",
    "release-verdict.schema.json": "release-verdict.example.json",
    "ticket.schema.json": "ticket.example.json",
    "project-ledger.schema.json": "project-ledger.example.json",
    "improvement-proposal.schema.json": "improvement-proposal.example.json",
}
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def frontmatter(path: Path) -> dict[str, Any]:
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if not match:
        ERRORS.append(f"{path.relative_to(ROOT)} missing YAML frontmatter")
        return {}
    try:
        value = yaml.safe_load(match.group(1)) or {}
        if not isinstance(value, dict):
            raise TypeError("frontmatter must be a mapping")
        return value
    except Exception as exc:
        ERRORS.append(f"{path.relative_to(ROOT)} invalid frontmatter: {exc}")
        return {}


def validate_instance(instance: Any, schema: dict[str, Any], label: str) -> None:
    for error in sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda item: list(item.path)):
        where = ".".join(str(part) for part in error.path) or "<root>"
        ERRORS.append(f"{label}:{where}: {error.message}")


def main() -> int:
    skills = {path.parent.name for path in (CLAUDE_DIR / "skills").glob("*/SKILL.md")}
    agents = {path.stem for path in (CLAUDE_DIR / "agents").glob("*.md")}
    if skills != CORE_SKILLS:
        ERRORS.append(f"skill set mismatch missing={sorted(CORE_SKILLS-skills)} extra={sorted(skills-CORE_SKILLS)}")
    if agents != EXPECTED_AGENTS:
        ERRORS.append(f"agent set mismatch missing={sorted(EXPECTED_AGENTS-agents)} extra={sorted(agents-EXPECTED_AGENTS)}")

    for path in list((CLAUDE_DIR / "skills").glob("*/SKILL.md")) + list((CLAUDE_DIR / "agents").glob("*.md")):
        data = frontmatter(path)
        for key in ("name", "description"):
            if not data.get(key):
                ERRORS.append(f"{path.relative_to(ROOT)} missing {key}")

    for name in EXPECTED_AGENTS:
        path = CLAUDE_DIR / "agents" / f"{name}.md"
        data = frontmatter(path)
        tools = set(data.get("tools") or [])
        expected_class = "production" if name == "implementation-engineer" else "assurance"
        if data.get("role_class") != expected_class:
            ERRORS.append(f"agent {name} role_class={data.get('role_class')} expected={expected_class}")
        if name in ASSURANCE and tools.intersection({"Edit", "Write", "MultiEdit", "NotebookEdit"}):
            ERRORS.append(f"assurance agent {name} has write tools {sorted(tools)}")
        body = path.read_text(encoding="utf-8")
        for marker in ("## Mission", "## Receives", "## Method", "## Returns", "## Stop and escalate", "## Prohibited"):
            if marker not in body:
                ERRORS.append(f"agent {name} missing role marker {marker}")

    router = (CLAUDE_DIR / "hooks" / "skill-router.ps1").read_text(encoding="utf-8").lower()
    if "engineering-loop" in router:
        ERRORS.append("router references retired engineering-loop")
    for required in ("turn-up-time", "plug-it-in", "its-not-you-its-me", "guard-before-write"):
        if required not in router:
            ERRORS.append(f"router missing {required}")
    for forbidden in ("route = 'omnidex'", "route = 'boil-the-ocean'", "route = 'impeccable'"):
        if forbidden in router:
            ERRORS.append(f"router bypasses control plane: {forbidden}")

    registry_path = CLAUDE_DIR / "capabilities" / "registry.json"
    registry_schema = read_json(CLAUDE_DIR / "schemas" / "capability-registry.schema.json")
    registry = read_json(registry_path)
    validate_instance(registry, registry_schema, str(registry_path.relative_to(ROOT)))
    if (CLAUDE_DIR / "capabilities" / "registry.yaml").exists():
        ERRORS.append("duplicate registry.yaml exists")
    for name, capability in registry.get("capabilities", {}).items():
        if capability.get("bundled"):
            provider = capability.get("provider")
            if not (CLAUDE_DIR / "skills" / str(provider) / "SKILL.md").is_file():
                ERRORS.append(f"bundled capability {name} provider missing: {provider}")

    schemas = {path.name: read_json(path) for path in (CLAUDE_DIR / "schemas").glob("*.json")}
    expected_schemas = set(SCHEMA_EXAMPLES) | {"finding.schema.json", "capability-registry.schema.json"}
    missing_schemas = expected_schemas - set(schemas)
    if missing_schemas:
        ERRORS.append(f"missing schemas {sorted(missing_schemas)}")
    for schema_name, example_name in SCHEMA_EXAMPLES.items():
        example_path = CLAUDE_DIR / "templates" / example_name
        if not example_path.is_file():
            ERRORS.append(f"missing example {example_name}")
            continue
        validate_instance(read_json(example_path), schemas[schema_name], example_name)
    if any((CLAUDE_DIR / "templates").glob("*.yaml")):
        ERRORS.append("loose YAML templates remain; examples must be schema-valid JSON")

    required_scripts = {"validate_repo.py", "run_seeded_evals.py", "fresh_review.py", "scaffold_project.py", "validate_project.py", "resolve_capabilities.py"}
    actual_scripts = {path.name for path in (CLAUDE_DIR / "scripts").glob("*.py")}
    if not required_scripts.issubset(actual_scripts):
        ERRORS.append(f"missing scripts {sorted(required_scripts-actual_scripts)}")

    constitution = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    for phrase in ("Loop contract", "Separation of duties", "Human-owned decisions", "Capability routing", "Stage transition contract"):
        if phrase not in constitution:
            ERRORS.append(f"CLAUDE.md missing marker: {phrase}")

    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        for target in link_pattern.findall(path.read_text(encoding="utf-8", errors="replace")):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            relative = target.split("#", 1)[0]
            if relative and not (path.parent / relative).resolve().exists():
                ERRORS.append(f"broken link {path.relative_to(ROOT)} -> {target}")

    if ERRORS:
        print("VALIDATION: RED")
        for error in ERRORS:
            print(f" - {error}")
        return 1
    print("VALIDATION: GREEN")
    print(f" skills={len(skills)} agents={len(agents)} schemas={len(schemas)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
