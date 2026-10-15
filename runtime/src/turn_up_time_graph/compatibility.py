"""Explicit, narrow legacy repair. No approval, evidence, or stage migration."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from .events import utc_now
from .exceptions import TurnUpTimeGraphError
from .ledger import load_ledger
from .transactions import file_sha, writer_lock
from .workspace import project_file

PROFILE = "ledger-v2-risk-severity-v1"
_SEVERITIES = {value.upper(): value for value in ("low", "medium", "high", "critical")}
_CHECKPOINT = ".claude/runtime/turn-up-time-checkpoints.sqlite"


def _no_symlink_chain(project: Path, path: Path) -> None:
    current = project
    for part in path.relative_to(project).parts:
        current = current / part
        if current.is_symlink():
            raise TurnUpTimeGraphError("compatibility backup paths must not contain symlinks")


def _sqlite_digest(path: Path) -> str:
    import hashlib
    with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
        return hashlib.sha256("\n".join(connection.iterdump()).encode()).hexdigest()


def compatibility_plan(project: Path) -> dict[str, Any]:
    ledger = load_ledger(project)
    if ledger.get("schema_version") != 2:
        raise TurnUpTimeGraphError("compatibility profile requires ledger schema_version 2")
    if not isinstance(ledger.get("risks"), list):
        raise TurnUpTimeGraphError("compatibility profile requires an array of risks")
    changes = []
    for index, risk in enumerate(ledger["risks"]):
        if not isinstance(risk, dict) or risk.get("severity") not in (*_SEVERITIES, *_SEVERITIES.values()):
            raise TurnUpTimeGraphError("unsupported risk severity; explicit contract repair required")
        if risk["severity"] in _SEVERITIES:
            changes.append({"path": f"/risks/{index}/severity", "before": risk["severity"],
                            "after": _SEVERITIES[risk["severity"]]})
    return {"profile": PROFILE, "project_id": ledger["project_id"],
            "ledger_sha256": file_sha(project / "project-ledger.json"), "changes": changes,
            "preserved": ["decisions including WITHDRAWN", "approvals", "spawn consumption and history",
                          "stage and stage history", "controlling artifacts and validation failures"]}


def _sources(repo: Path, project: Path) -> dict[str, Path]:
    sources = {}
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project).as_posix()
        if relative.startswith(".runtime/backups/") or relative == ".runtime/writer.lock":
            continue
        # SQLite online backup incorporates WAL; copying sidecars separately is unsafe.
        if relative.endswith((".sqlite-wal", ".sqlite-shm", ".sqlite-journal")):
            continue
        if path.is_symlink():
            raise TurnUpTimeGraphError(f"backup does not support symlinks: {relative}")
        if path.is_file():
            sources[f"project/{relative}"] = path
    checkpoint = repo / _CHECKPOINT
    if checkpoint.is_symlink():
        raise TurnUpTimeGraphError("checkpoint backup does not support symlinks")
    if checkpoint.is_file():
        sources[f"repository/{_CHECKPOINT}"] = checkpoint
    return sources


def _copy_snapshot(source: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix == ".sqlite":
        with sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True) as original:
            with sqlite3.connect(target) as backup:
                original.backup(backup)
                if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise TurnUpTimeGraphError("SQLite backup integrity check failed")
        kind = "sqlite-online-backup"
    else:
        with target.open("xb") as handle:
            handle.write(source.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        kind = "exact-bytes"
    with target.open("rb") as handle:
        os.fsync(handle.fileno())
    target.chmod(0o444)
    return kind


def backup_project(repo: Path, project: Path, backup_id: str) -> dict[str, Any]:
    """Capture before mutation; never overwrite an existing backup or restore state.

    Quiesce other controllers first. The per-project lock prevents journal writes;
    SQLite's online backup retains committed checkpoint/journal contents including WAL.
    An interrupted capture is deliberately retained and cannot authorize migration.
    """
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", backup_id):
        raise TurnUpTimeGraphError("backup-id must be 1-80 safe alphanumeric, underscore or hyphen characters")
    with writer_lock(project):
        if (project / ".runtime/backups").is_symlink():
            raise TurnUpTimeGraphError("backup directory must not be a symlink")
        directory = project / ".runtime/backups" / backup_id
        if directory.exists():
            raise TurnUpTimeGraphError("backup already exists; verify it or choose a new capture ID")
        directory.mkdir(parents=True)
        before = file_sha(project / "project-ledger.json")
        records = []
        for name, source in _sources(repo, project).items():
            target = directory / "files" / name
            kind = _copy_snapshot(source, target)
            record = {"source": name, "path": target.relative_to(project).as_posix(),
                      "sha256": file_sha(target), "kind": kind}
            if kind == "sqlite-online-backup":
                record["logical_sha256"] = _sqlite_digest(target)
                if _sqlite_digest(source) != record["logical_sha256"]:
                    raise TurnUpTimeGraphError("SQLite source changed during backup; capture is unusable")
            records.append(record)
        if before != file_sha(project / "project-ledger.json"):
            raise TurnUpTimeGraphError("ledger changed during backup; capture is unusable")
        manifest = {"schema_version": 1, "kind": "ledger-compatibility-backup",
                    "project_id": load_ledger(project)["project_id"], "created_at": utc_now(),
                    "ledger_sha256": before, "files": records}
        path = directory / "manifest.json"
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(manifest, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        path.chmod(0o444)
        if os.name != "nt":
            for folder in [*sorted((item for item in directory.rglob("*") if item.is_dir()), reverse=True), directory, directory.parent]:
                descriptor = os.open(folder, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        return {"backup_ref": path.relative_to(project).as_posix(), "backup_sha256": file_sha(path),
                "ledger_sha256": before, "file_count": len(records)}


def verify_backup(repo: Path, project: Path, reference: str, expected_hash: str) -> dict[str, Any]:
    path = project_file(project, reference)
    _no_symlink_chain(project, path)
    if not reference.startswith(".runtime/backups/") or path.name != "manifest.json":
        raise TurnUpTimeGraphError("compatibility migration requires a runtime backup manifest")
    if file_sha(path) != expected_hash:
        raise TurnUpTimeGraphError("backup manifest hash mismatch")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if (set(manifest) != {"schema_version", "kind", "project_id", "created_at", "ledger_sha256", "files"}
                or manifest["schema_version"] != 1 or manifest["kind"] != "ledger-compatibility-backup"
                or manifest["project_id"] != load_ledger(project)["project_id"]
                or manifest["ledger_sha256"] != file_sha(project / "project-ledger.json")):
            raise ValueError("backup identity differs")
        records = manifest["files"]
        if not isinstance(records, list):
            raise ValueError("files must be an array")
        sources = _sources(repo, project)
        # Files created by a later record_artifact/operation need a fresh snapshot.
        if {row["source"] for row in records} != set(sources) or len(records) != len(sources):
            raise ValueError("backup file inventory differs")
        for row in records:
            expected_kind = "sqlite-online-backup" if sources[row["source"]].suffix == ".sqlite" else "exact-bytes"
            if row["kind"] != expected_kind:
                raise ValueError("backup kind differs from source format")
            expected_fields = {"source", "path", "sha256", "kind"}
            if row["kind"] == "sqlite-online-backup":
                expected_fields.add("logical_sha256")
            if set(row) != expected_fields:
                raise ValueError("unsupported backup record fields")
            backup = project_file(project, row["path"])
            _no_symlink_chain(project, backup)
            if not backup.is_relative_to(path.parent / "files") or file_sha(backup) != row["sha256"]:
                raise ValueError("backup content differs")
            if row["kind"] == "exact-bytes":
                if file_sha(sources[row["source"]]) != row["sha256"]:
                    raise ValueError("source changed since backup")
            elif row["kind"] == "sqlite-online-backup":
                if sources[row["source"]].suffix != ".sqlite":
                    raise ValueError("invalid SQLite source")
                with sqlite3.connect(f"{backup.as_uri()}?mode=ro", uri=True) as connection:
                    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ValueError("invalid SQLite backup")
                if (_sqlite_digest(backup) != row["logical_sha256"]
                        or _sqlite_digest(sources[row["source"]]) != row["logical_sha256"]):
                    raise ValueError("SQLite contents changed since backup")
            else:
                raise ValueError("unsupported backup kind")
    except (KeyError, TypeError, ValueError, sqlite3.Error) as exc:
        raise TurnUpTimeGraphError(f"invalid or stale compatibility backup: {exc}") from exc
    return manifest


def migrate_compatibility(repo: Path, project: Path, ledger: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    plan = compatibility_plan(project)
    if data["profile"] != PROFILE or data["expected_ledger_sha256"] != plan["ledger_sha256"]:
        raise TurnUpTimeGraphError("compatibility profile or expected ledger hash mismatch")
    verify_backup(repo, project, data["backup_ref"], data["backup_sha256"])
    if not plan["changes"]:
        raise TurnUpTimeGraphError("compatibility profile has no changes; do not create a redundant migration")
    for risk in ledger["risks"]:
        risk["severity"] = _SEVERITIES.get(risk["severity"], risk["severity"])
    return ledger
