import json

from turn_up_time_graph.events import append_event


def test_append_event_is_idempotent(tmp_path):
    path = tmp_path / "events.jsonl"
    event = {"event_id": "evt-1", "event_type": "EDGE_TRAVERSED"}
    assert append_event(path, event) is True
    assert append_event(path, event) is False
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows == [event]
