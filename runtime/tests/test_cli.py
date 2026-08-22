from turn_up_time_graph.cli import build_parser


def test_cli_parser_accepts_validate_topology():
    args = build_parser().parse_args(["validate-topology"])
    assert args.command == "validate-topology"


def test_cli_parser_accepts_signal():
    args = build_parser().parse_args(
        ["signal", "--project-dir", "project", "--event", "intake_ready"]
    )
    assert args.command == "signal"
    assert args.event == "intake_ready"
