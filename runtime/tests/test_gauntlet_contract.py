import hashlib
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'.claude'/'scripts'))
from gauntlet_contract import evaluate, check_project_gauntlet, recorded_obligations
from gauntlet_common import strict_json, validate
from gauntlet_examples import make, put
from gauntlet_dispositions import recorded_dispositions

@pytest.fixture
def example(tmp_path):
    return tmp_path,make(tmp_path)

def run(root,digest,**kwargs):
    attest={'verifier':{'path':'evidence/attestation.json','sha256':hashlib.sha256((root/'evidence/attestation.json').read_bytes()).hexdigest()}}
    return evaluate(root,'gauntlet/contract.json',digest,'gauntlet/results.json',project_id='synthetic',build=kwargs.get('build','candidate'),round_events=kwargs.get('events',['round-1','round-2']),assurance_ids=['verifier'],assurance_proofs=kwargs.get('attestations',attest),repair_obligations=kwargs.get('obligations'),repair_dispatches=kwargs.get('dispatches'),finding_dispositions=kwargs.get('dispositions'),triage_dispatches=kwargs.get('triage'),finding_history=kwargs.get('history'))

def test_valid_component_and_independent_digest(example):
    root,(_,_,_,digest)=example
    r=run(root,digest)
    assert r['status']=='COMPONENT_PASS' and r['required_total']==r['required_passed']==1
    assert run(root,'0'*64)['status']=='BLOCKED'

@pytest.mark.parametrize('status',['FAIL','SKIPPED','BLOCKED','UNKNOWN'])
def test_required_status_cannot_pass(example,status):
    root,(_,r,_,digest)=example;r['checks'][0]['status']=status
    put(root,'gauntlet/results.json',r)
    assert run(root,digest)['status']=='BLOCKED'

@pytest.mark.parametrize('mutation',['missing','duplicate','wrongbuild','missingproof','selfverified','unknownverifier','resetbudget','extraevent','missingfinding','noreplay','staleproof','tamper','extra_root'])
def test_seeded_failures(example,mutation):
    root,(c,r,_,digest)=example
    if mutation=='missing':r['checks']=[]
    if mutation=='duplicate':r['checks']*=2
    if mutation=='wrongbuild':r['build_identity']='old'
    if mutation=='missingproof':r['checks'][0]['proof']=None
    if mutation=='selfverified':r['repairs'][0]['verifier']='engineer'
    if mutation=='unknownverifier':r['repairs'][0]['verifier']='impostor'
    if mutation=='resetbudget':r['budget']={'used':1,'event_ids':['round-2']}
    if mutation=='extraevent':r['budget']['event_ids'].append('round-3');r['budget']['used']=3
    if mutation=='missingfinding':r['findings']=[]
    if mutation=='noreplay':r['repairs']=[]
    if mutation=='staleproof':
        old=json.loads((root/'evidence/journey.json').read_text());old['build_identity']='before'
        r['checks'][0]['proof']=put(root,'evidence/journey.json',old)
    if mutation=='tamper':(root/'evidence/synthetic.json').write_text('{}')
    if mutation=='extra_root':r['release_ready']=True
    put(root,'gauntlet/results.json',r)
    assert run(root,digest)['status']=='BLOCKED'

def test_changed_matrix_cannot_shrink_denominator(example):
    root,(c,r,_,digest)=example;c['checks'][0]['required']=False
    put(root,'gauntlet/contract.json',c)
    assert 'HASH_MISMATCH' in str(run(root,digest)['errors'])

def test_material_open_and_acceptance_change(example):
    root,(_,r,_,digest)=example
    f=json.loads((root/'closeout/findings/F1.json').read_text());f['status']='REOPENED'
    r['findings']=[put(root,'closeout/findings/F1.json',f)];put(root,'gauntlet/results.json',r)
    assert 'UNRESOLVED_MANDATORY' in str(run(root,digest)['errors'])
    f['status']='VERIFIED';f['acceptance_criteria']='Pretend success'
    r['findings']=[put(root,'closeout/findings/F1.json',f)];put(root,'gauntlet/results.json',r)
    assert 'REPAIR_ACCEPTANCE_CHANGED' in str(run(root,digest)['errors'])

def test_no_opt_in_preserves_existing_projects(tmp_path):
    errors=[];check_project_gauntlet(tmp_path,{'requirements':[]},{},None,errors)
    assert errors==[]

def test_duplicate_json_and_schema_rejected():
    with pytest.raises(ValueError):strict_json(b'{"a":1,"a":2}')
    with pytest.raises(ValueError):strict_json(b'{"a":NaN}')
    with pytest.raises(ValueError):validate({'schema_version':1},'gauntlet-contract.schema.json')

def test_opt_in_missing_receipt_blocks(example):
    root,(_,r,_,digest)=example
    put(root,'project-ledger.json',{'spawn_log':[]})
    definition={'requirements':[{'id':'RG','priority':'MUST','acceptance':{'check':'gauntlet-contract','expected':'sha256:'+digest}},{'id':'R1','priority':'MUST','acceptance':{'check':'save','expected':'saved'}}]}
    errors=[];check_project_gauntlet(root,definition,{'evidence_refs':[]},'candidate',errors)
    assert 'GAUNTLET_TERMINAL_REFERENCE_REQUIRED' in str(errors)

def test_opt_in_real_hook_accepts_and_catches_omitted_log_finding(tmp_path):
    root=tmp_path/'synthetic';_,r,_,digest=make(root)
    definition={'requirements':[{'id':'RG','priority':'MUST','acceptance':{'check':'gauntlet-contract','expected':'sha256:'+digest}},{'id':'R1','priority':'MUST','acceptance':{'check':'save','expected':'saved'}}]}
    attestation_hash=hashlib.sha256((root/'evidence/attestation.json').read_bytes()).hexdigest()
    put(root,'project-ledger.json',{'spawn_log':[{'id':'verifier','role_class':'assurance','completed_at':'2026-10-10T00:00:00Z','outcome':'PASS','artifact_refs':['evidence/attestation.json']}],'artifacts':{'attestation':{'path':'evidence/attestation.json','sha256':attestation_hash,'status':'CURRENT','schema':'verification-receipt.schema.json'}}})
    results_ref={'path':'gauntlet/results.json','sha256':hashlib.sha256((root/'gauntlet/results.json').read_bytes()).hexdigest()}
    put(root,'gauntlet/verification.json',dict(schema_version=1,project_id='synthetic',build_identity='candidate',check_id='gauntlet-contract',status='PASS',checked_at='2026-10-10T00:00:00Z',evidence_refs=[results_ref]))
    packet={'evidence_refs':['gauntlet/verification.json'],'round_history':['round-1','round-2']}
    errors=[];check_project_gauntlet(root,definition,packet,'candidate',errors)
    assert errors==[]
    original_attestation=(root/'evidence/attestation.json').read_bytes()
    altered=json.loads(original_attestation);altered['checked_at']='2026-10-09T00:00:00Z'
    put(root,'evidence/attestation.json',altered)
    errors=[];check_project_gauntlet(root,definition,packet,'candidate',errors)
    assert 'HASH_MISMATCH evidence/attestation.json' in str(errors)
    (root/'evidence/attestation.json').write_bytes(original_attestation)
    f=json.loads((root/'closeout/findings/F1.json').read_text());f['finding_id']='F2'
    (root/'closeout/findings.jsonl').write_text(json.dumps(f)+'\n')
    errors=[];check_project_gauntlet(root,definition,packet,'candidate',errors)
    assert 'GAUNTLET_FINDING_LOG_PROJECTION_MISMATCH' in str(errors)

def test_exhausted_budget_cannot_reset_by_rewriting_results(example):
    root,(c,r,_,digest)=example
    r['budget']={'used':5,'event_ids':['round-1','round-2','round-3','round-4','round-5']}
    put(root,'gauntlet/results.json',r)
    assert 'BUDGET_RESET_OR_EXCEEDED' in str(run(root,digest,events=r['budget']['event_ids'])['errors'])

def test_verifier_name_cannot_substitute_for_actual_attestation(example):
    root,(_,r,_,digest)=example
    assert 'VERIFIER_PROVENANCE_REQUIRED' in str(run(root,digest,attestations={})['errors'])
    proof=json.loads((root/'evidence/replay.json').read_text());proof['evidence_refs']=[put(root,'evidence/forged.json',{'synthetic':'different replay'})]
    r['repairs'][0]['replay']=put(root,'evidence/replay.json',proof)
    put(root,'gauntlet/results.json',r)
    assert run(root,digest)['status']=='BLOCKED'

def discovered_obligation(root):
    c,r,_,_=make(root)
    historical=c['repair_cases'][0]
    # Freeze before the independent review knows any finding identity.
    c['repair_cases']=[];c['mandatory_finding_ids']=[]
    digest=put(root,'gauntlet/contract.json',c)['sha256']
    r['contract_sha256']=digest
    put(root,'gauntlet/results.json',r)
    original=json.loads((root/'closeout/findings/F1.json').read_text())
    original.update(build_identity='before',status='VALIDATED',verification_status='NOT_RUN',observed='Reload loses saved value')
    finding_ref=put(root,'evidence/original-finding.json',original)
    authority=json.loads((root/'triage/authority.json').read_text());authority['build_identity']='before'
    authority_ref=put(root,'triage/authority.json',authority)
    obligation=dict(schema_version=1,project_id='synthetic',contract_sha256=digest,**historical,
                    original_finding=finding_ref,owner_role='implementation-engineer',requirement_ids=['R1'],repair_authority=authority_ref,recorded_at='2026-10-10T00:01:00Z')
    ref=put(root,'gauntlet/repairs/F1.json',obligation)
    dispatch={'id':'engineer','role':'implementation-engineer','role_class':'production','started_at':'2026-10-10T00:02:00Z','completed_at':'2026-10-10T00:03:00Z','outcome':'EVIDENCE_GREEN','artifact_refs':[ref['path']]}
    ledger={'artifacts':{'repair-F1':{**ref,'status':'CURRENT','schema':'gauntlet-repair-obligation.schema.json'}},'spawn_log':[dispatch]}
    replay=json.loads((root/'evidence/replay.json').read_text());replay['checked_at']='2026-10-10T00:04:00Z'
    r['repairs'][0]['replay']=put(root,'evidence/replay.json',replay)
    attestation=json.loads((root/'evidence/attestation.json').read_text());attestation['evidence_refs']=[r['repairs'][0]['replay']];attestation['checked_at']='2026-10-10T00:05:00Z'
    journey=json.loads((root/'evidence/journey.json').read_text());journey['checked_at']='2026-10-10T00:04:00Z'
    r['checks'][0]['proof']=put(root,'evidence/journey.json',journey)
    put(root,'evidence/attestation.json',attestation);put(root,'gauntlet/results.json',r)
    return c,r,digest,obligation,ref,ledger

def test_discover_authorize_repair_and_verify_without_relocking_matrix(tmp_path):
    c,r,digest,obligation,ref,ledger=discovered_obligation(tmp_path)
    locked=(tmp_path/'gauntlet/contract.json').read_bytes()
    assert c['repair_cases']==[] and c['mandatory_finding_ids']==[]
    assert 'REPAIR_COVERAGE_MISMATCH' in str(run(tmp_path,digest)['errors'])
    refs,dispatches=recorded_obligations(ledger)
    # Authorized obligation alone cannot assert that the repair happened.
    f=json.loads((tmp_path/'closeout/findings/F1.json').read_text())
    f['status']='AUTHORIZED';f['verification_status']='NOT_RUN'
    r['findings']=[put(tmp_path,'closeout/findings/F1.json',f)]
    put(tmp_path,'gauntlet/results.json',r)
    assert run(tmp_path,digest,obligations=refs,dispatches=dispatches)['status']=='BLOCKED'
    # Separate final replay, affected journey and verifier attestation are already fixture proofs.
    f['status']='VERIFIED';f['verification_status']='VERIFIED'
    r['findings']=[put(tmp_path,'closeout/findings/F1.json',f)]
    put(tmp_path,'gauntlet/results.json',r)
    answer=run(tmp_path,digest,obligations=refs,dispatches=dispatches)
    assert answer['status']=='COMPONENT_PASS' and answer['required_total']==answer['required_passed']==1
    assert (tmp_path/'gauntlet/contract.json').read_bytes()==locked

@pytest.mark.parametrize('mutation',['tampered','missingfile','dropfinding','droprepair','originalacceptance','duplicate','dispatchmissing','afterdispatch','authoritymismatch','resetbudget','earlyreplay','earlyattestation','earlyjourney'])
def test_discovered_obligation_cannot_disappear_or_weaken_contract(tmp_path,mutation):
    c,r,digest,o,ref,ledger=discovered_obligation(tmp_path)
    refs,dispatches=recorded_obligations(ledger)
    if mutation=='tampered':o['acceptance_sha256']='0'*64;put(tmp_path,ref['path'],o)
    if mutation=='missingfile':(tmp_path/ref['path']).unlink()
    if mutation=='dropfinding':r['findings']=[]
    if mutation=='droprepair':r['repairs']=[]
    if mutation=='originalacceptance':
        original=json.loads((tmp_path/'evidence/original-finding.json').read_text());original['acceptance_criteria']='Ignore persistence'
        o['original_finding']=put(tmp_path,'evidence/original-finding.json',original);refs=[put(tmp_path,ref['path'],o)]
    if mutation=='duplicate':refs*=2
    if mutation=='dispatchmissing':dispatches={}
    if mutation=='afterdispatch':o['recorded_at']='2026-10-10T00:04:00Z';refs=[put(tmp_path,ref['path'],o)]
    if mutation=='authoritymismatch':
        a=json.loads((tmp_path/'triage/authority.json').read_text());a['finding_ids']=['different']
        o['repair_authority']=put(tmp_path,'triage/authority.json',a);refs=[put(tmp_path,ref['path'],o)]
    if mutation=='resetbudget':r['budget']={'used':1,'event_ids':['round-2']}
    if mutation=='earlyreplay':
        replay=json.loads((tmp_path/'evidence/replay.json').read_text());replay['checked_at']='2026-10-10T00:02:00Z'
        r['repairs'][0]['replay']=put(tmp_path,'evidence/replay.json',replay)
        attestation=json.loads((tmp_path/'evidence/attestation.json').read_text());attestation['evidence_refs']=[r['repairs'][0]['replay']]
        put(tmp_path,'evidence/attestation.json',attestation)
    if mutation=='earlyattestation':
        attestation=json.loads((tmp_path/'evidence/attestation.json').read_text());attestation['checked_at']='2026-10-10T00:02:00Z'
        put(tmp_path,'evidence/attestation.json',attestation)
    if mutation=='earlyjourney':
        journey=json.loads((tmp_path/'evidence/journey.json').read_text());journey['checked_at']='2026-10-10T00:02:00Z'
        r['checks'][0]['proof']=put(tmp_path,'evidence/journey.json',journey)
    put(tmp_path,'gauntlet/results.json',r)
    assert run(tmp_path,digest,obligations=refs,dispatches=dispatches)['status']=='BLOCKED'

def test_existing_locked_case_cannot_be_overwritten(tmp_path):
    c,r,digest,o,ref,ledger=discovered_obligation(tmp_path)
    c['repair_cases']=[{k:o[k] for k in ['finding_id','original_failure','original_build','implementer','affected_check_ids','acceptance_sha256']}]
    digest=put(tmp_path,'gauntlet/contract.json',c)['sha256'];r['contract_sha256']=digest;o['contract_sha256']=digest
    refs=[put(tmp_path,ref['path'],o)];put(tmp_path,'gauntlet/results.json',r)
    _,dispatches=recorded_obligations(ledger)
    assert 'REPAIR_OBLIGATION_OVERWRITES_HISTORY' in str(run(tmp_path,digest,obligations=refs,dispatches=dispatches)['errors'])

def test_controller_history_status_cannot_hide_obligation(tmp_path):
    *_,ledger=discovered_obligation(tmp_path)
    ledger['artifacts']['repair-F1']['status']='SUPERSEDED'
    with pytest.raises(ValueError,match='HISTORY_CANNOT_BE_DROPPED'):recorded_obligations(ledger)

def test_project_hook_uses_complete_recorded_obligation_inventory(tmp_path):
    root=tmp_path/'synthetic';c,r,digest,o,ref,ledger=discovered_obligation(root)
    attestation={'path':'evidence/attestation.json','sha256':hashlib.sha256((root/'evidence/attestation.json').read_bytes()).hexdigest()}
    ledger['artifacts']['attestation']={**attestation,'status':'CURRENT','schema':'verification-receipt.schema.json'}
    ledger['spawn_log'].append({'id':'verifier','role_class':'assurance','completed_at':'2026-10-10T00:05:00Z','outcome':'PASS','artifact_refs':[attestation['path']]})
    put(root,'project-ledger.json',ledger)
    results_ref={'path':'gauntlet/results.json','sha256':hashlib.sha256((root/'gauntlet/results.json').read_bytes()).hexdigest()}
    put(root,'gauntlet/verification.json',dict(schema_version=1,project_id='synthetic',build_identity='candidate',check_id='gauntlet-contract',status='PASS',checked_at='2026-10-10T00:06:00Z',evidence_refs=[results_ref]))
    definition={'requirements':[{'id':'RG','priority':'MUST','acceptance':{'check':'gauntlet-contract','expected':'sha256:'+digest}},{'id':'R1','priority':'MUST','acceptance':{'check':'save','expected':'saved'}}]}
    packet={'evidence_refs':['gauntlet/verification.json'],'round_history':['round-1','round-2']}
    errors=[];check_project_gauntlet(root,definition,packet,'candidate',errors)
    assert errors==[]
    # A worker cannot omit an obligation from results or overwrite its trusted recorded bytes.
    o['acceptance_sha256']='0'*64;put(root,ref['path'],o)
    errors=[];check_project_gauntlet(root,definition,packet,'candidate',errors)
    assert 'HASH_MISMATCH gauntlet/repairs/F1.json' in str(errors)

def disposition_fixture(root,kind='reject'):
    c,r,_,_=make(root)
    if kind=='reject':c['repair_cases']=[];c['mandatory_finding_ids']=[];r['repairs']=[]
    digest=put(root,'gauntlet/contract.json',c)['sha256'];r['contract_sha256']=digest
    original=json.loads((root/'closeout/findings/F1.json').read_text())
    original.update(finding_id='FALSE' if kind=='reject' else 'DUP',status='RAW',verification_status='NOT_RUN')
    orig_ref=put(root,'evidence/original-disposition-finding.json',original)
    current=dict(original,status='REJECTED' if kind=='reject' else 'SUPERSEDED',verification_status='NOT_RUN' if kind=='reject' else 'SUPERSEDED')
    if kind=='reject':
        (root/'closeout/findings/F1.json').unlink();r['findings']=[]
    r['findings'].append(put(root,'closeout/findings/'+current['finding_id']+'.json',current))
    evidence={'path':'evidence/synthetic.json','sha256':hashlib.sha256((root/'evidence/synthetic.json').read_bytes()).hexdigest()}
    d=dict(schema_version=1,project_id='synthetic',build_identity='candidate',contract_sha256=digest,finding_id=current['finding_id'],original_finding=orig_ref,
           action='REJECT_WITH_EVIDENCE' if kind=='reject' else 'LINK_DUPLICATE',canonical_finding_id=None if kind=='reject' else 'F1',triage_dispatch_id='triage-1',
           affected_check_ids=['J1:success:web'],evidence_refs=[evidence],rationale='Synthetic independently reproduced observation; evidence demonstrates false positive or the same canonical defect.',checked_at='2026-10-10T00:01:00Z',supersedes=None)
    ref=put(root,'gauntlet/dispositions/initial.json',d)
    dispatch=dict(id='triage-1',role='triage-lead',role_class='assurance',started_at='2026-10-10T00:00:00Z',completed_at='2026-10-10T00:02:00Z',outcome='TRIAGE_READY',artifact_refs=[ref['path']])
    ledger={'artifacts':{'disposition':{**ref,'status':'CURRENT','schema':'gauntlet-finding-disposition.schema.json'},'original':{**orig_ref,'status':'CURRENT','schema':'finding.schema.json'}},'spawn_log':[dispatch]}
    put(root,'gauntlet/results.json',r)
    return c,r,digest,d,ref,ledger

@pytest.mark.parametrize('kind',['reject','duplicate'])
def test_retained_false_positive_or_duplicate_requires_controller_disposition(tmp_path,kind):
    c,r,digest,d,ref,ledger=disposition_fixture(tmp_path,kind)
    assert run(tmp_path,digest)['status']=='BLOCKED'
    refs,triage=recorded_dispositions(ledger)
    result=run(tmp_path,digest,dispositions=refs,triage=triage)
    assert result['status']=='COMPONENT_PASS' and result['required_total']==result['required_passed']==1

@pytest.mark.parametrize('mutation',['tamper','wrongactor','nofinishedtriage','missingreference','lowerseverity','missingoriginal','blankreason','missingcanonical','selfcanonical','canonicalopen','canonicalrequirements','dropfinding'])
def test_dispositions_cannot_hide_material_work(tmp_path,mutation):
    c,r,digest,d,ref,ledger=disposition_fixture(tmp_path,'duplicate')
    refs,triage=recorded_dispositions(ledger)
    if mutation=='tamper':d['rationale']='A changed, unrecorded disposition rationale.';put(tmp_path,ref['path'],d)
    if mutation=='wrongactor':triage['triage-1']['role']='implementation-engineer'
    if mutation=='nofinishedtriage':triage['triage-1']['completed_at']=None
    if mutation=='missingreference':triage['triage-1']['artifact_refs']=[]
    if mutation=='lowerseverity':
        f=json.loads((tmp_path/'closeout/findings/DUP.json').read_text());f['severity']='S4';r['findings'][1]=put(tmp_path,'closeout/findings/DUP.json',f)
    if mutation=='missingoriginal':(tmp_path/'evidence/original-disposition-finding.json').unlink()
    if mutation=='blankreason':d['rationale']=' '*25;refs=[put(tmp_path,ref['path'],d)]
    if mutation=='missingcanonical':d['canonical_finding_id']='missing';refs=[put(tmp_path,ref['path'],d)]
    if mutation=='selfcanonical':d['canonical_finding_id']='DUP';refs=[put(tmp_path,ref['path'],d)]
    if mutation in {'canonicalopen','canonicalrequirements'}:
        f=json.loads((tmp_path/'closeout/findings/F1.json').read_text())
        if mutation=='canonicalopen':f['status']='REOPENED';f['verification_status']='REOPENED'
        else:f['requirement_ids']=[]
        r['findings'][0]=put(tmp_path,'closeout/findings/F1.json',f)
    if mutation=='dropfinding':r['findings']=r['findings'][:1]
    put(tmp_path,'gauntlet/results.json',r)
    assert run(tmp_path,digest,dispositions=refs,triage=triage)['status']=='BLOCKED'

def test_recorded_material_history_survives_worker_severity_downgrade(tmp_path):
    c,r,digest,d,ref,ledger=disposition_fixture(tmp_path)
    original=json.loads((tmp_path/'evidence/original-disposition-finding.json').read_text())
    f=dict(original,severity='S4',status='VALIDATED')
    r['findings']=[put(tmp_path,'closeout/findings/FALSE.json',f)];put(tmp_path,'gauntlet/results.json',r)
    assert run(tmp_path,digest,history=[original])['status']=='BLOCKED'

def test_disposition_can_be_revalidated_on_next_candidate_with_history_intact(tmp_path):
    c,r,digest,d,ref,ledger=disposition_fixture(tmp_path)
    old_bytes=(tmp_path/ref['path']).read_bytes()
    r['build_identity']='candidate-B'
    current=json.loads((tmp_path/'closeout/findings/FALSE.json').read_text());current['build_identity']='candidate-B'
    r['findings']=[put(tmp_path,'closeout/findings/FALSE.json',current)]
    journey=json.loads((tmp_path/'evidence/journey.json').read_text());journey['build_identity']='candidate-B'
    r['checks'][0]['proof']=put(tmp_path,'evidence/journey-B.json',journey)
    put(tmp_path,'gauntlet/results.json',r)
    refs,triage=recorded_dispositions(ledger)
    assert run(tmp_path,digest,build='candidate-B',dispositions=refs,triage=triage)['status']=='BLOCKED'
    original=dict(current,status='RAW',verification_status='NOT_RUN')
    next_d=dict(d,build_identity='candidate-B',original_finding=put(tmp_path,'evidence/original-B.json',original),supersedes=ref,triage_dispatch_id='triage-2',checked_at='2026-10-10T00:04:00Z')
    new_ref=put(tmp_path,'gauntlet/dispositions/candidate-B.json',next_d)
    ledger['artifacts']['next']={**new_ref,'status':'CURRENT','schema':'gauntlet-finding-disposition.schema.json'}
    ledger['spawn_log'].append(dict(id='triage-2',role='triage-lead',role_class='assurance',started_at='2026-10-10T00:03:00Z',completed_at='2026-10-10T00:05:00Z',outcome='TRIAGE_READY',artifact_refs=[new_ref['path']]))
    refs,triage=recorded_dispositions(ledger)
    assert run(tmp_path,digest,build='candidate-B',dispositions=refs,triage=triage)['status']=='COMPONENT_PASS'
    assert (tmp_path/ref['path']).read_bytes()==old_bytes
    assert run(tmp_path,digest,build='candidate-B',dispositions=[new_ref],triage=triage)['status']=='BLOCKED'
    next_d['supersedes']=None;refs[1]=put(tmp_path,new_ref['path'],next_d)
    assert run(tmp_path,digest,build='candidate-B',dispositions=refs,triage=triage)['status']=='BLOCKED'

@pytest.mark.parametrize('kind',['reject','duplicate'])
def test_project_hook_loads_recorded_triage_disposition_and_original_history(tmp_path,kind):
    root=tmp_path/'synthetic';c,r,digest,d,ref,ledger=disposition_fixture(root,kind)
    attestation={'path':'evidence/attestation.json','sha256':hashlib.sha256((root/'evidence/attestation.json').read_bytes()).hexdigest()}
    ledger['artifacts']['attestation']={**attestation,'status':'CURRENT','schema':'verification-receipt.schema.json'}
    ledger['spawn_log'].append({'id':'verifier','role_class':'assurance','completed_at':'2026-10-10T00:05:00Z','outcome':'PASS','artifact_refs':[attestation['path']]})
    put(root,'project-ledger.json',ledger)
    results_ref={'path':'gauntlet/results.json','sha256':hashlib.sha256((root/'gauntlet/results.json').read_bytes()).hexdigest()}
    put(root,'gauntlet/verification.json',dict(schema_version=1,project_id='synthetic',build_identity='candidate',check_id='gauntlet-contract',status='PASS',checked_at='2026-10-10T00:06:00Z',evidence_refs=[results_ref]))
    definition={'requirements':[{'id':'RG','priority':'MUST','acceptance':{'check':'gauntlet-contract','expected':'sha256:'+digest}},{'id':'R1','priority':'MUST','acceptance':{'check':'save','expected':'saved'}}]}
    packet={'evidence_refs':['gauntlet/verification.json'],'round_history':['round-1','round-2']}
    errors=[];check_project_gauntlet(root,definition,packet,'candidate',errors)
    assert errors==[]
    ledger['artifacts']['disposition']['sha256']='0'*64;put(root,'project-ledger.json',ledger)
    errors=[];check_project_gauntlet(root,definition,packet,'candidate',errors)
    assert 'HASH_MISMATCH gauntlet/dispositions/initial.json' in str(errors)
