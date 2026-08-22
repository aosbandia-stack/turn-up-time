#!/usr/bin/env python3
"""Resolve ticket capabilities into a minimal, conflict-free provider plan."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def merge_registries(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(base.get("capabilities", {}))
    if override:
        merged.update(override.get("capabilities", {}))
    return merged


def provider_exists(provider: str, roots: list[Path]) -> bool:
    return any((root / provider / "SKILL.md").is_file() for root in roots)


def resolve(requested: list[str], registry: dict[str, Any], provider_roots: list[Path]) -> tuple[int, dict[str, Any]]:
    queue = list(dict.fromkeys(requested))
    selected: list[str] = []
    errors: list[dict[str, str]] = []

    while queue:
        name = queue.pop(0)
        if name in selected:
            continue
        entry = registry.get(name)
        if not isinstance(entry, dict):
            errors.append({"code": "UNKNOWN_CAPABILITY", "capability": name})
            continue
        selected.append(name)
        for required in entry.get("requires", []):
            if required not in selected and required not in queue:
                queue.append(required)

    selected_set = set(selected)
    for name in selected:
        entry = registry.get(name, {})
        for conflict in entry.get("conflicts", []):
            if conflict in selected_set:
                pair = "::".join(sorted((name, conflict)))
                if not any(error.get("pair") == pair for error in errors):
                    errors.append({"code": "CAPABILITY_CONFLICT", "pair": pair})
        provider = str(entry.get("provider", ""))
        if entry.get("bundled") and not provider_exists(provider, provider_roots):
            errors.append({"code": "BUNDLED_PROVIDER_MISSING", "capability": name, "provider": provider})

    plan = []
    for name in selected:
        entry = registry[name]
        provider = str(entry["provider"])
        installed = provider_exists(provider, provider_roots)
        plan.append(
            {
                "capability": name,
                "provider": provider,
                "installed": installed,
                "bundled": bool(entry.get("bundled")),
                "authority": entry.get("authority"),
                "stages": entry.get("stages", []),
                "mode": entry.get("mode", "default"),
                "load_policy": entry.get("load_policy"),
            }
        )
        if not installed and not entry.get("bundled"):
            errors.append({"code": "OPTIONAL_PROVIDER_NOT_INSTALLED", "capability": name, "provider": provider})

    blocking = [error for error in errors if error["code"] != "OPTIONAL_PROVIDER_NOT_INSTALLED"]
    output = {"requested": requested, "selected": selected, "plan": plan, "errors": errors, "status": "READY" if not blocking else "BLOCKED"}
    return (0 if not blocking else 2), output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capabilities", nargs="+")
    parser.add_argument("--registry", type=Path, default=Path(__file__).resolve().parents[1] / "capabilities" / "registry.json")
    parser.add_argument("--project-registry", type=Path)
    parser.add_argument("--provider-root", action="append", type=Path, default=[])
    args = parser.parse_args()

    base = load_json(args.registry)
    override = load_json(args.project_registry) if args.project_registry and args.project_registry.exists() else None
    registry = merge_registries(base, override)
    roots = list(args.provider_root)
    roots.extend([Path.cwd() / ".claude" / "skills", Path.home() / ".claude" / "skills"])
    code, output = resolve(args.capabilities, registry, roots)
    print(json.dumps(output, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
