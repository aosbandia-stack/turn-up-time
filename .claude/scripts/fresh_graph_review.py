#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
checks: list[tuple[str, bool, str]] = []


def add(name: str, ok: bool, detail: str) -> None:
    checks.append((name, bool(ok), detail))


def run(name: str, command: list[str], cwd: Path = ROOT) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    add(name, result.returncode == 0, (result.stdout + result.stderr).strip()[-2000:])


run("repository-contract", [sys.executable, ".claude/scripts/validate_repo.py"])
run("seeded-process-evals", [sys.executable, ".claude/scripts/run_seeded_evals.py"])
run("runtime-pytest", [sys.executable, "-m", "pytest", "-q", "runtime/tests"])
run("topology-validation", [sys.executable, "-m", "turn_up_time_graph.cli", "validate-topology"])
run("topology-render", [sys.executable, "-m", "turn_up_time_graph.cli", "render", "--repo-root", str(ROOT)])

# Structural review independent of runtime assertions.
topology_path = ROOT / "runtime/src/turn_up_time_graph/topology.py"
topology_source = topology_path.read_text(encoding="utf-8")
ast.parse(topology_source)
for marker in (
    "human_gate=\"TICKETS\"",
    "human_gate=\"RELEASE\"",
    "loop_id=\"discovery-premise-repair\"",
    "loop_id=\"integration-repair\"",
    "loop_id=\"closeout-repair\"",
    "requires_new_evidence=True",
):
    add(f"topology-marker-{marker}", marker in topology_source, marker)

install = (ROOT / "scripts/install.ps1").read_text(encoding="utf-8")
uninstall = (ROOT / "scripts/uninstall.ps1").read_text(encoding="utf-8")
add("installer-graph-switch", "EnableGraphRuntime" in install, "graph runtime is opt-in and explicit")
add("installer-ps51-trim", "[char[]]@([char]92, [char]47)" in install, "PS5.1-safe TrimStart")
add("installer-runtime-marker", "runtime-manifest.json" in install, "owned runtime marker")
add("uninstaller-modified-safe", "SKIP MODIFIED GRAPH RUNTIME" in uninstall, "modified runtime is not silently deleted")
add("uninstaller-removes-owned-runtime", "Remove-Item -LiteralPath $runtime.home -Recurse -Force" in uninstall, "owned runtime removal")

# Rendered machine graph must validate against its contract.
workflow_json = ROOT / "docs/generated/workflow.json"
workflow_schema = ROOT / ".claude/schemas/workflow-graph.schema.json"
if workflow_json.exists():
    value = json.loads(workflow_json.read_text())
    contract = json.loads(workflow_schema.read_text())
    errors = list(Draft202012Validator(contract).iter_errors(value))
    add("workflow-artifact-schema", not errors, "; ".join(error.message for error in errors[:5]) or "valid")
else:
    add("workflow-artifact-schema", False, "render did not produce workflow.json")

failed = [item for item in checks if not item[1]]
for name, ok, detail in checks:
    print(("PASS" if ok else "FAIL"), name, "-", detail)
print(f"FRESH GRAPH REVIEW: {len(checks)-len(failed)}/{len(checks)} passed")

report = [
    "# Fresh graph-runtime review",
    "",
    "This deterministic cold pass reruns the official validators from the final tree and separately inspects graph, install, and artifact contracts.",
    "",
    f"**Verdict: {'GREEN' if not failed else 'RED'} — {len(checks)-len(failed)}/{len(checks)} checks passed.**",
    "",
    "## Checks",
    "",
]
for name, ok, detail in checks:
    report.append(f"- [{'x' if ok else ' '}] `{name}` — {detail}")
report += [
    "",
    "## Boundary",
    "",
    "This is deterministic structural and behavioral verification. A separate fresh Claude Code model review remains useful for judgment quality, but it is not permitted to overwrite this evidence.",
    "",
]
(ROOT / "docs/GRAPH-REVIEW-REPORT.md").write_text("\n".join(report), encoding="utf-8")
raise SystemExit(1 if failed else 0)
