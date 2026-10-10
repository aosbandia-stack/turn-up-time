"""Whole-generation integrity and interrupted cutover tests; no network or live home."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('provider_generation_test', ROOT / 'scripts/provider_install.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    content = '# Complete fixture instructions\n'
    lock = {'schema_version': 1, 'repositories': {'fixture': {
        'url': 'https://github.com/example/fixture.git', 'commit': 'a' * 40}},
        'packages': [{'name': name, 'repository': 'fixture', 'files': {
            'SKILL.md': {'content': content, 'sha256': p.digest(content.encode())},
            'references/required.md': {'content': 'Required context', 'sha256': p.digest(b'Required context')}}}
            for name in ['first', 'second']]}
    lock_path = tmp_path / 'lock.json'
    lock_path.write_text(json.dumps(lock))
    registry = tmp_path / 'registry.json'
    registry.write_text('{"schema_version":3,"capabilities":{}}')
    monkeypatch.setattr(p, 'LOCK', lock_path)
    monkeypatch.setattr(p, 'REGISTRY', registry)
    monkeypatch.setattr(p, 'fetch_blob', lambda *args: pytest.fail('Fixture unexpectedly fetched source'))
    home = tmp_path / 'home'
    home.mkdir()
    legacy = home / 'skills/old-provider/SKILL.md'
    legacy.parent.mkdir(parents=True)
    legacy.write_text('Existing user package')
    (home / 'unmanaged.txt').write_text('User notes')
    return home, lock_path


def stage(home, name):
    return p.stage_generation(home, name, {}, True)


def test_full_generation_roundtrip_preserves_legacy_and_unmanaged(bundle):
    home, _ = bundle
    stage(home, 'one')
    assert not (home / p.SELECTION).exists()
    p.select_generation(home, 'one', True)
    stage(home, 'two')
    p.select_generation(home, 'two', True)
    assert p.read_selection(home)['generation_id'] == 'two'
    p.select_generation(home, None, True, rollback=True)
    assert p.read_selection(home)['generation_id'] == 'one'
    assert (home / 'skills/old-provider/SKILL.md').read_text() == 'Existing user package'
    assert (home / 'unmanaged.txt').read_text() == 'User notes'
    assert p.verify_generation(home, 'two')['generation_id'] == 'two'


def test_first_selection_rolls_back_to_no_managed_generation(bundle):
    home, _ = bundle
    stage(home, 'one')
    p.select_generation(home, 'one', True)
    p.select_generation(home, None, True, rollback=True)
    assert p.read_selection(home)['generation_id'] is None
    assert (home / 'skills/old-provider/SKILL.md').exists()


@pytest.mark.parametrize('mutation', ['missing', 'edited', 'extra', 'manifest', 'registry'])
def test_modified_selected_generation_blocks_cutover_and_rollback(bundle, mutation):
    home, _ = bundle
    stage(home, 'one'); stage(home, 'two')
    p.select_generation(home, 'one', True)
    before = (home / p.SELECTION).read_bytes()
    base = p.generation_path(home, 'one')
    target = base / 'skills/first/references/required.md'
    if mutation == 'missing':
        target.unlink()
    elif mutation == 'edited':
        target.write_text('local changes')
    elif mutation == 'extra':
        (target.parent / 'unmanaged.md').write_text('Do not remove')
    elif mutation == 'registry':
        (base / 'registry.json').write_text('{}')
    else:
        (base / 'generation.json').write_text('{}')
    with pytest.raises(p.InstallError):
        p.select_generation(home, 'two', True)
    with pytest.raises(p.InstallError):
        p.select_generation(home, None, True, rollback=True)
    assert (home / p.SELECTION).read_bytes() == before


def test_modified_previous_generation_blocks_rollback_as_unit(bundle):
    home, _ = bundle
    stage(home, 'one'); stage(home, 'two')
    p.select_generation(home, 'one', True); p.select_generation(home, 'two', True)
    before = (home / p.SELECTION).read_bytes()
    (p.generation_path(home, 'one') / 'skills/second/SKILL.md').write_text('user edit')
    with pytest.raises(p.InstallError):
        p.select_generation(home, None, True, rollback=True)
    assert (home / p.SELECTION).read_bytes() == before


def test_interrupted_pointer_replace_keeps_old_generation_and_blocks_retry(bundle, monkeypatch):
    home, _ = bundle
    stage(home, 'one'); stage(home, 'two')
    p.select_generation(home, 'one', True)
    before = (home / p.SELECTION).read_bytes()
    def fail(*args):
        raise OSError('injected power interruption before atomic replace')
    monkeypatch.setattr(p.os, 'replace', fail)
    with pytest.raises(OSError):
        p.select_generation(home, 'two', True)
    assert (home / p.SELECTION).read_bytes() == before
    assert p.read_selection(home)['generation_id'] == 'one'
    assert (home / (p.SELECTION + '.tmp')).exists()
    with pytest.raises(FileExistsError):
        p.select_generation(home, 'two', True)


def test_interrupted_stage_never_exposes_partial_generation(bundle, monkeypatch):
    home, _ = bundle
    def fail(lock, staged):
        (staged / 'partial').write_text('incomplete')
        raise OSError('injected interrupted download')
    monkeypatch.setattr(p, 'materialize_blobs', fail)
    with pytest.raises(OSError):
        stage(home, 'bad')
    assert not p.generation_path(home, 'bad').exists()
    assert not (home / p.SELECTION).exists()


@pytest.mark.parametrize('name', ['../escape', 'Bad', 'x/y', 'x\\y', '', 'a' * 81])
def test_generation_path_rejects_escape(bundle, name):
    with pytest.raises(p.InstallError):
        stage(bundle[0], name)


@pytest.mark.parametrize('name', ['skill.md', 'references'])
def test_case_and_file_directory_collisions_fail_before_stage(bundle, name):
    home, lock_path = bundle
    lock = json.loads(lock_path.read_text())
    lock['packages'][0]['files'][name] = {'content': 'x', 'sha256': p.digest(b'x')}
    lock_path.write_text(json.dumps(lock))
    with pytest.raises(p.InstallError):
        stage(home, 'bad')
    assert not p.generation_path(home, 'bad').exists()


def test_catalog_complete_and_external_readiness_separate():
    lock, _ = p.read_lock()
    names = {package['name'] for package in lock['packages']}
    assert {'rea', 'serena', 'context7', 'backend-architect', 'database-architect',
            'database-optimizer', 'ponytail', 'ponytail-review', 'typesafe-ai',
            'vercel-react-best-practices', 'gstack-qa-only', '21st-ui',
            'impeccable', 'polish', 'security-audit'} <= names
    registry = json.loads(p.REGISTRY.read_text())['capabilities']
    for name in ['reference-app-analysis', 'code-symbol-analysis', 'dependency-docs',
                 'fast-triage-decision', 'browser-qa', '21st-catalog', '21st-generate']:
        assert registry[name]['provider_kind'] == 'external'
        assert registry[name]['readiness_requirements']
    qa = next(package for package in lock['packages'] if package['name'] == 'gstack-qa-only')
    assert {'sections/exploratory.md', 'sections/reporting.md', 'sections/browser-setup.md',
            'sections/scope.md', 'sections/system-functional.md', 'sections/qa-patterns.md',
            'browse/SKILL.md', 'browse/sections/command-list.md', 'qa/references/issue-taxonomy.md',
            'templates/functional-report-template.md', 'templates/qa-report-template.md'} <= qa['files'].keys()


def test_registry_schema_and_dependencies():
    import jsonschema
    registry = json.loads(p.REGISTRY.read_text())
    schema = json.loads((ROOT / '.claude/schemas/capability-registry.schema.json').read_text())
    jsonschema.validate(registry, schema)
    for entry in registry['capabilities'].values():
        assert set(entry['requires']) <= registry['capabilities'].keys()


def test_frontend_and_core_closures_have_locked_instruction_packages():
    lock, _ = p.read_lock()
    packages = {package['name']: package for package in lock['packages']}
    registry = json.loads(p.REGISTRY.read_text())['capabilities']
    pending = [name for name in registry if name.startswith(('frontend-', 'ui-'))]
    pending += ['workflow-evals', 'repository-cleanup', 'irreversible-write']
    visited = set()
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        entry = registry[name]
        assert entry['provider'] in packages
        pending.extend(entry['requires'])
    browser = registry['browser-e2e']
    assert browser['provider'] == 'gstack-qa-only'
    assert browser['provider_kind'] == 'external' and browser['authority'] == 'assurance'
    assert set(browser['produces']) == {'e2e-results', 'screenshots', 'trace'}
    assert set(browser['readiness_requirements']) >= {'tool_access', 'browser_runtime', 'isolated_output'}
    for name in ['eval-harness', 'swiper-dont-swpe-me', 'guard-before-write']:
        package = packages[name]
        repo = lock['repositories'][package['repository']]
        assert repo['kind'] == 'local-snapshot' and 'commit' not in repo and 'url' not in repo
        record = package['files']['SKILL.md']
        assert record['content'].encode() == (ROOT / record['source']).read_bytes()
        assert p.repository_source_ref(repo).startswith('local-snapshot:.claude/skills@sha256:')


@pytest.mark.parametrize('mutation', ['revision', 'network-origin', 'source-escape', 'nonembedded'])
def test_local_snapshot_cannot_hide_wrong_content_or_network_origin(tmp_path, mutation):
    lock, _ = p.read_lock()
    lock = json.loads(json.dumps(lock))
    repo = lock['repositories']['turn-up-time-core']
    package = next(item for item in lock['packages'] if item['name'] == 'eval-harness')
    if mutation == 'revision':
        repo['revision'] = 'sha256:' + '0' * 64
    elif mutation == 'network-origin':
        repo['url'] = 'https://unapproved.invalid/code'
    elif mutation == 'source-escape':
        package['files']['SKILL.md']['source'] = '../../secrets'
    else:
        package['files']['SKILL.md'].pop('content')
    path = tmp_path / 'invalid-lock.json'
    path.write_text(json.dumps(lock))
    with pytest.raises(p.InstallError):
        p.read_lock(path)


def test_source_doc_validator_excludes_exact_generated_runtime_only(tmp_path):
    spec = importlib.util.spec_from_file_location('source_docs', ROOT / '.claude/scripts/validate_repo.py')
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    for name in ['.claude/runtime/generation/upstream/README.md',
                 '.claude/runtime-not-generated/README.md', 'docs/runtime/README.md',
                 'scripts/provider_adapters/example/SKILL.md', '.claude/skills/example/SKILL.md']:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('[required](missing.md)')
    errors = validator.markdown_link_errors(tmp_path)
    assert len(errors) == 4
    assert not any('generation' in error for error in errors)
    assert any('provider_adapters' in error for error in errors)
    assert any('runtime-not-generated' in error for error in errors)
    # Repairing actual source links clears those errors; generated files remain untouched.
    for name in ['.claude/runtime-not-generated', 'docs/runtime',
                 'scripts/provider_adapters/example', '.claude/skills/example']:
        (tmp_path / name / 'missing.md').write_text('Present')
    assert validator.markdown_link_errors(tmp_path) == []
