"""Swiper's release boundary consumes instruction, risk and action authority evidence."""
from __future__ import annotations

import hashlib
import json

import pytest

from .test_completion_contracts import (
    BUILD, ROOT, STAMP, edit, errors_for, instruction_proof, make_project, proof, read, write,
)
from turn_up_time_graph.topology import Stage
from turn_up_time_graph.validation import TransitionError, validate_project_for_target

BASELINE = 'fixture-before-cleanup'


def action(project, decision='KEEP', dependencies='VERIFIED', external='VERIFIED'):
    return {
        'path': 'legacy.ps1', 'decision': decision, 'reason': 'Owner-reviewed cleanup candidate.',
        'owner': 'fixture-system-owner', 'dependencies': dependencies, 'external_callers': external,
        'dependency_evidence_refs': [proof(project, 'dependencies:legacy.ps1')],
        'external_caller_evidence_refs': [proof(project, 'external-callers:legacy.ps1')],
        'rollback': 'Restore legacy.ps1 from the exact baseline snapshot.',
    }


def guarded_action(project, decision='REMOVE'):
    item = action(project, decision)
    binding = {'path': item['path'], 'decision': decision}
    guard_ref = proof(project, 'cleanup-guard:' + item['path'])
    guard = read(project / guard_ref)
    guard.update(build_identity=BASELINE, cleanup_action=binding, guard={
        'verdict': 'PROCEED', 'authority_required': True, 'authority_status': 'APPROVED',
        'by': 'fixture-authorizing-human', 'at': STAMP,
    })
    # Preserve the existing guard's six checks as the actual captured output.
    output = project / guard['evidence_refs'][0]['path']
    output.write_text(json.dumps({
        'action': binding, 'blast_radius': ['legacy.ps1'], 'backup': 'baseline/legacy.ps1',
        'sample_or_dry_run': 'Only the duplicate is removed; maintained entry point is unchanged.',
        'expected_count': 1, 'actual_count': 1, 'rollback': item['rollback'],
        'authority_required': True, 'authority_status': 'APPROVED', 'verdict': 'PROCEED',
    }))
    guard['evidence_refs'][0]['sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    write(project / guard_ref, guard)
    execution_ref = proof(project, 'cleanup-execution:' + item['path'])
    edit(project, execution_ref, lambda value: value.update(cleanup_action=binding))
    item.update(guard_ref=guard_ref, execution_ref=execution_ref)
    edit(project, 'closeout/terminal-state.json', lambda value: value['cleanup'].update(
        outcome='CHANGED', baseline_identity=BASELINE, instruction=instruction_proof(project, BASELINE),
        actions=[item], reproof_refs=['receipts/CHK-001.json', 'receipts/JRN-001.json'],
    ))
    return item


@pytest.mark.parametrize('decision', ['REMOVE', 'CONSOLIDATE'])
def test_guarded_cleanup_is_consumed_by_runtime_release_and_done(tmp_path, decision):
    project = make_project(tmp_path)
    item = guarded_action(project, decision)
    validate_project_for_target(ROOT, project, Stage.RELEASE)
    validate_project_for_target(ROOT, project, Stage.DONE)
    # A deployment guard or general PASS receipt cannot substitute for this action's authority.
    edit(project, 'closeout/terminal-state.json', lambda value: value['cleanup']['actions'][0].pop('guard_ref'))
    with pytest.raises(TransitionError, match='CLEANUP_ACTION_GUARD_REQUIRED'):
        validate_project_for_target(ROOT, project, Stage.RELEASE)


@pytest.mark.parametrize('mutation,expected', [
    ('missing-binding', 'INVALID'),
    ('wrong-source', 'CLEANUP_INSTRUCTION_SOURCE_MISMATCH'),
    ('wrong-hash', 'CLEANUP_INSTRUCTION_HASH_MISMATCH'),
    ('missing-receipt', 'MISSING_EVIDENCE'),
    ('unrelated-snapshot', 'CLEANUP_INSTRUCTION_SNAPSHOT_MISSING'),
    ('tampered-snapshot', 'EVIDENCE_HASH_MISMATCH'),
    ('late-load', 'CLEANUP_PREDATES_INSTRUCTIONS'),
])
def test_instruction_integrity_is_required_at_runtime_boundary(tmp_path, mutation, expected):
    project = make_project(tmp_path)
    packet = 'closeout/terminal-state.json'
    binding = read(project / packet)['cleanup']['instruction']
    receipt_ref = binding['receipt_ref']
    if mutation == 'missing-binding':
        edit(project, packet, lambda value: value['cleanup'].pop('instruction'))
    elif mutation == 'wrong-source':
        edit(project, packet, lambda value: value['cleanup']['instruction'].update(source_path='/untrusted/claimed/SKILL.md'))
    elif mutation == 'wrong-hash':
        edit(project, packet, lambda value: value['cleanup']['instruction'].update(sha256='0' * 64))
    elif mutation == 'missing-receipt':
        edit(project, packet, lambda value: value['cleanup']['instruction'].update(receipt_ref='receipts/missing.json'))
    elif mutation == 'unrelated-snapshot':
        proof(project, 'cleanup-instructions')
    elif mutation == 'tampered-snapshot':
        snapshot = project / read(project / receipt_ref)['evidence_refs'][0]['path']
        snapshot.write_text('Changed after the instruction receipt.')
    elif mutation == 'late-load':
        edit(project, receipt_ref, lambda value: value.update(checked_at='2026-01-02T00:00:00Z'))
    with pytest.raises(TransitionError, match=expected):
        validate_project_for_target(ROOT, project, Stage.RELEASE)


@pytest.mark.parametrize('mutation,expected', [
    ('wrong-guard-action', 'CLEANUP_ACTION_MISMATCH'),
    ('wrong-execution-action', 'CLEANUP_ACTION_MISMATCH'),
    ('wrong-check', 'CHECK_ID_MISMATCH'),
    ('failed-receipt', 'FAILED_EVIDENCE'),
    ('blocked-guard', 'CLEANUP_ACTION_AUTHORITY_REQUIRED'),
    ('missing-authority', 'CLEANUP_ACTION_AUTHORITY_REQUIRED'),
    ('not-required-bypass', 'CLEANUP_ACTION_AUTHORITY_REQUIRED'),
    ('unnamed-authority', 'CLEANUP_ACTION_AUTHORITY_REQUIRED'),
    ('missing-approval-time', 'CLEANUP_ACTION_AUTHORITY_REQUIRED'),
    ('late-approval', 'CLEANUP_GUARD_PREDATES_APPROVAL'),
    ('late-guard', 'CLEANUP_ACTION_PREDATES_GUARD'),
    ('wrong-baseline', 'BUILD_IDENTITY_MISMATCH'),
    ('missing-execution', 'CLEANUP_ACTION_GUARD_REQUIRED'),
])
def test_removal_cannot_bypass_action_authority(tmp_path, mutation, expected):
    project = make_project(tmp_path)
    item = guarded_action(project)
    guard_ref, execution_ref = item['guard_ref'], item['execution_ref']
    if mutation == 'wrong-guard-action':
        edit(project, guard_ref, lambda value: value['cleanup_action'].update(path='another.ps1'))
    elif mutation == 'wrong-execution-action':
        edit(project, execution_ref, lambda value: value['cleanup_action'].update(decision='CONSOLIDATE'))
    elif mutation == 'wrong-check':
        edit(project, guard_ref, lambda value: value.update(check_id='deployment-guard'))
    elif mutation == 'failed-receipt':
        edit(project, guard_ref, lambda value: value.update(status='FAIL'))
    elif mutation == 'blocked-guard':
        edit(project, guard_ref, lambda value: value['guard'].update(verdict='BLOCK'))
    elif mutation == 'missing-authority':
        edit(project, guard_ref, lambda value: value.pop('guard'))
    elif mutation == 'not-required-bypass':
        edit(project, guard_ref, lambda value: value['guard'].update(authority_required=False, authority_status='NOT_REQUIRED'))
    elif mutation == 'unnamed-authority':
        edit(project, guard_ref, lambda value: value['guard'].update(by=None))
    elif mutation == 'missing-approval-time':
        edit(project, guard_ref, lambda value: value['guard'].update(at=None))
    elif mutation == 'late-approval':
        edit(project, guard_ref, lambda value: value['guard'].update(at='2026-01-02T00:00:00Z'))
    elif mutation == 'late-guard':
        edit(project, guard_ref, lambda value: value.update(checked_at='2026-01-02T00:00:00Z'))
    elif mutation == 'wrong-baseline':
        edit(project, guard_ref, lambda value: value.update(build_identity='unrelated-baseline'))
    elif mutation == 'missing-execution':
        edit(project, 'closeout/terminal-state.json', lambda value: value['cleanup']['actions'][0].pop('execution_ref'))
    with pytest.raises(TransitionError, match=expected):
        validate_project_for_target(ROOT, project, Stage.RELEASE)


@pytest.mark.parametrize('decision,dependencies,external', [
    ('INVESTIGATE', 'VERIFIED', 'VERIFIED'),
    ('KEEP', 'UNKNOWN', 'VERIFIED'),
    ('KEEP', 'VERIFIED', 'UNKNOWN'),
])
def test_uncertainty_requires_owned_risk_and_release_acceptance(tmp_path, decision, dependencies, external):
    project = make_project(tmp_path)
    item = action(project, decision, dependencies, external)
    packet = 'closeout/terminal-state.json'
    edit(project, packet, lambda value: value['cleanup'].update(actions=[item]))
    with pytest.raises(TransitionError, match='CLEANUP_RISK_LINK_REQUIRED'):
        validate_project_for_target(ROOT, project, Stage.RELEASE)
    edit(project, packet, lambda value: value['cleanup']['actions'][0].update(risk_ref='unknown-risk'))
    with pytest.raises(TransitionError, match='CLEANUP_RISK_LINK_REQUIRED'):
        validate_project_for_target(ROOT, project, Stage.RELEASE)
    # The action retains ownership. A real reference is the existing risk string, not a new registry.
    risk = 'legacy.ps1 maintenance decision pending confirmation'
    edit(project, packet, lambda value: (value.update(open_risks=[risk]), value['cleanup']['actions'][0].update(risk_ref=risk)))
    validate_project_for_target(ROOT, project, Stage.RELEASE)
    with pytest.raises(TransitionError, match='RELEASE_RISKS_OMITTED'):
        validate_project_for_target(ROOT, project, Stage.DONE)
    edit(project, 'release/production-audit.json', lambda value: value.update(status='SHIP_WITH_ACCEPTED_RISK', accepted_risks=[risk]))
    edit(project, 'release/release-verdict.json', lambda value: value.update(
        production_audit='SHIP_WITH_ACCEPTED_RISK', status='SHIP_WITH_ACCEPTED_RISK', accepted_risks=[risk],
        human_approval={'required': True, 'status': 'APPROVED', 'by': 'fixture-authorizing-human', 'at': STAMP},
    ))
    validate_project_for_target(ROOT, project, Stage.DONE)


def test_no_change_and_known_keep_need_no_removal_guard(tmp_path):
    project = make_project(tmp_path)
    validate_project_for_target(ROOT, project, Stage.DONE)
    edit(project, 'closeout/terminal-state.json', lambda value: value['cleanup'].update(actions=[action(project)]))
    assert errors_for(project) == []
