"""Verify owner-signed, expiring approvals bound to the exact action and inputs.

The runtime never holds a signing key. The trust file and runtime must be mounted
read-only for workers, and signing must happen outside their OS authority. This
module does not make arbitrary shell access under the owner's account safe.
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .exceptions import TurnUpTimeGraphError
from .transactions import file_sha
from .workspace import build_identity, evidence_manifest, project_file


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def approval_request(repo: Path, project: Path, transition, payload: dict[str, Any]) -> dict[str, Any]:
    ledger = json.loads((project / "project-ledger.json").read_text(encoding="utf-8"))
    if not transition.human_gate:
        raise TurnUpTimeGraphError("this transition has no human approval gate")
    if not payload.get("event_id"):
        raise TurnUpTimeGraphError("request-approval requires a stable event ID")
    return {
        "schema_version": 1,
        "project_id": ledger["project_id"],
        "repo_root": str(repo.resolve()),
        "project_dir": str(project.resolve()),
        "gate": transition.human_gate,
        "from_stage": transition.source.value,
        "to_stage": transition.target.value,
        "event": payload["event"],
        "event_id": payload["event_id"],
        "approved_by": payload.get("approved_by"),
        "receipt_refs": payload.get("receipt_refs", []),
        "evidence_delta": payload.get("evidence_delta", []),
        "ledger_sha256": file_sha(project / "project-ledger.json"),
        "code_identity": build_identity(repo),
        "artifacts": evidence_manifest(project),
    }


def _time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return result


def verify_envelope(expected: dict[str, Any], envelope: dict[str, Any], trust: dict[str, Any],
                    *, now: datetime | None = None) -> str:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise TurnUpTimeGraphError("approval verification dependency is missing; reinstall the runtime") from exc
    try:
        key_id = envelope["key_id"]
        key = trust["keys"][key_id]
        statement = envelope["statement"]
        if key.get("revoked", False) or envelope.get("approval_id") in trust.get("revoked_approvals", []):
            raise ValueError("approval or signing key was revoked")
        if statement["request"] != expected:
            raise ValueError("approval does not match this action, code, ledger, or evidence")
        if expected["gate"] not in key["gates"]:
            raise ValueError("signer is not authorized for this gate")
        if statement["approver"] != key["approver"] or expected.get("approved_by") != key["approver"]:
            raise ValueError("approver identity does not match the trusted key")
        if statement["approval_id"] != envelope["approval_id"]:
            raise ValueError("approval ID mismatch")
        clock = now or datetime.now(timezone.utc)
        issued, expires = _time(statement["issued_at"]), _time(statement["expires_at"])
        if not issued <= clock < expires or (expires - issued).total_seconds() > 86400:
            raise ValueError("approval is expired, not yet valid, or exceeds its 24-hour maximum lifetime")
        public = Ed25519PublicKey.from_public_bytes(base64.b64decode(key["public_key"], validate=True))
        public.verify(base64.b64decode(envelope["signature"], validate=True), canonical(statement))
        return key["approver"]
    except (KeyError, TypeError, ValueError, InvalidSignature) as exc:
        raise TurnUpTimeGraphError(f"human approval rejected: {exc}") from exc


def verify_approval(repo: Path, project: Path, transition, payload: dict[str, Any]) -> str:
    reference = payload.get("approval_ref")
    if not reference:
        raise TurnUpTimeGraphError("human gate requires an owner-signed --approval-ref; a name is not authorization")
    # Not configurable from a ticket, project file, command argument, or environment.
    trust_path = Path.home() / ".claude" / "turn-up-time-trust.json"
    try:
        trust = json.loads(trust_path.read_text(encoding="utf-8"))
        envelope = json.loads(project_file(project, reference).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TurnUpTimeGraphError("trusted approval configuration or approval envelope is unavailable") from exc
    return verify_envelope(approval_request(repo, project, transition, payload), envelope, trust)
