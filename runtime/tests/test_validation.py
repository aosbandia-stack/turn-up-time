import pytest

from turn_up_time_graph.topology import Stage, TRANSITION_INDEX
from turn_up_time_graph.validation import TransitionError, validate_event_payload


def test_human_gate_requires_approver():
    transition = TRANSITION_INDEX[(Stage.TICKETING, "tickets_approved")]
    with pytest.raises(TransitionError):
        validate_event_payload(transition, {"event_id": "evt"})


def test_loop_requires_evidence_delta():
    transition = TRANSITION_INDEX[(Stage.INTEGRATION, "seams_blocked")]
    with pytest.raises(TransitionError):
        validate_event_payload(transition, {"event_id": "evt", "evidence_delta": []})


def test_loop_accepts_named_delta():
    transition = TRANSITION_INDEX[(Stage.INTEGRATION, "seams_blocked")]
    validate_event_payload(
        transition,
        {"event_id": "evt", "evidence_delta": ["INT-001"]},
    )
