from turn_up_time_graph.exceptions import TurnUpTimeGraphError


def test_exception_type():
    assert issubclass(TurnUpTimeGraphError, RuntimeError)
