from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .exceptions import TurnUpTimeGraphError
from .ledger import ledger_sha256, load_ledger
from .models import EventSignal
from .topology import Stage, Transition, validate_topology


class TransitionError(TurnUpTimeGraphError):
    """Raised when a requested graph edge is illegal or not yet evidenced."""


def validate_event_payload(transition: Transition, payload: dict[str, Any]) -> EventSignal:
    candidate = dict(payload)
    candidate.setdefault("event", transition.event)
    try:
        signal = EventSignal.model_validate(candidate)
    except ValidationError as exc:
        raise TransitionError(f"invalid graph signal: {exc}") from exc
    if signal.event != transition.event:
        raise TransitionError(
            f"signal event {signal.event!r} does not match transition {transition.event!r}"
        )
    if transition.human_gate and not (signal.approved_by or "").strip():
        raise TransitionError(
            f"transition {transition.event} requires human approval for gate {transition.human_gate}"
        )
    if transition.requires_new_evidence:
        evidence = [item.strip() for item in signal.evidence_delta if item.strip()]
        if not evidence:
            raise TransitionError(
                f"transition {transition.event} requires a non-empty evidence_delta"
            )
    return signal


def validate_runtime_topology() -> None:
    errors = validate_topology()
    if errors:
        raise TransitionError("invalid executable topology: " + "; ".join(errors))


def ensure_checkpoint_ledger_alignment(
    project_dir: Path, expected_stage: str, expected_sha256: str | None
) -> None:
    ledger = load_ledger(project_dir)
    actual_stage = ledger.get("stage")
    if actual_stage != expected_stage:
        raise TransitionError(
            f"checkpoint/ledger stage drift: checkpoint={expected_stage}, ledger={actual_stage}"
        )
    if expected_sha256:
        actual_sha = ledger_sha256(project_dir)
        if actual_sha != expected_sha256:
            raise TransitionError(
                "checkpoint/ledger hash drift: the ledger changed outside the recorded graph transition"
            )


def _validator_candidates(repo_root: Path) -> tuple[Path, ...]:
    claude_home = Path(
        os.environ.get("TURN_UP_TIME_CLAUDE_HOME", str(Path.home() / ".claude"))
    )
    return (
        repo_root / ".claude" / "scripts" / "validate_project.py",
        claude_home / "scripts" / "validate_project.py",
    )


def validate_project_for_target(
    repo_root: Path, project_dir: Path, target: Stage
) -> None:
    if target is Stage.BLOCKED:
        return
    validator = next((path for path in _validator_candidates(repo_root) if path.is_file()), None)
    if validator is None:
        # Library-level tests intentionally exercise the graph with only a ledger.
        # Installed and project-scoped runs include this validator.
        return
    result = subprocess.run(
        [sys.executable, str(validator), str(project_dir), "--stage", target.value],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip()
        raise TransitionError(
            f"project prerequisites are not green for {target.value}: {detail}"
        )
