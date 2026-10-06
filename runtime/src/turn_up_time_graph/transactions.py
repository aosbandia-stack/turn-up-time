"""Write-ahead operation journal for ledger, event log, and graph recovery.

SQLite persists an authorized intent BEFORE file projections. A process death at
any projection boundary can therefore finish that same operation on restart.
This is not an atomic transaction with LangGraph; the checkpoint is reconciled
by replaying the stored state update, without re-running the authorized action.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from .events import append_event, atomic_text
from .exceptions import TurnUpTimeGraphError


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def ledger_text(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def writer_lock(project: Path):
    directory = project / ".runtime"
    directory.mkdir(parents=True, exist_ok=True)
    # Never unlink this file: another process could otherwise lock a new inode.
    with (directory / "writer.lock").open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise TurnUpTimeGraphError("project writer is busy; retry the SAME event ID") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_UN)


@contextmanager
def _database(project: Path):
    path = project / ".runtime" / "operations.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("""CREATE TABLE IF NOT EXISTS operations (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE, request_sha TEXT NOT NULL,
            before_sha TEXT NOT NULL, previous_event_id TEXT,
            after_sha TEXT NOT NULL, ledger TEXT NOT NULL,
            event TEXT NOT NULL, state_update TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0)""")
        connection.commit()
        yield connection
    finally:
        connection.close()


def _materialize(project: Path, connection, row) -> dict[str, Any]:
    ledger = project / "project-ledger.json"
    current = file_sha(ledger)
    if current not in {row["before_sha"], row["after_sha"]}:
        raise TurnUpTimeGraphError("unrecorded ledger drift; recovery will not overwrite it")
    if current != row["after_sha"]:
        atomic_text(ledger, row["ledger"])
    append_event(project / "events.jsonl", json.loads(row["event"]))
    connection.execute("UPDATE operations SET completed=1 WHERE event_id=?", (row["event_id"],))
    connection.commit()
    return json.loads(row["state_update"])


def replay(project: Path, expected_sha: str, previous_event_id: str | None) -> dict[str, Any] | None:
    """Return exactly the missing checkpoint update, anchored to its prior state."""
    with writer_lock(project), _database(project) as connection:
        rows = connection.execute(
            "SELECT * FROM operations WHERE before_sha=? AND previous_event_id IS ? ORDER BY sequence",
            (expected_sha, previous_event_id),
        ).fetchall()
        if not rows:
            return None
        if len(rows) != 1:
            raise TurnUpTimeGraphError("ambiguous journal ancestry; manual investigation required")
        return _materialize(project, connection, rows[0])


def lookup(project: Path, event_id: str, request: dict[str, Any]) -> dict[str, Any] | None:
    """Read an idempotency result without moving the current ledger backwards."""
    with writer_lock(project), _database(project) as connection:
        row = connection.execute("SELECT * FROM operations WHERE event_id=?", (event_id,)).fetchone()
        if row is None:
            return None
        if row["request_sha"] != digest(request):
            raise TurnUpTimeGraphError("event ID reused with a different request")
        if not row["completed"]:
            raise TurnUpTimeGraphError("operation is pending; run recover before submitting another signal")
        return json.loads(row["state_update"])


def execute(project: Path, request: dict[str, Any], expected_sha: str,
            previous_event_id: str | None,
            prepare: Callable[[], tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    event_id = request.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise TurnUpTimeGraphError("a stable event ID is required")
    with writer_lock(project), _database(project) as connection:
        existing = connection.execute("SELECT * FROM operations WHERE event_id=?", (event_id,)).fetchone()
        if existing is not None:
            if existing["request_sha"] != digest(request):
                raise TurnUpTimeGraphError("event ID reused with a different request")
            if existing["before_sha"] != expected_sha or existing["previous_event_id"] != previous_event_id:
                raise TurnUpTimeGraphError("already applied event belongs to an earlier state; inspect status")
            return _materialize(project, connection, existing)
        pending = connection.execute("SELECT event_id FROM operations WHERE completed=0").fetchone()
        if pending:
            raise TurnUpTimeGraphError("pending operation must be recovered before new work")
        if file_sha(project / "project-ledger.json") != expected_sha:
            raise TurnUpTimeGraphError("checkpoint/ledger hash drift before operation")
        descendant = connection.execute(
            "SELECT event_id FROM operations WHERE before_sha=? AND previous_event_id IS ?",
            (expected_sha, previous_event_id),
        ).fetchone()
        if descendant:
            raise TurnUpTimeGraphError("stale checkpoint already has a journal successor; recover first")
        ledger, event, update = prepare()
        text = ledger_text(ledger)
        after_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        update = dict(update, ledger_sha256=after_sha, last_event_id=event_id)
        event = dict(event, ledger_sha256_before=expected_sha, ledger_sha256_after=after_sha)
        update["last_transition"] = event
        connection.execute(
            "INSERT INTO operations(event_id,request_sha,before_sha,previous_event_id,after_sha,ledger,event,state_update) VALUES(?,?,?,?,?,?,?,?)",
            (event_id, digest(request), expected_sha, previous_event_id, after_sha, text,
             json.dumps(event, allow_nan=False), json.dumps(update, allow_nan=False)),
        )
        connection.commit()  # durable intent; no product/release action is repeated
        row = connection.execute("SELECT * FROM operations WHERE event_id=?", (event_id,)).fetchone()
        return _materialize(project, connection, row)


def latest_update(project: Path) -> dict[str, Any] | None:
    """Recover counters when creating a new checkpoint from an existing journal."""
    with writer_lock(project), _database(project) as connection:
        row = connection.execute("SELECT * FROM operations ORDER BY sequence DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return _materialize(project, connection, row)
