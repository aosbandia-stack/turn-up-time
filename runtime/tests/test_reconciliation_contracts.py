"""PR8's attestation and Swiper's receipt must agree at the real runtime gate."""
import copy
import hashlib
import json
from pathlib import Path, PureWindowsPath

import pytest

from .test_completion_contracts import BUILD, ROOT, edit, make_project, proof, read
from contract_evidence import check_proof
from turn_up_time_graph.topology import Stage
from turn_up_time_graph.validation import TransitionError, validate_project_for_target


def test_independent_result_and_swiper_receipt_advance_integration(tmp_path):
    project = make_project(tmp_path)
    validate_project_for_target(ROOT, project, Stage.INTEGRATION)


def test_receipt_writer_normalizes_windows_paths_and_rejects_unsafe_claims(tmp_path, monkeypatch):
    project = tmp_path / 'example-project'
    project.mkdir()
    relative_to = Path.relative_to
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'relative_to', lambda path, *args: PureWindowsPath(relative_to(path, *args).as_posix()))
        reference = proof(project, 'portable')
    assert read(project / reference)['evidence_refs'][0]['path'] == 'receipts/portable.txt'
    failures = []
    check_proof(project, reference, BUILD, failures, 'portable')
    assert failures == []
    for unsafe in ('receipts\\portable.txt', '../outside.txt'):
        edit(project, reference, lambda value: value['evidence_refs'][0].update(path=unsafe))
        failures = []
        check_proof(project, reference, BUILD, failures, 'portable')
        assert any('EVIDENCE_OUTSIDE_PROJECT' in failure for failure in failures)


@pytest.mark.parametrize('mutation,expected', [
    ('duplicate', 'UNKNOWN_OR_DUPLICATE_CHECK_RESULT'),
    ('unknown-check', 'UNKNOWN_OR_DUPLICATE_CHECK_RESULT'),
    ('builder-role', 'evaluator_role'),
    ('failed-result', 'status'),
    ('wrong-result-hash', 'EVIDENCE_HASH_MISMATCH'),
    ('wrong-receipt-check', 'CHECK_ID_MISMATCH'),
    ('failed-receipt', 'FAILED_EVIDENCE'),
    ('raw-output-instead-of-receipt', 'UNREADABLE'),
])
def test_structured_results_cannot_bypass_swiper_receipt(tmp_path, mutation, expected):
    project = make_project(tmp_path)
    ticket_path = 'tickets/EXAMPLE-001.json'
    if mutation == 'duplicate':
        edit(project, ticket_path, lambda value: value['build_receipt']['check_results'].append(copy.deepcopy(value['build_receipt']['check_results'][0])))
    elif mutation == 'unknown-check':
        edit(project, ticket_path, lambda value: value['build_receipt']['check_results'][0].update(check_id='unknown'))
    elif mutation == 'builder-role':
        edit(project, ticket_path, lambda value: value['build_receipt']['check_results'][0].update(evaluator_role='production'))
    elif mutation == 'failed-result':
        edit(project, ticket_path, lambda value: value['build_receipt']['check_results'][0].update(status='FAIL'))
    elif mutation == 'wrong-result-hash':
        edit(project, ticket_path, lambda value: value['build_receipt']['check_results'][0].update(evidence_sha256='0' * 64))
    else:
        reference = 'receipts/CHK-001.json'
        if mutation == 'raw-output-instead-of-receipt':
            reference = 'receipts/CHK-001.txt'
            edit(project, ticket_path, lambda value: value['acceptance_checks'][0].update(evidence=reference))
        elif mutation == 'wrong-receipt-check':
            edit(project, reference, lambda value: value.update(check_id='different-check'))
        else:
            edit(project, reference, lambda value: value.update(status='FAIL'))
        # A matching receipt-file hash still cannot excuse an invalid receipt contract.
        digest = hashlib.sha256((project / reference).read_bytes()).hexdigest()
        edit(project, ticket_path, lambda value: value['build_receipt']['check_results'][0].update(evidence_ref=reference, evidence_sha256=digest))
    with pytest.raises(TransitionError, match=expected):
        validate_project_for_target(ROOT, project, Stage.INTEGRATION)
