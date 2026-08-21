#!/usr/bin/env python3
"""Deterministic repository contract validation."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator, FormatChecker
import yaml

CLAUDE_DIR = Path(__file__).resolve().parents[1]
ROOT = CLAUDE_DIR.parent
errors: list[str] = []
CORE_SKILLS = {
    "turn-up-time", "grill-me", "omnidex", "boil-the-ocean", "easily-irritated",
    "production-audit", "its-not-you-its-me", "plug-it-in", "guard-before-write", "eval-harness"
}
EXPECTED_SCHEMAS = {
    "capability-registry.schema.json", "intake-readiness.schema.json", "definition-of-good.schema.json",
    "evidence-pack.schema.json", "ticket.schema.json", "project-ledger.schema.json", "finding.schema.json",
    "improvement-proposal.schema.json", "stage-verdict.schema.json"
}
ROLE_SECTIONS = ("## Mission", "## Inputs", "## Required procedure", "## Output contract", "## Stop or escalate", "## Boundaries")
ASSURANCE_TOKENS = (
    "researcher", "auditor", "architect", "integration-lead", "irritated-domain-user",
    "functional-qa", "reviewer", "triage-lead", "ticket-verifier", "judge"
)
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def check_schema(instance_path: Path, schema_path: Path) -> None:
    try:
        instance = load_json(instance_path)
        schema = load_json(schema_path)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for error in validator.iter_errors(instance):
            location = ".".join(str(part) for part in error.path) or "<root>"
            errors.append(f"{instance_path.relative_to(ROOT)}: {location}: {error.message}")
    except Exception as exc:
        errors.append(f"schema validation failed for {instance_path.relative_to(ROOT)}: {exc}")


def main() -> int:
    skill_paths = sorted((CLAUDE_DIR / "skills").glob("*/SKILL.md"))
    skill_names = {path.parent.name for path in skill_paths}
    if skill_names != CORE_SKILLS:
        errors.append(f"core skill set differs: missing={sorted(CORE_SKILLS-skill_names)} extra={sorted(skill_names-CORE_SKILLS)}")

    agent_paths = sorted((CLAUDE_DIR / "agents").glob("*.md"))
    if len(agent_paths) != 17:
        errors.append(f"expected 17 agents, found {len(agent_paths)}")

    for path in skill_paths + agent_paths:
        text = path.read_text(encoding="utf-8")
        match = FRONTMATTER.match(text)
        if not match:
            errors.append(f"{path.relative_to(ROOT)} missing frontmatter")
            continue
        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)} bad frontmatter: {exc}")
            continue
        for key in ("name", "description"):
            if not frontmatter.get(key):
                errors.append(f"{path.relative_to(ROOT)} missing {key}")
        if path.parent.parent.name == "agents":
            name = frontmatter.get("name", "")
            tools = set(frontmatter.get("tools") or [])
            for section in ROLE_SECTIONS:
                if section not in text:
                    errors.append(f"agent {name} missing role section {section}")
            if any(token in name for token in ASSURANCE_TOKENS) and name != "implementation-engineer":
                forbidden = tools & {"Edit", "Write", "MultiEdit", "NotebookEdit"}
                if forbidden:
                    errors.append(f"assurance role {name} has write tools {sorted(forbidden)}")

    schema_names = {path.name for path in (CLAUDE_DIR / "schemas").glob("*.json")}
    if schema_names != EXPECTED_SCHEMAS:
        errors.append(f"schema set differs: missing={sorted(EXPECTED_SCHEMAS-schema_names)} extra={sorted(schema_names-EXPECTED_SCHEMAS)}")
    for path in (CLAUDE_DIR / "schemas").glob("*.json"):
        try:
            load_json(path)
        except Exception as exc:
            errors.append(f"invalid JSON schema {path.name}: {exc}")

    registry = CLAUDE_DIR / "capabilities" / "registry.json"
    if not registry.exists():
        errors.append("canonical capability registry.json is missing")
    else:
        check_schema(registry, CLAUDE_DIR / "schemas" / "capability-registry.schema.json")
    if (CLAUDE_DIR / "capabilities" / "registry.yaml").exists():
        errors.append("duplicate registry.yaml must not exist")

    template_checks = {
        "intake-readiness.json": "intake-readiness.schema.json",
        "evidence-pack.example.json": "evidence-pack.schema.json",
        "definition-of-good.example.json": "definition-of-good.schema.json",
        "ticket.example.json": "ticket.schema.json",
        "improvement-proposal.example.json": "improvement-proposal.schema.json",
    }
    for template, schema in template_checks.items():
        check_schema(CLAUDE_DIR / "templates" / template, CLAUDE_DIR / "schemas" / schema)

    router = (CLAUDE_DIR / "hooks" / "skill-router.ps1").read_text(encoding="utf-8").lower()
    if "engineering-loop" in router:
        errors.append("router references retired engineering-loop")
    for required in ("turn-up-time", "plug-it-in", "its-not-you-its-me", "guard-before-write"):
        if required not in router:
            errors.append(f"router missing {required}")
    if "route = 'omnidex'" in router or "route = 'boil-the-ocean'" in router:
        errors.append("router bypasses the single control plane")

    settings = load_json(CLAUDE_DIR / "settings.json")
    settings_text = json.dumps(settings)
    for hook in ("skill-router.ps1", "destructive-command-guard.ps1"):
        if hook not in settings_text:
            errors.append(f"project settings do not register {hook}")

    flows = {
        "turn-up-time": ("scaffold_project.py", "validate_project.py", "advance_stage.py"),
        "omnidex": ("definition-of-good.json", "TICKETING", "AWAITING_HUMAN", "ticket.schema.json"),
        "boil-the-ocean": ("resolve_capabilities.py", "CAPABILITY_PROVIDER_MISSING", "validate_project.py"),
        "easily-irritated": ("finding.schema.json", "product-closeout", "verdict.json"),
        "production-audit": ("fresh-release-judge", "final-judge.json", "production-audit.json"),
        "its-not-you-its-me": ("improvement-proposal.schema.json", "human approval"),
        "plug-it-in": ("registry.json", "capability-registry.schema.json", "resolve_capabilities.py"),
    }
    for skill, markers in flows.items():
        text = (CLAUDE_DIR / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        for marker in markers:
            if marker.lower() not in text.lower():
                errors.append(f"{skill} missing flow marker {marker}")

    for script in ("resolve_capabilities.py", "scaffold_project.py", "validate_project.py", "record_artifact.py", "advance_stage.py"):
        if not (CLAUDE_DIR / "scripts" / script).exists():
            errors.append(f"missing runtime script {script}")

    constitution = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    for phrase in ("Loop contract", "Separation of duties", "Human-owned decisions", "Capability routing"):
        if phrase not in constitution:
            errors.append(f"CLAUDE.md missing marker: {phrase}")

    install = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
    for marker in ("KeepGlobalConstitution", "ReplaceGlobalConstitution", "destructive-command-guard.ps1", "installedSha256", "turn-up-time-install-manifest.json"):
        if marker not in install:
            errors.append(f"installer missing safety marker {marker}")
    uninstall = (ROOT / "scripts" / "uninstall.ps1").read_text(encoding="utf-8")
    for marker in ("ForceModified", "installedSha256", "SKIP MODIFIED"):
        if marker not in uninstall:
            errors.append(f"uninstaller missing safety marker {marker}")

    if errors:
        print("VALIDATION: RED")
        for error in errors:
            print(" -", error)
        return 1
    print("VALIDATION: GREEN")
    print(f" skills={len(skill_paths)} agents={len(agent_paths)} schemas={len(schema_names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
