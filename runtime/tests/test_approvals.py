import base64
import copy
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from turn_up_time_graph.approvals import canonical, verify_envelope
from turn_up_time_graph.exceptions import TurnUpTimeGraphError


def fixture():
    private = Ed25519PrivateKey.generate()  # disposable fixture only; never an operator key
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    now = datetime(2026, 9, 11, tzinfo=timezone.utc)
    expected = {"gate": "RELEASE", "event_id": "ship-1", "approved_by": "Owner", "artifacts": {"test": "sha1"}}
    statement = {"request": expected, "approver": "Owner", "approval_id": "a1",
                 "issued_at": now.isoformat(), "expires_at": (now + timedelta(hours=1)).isoformat()}
    envelope = {"key_id": "owner", "approval_id": "a1", "statement": statement,
                "signature": base64.b64encode(private.sign(canonical(statement))).decode()}
    trust = {"keys": {"owner": {"public_key": base64.b64encode(public).decode(), "approver": "Owner", "gates": ["RELEASE"]}}}
    return expected, envelope, trust, now


def test_trusted_approval_passes():
    expected, envelope, trust, now = fixture()
    assert verify_envelope(expected, envelope, trust, now=now) == "Owner"


@pytest.mark.parametrize("mutation", [
    lambda expected, e, t: expected.update(event_id="different-action"),
    lambda expected, e, t: expected.update(artifacts={"test": "changed-evidence"}),
    lambda expected, e, t: e.update(signature=base64.b64encode(b"bad signature").decode()),
    lambda expected, e, t: e.update(key_id="unknown"),
    lambda expected, e, t: e.update(approval_id="wrong"),
    lambda expected, e, t: t["keys"]["owner"].update(revoked=True),
    lambda expected, e, t: t.update(revoked_approvals=["a1"]),
    lambda expected, e, t: t["keys"]["owner"].update(gates=["INTAKE"]),
    lambda expected, e, t: t["keys"]["owner"].update(approver="Someone else"),
    lambda expected, e, t: e["statement"].update(approver="Someone else"),
    lambda expected, e, t: e["statement"].update(expires_at="2026-09-10T00:00:00Z"),
    lambda expected, e, t: e["statement"].update(issued_at="2026-09-12T00:00:00Z"),
])
def test_approval_forgery_or_staleness_denied(mutation):
    expected, envelope, trust, now = fixture()
    expected = copy.deepcopy(expected)
    mutation(expected, envelope, trust)
    with pytest.raises(TurnUpTimeGraphError):
        verify_envelope(expected, envelope, trust, now=now)


def test_name_only_is_not_an_approval():
    expected, _, trust, now = fixture()
    with pytest.raises(TurnUpTimeGraphError):
        verify_envelope(expected, {"approved_by": "Owner"}, trust, now=now)
