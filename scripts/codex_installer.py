#!/usr/bin/env python3
"""Reversible, generation-based Codex adapter. Mutations require --apply."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import uuid
from datetime import datetime, timezone
from typing import Callable

BEGIN = '<!-- BEGIN TURN-UP-TIME CODEX DEFAULT -->'
END = '<!-- END TURN-UP-TIME CODEX DEFAULT -->'
FORMAT = 2
IGNORED_DIRS = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'node_modules', 'build', 'dist', '.eggs'}
STATE_DIRS = {'projects', 'runtime', 'audit-runs', 'review-output'}


class InstallError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str | None:
    return digest(path.read_bytes()) if path.is_file() else None


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.tut-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def interpreter(venv: Path, platform: str | None = None) -> Path:
    return venv / ('Scripts/python.exe' if (platform or os.name) == 'nt' else 'bin/python')


def inventory(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): file_hash(p)
        for p in sorted(root.rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'
        and '.pytest_cache' not in p.parts
    }


def redirected(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        # Windows junctions need this on Python versions predating Path.is_junction.
        return bool(getattr(path.lstat(), 'st_file_attributes', 0) & 0x400)
    except FileNotFoundError:
        return False


def snapshot(source: Path, target: Path) -> None:
    """Copy workflow payload only; never copy project state or local evidence."""
    def copy_file(path: Path) -> None:
        if redirected(path) or not path.resolve().is_relative_to(source.resolve()):
            raise InstallError(f'Source redirection is unsupported: {path}')
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

    roots = [source / '.claude', source / 'runtime', source / 'docs', source / 'scripts']
    for root in roots:
        if redirected(root) or not root.resolve().is_relative_to(source.resolve()):
            raise InstallError(f'Source root redirection is unsupported: {root}')
    for root in roots:
        for directory, names, files in os.walk(root, followlinks=False):
            current = Path(directory)
            names[:] = [n for n in names if n not in IGNORED_DIRS
                        and not n.endswith('.egg-info')
                        and not (current == source / '.claude' and n in STATE_DIRS)
                        and not (root.name == 'docs' and (n in {'evidence', 'artifacts'} or n.startswith('audit-')))]
            for name in names:
                if redirected(current / name):
                    raise InstallError(f'Source redirection is unsupported: {current / name}')
            for name in files:
                path = current / name
                if path.suffix in {'.pyc', '.log', '.tmp', '.sqlite', '.sqlite-shm', '.sqlite-wal'} or '.bak' in name:
                    continue
                copy_file(path)
    for name in ('CLAUDE.md', 'AGENTS.md', 'README.md', 'MANIFEST.md', 'THIRD_PARTY_NOTICES.md', 'LICENSE', 'requirements-dev.txt'):
        path = source / name
        if path.is_file():
            copy_file(path)


def run(command: list[str | Path], **kwargs) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PIP_DISABLE_PIP_VERSION_CHECK='1')
    return subprocess.run([str(part) for part in command], check=True, capture_output=True, text=True, env=env, **kwargs)


def build_runtime(source: Path, venv: Path) -> Path:
    run([sys.executable, '-m', 'venv', venv])
    python = interpreter(venv)
    run([python, '-m', 'pip', 'install', '--no-compile', str(source / 'runtime'), 'PyYAML>=6,<7'])
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TURN_UP_TIME_CLAUDE_HOME=str(source / '.claude'))
    subprocess.run([str(python), '-m', 'turn_up_time_graph.cli', 'validate-topology'],
                   check=True, capture_output=True, text=True, env=env, cwd=source)
    run([python, source / '.claude/scripts/validate_repo.py'], cwd=source)
    return python


def metadata(source: Path, python: Path) -> dict:
    # Use the candidate runtime's YAML parser; plan needs no optional dependencies.
    program = '''import json, pathlib, re, sys, yaml
root = pathlib.Path(sys.argv[1])
result = {'skills': {}, 'agents': {}}
for category, paths in [('skills', (root/'.claude/skills').glob('*/SKILL.md')), ('agents', (root/'.claude/agents').glob('*.md'))]:
    for path in sorted(paths):
        text = path.read_text(encoding='utf-8')
        match = re.match(r'^---\\n(.*?)\\n---\\n(.*)', text, re.S)
        if not match: raise ValueError('Missing frontmatter: '+str(path))
        info = yaml.safe_load(match[1])
        info['body'] = match[2]
        info['relative_path'] = path.relative_to(root).as_posix()
        result[category][info['name']] = info
print(json.dumps(result))
'''
    result = json.loads(run([python, '-c', program, source]).stdout)
    if 'turn-up-time' not in result['skills'] or 'implementation-engineer' not in result['agents']:
        raise InstallError('Source lacks the canonical root skill or production role')
    for category in result.values():
        for name, info in category.items():
            if not re.fullmatch(r'[a-z][a-z0-9-]*', name) or not isinstance(info.get('description'), str):
                raise InstallError(f'Invalid source metadata: {name}')
    return result


def owned_block(content: bytes) -> bytes | None:
    start, end = BEGIN.encode(), END.encode()
    if content.count(start) != content.count(end) or content.count(start) > 1:
        raise InstallError('Global AGENTS.md has malformed or duplicate ownership markers')
    if start not in content:
        return None
    first, last = content.index(start), content.index(end)
    if last < first:
        raise InstallError('Global AGENTS.md ownership markers are reversed')
    return content[first:last + len(end)]


def merge_block(content: bytes, expected: bytes | None, replacement: bytes | None) -> bytes:
    present = owned_block(content)
    if present != expected:
        raise InstallError('The owned Turn Up Time AGENTS.md block was modified; preserving all dependencies')
    if present is not None:
        return content.replace(present, replacement or b'', 1)
    if replacement is None:
        return content
    separator = b'\n' if content.endswith(b'\n') else b'\n\n'
    return content + (separator if content else b'') + replacement + b'\n'


def generated_files(home: Path, generation: Path, python: Path, meta: dict) -> tuple[dict[str, bytes], bytes]:
    base = home / 'workflows/turn-up-time'
    source = generation / 'source'
    result: dict[str, bytes] = {}
    role_map = {name: 'tut_' + name.replace('-', '_') for name in meta['agents']}
    skill_map = {name: name if name == 'turn-up-time' else 'tut-' + name for name in meta['skills']}
    for name, info in meta['agents'].items():
        installed = role_map[name]
        instruction = (f'You are the Turn Up Time {name} role. Read {base.as_posix()}/CODEX.md. '
                       'The parent owns the ledger and persists your returned artifacts. Do not restart the root workflow. '
                       "You are not alone in the workspace; preserve other agents' changes. "
                       'Use available Codex tools; source Claude tool names describe capabilities.\n'
                       f'Resolve relative links below from {(source / info["relative_path"]).parent.as_posix()}/.\n\n' + info['body'])
        fields = {'name': installed, 'description': info['description'], 'developer_instructions': instruction}
        if info.get('role_class') != 'production':
            fields['sandbox_mode'] = 'read-only'
        text = ''.join(f'{key} = {json.dumps(value, ensure_ascii=False)}\n' for key, value in fields.items())
        tomllib.loads(text)
        result[f'agents/{installed}.toml'] = text.encode()
    for name, info in meta['skills'].items():
        installed = skill_map[name]
        text = (f'---\nname: {installed}\ndescription: {json.dumps("Turn Up Time: " + info["description"])}\n---\n\n'
                f'Read [{name} procedure]({(source / info["relative_path"]).as_posix()}) and '
                f'[Codex compatibility contract]({base.as_posix()}/CODEX.md), then use the Codex mappings.\n'
                'Tier A/B use the smallest process; Tier B may execute directly without discovery agents.\n'
                'Installed source is reference material. Project writes/state belong in the active product repository.\n')
        result[f'skills/{installed}/SKILL.md'] = text.encode()
    runner = f'''import os, runpy, sys
from pathlib import Path
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
source = Path({str(source)!r})
os.environ['TURN_UP_TIME_CLAUDE_HOME'] = str(source / '.claude')
if len(sys.argv) < 2:
    raise SystemExit('Usage: run.py <graph|script-name> [arguments]')
command, *args = sys.argv[1:]
if command == 'graph':
    sys.argv = ['turn-up-time-graph', *args]
    runpy.run_module('turn_up_time_graph.cli', run_name='__main__')
else:
    scripts = {{p.stem: p for p in (source / '.claude/scripts').glob('*.py')}}
    if command not in scripts:
        raise SystemExit('Unknown workflow command: ' + command)
    if command == 'resolve_capabilities':
        args += ['--provider-root', str(source / '.claude/skills'), '--provider-root', str(Path.home() / '.agents/skills'), '--provider-root', {str(home / 'skills')!r}]
    sys.path.insert(0, str(source / '.claude/scripts'))
    sys.argv = [str(scripts[command]), *args]
    runpy.run_path(str(scripts[command]), run_name='__main__')
'''
    result['workflows/turn-up-time/run.py'] = runner.encode()
    contract = f'''# Turn Up Time for Codex

Canonical authority: `{source.as_posix()}/CLAUDE.md`.
Use `$turn-up-time` as the software default. Tier A answers, Tier B bounded changes, Tier C graph-backed work.
Source control-role delegation constraints apply to Tier C. Preserve user authorization and higher-priority instructions.
Routing and consequential-action guards are instruction-based in Codex; sandbox and tool approvals remain authoritative.

## Roles and skills

Use the following names within this workflow instead of overlapping legacy Harold/OmniDex defaults.
Queue independent roles within available concurrency; never silently substitute a writable role for an enforced read-only role.
Configuration validity does not prove role discovery or effective sandbox permissions. Check the current tool inventory.
If required role enforcement is unavailable, report that limitation. Do not claim full assurance from a configuration check.
Only root operates project-ledger transitions; roles return artifacts for root to persist.

''' + '\n'.join(f'- `/{name}` → `${installed}`' for name, installed in skill_map.items()) + '\n\n' + '\n'.join(f'- `{name}` → `{installed}`' for name, installed in role_map.items()) + f'''

## Execution and recovery

Run helpers from the product repository with interpreter `{python}` and dispatcher `{base / 'run.py'}`.
For example, pass `graph validate-topology`, `scaffold_project <id> --profile lite --objective ...`,
`validate_project <project-dir> --stage <target>`, or `resolve_capabilities <capability>`.
Canonical scripts/schemas/profiles/templates/registry resolve under `{source.as_posix()}`.
Project `.claude/projects` and `.claude/runtime` remain relative to the actual product repository.
Do not run the Claude installer or create product state in the installed snapshot.
Use graph transitions and explicit recovery commands documented in `{source.as_posix()}/docs/GRAPH-RUNTIME.md`.
Never manually advance a Tier C ledger or delete checkpoints to bypass rejection.
The dispatcher selects the installed validator. Missing providers block; use `$tut-plug-it-in` for approved intake.
Use `--project-registry` for project overrides.

The source-owned installer is `{source.as_posix()}/scripts/codex_installer.py`.
Run `verify --codex-home <home>` for integrity diagnostics; `rollback --codex-home <home> --apply`
restores the prior installation after ownership and backup checks. Modified owned files block rollback as a unit.
Generations and runtime environments are retained for recovery. See `{source.as_posix()}/docs/CODEX.md`.
'''
    result['workflows/turn-up-time/CODEX.md'] = contract.encode()
    block = f'''{BEGIN}
# Default software workflow: Turn Up Time

For software design, builds, implementation, automation, refactors and fixes, load
`{home.as_posix()}/skills/turn-up-time/SKILL.md` and follow `{base.as_posix()}/CODEX.md`.
Use Tier A for answers, Tier B for bounded edits, and Tier C for substantial capabilities.
Turn Up Time replaces overlapping default Harold routers/spec/done loops for ordinary software work.
Use its `tut-*` skills and `tut_*` agents; check actual role availability and effective permissions.
Preserve repository build/test constraints, higher-priority instructions, and explicit user choices.
Do not route unrelated conversation or document work into software workflow machinery.
{END}'''.encode()
    return result, block


class Installer:
    def __init__(self, source: Path, home: Path, runtime_builder: Callable = build_runtime):
        self.source = source.resolve()
        self.home = home.resolve()
        self.base = self.home / 'workflows/turn-up-time'
        self.manifest_path = self.base / 'install-manifest.json'
        self.pending_path = self.base / 'pending-operation.json'
        self.runtime_builder = runtime_builder
        self.internal(self.base)

    def internal(self, path: Path) -> Path:
        path = path.absolute()
        if not path.is_relative_to(self.home) or not path.resolve().is_relative_to(self.home):
            raise InstallError(f'Internal path escapes Codex home: {path}')
        for part in [path, *path.parents]:
            if part == self.home:
                break
            if redirected(part):
                raise InstallError(f'Internal directory redirection is unsupported: {part}')
        return path

    def target(self, relative: str) -> Path:
        allowed = (relative == 'AGENTS.md' or
                   re.fullmatch(r'agents/tut_[a-z0-9_]+\.toml', relative) or
                   re.fullmatch(r'skills/(turn-up-time|tut-[a-z0-9-]+)/SKILL\.md', relative) or
                   relative in {'workflows/turn-up-time/run.py', 'workflows/turn-up-time/CODEX.md',
                                'workflows/turn-up-time/install-manifest.json'})
        if not allowed:
            raise InstallError(f'Unsafe managed path: {relative}')
        path = self.internal(self.home / relative)
        if Path(relative).is_absolute() or not path.resolve().is_relative_to(self.home):
            raise InstallError(f'Unsafe managed path: {relative}')
        if path.exists() and not path.is_file():
            raise InstallError(f'Managed path is not a regular file: {relative}')
        # A symlink may point inside the root but still aliases another owned file.
        if any(p.is_symlink() for p in [path, *path.parents] if p != self.home.parent):
            raise InstallError(f'Symlinked managed path: {relative}')
        return path

    @contextmanager
    def lock(self):
        self.internal(self.base).mkdir(parents=True, exist_ok=True)
        path = self.internal(self.base / '.installer.lock')
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise InstallError('Another installer operation owns .installer.lock; inspect its process before recovery') from exc
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump({'pid': os.getpid()}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            yield
        finally:
            path.unlink(missing_ok=True)

    def manifest(self) -> dict | None:
        self.internal(self.manifest_path)
        if not self.manifest_path.exists():
            return None
        return json.loads(self.manifest_path.read_text(encoding='utf-8'))

    def rows(self, manifest: dict) -> list[dict]:
        result = []
        for row in manifest['files']:
            relative = row.get('relative')
            if relative is None:
                try:
                    relative = Path(row['path']).resolve().relative_to(self.home).as_posix()
                except ValueError as exc:
                    raise InstallError('Legacy manifest contains a path outside Codex home') from exc
            self.target(relative)
            result.append(dict(row, relative=relative))
        return result

    def check_ownership(self, manifest: dict | None) -> None:
        if manifest is None:
            if owned_block((self.home / 'AGENTS.md').read_bytes() if (self.home / 'AGENTS.md').exists() else b''):
                raise InstallError('Unowned global workflow block exists; refusing to adopt it implicitly')
            return
        for row in self.rows(manifest):
            path = self.target(row['relative'])
            if row['relative'] == 'AGENTS.md' and manifest.get('format') == FORMAT:
                if owned_block(path.read_bytes() if path.exists() else b'') != manifest['owned_block'].encode():
                    raise InstallError('Modified owned AGENTS.md block; all dependencies preserved')
            elif file_hash(path) != row['sha256']:
                raise InstallError(f'Modified or missing owned file: {path}')

    def plan(self, action: str) -> dict:
        old = self.manifest()
        report = {'status': 'PLAN', 'action': action, 'apply_required': True,
                  'source': str(self.source), 'codex_home': str(self.home),
                  'current_format': old.get('format', 1) if old else None,
                  'current_generation': old.get('generation') if old else None,
                  'roles': {'configuration': 'NOT_CHECKED', 'discovery': 'DISCOVERY_UNVERIFIED',
                            'effective_sandbox': 'EFFECTIVE_SANDBOX_UNVERIFIED'}}
        self.internal(self.pending_path)
        if self.pending_path.exists():
            pending = json.loads(self.pending_path.read_text())
            report['pending_operation'] = pending['status']
        if action == 'rollback':
            report['managed_targets'] = [r['relative'] for r in self.rows(old)] if old else []
            report['operation'] = 'Restore preceding generation, preserving all dependencies on ownership conflict'
        else:
            targets = ['AGENTS.md', 'workflows/turn-up-time/run.py', 'workflows/turn-up-time/CODEX.md']
            targets += ['agents/tut_' + p.stem.replace('-', '_') + '.toml'
                        for p in sorted((self.source / '.claude/agents').glob('*.md'))]
            targets += ['skills/' + (p.parent.name if p.parent.name == 'turn-up-time' else 'tut-' + p.parent.name) + '/SKILL.md'
                        for p in sorted((self.source / '.claude/skills').glob('*/SKILL.md'))]
            report['managed_targets'] = targets
            report['candidate_root'] = str(self.base / 'generations/<new-generation>')
            report['runtime_setup'] = 'Create isolated venv; install source runtime and PyYAML; validate before activation'
            report['legacy_migration'] = bool(old and old.get('format') != FORMAT)
        try:
            self.check_ownership(old)
        except InstallError as exc:
            report['status'] = 'BLOCKED'
            report['ownership_conflict'] = str(exc)
        return report

    def transaction(self, desired: dict[str, bytes | None], operation: str, fail_after: int | None = None) -> None:
        transaction_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:10]
        journal_dir = self.internal(self.base / 'operations' / transaction_id)
        rows = []
        # Backup and checksum every target before the journal or first active write.
        for index, (relative, content) in enumerate(desired.items()):
            path = self.target(relative)
            previous = path.read_bytes() if path.exists() else None
            backup = self.internal(journal_dir / f'{index}.before')
            if previous is not None:
                atomic_write(backup, previous)
            rows.append({'relative': relative, 'before_hash': digest(previous) if previous is not None else None,
                         'backup': str(backup) if previous is not None else None,
                         'after_hash': digest(content) if content is not None else None})
        journal = {'status': 'PREPARED', 'operation': operation, 'rows': rows, 'receipt': str(journal_dir / 'journal.json')}
        def record(status):
            journal['status'] = status
            atomic_write(Path(journal['receipt']), json_bytes(journal))
            atomic_write(self.pending_path, json_bytes(journal))
        record('PREPARED')
        try:
            record('APPLYING')
            for count, (relative, content) in enumerate(desired.items(), 1):
                path = self.target(relative)
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write(path, content)
                if fail_after == count:
                    raise InstallError(f'Injected activation failure after {count} writes')
            record('COMMITTED')
        except BaseException:
            self.restore_pending(journal)
            raise

    def restore_pending(self, journal: dict) -> None:
        receipt = self.internal(Path(journal['receipt']))
        if not receipt.resolve().is_relative_to((self.base / 'operations').resolve()):
            raise InstallError('Unsafe recovery receipt path')
        for row in journal['rows']:
            path = self.target(row['relative'])
            if file_hash(path) not in {row['before_hash'], row['after_hash']}:
                raise InstallError(f'Interrupted operation conflicts with later edits: {path}')
            if row['backup']:
                backup = self.internal(Path(row['backup']))
                if not backup.resolve().is_relative_to((self.base / 'operations').resolve()) or file_hash(backup) != row['before_hash']:
                    raise InstallError('Interrupted operation backup is missing or changed')
        for row in reversed(journal['rows']):
            path = self.target(row['relative'])
            if row['backup']:
                atomic_write(path, Path(row['backup']).read_bytes())
            else:
                path.unlink(missing_ok=True)
        journal['status'] = 'RECOVERED'
        atomic_write(receipt, json_bytes(journal))
        atomic_write(self.pending_path, json_bytes(journal))

    def recover(self) -> bool:
        self.internal(self.pending_path)
        if self.pending_path.exists():
            journal = json.loads(self.pending_path.read_text())
            if journal['status'] in {'PREPARED', 'APPLYING'}:
                self.restore_pending(journal)
                return True
        return False

    def install(self, update: bool = False, fail_after: int | None = None) -> dict:
        self.recover()
        old = self.manifest()
        if old and old.get('shared_release_id'):
            raise InstallError('Shared release: use promote_workflow.py for coordinated recovery or migration')
        if old and not update:
            raise InstallError('Installation exists; use update --apply')
        if not old and update:
            raise InstallError('No installation exists; use install --apply')
        self.check_ownership(old)
        if self.base.is_relative_to(self.source):
            raise InstallError('Codex installation cannot be nested inside its source tree')
        for required in ('CLAUDE.md', '.claude/skills/turn-up-time/SKILL.md', 'runtime/pyproject.toml', 'docs/CODEX.md'):
            if not (self.source / required).is_file():
                raise InstallError(f'Missing source prerequisite: {required}')
        generation = self.base / 'generations' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:10])
        self.internal(generation)
        source = generation / 'source'
        snapshot(self.source, source)
        python = self.runtime_builder(source, generation / 'venv')
        meta = metadata(source, python)
        generated, block = generated_files(self.home, generation, python, meta)
        # Recheck ownership after potentially lengthy runtime creation.
        self.check_ownership(old)
        old_rows = {row['relative']: row for row in self.rows(old)} if old else {}
        for relative in generated:
            if self.target(relative).exists() and relative not in old_rows:
                raise InstallError(f'Unowned target exists: {relative}')
        agents_path = self.target('AGENTS.md')
        agents_before = agents_path.read_bytes() if agents_path.exists() else b''
        old_block = owned_block(agents_before) if old else None
        generated['AGENTS.md'] = merge_block(agents_before, old_block, block)
        desired: dict[str, bytes | None] = dict(generated)
        for relative in old_rows:
            if relative not in desired:
                desired[relative] = None
        # Keep activation/default last, manifest commit after it.
        desired['AGENTS.md'] = desired.pop('AGENTS.md')
        rows = []
        for relative, content in desired.items():
            path = self.target(relative)
            before = path.read_bytes() if path.exists() else None
            backup = self.internal(generation / 'previous-files' / relative)
            if before is not None:
                atomic_write(backup, before)
            rows.append({'relative': relative, 'sha256': digest(content) if content is not None else None,
                         'backup': str(backup) if before is not None else None,
                         'backup_sha256': digest(before) if before is not None else None})
        previous_manifest = generation / 'previous-manifest.json'
        previous_data = self.manifest_path.read_bytes() if old else None
        if previous_data is not None:
            atomic_write(previous_manifest, previous_data)
        environment = json.loads(run([python, '-c', 'import importlib.metadata,json,sys; print(json.dumps({"python":sys.version,"packages":sorted((d.metadata["Name"],d.version) for d in importlib.metadata.distributions())}))']).stdout)
        manifest = {'format': FORMAT, 'status': 'ACTIVE', 'generation': str(generation), 'source_origin': str(self.source),
                    'python': str(python), 'files': rows, 'owned_block': block.decode(),
                    'previous_block': old_block.decode() if old_block else None,
                    'previous_manifest': str(previous_manifest) if old else None,
                    'previous_manifest_sha256': digest(previous_data) if previous_data else None,
                    'source_inventory': inventory(source), 'runtime_inventory': inventory(generation / 'venv'),
                    'environment': environment,
                    'agents': {name: 'tut_' + name.replace('-', '_') for name in meta['agents']},
                    'skills': {name: name if name == 'turn-up-time' else 'tut-' + name for name in meta['skills']}}
        atomic_write(generation / 'candidate-manifest.json', json_bytes(manifest))
        desired['workflows/turn-up-time/install-manifest.json'] = json_bytes(manifest)
        self.transaction(desired, 'UPDATE' if update else 'INSTALL', fail_after)
        return {'status': 'INSTALLED', 'generation': str(generation), 'python': str(python),
                'roles': {'configuration': 'CONFIG_VALID', 'discovery': 'DISCOVERY_UNVERIFIED',
                          'effective_sandbox': 'EFFECTIVE_SANDBOX_UNVERIFIED'}}

    def payload_errors(self, manifest: dict) -> list[str]:
        generation = self.internal(Path(manifest['generation']))
        if not generation.resolve().is_relative_to((self.base / 'generations').resolve()):
            raise InstallError('Unsafe generation path')
        errors = []
        for key, directory in [('source_inventory', 'source'), ('runtime_inventory', 'venv')]:
            actual, expected = inventory(generation / directory), manifest[key]
            for name in sorted(set(actual) | set(expected)):
                if actual.get(name) != expected.get(name):
                    errors.append(f'{directory} integrity mismatch: {name}')
        return errors

    def verify(self) -> dict:
        manifest = self.manifest()
        if not manifest:
            raise InstallError('No active installation')
        errors = []
        try:
            self.check_ownership(manifest)
        except InstallError as exc:
            errors.append(str(exc))
        legacy = manifest.get('format') != FORMAT
        if not legacy:
            errors.extend(self.payload_errors(manifest))
        config_errors = []
        for role in manifest.get('agents', {}).values():
            try:
                data = tomllib.loads(self.target(f'agents/{role}.toml').read_text(encoding='utf-8'))
                if data['name'] != role or not data['developer_instructions']:
                    raise ValueError('Role name/instructions invalid')
                if role != 'tut_implementation_engineer' and data.get('sandbox_mode') != 'read-only':
                    raise ValueError('Assurance sandbox declaration missing')
            except (KeyError, ValueError, OSError, InstallError) as exc:
                config_errors.append(f'{role}: {exc}')
        errors.extend(config_errors)
        if self.pending_path.exists() and json.loads(self.pending_path.read_text())['status'] in {'PREPARED', 'APPLYING'}:
            errors.append('Interrupted activation: run rollback --apply to restore owned files before continuing')
        return {'status': 'DRIFTED' if errors else ('LEGACY_UNVERIFIED' if legacy else 'VERIFIED'), 'errors': errors,
                'integrity_scope': 'managed files only' if legacy else 'managed files, source snapshot, runtime payload',
                'roles': {'configuration': 'CONFIG_INVALID' if config_errors else 'CONFIG_VALID',
                          'discovery': 'DISCOVERY_UNVERIFIED', 'effective_sandbox': 'EFFECTIVE_SANDBOX_UNVERIFIED'}}

    def rollback(self, fail_after: int | None = None) -> dict:
        if self.recover():
            return {'status': 'RECOVERED_INTERRUPTED_OPERATION'}
        manifest = self.manifest()
        if not manifest:
            raise InstallError('No active installation')
        if manifest.get('shared_release_id'):
            raise InstallError('Shared release: use promote_workflow.py for coordinated recovery')
        if manifest.get('format') != FORMAT:
            raise InstallError('Legacy installation: migrate with update before using this rollback')
        self.check_ownership(manifest)
        generation = self.internal(Path(manifest['generation']))
        if not generation.resolve().is_relative_to((self.base / 'generations').resolve()):
            raise InstallError('Unsafe generation path')
        desired = {}
        for row in self.rows(manifest):
            backup = Path(row['backup']) if row['backup'] else None
            if backup and (not backup.resolve().is_relative_to(generation.resolve()) or file_hash(backup) != row['backup_sha256']):
                raise InstallError(f'Missing or modified rollback backup: {backup}')
            content = backup.read_bytes() if backup else None
            path = self.target(row['relative'])
            if row['relative'] == 'AGENTS.md' and file_hash(path) != row['sha256']:
                content = merge_block(path.read_bytes(), manifest['owned_block'].encode(),
                                      manifest['previous_block'].encode() if manifest['previous_block'] else None)
            desired[row['relative']] = content
        previous = Path(manifest['previous_manifest']) if manifest['previous_manifest'] else None
        if previous and (not previous.resolve().is_relative_to(generation.resolve()) or file_hash(previous) != manifest['previous_manifest_sha256']):
            raise InstallError('Missing or modified previous manifest')
        restored_integrity = 'NO_PREVIOUS_INSTALLATION'
        if previous:
            prior_manifest = json.loads(previous.read_text(encoding='utf-8'))
            if prior_manifest.get('format') == FORMAT:
                prior_errors = self.payload_errors(prior_manifest)
                if prior_errors:
                    raise InstallError('Previous generation failed integrity preflight: ' + '; '.join(prior_errors))
                restored_integrity = 'PAYLOAD_VERIFIED'
            else:
                # Legacy receipts never hashed source/runtime. Preserve that limitation explicitly.
                restored_integrity = 'LEGACY_UNVERIFIED'
        desired['workflows/turn-up-time/install-manifest.json'] = previous.read_bytes() if previous else None
        self.transaction(desired, 'ROLLBACK', fail_after)
        return {'status': 'ROLLED_BACK', 'generations_retained': True, 'restored_integrity': restored_integrity}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'install', 'update', 'verify', 'rollback'], nargs='?', default='plan')
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')))
    parser.add_argument('--apply', action='store_true', help='Apply install/update/rollback; otherwise print a read-only plan')
    args = parser.parse_args(argv)
    try:
        installer = Installer(args.source, args.codex_home)
        if args.command == 'verify':
            report = installer.verify()
        elif args.command == 'plan' or not args.apply:
            report = installer.plan(args.command)
        else:
            with installer.lock():
                report = installer.rollback() if args.command == 'rollback' else installer.install(update=args.command == 'update')
        print(json.dumps(report, indent=2))
        return 2 if report['status'] in {'DRIFTED', 'LEGACY_UNVERIFIED', 'BLOCKED'} else 0
    except (InstallError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        detail = str(exc)
        if isinstance(exc, subprocess.CalledProcessError):
            detail += '\n' + (exc.stderr or exc.stdout or '')
        print(json.dumps({'status': 'PARTIAL_ROLLBACK' if args.command == 'rollback' else 'BLOCKED',
                          'error': detail, 'dependencies_preserved': True}, indent=2))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
