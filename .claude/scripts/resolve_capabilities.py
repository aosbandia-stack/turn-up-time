#!/usr/bin/env python3
"""Resolve only selected capabilities; required providers fail closed."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from contract_evidence import check_assets, local_path, read_contract, timestamp


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError(f'{path} must contain an object')
    return value


def merge_registries(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(base.get('capabilities', {}))
    if override:
        merged.update(override.get('capabilities', {}))
    return merged


def provider_exists(provider: str, roots: list[Path]) -> bool:
    if Path(provider).name != provider or provider in {'.', '..'}:
        return False
    for root in roots:
        try:
            if (root / provider / 'SKILL.md').read_text(encoding='utf-8').strip():
                return True
        except (OSError, UnicodeError):
            continue
    return False


def capability_closure(requested: list[str], registry: dict[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    queue = list(dict.fromkeys(requested))
    selected: list[str] = []
    errors: list[dict[str, str]] = []
    while queue:
        name = queue.pop(0)
        if name in selected:
            continue
        entry = registry.get(name)
        if not isinstance(entry, dict):
            errors.append({'code': 'UNKNOWN_CAPABILITY', 'capability': name})
            continue
        selected.append(name)
        queue.extend(item for item in entry.get('requires', []) if item not in selected and item not in queue)
    return selected, errors


def expand_ui(surfaces: list[dict[str, Any]], registry: dict[str, Any], project: Path | None = None) -> tuple[dict[str, list[str]], list[dict[str, str]]]:
    """One registry expansion for CLI and stage gates; selectors are not provider APIs."""
    expanded: dict[str, list[str]] = {}
    errors: list[dict[str, str]] = []
    for surface in surfaces:
        label = surface.get('id', 'cli')
        platform, purpose = surface.get('platform'), surface.get('purpose')
        if platform not in {'web', 'native'} or purpose not in {'operate', 'persuade', 'read', 'experience'}:
            errors.append({'code':'UNKNOWN_UI_SELECTOR', 'capability':label})
            continue
        names = []
        for flag in [None, *surface.get('flags', [])]:
            matches = [name for name, entry in registry.items()
                       if entry.get('ui_selector', {}).get('flag') == flag
                       and platform in entry.get('ui_selector', {}).get('platforms', [])
                       and purpose in entry.get('ui_selector', {}).get('purposes', [])]
            if not matches or (flag is None and not any(registry[name]['authority'] == 'production' for name in matches)):
                errors.append({'code':'UI_SELECTOR_UNAVAILABLE', 'capability':str(flag or purpose)})
            names.extend(matches)
        verification = surface.get('verification_capabilities', [])
        if platform == 'native' and not verification:
            errors.append({'code':'NATIVE_ASSURANCE_REQUIRED', 'capability':label})
        for name in verification:
            entry = registry.get(name, {})
            if entry.get('authority') != 'assurance' or entry.get('provider_kind') != 'external' or platform not in entry.get('supported_platforms', []):
                errors.append({'code':'UI_ASSURANCE_ADAPTER_INVALID', 'capability':name})
        names.extend(verification)
        selected, failures = capability_closure(names, registry)
        errors.extend(failures)
        for name in selected:
            entry = registry[name]
            if entry.get('supported_platforms') and platform not in entry['supported_platforms']:
                errors.append({'code':'UI_PLATFORM_INCOMPATIBLE', 'capability':name})
            if entry.get('compatible_stacks') and surface.get('stack') not in entry['compatible_stacks']:
                errors.append({'code':'UI_STACK_INCOMPATIBLE', 'capability':name})
            # A nonstandard 21st mapping needs an explicit reviewed adapter in
            # addition to its stack declaration, never an invented native API.
            if entry.get('ui_selector', {}).get('flag') in {'21st-catalog','21st-generate'} and surface.get('stack') != 'react-tailwind':
                failures = []
                if not project or not entry.get('stack_adapter_ref'):
                    failures.append('UI_STACK_ADAPTER_REQUIRED')
                else:
                    local_path(project, entry['stack_adapter_ref'], failures)
                errors.extend({'code':code, 'capability':name} for code in failures)
        expanded[label] = selected
    return expanded, errors


def resolve(requested: list[str], registry: dict[str, Any], provider_roots: list[Path], *, readiness: dict[str, Any] | None = None, project: Path | None = None, environment: str | None = None, build_identity: str | None = None, require_use: bool = False, ui_surfaces: list[dict[str, Any]] | None = None) -> tuple[int, dict[str, Any]]:
    surfaces, errors = expand_ui(ui_surfaces or [], registry, project)
    ui_required = list(dict.fromkeys(name for names in surfaces.values() for name in names))
    selected, failures = capability_closure(requested + ui_required, registry)
    errors.extend(failures)
    plan = []
    for name in selected:
        entry = registry[name]
        provider = str(entry.get('provider', ''))
        installed = provider_exists(provider, provider_roots)
        kind = entry.get('provider_kind')
        local_errors: list[str] = []
        flag = entry.get('ui_selector', {}).get('flag')
        if flag in {'21st-catalog','21st-generate'} and kind != 'external':
            local_errors.append('UI_EXTERNAL_PROVIDER_REQUIRED')
        if not installed:
            local_errors.append('REQUIRED_PROVIDER_MISSING')
        if kind not in {'instruction-only', 'external'}:
            local_errors.append('PROVIDER_KIND_REQUIRED: migrate registry to schema_version 3')
        for conflict in entry.get('conflicts', []):
            if conflict in selected:
                local_errors.append('CAPABILITY_CONFLICT')
        usable = installed and kind == 'instruction-only'
        used = False
        context_ok = bool(readiness and project and readiness.get('project_id') == project.name and environment and readiness.get('environment') == environment)
        if kind == 'external':
            receipts = [r for r in (readiness or {}).get('receipts', []) if r.get('capability') == name and r.get('provider') == provider]
            if not context_ok or len(receipts) != 1:
                local_errors.append('READINESS_PROOF_REQUIRED')
            else:
                receipt = receipts[0]
                proof_errors: list[str] = []
                try:
                    checked = timestamp(receipt['checked_at'])
                    expires = timestamp(receipt['expires_at'])
                    now = datetime.now(timezone.utc)
                    if receipt['status'] != 'PASS' or not checked <= now < expires or expires - checked > timedelta(hours=24):
                        proof_errors.append('READINESS_EXPIRED_OR_FAILED')
                    if not receipt['evidence_refs']:
                        proof_errors.append('READINESS_EVIDENCE_MISSING')
                    check_assets(project, receipt['evidence_refs'], proof_errors)
                    required_checks = set(entry.get('readiness_requirements', []))
                    if flag in {'21st-catalog','21st-generate'}:
                        required_checks.add('tool_access')
                    if flag == '21st-generate':
                        required_checks.add('entitlement')
                    for check in sorted(required_checks):
                        if receipt.get('checks', {}).get(check) != 'PASS':
                            proof_errors.append('READINESS_CHECK_REQUIRED:' + check)
                except (KeyError, ValueError, TypeError):
                    proof_errors.append('INVALID_READINESS_PROOF')
                local_errors.extend(proof_errors)
                usable = installed and not proof_errors
        usages = [r for r in (readiness or {}).get('usage', []) if r.get('capability') == name and r.get('provider') == provider]
        if usages:
            use_errors: list[str] = []
            if not context_ok or len(usages) != 1 or not build_identity or usages[0].get('build_identity') != build_identity:
                use_errors.append('USAGE_CONTEXT_MISMATCH')
            else:
                for key in ('invocation_refs', 'output_refs'):
                    if not usages[0].get(key):
                        use_errors.append('USAGE_EVIDENCE_MISSING')
                    else:
                        check_assets(project, usages[0][key], use_errors)
            local_errors.extend(use_errors)
            used = not use_errors
        if require_use and kind == 'external' and not used:
            local_errors.append('ACTUAL_USE_PROOF_REQUIRED')
        for code in local_errors:
            errors.append({'code': code, 'capability': name, 'provider': provider})
        plan.append({'capability': name, 'provider': provider, 'provider_kind': kind, 'installed': installed, 'usable': usable, 'used': used, 'bundled': bool(entry.get('bundled')), 'authority': entry.get('authority'), 'stages': entry.get('stages', []), 'mode': entry.get('mode', 'default'), 'load_policy': entry.get('load_policy'), 'provenance':entry.get('provenance')})
    output = {'requested': requested, 'selected': selected, 'ui_required':ui_required, 'ui_surfaces':surfaces, 'plan': plan, 'errors': errors, 'status': 'BLOCKED' if errors else 'READY'}
    return (2 if errors else 0), output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('capabilities', nargs='*')
    parser.add_argument('--registry', type=Path, default=Path(__file__).resolve().parents[1] / 'capabilities' / 'registry.json')
    parser.add_argument('--user-registry', type=Path, default=Path.home() / '.claude' / 'capabilities' / 'registry.json')
    parser.add_argument('--project-registry', type=Path)
    parser.add_argument('--provider-root', action='append', type=Path, default=[])
    parser.add_argument('--readiness', type=Path)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--environment')
    parser.add_argument('--build-identity')
    parser.add_argument('--require-use', action='store_true')
    parser.add_argument('--ui-platform')
    parser.add_argument('--ui-purpose')
    parser.add_argument('--ui-stack')
    parser.add_argument('--ui-flag', action='append', default=[])
    parser.add_argument('--ui-verification-capability', action='append', default=[])
    args = parser.parse_args()
    errors: list[str] = []
    registry = {}
    for path in (args.registry, args.user_registry, args.project_registry):
        if path and (path.is_file() or path == args.registry):
            value = read_contract(path, 'capability-registry.schema.json', errors)
            if value:
                registry.update(value['capabilities'])
    readiness = read_contract(args.readiness, 'capability-readiness.schema.json', errors) if args.readiness else None
    if errors:
        print(json.dumps({'status':'BLOCKED', 'errors':errors}, indent=2))
        return 2
    roots = args.provider_root + [Path.cwd() / '.claude' / 'skills', Path.home() / '.claude' / 'skills', Path(__file__).resolve().parents[1] / 'skills']
    surfaces = []
    if args.ui_platform or args.ui_purpose or args.ui_stack or args.ui_flag or args.ui_verification_capability:
        surfaces = [{'id':'cli', 'platform':args.ui_platform, 'purpose':args.ui_purpose, 'stack':args.ui_stack,
                     'flags':args.ui_flag, 'verification_capabilities':args.ui_verification_capability}]
    if not args.capabilities and not surfaces:
        parser.error('request a capability or UI platform/purpose')
    code, output = resolve(args.capabilities, registry, roots, readiness=readiness, project=args.project.resolve() if args.project else None, environment=args.environment, build_identity=args.build_identity, require_use=args.require_use, ui_surfaces=surfaces)
    print(json.dumps(output, indent=2, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
