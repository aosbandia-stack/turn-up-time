from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .exceptions import TurnUpTimeGraphError


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_text(path: Path, text: str) -> None:
    """Crash-safe replacement. Caller supplies the per-project writer lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def append_event(path: Path, event: dict[str, Any]) -> bool:
    """Logical append-only history; atomic replacement prevents torn JSONL tails.

    Identical retries are no-ops; reuse of an event ID with different contents is
    an error. The journal owns the lock around runtime calls to this function.
    """
    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise TurnUpTimeGraphError("graph event requires a non-empty event_id")
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    for line_number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        try:
            existing = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TurnUpTimeGraphError(f"invalid graph event JSON at {path}:{line_number}: {exc}") from exc
        if not isinstance(existing, dict):
            raise TurnUpTimeGraphError(f"invalid graph event object at {path}:{line_number}")
        if existing.get("event_id") == event_id:
            if existing != event:
                raise TurnUpTimeGraphError(f"event ID reused with different contents: {event_id}")
            return False
    prefix = text if not text or text.endswith("\n") else text + "\n"
    atomic_text(path, prefix + json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
    return True
