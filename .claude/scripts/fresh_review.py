#!/usr/bin/env python3
"""Cold deterministic review of the final workflow tree."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CLAUDE_DIR = ROOT / ".claude"
CHECKS: list[tuple[str, bool, str]] = []
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)


def add(name: str, ok: bool, detail: str) -> None:
    CHECKS.append((name, bool(ok), detail))


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True)


def fm(path: Path) -> dict[str, Any]:
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    return yaml.safe_load(match.group(1)) if match else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument(
        "--report-path", type=Path, default=ROOT / "docs" / "REVIEW-REPORT.md"
    )
    args = parser.parse_args()

    validate = run([sys.executable, ".claude/scripts/validate_repo.py"])
    add(
        "repository-validator",
        validate.returncode == 0,
        validate.stdout.strip() or validate.stderr.strip(),
    )
    seeded = run([sys.executable, ".claude/scripts/run_seeded_evals.py"])
    add(
        "seeded-process-evals",
        seeded.returncode == 0,
        seeded.stdout.strip().splitlines()[-1]
        if seeded.stdout
        else seeded.stderr.strip(),
    )

    skills = sorted((CLAUDE_DIR / "skills").glob("*/SKILL.md"))
    agents = sorted((CLAUDE_DIR / "agents").glob("*.md"))
    schemas = sorted((CLAUDE_DIR / "schemas").glob("*.json"))
    add("skill-count", len(skills) == 10, f"count={len(skills)}")
    add("agent-count", len(agents) == 17, f"count={len(agents)}")
    add("schema-count", len(schemas) == 13, f"count={len(schemas)}")

    constitution = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    add(
        "single-constitution",
        "one constitution" in constitution.lower(),
        "CLAUDE.md declares authority",
    )
    for marker in (
        "One funnel",
        "Loop contract",
        "Separation of duties",
        "Stage transition contract",
        "Capability routing",
        "Release and mutation",
    ):
        add(
            "constitution-" + marker.lower().replace(" ", "-"),
            marker in constitution,
            marker,
        )

    architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    for stage in (
        "INTAKE",
        "DISCOVERY",
        "EVIDENCE_REVIEW",
        "DEFINITION",
        "TICKETING",
        "SEAM_REVIEW",
        "BUILD",
        "INTEGRATION",
        "CLOSEOUT",
        "RELEASE",
        "WORKFLOW_CLOSEOUT",
    ):
        add(
            "stage-owner-" + stage.lower(),
            f"| {stage} |" in architecture,
            "owner/input/output row exists",
        )

    assurance: list[str] = []
    for path in agents:
        data = fm(path)
        tools = set(data.get("tools") or [])
        role_class = data.get("role_class")
        if role_class == "assurance":
            assurance.append(path.stem)
            add(
                "readonly-" + path.stem,
                not tools.intersection({"Edit", "Write", "MultiEdit", "NotebookEdit"}),
                f"tools={sorted(tools)}",
            )
        source = path.read_text(encoding="utf-8")
        for heading in (
            "## Mission",
            "## Receives",
            "## Method",
            "## Returns",
            "## Stop and escalate",
            "## Prohibited",
        ):
            add(
                f"profile-{path.stem}-{heading[3:].lower().replace(' ', '-')}",
                heading in source,
                heading,
            )
    add("assurance-majority", len(assurance) == 16, f"assurance={len(assurance)}")

    router = (CLAUDE_DIR / "hooks" / "skill-router.ps1").read_text(
        encoding="utf-8"
    ).lower()
    add(
        "router-control-plane",
        "route = 'turn-up-time'" in router,
        "build work enters Turn Up Time",
    )
    add("router-no-legacy-loop", "engineering-loop" not in router, "legacy loop absent")
    add("router-no-direct-omnidex", "route = 'omnidex'" not in router, "no planning bypass")
    add("router-no-direct-boil", "route = 'boil-the-ocean'" not in router, "no build bypass")

    registry = json.loads(
        (CLAUDE_DIR / "capabilities" / "registry.json").read_text(encoding="utf-8")
    )
    add(
        "registry-json-only",
        not (CLAUDE_DIR / "capabilities" / "registry.yaml").exists(),
        "one registry",
    )
    for name, capability in registry["capabilities"].items():
        add(
            "capability-eval-" + name,
            bool(capability.get("evals")),
            str(capability.get("evals")),
        )
        add(
            "capability-uninstall-" + name,
            bool(capability.get("uninstall")),
            capability.get("uninstall", ""),
        )
        add(
            "capability-authority-" + name,
            capability.get("authority")
            in {"control", "production", "assurance", "reference"},
            str(capability.get("authority")),
        )
        if capability.get("bundled"):
            add(
                "bundled-provider-" + name,
                (CLAUDE_DIR / "skills" / capability["provider"] / "SKILL.md").is_file(),
                capability["provider"],
            )

    install = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
    uninstall = (ROOT / "scripts" / "uninstall.ps1").read_text(encoding="utf-8")
    for marker in (
        "[switch]$Apply",
        "BackupRoot",
        "turn-up-time-install-manifest.json",
        "installed_sha256",
        "skill-router.ps1",
    ):
        add(
            "installer-" + re.sub(r"[^a-z0-9]+", "-", marker.lower()).strip("-"),
            marker in install,
            marker,
        )
    add(
        "uninstall-hash-safe",
        "installed_sha256" in uninstall and "SKIP MODIFIED" in uninstall,
        "modified installed files are preserved",
    )
    add(
        "uninstall-removes-router-only",
        "skill-router.ps1" in uninstall and "UserPromptSubmit" in uninstall,
        "settings cleanup is targeted",
    )

    required_scripts = (
        "resolve_capabilities.py",
        "validate_project.py",
        "scaffold_project.py",
        "validate_repo.py",
        "run_seeded_evals.py",
    )
    for name in required_scripts:
        add("script-" + name, (CLAUDE_DIR / "scripts" / name).is_file(), name)

    patterns = {
        "github-token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
        "api-key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
        "aws-key": re.compile(r"AKIA[0-9A-Z]{16}"),
        "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "windows-user": re.compile(r"C:\\Users\\[^\\\s]+", re.I),
        "company-domain": re.compile(r"teamtag\.com", re.I),
    }
    all_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts
    )
    for name, pattern in patterns.items():
        add("scan-" + name, not pattern.search(all_text), "no match")

    broken: list[str] = []
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        for target in link_pattern.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            relative = target.split("#", 1)[0]
            if relative and not (path.parent / relative).resolve().exists():
                broken.append(f"{path.relative_to(ROOT)} -> {target}")
    add("relative-links", not broken, "; ".join(broken[:5]) or "all resolved")

    failed = [item for item in CHECKS if not item[1]]
    for name, ok, detail in CHECKS:
        print(("PASS" if ok else "FAIL"), name, "-", detail)
    print(f"FRESH REVIEW: {len(CHECKS)-len(failed)}/{len(CHECKS)} passed")

    if args.write_report:
        lines = [
            "# Fresh workflow review",
            "",
            f"**Verdict: {'GREEN' if not failed else 'RED'} — {len(CHECKS)-len(failed)}/{len(CHECKS)} checks passed.**",
            "",
            "## Checks",
            "",
        ]
        for name, ok, detail in CHECKS:
            lines.append(f"- [{'x' if ok else ' '}] `{name}` — {detail}")
        lines += [
            "",
            "## Limits",
            "",
            "- This deterministic cold pass is not a separate model judgment.",
            "- Windows PowerShell behavior is exercised in the Windows CI job.",
            "- Optional external providers are intentionally not vendored.",
            "",
        ]
        args.report_path.write_text("\n".join(lines), encoding="utf-8")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
