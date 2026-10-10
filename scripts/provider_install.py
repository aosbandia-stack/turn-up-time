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

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / '.claude/capabilities/provider-lock.json'
MANIFEST = 'turn-up-time-provider-manifest.json'
MUTEX = '.turn-up-time-provider-operation.lock'


class InstallError(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_relative(value: str) -> Path:
    parts = PurePosixPath(value).parts
    if (not parts or value != '/'.join(parts) or any(p in {'.', '..'} for p in parts)
            or any(':' in p or '\\' in p or p.endswith((' ', '.')) for p in parts)
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


def read_lock() -> tuple[dict, str]:
    data = LOCK.read_bytes()
    lock = json.loads(data)
    if lock.get('schema_version') != 1:
        raise InstallError('Unsupported provider lock version')
    seen = set()
    for package in lock['packages']:
        name = package['name']
        if not re.fullmatch(r'[a-z][a-z0-9-]+', name) or name in seen:
            raise InstallError(f'Invalid or repeated provider name: {name}')
        seen.add(name)
        repo = lock['repositories'][package['repository']]
        if not re.fullmatch(r'https://github.com/[\w-]+/[\w.-]+\.git', repo['url']):
            raise InstallError('Only reviewed HTTPS GitHub source repositories are supported')
        if not re.fullmatch(r'[0-9a-f]{40}', repo['commit']):
            raise InstallError('Source commit must be an immutable full SHA')
        folded = set()
        for dest, record in package['files'].items():
            safe_relative(dest)
            if dest.casefold() in folded:
                raise InstallError(f'Case-colliding package path: {dest}')
            folded.add(dest.casefold())
            if not re.fullmatch(r'[0-9a-f]{64}', record['sha256']):
                raise InstallError(f'Invalid package hash: {dest}')
            if 'content' in record:
                if digest(record['content'].encode()) != record['sha256']:
                    raise InstallError(f'Adapter hash mismatch: {name}/{dest}')
            else:
                safe_relative(record['source'])
        if 'SKILL.md' not in package['files']:
            raise InstallError(f'Missing provider entrypoint: {name}')
    for package in lock['packages']:
        if not set(package.get('requires', [])) <= seen:
            raise InstallError(f'Missing provider dependency: {package["name"]}')
    return lock, digest(data)


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
        source = source_roots[package['repository']]
        tree = {}
        for row in git(source, 'ls-tree', '-rz', repo['commit']).split(b'\0'):
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
            print(f'  {repo["url"]} @ {repo["commit"]}')
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install', 'verify', 'remove'])
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
