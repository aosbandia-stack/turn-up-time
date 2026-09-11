import json
from pathlib import Path
from unittest.mock import patch

import pytest

from turn_up_time_graph import transactions as tx
from turn_up_time_graph.exceptions import TurnUpTimeGraphError


def project(tmp_path):
    (tmp_path / "project-ledger.json").write_text(tx.ledger_text({"stage": "INTAKE"}))
    return tmp_path


def proposal():
    return ({"stage": "DISCOVERY"}, {"event_id": "e1", "trigger": "intake_ready"},
            {"stage": "DISCOVERY", "loop_counts": {"repair": 1}})


def test_exactly_once_and_payload_conflict(tmp_path):
    root = project(tmp_path)
    before = tx.file_sha(root / "project-ledger.json")
    request = {"event_id": "e1", "event": "intake_ready"}
    first = tx.execute(root, request, before, None, proposal)
    again = tx.execute(root, request, before, None, lambda: pytest.fail("re-executed"))
    assert first == again
    assert len((root / "events.jsonl").read_text().splitlines()) == 1
    with pytest.raises(TurnUpTimeGraphError, match="different request"):
        tx.execute(root, dict(request, event="something-else"), before, None, proposal)


@pytest.mark.parametrize("boundary", ["before_ledger", "before_event", "after_event"])
def test_interruption_recovers_saved_intent(tmp_path, boundary):
    root = project(tmp_path)
    before = tx.file_sha(root / "project-ledger.json")
    real_append = tx.append_event
    def after_event(*args):
        real_append(*args)
        raise RuntimeError("simulated process death")
    target = "atomic_text" if boundary == "before_ledger" else "append_event"
    failure = after_event if boundary == "after_event" else RuntimeError("simulated process death")
    with patch.object(tx, target, side_effect=failure):
        with pytest.raises(RuntimeError):
            tx.execute(root, {"event_id": "e1"}, before, None, proposal)
    # A new call reopens SQLite; the original callback is not needed for recovery.
    restored = tx.replay(root, before, None)
    assert restored["stage"] == "DISCOVERY"
    assert restored["loop_counts"] == {"repair": 1}
    assert len((root / "events.jsonl").read_text().splitlines()) == 1
    assert tx.replay(root, restored["ledger_sha256"], "e1") is None


def test_external_edit_not_overwritten(tmp_path):
    root = project(tmp_path)
    before = tx.file_sha(root / "project-ledger.json")
    with patch.object(tx, "append_event", side_effect=OSError("interrupted")):
        with pytest.raises(OSError):
            tx.execute(root, {"event_id": "e1"}, before, None, proposal)
    (root / "project-ledger.json").write_text('{"stage":"UNAUTHORIZED"}')
    with pytest.raises(TurnUpTimeGraphError, match="unrecorded ledger drift"):
        tx.replay(root, before, None)
    assert "UNAUTHORIZED" in (root / "project-ledger.json").read_text()


def test_pending_operation_prevents_different_event(tmp_path):
    root = project(tmp_path)
    before = tx.file_sha(root / "project-ledger.json")
    with patch.object(tx, "atomic_text", side_effect=OSError("interrupted")):
        with pytest.raises(OSError):
            tx.execute(root, {"event_id": "e1"}, before, None, proposal)
    with pytest.raises(TurnUpTimeGraphError, match="pending operation"):
        tx.execute(root, {"event_id": "e2"}, before, None, proposal)


def test_writer_is_exclusive(tmp_path):
    root = project(tmp_path)
    with tx.writer_lock(root):
        with pytest.raises(TurnUpTimeGraphError, match="writer is busy"):
            with tx.writer_lock(root):
                pytest.fail("two writers")


def test_event_id_collision_does_not_erase_history(tmp_path):
    from turn_up_time_graph.events import append_event
    path = tmp_path / "events.jsonl"
    assert append_event(path, {"event_id": "e1", "status": "PASS"})
    assert not append_event(path, {"event_id": "e1", "status": "PASS"})
    with pytest.raises(TurnUpTimeGraphError, match="different contents"):
        append_event(path, {"event_id": "e1", "status": "FAIL"})
    assert json.loads(path.read_text())["status"] == "PASS"


def test_lost_checkpoint_restores_loop_counts(tmp_path):
    root = project(tmp_path)
    before = tx.file_sha(root / "project-ledger.json")
    result = tx.execute(root, {"event_id": "e1"}, before, None, proposal)
    assert tx.latest_update(root) == result


def test_lookup_old_result_does_not_rewind_state(tmp_path):
    root = project(tmp_path)
    before = tx.file_sha(root / "project-ledger.json")
    result = tx.execute(root, {"event_id": "e1"}, before, None, proposal)
    def second():
        return {"stage": "BUILD"}, {"event_id": "e2"}, {"stage": "BUILD"}
    tx.execute(root, {"event_id": "e2"}, result["ledger_sha256"], "e1", second)
    assert tx.lookup(root, "e1", {"event_id": "e1"}) == result
    assert json.loads((root / "project-ledger.json").read_text())["stage"] == "BUILD"
