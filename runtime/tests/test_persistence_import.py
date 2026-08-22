from turn_up_time_graph.persistence import sqlite_checkpointer


def test_sqlite_checkpointer_is_callable():
    assert callable(sqlite_checkpointer)
