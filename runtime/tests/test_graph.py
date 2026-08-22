from turn_up_time_graph.graph import build_graph


def test_graph_compiles_and_renders():
    graph = build_graph()
    mermaid = graph.get_graph().draw_mermaid()
    assert "intake" in mermaid
    assert "discovery" in mermaid
    assert "release" in mermaid
