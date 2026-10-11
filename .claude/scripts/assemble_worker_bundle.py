#!/usr/bin/env python3
"""Assemble pinned provider instructions and validate independently consumed evidence.

Authorization and evaluator identities MUST come from the controller's trusted task
record, never the worker. Hash checks establish integrity, not author authenticity.
No provider commands are executed here; external readiness uses the existing resolver.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from resolve_capabilities import resolve

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / '.claude/schemas'
MAX_FILE = 8_000_000
IDENTITY = ('project_id', 'task_id', 'build_identity', 'generation_id')
AUTH_FIELDS = {*IDENTITY, 'schema_version', 'stage', 'role', 'capability_ids',
               'registry_sha256', 'lock_sha256', 'environment'}
HASH = re.compile(r'[a-f0-9]{64}\Z')


class BundleError(ValueError):
    pass


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BundleError('DUPLICATE_JSON_KEY:' + key)
        result[key] = value
    return result


def parse(raw: bytes) -> dict:
    if len(raw) > MAX_FILE:
        raise BundleError('ARTIFACT_TOO_LARGE')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                       parse_constant=lambda x: (_ for _ in ()).throw(BundleError('INVALID_NUMBER')))
    if not isinstance(value, dict):
        raise BundleError('OBJECT_REQUIRED')
    return value


def plain(path: Path) -> None:
    for item in [*reversed(path.absolute().parents), path.absolute()]:
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise BundleError('SYMLINK_OR_REPARSE:' + str(item))


def relative(value: str) -> None:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise BundleError('INVALID_PATH')
    parts = PurePosixPath(value).parts
    if (value != '/'.join(parts) or PurePosixPath(value).is_absolute()
            or any(p in {'.', '..'} or p.endswith((' ', '.')) for p in parts)
            or any(ord(c) < 33 or ord(c) > 126 or c in '\\:*?"<>|' for c in value)
            or any(re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', p) for p in parts)):
        raise BundleError('UNSAFE_PATH:' + value)


def confined(root: Path, value: str) -> Path:
    relative(value)
    path = root / value
    plain(path)
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise BundleError('NON_REGULAR_ARTIFACT:' + value)
    if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_size > MAX_FILE:
        raise BundleError('INVALID_ARTIFACT_SIZE_OR_TYPE:' + value)
    return path


def schema(value: dict, name: str) -> None:
    contract = parse((SCHEMAS / name).read_bytes())
    errors = sorted(Draft202012Validator(contract, format_checker=FormatChecker()).iter_errors(value), key=lambda e: str(e.path))
    if errors:
        raise BundleError('INVALID_CONTRACT:' + errors[0].message)


def exact(value: dict, fields: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise BundleError('UNKNOWN_OR_MISSING_FIELDS')


def unique(values: list[str]) -> None:
    if not isinstance(values, list) or not values or len(values) > 512 or any(
            not isinstance(v, str) or not v or len(v) > 256 for v in values):
        raise BundleError('INVALID_IDENTITIES')
    if len({v.casefold() for v in values}) != len(values):
        raise BundleError('DUPLICATE_OR_CASE_COLLISION')


def references(root: Path, refs: list[dict], *, nonempty=True) -> list[bytes]:
    seen = set()
    spellings = {}
    result = []
    if not isinstance(refs, list) or len(refs) > 512 or (nonempty and not refs):
        raise BundleError('EVIDENCE_REQUIRED')
    for ref in refs:
        exact(ref, {'path', 'sha256'})
        if not isinstance(ref['sha256'], str) or not HASH.fullmatch(ref['sha256']):
            raise BundleError('INVALID_HASH')
        relative(ref['path'])
        parts = PurePosixPath(ref['path']).parts
        for index in range(1, len(parts) + 1):
            prefix = '/'.join(parts[:index])
            previous = spellings.setdefault(prefix.casefold(), prefix)
            if previous != prefix:
                raise BundleError('DUPLICATE_OR_CASE_COLLISION')
        if ref['path'].casefold() in seen:
            raise BundleError('DUPLICATE_OR_CASE_COLLISION')
        seen.add(ref['path'].casefold())
    # Reject every collision before touching disk, so case-sensitive filesystems fail the same way.
    for ref in refs:
        raw = confined(root, ref['path']).read_bytes()
        if digest(raw) != ref['sha256']:
            raise BundleError('ARTIFACT_HASH_MISMATCH:' + ref['path'])
        if nonempty and not raw.strip():
            raise BundleError('EMPTY_EVIDENCE:' + ref['path'])
        result.append(raw)
    return result


def authorization(value: dict) -> None:
    exact(value, AUTH_FIELDS | ({'ui_surfaces'} if isinstance(value, dict) and 'ui_surfaces' in value else set()))
    if value['schema_version'] != 1:
        raise BundleError('AUTH_VERSION')
    for key in AUTH_FIELDS - {'schema_version', 'capability_ids'}:
        if not isinstance(value[key], str) or not value[key] or len(value[key]) > 256:
            raise BundleError('AUTH_VALUE:' + key)
    unique(value['capability_ids'])
    relative(value['generation_id'])
    if '/' in value['generation_id'] or any(not HASH.fullmatch(value[k]) for k in ('registry_sha256', 'lock_sha256')):
        raise BundleError('AUTH_PIN_REQUIRED')
    if 'ui_surfaces' in value:
        string = {'type':'string', 'minLength':1, 'maxLength':256}
        surface_schema = {'type':'array', 'maxItems':32, 'items':{'type':'object', 'additionalProperties':False,
            'required':['id','platform','purpose','stack','flags','verification_capabilities'], 'properties':{
                'id':string, 'platform':{'enum':['web','native']},
                'purpose':{'enum':['operate','persuade','read','experience']}, 'stack':string,
                'flags':{'type':'array','maxItems':32,'uniqueItems':True,'items':string},
                'verification_capabilities':{'type':'array','maxItems':32,'uniqueItems':True,'items':string}}}}
        if not Draft202012Validator(surface_schema).is_valid(value['ui_surfaces']):
            raise BundleError('INVALID_AUTHORIZED_UI_SURFACES')
        if value['ui_surfaces']:
            unique([s['id'] for s in value['ui_surfaces']])


def provider_installer():
    # Read-only APIs owned by provider_install; never invoke its mutation CLI.
    spec = importlib.util.spec_from_file_location('tut_provider_install_read', ROOT / 'scripts/provider_install.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generation(home: Path, generation_id: str) -> Path:
    provider_installer().verify_generation(home, generation_id)
    return home / 'provider-generations' / generation_id


def assemble(home: Path, project: Path, auth: dict, *, role: str, stage: str,
             build_identity: str, requested: list[str], readiness: dict | None = None) -> dict:
    authorization(auth)
    unique(requested)
    if role != auth['role'] or stage != auth['stage'] or build_identity != auth['build_identity']:
        raise BundleError('TASK_AUTHORIZATION_MISMATCH')
    if project.name != auth['project_id']:
        raise BundleError('PROJECT_MISMATCH')
    root = generation(home, auth['generation_id'])
    registry_raw = confined(root, 'registry.json').read_bytes()
    lock_raw = confined(root, 'provider-lock.json').read_bytes()
    if digest(registry_raw) != auth['registry_sha256'] or digest(lock_raw) != auth['lock_sha256']:
        raise BundleError('GENERATION_AUTHORIZATION_HASH_MISMATCH')
    registry_doc, lock = parse(registry_raw), parse(lock_raw)
    schema(registry_doc, 'capability-registry.schema.json')
    registry = registry_doc['capabilities']
    if readiness is not None:
        schema(readiness, 'capability-readiness.schema.json')
        for proof in readiness['receipts']:
            references(project, proof['evidence_refs'])
    code, plan = resolve(requested, registry, [root / 'skills'], readiness=readiness,
                         project=project, environment=auth['environment'], build_identity=build_identity,
                         ui_surfaces=auth.get('ui_surfaces'))
    if code:
        raise BundleError('RESOLVER_BLOCKED:' + json.dumps(plan['errors'], sort_keys=True))
    if set(plan['selected']) != set(auth['capability_ids']):
        raise BundleError('CAPABILITY_AUTHORIZATION_MISMATCH')
    for cap in plan['selected']:
        if stage not in registry[cap]['stages']:
            raise BundleError('STAGE_NOT_ALLOWED:' + cap)
        if registry[cap]['authority'] == 'control' and role not in {'turn-up-time', 'root', 'controller'}:
            raise BundleError('CONTROLLER_ONLY_CAPABILITY:' + cap)
    packages = {p['name']: p for p in lock['packages']}
    if len(packages) != len(lock['packages']):
        raise BundleError('DUPLICATE_PROVIDER')
    groups = {}
    for cap in sorted(plan['selected']):
        groups.setdefault(registry[cap]['provider'], []).append(cap)
    providers = []
    for provider, caps in sorted(groups.items()):
        package = packages.get(provider)
        if not package:
            raise BundleError('PROVIDER_NOT_LOCKED:' + provider)
        kinds = {registry[c]['provider_kind'] for c in caps}
        authorities = {registry[c]['authority'] for c in caps}
        effective_authorities = authorities - {'reference'} or {'reference'}
        if len(effective_authorities) != 1:
            raise BundleError('INCOMPATIBLE_PROVIDER_BINDINGS:' + provider)
        assets = [{'path': f'skills/{provider}/{p}', 'sha256': info['sha256']}
                  for p, info in sorted(package['files'].items())]
        raw_assets = references(root, assets, nonempty=False)
        # Include all locked UTF-8 documentation deterministically, preserving bytes
        # within each resource. Binary/template assets remain available by hashed path.
        documents = []
        for ref, raw in zip(assets, raw_assets):
            if ref['path'].lower().endswith(('.md', '.txt', '.rst')):
                documents.append('RESOURCE ' + ref['path'] + '\n' + raw.decode('utf-8'))
        instructions = '\n\n'.join(documents)
        if not instructions.strip():
            raise BundleError('EMPTY_INSTRUCTIONS')
        readiness_refs = []
        readiness_expiries = []
        for proof in (readiness or {}).get('receipts', []):
            if proof['capability'] in caps and proof['provider'] == provider and registry[proof['capability']]['provider_kind'] == 'external':
                readiness_expiries.append(datetime.fromisoformat(proof['expires_at'].replace('Z', '+00:00')))
                for ref in proof['evidence_refs']:
                    if ref not in readiness_refs:
                        readiness_refs.append(ref)
        repo = lock['repositories'][package['repository']]
        providers.append(dict(provider=provider, capabilities=caps, provider_kind='external' if 'external' in kinds else 'instruction-only',
            authority=next(iter(effective_authorities)), source_ref=provider_installer().repository_source_ref(repo),
            entrypoint=f'skills/{provider}/SKILL.md', assets=assets, instructions_utf8=instructions,
            instructions_sha256=digest(instructions.encode('utf-8')), readiness_status='READY', readiness_refs=readiness_refs,
            readiness_valid_until=min(readiness_expiries).isoformat() if readiness_expiries else None,
            readiness_environment=auth['environment'] if 'external' in kinds else None,
            required_outputs=sorted({o for c in caps for o in registry[c]['produces']})))
    manifest = {k: auth[k] for k in IDENTITY}
    manifest.update(schema_version=1, stage=stage, role=role, registry_sha256=digest(registry_raw),
        lock_sha256=digest(lock_raw), selected_capabilities=sorted(plan['selected']), providers=providers,
        required_outputs=sorted({o for c in plan['selected'] for o in registry[c]['produces']}))
    schema(manifest, 'worker-bundle.schema.json')
    return manifest


def validate_dispatch_readiness(manifest: dict, trusted_environment: str, *, now: datetime | None = None) -> None:
    """Check freshness immediately before dispatch; this is not a connectivity probe.

    Studio's trusted environment is derived from its local runtime, e.g.
    local:win32, never from a worker-start request. Receipt validation is
    retrospective and does not apply this current-clock check to past work.
    """
    schema(manifest, 'worker-bundle.schema.json')
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise BundleError('DISPATCH_CLOCK_TIMEZONE_REQUIRED')
    for provider in manifest['providers']:
        if provider['provider_kind'] != 'external':
            continue
        expires = datetime.fromisoformat(provider['readiness_valid_until'].replace('Z', '+00:00'))
        if expires.tzinfo is None or expires <= current:
            raise BundleError('READINESS_EXPIRED_BEFORE_DISPATCH')
        if provider['readiness_environment'] != trusted_environment:
            raise BundleError('READINESS_DISPATCH_ENVIRONMENT_MISMATCH')


def validate_receipt(project: Path, manifest_raw: bytes, receipt: dict, auth: dict, *,
                     manifest_sha256: str, dispatch_id: str, worker_id: str, evaluator_id: str) -> dict:
    authorization(auth)
    if not isinstance(manifest_sha256, str) or not HASH.fullmatch(manifest_sha256) or digest(manifest_raw) != manifest_sha256:
        raise BundleError('TRUSTED_MANIFEST_HASH_MISMATCH')
    manifest = parse(manifest_raw)
    schema(manifest, 'worker-bundle.schema.json')
    schema(receipt, 'worker-provider-receipt.schema.json')
    for key in (*IDENTITY, 'role', 'stage', 'registry_sha256', 'lock_sha256'):
        if manifest[key] != auth[key]:
            raise BundleError('MANIFEST_AUTHORIZATION_MISMATCH:' + key)
    if set(manifest['selected_capabilities']) != set(auth['capability_ids']):
        raise BundleError('CAPABILITY_AUTHORIZATION_MISMATCH')
    unique(manifest['selected_capabilities'])
    unique([p['provider'] for p in manifest['providers']])
    flattened = [c for p in manifest['providers'] for c in p['capabilities']]
    unique(flattened)
    if set(flattened) != set(manifest['selected_capabilities']):
        raise BundleError('PROVIDER_CAPABILITY_COVERAGE_MISMATCH')
    unique(manifest['required_outputs'])
    for provider in manifest['providers']:
        unique(provider['required_outputs'])
    if {o for p in manifest['providers'] for o in p['required_outputs']} != set(manifest['required_outputs']):
        raise BundleError('PROVIDER_OUTPUT_CONTRACT_COVERAGE_MISMATCH')
    for key in IDENTITY:
        if receipt[key] != manifest[key]:
            raise BundleError('RECEIPT_CONTEXT_MISMATCH:' + key)
    if project.name != auth['project_id'] or receipt['dispatch_id'] != dispatch_id:
        raise BundleError('DISPATCH_OR_PROJECT_MISMATCH')
    if receipt['manifest_sha256'] != digest(manifest_raw):
        raise BundleError('MANIFEST_HASH_MISMATCH')
    selected = [p for p in manifest['providers'] if p['provider'] == receipt['provider']]
    if len(selected) != 1:
        raise BundleError('PROVIDER_NOT_SELECTED')
    provider = selected[0]
    if (receipt['instruction_sha256'] != provider['instructions_sha256']
            or digest(provider['instructions_utf8'].encode()) != provider['instructions_sha256']
            or set(receipt['capability_ids']) != set(provider['capabilities'])):
        raise BundleError('INSTRUCTION_OR_CAPABILITY_MISMATCH')
    if receipt['status'] != 'APPLIED':
        return {'status': receipt['status'], 'accepted': False}
    if not worker_id or not evaluator_id or evaluator_id == worker_id:
        raise BundleError('INDEPENDENT_EVALUATOR_REQUIRED')
    invocations = references(project, receipt['invocation_refs'])
    references(project, receipt['output_refs'])
    consumers = references(project, receipt['consumed_by'])
    if receipt['verification_ref'] is None:
        raise BundleError('INDEPENDENT_VERIFICATION_REQUIRED')
    verification_raw = references(project, [receipt['verification_ref']])[0]
    context = {k: receipt[k] for k in (*IDENTITY, 'dispatch_id', 'provider', 'manifest_sha256', 'instruction_sha256')}
    for raw in invocations:
        record = parse(raw)
        exact(record, {*context, 'worker_id', 'status'})
        if any(record[k] != v for k, v in context.items()) or record['worker_id'] != worker_id or record['status'] != 'COMPLETED':
            raise BundleError('INVOCATION_CONTEXT_MISMATCH')
    output_set = {(r['path'], r['sha256']) for r in receipt['output_refs']}
    used = set()
    consumed_contracts = set()
    for raw in consumers:
        record = parse(raw)
        exact(record, {*context, 'contract_id', 'output_refs', 'status'})
        if any(record[k] != v for k, v in context.items()) or record['status'] != 'PASS' or record['contract_id'] not in provider['required_outputs']:
            raise BundleError('CONSUMPTION_CONTRACT_MISMATCH')
        consumed_contracts.add(record['contract_id'])
        references(project, record['output_refs'])
        used.update((r['path'], r['sha256']) for r in record['output_refs'])
    if used != output_set:
        raise BundleError('UNCONSUMED_OUTPUT')
    if consumed_contracts != set(provider['required_outputs']):
        raise BundleError('MISSING_REQUIRED_OUTPUT_CONTRACT')
    verification = parse(verification_raw)
    exact(verification, {*context, 'evaluator_id', 'worker_id', 'status', 'evidence_refs'})
    if (any(verification[k] != v for k, v in context.items()) or verification['status'] != 'PASS'
            or verification['evaluator_id'] != evaluator_id or verification['worker_id'] != worker_id):
        raise BundleError('INDEPENDENT_VERIFICATION_MISMATCH')
    references(project, verification['evidence_refs'])
    required_refs = receipt['invocation_refs'] + receipt['output_refs'] + receipt['consumed_by']
    if {(r['path'], r['sha256']) for r in verification['evidence_refs']} != {(r['path'], r['sha256']) for r in required_refs}:
        raise BundleError('VERIFICATION_COVERAGE_MISMATCH')
    # A worker log/receipt is never itself a useful provider output.
    proof_paths = {r['path'].casefold() for r in receipt['invocation_refs'] + receipt['consumed_by'] + [receipt['verification_ref']]}
    if any(r['path'].casefold() in proof_paths for r in receipt['output_refs']):
        raise BundleError('OUTPUT_IS_SELF_REPORT')
    return {'status': 'APPLIED', 'accepted': True, 'provider': receipt['provider'], 'dispatch_id': dispatch_id}


def studio_task_spec(manifest_raw: bytes, brief: str) -> dict:
    """Export for authenticated coordinator persistence, never grant authorization."""
    manifest = parse(manifest_raw)
    schema(manifest, 'worker-bundle.schema.json')
    if not isinstance(brief, str) or not brief.strip() or len(brief) > 100000:
        raise BundleError('INVALID_TASK_BRIEF')
    binding = {k: manifest[k] for k in (*IDENTITY, 'stage', 'role', 'registry_sha256', 'lock_sha256', 'selected_capabilities')}
    binding['manifest_sha256'] = digest(manifest_raw)
    return {'kind':'tut-worker-task-v1', 'brief':brief, 'authorization':binding}


def export_task(worktree: Path, project: Path, manifest_path: str, manifest_sha256: str,
                auth: dict, brief: str) -> dict:
    """Convert project-relative evidence into the trusted Studio worktree namespace.

    This produces a coordinator input artifact, not an approval or a task mutation.
    The coordinator must bind it using Studio's authenticated tutTaskBind operation.
    """
    authorization(auth)
    plain(worktree)
    plain(project)
    if not worktree.is_dir() or not project.is_dir() or not project.resolve().is_relative_to(worktree.resolve()):
        raise BundleError('PROJECT_OUTSIDE_TRUSTED_WORKTREE')
    manifest_file = confined(project, manifest_path)
    manifest_raw = manifest_file.read_bytes()
    if not isinstance(manifest_sha256, str) or not HASH.fullmatch(manifest_sha256) or digest(manifest_raw) != manifest_sha256:
        raise BundleError('TRUSTED_MANIFEST_HASH_MISMATCH')
    manifest = parse(manifest_raw)
    schema(manifest, 'worker-bundle.schema.json')
    for key in (*IDENTITY, 'role', 'stage', 'registry_sha256', 'lock_sha256'):
        if manifest[key] != auth[key]:
            raise BundleError('MANIFEST_AUTHORIZATION_MISMATCH:' + key)
    if project.name != auth['project_id'] or set(manifest['selected_capabilities']) != set(auth['capability_ids']):
        raise BundleError('TASK_AUTHORIZATION_MISMATCH')
    worktree_relative = manifest_file.resolve().relative_to(worktree.resolve()).as_posix()
    # Validate in both namespaces; a conversion cannot grant access outside either.
    converted = confined(worktree, worktree_relative)
    if converted.resolve() != manifest_file.resolve():
        raise BundleError('MANIFEST_PATH_CONVERSION_MISMATCH')
    return {'schema_version':1, 'task_spec':studio_task_spec(manifest_raw, brief),
            'worker_start_params':{'task':auth['task_id'], 'tutCapabilityBundle':{
                'manifestPath':worktree_relative, 'manifestSha256':manifest_sha256,
                'role':auth['role'], 'capabilityIds':manifest['selected_capabilities']}}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['assemble', 'export-task', 'validate-receipt'])
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--authorization', type=Path, required=True, help='Controller-owned trusted task record')
    parser.add_argument('--home', type=Path)
    parser.add_argument('--worktree', type=Path, help='Controller-selected Studio worktree root')
    parser.add_argument('--brief-file', help='Task brief path relative to project')
    parser.add_argument('--role')
    parser.add_argument('--stage')
    parser.add_argument('--build-identity')
    parser.add_argument('--capability', action='append', default=[])
    parser.add_argument('--readiness', type=Path)
    parser.add_argument('--output', help='New manifest/export path relative to project')
    parser.add_argument('--manifest')
    parser.add_argument('--manifest-sha256', help='Exact hash from trusted controller task record')
    parser.add_argument('--receipt')
    parser.add_argument('--dispatch-id')
    parser.add_argument('--worker-id')
    parser.add_argument('--evaluator-id')
    args = parser.parse_args()
    try:
        plain(args.authorization)
        auth = parse(args.authorization.read_bytes())
        if args.command == 'assemble':
            if not args.home or not args.output:
                raise BundleError('HOME_AND_OUTPUT_REQUIRED')
            readiness = parse(args.readiness.read_bytes()) if args.readiness else None
            result = assemble(args.home, args.project, auth, role=args.role, stage=args.stage,
                build_identity=args.build_identity, requested=args.capability, readiness=readiness)
            relative(args.output)
            destination = args.project / args.output
            plain(destination.parent)
            raw = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
            with destination.open('xb') as handle:
                handle.write(raw)
            print(json.dumps({'status':'READY', 'manifest':{'path':args.output, 'sha256':digest(raw)}}))
        elif args.command == 'export-task':
            if not args.worktree or not args.output or not args.brief_file:
                raise BundleError('WORKTREE_OUTPUT_AND_BRIEF_REQUIRED')
            brief = confined(args.project, args.brief_file).read_text(encoding='utf-8')
            result = export_task(args.worktree, args.project, args.manifest, args.manifest_sha256, auth, brief)
            relative(args.output)
            destination = args.project / args.output
            plain(destination.parent)
            raw = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
            with destination.open('xb') as handle:
                handle.write(raw)
            print(json.dumps({'status':'READY', 'export':{'path':args.output, 'sha256':digest(raw)}}))
        else:
            manifest_raw = confined(args.project, args.manifest).read_bytes()
            receipt = parse(confined(args.project, args.receipt).read_bytes())
            result = validate_receipt(args.project, manifest_raw, receipt, auth, manifest_sha256=args.manifest_sha256, dispatch_id=args.dispatch_id,
                                      worker_id=args.worker_id, evaluator_id=args.evaluator_id)
            print(json.dumps(result))
            return 0 if result['accepted'] else 2
        return 0
    except Exception as exc:
        print(json.dumps({'status':'BLOCKED', 'errors':[str(exc)]}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
