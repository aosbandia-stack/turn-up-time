import json

from turn_up_time_graph.render import render


def test_render_writes_json_and_mermaid(tmp_path):
    mermaid_path, json_path = render(tmp_path)
    assert mermaid_path.exists()
    assert json_path.exists()
    payload = json.loads(json_path.read_text())
    assert payload["schema_version"] == 1
    assert payload["transitions"]
