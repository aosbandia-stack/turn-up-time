import json

from turn_up_time_graph.ledger import apply_transition_to_ledger
from turn_up_time_graph.topology import Stage, TRANSITION_INDEX


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


def test_transition_updates_ledger(tmp_path):
    project = tmp_path / "pilot"
    project.mkdir()
    (project / "project-ledger.json").write_text(json.dumps(_ledger()))
    transition = TRANSITION_INDEX[(Stage.INTAKE, "intake_ready")]
    ledger = apply_transition_to_ledger(
        project,
        transition,
        event_id="evt",
        approved_by="Harold",
        receipt_refs=[],
    )
    assert ledger["stage"] == "DISCOVERY"
    assert ledger["stage_history"][-1]["stage"] == "DISCOVERY"
    assert ledger["approvals"][0]["gate"] == "INTAKE"
