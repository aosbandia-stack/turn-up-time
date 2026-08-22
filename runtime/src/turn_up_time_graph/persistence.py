from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


@asynccontextmanager
async def sqlite_checkpointer(repo_root: Path):
    runtime_dir = repo_root / ".claude" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    db_path = runtime_dir / "turn-up-time-checkpoints.sqlite"
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
        yield saver
