from turn_up_time_graph.topology import Stage, TRANSITION_INDEX, validate_topology


def test_topology_is_valid():
    assert validate_topology() == []


def test_bounded_loops_are_present():
    assert TRANSITION_INDEX[(Stage.EVIDENCE_REVIEW, "evidence_blocked")].max_traversals == 2
    assert TRANSITION_INDEX[(Stage.INTEGRATION, "seams_blocked")].max_traversals == 2
    assert TRANSITION_INDEX[(Stage.CLOSEOUT, "validated_repairs")].max_traversals == 4


def test_human_gates_are_explicit():
    assert TRANSITION_INDEX[(Stage.TICKETING, "tickets_approved")].human_gate == "TICKETS"
    assert TRANSITION_INDEX[(Stage.RELEASE, "release_shipped")].human_gate == "RELEASE"
