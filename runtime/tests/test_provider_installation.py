"""Real filesystem/Git failure paths for the opt-in provider installer; no network."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('provider_install', ROOT / 'scripts/provider_install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


@pytest.fixture
def setup(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir()
    git(source, 'init')
    git(source, 'config', 'user.name', 'Provider Test')
    git(source, 'config', 'user.email', 'provider-test@example.invalid')
    (source / 'SKILL.md').write_text('Pinned skill\n', encoding='utf-8')
    (source / 'LICENSE').write_text('Test license\n', encoding='utf-8')
    git(source, 'add', '.')
    git(source, '-c', 'core.hooksPath=' + os.devnull, 'commit', '-m', 'fixture')
    commit = git(source, 'rev-parse', 'HEAD')
    packages = []
    for name in ['first-provider', 'second-provider']:
        files = {p: {'source': p, 'sha256': installer.digest((source / p).read_bytes())}
                 for p in ['SKILL.md', 'LICENSE']}
        packages.append({'name': name, 'repository': 'fixture', 'files': files})
    lock = {'schema_version': 1, 'repositories': {'fixture': {
        'url': 'https://github.com/example/provider.git', 'commit': commit}}, 'packages': packages}
    lock_path = tmp_path / 'provider-lock.json'
    lock_path.write_text(json.dumps(lock))
    monkeypatch.setattr(installer, 'LOCK', lock_path)
    home = tmp_path / 'claude'
    args = ['--home', str(home)]
    source_arg = ['--source', 'fixture=' + str(source)]
    return home, source, lock, lock_path, args, source_arg


def test_dry_run_writes_nothing_and_does_not_fetch(setup, monkeypatch):
    home, _, _, _, args, _ = setup
    monkeypatch.setattr(installer, 'git', lambda *a: pytest.fail('Dry run invoked Git'))
    assert installer.main(['install', *args]) == 0
    assert not home.exists()


def test_roundtrip_idempotence_preserves_custom_skill(setup, monkeypatch):
    home, _, _, _, args, supplied = setup
    custom = home / 'skills/custom/SKILL.md'
    custom.parent.mkdir(parents=True)
    custom.write_text('Mine')
    assert installer.main(['install', *args, *supplied, '--apply']) == 0
    before = (home / installer.MANIFEST).read_bytes()
    assert installer.main(['verify', *args]) == 0
    monkeypatch.setattr(installer, 'git', lambda *a: pytest.fail('Repeat install fetched sources'))
    assert installer.main(['install', *args, '--apply']) == 0
    assert (home / installer.MANIFEST).read_bytes() == before
    assert installer.main(['remove', *args]) == 0
    assert (home / 'skills/first-provider/SKILL.md').exists()
    assert installer.main(['remove', *args, '--apply']) == 0
    assert custom.read_text() == 'Mine'
    assert not (home / installer.MANIFEST).exists()
    assert not (home / 'skills/first-provider').exists()


@pytest.mark.parametrize('change', ['edit', 'extra', 'extra-directory', 'missing'])
def test_tamper_blocks_verify_reinstall_and_all_removal(setup, change):
    home, _, _, _, args, supplied = setup
    assert installer.main(['install', *args, *supplied, '--apply']) == 0
    entry = home / 'skills/second-provider/SKILL.md'
    if change == 'edit':
        entry.write_text('Local work')
    elif change == 'extra':
        entry.with_name('local-notes.md').write_text('Local work')
    elif change == 'extra-directory':
        entry.with_name('local-work').mkdir()
    else:
        entry.unlink()
    assert installer.main(['verify', *args]) == 1
    assert installer.main(['install', *args, *supplied, '--apply']) == 1
    assert installer.main(['remove', *args, '--apply']) == 1
    assert (home / 'skills/first-provider/SKILL.md').exists()
    assert (home / installer.MANIFEST).exists()


def test_unmanaged_provider_is_never_adopted_even_if_bytes_match(setup):
    home, source, _, _, args, supplied = setup
    target = home / 'skills/first-provider'
    target.mkdir(parents=True)
    (target / 'SKILL.md').write_bytes((source / 'SKILL.md').read_bytes())
    assert installer.main(['install', *args, *supplied, '--apply']) == 1
    assert not (home / installer.MANIFEST).exists()
    assert not (home / 'skills/second-provider').exists()


@pytest.mark.parametrize('failure', ['dirty', 'wrong-pin', 'missing-asset', 'bad-hash'])
def test_source_failure_never_activates_partial_package(setup, failure):
    home, source, lock, lock_path, args, supplied = setup
    if failure == 'dirty':
        (source / 'SKILL.md').write_text('Not reviewed')
    elif failure == 'wrong-pin':
        lock['repositories']['fixture']['commit'] = '0' * 40
    elif failure == 'missing-asset':
        lock['packages'][1]['files']['LICENSE']['source'] = 'absent.md'
    else:
        lock['packages'][1]['files']['LICENSE']['sha256'] = '0' * 64
    lock_path.write_text(json.dumps(lock))
    assert installer.main(['install', *args, *supplied, '--apply']) == 1
    assert not (home / installer.MANIFEST).exists()
    assert not (home / 'skills/first-provider').exists()


def test_download_failure_never_activates_package(setup, monkeypatch):
    home, _, _, _, args, _ = setup
    def failing_git(*args):
        raise installer.InstallError('Download unavailable')
    monkeypatch.setattr(installer, 'git', failing_git)
    assert installer.main(['install', *args, '--apply']) == 1
    assert not (home / installer.MANIFEST).exists()
    assert not (home / 'skills').exists()


def test_interrupted_promotion_is_not_complete_and_is_recoverable(setup, monkeypatch):
    home, _, _, _, args, supplied = setup
    rename = Path.rename
    def failing_rename(path, target):
        if Path(target).name == 'second-provider':
            raise OSError('Injected disk failure')
        return rename(path, target)
    with monkeypatch.context() as m:
        m.setattr(Path, 'rename', failing_rename)
        assert installer.main(['install', *args, *supplied, '--apply']) == 1
    assert json.loads((home / installer.MANIFEST).read_text())['state'] == 'installing'
    assert installer.main(['verify', *args]) == 1
    assert installer.main(['install', *args, *supplied, '--apply']) == 1
    assert installer.main(['remove', *args, '--apply']) == 0
    assert installer.main(['install', *args, *supplied, '--apply']) == 0


def test_manifest_cannot_claim_an_outside_path(setup):
    home, _, _, _, args, supplied = setup
    assert installer.main(['install', *args, *supplied, '--apply']) == 0
    path = home / installer.MANIFEST
    manifest = json.loads(path.read_text())
    manifest['files']['../outside'] = {}
    path.write_text(json.dumps(manifest))
    assert installer.main(['remove', *args, '--apply']) == 1
    assert (home / 'skills/first-provider/SKILL.md').exists()


@pytest.mark.parametrize('bad', ['../escape', '/absolute', 'C:/escape', 'safe/../../escape', 'foo\\bar', 'foo/../bar', 'foo:stream'])
def test_lock_path_traversal_blocks_before_copy(setup, bad):
    home, _, lock, lock_path, args, supplied = setup
    lock['packages'][0]['files'][bad] = {'content': 'escape', 'sha256': installer.digest(b'escape')}
    lock_path.write_text(json.dumps(lock))
    assert installer.main(['install', *args, *supplied, '--apply']) == 1
    assert not (home / 'skills').exists()


def test_target_symlink_or_junction_is_rejected(setup, tmp_path):
    home, _, _, _, args, supplied = setup
    outside = tmp_path / 'outside'
    outside.mkdir()
    if os.name == 'nt':
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(home), str(outside)], check=True, capture_output=True)
    else:
        home.symlink_to(outside, target_is_directory=True)
    assert installer.main(['install', *args, *supplied, '--apply']) == 1
    assert list(outside.iterdir()) == []


def test_symlink_source_blob_is_rejected(setup):
    home, source, lock, lock_path, args, supplied = setup
    oid = git(source, 'hash-object', '-w', 'LICENSE')
    git(source, 'update-index', '--add', '--cacheinfo', '120000,' + oid + ',link')
    git(source, 'commit', '-m', 'symlink fixture')
    # A real symlink is not required on Windows; materialization reads the committed mode.
    commit = git(source, 'rev-parse', 'HEAD')
    lock['repositories']['fixture']['commit'] = commit
    lock['packages'][0]['files']['link'] = {'source': 'link', 'sha256': installer.digest((source / 'LICENSE').read_bytes())}
    lock_path.write_text(json.dumps(lock))
    staged = home / 'staged'
    with pytest.raises(installer.InstallError, match='unsafe upstream asset'):
        installer.materialize(lock, {'fixture': source}, staged)


def test_operation_lock_prevents_concurrent_writer(setup):
    home, _, _, _, args, supplied = setup
    home.mkdir()
    mutex = home / installer.MUTEX
    mutex.write_text('another process')
    assert installer.main(['install', *args, *supplied, '--apply']) == 1
    assert mutex.read_text() == 'another process'
    assert not (home / installer.MANIFEST).exists()


def test_real_lock_preserves_required_layout_and_safe_loaders():
    lock, _ = installer.read_lock()
    packages = {p['name']: p for p in lock['packages']}
    assert set(packages) == {'diagram-design', 'security-audit', 'incremental-implementation',
                             'test-driven-development', 'debugging-and-error-recovery',
                             'code-simplification', 'impeccable', 'polish'}
    assert 'upstream/references/definition-of-done.md' in packages['incremental-implementation']['files']
    assert 'upstream/references/testing-patterns.md' in packages['test-driven-development']['files']
    assert 'upstream/skills/security-audit/validate-findings.cjs' in packages['security-audit']['files']
    assert 'upstream/skills/security-audit/validate-coverage-ledger.cjs' in packages['security-audit']['files']
    assert 'upstream/skills/diagram-design/scripts/self_check.py' in packages['diagram-design']['files']
    assert 'INSTRUCTION-ONLY MODE' in packages['impeccable']['files']['SKILL.md']['content']
    assert packages['polish']['requires'] == ['impeccable']
    # These notices cover content in installed references/assets, not just the upstream root license.
    assert packages['impeccable']['files']['upstream/NOTICE.md']['source'] == 'NOTICE.md'
    assert packages['diagram-design']['files']['upstream/THIRD_PARTY_LICENSES.md']['source'] == 'THIRD_PARTY_LICENSES.md'
    for name, package in packages.items():
        assert not any('/hooks/' in path or '/agents/' in path for path in package['files'])
        if name != 'polish':
            assert 'upstream/LICENSE' in package['files']


def test_local_content_filter_is_not_executed(setup):
    home, source, _, _, args, supplied = setup
    git(source, 'config', 'filter.surprise.clean', 'echo SHOULD_NOT_RUN')
    assert installer.main(['install', *args, *supplied, '--apply']) == 1
    assert not (home / installer.MANIFEST).exists()


def test_unowned_symlink_mutex_is_preserved(setup, tmp_path):
    home, _, _, _, args, supplied = setup
    home.mkdir()
    outside = tmp_path / 'outside-lock'
    outside.write_text('owner')
    mutex = home / installer.MUTEX
    try:
        mutex.symlink_to(outside)
    except OSError:
        pytest.skip('Host does not allow file symlinks')
    assert installer.main(['install', *args, *supplied, '--apply']) == 1
    assert mutex.is_symlink()
    assert outside.read_text() == 'owner'
