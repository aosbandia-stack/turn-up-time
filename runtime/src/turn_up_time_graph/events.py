from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .exceptions import TurnUpTimeGraphError


def utc_now() -> str:
    """Return a second-precision UTC timestamp in JSON Schema date-time form."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def append_event(path: Path, event: dict[str, Any]) -> bool:
    """Append an event once, keyed by ``event_id``.

    The file is deliberately JSONL and append-only. Replaying the same runtime
    signal is harmless: an existing event ID returns ``False`` without writing.
    """

    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise TurnUpTimeGraphError("graph event requires a non-empty event_id")

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                existing = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise TurnUpTimeGraphError(
                    f"invalid graph event JSON at {path}:{line_number}: {exc}"
                ) from exc
            if existing.get("event_id") == event_id:
                return False

    serialized = json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    return True
