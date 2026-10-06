from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .approvals import verify_approval
from .events import utc_now
from .ledger import apply_transition_to_ledger, ledger_sha256, load_ledger
from .models import EventSignal
from .operations import OPERATIONS, apply_operation
from .state import GauntletState
from .topology import TERMINAL_STAGES, TRANSITION_INDEX, TRANSITIONS, Stage, expected_events
from .transactions import execute, latest_update, replay
from .validation import (
    TransitionError, ensure_checkpoint_ledger_alignment, validate_event_payload,
    validate_project_for_target, validate_runtime_topology,
)
from .workspace import project_file


def _node_name(stage: Stage) -> str:
    return stage.value.lower()


def _project_paths(state: GauntletState) -> tuple[Path, Path]:
    return Path(state["repo_root"]), Path(state["project_dir"])


def _transition_update(state: GauntletState, transition, payload: dict[str, Any]) -> dict[str, Any]:
    repo_root, project_dir = _project_paths(state)
    def prepare():
        validate_event_payload(transition, payload)
        validate_project_for_target(repo_root, project_dir, transition.target)
        for reference in payload.get("receipt_refs", []):
            project_file(project_dir, reference)
        # Signed approval is checked at the actual transition, not merely at intake.
        approver = verify_approval(repo_root, project_dir, transition, payload) if transition.human_gate else None
        counts = dict(state.get("loop_counts") or {})
        if transition.loop_id:
            next_count = counts.get(transition.loop_id, 0) + 1
            if transition.max_traversals is not None and next_count > transition.max_traversals:
                raise TransitionError(f"loop {transition.loop_id} exhausted at {transition.max_traversals} traversals")
            counts[transition.loop_id] = next_count
        receipt_refs = list(payload.get("receipt_refs", []))
        if payload.get("approval_ref"):
            receipt_refs.append(payload["approval_ref"])
        ledger = apply_transition_to_ledger(project_dir, transition, event_id=payload["event_id"],
                                           approved_by=approver, receipt_refs=receipt_refs, write=False)
        event = {
            "schema_version": 1, "event_id": payload["event_id"], "event_type": "EDGE_TRAVERSED",
            "project_id": state["project_id"], "thread_id": state["thread_id"],
            "from_stage": transition.source.value, "to_stage": transition.target.value,
            "trigger": transition.event, "verdict": transition.verdict, "loop_id": transition.loop_id,
            "iteration": counts.get(transition.loop_id) if transition.loop_id else None,
            "approved_by": approver, "evidence_delta": payload.get("evidence_delta", []),
            "receipt_refs": receipt_refs, "occurred_at": utc_now(),
        }
        update = {"stage": transition.target.value, "status": ledger["status"], "loop_counts": counts,
                  "last_event": transition.event,
                  "messages": [f"{transition.source.value} --{transition.event}--> {transition.target.value}"]}
        return ledger, event, update
    return execute(project_dir, payload, state["ledger_sha256"], state.get("last_event_id"), prepare)


def _operation_update(state: GauntletState, payload: dict[str, Any]) -> dict[str, Any]:
    repo, project = _project_paths(state)
    def prepare():
        ledger = apply_operation(repo, project, load_ledger(project), payload["event"], payload["data"])
        event = {
            "schema_version": 1, "event_id": payload["event_id"], "event_type": "CONTROL_OPERATION",
            "project_id": state["project_id"], "thread_id": state["thread_id"],
            "from_stage": state["stage"], "to_stage": state["stage"], "trigger": payload["event"],
            "verdict": "RECORDED", "loop_id": None, "iteration": None, "approved_by": None,
            "evidence_delta": [], "receipt_refs": [], "occurred_at": utc_now(),
        }
        return ledger, event, {"stage": state["stage"], "status": ledger["status"],
                               "loop_counts": dict(state.get("loop_counts") or {}),
                               "last_event": payload["event"], "messages": [f"recorded:{payload['event']}"]}
    return execute(project, payload, state["ledger_sha256"], state.get("last_event_id"), prepare)


def _make_stage_node(stage: Stage):
    async def stage_node(state: GauntletState) -> Command:
        _, project_dir = _project_paths(state)
        recovered = replay(project_dir, state["ledger_sha256"], state.get("last_event_id"))
        if recovered is not None:
            return Command(goto=_node_name(Stage(recovered["stage"])), update=recovered)
        ensure_checkpoint_ledger_alignment(project_dir, stage.value, state.get("ledger_sha256"))
        raw = interrupt({
            "kind": "turn-up-time-event", "project_id": state["project_id"], "stage": stage.value,
            "expected_events": list(expected_events(stage)), "control_operations": sorted(OPERATIONS),
            "human_gates": sorted({t.human_gate for t in TRANSITIONS if t.source == stage and t.human_gate}),
        })
        if not isinstance(raw, dict):
            raise TransitionError("resume payload must be an object")
        try:
            payload = EventSignal.model_validate(raw).model_dump()
        except ValueError as exc:
            raise TransitionError(f"invalid graph signal: {exc}") from exc
        event_name = payload["event"]
        if event_name in OPERATIONS:
            update = _operation_update(state, payload)
            return Command(goto=_node_name(stage), update=update)
        transition = TRANSITION_INDEX.get((stage, event_name))
        if transition is None:
            raise TransitionError(f"illegal event {event_name!r} from {stage.value}; expected {expected_events(stage)}")
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
    builder.add_node("entry", _entry, destinations=tuple(_node_name(stage) for stage in Stage))
    builder.add_edge(START, "entry")
    for stage in Stage:
        name = _node_name(stage)
        if stage in TERMINAL_STAGES:
            builder.add_node(name, _terminal)
            builder.add_edge(name, END)
            continue
        # Bookkeeping can revisit the SAME stage but cannot invent a stage edge.
        destinations = tuple(sorted({name} | {_node_name(t.target) for t in TRANSITIONS if t.source == stage}))
        builder.add_node(name, _make_stage_node(stage), destinations=destinations)
    return builder.compile(checkpointer=checkpointer)


def initial_state(repo_root: Path, project_dir: Path) -> GauntletState:
    recovered = latest_update(project_dir)
    ledger = load_ledger(project_dir)
    project_id = ledger["project_id"]
    state = {
        "project_id": project_id, "project_dir": str(project_dir.resolve()),
        "repo_root": str(repo_root.resolve()), "stage": ledger["stage"], "status": ledger["status"],
        "profile": ledger["profile"], "thread_id": project_id, "loop_counts": {},
        "blockers": list(ledger.get("blockers", [])), "last_event_id": None, "last_event": None,
        "last_transition": None, "messages": [], "ledger_sha256": ledger_sha256(project_dir),
    }
    if recovered:
        state.update(recovered)
    return state
