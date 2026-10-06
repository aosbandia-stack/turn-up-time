"""Executable controls for the public artifact contracts and real target validator."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / '.claude'
sys.path.insert(0, str(CLAUDE / 'scripts'))
from resolve_capabilities import resolve
from validate_project import validate_transition
from turn_up_time_graph.topology import Stage
from turn_up_time_graph.workspace import build_identity
from turn_up_time_graph.validation import TransitionError, validate_project_for_target

BUILD = build_identity(ROOT)
STAMP = '2026-01-01T00:00:00Z'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def edit(project, name, change):
    value = read(project / name)
    change(value)
    write(project / name, value)


def example(name):
    return read(CLAUDE / 'templates' / name)


def proof(project, identifier, context=None):
    filename = identifier.replace('/', '_').replace(':', '_')
    output = project / 'receipts' / (filename + '.txt')
    output.parent.mkdir(exist_ok=True)
    output.write_text('Fixture output for ' + identifier + '\n')
    asset = {'path': str(output.relative_to(project)), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
    value = {'schema_version':1, 'project_id':project.name, 'build_identity':BUILD, 'check_id':identifier, 'status':'PASS', 'checked_at':STAMP, 'evidence_refs':[asset]}
    if context:
        value['context'] = context
    ref = 'receipts/' + filename + '.json'
    write(project / ref, value)
    return ref


def instruction_proof(project, baseline=BUILD):
    source = (CLAUDE / 'skills/swiper-dont-swpe-me/SKILL.md').resolve()
    reference = proof(project, 'cleanup-instructions')
    receipt = read(project / reference)
    snapshot = project / receipt['evidence_refs'][0]['path']
    snapshot.write_bytes(source.read_bytes())
    digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    receipt['build_identity'] = baseline
    receipt['evidence_refs'][0]['sha256'] = digest
    write(project / reference, receipt)
    return {'source_path': str(source), 'sha256': digest, 'receipt_ref': reference}


def make_project(tmp_path, ui=False):
    project = tmp_path / 'example-project'
    project.mkdir()
    ledger = example('project-ledger.example.json')
    ledger.update(profile='lite', build_identity=BUILD)
    write(project / 'project-ledger.json', ledger)
    intake = example('intake-readiness.json')
    intake.update(status='READY', primary_user='maintainer', primary_job='verify workflow', desired_outcome='honest completion', product_boundary='fixture')
    write(project / 'intake-readiness.json', intake)
    for lane in ('product','combined-engineering'):
        pack = example('evidence-pack.example.json')
        pack['lane'] = lane
        write(project / 'evidence' / (lane + '.json'), pack)
    write(project / 'evidence/premise-verdict.json', example('premise-verdict.example.json'))
    (project / 'architecture.md').write_text('# Behavior\nThe command validates input and persists one result, or returns a recoverable error.\n# Layout\nThe maintained entry point is src/example.ts; generated output is ignored.\n# Design\nReuse one shared component system across all routes.\n')
    dog = example('definition-of-good.example.json')
    dog.update(status='APPROVED', approved_by='fixture-human', approved_at=STAMP)
    if ui:
        dog['ui'] = {'applicable':True, 'reason':'Product interface is in scope.', 'design_reference':'architecture.md#design', 'component_owner':'frontend-owner', 'shared_components':['Button','FormField'], 'route_states':[{'route':'/items','states':['loading','empty','error','success']}], 'viewports':['desktop','mobile'], 'keyboard_expectations':['Tab through the form and submit with Enter.'], 'first_slice_journey_id':'JRN-001'}
    write(project / 'definition-of-good.json', dog)
    trace = example('traceability.example.json')
    trace['journeys'][0]['evidence_refs'] = [proof(project,'JRN-001')]
    write(project / 'traceability.json', trace)
    ticket = example('ticket.example.json')
    ticket['status'] = 'EVIDENCE_GREEN'
    ticket['required_capabilities'] = ['workflow-evals']
    ticket['acceptance_checks'][0]['evidence'] = proof(project,'CHK-001')
    check_ref = ticket['acceptance_checks'][0]['evidence']
    ticket['build_receipt'] = {'build_identity':BUILD,'changed_files':['src/example.ts'],
        'check_results':[{'check_id':'CHK-001','status':'PASS','build_identity':BUILD,
                          'evaluator_role':'assurance','evaluator_id':'fixture-independent-verifier',
                          'evidence_ref':check_ref,'evidence_sha256':hashlib.sha256((project/check_ref).read_bytes()).hexdigest()}],
        'completed_at':STAMP}
    write(project / 'tickets/EXAMPLE-001.json', ticket)
    for phase in ('pre','post'):
        seam = example(f'seam-verdict.{phase}-build.example.json')
        seam['build_identity'] = BUILD if phase == 'post' else None
        write(project / 'integration' / (phase + '-build-verdict.json'), seam)
    terminal = example('terminal-state.example.json')
    terminal.update(build_identity=BUILD, checked_at=STAMP, evidence_refs=[proof(project,'JRN-001')])
    terminal['cleanup'].update(instruction=instruction_proof(project), baseline_identity=BUILD, build_identity=BUILD, actions=[], evidence_refs=[proof(project,'cleanup')], handoff_ref=proof(project,'handoff'))
    terminal['completion'].update(build_identity=BUILD, checked_at=STAMP, handoff_ref=proof(project,'handoff'))
    if ui:
        terminal['evidence_refs'] += [proof(project,'ui:/items:desktop'), proof(project,'ui:/items:mobile'), proof(project,'keyboard:/items')]
    write(project / 'closeout/terminal-state.json', terminal)
    for name in ('production-audit','final-judge'):
        component = example(name + '.example.json')
        component.update(build_identity=BUILD, checked_at=STAMP, evidence_refs=[proof(project,'CHK-001')])
        write(project / 'release' / (name + '.json'), component)
    release = example('release-verdict.example.json')
    release.update(build_identity=BUILD, decided_at=STAMP)
    write(project / 'release/release-verdict.json', release)
    return project


def errors_for(project, stage='DONE'):
    errors = []
    validate_transition(project, stage, errors)
    return errors


@pytest.mark.parametrize('ui',[False,True])
def test_documented_candidate_contract_accepts_ui_and_non_ui(tmp_path, ui):
    project = make_project(tmp_path, ui=ui)
    assert errors_for(project) == []
    result = subprocess.run([sys.executable,str(CLAUDE / 'scripts/validate_project.py'),str(project),'--stage','DONE'],capture_output=True,text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('mutation,expected',[
    ('legacy-definition','MIGRATION_REQUIRED'),
    ('missing-architecture','MISSING_EVIDENCE'),
    ('missing-design','INVALID'),
    ('empty-ui-journeys','INVALID'),
    ('empty-ui-route-state','UI_ROUTE_STATES_INCOMPLETE'),
    ('unknown-first-slice','FIRST_SLICE_JOURNEY_UNKNOWN'),
    ('unknown-design-anchor','UNKNOWN_DESIGN_ANCHOR'),
    ('missing-must','REQUIREMENT_TRACE_COVERAGE_MISMATCH'),
    ('unknown-ticket','NONRECIPROCAL_TICKET'),
    ('unknown-check','UNKNOWN_ACCEPTANCE_CHECK'),
    ('unknown-dependency','UNKNOWN_OR_SELF_DEPENDENCY'),
    ('duplicate-requirement','DUPLICATE_ID'),
    ('source-claim-missing','UNKNOWN_EVIDENCE_CLAIM'),
    ('missing-acceptance-proof','acceptance_checks.0.evidence'),
    ('failed-acceptance-proof','FAILED_EVIDENCE'),
    ('missing-journey-proof','JOURNEY_EVIDENCE_MISSING'),
    ('stale-post-build','BUILD_IDENTITY_MISMATCH'),
    ('stale-cleanup','STALE_CLEANUP_BUILD'),
    ('changed-cleanup-no-reproof','CLEANUP_REPROOF_REQUIRED'),
    ('tampered-cleanup-output','EVIDENCE_HASH_MISMATCH'),
    ('outside-proof','EVIDENCE_OUTSIDE_PROJECT'),
    ('missing-ui-proof','UI_CLOSEOUT_PROOF_MISSING'),
    ('legacy-component-verdict','INVALID'),
    ('conflicting-component-field','INVALID'),
    ('negative-judge','RELEASE_PACKET_MISMATCH'),
    ('wrong-component-build','BUILD_IDENTITY_MISMATCH'),
    ('missing-component-proof','MISSING_EVIDENCE'),
    ('unaccepted-risk','RELEASE_APPROVAL_MISSING'),
    ('missing-completion','COMPLETION_PROOF_REQUIRED'),
    ('overclaimed-completion','CANDIDATE_SCOPE_OVERCLAIM'),
])
def test_false_ready_packets_fail(tmp_path, mutation, expected):
    p = make_project(tmp_path, ui=True)
    if mutation == 'legacy-definition': edit(p,'definition-of-good.json',lambda v:v.update(schema_version=1))
    elif mutation == 'missing-architecture': (p/'architecture.md').unlink()
    elif mutation == 'missing-design': edit(p,'definition-of-good.json',lambda v:v['ui'].update(design_reference=None))
    elif mutation == 'empty-ui-journeys': edit(p,'definition-of-good.json',lambda v:v.update(critical_journeys=[]))
    elif mutation == 'empty-ui-route-state': edit(p,'definition-of-good.json',lambda v:v['ui']['route_states'][0].update(states=['success']))
    elif mutation == 'unknown-first-slice': edit(p,'definition-of-good.json',lambda v:v['ui'].update(first_slice_journey_id='unknown'))
    elif mutation == 'unknown-design-anchor': edit(p,'traceability.json',lambda v:v['requirements'][0].update(design_ref='architecture.md#unknown'))
    elif mutation == 'missing-must': edit(p,'traceability.json',lambda v:v['requirements'][0].update(requirement_id='unknown'))
    elif mutation == 'unknown-ticket':
        edit(p,'definition-of-good.json',lambda v:v['requirements'][0].update(ticket_ids=['unknown']))
        edit(p,'traceability.json',lambda v:v['requirements'][0].update(ticket_ids=['unknown']))
    elif mutation == 'unknown-check': edit(p,'traceability.json',lambda v:v['requirements'][0]['acceptance_checks'][0].update(check_id='unknown'))
    elif mutation == 'unknown-dependency': edit(p,'tickets/EXAMPLE-001.json',lambda v:v.update(dependencies=['unknown']))
    elif mutation == 'duplicate-requirement': edit(p,'definition-of-good.json',lambda v:v['requirements'].append(copy.deepcopy(v['requirements'][0])))
    elif mutation == 'source-claim-missing': edit(p,'tickets/EXAMPLE-001.json',lambda v:v.update(evidence_refs=['product:unknown']))
    elif mutation == 'missing-acceptance-proof': edit(p,'tickets/EXAMPLE-001.json',lambda v:v['acceptance_checks'][0].update(evidence=None))
    elif mutation == 'failed-acceptance-proof': edit(p,'receipts/CHK-001.json',lambda v:v.update(status='FAIL'))
    elif mutation == 'missing-journey-proof': edit(p,'traceability.json',lambda v:v['journeys'][0].update(evidence_refs=[]))
    elif mutation == 'stale-post-build': edit(p,'integration/post-build-verdict.json',lambda v:v.update(build_identity='old-build'))
    elif mutation == 'stale-cleanup': edit(p,'closeout/terminal-state.json',lambda v:v['cleanup'].update(build_identity='old-build'))
    elif mutation == 'changed-cleanup-no-reproof': edit(p,'closeout/terminal-state.json',lambda v:v['cleanup'].update(outcome='CHANGED',baseline_identity='old-build'))
    elif mutation == 'tampered-cleanup-output': (p/'receipts/cleanup.txt').write_text('Changed after receipt was made.')
    elif mutation == 'outside-proof': edit(p,'receipts/cleanup.json',lambda v:v['evidence_refs'][0].update(path='../outside.txt'))
    elif mutation == 'missing-ui-proof': edit(p,'closeout/terminal-state.json',lambda v:v.update(evidence_refs=['receipts/JRN-001.json']))
    elif mutation == 'legacy-component-verdict': edit(p,'release/production-audit.json',lambda v:v.update(verdict=v.pop('status')))
    elif mutation == 'conflicting-component-field': edit(p,'release/final-judge.json',lambda v:v.update(verdict='RED'))
    elif mutation == 'negative-judge': edit(p,'release/final-judge.json',lambda v:v.update(status='RED'))
    elif mutation == 'wrong-component-build': edit(p,'release/production-audit.json',lambda v:v.update(build_identity='old-build'))
    elif mutation == 'missing-component-proof': edit(p,'release/final-judge.json',lambda v:v.update(evidence_refs=['missing.json']))
    elif mutation == 'unaccepted-risk': edit(p,'release/production-audit.json',lambda v:v.update(status='SHIP_WITH_ACCEPTED_RISK',accepted_risks=['named-risk']))
    elif mutation == 'missing-completion': edit(p,'closeout/terminal-state.json',lambda v:v.update(completion=None))
    elif mutation == 'overclaimed-completion': edit(p,'closeout/terminal-state.json',lambda v:v['completion'].update(status='LIVE_VERIFIED'))
    assert any(expected in error for error in errors_for(p)), errors_for(p)


def test_real_runtime_target_validation_rejects_missing_required_provider(tmp_path):
    project = make_project(tmp_path)
    edit(project,'tickets/EXAMPLE-001.json',lambda v:v.update(required_capabilities=['frontend-operate']))
    with pytest.raises(TransitionError, match='REQUIRED_PROVIDER_MISSING'):
        validate_project_for_target(ROOT, project, Stage.BUILD)


def test_real_runtime_release_validation_rejects_stale_cleanup(tmp_path):
    project = make_project(tmp_path)
    edit(project,'closeout/terminal-state.json',lambda v:v['cleanup'].update(build_identity='old-build'))
    with pytest.raises(TransitionError, match='STALE_CLEANUP_BUILD'):
        validate_project_for_target(ROOT, project, Stage.RELEASE)


def test_changed_cleanup_reproof_and_unsafe_deletion(tmp_path):
    p = make_project(tmp_path)
    edit(p,'closeout/terminal-state.json',lambda v:v['cleanup'].update(outcome='CHANGED',baseline_identity='prior-build',instruction=instruction_proof(p,'prior-build'),reproof_refs=['receipts/CHK-001.json']))
    assert errors_for(p) == []
    action = {'path':'legacy.ps1','decision':'REMOVE','reason':'Candidate for removal.','owner':'maintainer','dependencies':'VERIFIED','external_callers':'UNKNOWN','dependency_evidence_refs':[proof(p,'dependencies:legacy.ps1')],'external_caller_evidence_refs':[proof(p,'external-callers:legacy.ps1')],'rollback':'Restore exact baseline version.'}
    edit(p,'closeout/terminal-state.json',lambda v:v['cleanup']['actions'].append(action))
    assert any('UNSAFE_CLEANUP_CALLERS' in error for error in errors_for(p))
    risk = 'legacy.ps1 callers remain unconfirmed'
    edit(p,'closeout/terminal-state.json',lambda v:(v['cleanup']['actions'][0].update(decision='KEEP',risk_ref=risk),v.update(open_risks=[risk])))
    assert errors_for(p, stage='RELEASE') == []


def deployed(project):
    context={'target':'test-app','environment':'staging'}
    edit(project,'definition-of-good.json',lambda v:v.update(deployment={'scope':'DEPLOYED',**context}))
    edit(project,'release/release-verdict.json',lambda v:v.update(guard_receipt_ref=proof(project,'deployment-guard'),human_approval={'required':True,'status':'APPROVED','by':'fixture-human','at':STAMP}))
    edit(project,'closeout/terminal-state.json',lambda v:v['completion'].update(scope='DEPLOYED',status='LIVE_VERIFIED',**context,execution_ref=proof(project,'deployment-execution',context),live_verification_refs=[proof(project,'live-verification',context)]))


def test_deployment_scope_requires_target_execution_and_live_evidence(tmp_path):
    p = make_project(tmp_path)
    deployed(p)
    assert errors_for(p) == []
    edit(p,'closeout/terminal-state.json',lambda v:v['completion'].update(live_verification_refs=[]))
    with pytest.raises(TransitionError, match='DEPLOYMENT_EXECUTION_OR_LIVE_PROOF_MISSING'):
        validate_project_for_target(ROOT,p,Stage.DONE)
    deployed(p)
    edit(p,'receipts/live-verification.json',lambda v:v['context'].update(target='different-app'))
    assert any('LIVE_TARGET_MISMATCH' in error for error in errors_for(p))
    deployed(p)
    edit(p,'definition-of-good.json',lambda v:v['deployment'].update(target=None))
    with pytest.raises(TransitionError, match='INVALID'):
        validate_project_for_target(ROOT,p,Stage.DONE)


def test_capability_requiredness_and_external_use(tmp_path):
    registry = read(CLAUDE/'capabilities/registry.json')['capabilities']
    code, result = resolve(['frontend-operate'],registry,[])
    assert code == 2 and {e['capability'] for e in result['errors']} == {'frontend-operate','browser-e2e'}
    assert resolve(['workflow-evals'],registry,[CLAUDE/'skills'])[0] == 0
    providers = tmp_path/'providers'
    for name in ('impeccable','e2e-testing'):
        (providers/name).mkdir(parents=True)
        (providers/name/'SKILL.md').write_text('# Fixture provider instructions\n')
    code,result = resolve(['frontend-operate'],registry,[providers])
    assert code == 2 and any(e['code']=='READINESS_PROOF_REQUIRED' for e in result['errors'])
    p = make_project(tmp_path)
    probe = proof(p,'provider-probe')
    assets = read(p/probe)['evidence_refs']
    now = datetime.now(timezone.utc)
    readiness={'schema_version':1,'project_id':p.name,'environment':'local-test','receipts':[{'capability':'browser-e2e','provider':'e2e-testing','status':'PASS','checked_at':(now-timedelta(minutes=1)).isoformat(),'expires_at':(now+timedelta(minutes=30)).isoformat(),'evidence_refs':assets}],'usage':[]}
    args={'readiness':readiness,'project':p,'environment':'local-test','build_identity':BUILD}
    code,result = resolve(['frontend-operate'],registry,[providers],**args)
    assert code == 0 and result['plan'][1]['usable'] and not result['plan'][1]['used']
    assert resolve(['frontend-operate'],registry,[providers],require_use=True,**args)[0] == 2
    readiness['usage']=[{'capability':'browser-e2e','provider':'e2e-testing','build_identity':BUILD,'invocation_refs':assets,'output_refs':assets}]
    assert resolve(['frontend-operate'],registry,[providers],require_use=True,**args)[0] == 0
    readiness['environment']='another-environment'
    assert resolve(['frontend-operate'],registry,[providers],**args)[0] == 2
    readiness['environment']='local-test'
    readiness['receipts'][0]['expires_at']=(now-timedelta(seconds=1)).isoformat()
    assert resolve(['frontend-operate'],registry,[providers],**args)[0] == 2


def test_capability_cli_returns_blocked_for_unavailable_selected_provider(tmp_path):
    registry = read(CLAUDE/'capabilities/registry.json')
    registry['capabilities']['frontend-operate']['provider']='fixture-missing-design-provider'
    registry_path=tmp_path/'registry.json'
    write(registry_path,registry)
    result=subprocess.run([sys.executable,str(CLAUDE/'scripts/resolve_capabilities.py'),'frontend-operate','--registry',str(registry_path),'--user-registry',str(tmp_path/'none')],capture_output=True,text=True)
    assert result.returncode == 2
    assert json.loads(result.stdout)['status'] == 'BLOCKED'


@pytest.mark.parametrize('transitive', [False, True])
def test_runtime_build_rejects_frontend_capability_with_ui_disabled(tmp_path, transitive):
    p = make_project(tmp_path, ui=True)
    for provider in ('impeccable', 'e2e-testing'):
        instructions = p / '.claude' / 'skills' / provider / 'SKILL.md'
        instructions.parent.mkdir(parents=True)
        instructions.write_text('# Installed fixture provider\n')
    capability = 'frontend-operate'
    if transitive:
        capability = 'ui-wrapper'
        wrapper = copy.deepcopy(read(CLAUDE / 'capabilities/registry.json')['capabilities']['workflow-evals'])
        wrapper['requires'] = ['frontend-operate']
        write(p / 'capability-registry.json', {'schema_version': 3, 'capabilities': {capability: wrapper}})
    edit(p, 'tickets/EXAMPLE-001.json', lambda value: value.update(required_capabilities=[capability]))
    now = datetime.now(timezone.utc)
    probe = proof(p, 'provider-probe')
    write(p / 'capability-readiness.json', {
        'schema_version': 1, 'project_id': p.name, 'environment': 'local-test',
        'receipts': [{
            'capability': 'browser-e2e', 'provider': 'e2e-testing', 'status': 'PASS',
            'checked_at': (now - timedelta(minutes=1)).isoformat(),
            'expires_at': (now + timedelta(minutes=30)).isoformat(),
            'evidence_refs': read(p / probe)['evidence_refs'],
        }],
        'usage': [],
    })
    # Readable providers, current probe and a real UI definition permit BUILD.
    validate_project_for_target(ROOT, p, Stage.BUILD)
    edit(p, 'definition-of-good.json', lambda value: value.update(ui=example('definition-of-good.example.json')['ui']))
    # A claimed non-UI exemption cannot suppress a selected frontend requirement.
    with pytest.raises(TransitionError, match='UI_APPLICABILITY_CONFLICT'):
        validate_project_for_target(ROOT, p, Stage.BUILD)


def test_runtime_done_requires_guard_before_deployment(tmp_path):
    p = make_project(tmp_path)
    deployed(p)
    edit(p, 'receipts/deployment-guard.json', lambda value: value.update(checked_at='2026-01-01T00:01:00Z'))
    edit(p, 'receipts/deployment-execution.json', lambda value: value.update(checked_at='2026-01-01T00:02:00Z'))
    edit(p, 'receipts/live-verification.json', lambda value: value.update(checked_at='2026-01-01T00:03:00Z'))
    edit(p, 'closeout/terminal-state.json', lambda value: value['completion'].update(checked_at='2026-01-01T00:04:00Z'))
    # Release, guard, execution and live proof are distinct ordered observations.
    validate_project_for_target(ROOT, p, Stage.DONE)
    edit(p, 'receipts/deployment-guard.json', lambda value: value.update(checked_at='2026-01-02T00:00:00Z'))
    with pytest.raises(TransitionError, match='DEPLOYMENT_PREDATES_GUARD'):
        validate_project_for_target(ROOT, p, Stage.DONE)
