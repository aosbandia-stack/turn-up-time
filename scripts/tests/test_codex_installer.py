"""Seeded adapter failures use temporary homes; never touch the user's Codex profile."""
import importlib.util
import json
import os
import subprocess
from pathlib import Path
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'codex_installer.py'
spec = importlib.util.spec_from_file_location('codex_installer', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def fixture(tmp_path):
    source = tmp_path / 'source with spaces'
    home = tmp_path / 'codex home with spaces'
    files = {
        'CLAUDE.md': '# Canonical workflow',
        '.claude/skills/turn-up-time/SKILL.md': '---\nname: turn-up-time\ndescription: Root workflow\n---\nRoot procedure',
        '.claude/skills/eval-harness/SKILL.md': '---\nname: eval-harness\ndescription: Evaluation\n---\nEval procedure',
        '.claude/agents/implementation-engineer.md': '---\nname: implementation-engineer\ndescription: Builder\nrole_class: production\n---\nOwned scope only',
        '.claude/agents/reviewer.md': '---\nname: reviewer\ndescription: Independent reviewer\nrole_class: assurance\n---\nNo writes',
        '.claude/scripts/probe.py': 'print("ok")',
        'runtime/pyproject.toml': '[project]\nname="fixture"\nversion="1"',
        'docs/CODEX.md': '# Codex adapter documentation',
        'docs/GRAPH-REVIEW-REPORT.md': 'Canonical linked release report',
        'docs/WORKFLOW-AUDIT-local.md': 'Source-owned audit document',
        'docs/local-audit.log': 'Local raw logs',
        'scripts/codex_installer.py': SCRIPT.read_text(encoding='utf-8'),
        '.claude/projects/private/evidence.json': 'PRIVATE PROJECT EVIDENCE',
        '.claude/runtime/active.sqlite': 'PRIVATE STATE',
        '.claude/audit-runs/secret.txt': 'LOCAL EVIDENCE',
        '.git/config': 'GIT CONFIG',
        'runtime/.venv/secret.txt': 'OLD VENV',
        'runtime/__pycache__/x.pyc': 'CACHE',
    }
    for name, text in files.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    (source / 'scripts/codex_installer.py').write_bytes(SCRIPT.read_bytes())
    def runtime(source, venv):
        venv.mkdir(parents=True)
        (venv / 'payload.txt').write_text('deterministic runtime payload')
        return Path(sys.executable)
    return module.Installer(source, home, runtime), source, home


def test_dry_run_is_read_only(fixture, capsys):
    installer, source, home = fixture
    assert module.main(['install', '--source', str(source), '--codex-home', str(home)]) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'PLAN'
    assert not home.exists()
    assert installer.plan('install')['managed_targets']


def test_shared_release_can_verify_but_cannot_independently_rollback(fixture):
    installer, source, home = fixture
    installer.install()
    manifest = installer.manifest()
    manifest['shared_release_id'] = 'shared-test'
    module.atomic_write(installer.manifest_path, module.json_bytes(manifest))
    assert installer.verify()['status'] == 'VERIFIED'
    with pytest.raises(module.InstallError, match='Shared release'):
        installer.rollback()
    with pytest.raises(module.InstallError, match='Shared release'):
        installer.install(update=True)
    assert installer.plan('install')['runtime_setup']


def test_install_inventory_and_honest_roles(fixture):
    installer, source, home = fixture
    result = installer.install()
    assert result['roles']['discovery'] == 'DISCOVERY_UNVERIFIED'
    report = installer.verify()
    assert report['status'] == 'VERIFIED'
    assert report['roles']['effective_sandbox'] == 'EFFECTIVE_SANDBOX_UNVERIFIED'
    manifest = installer.manifest()
    assert manifest['source_inventory'] and manifest['runtime_inventory']
    assert manifest['environment']['python']
    snapshot = Path(manifest['generation']) / 'source'
    for path in ['.claude/projects', '.claude/runtime', '.claude/audit-runs', '.git', 'runtime/.venv', 'runtime/__pycache__']:
        assert not (snapshot / path).exists()
    assert (snapshot / 'docs/GRAPH-REVIEW-REPORT.md').is_file()
    assert (snapshot / 'docs/WORKFLOW-AUDIT-local.md').exists()
    assert not (snapshot / 'docs/local-audit.log').exists()
    reviewer = (home / 'agents/tut_reviewer.toml').read_text()
    assert 'sandbox_mode = "read-only"' in reviewer
    assert 'sandbox_mode' not in (home / 'agents/tut_implementation_engineer.toml').read_text()


def test_generated_outputs_match_source_owned_generator(fixture):
    installer, _, home = fixture
    installer.install()
    manifest = installer.manifest()
    generation = Path(manifest['generation'])
    # Regenerate from installed source through the source-owned generator, not profile-local patches.
    meta = module.metadata(generation / 'source', Path(manifest['python']))
    desired, block = module.generated_files(home, generation, Path(manifest['python']), meta)
    for name, expected in desired.items():
        assert (home / name).read_bytes() == expected
    assert module.owned_block((home / 'AGENTS.md').read_bytes()) == block
    assert 'dont_write_bytecode = True' in desired['workflows/turn-up-time/run.py'].decode()
    assert (generation / 'source/scripts/codex_installer.py').read_bytes() == SCRIPT.read_bytes()


def test_update_rollback_and_reinstall(fixture):
    installer, source, home = fixture
    (home / 'AGENTS.md').parent.mkdir(parents=True)
    original = b'# User preferences\n'
    (home / 'AGENTS.md').write_bytes(original)
    installer.install()
    initial = installer.manifest_path.read_bytes()
    initial_runner = (installer.base / 'run.py').read_bytes()
    (source / 'CLAUDE.md').write_text('Updated workflow')
    installer.install(update=True)
    assert installer.manifest_path.read_bytes() != initial
    installer.rollback()
    assert installer.manifest_path.read_bytes() == initial
    assert (installer.base / 'run.py').read_bytes() == initial_runner
    assert installer.verify()['status'] == 'VERIFIED'
    installer.rollback()
    assert not installer.manifest_path.exists()
    assert (home / 'AGENTS.md').read_bytes() == original
    installer.install()
    assert installer.verify()['status'] == 'VERIFIED'


def test_unrelated_global_edits_survive_update_and_rollback(fixture):
    installer, _, home = fixture
    installer.install()
    agents = home / 'AGENTS.md'
    agents.write_bytes(b'# Additional preference\n' + agents.read_bytes() + b'\n# New footer\n')
    installer.install(update=True)
    installer.rollback()
    installer.rollback()
    assert b'Additional preference' in agents.read_bytes()
    assert b'New footer' in agents.read_bytes()
    assert module.BEGIN.encode() not in agents.read_bytes()
    assert not (home / 'skills/turn-up-time/SKILL.md').exists()


def test_modified_owned_block_blocks_whole_rollback(fixture, capsys):
    installer, source, home = fixture
    installer.install()
    agents = home / 'AGENTS.md'
    agents.write_text(agents.read_text().replace('Tier A for answers', 'Tier A CUSTOM answers'))
    wrapper = home / 'skills/turn-up-time/SKILL.md'
    before = wrapper.read_bytes()
    assert module.main(['rollback', '--source', str(source), '--codex-home', str(home), '--apply']) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'PARTIAL_ROLLBACK'
    assert wrapper.read_bytes() == before
    assert installer.manifest_path.exists()


def test_modified_skill_blocks_update_without_activation(fixture):
    installer, _, home = fixture
    installer.install()
    wrapper = home / 'skills/turn-up-time/SKILL.md'
    wrapper.write_text('user custom workflow')
    manifest = installer.manifest_path.read_bytes()
    with pytest.raises(module.InstallError, match='Modified or missing owned file'):
        installer.install(update=True)
    assert installer.manifest_path.read_bytes() == manifest
    assert wrapper.read_text() == 'user custom workflow'


@pytest.mark.parametrize('changed', ['source/CLAUDE.md', 'venv/payload.txt'])
def test_payload_tampering_is_detected(fixture, changed):
    installer, _, _ = fixture
    installer.install()
    path = Path(installer.manifest()['generation']) / changed
    path.write_text('tampered payload')
    report = installer.verify()
    assert report['status'] == 'DRIFTED'
    assert any('integrity mismatch' in error for error in report['errors'])


@pytest.mark.parametrize('write_number', [1, 3, 7, 8])
def test_injected_activation_failure_restores_prior_install(fixture, write_number):
    installer, source, home = fixture
    installer.install()
    initial = installer.manifest_path.read_bytes()
    tracked = {r['relative']: (home / r['relative']).read_bytes() for r in installer.manifest()['files']}
    (source / 'CLAUDE.md').write_text('new source')
    with pytest.raises(module.InstallError, match='Injected activation failure'):
        installer.install(update=True, fail_after=write_number)
    assert installer.manifest_path.read_bytes() == initial
    for name, expected in tracked.items():
        assert (home / name).read_bytes() == expected
    assert installer.verify()['status'] == 'VERIFIED'
    assert json.loads(installer.pending_path.read_text())['status'] == 'RECOVERED'


def test_interrupted_activation_recovery_preserves_later_edits(fixture):
    installer, _, home = fixture
    path = home / 'skills/turn-up-time/SKILL.md'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'before')
    # A process died after one managed write: durable backup + pending journal remain.
    directory = installer.base / 'operations/crashed'
    directory.mkdir(parents=True)
    backup = directory / '0.before'
    backup.write_bytes(b'before')
    journal = {'status': 'APPLYING', 'operation': 'INSTALL', 'receipt': str(directory / 'journal.json'),
               'rows': [{'relative': 'skills/turn-up-time/SKILL.md', 'before_hash': module.digest(b'before'),
                         'after_hash': module.digest(b'after'), 'backup': str(backup)}]}
    module.atomic_write(installer.pending_path, module.json_bytes(journal))
    path.write_bytes(b'later user edit')
    with pytest.raises(module.InstallError, match='conflicts with later edits'):
        installer.recover()
    assert path.read_bytes() == b'later user edit'
    path.write_bytes(b'after')
    assert installer.recover()
    assert path.read_bytes() == b'before'


def test_missing_backup_blocks_rollback_before_any_write(fixture):
    installer, _, home = fixture
    home.mkdir(parents=True)
    (home / 'AGENTS.md').write_text('Original preferences')
    installer.install()
    row = next(row for row in installer.manifest()['files'] if row['relative'] == 'AGENTS.md')
    Path(row['backup']).unlink()
    wrapper = home / 'skills/turn-up-time/SKILL.md'
    before = wrapper.read_bytes()
    with pytest.raises(module.InstallError, match='Missing or modified rollback backup'):
        installer.rollback()
    assert wrapper.read_bytes() == before


def test_legacy_manifest_migrates_and_restores_exactly(fixture):
    installer, _, home = fixture
    installer.install()
    modern = installer.manifest()
    legacy = {'source': 'old source', 'revision': 'old revision',
              'python': modern['python'], 'skills': modern['skills'], 'agents': modern['agents'],
              'files': [{'path': str(home / row['relative']), 'sha256': row['sha256'], 'backup': None}
                        for row in modern['files']]}
    previous = module.json_bytes(legacy)
    installer.manifest_path.write_bytes(previous)
    wrapper = (home / 'skills/turn-up-time/SKILL.md').read_bytes()
    installer.install(update=True)
    assert installer.verify()['status'] == 'VERIFIED'
    installer.rollback()
    assert installer.manifest_path.read_bytes() == previous
    assert (home / 'skills/turn-up-time/SKILL.md').read_bytes() == wrapper
    assert installer.verify()['status'] == 'LEGACY_UNVERIFIED'


def test_unsafe_manifest_path_is_rejected(fixture):
    installer, _, _ = fixture
    installer.install()
    manifest = installer.manifest()
    manifest['files'][0]['relative'] = '../outside.txt'
    installer.manifest_path.write_bytes(module.json_bytes(manifest))
    with pytest.raises(module.InstallError, match='Unsafe managed path'):
        installer.rollback()


def test_portable_python_paths():
    assert module.interpreter(Path('/env'), 'nt').as_posix().endswith('/Scripts/python.exe')
    assert module.interpreter(Path('/env'), 'posix').as_posix().endswith('/bin/python')


def test_concurrent_installer_is_blocked(fixture):
    installer, _, _ = fixture
    with installer.lock():
        with pytest.raises(module.InstallError, match='Another installer operation'):
            with installer.lock():
                pass
    assert not (installer.base / '.installer.lock').exists()


@pytest.mark.parametrize('changed', ['source/CLAUDE.md', 'venv/payload.txt'])
def test_rollback_never_activates_tampered_previous_generation(fixture, changed):
    installer, source, home = fixture
    installer.install()
    previous_generation = Path(installer.manifest()['generation'])
    (source / 'CLAUDE.md').write_text('candidate generation two')
    installer.install(update=True)
    current_manifest = installer.manifest_path.read_bytes()
    tracked = {r['relative']: (home / r['relative']).read_bytes() for r in installer.manifest()['files']}
    (previous_generation / changed).write_text('inactive generation tampered')
    with pytest.raises(module.InstallError, match='Previous generation failed integrity preflight'):
        installer.rollback()
    assert installer.manifest_path.read_bytes() == current_manifest
    for name, content in tracked.items():
        assert (home / name).read_bytes() == content
    assert installer.verify()['status'] == 'VERIFIED'


def directory_link(link, target):
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name == 'nt':
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], check=True, capture_output=True)
    else:
        link.symlink_to(target, target_is_directory=True)


@pytest.mark.parametrize('relative', ['workflows', 'workflows/turn-up-time/generations', 'workflows/turn-up-time/operations'])
def test_internal_redirect_blocks_before_writes(fixture, relative):
    installer, source, home = fixture
    outside = source.parent / 'outside installation'
    outside.mkdir()
    (outside / 'sentinel.txt').write_text('untouched')
    directory_link(home / relative, outside)
    with pytest.raises(module.InstallError, match='escapes|redirection'):
        if relative.endswith('operations'):
            installer.transaction({'AGENTS.md': b'candidate'}, 'TEST')
        else:
            with installer.lock():
                installer.install()
    assert list(outside.iterdir()) == [outside / 'sentinel.txt']
    assert not (home / 'AGENTS.md').exists()


@pytest.mark.parametrize('root', ['.claude', 'runtime', 'docs', 'scripts'])
def test_snapshot_root_redirect_fails_before_copying(tmp_path, root):
    source = tmp_path / 'source'
    source.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'sentinel.txt').write_text('private')
    for name in ['.claude', 'runtime', 'docs', 'scripts']:
        if name != root:
            (source / name).mkdir()
            (source / name / 'regular.txt').write_text('regular')
    directory_link(source / root, outside)
    target = tmp_path / 'snapshot'
    with pytest.raises(module.InstallError, match='Source root redirection'):
        module.snapshot(source, target)
    assert not target.exists()
    assert (outside / 'sentinel.txt').read_text() == 'private'


def test_old_rollback_helper_fails_before_touching_v2(fixture):
    installer, _, home = fixture
    installer.install()
    before = {r['relative']: (home / r['relative']).read_bytes() for r in installer.manifest()['files']}
    # Exact first operations in the historical rollback.py, before restoration/unlink.
    legacy = "import json\nfrom pathlib import Path\nmanifest=json.loads(Path(__file__).with_name('install-manifest.json').read_text())\nfor row in reversed(manifest['files']):\n    p=Path(row['path'])\n    raise RuntimeError('old helper must not reach any mutation')\n"
    helper = installer.base / 'old-rollback-probe.py'
    helper.write_text(legacy)
    result = subprocess.run([sys.executable, str(helper)], capture_output=True, text=True)
    assert result.returncode != 0
    assert "KeyError: 'path'" in result.stderr
    for name, content in before.items():
        assert (home / name).read_bytes() == content
