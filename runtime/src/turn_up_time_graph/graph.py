from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .events import append_event, utc_now
from .ledger import apply_transition_to_ledger, ledger_sha256, load_ledger
from .state import GauntletState
from .topology import (
    TERMINAL_STAGES,
    TRANSITION_INDEX,
    TRANSITIONS,
    Stage,
    expected_events,
)
from .validation import (
    TransitionError,
    ensure_checkpoint_ledger_alignment,
    validate_event_payload,
    validate_project_for_target,
    validate_runtime_topology,
)


def _node_name(stage: Stage) -> str:
    return stage.value.lower()


def _project_paths(state: GauntletState) -> tuple[Path, Path]:
    return Path(state["repo_root"]), Path(state["project_dir"])


def _transition_update(
    state: GauntletState, transition, payload: dict[str, Any]
) -> dict[str, Any]:
    repo_root, project_dir = _project_paths(state)
    validate_event_payload(transition, payload)
    validate_project_for_target(repo_root, project_dir, transition.target)
    counts = dict(state.get("loop_counts") or {})
    if transition.loop_id:
        next_count = counts.get(transition.loop_id, 0) + 1
        if transition.max_traversals is not None and next_count > transition.max_traversals:
            raise TransitionError(
                f"loop {transition.loop_id} exhausted at {transition.max_traversals} traversals"
            )
        counts[transition.loop_id] = next_count
    receipt_refs = [str(item) for item in payload.get("receipt_refs", [])]
    before_sha = ledger_sha256(project_dir)
    ledger = apply_transition_to_ledger(
        project_dir,
        transition,
        event_id=payload["event_id"],
        approved_by=payload.get("approved_by"),
        receipt_refs=receipt_refs,
    )
    after_sha = ledger_sha256(project_dir)
    graph_event = {
        "schema_version": 1,
        "event_id": payload["event_id"],
        "event_type": "EDGE_TRAVERSED",
        "project_id": state["project_id"],
        "thread_id": state["thread_id"],
        "from_stage": transition.source.value,
        "to_stage": transition.target.value,
        "trigger": transition.event,
        "verdict": transition.verdict,
        "loop_id": transition.loop_id,
        "iteration": counts.get(transition.loop_id) if transition.loop_id else None,
        "approved_by": payload.get("approved_by"),
        "evidence_delta": payload.get("evidence_delta", []),
        "receipt_refs": receipt_refs,
        "ledger_sha256_before": before_sha,
        "ledger_sha256_after": after_sha,
        "occurred_at": utc_now(),
    }
    append_event(project_dir / "events.jsonl", graph_event)
    return {
        "stage": transition.target.value,
        "status": ledger["status"],
        "loop_counts": counts,
        "last_event_id": payload["event_id"],
        "last_event": transition.event,
        "last_transition": graph_event,
        "messages": [
            f"{transition.source.value} --{transition.event}--> {transition.target.value}"
        ],
        "ledger_sha256": after_sha,
    }


def _make_stage_node(stage: Stage):
    async def stage_node(state: GauntletState) -> Command:
        _, project_dir = _project_paths(state)
        ensure_checkpoint_ledger_alignment(
            project_dir, stage.value, state.get("ledger_sha256")
        )
        payload = interrupt(
            {
                "kind": "turn-up-time-event",
                "project_id": state["project_id"],
                "stage": stage.value,
                "expected_events": list(expected_events(stage)),
                "human_gates": sorted(
                    {
                        transition.human_gate
                        for transition in TRANSITIONS
                        if transition.source == stage and transition.human_gate
                    }
                ),
            }
        )
        if not isinstance(payload, dict):
            raise TransitionError("resume payload must be an object")
        event_name = payload.get("event")
        if not isinstance(event_name, str):
            raise TransitionError("resume payload requires event")
        transition = TRANSITION_INDEX.get((stage, event_name))
        if transition is None:
            raise TransitionError(
                f"illegal event {event_name!r} from {stage.value}; expected {expected_events(stage)}"
            )
        update = _transition_update(state, transition, payload)
        return Command(goto=_node_name(transition.target), update=update)

    stage_node.__name__ = f"wait_{stage.value.lower()}"
    return stage_node


async def _entry(state: GauntletState) -> Command:
    return Command(goto=_node_name(Stage(state["stage"])))


async def _terminal(state: GauntletState) -> dict[str, Any]:
    return {"messages": [f"terminal:{state['stage']}"]}


def build_graph(checkpointer=None):
    validate_runtime_topology()
    builder = StateGraph(GauntletState)
    all_nodes = tuple(_node_name(stage) for stage in Stage)
    builder.add_node("entry", _entry, destinations=all_nodes)
    builder.add_edge(START, "entry")
    for stage in Stage:
        name = _node_name(stage)
        if stage in TERMINAL_STAGES:
            builder.add_node(name, _terminal)
            builder.add_edge(name, END)
            continue
        destinations = tuple(
            sorted({_node_name(t.target) for t in TRANSITIONS if t.source == stage})
        )
        builder.add_node(name, _make_stage_node(stage), destinations=destinations)
    return builder.compile(checkpointer=checkpointer)


def initial_state(repo_root: Path, project_dir: Path) -> GauntletState:
    ledger = load_ledger(project_dir)
    project_id = ledger["project_id"]
    return {
        "project_id": project_id,
        "project_dir": str(project_dir.resolve()),
        "repo_root": str(repo_root.resolve()),
        "stage": ledger["stage"],
        "status": ledger["status"],
        "profile": ledger["profile"],
        "thread_id": project_id,
        "loop_counts": {},
        "blockers": list(ledger.get("blockers", [])),
        "last_event_id": None,
        "last_event": None,
        "last_transition": None,
        "messages": [],
        "ledger_sha256": ledger_sha256(project_dir),
    }
