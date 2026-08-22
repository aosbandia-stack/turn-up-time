import json

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from turn_up_time_graph.graph import build_graph, initial_state


def _ledger():
    return {
        "schema_version": 2,
        "project_id": "pilot",
        "tier": "C",
        "profile": "standard",
        "stage": "INTAKE",
        "status": "ACTIVE",
        "objective": "pilot",
        "spawn_budget": {"limit": 5, "used": 0},
        "spawn_log": [],
        "decisions": [],
        "risks": [],
        "blockers": [],
        "artifacts": {},
        "approvals": [],
        "stage_history": [
            {
                "stage": "INTAKE",
                "entered_at": "2026-08-22T00:00:00Z",
                "exited_at": None,
                "verdict": None,
                "receipt_refs": [],
            }
        ],
        "build_identity": None,
    }


@pytest.mark.asyncio
async def test_interrupt_resume_advances_ledger(tmp_path):
    repo_root = tmp_path / "repo"
    project = repo_root / ".claude" / "projects" / "pilot"
    project.mkdir(parents=True)
    (project / "project-ledger.json").write_text(
        json.dumps(_ledger(), indent=2) + "\n", encoding="utf-8"
    )

    graph = build_graph(MemorySaver())
    config = {"configurable": {"thread_id": "pilot"}}
    await graph.ainvoke(initial_state(repo_root, project), config)
    waiting = await graph.aget_state(config)
    assert waiting.next == ("intake",)
    assert waiting.tasks[0].interrupts

    await graph.ainvoke(
        Command(
            resume={
                "event": "intake_ready",
                "event_id": "evt-intake-ready",
                "approved_by": "Harold",
                "receipt_refs": [],
                "evidence_delta": [],
            }
        ),
        config,
    )

    ledger = json.loads((project / "project-ledger.json").read_text())
    assert ledger["stage"] == "DISCOVERY"
    events = (project / "events.jsonl").read_text().splitlines()
    assert len(events) == 1
    assert json.loads(events[0])["trigger"] == "intake_ready"
