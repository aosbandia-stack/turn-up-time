import pytest
from pydantic import ValidationError

from turn_up_time_graph.models import EventSignal


def test_event_signal_requires_nonempty_identifiers():
    with pytest.raises(ValidationError):
        EventSignal(event="", event_id="")


def test_event_signal_defaults_lists():
    signal = EventSignal(event="intake_ready", event_id="evt-1")
    assert signal.evidence_delta == []
    assert signal.receipt_refs == []
