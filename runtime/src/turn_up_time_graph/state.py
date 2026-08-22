from __future__ import annotations

from typing import Any, TypedDict


class GauntletState(TypedDict):
    """Durable state carried by the executable Turn Up Time graph."""

    project_id: str
    project_dir: str
    repo_root: str
    stage: str
    status: str
    profile: str
    thread_id: str
    loop_counts: dict[str, int]
    blockers: list[str]
    last_event_id: str | None
    last_event: str | None
    last_transition: dict[str, Any] | None
    messages: list[str]
    ledger_sha256: str
