"""Prepare and recover a quiescent, journaled Codex + Claude workflow promotion.

This is not a cross-filesystem atomic rename. Admission remains paused until the
complete cohort verifies. Preparation never replaces active entrypoints.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

import codex_installer as codex
import provider_install as providers
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.claude/scripts'))
from promotion_admission import check as admission_check

BARRIER = 'turn-up-time-promotion.json'
CORE_MANIFEST = 'turn-up-time-install-manifest.json'
CORE_DIRS = {'skills', 'agents', 'hooks', 'capabilities', 'schemas', 'templates', 'evals', 'profiles', 'scripts'}
SKIP = {'fresh_review.py', 'fresh_graph_review.py', 'notify.ps1'}
CATALOG = 'capabilities/runtime-catalog.json'
Error = codex.InstallError
hash_file = codex.file_hash
pack = codex.json_bytes


def read(path: Path):
    providers.plain_path(path)
    return json.loads(path.read_text(encoding='utf-8-sig'))


def target(home: Path, relative: str) -> Path:
    path = home / providers.safe_relative(relative)
    providers.plain_path(path)
    if path.exists() and not path.is_file():
        raise Error('Non-file target: ' + str(path))
    return path


def stream_hash(path: Path) -> str:
    providers.plain_path(path)
    if not path.is_file():
        raise Error('Missing retained runtime file: ' + str(path))
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def runtime_json(path: Path, schema_path: Path) -> dict:
    import jsonschema
    providers.plain_path(path)
    if path.stat().st_size > 32 * 1024 * 1024:
        raise Error('Runtime catalog/inventory exceeds 32 MiB')
    def unique(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise Error('Duplicate runtime catalog/inventory field')
            result[key] = value
        return result
    value = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)
    jsonschema.Draft202012Validator(read(schema_path)).validate(value)
    return value


def verify_runtime_catalog(path: Path, source: Path, generation: str, metadata_sha256: str) -> dict:
    """Validate retained executable payloads; this is not worker tool-use proof."""
    schemas = source / '.claude/schemas'
    catalog = runtime_json(path, schemas / 'tool-runtime-catalog.schema.json')
    if catalog['provider_generation'] != {'generation_id':generation, 'metadata_sha256':metadata_sha256}:
        raise Error('Runtime catalog/provider generation mismatch')
    inventories = [catalog['inventory'], catalog['providers']['serena']['interpreter_inventory']]
    for index, ref in enumerate(inventories):
        inventory_path = Path(ref['path'])
        if stream_hash(inventory_path) != ref['sha256']:
            raise Error('Runtime inventory metadata changed')
        inventory = runtime_json(inventory_path, schemas / 'tool-runtime-inventory.schema.json')
        if inventory['runtime_id'] != catalog['runtime_id']:
            raise Error('Runtime inventory identity mismatch')
        required_exclusions = ['.git'] if index == 0 else ['.git', 'Lib/site-packages']
        if inventory['exclusions'] != required_exclusions:
            raise Error('Runtime inventory exclusion mismatch')
        inventory_root = Path(inventory['root'])
        providers.plain_path(inventory_root)
        expected = {}
        folded = set()
        for row in inventory['files']:
            relative = providers.safe_relative(row['path']).as_posix()
            if relative.casefold() in folded:
                raise Error('Runtime inventory path collision')
            folded.add(relative.casefold())
            expected[relative] = row['sha256']
        # Share the runtime owner's exact scope/exclusion enumerator rather
        # than maintaining a second interpretation of executable inventory.
        import tool_runtime_catalog
        for scope in inventory['managed_paths']:
            scoped = inventory_root if scope == '.' else inventory_root / providers.safe_relative(scope)
            providers.plain_path(scoped)
        actual = {row['path']:row['sha256'] for row in tool_runtime_catalog.enumerate_files(inventory_root, inventory['managed_paths'], inventory['exclusions'])}
        if actual != expected:
            raise Error('Retained runtime inventory drift')
    # Explicit references outside managed roots (for example the installed
    # Codex binary) remain separately content-pinned, never copied or executed.
    def refs(value):
        if isinstance(value, dict):
            if set(value) == {'path', 'sha256'}:
                if stream_hash(Path(value['path'])) != value['sha256']:
                    raise Error('Runtime executable/context reference drift')
            else:
                for child in value.values():
                    refs(child)
    refs(catalog)
    providers.plain_path(Path(catalog['providers']['serena']['home_root']))
    return catalog


def prior_claude(home: Path, legacy_lock: Path | None) -> dict[str, str]:
    """Recognize only hash-proven ownership; no adoption of coincidental bytes."""
    owned = {}
    core_path = home / CORE_MANIFEST
    if core_path.exists():
        core = read(core_path)
        if core.get('schema_version') != 3:
            raise Error('Use shared release recovery for an already migrated installation')
        for row in core['files']:
            path = Path(row['path']).absolute()
            try:
                relative = path.relative_to(home).as_posix()
            except ValueError as exc:
                raise Error('Core ownership path outside home') from exc
            owned[relative] = row['installed_sha256']
        constitution = core.get('constitution', {})
        if constitution.get('replaced'):
            owned['CLAUDE.md'] = constitution['installed_sha256']
        runtime = core.get('graph_runtime', {})
        if runtime.get('enabled'):
            owned['runtime/turn-up-time/runtime-manifest.json'] = runtime['marker_sha256']
        owned[CORE_MANIFEST] = hash_file(core_path)
    old_provider_path = home / providers.MANIFEST
    if old_provider_path.exists():
        old = read(old_provider_path)
        if not legacy_lock or hash_file(legacy_lock) != old.get('lock_sha256'):
            raise Error('Exact archived provider lock is required')
        old_lock, sha = providers.read_lock(legacy_lock)
        expected = providers.expected(old_lock)
        providers.read_manifest(home, sha, expected)
        providers.verify(home, expected, old)
        for provider, files in expected.items():
            for relative, digest in files.items():
                key = 'skills/' + provider + '/' + relative
                if key in owned and owned[key] != digest:
                    raise Error('Prior ownership overlap mismatch: ' + key)
                owned[key] = digest
        owned[providers.MANIFEST] = hash_file(old_provider_path)
    for relative, sha in owned.items():
        if hash_file(target(home, relative)) != sha:
            raise Error('Modified owned Claude file: ' + relative)
    return owned


def claude_payload(source: Path, provider_home: Path, generation: str) -> dict[str, bytes]:
    meta = providers.verify_generation(provider_home, generation)
    root = providers.generation_path(provider_home, generation)
    if hash_file(source / '.claude/capabilities/registry.json') != meta['registry_sha256'] or hash_file(source / '.claude/capabilities/provider-lock.json') != meta['lock_sha256']:
        raise Error('Source and provider generation identity differ')
    payload = {}
    for directory in sorted(CORE_DIRS):
        for path in sorted((source / '.claude' / directory).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc' and path.name not in SKIP:
                providers.plain_path(path)
                payload[path.relative_to(source / '.claude').as_posix()] = path.read_bytes()
    payload['CLAUDE.md'] = (source / 'CLAUDE.md').read_bytes()
    for path in sorted((root / 'skills').rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        if relative in payload and payload[relative] != raw:
            raise Error('Core/provider snapshot overlap mismatch: ' + relative)
        payload[relative] = raw
    return payload


def preflight(source: Path, codex_home: Path, claude_home: Path, provider_home: Path, generation: str, legacy_lock: Path | None, runtime_catalog: Path | None = None) -> tuple[dict, dict, dict]:
    for home in (codex_home, claude_home):
        providers.plain_path(home)
    if codex_home == claude_home or codex_home.is_relative_to(claude_home) or claude_home.is_relative_to(codex_home):
        raise Error('Homes must be disjoint')
    if (claude_home / BARRIER).exists():
        raise Error('Prior promotion exists; use verify/recover before another promotion')
    installer = codex.Installer(source, codex_home)
    plan = installer.plan('update')
    if plan['status'] != 'PLAN' or plan.get('pending_operation') not in {None, 'COMMITTED', 'ROLLED_BACK'}:
        raise Error('Codex ownership or recovery conflict: ' + json.dumps(plan))
    owned = prior_claude(claude_home, legacy_lock)
    payload = claude_payload(source, provider_home, generation)
    for relative in payload:
        if target(claude_home, relative).exists() and relative not in owned:
            raise Error('Unmanaged Claude collision: ' + relative)
    if runtime_catalog is None:
        raise Error('A qualified retained runtime catalog is required')
    verify_runtime_catalog(runtime_catalog, source, generation,
                           hash_file(providers.generation_path(provider_home, generation) / 'generation.json'))
    if target(claude_home, CATALOG).exists() and CATALOG not in owned:
        raise Error('Unmanaged runtime catalog collision')
    payload[CATALOG] = runtime_catalog.read_bytes()
    return payload, owned, plan


class CaptureInstaller(codex.Installer):
    def transaction(self, desired, operation, fail_after=None):
        self.desired = desired

    def recover(self):
        # Preparation must never mutate an interrupted active installation.
        if self.pending_path.exists() and read(self.pending_path).get('status') in {'PREPARED', 'APPLYING'}:
            raise Error('Recover prior Codex operation first')
        return False


def prepare(source: Path, codex_home: Path, claude_home: Path, provider_home: Path, generation: str,
            legacy_lock: Path | None, release_dir: Path, release_id: str, runtime_catalog: Path,
            runtime_builder=codex.build_runtime) -> dict:
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', release_id):
        raise Error('Invalid release id')
    payload, owned, _ = preflight(source, codex_home, claude_home, provider_home, generation, legacy_lock, runtime_catalog)
    providers.plain_path(release_dir)
    release_dir.mkdir(parents=True, exist_ok=False)
    installer = CaptureInstaller(source, codex_home, runtime_builder)
    with installer.lock():
        result = installer.install(update=installer.manifest() is not None)
    desired_codex = installer.desired
    manifest_key = 'workflows/turn-up-time/install-manifest.json'
    manifest = json.loads(desired_codex[manifest_key])
    immutable_source = Path(result['generation']) / 'source'
    guard = ("import sys\nfrom pathlib import Path\nsys.path.insert(0, " + repr(str(immutable_source / 'scripts')) + ")\n"
             "from promote_workflow import admission_check\nadmission_check(Path(" + repr(str(claude_home)) + "), " + repr(release_id) + ")\n")
    desired_codex['workflows/turn-up-time/run.py'] = guard.encode() + desired_codex['workflows/turn-up-time/run.py']
    for row in manifest['files']:
        if row['relative'] == 'workflows/turn-up-time/run.py':
            row['sha256'] = codex.digest(desired_codex[row['relative']])
    manifest['shared_release_id'] = release_id
    manifest['shared_claude_home'] = str(claude_home)
    desired_codex[manifest_key] = pack(manifest)
    codex.atomic_write(Path(result['generation']) / 'candidate-manifest.json', pack(manifest))
    meta = providers.verify_generation(provider_home, generation)
    provider_root = providers.generation_path(provider_home, generation)
    # Retain immutable generations on both success and recovery; only selection
    # is active state. Never overwrite an existing generation.
    installed_generation = providers.generation_path(claude_home, generation)
    if installed_generation.exists():
        providers.verify_generation(claude_home, generation, hash_file(provider_root / 'generation.json'))
    else:
        installed_generation.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(provider_root, installed_generation)
        providers.verify_generation(claude_home, generation, hash_file(provider_root / 'generation.json'))
    selection = {'schema_version':1, 'generation_id':generation, 'manifest_sha256':hash_file(provider_root / 'generation.json'),
                 'previous_generation_id':None, 'previous_manifest_sha256':None}
    payload[providers.SELECTION] = pack(selection)
    catalog_raw = payload[CATALOG]
    catalog_sha = codex.digest(catalog_raw)
    catalog_archive = claude_home / 'runtime-catalogs' / (catalog_sha + '.json')
    providers.plain_path(catalog_archive)
    if catalog_archive.exists() and stream_hash(catalog_archive) != catalog_sha:
        raise Error('Immutable runtime catalog archive collision')
    if not catalog_archive.exists():
        codex.atomic_write(catalog_archive, catalog_raw)
    catalog = json.loads(catalog_raw)
    lock = read(provider_root / 'provider-lock.json')
    payload[providers.MANIFEST] = pack({'schema_version':2, 'state':'shared-release', 'release_id':release_id,
        'home':str(claude_home), 'lock_sha256':meta['lock_sha256'], 'files':providers.expected(lock),
        'recovery':str(release_dir / 'release.json')})
    payload['runtime/turn-up-time/runtime-manifest.json'] = pack({'schema_version':2, 'release_id':release_id,
        'venv_python':result['python'], 'source':str(immutable_source / 'runtime'), 'runtime_owner':'shared-codex-generation'})
    payload[CORE_MANIFEST] = pack({'schema_version':4, 'state':'shared-release', 'release_id':release_id,
        'files':{key:codex.digest(raw) for key, raw in payload.items()}, 'recovery':str(release_dir / 'release.json')})
    # Settings and the old runtime payload are deliberately never replaced.
    watched = {'settings.json':hash_file(claude_home / 'settings.json')}
    rows = []
    for side, home, desired in [('codex', codex_home, desired_codex), ('claude', claude_home, payload)]:
        for relative, raw in desired.items():
            destination = target(home, relative)
            if side == 'claude' and destination.exists() and relative not in owned:
                raise Error('Unmanaged target appeared: ' + str(destination))
            before = destination.read_bytes() if destination.exists() else None
            index = str(len(rows))
            for suffix, content in [('before', before), ('after', raw)]:
                if content is not None:
                    codex.atomic_write(release_dir / 'blobs' / (index + '.' + suffix), content)
            rows.append({'side':side, 'relative':relative, 'before_sha256':codex.digest(before) if before is not None else None,
                'after_sha256':codex.digest(raw) if raw is not None else None, 'blob':index})
    plan = {'schema_version':1, 'release_id':release_id, 'codex_home':str(codex_home), 'claude_home':str(claude_home),
        'generation_id':generation, 'registry_sha256':meta['registry_sha256'], 'lock_sha256':meta['lock_sha256'],
        'codex_generation':result['generation'], 'python':result['python'], 'source_inventory':manifest['source_inventory'],
        'runtime_inventory':manifest['runtime_inventory'], 'watched':watched, 'rows':rows}
    plan['runtime_catalog'] = {'runtime_id':catalog['runtime_id'], 'sha256':catalog_sha, 'archive':str(catalog_archive),
        'inventory':catalog['inventory'], 'interpreter_inventory':catalog['providers']['serena']['interpreter_inventory']}
    codex.atomic_write(release_dir / 'release.json', pack(plan))
    return summary(plan, release_dir)


def summary(plan: dict, directory: Path) -> dict:
    return {'release_id':plan['release_id'], 'plan':str(directory / 'release.json'), 'plan_sha256':hash_file(directory / 'release.json'),
        'objects':len(plan['rows']), 'changed':sum(row['before_sha256'] != row['after_sha256'] for row in plan['rows']),
        'created':sum(row['before_sha256'] is None for row in plan['rows']),
        'codex_objects':sum(row['side'] == 'codex' for row in plan['rows']), 'status':'PREPARED_NOT_ACTIVE'}


def load_plan(path: Path, expected_sha: str) -> dict:
    if hash_file(path) != expected_sha:
        raise Error('Promotion plan hash mismatch')
    plan = read(path)
    seen = set()
    for row in plan['rows']:
        if row['side'] not in {'claude', 'codex'} or not re.fullmatch(r'[0-9]+', row['blob']):
            raise Error('Invalid promotion row')
        key = (row['side'], row['relative'].casefold())
        if key in seen:
            raise Error('Duplicate promotion target')
        seen.add(key)
        target(Path(plan[row['side'] + '_home']), row['relative'])
        for phase in ('before', 'after'):
            sha = row[phase + '_sha256']
            if sha is not None and hash_file(path.parent / 'blobs' / (row['blob'] + '.' + phase)) != sha:
                raise Error('Promotion backup/payload hash mismatch')
    return plan


def check_quiescence(path: Path, plan_path: Path, plan: dict) -> None:
    value = read(path)
    now = datetime.now(timezone.utc)
    checked = datetime.fromisoformat(value['checked_at'].replace('Z', '+00:00'))
    expires = datetime.fromisoformat(value['expires_at'].replace('Z', '+00:00'))
    if not checked <= now < expires or (expires - checked).total_seconds() > 900:
        raise Error('Quiescence receipt expired or overlong')
    if (value.get('release_id') != plan['release_id'] or value.get('plan_sha256') != hash_file(plan_path)
            or value.get('codex_home') != plan['codex_home'] or value.get('claude_home') != plan['claude_home']
            or value.get('active_jobs') != [] or value.get('interactive_sessions_paused') is not True):
        raise Error('Quiescence scope or drained-job proof mismatch')
    lease_path = Path(value['pause_lease']['path'])
    lease = read(lease_path)
    if hash_file(lease_path) != value['pause_lease']['sha256'] or lease.get('admissions_paused') is not True or lease.get('release_id') != plan['release_id']:
        raise Error('Controller admission pause is not held')
    if not value.get('evidence'):
        raise Error('Actual controller quiescence evidence is required')
    for ref in value['evidence']:
        if hash_file(Path(ref['path'])) != ref['sha256']:
            raise Error('Quiescence evidence changed')


@contextmanager
def lock(home: Path):
    home.mkdir(parents=True, exist_ok=True)
    path = home / '.turn-up-time-promotion.lock'
    providers.plain_path(path)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        path.unlink(missing_ok=True)


def state(home: Path, plan_path: Path, plan: dict, status: str) -> None:
    binding = {relative:next(row['after_sha256'] for row in plan['rows'] if row['side'] == 'claude' and row['relative'] == relative)
        for relative in ('capabilities/registry.json', 'capabilities/provider-lock.json', providers.SELECTION, CATALOG)}
    codex.atomic_write(home / BARRIER, pack({'schema_version':1, 'state':status, 'release_id':plan['release_id'],
        'plan':str(plan_path), 'plan_sha256':hash_file(plan_path), 'binding':binding}))


def check_rows(plan: dict, phase: str) -> None:
    for row in plan['rows']:
        if hash_file(target(Path(plan[row['side'] + '_home']), row['relative'])) != row[phase + '_sha256']:
            raise Error('Promotion cohort drift: ' + row['side'] + '/' + row['relative'])
    for relative, sha in plan['watched'].items():
        if hash_file(target(Path(plan['claude_home']), relative)) != sha:
            raise Error('Preserved settings drift')


def apply(plan_path: Path, expected_sha: str, quiescence: Path, fail_after: int | None = None) -> dict:
    plan = load_plan(plan_path, expected_sha)
    home = Path(plan['claude_home'])
    with lock(home):
        if (home / BARRIER).exists():
            raise Error('Promotion already started; recover or verify')
        check_quiescence(quiescence, plan_path, plan)
        check_rows(plan, 'before')
        state(home, plan_path, plan, 'PREPARED')
        state(home, plan_path, plan, 'APPLYING')
        try:
            for index, row in enumerate(plan['rows'], 1):
                check_quiescence(quiescence, plan_path, plan)
                path = target(Path(plan[row['side'] + '_home']), row['relative'])
                if hash_file(path) != row['before_sha256']:
                    raise Error('Target changed during promotion')
                if row['after_sha256'] is None:
                    path.unlink(missing_ok=True)
                else:
                    codex.atomic_write(path, (plan_path.parent / 'blobs' / (row['blob'] + '.after')).read_bytes())
                if fail_after == index:
                    raise InterruptedError('Injected promotion interruption')
            verify_payload(plan)
            check_quiescence(quiescence, plan_path, plan)
            state(home, plan_path, plan, 'COMMITTED')
        except BaseException:
            state(home, plan_path, plan, 'RECOVERY_REQUIRED')
            raise
    return {'status':'COMMITTED', 'release_id':plan['release_id']}


def verify_payload(plan: dict) -> None:
    check_rows(plan, 'after')
    installer = codex.Installer(Path(plan['codex_generation']) / 'source', Path(plan['codex_home']))
    result = installer.verify()
    if result['status'] != 'VERIFIED':
        raise Error('Codex payload verification failed: ' + json.dumps(result))
    providers.verify_generation(Path(plan['claude_home']), plan['generation_id'])
    catalog_path = Path(plan['claude_home']) / CATALOG
    if hash_file(catalog_path) != plan['runtime_catalog']['sha256'] or stream_hash(Path(plan['runtime_catalog']['archive'])) != plan['runtime_catalog']['sha256']:
        raise Error('Runtime catalog selection/archive mismatch')
    verify_runtime_catalog(catalog_path, Path(plan['codex_generation']) / 'source', plan['generation_id'],
                           hash_file(providers.generation_path(Path(plan['claude_home']), plan['generation_id']) / 'generation.json'))


def recover(plan_path: Path, expected_sha: str, quiescence: Path) -> dict:
    plan = load_plan(plan_path, expected_sha)
    home = Path(plan['claude_home'])
    with lock(home):
        check_quiescence(quiescence, plan_path, plan)
        barrier = read(home / BARRIER)
        if barrier.get('plan_sha256') != expected_sha or barrier.get('release_id') != plan['release_id']:
            raise Error('Recovery release mismatch')
        # Check the ENTIRE recovery set before restoring a single file.
        for row in plan['rows']:
            if hash_file(target(Path(plan[row['side'] + '_home']), row['relative'])) not in {row['before_sha256'], row['after_sha256']}:
                state(home, plan_path, plan, 'RECOVERY_REQUIRED')
                raise Error('Modified promotion target; recovery preserves every file')
        state(home, plan_path, plan, 'RECOVERY_REQUIRED')
        for row in reversed(plan['rows']):
            check_quiescence(quiescence, plan_path, plan)
            path = target(Path(plan[row['side'] + '_home']), row['relative'])
            if row['before_sha256'] is None:
                path.unlink(missing_ok=True)
            else:
                codex.atomic_write(path, (plan_path.parent / 'blobs' / (row['blob'] + '.before')).read_bytes())
        check_rows(plan, 'before')
        (home / BARRIER).unlink()
    return {'status':'RESTORED_PRIOR_COHORT', 'release_id':plan['release_id'], 'generations_retained':True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'prepare', 'apply', 'recover', 'verify'])
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--codex-home', type=Path)
    parser.add_argument('--claude-home', type=Path)
    parser.add_argument('--provider-home', type=Path)
    parser.add_argument('--generation')
    parser.add_argument('--legacy-lock', type=Path)
    parser.add_argument('--runtime-catalog', type=Path, help='R-qualified immutable runtime catalog; no secrets')
    parser.add_argument('--release-dir', type=Path)
    parser.add_argument('--release-id')
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--plan-sha256')
    parser.add_argument('--quiescence', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command in {'plan', 'prepare'}:
            if not all((args.codex_home, args.claude_home, args.provider_home, args.generation)):
                raise Error('Explicit homes and provider generation required')
            values = [p.absolute() for p in (args.source, args.codex_home, args.claude_home, args.provider_home)]
            if args.command == 'plan':
                payload, owned, cp = preflight(*values, args.generation, args.legacy_lock, args.runtime_catalog)
                result = {'status':'PLAN', 'claude_payload_objects':len(payload), 'prior_owned':len(owned),
                    'codex_managed_targets':cp['managed_targets'], 'claude_targets':sorted(payload),
                    'changed_claude_payload':sum(hash_file(values[2] / name) != codex.digest(raw) for name, raw in payload.items())}
            else:
                if not args.release_dir or not args.release_id:
                    raise Error('Release directory and ID required')
                if not args.runtime_catalog:
                    raise Error('Runtime catalog is required')
                result = prepare(*values, args.generation, args.legacy_lock, args.release_dir.absolute(), args.release_id, args.runtime_catalog)
        else:
            if not args.plan or not args.plan_sha256:
                raise Error('Exact promotion plan and SHA256 required')
            if args.command == 'apply':
                if not args.quiescence:
                    raise Error('Actual checked quiescence receipt required')
                result = apply(args.plan, args.plan_sha256, args.quiescence)
            elif args.command == 'recover':
                if not args.quiescence:
                    raise Error('Held quiescence is required for rollback/recovery')
                result = recover(args.plan, args.plan_sha256, args.quiescence)
            else:
                plan = load_plan(args.plan, args.plan_sha256)
                admission_check(Path(plan['claude_home']), plan['release_id'])
                verify_payload(plan)
                result = {'status':'VERIFIED_COHORT', 'release_id':plan['release_id']}
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'status':'BLOCKED', 'error':str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
