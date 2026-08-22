from __future__ import annotations

import json
from pathlib import Path

from .graph import build_graph
from .topology import TRANSITIONS


def render(repo_root: Path) -> tuple[Path, Path]:
    generated = repo_root / "docs" / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    graph = build_graph()
    mermaid_path = generated / "workflow.mmd"
    json_path = generated / "workflow.json"
    mermaid_path.write_text(graph.get_graph().draw_mermaid() + "\n", encoding="utf-8")
    payload = {
        "schema_version": 1,
        "transitions": [transition.to_json() for transition in TRANSITIONS],
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return mermaid_path, json_path
