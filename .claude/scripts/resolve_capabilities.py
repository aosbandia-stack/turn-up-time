#!/usr/bin/env python3
"""Resolve ticket capability names to installed providers.

Project registry entries override user registry entries. Resolution fails closed on unknown
capabilities, declared conflicts, stage mismatches, or missing provider skill files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

CLAUDE_DIR = Path(__file__).resolve().parents[1]


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, dict):
        raise ValueError(f"Registry has no capabilities object: {path}")
    return capabilities


def provider_locations(provider: str, project_root: Path, user_home: Path) -> list[Path]:
    return [
        project_root / ".claude" / "skills" / provider / "SKILL.md",
        user_home / ".claude" / "skills" / provider / "SKILL.md",
        CLAUDE_DIR / "skills" / provider / "SKILL.md",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capabilities", nargs="+")
    parser.add_argument("--stage", default="BUILD")
    parser.add_argument("--project-root", default=str(Path.cwd()))
    parser.add_argument("--user-home", default=str(Path.home()))
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    user_home = Path(args.user_home).resolve()
    stage = args.stage.upper()

    merged: dict[str, Any] = {}
    registry_sources: list[str] = []
    bundled_registry = CLAUDE_DIR / "capabilities" / "registry.json"
    user_registry = user_home / ".claude" / "capabilities" / "registry.json"
    project_registry = project_root / ".claude" / "capabilities" / "registry.json"

    # Defaults first; later scopes deliberately override earlier scopes.
    for path in (bundled_registry, user_registry, project_registry):
        if path.exists():
            merged.update(load_registry(path))
            registry_sources.append(str(path))

    requested = list(dict.fromkeys(args.capabilities))
    unknown = [name for name in requested if name not in merged]
    if unknown:
        print(json.dumps({"status": "CAPABILITY_UNKNOWN", "capabilities": unknown}, indent=2))
        return 2

    resolved = {name: merged[name] for name in requested}
    providers = {entry["provider"] for entry in resolved.values()}
    conflicts: list[dict[str, str]] = []
    for name, entry in resolved.items():
        for token in entry.get("conflicts", []):
            kind, separator, value = token.partition(":")
            if separator and kind == "capability" and value in requested:
                conflicts.append({"capability": name, "conflict": token})
            elif separator and kind == "provider" and value in providers:
                conflicts.append({"capability": name, "conflict": token})
            elif not separator and (token in requested or token in providers):
                conflicts.append({"capability": name, "conflict": token})
    if conflicts:
        print(json.dumps({"status": "CAPABILITY_CONFLICT", "conflicts": conflicts}, indent=2))
        return 3

    stage_errors: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    receipt: list[dict[str, Any]] = []
    for name, entry in resolved.items():
        stages = entry.get("stages", [])
        if "ANY" not in stages and stage not in stages:
            stage_errors.append({"capability": name, "stage": stage, "allowed": stages})

        provider = entry["provider"]
        locations = provider_locations(provider, project_root, user_home)
        installed = next((path for path in locations if path.exists()), None)
        if installed is None:
            missing.append({"capability": name, "provider": provider, "searched": [str(path) for path in locations]})
        else:
            receipt.append(
                {
                    "capability": name,
                    "provider": provider,
                    "provider_path": str(installed),
                    "mode": entry.get("mode"),
                    "authority": entry.get("authority"),
                    "eval": entry.get("eval"),
                }
            )

    if stage_errors:
        print(json.dumps({"status": "CAPABILITY_STAGE_MISMATCH", "errors": stage_errors}, indent=2))
        return 4
    if missing:
        print(json.dumps({"status": "CAPABILITY_PROVIDER_MISSING", "missing": missing}, indent=2))
        return 5

    print(json.dumps({"status": "CAPABILITIES_READY", "stage": stage, "registry_sources": registry_sources, "resolved": receipt}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
