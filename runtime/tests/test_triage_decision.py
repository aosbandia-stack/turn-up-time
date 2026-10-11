import hashlib
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'.claude'/'scripts'))
from gauntlet_examples import make,put
from triage_decision import decide

@pytest.fixture
def example(tmp_path):
    return tmp_path,make(tmp_path)[2]

def test_deterministic_route_no_model_call(example):
    root,v=example
    def no_call(*args):raise AssertionError('Unnecessary model call')
    r=decide(root,v,transport=no_call)
    assert r['action']=='ROUTE_AUTHORIZED_REPAIR' and r['provider']=='deterministic'

@pytest.mark.parametrize('mutation',['stale','missingauthority','evidencetamper','unknownrequirement','raw','duplicates','outofscope'])
def test_invalid_route_blocked(example,mutation):
    root,v=example
    if mutation=='stale':v['finding']['build_identity']='old'
    if mutation=='missingauthority':v['repair_authority']=None
    if mutation=='evidencetamper':(root/'evidence/synthetic.json').write_text('{}')
    if mutation=='unknownrequirement':v['finding']['requirement_ids']=['R2']
    if mutation=='raw':v['finding']['status']='RAW'
    if mutation=='duplicates':v['owner_candidates']*=2
    if mutation=='outofscope':
        a=json.loads((root/'triage/authority.json').read_text());a['finding_ids']=['F2'];v['repair_authority']=put(root,'triage/authority.json',a)
    assert decide(root,v)['action']!='ROUTE_AUTHORIZED_REPAIR'

def semantic(root,v):
    policy=json.loads((root/'triage/policy.json').read_text())
    policy['owner_by_requirement']={'OTHER':'implementation-engineer'}
    policy['semantic_classes']=['owner-routing']
    digest=hashlib.sha256(json.dumps({k:x for k,x in policy.items() if k!='qualification_refs'},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    q=dict(schema_version=1,provider='typesafe-ai',model='jev-1.13.0',policy_sha256=digest,decision_class='owner-routing',status='QUALIFIED',evaluated_by='independent-fixture',evidence_refs=v['evidence_refs'],minimum_probability=.8)
    qref=put(root,'triage/qualification.json',q);policy['qualification_refs']=[qref]
    v['policy']=put(root,'triage/policy.json',policy)
    v['provider'].update(mode='jev',model='jev-1.13.0',qualification=qref,permit_egress=True,permit_cost=True,permitted_fields=['expected','observed','impact','recovery','type','severity','requirement_ids'])
    return v

def response(*args):
    return {'model':'jev-1.13.0','answers':{'owner':{'type':'choice','choice':'0','confidence':.9,'probabilities':{'0':.9,'none':.1}}}}

def test_qualified_typed_mock_owner(example):
    root,v=example;semantic(root,v)
    r=decide(root,v,transport=response,api_key='synthetic-not-a-key')
    assert r['action']=='ROUTE_AUTHORIZED_REPAIR' and r['qualification_status']=='QUALIFIED'

@pytest.mark.parametrize('failure',['timeout','wrongmodel','unknownchoice','badprobability','unknownquestion','unqualified','noegress','nocost','unpermittedfield','latest','nomodel','none'])
def test_jev_failure_is_explicit_pending_no_hidden_fallback(example,failure):
    root,v=example;semantic(root,v)
    if failure=='unqualified':v['provider']['qualification']=None
    if failure=='noegress':v['provider']['permit_egress']=False
    if failure=='nocost':v['provider']['permit_cost']=False
    if failure=='unpermittedfield':v['provider']['permitted_fields'].append('private_key')
    if failure=='latest':v['provider']['model']='jev-latest'
    if failure=='nomodel':v['provider']['model']=None
    def transport(*args):
        if failure=='timeout':raise TimeoutError()
        r=response()
        if failure=='wrongmodel':r['model']='jev-2.0.0'
        if failure=='unknownchoice':r['answers']['owner']['choice']='hacker'
        if failure=='badprobability':r['answers']['owner']['probabilities']['0']=float('nan')
        if failure=='unknownquestion':r['answers']['reject']=True
        if failure=='none':r['answers']['owner'].update(choice='none',probabilities={'0':.1,'none':.9})
        return r
    r=decide(root,v,transport=transport,api_key='synthetic-not-a-key')
    assert r['status']=='PENDING' and r['fallback_status']=='PENDING'
    assert r['action'] not in {'ROUTE_AUTHORIZED_REPAIR','REJECT_WITH_EVIDENCE','LINK_DUPLICATE'}

def test_repeated_failure_and_business_decision(example):
    root,v=example;v['prior_attempts']=2
    assert decide(root,v)['action']=='REFER_ARCHITECT'
    v['finding']['type']='business-question'
    assert decide(root,v)['action']=='REFER_OWNER'

def test_invalid_unknown_options_schema(example):
    root,v=example;v['provider']['mode']='automatic'
    with pytest.raises(ValueError):decide(root,v)

def test_http_official_host_bounded_request_and_no_redirect(monkeypatch):
    import triage_decision as module
    calls=[]
    class Response:
        status=200
        def read(self,n):calls.append(('read',n));return json.dumps(response()).encode()
    class Connection:
        def __init__(self,host,timeout):calls.append(('connect',host,timeout))
        def request(self,method,path,data,headers):calls.append(('request',method,path,json.loads(data),headers))
        def getresponse(self):return Response()
        def close(self):calls.append(('close',))
    monkeypatch.setattr(module.http.client,'HTTPSConnection',Connection)
    payload={'model':'jev-1.13.0','state':'synthetic','questions':{}}
    assert module.jev_http(payload,'synthetic-key',3)['model']=='jev-1.13.0'
    assert calls[0]==('connect','api.typesafe.ai',3)
    assert calls[1][1:3]==('POST','/v1/systemone')
    assert calls[1][4]['Authorization']=='Bearer synthetic-key'
    assert calls[2]==('read',65537) and calls[-1]==('close',)
    Response.status=302
    with pytest.raises(ValueError):module.jev_http(payload,'synthetic-key',3)
    with pytest.raises(ValueError):module.jev_http({'state':'x'*65537},'synthetic-key',3)
