from __future__ import annotations

import json
from pathlib import Path

from .topology import Stage, TRANSITIONS


def _edge_label(transition) -> str:
    parts = [transition.event, transition.verdict]
    if transition.loop_id:
        parts.append(f"loop:{transition.loop_id} {transition.max_traversals}x")
    if transition.human_gate:
        parts.append(f"human:{transition.human_gate}")
    if transition.requires_new_evidence:
        parts.append("new-evidence")
    return "<br/>".join(parts)


def render(repo_root: Path) -> tuple[Path, Path]:
    generated = repo_root / "docs" / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    mermaid_path = generated / "workflow.mmd"
    json_path = generated / "workflow.json"

    lines = ["flowchart TD"]
    for stage in Stage:
        lines.append(f'    {stage.value}["{stage.value}"]')
    for transition in TRANSITIONS:
        lines.append(
            f'    {transition.source.value} -->|"{_edge_label(transition)}"| {transition.target.value}'
        )
    mermaid_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload = {
        "schema_version": 1,
        "transitions": [transition.to_json() for transition in TRANSITIONS],
    }
    json_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return mermaid_path, json_path
