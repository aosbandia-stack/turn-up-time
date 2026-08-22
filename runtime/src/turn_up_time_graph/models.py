from __future__ import annotations

from pydantic import BaseModel, Field


class EventSignal(BaseModel):
    event: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    approved_by: str | None = None
    evidence_delta: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
