"""Catch a saved skill silently disappearing from TUT routing or installed Codex payloads."""
import importlib.util
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load('ui_craft_validator', ROOT / '.claude/scripts/validate_repo.py')
installer = load('ui_craft_installer', ROOT / 'scripts/codex_installer.py')


@pytest.fixture
def routed_source(tmp_path):
    for relative in validator.UI_CRAFT_ROUTES:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    shutil.copytree(ROOT / '.claude/skills/reference-to-reality',
                    tmp_path / '.claude/skills/reference-to-reality')
    return tmp_path


def test_real_ui_routes_are_complete():
    assert validator.ui_craft_routing_errors(ROOT) == []


@pytest.mark.parametrize('route', validator.UI_CRAFT_ROUTES)
def test_seeded_missing_stage_route_is_detected(routed_source, route):
    path = routed_source / route
    target = validator.UI_CRAFT_ROUTES[route]
    path.write_text(path.read_text().replace(f']({target})', ''))
    assert validator.ui_craft_routing_errors(routed_source) == [f'UI_CRAFT_ROUTE_MISSING: {route}']


def test_seeded_missing_procedure_is_detected(routed_source):
    (routed_source / '.claude/skills/reference-to-reality/SKILL.md').unlink()
    errors = validator.ui_craft_routing_errors(routed_source)
    assert len(errors) == len(validator.UI_CRAFT_ROUTES)
    assert all(error.startswith('UI_CRAFT_PROCEDURE_MISSING:') for error in errors)


def test_real_codex_snapshot_wrapper_and_role_link_context(tmp_path):
    generation = tmp_path / 'generation'
    source = generation / 'source'
    installer.snapshot(ROOT, source)
    skill = Path('.claude/skills/reference-to-reality')
    # Supporting references survive packaging byte for byte, not just SKILL.md.
    for original in (ROOT / skill).rglob('*'):
        if original.is_file():
            assert (source / original.relative_to(ROOT)).read_bytes() == original.read_bytes()
    assert validator.ui_craft_routing_errors(source) == []
    meta = installer.metadata(source, Path(sys.executable))
    generated, _ = installer.generated_files(tmp_path / 'codex', generation, Path(sys.executable), meta)
    wrapper = generated['skills/tut-reference-to-reality/SKILL.md'].decode()
    assert str(source / skill / 'SKILL.md') in wrapper
    contract = generated['workflows/turn-up-time/CODEX.md'].decode()
    assert '`/reference-to-reality` → `$tut-reference-to-reality`' in contract
    for role in ('frontend_experience_researcher', 'implementation_engineer', 'ux_accessibility_reviewer'):
        text = generated[f'agents/tut_{role}.toml'].decode()
        assert 'reference-to-reality/SKILL.md' in text
        assert f'Resolve relative links below from {source / ".claude/agents"}/' in text
    # The existing Claude recursive copy preserves the same relative procedure/reference layout.
    claude_installer = (ROOT / 'scripts/install.ps1').read_text()
    assert "Source = Join-Path $RepoRoot '.claude\\skills'; Target = Join-Path $ClaudeHome 'skills'" in claude_installer
    assert 'Get-ChildItem -Path $entry.Source -Recurse -File' in claude_installer
