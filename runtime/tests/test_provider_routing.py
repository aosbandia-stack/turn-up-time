"""Optional audit routing at the real integration gate; fixtures do not run an audit."""
import pytest

from .test_completion_contracts import (BUILD, ROOT, edit, make_project, ready_provider)
from turn_up_time_graph.topology import Stage
from turn_up_time_graph.validation import TransitionError, validate_project_for_target

CHECKS = ('audit_scope', 'audit_budget', 'independent_review', 'isolated_output',
          'audit_validators', 'execution_policy')


def audit_project(tmp_path):
    project = make_project(tmp_path)
    edit(project, 'tickets/EXAMPLE-001.json',
         lambda value: value['required_capabilities'].append('security-audit'))
    ready_provider(project, 'security-audit', 'security-audit', dict.fromkeys(CHECKS, 'PASS'))
    return project


def test_full_audit_requires_actual_use_at_integration(tmp_path):
    project = audit_project(tmp_path)
    validate_project_for_target(ROOT, project, Stage.INTEGRATION)
    edit(project, 'capability-readiness.json', lambda value: value.update(usage=[]))
    with pytest.raises(TransitionError, match='ACTUAL_USE_PROOF_REQUIRED'):
        validate_project_for_target(ROOT, project, Stage.INTEGRATION)


@pytest.mark.parametrize('check', CHECKS)
@pytest.mark.parametrize('status', [None, 'UNKNOWN', 'FAIL'])
def test_each_audit_readiness_requirement_blocks_at_real_gate(tmp_path, check, status):
    project = audit_project(tmp_path)
    def change(value):
        checks = value['receipts'][0]['checks']
        if status is None:
            checks.pop(check)
        else:
            checks[check] = status
    edit(project, 'capability-readiness.json', change)
    with pytest.raises(TransitionError, match='READINESS_CHECK_REQUIRED:' + check):
        validate_project_for_target(ROOT, project, Stage.INTEGRATION)


@pytest.mark.parametrize('mutation,expected', [
    ('expired', 'READINESS_EXPIRED_OR_FAILED'),
    ('different-environment', 'READINESS_PROOF_REQUIRED'),
    ('different-candidate', 'USAGE_CONTEXT_MISMATCH'),
    ('no-output', 'ACTUAL_USE_PROOF_REQUIRED'),
    ('tampered-output', 'EVIDENCE_HASH_MISMATCH'),
    ('no-instructions', 'REQUIRED_PROVIDER_MISSING'),
])
def test_audit_proof_is_bound_to_actual_environment_and_candidate(tmp_path, mutation, expected):
    project = audit_project(tmp_path)
    def change(value):
        if mutation == 'expired':
            value['receipts'][0]['expires_at'] = '2020-01-01T00:00:00Z'
        elif mutation == 'different-environment':
            value['environment'] = 'other-host'
        elif mutation == 'different-candidate':
            value['usage'][0]['build_identity'] = BUILD + '-obsolete'
        elif mutation == 'no-output':
            value['usage'] = []
        elif mutation == 'tampered-output':
            ref = value['usage'][0]['output_refs'][0]
            (project / ref['path']).write_text('Changed output after capture')
        elif mutation == 'no-instructions':
            (project / '.claude/skills/security-audit/SKILL.md').unlink()
    edit(project, 'capability-readiness.json', change)
    with pytest.raises(TransitionError, match=expected):
        validate_project_for_target(ROOT, project, Stage.INTEGRATION)


def test_focused_guidance_does_not_claim_execution_or_require_full_audit(tmp_path):
    project = make_project(tmp_path)
    edit(project, 'tickets/EXAMPLE-001.json',
         lambda value: value['required_capabilities'].append('security-guidance'))
    instructions = project / '.claude/skills/security-audit/SKILL.md'
    instructions.parent.mkdir(parents=True)
    instructions.write_text('# Disposable focused guidance fixture\n')
    validate_project_for_target(ROOT, project, Stage.INTEGRATION)
