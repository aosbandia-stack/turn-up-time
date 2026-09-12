"""Verify owner-signed, expiring approvals bound to the exact action and inputs.

The runtime never holds a signing key. The trust file and runtime must be mounted
read-only for workers, and signing must happen outside their OS authority. This
module does not make arbitrary shell access under the owner's account safe.
"""
from __future__ import annotations

import base64
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .exceptions import TurnUpTimeGraphError
from .transactions import file_sha
from .workspace import build_identity, evidence_manifest, project_file

TRUST_FILE_VARIABLE = "TURN_UP_TIME_TRUST_FILE"


def account_home() -> Path:
    """The OS account's home, resolved WITHOUT consulting HOME or USERPROFILE.

    `Path.home()` expands `$HOME` (POSIX) or `%USERPROFILE%` (Windows), both of
    which any caller sets on a child process it spawns. Selecting the trust
    root that way let a worker supply its own trust file naming its own key as
    the owner, which forged approvals for every human gate without touching a
    single protected file. The account database and the process token are not
    settable that way.
    """
    if sys.platform != "win32":
        try:
            import pwd

            return Path(pwd.getpwuid(os.getuid()).pw_dir)
        except (ImportError, KeyError, OSError) as exc:  # pragma: no cover - exotic POSIX
            raise TurnUpTimeGraphError(
                "cannot resolve the account home from the password database; "
                f"set {TRUST_FILE_VARIABLE} to a trust file this account cannot write"
            ) from exc

    try:  # pragma: no cover - exercised on Windows hosts only
        import ctypes
        from ctypes import wintypes

        class _Guid(ctypes.Structure):
            _fields_ = [("d1", wintypes.DWORD), ("d2", wintypes.WORD),
                        ("d3", wintypes.WORD), ("d4", ctypes.c_byte * 8)]

        # FOLDERID_Profile {5E6C858F-0E22-4760-9AFE-EA3317B67173}
        folder = _Guid(0x5E6C858F, 0x0E22, 0x4760,
                       (ctypes.c_byte * 8)(*bytes((0x9A, 0xFE, 0xEA, 0x33, 0x17, 0xB6, 0x71, 0x73))))
        buffer = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(folder), 0, None, ctypes.byref(buffer)
        ):
            raise OSError("SHGetKnownFolderPath failed")
        try:
            return Path(buffer.value)
        finally:
            ctypes.windll.ole32.CoTaskMemFree(buffer)
    except Exception as exc:  # pragma: no cover - exercised on Windows hosts only
        raise TurnUpTimeGraphError(
            "cannot resolve the account profile from the process token; "
            f"set {TRUST_FILE_VARIABLE} to a trust file this account cannot write"
        ) from exc


def trust_file_path() -> Path:
    """Where the owner's public trust configuration lives.

    An explicit override is honoured only when the process cannot write the
    file it names. That keeps the operator's supported deployment (a trust file
    owned by root, or otherwise read-only) usable, while refusing a path a
    worker just wrote for itself.

    This raises the cost of substitution; it is not an isolation boundary. A
    process running as the owner's own account can still change file modes. On
    Windows the writability probe reflects the read-only attribute and does not
    consult ACLs. See docs/SECURITY-BOUNDARY.md.
    """
    override = os.environ.get(TRUST_FILE_VARIABLE)
    if not override:
        return account_home() / ".claude" / "turn-up-time-trust.json"
    path = Path(override)
    if _mode_grants_write(path):
        raise TurnUpTimeGraphError(
            f"{TRUST_FILE_VARIABLE} names a file whose permissions let this account write it "
            f"({path}); a writable trust file is not an authority boundary"
        )
    return path


def _mode_grants_write(path: Path) -> bool:
    """Whether this account's permissions grant write to `path`.

    Deliberately reads mode bits rather than calling `os.access`, which honours
    the superuser bypass and so reports every file as writable when the
    controller runs as root - turning the check into a no-op exactly where the
    stakes are highest.
    """
    try:
        info = path.stat()
    except OSError as exc:
        raise TurnUpTimeGraphError(f"trust file is unreadable: {path}") from exc

    if sys.platform == "win32":  # pragma: no cover - exercised on Windows hosts only
        return os.access(path, os.W_OK)

    import stat as stat_module

    if info.st_uid == os.geteuid():
        return bool(info.st_mode & stat_module.S_IWUSR)
    if info.st_gid == os.getegid() or info.st_gid in os.getgroups():
        return bool(info.st_mode & stat_module.S_IWGRP)
    return bool(info.st_mode & stat_module.S_IWOTH)


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
    # Not selectable from a ticket, project file, command argument, or from
    # HOME/USERPROFILE. An override must name a file this process cannot write.
    trust_path = trust_file_path()
    try:
        trust = json.loads(trust_path.read_text(encoding="utf-8"))
        envelope = json.loads(project_file(project, reference).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TurnUpTimeGraphError("trusted approval configuration or approval envelope is unavailable") from exc
    return verify_envelope(approval_request(repo, project, transition, payload), envelope, trust)
