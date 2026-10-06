"""Real UI selector expansion and target gates, without pretending providers ran."""
import copy
import json
import subprocess
import sys

import pytest

from .test_completion_contracts import (BUILD, CLAUDE, ROOT, edit, make_project, proof, read,
                                        ready_provider, ui_surface, write)
from resolve_capabilities import resolve
from turn_up_time_graph.topology import Stage
from turn_up_time_graph.validation import TransitionError, validate_project_for_target


def registry():
    return read(CLAUDE / 'capabilities/registry.json')['capabilities']


def selected(project, surface):
    return resolve([], registry(), [project / '.claude/skills'],
                   readiness=read(project / 'capability-readiness.json'), project=project,
                   environment='local-test', build_identity=BUILD, require_use=True, ui_surfaces=[surface])


@pytest.mark.parametrize('purpose', ['operate','persuade','read','experience'])
def test_purposes_use_real_required_capabilities_and_target_validator(tmp_path, purpose):
    project = make_project(tmp_path, ui=True)
    surface = ui_surface(purpose=purpose)
    edit(project, 'definition-of-good.json', lambda value:value['ui'].update(surfaces=[surface]))
    edit(project, 'tickets/EXAMPLE-001.json', lambda value:value.update(required_capabilities=['ui-'+purpose,'browser-e2e']))
    code, result = selected(project, surface)
    assert code == 0, result
    assert set(result['selected']) == {'ui-'+purpose, 'browser-e2e'}
    validate_project_for_target(ROOT, project, Stage.INTEGRATION)


def flagged(project, flag):
    edit(project, 'definition-of-good.json', lambda value:value['ui']['surfaces'][0].update(flags=[flag]))
    edit(project, 'tickets/EXAMPLE-001.json', lambda value:value['required_capabilities'].append(flag))
    ready_provider(project, flag, '21st-ui', {'tool_access':'PASS','entitlement':'PASS'})


@pytest.mark.parametrize('flag', ['21st-catalog','21st-generate'])
def test_selected_21st_requires_real_receipts_and_cli_agrees(tmp_path, flag):
    project = make_project(tmp_path, ui=True)
    flagged(project, flag)
    validate_project_for_target(ROOT, project, Stage.INTEGRATION)
    result = subprocess.run([sys.executable, str(CLAUDE / 'scripts/resolve_capabilities.py'),
        '--ui-platform','web','--ui-purpose','operate','--ui-stack','react-tailwind','--ui-flag',flag,
        '--user-registry',str(tmp_path/'none'),'--provider-root',str(project/'.claude/skills'),
        '--readiness',str(project/'capability-readiness.json'),'--project',str(project),
        '--environment','local-test','--build-identity',BUILD,'--require-use'],capture_output=True,text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert set(json.loads(result.stdout)['ui_required']) == {'ui-operate','browser-e2e',flag}
    edit(project, 'capability-readiness.json', lambda value:value.update(usage=[row for row in value['usage'] if row['capability'] != flag]))
    with pytest.raises(TransitionError, match='ACTUAL_USE_PROOF_REQUIRED'):
        validate_project_for_target(ROOT, project, Stage.INTEGRATION)


@pytest.mark.parametrize('mutation,expected', [
    ('unknown-flag','UI_SELECTOR_UNAVAILABLE'),('incompatible-stack','UI_STACK_INCOMPATIBLE'),
    ('missing-entitlement','READINESS_CHECK_REQUIRED:entitlement'),('failed-tool','READINESS_CHECK_REQUIRED:tool_access'),
    ('missing-provider','REQUIRED_PROVIDER_MISSING'),('missing-readiness','READINESS_PROOF_REQUIRED'),
    ('flag-not-ticketed','UI_TICKET_CAPABILITY_COVERAGE_MISSING'),('unknown-purpose','INVALID'),
    ('missing-surface-route','UI_SURFACE_ROUTE_COVERAGE_MISMATCH'),
])
def test_ui_flags_cannot_disappear_at_the_real_gate(tmp_path, mutation, expected):
    project = make_project(tmp_path, ui=True)
    flagged(project, '21st-generate')
    if mutation == 'unknown-flag': edit(project,'definition-of-good.json',lambda v:v['ui']['surfaces'][0].update(flags=['made-up']))
    elif mutation == 'incompatible-stack': edit(project,'definition-of-good.json',lambda v:v['ui']['surfaces'][0].update(stack='swiftui'))
    elif mutation == 'missing-entitlement': edit(project,'capability-readiness.json',lambda v:v['receipts'][-1].update(checks={'tool_access':'PASS'}))
    elif mutation == 'failed-tool': edit(project,'capability-readiness.json',lambda v:v['receipts'][-1]['checks'].update(tool_access='FAIL'))
    elif mutation == 'missing-provider': (project/'.claude/skills/21st-ui/SKILL.md').unlink()
    elif mutation == 'missing-readiness': edit(project,'capability-readiness.json',lambda v:v.update(receipts=v['receipts'][:-1]))
    elif mutation == 'flag-not-ticketed': edit(project,'tickets/EXAMPLE-001.json',lambda v:v.update(required_capabilities=['ui-operate','browser-e2e']))
    elif mutation == 'unknown-purpose': edit(project,'definition-of-good.json',lambda v:v['ui']['surfaces'][0].update(purpose='unknown'))
    elif mutation == 'missing-surface-route': edit(project,'definition-of-good.json',lambda v:v['ui']['surfaces'][0].update(routes=['/different']))
    with pytest.raises(TransitionError, match=expected):
        validate_project_for_target(ROOT, project, Stage.INTEGRATION)


def test_native_requires_a_real_project_assurance_adapter(tmp_path):
    project = make_project(tmp_path, ui=True)
    surface = ui_surface(platform='native', stack='swiftui')
    edit(project,'definition-of-good.json',lambda v:v['ui'].update(surfaces=[surface]))
    with pytest.raises(TransitionError, match='NATIVE_ASSURANCE_REQUIRED'):
        validate_project_for_target(ROOT, project, Stage.BUILD)
    adapter = copy.deepcopy(registry()['browser-e2e'])
    adapter.pop('ui_selector')
    adapter.update(provider='fixture-native-runner',supported_platforms=['native'],compatible_stacks=['swiftui'])
    write(project/'capability-registry.json',{'schema_version':3,'capabilities':{'native-ui-assurance':adapter}})
    surface['verification_capabilities'] = ['native-ui-assurance']
    edit(project,'definition-of-good.json',lambda v:v['ui'].update(surfaces=[surface]))
    edit(project,'tickets/EXAMPLE-001.json',lambda v:v.update(required_capabilities=['ui-operate','native-ui-assurance']))
    ready_provider(project,'native-ui-assurance','fixture-native-runner')
    merged = {**registry(),'native-ui-assurance':adapter}
    code, result = resolve([],merged,[project/'.claude/skills'],ui_surfaces=[surface],project=project,
        readiness=read(project/'capability-readiness.json'),environment='local-test',build_identity=BUILD,require_use=True)
    assert code == 0, result
    assert set(result['selected']) == {'ui-operate','native-ui-assurance'}
    validate_project_for_target(ROOT,project,Stage.INTEGRATION)
    edit(project,'capability-registry.json',lambda v:v['capabilities']['native-ui-assurance'].update(provider_kind='instruction-only'))
    with pytest.raises(TransitionError,match='UI_ASSURANCE_ADAPTER_INVALID'):
        validate_project_for_target(ROOT,project,Stage.INTEGRATION)


def test_polish_and_project_provider_override_remain_instruction_only(tmp_path):
    project = make_project(tmp_path,ui=True)
    capabilities=registry()
    custom=copy.deepcopy(capabilities['ui-operate'])
    custom['provider']='incumbent-design'
    write(project/'capability-registry.json',{'schema_version':3,'capabilities':{'ui-operate':custom}})
    (project/'.claude/skills/impeccable/SKILL.md').unlink()
    for provider in ('incumbent-design','polish'):
        path=project/'.claude/skills'/provider/'SKILL.md'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('# Fixture installed instructions\n')
    edit(project,'definition-of-good.json',lambda v:v['ui']['surfaces'][0].update(flags=['polish']))
    edit(project,'tickets/EXAMPLE-001.json',lambda v:v['required_capabilities'].append('ui-polish'))
    validate_project_for_target(ROOT,project,Stage.INTEGRATION)


@pytest.mark.parametrize('mutation,expected', [('instruction-only','UI_EXTERNAL_PROVIDER_REQUIRED'),
                                             ('dropped-entitlement','READINESS_CHECK_REQUIRED:entitlement')])
def test_override_cannot_relabel_external_generation_as_installed_instructions(tmp_path,mutation,expected):
    project=make_project(tmp_path,ui=True)
    flagged(project,'21st-generate')
    override=copy.deepcopy(registry()['21st-generate'])
    if mutation=='instruction-only': override['provider_kind']='instruction-only'
    else:
        override.pop('readiness_requirements')
        edit(project,'capability-readiness.json',lambda v:v['receipts'][-1].update(checks={'tool_access':'PASS'}))
    write(project/'capability-registry.json',{'schema_version':3,'capabilities':{'21st-generate':override}})
    with pytest.raises(TransitionError,match=expected):
        validate_project_for_target(ROOT,project,Stage.INTEGRATION)


def test_new_direction_requires_comparables_but_supplied_evidence_can_be_offline(tmp_path):
    project=make_project(tmp_path,ui=True)
    edit(project,'definition-of-good.json',lambda v:v['ui']['surfaces'][0].update(change_scope='NEW'))
    with pytest.raises(TransitionError,match='UI_COMPARABLE_RESEARCH_REQUIRED'):
        validate_project_for_target(ROOT,project,Stage.BUILD)
    assets=read(project/proof(project,'supplied-comparable'))['evidence_refs']
    row={'source':'User supplied comparable capture','basis':'SUPPLIED','observation':'Action hierarchy is explicit in the supplied view.',
         'disposition':'ADAPT','rationale':'Retain project typography and use its action grouping.','guide_ref':'architecture.md#design','evidence_refs':assets}
    edit(project,'definition-of-good.json',lambda v:v['ui']['surfaces'][0].update(research_disposition='COMPARABLES',research=[row]))
    validate_project_for_target(ROOT,project,Stage.BUILD)
    (project/assets[0]['path']).write_text('changed capture')
    with pytest.raises(TransitionError,match='EVIDENCE_HASH_MISMATCH'):
        validate_project_for_target(ROOT,project,Stage.BUILD)


@pytest.mark.parametrize('mutation,expected', [
    ('instruction-only','UI_ASSURANCE_ADAPTER_INVALID'),
    ('wrong-authority','UI_ASSURANCE_ADAPTER_INVALID'),
    ('wrong-platform','UI_ASSURANCE_ADAPTER_INVALID'),
    ('removed-selector-and-ticket','UI_TICKET_CAPABILITY_COVERAGE_MISSING'),
])
def test_web_assurance_override_cannot_remove_required_execution(tmp_path, mutation, expected):
    project = make_project(tmp_path, ui=True)
    override = copy.deepcopy(registry()['browser-e2e'])
    if mutation == 'instruction-only': override['provider_kind'] = 'instruction-only'
    elif mutation == 'wrong-authority': override['authority'] = 'production'
    elif mutation == 'wrong-platform': override['supported_platforms'] = ['native']
    else:
        override.pop('ui_selector')
        edit(project, 'tickets/EXAMPLE-001.json', lambda value:value.update(required_capabilities=['ui-operate']))
    write(project / 'capability-registry.json', {'schema_version':3,'capabilities':{'browser-e2e':override}})
    (project / 'capability-readiness.json').unlink()
    with pytest.raises(TransitionError, match=expected):
        validate_project_for_target(ROOT, project, Stage.DONE)


@pytest.mark.parametrize('transitive', [False, True])
def test_ticket_selected_generation_requires_a_declared_surface_binding(tmp_path, transitive):
    project = make_project(tmp_path, ui=True)
    edit(project, 'definition-of-good.json', lambda value:value['ui']['surfaces'][0].update(stack='vue-css'))
    capability = '21st-generate'
    if transitive:
        capability = 'generation-wrapper'
        wrapper = copy.deepcopy(registry()['workflow-evals'])
        wrapper['requires'] = ['21st-generate']
        write(project / 'capability-registry.json', {'schema_version':3,'capabilities':{capability:wrapper}})
    edit(project, 'tickets/EXAMPLE-001.json', lambda value:value['required_capabilities'].append(capability))
    ready_provider(project, '21st-generate', '21st-ui', {'tool_access':'PASS','entitlement':'PASS'})
    with pytest.raises(TransitionError, match='UI_CAPABILITY_SURFACE_REQUIRED'):
        validate_project_for_target(ROOT, project, Stage.DONE)


def test_web_provider_can_be_substituted_without_a_selector(tmp_path):
    project = make_project(tmp_path, ui=True)
    override = copy.deepcopy(registry()['browser-e2e'])
    override.pop('ui_selector')
    override['provider'] = 'project-browser-runner'
    write(project / 'capability-registry.json', {'schema_version':3,'capabilities':{'browser-e2e':override}})
    (project / '.claude/skills/e2e-testing/SKILL.md').unlink()
    ready_provider(project, 'browser-e2e', 'project-browser-runner')
    validate_project_for_target(ROOT, project, Stage.DONE)
    merged = {**registry(), 'browser-e2e':override}
    code, result = resolve([], merged, [project / '.claude/skills'], readiness=read(project / 'capability-readiness.json'),
        project=project, environment='local-test', build_identity=BUILD, require_use=True, ui_surfaces=[ui_surface()])
    assert code == 0, result
    assert 'browser-e2e' in result['ui_required']
    assert next(row for row in result['plan'] if row['capability'] == 'browser-e2e')['provider'] == 'project-browser-runner'


@pytest.mark.parametrize('mutation,expected', [
    ('instruction-only','UI_EXTERNAL_PROVIDER_REQUIRED'),
    ('tool-access','READINESS_CHECK_REQUIRED:tool_access'),
    ('entitlement','READINESS_CHECK_REQUIRED:entitlement'),
])
def test_canonical_generation_minima_survive_removed_selector(tmp_path, mutation, expected):
    project = make_project(tmp_path, ui=True)
    flagged(project, '21st-generate')
    override = copy.deepcopy(registry()['21st-generate'])
    override.pop('ui_selector')
    override.pop('readiness_requirements')
    if mutation == 'instruction-only': override['provider_kind'] = 'instruction-only'
    else:
        check = mutation.replace('-', '_')
        edit(project, 'capability-readiness.json', lambda value:value['receipts'][-1]['checks'].pop(check))
    write(project / 'capability-registry.json', {'schema_version':3,'capabilities':{'21st-generate':override}})
    with pytest.raises(TransitionError, match=expected):
        validate_project_for_target(ROOT, project, Stage.DONE)


def test_supported_project_stack_adapter_survives_removed_selector(tmp_path):
    project = make_project(tmp_path, ui=True)
    flagged(project, '21st-generate')
    edit(project, 'definition-of-good.json', lambda value:value['ui']['surfaces'][0].update(stack='vue-css'))
    override = copy.deepcopy(registry()['21st-generate'])
    override.pop('ui_selector')
    override.update(compatible_stacks=['vue-css'], stack_adapter_ref='evidence/reviewed-adapter.md')
    (project / 'evidence/reviewed-adapter.md').write_text('Fixture reviewed adapter maps output into the incumbent Vue components.\n')
    write(project / 'capability-registry.json', {'schema_version':3,'capabilities':{'21st-generate':override}})
    validate_project_for_target(ROOT, project, Stage.DONE)
    (project / 'evidence/reviewed-adapter.md').unlink()
    with pytest.raises(TransitionError, match='MISSING_EVIDENCE'):
        validate_project_for_target(ROOT, project, Stage.DONE)


def test_web_generation_is_not_compared_to_unrelated_native_surface(tmp_path):
    project = make_project(tmp_path, ui=True)
    flagged(project, '21st-generate')
    native = ui_surface(id='native', platform='native', stack='swiftui', routes=['native/items'],
                        verification_capabilities=['native-ui-assurance'])
    edit(project, 'definition-of-good.json', lambda value:(value['ui']['surfaces'].append(native),
         value['ui']['route_states'].append({'route':'native/items','states':['loading','empty','error','success']})))
    adapter = copy.deepcopy(registry()['browser-e2e'])
    adapter.pop('ui_selector')
    adapter.update(provider='fixture-native-runner', supported_platforms=['native'], compatible_stacks=['swiftui'])
    write(project / 'capability-registry.json', {'schema_version':3,'capabilities':{'native-ui-assurance':adapter}})
    ready_provider(project, 'native-ui-assurance', 'fixture-native-runner')
    edit(project, 'tickets/EXAMPLE-001.json', lambda value:value['required_capabilities'].append('native-ui-assurance'))
    evidence = [proof(project,'ui:native/items:desktop'), proof(project,'ui:native/items:mobile'), proof(project,'keyboard:native/items')]
    edit(project, 'closeout/terminal-state.json', lambda value:value['evidence_refs'].extend(evidence))
    validate_project_for_target(ROOT, project, Stage.DONE)
