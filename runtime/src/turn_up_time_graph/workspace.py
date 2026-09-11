"""Deterministic identities for code and project evidence; no network access."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path, PurePosixPath

from .exceptions import TurnUpTimeGraphError
from .transactions import digest


def project_file(project: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise TurnUpTimeGraphError("expected a project-relative POSIX file path")
    rel = PurePosixPath(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise TurnUpTimeGraphError("external project path is not permitted")
    path = project.joinpath(*rel.parts)
    try:
        path.resolve(strict=True).relative_to(project.resolve(strict=True))
        if not path.is_file():
            raise ValueError("not a file")
    except (OSError, ValueError, RuntimeError) as exc:
        raise TurnUpTimeGraphError(f"missing or external project file: {relative}") from exc
    return path


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=30)
    if result.returncode:
        raise TurnUpTimeGraphError("unable to inspect Git workspace: " + result.stderr.decode(errors="replace"))
    return result.stdout


def build_identity(repo: Path) -> str:
    repo = repo.resolve()
    top = Path(_git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != repo:
        raise TurnUpTimeGraphError("repo-root must be the Git worktree root")
    head = _git(repo, "rev-parse", "HEAD").decode().strip()
    paths = set(_git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard").decode().split("\0"))
    entries = []
    for name in sorted(paths - {""}):
        if name.startswith((".claude/projects/", ".claude/runtime/")) or "__pycache__" in PurePosixPath(name).parts:
            continue
        path = repo / name
        if path.is_symlink():
            raise TurnUpTimeGraphError(f"symlink code requires an explicit supported identity policy: {name}")
        if not path.exists():
            entries.append([name, "DELETED"])
        elif path.is_file():
            entries.append([name, hashlib.sha256(path.read_bytes()).hexdigest()])
        else:
            raise TurnUpTimeGraphError(f"unsupported code entry (for example a submodule): {name}")
    return f"git:{head}:{digest(entries)}"


def evidence_manifest(project: Path) -> dict[str, str]:
    """Approval bytes are excluded to avoid a circular signature dependency."""
    result = {}
    roots = ["intake-readiness.json", "definition-of-good.json", "architecture.md", "traceability.json",
             "evidence", "tickets", "integration", "closeout", "release", "receipts"]
    for root in roots:
        path = project / root
        if not path.exists():
            continue
        paths = sorted(path.rglob("*")) if path.is_dir() else [path]
        for item in paths:
            if item.is_file():
                relative = item.relative_to(project).as_posix()
                checked = project_file(project, relative)
                result[relative] = hashlib.sha256(checked.read_bytes()).hexdigest()
    return result
