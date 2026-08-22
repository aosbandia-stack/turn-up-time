from turn_up_time_graph.constants import GRAPH_SCHEMA_VERSION, RUNTIME_VERSION


def test_runtime_constants():
    assert RUNTIME_VERSION == "1.0.0"
    assert GRAPH_SCHEMA_VERSION == 1
