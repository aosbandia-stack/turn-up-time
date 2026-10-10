"""Create synthetic local examples. No provider calls or real project approvals."""
import argparse
import hashlib
import json
from pathlib import Path

def put(root, name, value):
    path=root/name
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(value,indent=2)+'\n').encode()
    path.write_bytes(raw)
    return {'path':name,'sha256':hashlib.sha256(raw).hexdigest()}

def make(root):
    root.mkdir(parents=True,exist_ok=True)
    evidence=put(root,'evidence/synthetic.json',{'synthetic':True,'message':'Fixture evidence only; no live browser or model execution.'})
    def receipt(name,build,check,status):
        return put(root,name,dict(schema_version=1,project_id='synthetic',build_identity=build,check_id=check,status=status,checked_at='2026-10-10T00:00:00Z',evidence_refs=[evidence]))
    original=receipt('evidence/original.json','before','finding:F1','FAIL')
    replay=receipt('evidence/replay.json','candidate','finding:F1','PASS')
    put(root,'evidence/attestation.json',dict(schema_version=1,project_id='synthetic',build_identity='candidate',check_id='gauntlet-verifier:verifier',status='PASS',checked_at='2026-10-10T00:00:00Z',evidence_refs=[replay]))
    journey=receipt('evidence/journey.json','candidate','J1:success:web','PASS')
    f=dict(schema_version=2,project_id='synthetic',finding_id='F1',build_identity='candidate',requirement_ids=['R1'],journey_step='save',expected='Saved value survives reload',observed='Saved value survives reload after repair',impact='Lost work before repair',recovery=None,evidence=[evidence['path']],severity='S2',type='defect',status='VERIFIED',owner_role='implementation-engineer',acceptance_criteria='Save and reload preserves the value',verification_status='VERIFIED')
    finding=put(root,'closeout/findings/F1.json',f)
    contract=dict(schema_version=1,project_id='synthetic',locked_by='architect',requirements=['R1'],checks=[dict(id='J1:success:web',requirement_ids=['R1'],journey='J1',state='success',surface='web',required=True,expected='Save and reload preserves the value')],mandatory_finding_ids=['F1'],repair_cases=[dict(finding_id='F1',original_failure=original,original_build='before',implementer='engineer',affected_check_ids=['J1:success:web'],acceptance_sha256=hashlib.sha256(f['acceptance_criteria'].encode()).hexdigest())],budget=dict(max_rounds=4,baseline_used=1,baseline_event_ids=['round-1']))
    cref=put(root,'gauntlet/contract.json',contract)
    results=dict(schema_version=1,project_id='synthetic',build_identity='candidate',contract_sha256=cref['sha256'],checks=[dict(id='J1:success:web',status='PASS',proof=journey)],findings=[finding],repairs=[dict(finding_id='F1',verifier='verifier',replay=replay)],budget=dict(used=2,event_ids=['round-1','round-2']))
    put(root,'gauntlet/results.json',results)
    bad=json.loads(json.dumps(results));bad['checks'][0]['status']='SKIPPED';bad['checks'][0]['proof']=None
    put(root,'gauntlet/required-skip.json',bad)
    policy=put(root,'triage/policy.json',dict(schema_version=1,project_id='synthetic',owner_by_requirement={'R1':'implementation-engineer'},semantic_classes=[],qualification_refs=[]))
    approval=put(root,'triage/SYNTHETIC-AUTHORITY.json',{'synthetic':True,'message':'Not a signed approval; usable only as test data'})
    auth=put(root,'triage/authority.json',dict(schema_version=1,project_id='synthetic',build_identity='candidate',finding_ids=['F1'],owner_roles=['implementation-engineer'],requirement_ids=['R1'],status='APPROVED',approval_ref=approval['path']))
    f['status']='VALIDATED';f['verification_status']='NOT_RUN';f['observed']='Reload loses the saved value'
    triage=dict(schema_version=1,project_id='synthetic',build_identity='candidate',finding=f,policy=policy,evidence_refs=[evidence],requirement_ids=['R1'],owner_candidates=['implementation-engineer'],duplicate_candidates=[],prior_attempts=0,repair_authority=auth,provider=dict(mode='deterministic',fallback='reasoning',model=None,qualification=None,permit_egress=False,permit_cost=False,permitted_fields=[],timeout_seconds=5))
    put(root,'triage/input.json',triage)
    return contract,results,triage,cref['sha256']

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
    if a.output.exists():
        p.error('Output must not already exist; preserve prior examples and evidence')
    _,_,_,digest=make(a.output)
    print('SYNTHETIC fixture contract SHA256: '+digest)
