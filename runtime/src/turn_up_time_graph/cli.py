from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from langgraph.types import Command

from .graph import build_graph, initial_state
from .ledger import load_ledger
from .persistence import sqlite_checkpointer
from .render import render
from .topology import Stage, expected_events, validate_topology


def _paths(args) -> tuple[Path, Path]:
    repo_root = Path(args.repo_root or Path.cwd()).resolve()
    project_dir = Path(args.project_dir).resolve()
    return repo_root, project_dir


def _config(project_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": project_id}}


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


async def _ensure_started(graph, state, config):
    snapshot = await graph.aget_state(config)
    if snapshot.values:
        return snapshot
    await graph.ainvoke(state, config)
    return await graph.aget_state(config)


async def command_signal(args) -> int:
    repo_root, project_dir = _paths(args)
    ledger = load_ledger(project_dir)
    project_id = ledger["project_id"]
    payload = {
        "event": args.event,
        "event_id": args.event_id or str(uuid.uuid4()),
        "approved_by": args.approved_by,
        "evidence_delta": args.evidence_delta or [],
        "receipt_refs": args.receipt_ref or [],
    }
    async with sqlite_checkpointer(repo_root) as saver:
        graph = build_graph(saver)
        config = _config(project_id)
        state = initial_state(repo_root, project_dir)
        snapshot = await _ensure_started(graph, state, config)
        if not snapshot.next:
            raise RuntimeError(f"thread is not waiting for an event; next={snapshot.next}")
        result = await graph.ainvoke(Command(resume=payload), config)
        latest = await graph.aget_state(config)
        _print(
            {
                "result": result,
                "next": list(latest.next),
                "interrupts": [
                    item.value for task in latest.tasks for item in task.interrupts
                ],
            }
        )
    return 0


async def command_status(args) -> int:
    repo_root, project_dir = _paths(args)
    ledger = load_ledger(project_dir)
    project_id = ledger["project_id"]
    async with sqlite_checkpointer(repo_root) as saver:
        graph = build_graph(saver)
        snapshot = await graph.aget_state(_config(project_id))
        _print(
            {
                "ledger": ledger,
                "checkpoint": {
                    "exists": bool(snapshot.values),
                    "next": list(snapshot.next),
                    "values": snapshot.values,
                    "interrupts": [
                        item.value
                        for task in snapshot.tasks
                        for item in task.interrupts
                    ],
                },
            }
        )
    return 0


async def command_history(args) -> int:
    repo_root, project_dir = _paths(args)
    project_id = load_ledger(project_dir)["project_id"]
    rows = []
    async with sqlite_checkpointer(repo_root) as saver:
        graph = build_graph(saver)
        async for snapshot in graph.aget_state_history(
            _config(project_id), limit=args.limit
        ):
            rows.append(
                {
                    "created_at": snapshot.created_at,
                    "next": list(snapshot.next),
                    "stage": snapshot.values.get("stage") if snapshot.values else None,
                    "last_event": snapshot.values.get("last_event") if snapshot.values else None,
                    "config": snapshot.config,
                }
            )
    _print(rows)
    return 0


def command_validate_topology(args) -> int:
    errors = validate_topology()
    if errors:
        _print({"status": "RED", "errors": errors})
        return 1
    _print(
        {
            "status": "GREEN",
            "stages": [stage.value for stage in Stage],
            "expected_events": {
                stage.value: list(expected_events(stage)) for stage in Stage
            },
        }
    )
    return 0


def command_render(args) -> int:
    repo_root = Path(args.repo_root or Path.cwd()).resolve()
    paths = render(repo_root)
    _print({"status": "GREEN", "files": [str(path) for path in paths]})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="turn-up-time-graph")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-topology")
    validate.set_defaults(handler=command_validate_topology)

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--repo-root")
    render_parser.set_defaults(handler=command_render)

    for name in ("signal", "status", "history"):
        command = subparsers.add_parser(name)
        command.add_argument("--repo-root")
        command.add_argument("--project-dir", required=True)
        if name == "signal":
            command.add_argument("--event", required=True)
            command.add_argument("--event-id")
            command.add_argument("--approved-by")
            command.add_argument("--evidence-delta", action="append")
            command.add_argument("--receipt-ref", action="append")
            command.set_defaults(handler=command_signal)
        elif name == "status":
            command.set_defaults(handler=command_status)
        else:
            command.add_argument("--limit", type=int, default=20)
            command.set_defaults(handler=command_history)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = args.handler(args)
    if asyncio.iscoroutine(result):
        raise SystemExit(asyncio.run(result))
    raise SystemExit(result)


if __name__ == "__main__":
    main()
