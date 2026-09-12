"""The trust root must not be selectable by anything a worker controls.

Regression tests for a reproduced forgery: because `verify_approval` resolved
the trust file through `Path.home()`, a process could point HOME at a directory
holding its own trust file, name its own key as the owner, and have a forged
RELEASE approval accepted. No protected file had to be modified - one
environment variable on a spawned child was enough.
"""
import base64
import json
import os
import stat
import sys
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from turn_up_time_graph.approvals import (
    TRUST_FILE_VARIABLE,
    canonical,
    trust_file_path,
    verify_envelope,
)
from turn_up_time_graph.exceptions import TurnUpTimeGraphError


def _trust(private, approver="Owner", gates=("INTAKE", "RELEASE")):
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return {
        "keys": {
            "planted": {
                "public_key": base64.b64encode(public).decode(),
                "approver": approver,
                "gates": list(gates),
                "revoked": False,
            }
        },
        "revoked_approvals": [],
    }


def _envelope(private, request, approver="Owner"):
    now = datetime.now(timezone.utc)
    statement = {
        "approval_id": "forged-0001",
        "approver": approver,
        "request": request,
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=30)).isoformat(),
    }
    return {
        "key_id": "planted",
        "approval_id": "forged-0001",
        "statement": statement,
        "signature": base64.b64encode(private.sign(canonical(statement))).decode(),
    }


def test_home_does_not_select_the_trust_root(tmp_path, monkeypatch):
    """Pointing HOME at a planted trust directory must not move the trust root."""
    planted = tmp_path / "planted-home" / ".claude"
    planted.mkdir(parents=True)
    (planted / "turn-up-time-trust.json").write_text("{}")
    monkeypatch.setenv("HOME", str(tmp_path / "planted-home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "planted-home"))
    monkeypatch.delenv(TRUST_FILE_VARIABLE, raising=False)

    assert trust_file_path() != planted / "turn-up-time-trust.json"


def test_forged_release_approval_is_not_accepted_via_planted_home(tmp_path, monkeypatch):
    """The full reproduced attack, end to end, must fail."""
    private = Ed25519PrivateKey.generate()
    planted_home = tmp_path / "planted-home"
    (planted_home / ".claude").mkdir(parents=True)
    trust_file = planted_home / ".claude" / "turn-up-time-trust.json"
    trust_file.write_text(json.dumps(_trust(private)))
    monkeypatch.setenv("HOME", str(planted_home))
    monkeypatch.setenv("USERPROFILE", str(planted_home))
    monkeypatch.delenv(TRUST_FILE_VARIABLE, raising=False)

    request = {"gate": "RELEASE", "event": "release_approved", "approved_by": "Owner"}
    envelope = _envelope(private, request)

    # The planted trust file would accept this envelope if it were ever loaded.
    assert verify_envelope(request, envelope, json.loads(trust_file.read_text())) == "Owner"

    # It must not be the file the runtime loads.
    assert trust_file_path() != trust_file


def test_writable_override_is_refused(tmp_path, monkeypatch):
    """An override a worker could rewrite is not an authority boundary."""
    writable = tmp_path / "writable-trust.json"
    writable.write_text("{}")
    monkeypatch.setenv(TRUST_FILE_VARIABLE, str(writable))

    with pytest.raises(TurnUpTimeGraphError, match="not an authority boundary"):
        trust_file_path()


@pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX mode bits; Windows read-only attribute is covered below"
)
def test_read_only_override_is_accepted(tmp_path, monkeypatch):
    """The supported deployment - a trust file this account cannot write."""
    protected = tmp_path / "protected-trust.json"
    protected.write_text("{}")
    protected.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    monkeypatch.setenv(TRUST_FILE_VARIABLE, str(protected))

    assert trust_file_path() == protected


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX mode bits")
def test_root_does_not_defeat_the_writability_check(tmp_path, monkeypatch):
    """`os.access` honours the superuser bypass; the check must not.

    Run as root this is the whole test: os.access reports the read-only file as
    writable, so a probe built on it would reject the operator's supported
    deployment - or, inverted, accept a world-writable one.
    """
    protected = tmp_path / "root-trust.json"
    protected.write_text("{}")
    protected.chmod(0o444)
    monkeypatch.setenv(TRUST_FILE_VARIABLE, str(protected))

    if os.geteuid() == 0:
        assert os.access(protected, os.W_OK), "expected the superuser bypass"
    assert trust_file_path() == protected


def test_default_trust_root_is_under_the_account_home(monkeypatch):
    monkeypatch.delenv(TRUST_FILE_VARIABLE, raising=False)
    resolved = trust_file_path()
    assert resolved.name == "turn-up-time-trust.json"
    assert resolved.parent.name == ".claude"


def test_home_does_not_select_the_project_validator(tmp_path, monkeypatch):
    """The same defect class, in the fail-closed validation path.

    `_validator_candidates` derived its installed fallback from `Path.home()`,
    so repointing HOME made the runtime discover a planted validator that
    approves everything. A caller-selected validator is not validation.
    """
    from turn_up_time_graph.validation import _validator_candidates

    planted = tmp_path / "planted-home" / ".claude" / "scripts"
    planted.mkdir(parents=True)
    (planted / "validate_project.py").write_text("import sys; sys.exit(0)\n")
    monkeypatch.setenv("HOME", str(tmp_path / "planted-home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "planted-home"))
    monkeypatch.delenv("TURN_UP_TIME_CLAUDE_HOME", raising=False)

    candidates = _validator_candidates(tmp_path / "repo")
    assert planted / "validate_project.py" not in candidates


def test_explicit_claude_home_still_selects_the_validator(tmp_path, monkeypatch):
    """`TURN_UP_TIME_CLAUDE_HOME` stays an explicit installer/operator setting.

    It is trust-relevant configuration, not something a worker may set; the
    installed deployment depends on it, so it is deliberately still honoured.
    """
    from turn_up_time_graph.validation import _validator_candidates

    installed = tmp_path / "installed" / "scripts"
    installed.mkdir(parents=True)
    (installed / "validate_project.py").write_text("import sys; sys.exit(0)\n")
    monkeypatch.setenv("TURN_UP_TIME_CLAUDE_HOME", str(tmp_path / "installed"))

    assert installed / "validate_project.py" in _validator_candidates(tmp_path / "repo")
