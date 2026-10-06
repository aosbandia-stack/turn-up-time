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
    if not signal.event_id.strip():
        raise TransitionError("a nonempty stable event ID is required")
    if signal.event != transition.event:
        raise TransitionError(f"signal event {signal.event!r} does not match transition {transition.event!r}")
    if transition.human_gate and not (signal.approved_by or "").strip():
        raise TransitionError(f"transition {transition.event} requires human approval for gate {transition.human_gate}")
    if transition.requires_new_evidence:
        evidence = [item.strip() for item in signal.evidence_delta if item.strip()]
        if not evidence:
            raise TransitionError(f"transition {transition.event} requires a non-empty evidence_delta")
    return signal


def validate_runtime_topology() -> None:
    errors = validate_topology()
    if errors:
        raise TransitionError("invalid executable topology: " + "; ".join(errors))


def ensure_checkpoint_ledger_alignment(project_dir: Path, expected_stage: str, expected_sha256: str | None) -> None:
    ledger = load_ledger(project_dir)
    actual_stage = ledger.get("stage")
    if actual_stage != expected_stage:
        raise TransitionError(f"checkpoint/ledger stage drift: checkpoint={expected_stage}, ledger={actual_stage}")
    if expected_sha256 and ledger_sha256(project_dir) != expected_sha256:
        raise TransitionError("checkpoint/ledger hash drift: the ledger changed outside the recorded graph transition")


def _validator_candidates(repo_root: Path) -> tuple[Path, ...]:
    """Where the project validator may be found, in precedence order.

    The installed fallback is resolved from the OS account rather than `$HOME`,
    for the reason recorded in docs/SECURITY-BOUNDARY.md: `Path.home()` expands
    an environment variable any caller sets on a child process, so a worker
    could point it at a directory holding a validator that approves everything.
    Validation is meant to fail closed, and a caller-selected validator is not
    validation.

    `TURN_UP_TIME_CLAUDE_HOME` remains an explicit installer/operator setting.
    It is deliberately env-selectable and must be treated as trust-relevant
    configuration, not as something a worker may set.
    """
    from .approvals import account_home

    configured = os.environ.get("TURN_UP_TIME_CLAUDE_HOME")
    claude_home = Path(configured) if configured else account_home() / ".claude"
    return (repo_root / ".claude" / "scripts" / "validate_project.py", claude_home / "scripts" / "validate_project.py")


def validate_project_for_target(repo_root: Path, project_dir: Path, target: Stage) -> None:
    if target is Stage.BLOCKED:
        return  # Stopping work must remain possible with incomplete project artifacts.
    if target in {Stage.INTEGRATION, Stage.CLOSEOUT, Stage.RELEASE, Stage.WORKFLOW_CLOSEOUT, Stage.DONE}:
        from .workspace import build_identity
        if load_ledger(project_dir).get("build_identity") != build_identity(repo_root):
            raise TransitionError("assembled build identity is missing or stale; record and verify the current build")
    validator = next((path for path in _validator_candidates(repo_root) if path.is_file()), None)
    if validator is None:
        raise TransitionError("project validator is missing; reinstall Turn Up Time before advancing")
    try:
        result = subprocess.run(
            [sys.executable, str(validator), str(project_dir), "--stage", target.value],
            cwd=repo_root, capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TransitionError(f"project validation could not complete: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip()
        raise TransitionError(f"project prerequisites are not green for {target.value}: {detail}")
