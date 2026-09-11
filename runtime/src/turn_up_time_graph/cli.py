from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from langgraph.types import Command

from .approvals import approval_request, verify_approval
from .exceptions import TurnUpTimeGraphError
from .graph import build_graph, initial_state
from .ledger import load_ledger
from .models import EventSignal
from .operations import OPERATIONS, apply_operation
from .persistence import sqlite_checkpointer
from .render import render
from .topology import TRANSITION_INDEX, Stage, expected_events, validate_topology
from .transactions import lookup, replay
from .workspace import project_file
from .validation import ensure_checkpoint_ledger_alignment, validate_event_payload, validate_project_for_target


def _paths(args) -> tuple[Path, Path]:
    repo_root = Path(args.repo_root or Path.cwd()).resolve()
    project_dir = Path(args.project_dir).resolve()
    try:
        project_dir.relative_to(repo_root)
    except ValueError as exc:
        raise TurnUpTimeGraphError("project-dir must be inside repo-root") from exc
    return repo_root, project_dir


def _config(project_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": project_id}}


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def _payload(args) -> dict[str, Any]:
    if not args.event_id:
        raise TurnUpTimeGraphError("--event-id is required: retain it for retries and approval binding")
    data_file = getattr(args, "data_file", None)
    if data_file and getattr(args, "data_json", "{}") != "{}":
        raise TurnUpTimeGraphError("choose --data-file or --data-json, not both")
    data = json.loads(project_file(Path(args.project_dir), data_file).read_text(encoding="utf-8-sig")
                      if data_file else getattr(args, "data_json", "{}"))
    return EventSignal(
        event=args.event, event_id=args.event_id, approved_by=getattr(args, "approved_by", None),
        approval_ref=getattr(args, "approval_ref", None),
        evidence_delta=getattr(args, "evidence_delta", None) or [],
        receipt_refs=getattr(args, "receipt_ref", None) or [], data=data,
    ).model_dump()


async def _ensure_started(graph, state, config):
    snapshot = await graph.aget_state(config)
    if not snapshot.values:
        await graph.ainvoke(state, config)
        snapshot = await graph.aget_state(config)
    project = Path(state["project_dir"])
    if snapshot.next and replay(project, snapshot.values["ledger_sha256"], snapshot.values.get("last_event_id")):
        # Replay only when the journal proves a committed/authorized successor.
        # Do not blindly rerun a failed agent or a rejected signal.
        await graph.ainvoke(None, config)
        snapshot = await graph.aget_state(config)
    ensure_checkpoint_ledger_alignment(project, snapshot.values["stage"], snapshot.values.get("ledger_sha256"))
    return snapshot


async def command_signal(args) -> int:
    repo, project = _paths(args)
    payload = _payload(args)
    project_id = load_ledger(project)["project_id"]
    async with sqlite_checkpointer(repo) as saver:
        graph, config = build_graph(saver), _config(project_id)
        snapshot = await _ensure_started(graph, initial_state(repo, project), config)
        previous = lookup(project, payload["event_id"], payload)
        if previous is not None:
            _print({"status": "ALREADY_APPLIED", "event_id": payload["event_id"], "original_result": previous,
                    "current_stage": load_ledger(project)["stage"]})
            return 0
        if not snapshot.next:
            raise TurnUpTimeGraphError("project is terminal; no new signal may advance it")
        # Preflight before supplying a resume value. The node repeats validation
        # at the locked commit boundary; this is not a replacement for that check.
        if payload["event"] not in OPERATIONS:
            transition = TRANSITION_INDEX.get((Stage(snapshot.values["stage"]), payload["event"]))
            if transition is None:
                raise TurnUpTimeGraphError("illegal event for the current stage")
            validate_event_payload(transition, payload)
            validate_project_for_target(repo, project, transition.target)
            if transition.human_gate:
                verify_approval(repo, project, transition, payload)
        else:
            apply_operation(repo, project, load_ledger(project), payload["event"], payload["data"])
        result = await graph.ainvoke(Command(resume=payload), config)
        latest = await graph.aget_state(config)
        _print({"result": result, "next": list(latest.next),
                "interrupts": [item.value for task in latest.tasks for item in task.interrupts]})
    return 0


def command_request_approval(args) -> int:
    repo, project = _paths(args)
    payload = _payload(args)
    transition = TRANSITION_INDEX.get((Stage(load_ledger(project)["stage"]), payload["event"]))
    if transition is None:
        raise TurnUpTimeGraphError("illegal event for the current stage")
    validate_event_payload(transition, payload)
    _print(approval_request(repo, project, transition, payload))
    return 0


async def command_recover(args) -> int:
    repo, project = _paths(args)
    async with sqlite_checkpointer(repo) as saver:
        graph = build_graph(saver)
        snapshot = await _ensure_started(graph, initial_state(repo, project), _config(load_ledger(project)["project_id"]))
        _print({"status": "RECOVERED_OR_ALREADY_ALIGNED", "stage": snapshot.values["stage"], "next": list(snapshot.next)})
    return 0


async def command_status(args) -> int:
    repo, project = _paths(args)
    ledger = load_ledger(project)
    async with sqlite_checkpointer(repo) as saver:
        snapshot = await build_graph(saver).aget_state(_config(ledger["project_id"]))
        _print({"ledger": ledger, "checkpoint": {
            "exists": bool(snapshot.values), "next": list(snapshot.next), "values": snapshot.values,
            "interrupts": [item.value for task in snapshot.tasks for item in task.interrupts],
        }})
    return 0


async def command_history(args) -> int:
    repo, project = _paths(args)
    rows = []
    async with sqlite_checkpointer(repo) as saver:
        graph = build_graph(saver)
        async for snapshot in graph.aget_state_history(_config(load_ledger(project)["project_id"]), limit=args.limit):
            rows.append({"created_at": snapshot.created_at, "next": list(snapshot.next),
                         "stage": snapshot.values.get("stage") if snapshot.values else None,
                         "last_event": snapshot.values.get("last_event") if snapshot.values else None,
                         "config": snapshot.config})
    _print(rows)
    return 0


def command_validate_topology(args) -> int:
    errors = validate_topology()
    if errors:
        _print({"status": "RED", "errors": errors})
        return 1
    _print({"status": "GREEN", "stages": [stage.value for stage in Stage],
            "expected_events": {stage.value: list(expected_events(stage)) for stage in Stage},
            "control_operations": sorted(OPERATIONS)})
    return 0


def command_render(args) -> int:
    paths = render(Path(args.repo_root or Path.cwd()).resolve())
    _print({"status": "GREEN", "files": [str(path) for path in paths]})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="turn-up-time-graph")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate-topology").set_defaults(handler=command_validate_topology)
    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--repo-root")
    render_parser.set_defaults(handler=command_render)
    for name in ("signal", "request-approval", "recover", "status", "history"):
        command = subparsers.add_parser(name)
        command.add_argument("--repo-root")
        command.add_argument("--project-dir", required=True)
        if name in {"signal", "request-approval"}:
            command.add_argument("--event", required=True)
            command.add_argument("--event-id")
            command.add_argument("--approved-by")
            command.add_argument("--approval-ref")
            command.add_argument("--evidence-delta", action="append")
            command.add_argument("--receipt-ref", action="append")
            command.add_argument("--data-json", default="{}", help="JSON object for a control operation")
            command.add_argument("--data-file", help="project-relative JSON file; avoids PowerShell quoting issues")
            command.set_defaults(handler=command_signal if name == "signal" else command_request_approval)
        elif name == "recover":
            command.set_defaults(handler=command_recover)
        elif name == "status":
            command.set_defaults(handler=command_status)
        else:
            command.add_argument("--limit", type=int, default=20)
            command.set_defaults(handler=command_history)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = args.handler(args)
        if asyncio.iscoroutine(result):
            result = asyncio.run(result)
    except (TurnUpTimeGraphError, ValueError, OSError) as exc:
        _print({"status": "RED", "error": str(exc)})
        raise SystemExit(1) from exc
    raise SystemExit(result)


if __name__ == "__main__":
    main()
