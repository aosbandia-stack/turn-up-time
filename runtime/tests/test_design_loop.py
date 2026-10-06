"""Falsify bounded, independent UI grading at the actual release target gate."""
import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from .test_completion_contracts import BUILD, ROOT, edit, make_project, proof, read, write
from project_contracts import rubric_digest
from turn_up_time_graph.topology import Stage
from turn_up_time_graph.validation import TransitionError, validate_project_for_target


def design_project(tmp_path, rounds=((2,2),(3,3)), **limits):
    project=make_project(tmp_path,ui=True)
    loop={'rubric_version':'fixture-navigation-v1','rubric_sha256':'0'*64,
          'guide_sha256':hashlib.sha256((project/'architecture.md').read_bytes()).hexdigest(),
          'locked_at':'2025-12-31T20:00:00Z',
          'criteria':[{'id':name,'critical':critical,'minimum':3,
                       'anchors':{'0':'Primary action cannot be found.','1':'Primary action competes with three controls.',
                                  '2':'Action hierarchy needs a repeated scan.','3':'Primary and secondary actions are distinct.',
                                  '4':'Action hierarchy stays clear through recovery states.'}}
                      for name,critical in [('navigation',True),('hierarchy',False)]],
          'hard_gates':['journey','keyboard'],'max_rounds':4,'max_elapsed_seconds':900,
          'max_stagnant_rounds':2,'cost_ceiling':None,**limits}
    loop['rubric_sha256']=rubric_digest(loop)
    edit(project,'definition-of-good.json',lambda v:(v['ui'].update(design_loop=loop),v.update(approved_at='2025-12-31T20:01:00Z')))
    edit(project,'tickets/EXAMPLE-001.json',lambda v:v['build_receipt'].update(completed_at='2025-12-31T21:00:00Z'))
    refs=[]
    start=datetime(2025,12,31,22,0,tzinfo=timezone.utc)
    for i,values in enumerate(rounds):
        reference=proof(project,'design-round-'+str(i+1))
        receipt=read(project/reference)
        passed=all(score>=3 for score in values)
        receipt.update(check_id='design-evaluation',status='PASS' if passed else 'FAIL',
            build_identity=BUILD if i==len(rounds)-1 else 'changed-candidate-'+str(i),
            checked_at=(start+timedelta(minutes=2*i,seconds=60)).isoformat())
        assets=receipt['evidence_refs']
        receipt['design_evaluation']={'rubric_sha256':loop['rubric_sha256'],'guide_sha256':loop['guide_sha256'],
            'evaluator_role':'assurance','evaluator_id':'fresh-reviewer-'+str(i+1),
            'started_at':(start+timedelta(minutes=2*i)).isoformat(),
            'criteria':[{'id':name,'status':'PASS' if score>=3 else 'FAIL','score':score,'evidence_refs':assets}
                        for name,score in zip(('navigation','hierarchy'),values)],
            'hard_gates':[{'id':name,'status':'PASS','evidence_refs':assets} for name in ('journey','keyboard')],
            'cumulative_cost':None,'cost_unit':None,'cost_evidence_refs':[]}
        write(project/reference,receipt)
        refs.append(reference)
    edit(project,'closeout/terminal-state.json',lambda v:v.update(round_history=refs,design_stop_reason='THRESHOLD_MET'))
    return project,refs


def test_failed_historical_round_then_changed_passing_build_is_valid(tmp_path):
    project,refs=design_project(tmp_path)
    assert read(project/refs[0])['status']=='FAIL'
    validate_project_for_target(ROOT,project,Stage.DONE)


@pytest.mark.parametrize('mutation,expected',[
    ('critical-floor','DESIGN_FINAL_BUILD_NOT_PASS'),('failed-hard-gate','DESIGN_FINAL_BUILD_NOT_PASS'),
    ('unknown-criterion','DESIGN_FINAL_BUILD_NOT_PASS'),('missing-criterion','DESIGN_CRITERION_COVERAGE_MISMATCH'),
    ('duplicate-criterion','DUPLICATE_ID'),('builder-scores','DESIGN_INDEPENDENT_EVALUATOR_REQUIRED'),
    ('reused-evaluator','DESIGN_FRESH_EVALUATOR_REQUIRED'),('stale-final-build','DESIGN_FINAL_BUILD_NOT_PASS'),
    ('changed-rubric','DESIGN_RUBRIC_HASH_MISMATCH'),('rehashed-rubric','DESIGN_EVALUATION_CONTRACT_MISMATCH'),
    ('changed-guide','DESIGN_GUIDE_HASH_MISMATCH'),('late-lock','DESIGN_RUBRIC_LOCKED_AFTER_BUILD'),
    ('missing-actual-evidence','MISSING_EVIDENCE'),('tampered-evidence','EVIDENCE_HASH_MISMATCH'),
    ('same-build','DESIGN_UNCHANGED_BUILD_REGRADED'),('same-content-new-commit','DESIGN_UNCHANGED_BUILD_REGRADED'),
    ('wrong-stop','DESIGN_STOP_REASON_MISMATCH'),('backwards-time','DESIGN_EVALUATION_TIME_ORDER'),
    ('contradictory-criterion','DESIGN_CRITERION_VERDICT_CONTRADICTION'),
])
def test_design_judgment_cannot_bypass_hard_contract(tmp_path,mutation,expected):
    project,refs=design_project(tmp_path)
    final=refs[-1]
    if mutation=='critical-floor': edit(project,final,lambda v:v['design_evaluation']['criteria'][0].update(score=2,status='FAIL'))
    elif mutation=='failed-hard-gate': edit(project,final,lambda v:v['design_evaluation']['hard_gates'][0].update(status='FAIL'))
    elif mutation=='unknown-criterion': edit(project,final,lambda v:v['design_evaluation']['criteria'][0].update(score=None,status='UNKNOWN'))
    elif mutation=='missing-criterion': edit(project,final,lambda v:v['design_evaluation'].update(criteria=v['design_evaluation']['criteria'][:1]))
    elif mutation=='duplicate-criterion': edit(project,final,lambda v:v['design_evaluation']['criteria'].append(v['design_evaluation']['criteria'][0]))
    elif mutation=='builder-scores': edit(project,final,lambda v:v['design_evaluation'].update(evaluator_role='production'))
    elif mutation=='reused-evaluator': edit(project,final,lambda v:v['design_evaluation'].update(evaluator_id='fresh-reviewer-1'))
    elif mutation=='stale-final-build': edit(project,final,lambda v:v.update(build_identity='stale-candidate'))
    elif mutation in {'changed-rubric','rehashed-rubric','late-lock'}:
        dog=read(project/'definition-of-good.json')
        loop=dog['ui']['design_loop']
        if mutation=='late-lock': loop['locked_at']='2025-12-31T21:30:00Z'
        else: loop['criteria'][0]['anchors']['3']='A weaker substituted anchor.'
        if mutation!='changed-rubric': loop['rubric_sha256']=rubric_digest(loop)
        write(project/'definition-of-good.json',dog)
    elif mutation=='changed-guide': (project/'architecture.md').write_text((project/'architecture.md').read_text()+'Changed approved guide.\n')
    elif mutation=='missing-actual-evidence': edit(project,final,lambda v:v['design_evaluation']['criteria'][0].update(evidence_refs=[{'path':'missing.png','sha256':'0'*64}]))
    elif mutation=='tampered-evidence': (project/read(project/final)['evidence_refs'][0]['path']).write_text('different capture')
    elif mutation=='same-build': edit(project,refs[0],lambda v:v.update(build_identity=BUILD))
    elif mutation=='same-content-new-commit': edit(project,refs[0],lambda v:v.update(build_identity='git:'+'0'*40+':'+BUILD.rsplit(':',1)[-1]))
    elif mutation=='wrong-stop': edit(project,'closeout/terminal-state.json',lambda v:v.update(design_stop_reason='ROUND_LIMIT'))
    elif mutation=='backwards-time': edit(project,final,lambda v:v['design_evaluation'].update(started_at='2025-12-31T19:00:00Z'))
    elif mutation=='contradictory-criterion': edit(project,final,lambda v:v['design_evaluation']['criteria'][0].update(score=4,status='FAIL'))
    with pytest.raises(TransitionError,match=expected):
        validate_project_for_target(ROOT,project,Stage.RELEASE)


@pytest.mark.parametrize('rounds,limits,expected',[
    (((4,2),(3,3)),{},'DESIGN_LOOP_BLOCKED REGRESSION'),
    (((2,2),(2,2),(3,3)),{'max_stagnant_rounds':1},'DESIGN_CONTINUED_AFTER_STOP STAGNATION'),
    (((3,3),),{'max_elapsed_seconds':45},'DESIGN_LOOP_BLOCKED TIME_LIMIT'),
    (((2,2),(3,3)),{'max_rounds':1},'DESIGN_ROUND_LIMIT_EXCEEDED'),
])
def test_loop_limits_and_regressions_are_not_hidden_by_final_pass(tmp_path,rounds,limits,expected):
    project,_=design_project(tmp_path,rounds,**limits)
    with pytest.raises(TransitionError,match=expected):
        validate_project_for_target(ROOT,project,Stage.RELEASE)


def test_optional_cost_ceiling_needs_actual_known_usage(tmp_path):
    project,refs=design_project(tmp_path,((3,3),),cost_ceiling={'amount':1,'unit':'USD'})
    with pytest.raises(TransitionError,match='DESIGN_ACTUAL_COST_REQUIRED'):
        validate_project_for_target(ROOT,project,Stage.RELEASE)
    final=refs[-1]
    assets=read(project/proof(project,'actual-usage'))['evidence_refs']
    edit(project,final,lambda v:v['design_evaluation'].update(cumulative_cost=.5,cost_unit='USD',cost_evidence_refs=assets))
    validate_project_for_target(ROOT,project,Stage.DONE)
    edit(project,final,lambda v:v['design_evaluation'].update(cumulative_cost=2))
    with pytest.raises(TransitionError,match='DESIGN_LOOP_BLOCKED COST_LIMIT'):
        validate_project_for_target(ROOT,project,Stage.RELEASE)
