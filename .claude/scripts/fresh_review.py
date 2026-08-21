#!/usr/bin/env python3
"""Cold deterministic review of the final workflow tree.

This reviewer does not share build state. It invokes the actual validators, then performs a separate
structural and hygiene pass. Use --write-report to refresh docs/REVIEW-REPORT.md.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
CLAUDE_DIR = ROOT / ".claude"
checks: list[tuple[str, bool, str]] = []


def add(name: str, ok: bool, detail: str) -> None:
    checks.append((name, bool(ok), detail))


def run_script(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CLAUDE_DIR / "scripts" / name)], cwd=ROOT, text=True, capture_output=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    static = run_script("validate_repo.py")
    seeded = run_script("run_seeded_evals.py")
    add("repository-validator", static.returncode == 0, static.stdout.strip().splitlines()[-1] if static.stdout else static.stderr.strip())
    add("seeded-process-evals", seeded.returncode == 0, seeded.stdout.strip().splitlines()[-1] if seeded.stdout else seeded.stderr.strip())

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    add("single-constitution", "one constitution" in claude.lower() and "Canonical Operating Contract" in claude, "CLAUDE.md declares authority")
    add("readme-counts", "10 skills" in readme and "17" in readme and "9 machine-readable schemas" in readme, "README inventory matches validator")

    for stage in ("Route/intake", "Discovery", "Definition/tickets", "Seam review", "Build", "Product closeout", "Release", "Workflow closeout"):
        add("owner-" + stage.lower().replace("/", "-").replace(" ", "-"), stage in architecture, f"architecture names owner for {stage}")

    frontmatter_pattern = re.compile(r"^---\n(.*?)\n---\n", re.S)
    assurance_tokens = ("researcher", "auditor", "architect", "integration-lead", "irritated-domain-user", "functional-qa", "reviewer", "triage-lead", "ticket-verifier", "judge")
    for path in sorted((CLAUDE_DIR / "agents").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = frontmatter_pattern.match(text)
        frontmatter = yaml.safe_load(match.group(1)) if match else {}
        name = frontmatter.get("name", path.stem)
        tools = set(frontmatter.get("tools") or [])
        if any(token in name for token in assurance_tokens) and name != "implementation-engineer":
            add("readonly-" + name, not tools.intersection({"Edit", "Write", "MultiEdit", "NotebookEdit"}), f"tools={sorted(tools)}")
        add("profile-" + name, all(section in text for section in ("## Mission", "## Inputs", "## Required procedure", "## Output contract", "## Stop or escalate", "## Boundaries")), "complete role contract")

    router = (CLAUDE_DIR / "hooks" / "skill-router.ps1").read_text(encoding="utf-8").lower()
    add("router-control-plane", "route = 'turn-up-time'" in router, "build work enters Turn Up Time")
    add("router-no-retired-loop", "engineering-loop" not in router, "retired router absent")
    add("router-no-bypass", "route = 'omnidex'" not in router and "route = 'boil-the-ocean'" not in router, "downstream stages cannot be auto-routed")

    flows = {
        "turn-up-time": ("scaffold_project.py", "validate_project.py", "advance_stage.py"),
        "omnidex": ("TICKETING", "AWAITING_HUMAN", "definition-of-good.json"),
        "boil-the-ocean": ("resolve_capabilities.py", "CAPABILITY_PROVIDER_MISSING"),
        "easily-irritated": ("finding.schema.json", "verdict.json"),
        "production-audit": ("fresh-release-judge", "final-judge.json"),
        "its-not-you-its-me": ("improvement-proposal.schema.json", "human approval"),
        "plug-it-in": ("registry.json", "resolve_capabilities.py"),
    }
    for skill, markers in flows.items():
        text = (CLAUDE_DIR / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        add("flow-" + skill, all(marker.lower() in text.lower() for marker in markers), ", ".join(markers))

    registry = json.loads((CLAUDE_DIR / "capabilities" / "registry.json").read_text(encoding="utf-8"))["capabilities"]
    for name, capability in registry.items():
        add("cap-" + name + "-eval", bool(capability.get("eval")), capability.get("eval", "missing"))
        add("cap-" + name + "-uninstall", bool(capability.get("uninstall")), capability.get("uninstall", "missing"))
        if capability.get("bundled"):
            add("cap-" + name + "-provider", (CLAUDE_DIR / "skills" / capability["provider"] / "SKILL.md").exists(), capability["provider"])

    install = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
    uninstall = (ROOT / "scripts" / "uninstall.ps1").read_text(encoding="utf-8")
    add("installer-explicit-constitution", "KeepGlobalConstitution" in install and "ReplaceGlobalConstitution" in install, "apply requires explicit constitution choice when one exists")
    add("installer-registers-guard", "destructive-command-guard.ps1" in install and "PreToolUse" in install, "global destructive guard is wired")
    add("installer-hash-manifest", "installedSha256" in install, "installed content hashes recorded")
    add("uninstaller-preserves-modified", "SKIP MODIFIED" in uninstall and "ForceModified" in uninstall, "user edits are not deleted silently")

    patterns = {
        "github-token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
        "openai-key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
        "aws-key": re.compile(r"AKIA[0-9A-Z]{16}"),
        "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "windows-user": re.compile(r"C:\\Users\\[^\\\s]+", re.I),
        "company-domain": re.compile(r"teamtag\.com", re.I),
    }
    all_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts)
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
            local = target.split("#", 1)[0]
            if local and not (path.parent / local).resolve().exists():
                broken.append(f"{path.relative_to(ROOT)} -> {target}")
    add("relative-links", not broken, "; ".join(broken[:5]) or "all resolved")

    failed = [check for check in checks if not check[1]]
    for name, ok, detail in checks:
        print(("PASS" if ok else "FAIL"), name, "-", detail)
    print(f"FRESH REVIEW: {len(checks) - len(failed)}/{len(checks)} passed")

    if args.write_report:
        report = [
            "# Fresh review report", "",
            "This cold deterministic pass invokes the real repository validator and seeded process evals, then independently inspects role authority, stage connections, capability contracts, installation safety, secrets, and links.", "",
            f"**Verdict: {'GREEN' if not failed else 'RED'} — {len(checks) - len(failed)}/{len(checks)} checks passed.**", "", "## Checks", ""
        ]
        for name, ok, detail in checks:
            report.append(f"- [{'x' if ok else ' '}] `{name}` — {detail}")
        report.extend(["", "## Limits", "", "- This deterministic reviewer does not replace the separately launched read-only Claude reviewer.", "- External capability providers are not bundled; provider behavior is evaluated when `/plug-it-in` activates one.", ""])
        (ROOT / "docs" / "REVIEW-REPORT.md").write_text("\n".join(report), encoding="utf-8")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
