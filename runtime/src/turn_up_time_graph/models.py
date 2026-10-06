from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class EventSignal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    event: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    approved_by: str | None = None  # display identity; never proof of approval
    approval_ref: str | None = None
    evidence_delta: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
