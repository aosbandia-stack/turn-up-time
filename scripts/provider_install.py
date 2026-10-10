#!/usr/bin/env python3
"""Install the reviewed, pinned instruction providers without running upstream code."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import concurrent.futures
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / '.claude/capabilities/provider-lock.json'
MANIFEST = 'turn-up-time-provider-manifest.json'
MUTEX = '.turn-up-time-provider-operation.lock'
REGISTRY = ROOT / '.claude/capabilities/registry.json'
GENERATIONS = 'provider-generations'
SELECTION = 'provider-selection.json'


class InstallError(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_relative(value: str) -> Path:
    parts = PurePosixPath(value).parts
    if (not parts or value != '/'.join(parts) or any(p in {'.', '..'} for p in parts)
            or any(':' in p or '\\' in p or p.endswith((' ', '.')) for p in parts)
            or any(re.search(r'[<>"|?*\x00-\x1f]', p) or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', p, re.I) for p in parts)
            or PurePosixPath(value).is_absolute()):
        raise InstallError(f'Unsafe package path: {value!r}')
    return Path(*parts)


def plain_path(path: Path) -> None:
    """Reject symlinks and Windows junction/reparse points, including ancestors."""
    for part in [*reversed(path.parents), path]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise InstallError(f'Symlink/reparse point is not allowed: {part}')


def inventory(path: Path) -> dict[str, str]:
    plain_path(path)
    if not path.is_dir():
        raise InstallError(f'Missing provider directory: {path}')
    result = {}
    directories = set()
    for parent, dirs, files in os.walk(path, followlinks=False):
        for name in dirs + files:
            item = Path(parent) / name
            plain_path(item)
            if item.is_dir():
                directories.add(item.relative_to(path).as_posix())
                continue
            if not stat.S_ISREG(item.stat().st_mode):
                raise InstallError(f'Non-regular package file: {item}')
            result[item.relative_to(path).as_posix()] = digest(item.read_bytes())
    expected_directories = {str(parent) for name in result
                            for parent in PurePosixPath(name).parents if str(parent) != '.'}
    if directories != expected_directories:
        raise InstallError(f'Unexpected empty directories in provider; preserved: {path}')
    return result


def read_lock(path: Path | None = None) -> tuple[dict, str]:
    data = (path or LOCK).read_bytes()
    lock = json.loads(data)
    if lock.get('schema_version') != 1:
        raise InstallError('Unsupported provider lock version')
    seen = set()
    for package in lock['packages']:
        name = package['name']
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]+', name) or name in seen:
            raise InstallError(f'Invalid or repeated provider name: {name}')
        seen.add(name)
        repo = lock['repositories'][package['repository']]
        local = repo.get('kind') == 'local-snapshot'
        if local:
            if (set(repo) != {'kind', 'source', 'revision'} or repo['source'] != '.claude/skills'
                    or not re.fullmatch(r'sha256:[0-9a-f]{64}', repo['revision'])):
                raise InstallError('Invalid local instruction snapshot provenance')
        else:
            if not re.fullmatch(r'https://github.com/[\w-]+/[\w.-]+\.git', repo['url']):
                raise InstallError('Only reviewed HTTPS GitHub source repositories are supported')
            if not re.fullmatch(r'[0-9a-f]{40}', repo['commit']):
                raise InstallError('Source commit must be an immutable full SHA')
        folded = set()
        spellings = {}
        for dest, record in package['files'].items():
            safe_relative(dest)
            if local:
                if 'content' not in record:
                    raise InstallError('Local snapshots require exact embedded instruction bytes')
                safe_relative(record['source'])
                if not record['source'].startswith('.claude/skills/' + name + '/'):
                    raise InstallError('Local snapshot source does not match owned core skill')
            if dest.casefold() in folded:
                raise InstallError(f'Case-colliding package path: {dest}')
            folded.add(dest.casefold())
            for path in [PurePosixPath(dest), *PurePosixPath(dest).parents]:
                spelling = path.as_posix()
                if spellings.setdefault(spelling.casefold(), spelling) != spelling:
                    raise InstallError(f'Case-colliding package directory: {dest}')
            if not re.fullmatch(r'[0-9a-f]{64}', record['sha256']):
                raise InstallError(f'Invalid package hash: {dest}')
            if 'content' in record:
                if digest(record['content'].encode()) != record['sha256']:
                    raise InstallError(f'Adapter hash mismatch: {name}/{dest}')
            else:
                safe_relative(record['source'])
        if 'SKILL.md' not in package['files']:
            raise InstallError(f'Missing provider entrypoint: {name}')
        for dest in package['files']:
            if any(parent.as_posix().casefold() in folded for parent in PurePosixPath(dest).parents if str(parent) != '.'):
                raise InstallError(f'File/directory package collision: {dest}')
    for package in lock['packages']:
        if not set(package.get('requires', [])) <= seen:
            raise InstallError(f'Missing provider dependency: {package["name"]}')
    for name, repo in lock['repositories'].items():
        if repo.get('kind') == 'local-snapshot':
            snapshot = {record['source']: record['sha256'] for package in lock['packages']
                        if package['repository'] == name for record in package['files'].values()}
            revision = 'sha256:' + digest(json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode())
            if repo['revision'] != revision:
                raise InstallError('Local snapshot revision does not match locked instruction content')
    return lock, digest(data)


def repository_source_ref(repo: dict) -> str:
    if repo.get('kind') == 'local-snapshot':
        return 'local-snapshot:' + repo['source'] + '@' + repo['revision']
    return repo['url'] + '@' + repo['commit']


def expected(lock: dict) -> dict:
    return {p['name']: {name: value['sha256'] for name, value in p['files'].items()}
            for p in lock['packages']}


def read_manifest(home: Path, lock_hash: str, files: dict) -> dict | None:
    path = home / MANIFEST
    plain_path(path)
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding='utf-8'))
    if (value.get('schema_version') != 1 or value.get('home') != str(home)
            or value.get('lock_sha256') != lock_hash or value.get('files') != files
            or value.get('state') not in {'installing', 'installed', 'removing'}):
        raise InstallError('Unrecognized/changed ownership manifest. Preserve it and use the original installer/lock to recover.')
    return value


def write_manifest(home: Path, value: dict) -> None:
    path = home / MANIFEST
    plain_path(path)
    temporary = home / (MANIFEST + '.tmp')
    plain_path(temporary)
    # Exclusive create avoids overwriting an unrelated or crash-retained file.
    with temporary.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def verify(home: Path, files: dict, manifest: dict | None) -> None:
    if not manifest or manifest['state'] != 'installed':
        raise InstallError('No complete installation. An interrupted apply must be removed safely before retrying.')
    for name, hashes in files.items():
        path = home / 'skills' / name
        if inventory(path) != hashes:
            raise InstallError(f'MODIFIED or incomplete provider: {path}; preserved')


def git(path: Path, *args: str) -> bytes:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0')
    command = ['git', '-c', 'core.hooksPath=' + os.devnull, '-c', 'credential.helper=',
               '-c', 'protocol.file.allow=never', '-c', 'protocol.ext.allow=never',
               '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false',
               '-C', str(path), *args]
    try:
        return subprocess.run(command, env=env, check=True, capture_output=True, timeout=180).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        raise InstallError(f'Git source operation failed ({args[0]}) at {path}: {exc}') from exc


def sources(lock: dict, supplied: dict[str, Path], scratch: Path) -> dict[str, Path]:
    result = {}
    unknown = set(supplied) - set(lock['repositories'])
    if unknown:
        raise InstallError('Unknown source names: ' + ', '.join(sorted(unknown)))
    for name, repo in lock['repositories'].items():
        if repo.get('kind') == 'local-snapshot':
            if name in supplied:
                raise InstallError('Local embedded snapshots do not accept source checkout overrides')
            continue
        if name in supplied:
            path = supplied[name]
            plain_path(path)
            if git(path, 'rev-parse', 'HEAD').decode().strip() != repo['commit']:
                raise InstallError(f'Wrong source pin: {name} at {path}')
            if any(row.startswith(b'filter.') for row in git(path, 'config', '--list', '--null').split(b'\0')):
                raise InstallError(f'Local checkout has configured content filters; use a fresh source checkout: {path}')
            if git(path, 'status', '--porcelain', '--untracked-files=all').strip():
                raise InstallError(f'Dirty source checkout: {path}')
        else:
            path = scratch / name
            path.mkdir()
            git(path, 'init', '--bare', '--template=')
            git(path, 'fetch', '--depth=1', '--no-tags', repo['url'], repo['commit'])
            if git(path, 'rev-parse', 'FETCH_HEAD').decode().strip() != repo['commit']:
                raise InstallError(f'Fetched source pin mismatch: {name}')
        result[name] = path
    return result


def materialize(lock: dict, source_roots: dict, staged: Path) -> None:
    # Read Git blobs, never checkout/smudge filters or upstream install scripts.
    for package in lock['packages']:
        repo = lock['repositories'][package['repository']]
        source = source_roots.get(package['repository'])
        tree = {}
        rows = git(source, 'ls-tree', '-rz', repo['commit']).split(b'\0') if source else []
        for row in rows:
            if row:
                meta, name = row.split(b'\t', 1)
                mode, kind, oid = meta.decode().split()
                tree[name.decode()] = (mode, kind, oid)
        for dest, record in package['files'].items():
            if 'content' in record:
                data = record['content'].encode()
            else:
                entry = tree.get(record['source'])
                if not entry or entry[0] not in {'100644', '100755'} or entry[1] != 'blob':
                    raise InstallError(f'Missing or unsafe upstream asset: {record["source"]}')
                data = git(source, 'cat-file', 'blob', entry[2])
            if digest(data) != record['sha256']:
                raise InstallError(f'Upstream asset hash mismatch: {package["name"]}/{dest}')
            output = staged / package['name'] / safe_relative(dest)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)


def install(home: Path, lock: dict, lock_hash: str, files: dict, manifest: dict | None,
            supplied: dict, apply: bool) -> None:
    if manifest:
        verify(home, files, manifest)
        print('UNCHANGED: all pinned instruction providers already installed and verified.')
        return
    for name in files:
        target = home / 'skills' / name
        plain_path(target)
        if target.exists():
            raise InstallError(f'CONFLICT: unmanaged provider preserved: {target}')
    if not apply:
        print(f'DRY RUN: install {len(files)} instruction entrypoints into {home / "skills"}. No downloads or writes.')
        for repo in lock['repositories'].values():
            print('  ' + repository_source_ref(repo))
        print('Use --apply to fetch pinned sources and install. No hooks, launchers, MCP, or audit readiness are enabled.')
        return
    # Assemble and hash-check everything before exposing any provider entrypoint.
    with tempfile.TemporaryDirectory(prefix='tut-provider-sources-') as scratch:
        with tempfile.TemporaryDirectory(prefix='.tut-provider-stage-', dir=home) as stage:
            staged = Path(stage)
            materialize(lock, sources(lock, supplied, Path(scratch)), staged)
            for name, hashes in files.items():
                if inventory(staged / name) != hashes:
                    raise InstallError(f'Staging verification failed: {name}')
            manifest = {'schema_version': 1, 'home': str(home), 'lock_sha256': lock_hash,
                        'state': 'installing', 'files': files}
            write_manifest(home, manifest)
            (home / 'skills').mkdir(exist_ok=True)
            for name in files:
                target = home / 'skills' / name
                plain_path(target)
                if target.exists():
                    raise InstallError(f'CONFLICT during installation; preserved: {target}')
                (staged / name).rename(target)
            manifest['state'] = 'installed'
            write_manifest(home, manifest)
    verify(home, files, manifest)
    print(f'INSTALLED AND VERIFIED: {len(files)} instruction entrypoints in {home}.')
    print('Impeccable launcher disabled. External security audit readiness/use and Bandia wiring remain unproven.')


def remove(home: Path, files: dict, manifest: dict | None, apply: bool) -> None:
    if not manifest:
        raise InstallError('No owned provider manifest; nothing will be removed.')
    conflicts = []
    for name, hashes in files.items():
        target = home / 'skills' / name
        plain_path(target)
        if target.exists() and inventory(target) != hashes:
            conflicts.append(str(target))
    if conflicts:
        raise InstallError('MODIFIED providers preserved; no providers removed:\n' + '\n'.join(conflicts))
    if not apply:
        print(f'DRY RUN: remove only the {len(files)} hash-matching owned provider directories. Unrelated files stay.')
        return
    manifest['state'] = 'removing'
    write_manifest(home, manifest)
    for name in files:
        target = home / 'skills' / name
        plain_path(target)
        if target.exists():
            if inventory(target) != files[name]:
                raise InstallError(f'Provider changed during removal; preserved: {target}')
            shutil.rmtree(target)
    (home / MANIFEST).unlink()
    print('REMOVED: owned provider directories and ownership manifest. Unrelated files preserved.')


def generation_path(home: Path, generation_id: str) -> Path:
    if not isinstance(generation_id, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', generation_id):
        raise InstallError('Invalid generation ID')
    path = home / GENERATIONS / generation_id
    plain_path(path)
    return path


def verify_generation(home: Path, generation_id: str, manifest_sha256: str | None = None) -> dict:
    """Read-only full-generation verification; does not assert external readiness."""
    root = generation_path(home, generation_id)
    plain_path(root / 'generation.json')
    raw = (root / 'generation.json').read_bytes()
    if manifest_sha256 is not None and digest(raw) != manifest_sha256:
        raise InstallError('Generation manifest changed; selection preserved')
    meta = json.loads(raw)
    if (set(meta) != {'schema_version', 'generation_id', 'lock_sha256', 'registry_sha256', 'files'}
            or meta['schema_version'] != 1 or meta['generation_id'] != generation_id):
        raise InstallError('Invalid generation manifest')
    plain_path(root / 'provider-lock.json')
    plain_path(root / 'registry.json')
    lock, lock_hash = read_lock(root / 'provider-lock.json')
    registry_hash = digest((root / 'registry.json').read_bytes())
    hashes = {'provider-lock.json': lock_hash, 'registry.json': registry_hash}
    for package in lock['packages']:
        hashes.update({f'skills/{package["name"]}/{name}': record['sha256']
                       for name, record in package['files'].items()})
    if (meta['files'] != hashes or meta['lock_sha256'] != lock_hash
            or meta['registry_sha256'] != registry_hash):
        raise InstallError('Generation lock/registry ownership mismatch')
    actual = inventory(root)
    actual.pop('generation.json', None)
    if actual != hashes:
        raise InstallError('MODIFIED or incomplete generation; preserved')
    return meta


def fetch_blob(repo: dict, record: dict) -> bytes:
    """Fetch only a reviewed immutable Git blob; never unpack or execute sources."""
    repository = repo['url'].removeprefix('https://github.com/').removesuffix('.git')
    url = f'https://raw.githubusercontent.com/{repository}/{repo["commit"]}/{record["source"]}'
    request = urllib.request.Request(url, headers={'User-Agent': 'Turn-Up-Time-pinned-provider'})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            if response.url != url:
                raise InstallError('Unexpected upstream blob redirect')
            data = response.read(10 * 1024 * 1024 + 1)
    except OSError as exc:
        raise InstallError(f'Pinned blob unavailable: {url}: {exc}') from exc
    if len(data) > 10 * 1024 * 1024 or digest(data) != record['sha256']:
        raise InstallError(f'Pinned blob size/hash mismatch: {url}')
    return data


def materialize_blobs(lock: dict, staged: Path) -> None:
    jobs = [(p, dest, record) for p in lock['packages'] for dest, record in p['files'].items()]
    def load(job):
        package, dest, record = job
        data = record['content'].encode('utf-8') if 'content' in record else fetch_blob(lock['repositories'][package['repository']], record)
        if digest(data) != record['sha256']:
            raise InstallError('Adapter content hash mismatch')
        return package['name'], dest, data
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for name, dest, data in pool.map(load, jobs):
            output = staged / name / safe_relative(dest)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)


def stage_generation(home: Path, generation_id: str, supplied: dict, apply: bool) -> dict | None:
    target = generation_path(home, generation_id)
    lock, lock_hash = read_lock()
    if target.exists():
        meta = verify_generation(home, generation_id)
        if meta['lock_sha256'] != lock_hash or meta['registry_sha256'] != digest(REGISTRY.read_bytes()):
            raise InstallError('Generation ID already belongs to different source; use a new ID')
        return meta
    if not apply:
        print(f'DRY RUN: stage {len(lock["packages"])} packages at {target}; selection unchanged')
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    # Incomplete assembly stays outside the generations namespace until fully verified.
    with tempfile.TemporaryDirectory(prefix='.provider-stage-', dir=home) as temporary:
        stage = Path(temporary)
        (stage / 'skills').mkdir()
        if supplied:
            with tempfile.TemporaryDirectory(prefix='tut-provider-sources-') as scratch:
                materialize(lock, sources(lock, supplied, Path(scratch)), stage / 'skills')
        else:
            materialize_blobs(lock, stage / 'skills')
        for name, hashes in expected(lock).items():
            if inventory(stage / 'skills' / name) != hashes:
                raise InstallError(f'Incomplete package: {name}')
        (stage / 'provider-lock.json').write_bytes(LOCK.read_bytes())
        (stage / 'registry.json').write_bytes(REGISTRY.read_bytes())
        meta = {'schema_version': 1, 'generation_id': generation_id, 'lock_sha256': lock_hash,
                'registry_sha256': digest(REGISTRY.read_bytes()), 'files': inventory(stage)}
        with (stage / 'generation.json').open('x', encoding='utf-8', newline='\n') as handle:
            json.dump(meta, handle, sort_keys=True, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists():
            raise InstallError('Generation appeared during stage; preserved')
        stage.rename(target)
    return verify_generation(home, generation_id)


def read_selection(home: Path) -> dict | None:
    path = home / SELECTION
    plain_path(path)
    if not path.exists():
        return None
    value = json.loads(path.read_bytes())
    if (set(value) != {'schema_version', 'generation_id', 'manifest_sha256', 'previous_generation_id', 'previous_manifest_sha256'}
            or value['schema_version'] != 1):
        raise InstallError('Unrecognized selection; preserved')
    if value['generation_id'] is None:
        if value['manifest_sha256'] is not None:
            raise InstallError('Invalid deselected generation')
    else:
        if not isinstance(value['manifest_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', value['manifest_sha256']):
            raise InstallError('Invalid selected manifest hash')
        verify_generation(home, value['generation_id'], value['manifest_sha256'])
    previous = value['previous_generation_id']
    if (previous is None) != (value['previous_manifest_sha256'] is None):
        raise InstallError('Invalid previous selection')
    if previous is not None:
        generation_path(home, previous)
        if not re.fullmatch(r'[0-9a-f]{64}', value['previous_manifest_sha256']):
            raise InstallError('Invalid previous manifest hash')
    return value


def select_generation(home: Path, generation_id: str | None, apply: bool, rollback: bool = False) -> dict:
    previous = read_selection(home)
    if rollback:
        if previous is None:
            raise InstallError('No managed selection to roll back; legacy home is preserved')
        generation_id = previous['previous_generation_id']
        if generation_id is not None:
            verify_generation(home, generation_id, previous['previous_manifest_sha256'])
    if generation_id is None and not rollback:
        raise InstallError('--generation is required')
    if generation_id is not None:
        verify_generation(home, generation_id)
    manifest_hash = digest((generation_path(home, generation_id) / 'generation.json').read_bytes()) if generation_id else None
    if previous and previous['generation_id'] == generation_id:
        return previous
    value = {'schema_version': 1, 'generation_id': generation_id, 'manifest_sha256': manifest_hash,
             'previous_generation_id': previous['generation_id'] if previous else None,
             'previous_manifest_sha256': previous['manifest_sha256'] if previous else None}
    if apply:
        temporary = home / (SELECTION + '.tmp')
        plain_path(temporary)
        # Retained crash files block replacement instead of silently overwriting state.
        with temporary.open('x', encoding='utf-8', newline='\n') as handle:
            json.dump(value, handle, sort_keys=True)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, home / SELECTION)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install', 'verify', 'remove', 'stage', 'verify-generation', 'select', 'rollback'])
    parser.add_argument('--generation', help='Immutable managed generation ID')
    parser.add_argument('--home', type=Path, required=True, help='Explicit target Claude home, e.g. ~/.claude')
    parser.add_argument('--apply', action='store_true', help='Allow install/remove writes; default is dry run')
    parser.add_argument('--source', action='append', default=[], metavar='NAME=CHECKOUT',
                        help='Use a clean exact-pin local checkout instead of downloading that repository')
    args = parser.parse_args(argv)
    mutex = None
    try:
        home = Path(os.path.abspath(args.home.expanduser()))
        plain_path(home)
        plain_path(home / 'skills')
        lock, lock_hash = read_lock()
        files = expected(lock)
        supplied = {}
        for value in args.source:
            name, separator, path = value.partition('=')
            if not separator or name in supplied:
                raise InstallError('--source requires unique NAME=CHECKOUT arguments')
            supplied[name] = Path(os.path.abspath(Path(path).expanduser()))
        if args.apply and args.command != 'verify':
            home.mkdir(parents=True, exist_ok=True)
            lock_path = home / MUTEX
            plain_path(lock_path)
            try:
                fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                raise InstallError('Provider operation lock exists. Check no installer is running before removing that stale lock and recovering.')
            mutex = lock_path
            with os.fdopen(fd, 'w') as handle:
                handle.write(str(os.getpid()))
        if args.command in {'stage', 'verify-generation', 'select', 'rollback'}:
            if args.command == 'stage':
                if not args.generation:
                    raise InstallError('--generation is required')
                result = stage_generation(home, args.generation, supplied, args.apply)
            elif args.command == 'verify-generation':
                result = verify_generation(home, args.generation)
            else:
                result = select_generation(home, args.generation, args.apply, args.command == 'rollback')
            print(json.dumps({'command': args.command, 'generation_id': (result or {}).get('generation_id'),
                              'applied': args.apply, 'external_readiness': 'UNPROVEN'}))
            return 0
        manifest = read_manifest(home, lock_hash, files)
        if args.command == 'verify':
            verify(home, files, manifest)
            print(f'VERIFIED: all {len(files)} instruction entrypoints and every locked asset match. This is not external-tool readiness or actual use.')
        elif args.command == 'install':
            install(home, lock, lock_hash, files, manifest, supplied, args.apply)
        else:
            remove(home, files, manifest, args.apply)
        return 0
    except (InstallError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f'BLOCKED: {exc}', file=sys.stderr)
        return 1
    finally:
        if mutex is not None:
            mutex.unlink(missing_ok=True)


if __name__ == '__main__':
    if sys.version_info < (3, 11):
        raise SystemExit('Python 3.11 or newer is required.')
    raise SystemExit(main())
