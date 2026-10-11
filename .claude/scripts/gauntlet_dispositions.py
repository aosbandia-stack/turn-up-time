"""Validate retained finding dispositions using existing controller artifact/dispatch records."""
from datetime import datetime, timezone
from gauntlet_common import assets, read, unique

SCHEMA='gauntlet-finding-disposition.schema.json'

def recorded_finding_history(root,ledger):
    return [read(root,{'path':a['path'],'sha256':a['sha256']},'finding.schema.json')
            for a in ledger.get('artifacts',{}).values() if a['schema']=='finding.schema.json']

def recorded_dispositions(ledger):
    entries=[a for a in ledger.get('artifacts',{}).values() if a['schema']==SCHEMA]
    if any(a['status'] not in {'CURRENT','APPROVED'} for a in entries):
        raise ValueError('FINDING_DISPOSITION_HISTORY_CANNOT_BE_DROPPED')
    refs=[{'path':a['path'],'sha256':a['sha256']} for a in entries]
    unique([r['path'].casefold() for r in refs],'DISPOSITION_PATH')
    return refs,{d['id']:d for d in ledger['spawn_log'] if d['role_class']=='assurance'}

def dispositions(root,refs,dispatches,findings,contract,digest,project,build):
    result={}
    checks={c['id']:c for c in contract['checks'] if c['required']}
    unique([ref['path'].casefold() for ref in refs],'DISPOSITION_PATH')
    documents={ref['path']:(ref,read(root,ref,SCHEMA)) for ref in refs}
    successors={}
    for path,(ref,value) in documents.items():
        previous=value['supersedes']
        if previous:
            old=documents.get(previous['path'])
            if (not old or old[0]!=previous or old[1]['finding_id']!=value['finding_id']
                    or previous['path'] in successors
                    or datetime.fromisoformat(old[1]['checked_at'].replace('Z','+00:00')) >= datetime.fromisoformat(value['checked_at'].replace('Z','+00:00'))):
                raise ValueError('DISPOSITION_HISTORY_LINK_INVALID')
            successors[previous['path']]=path
    heads={path for path in documents if path not in successors}
    head_ids=[documents[path][1]['finding_id'] for path in heads]
    if len(head_ids)!=len(set(head_ids)) or set(head_ids)!={v[1]['finding_id'] for v in documents.values()}:
        raise ValueError('DISPOSITION_HISTORY_FORK_OR_CYCLE')
    for ref in refs:
        value=documents[ref['path']][1]
        fid=value['finding_id']
        active=ref['path'] in heads
        if (value['project_id'],value['contract_sha256']) != (project,digest) or (active and value['build_identity']!=build):
            raise ValueError('FINDING_DISPOSITION_CANDIDATE_MISMATCH ' + fid)
        original=read(root,value['original_finding'],'finding.schema.json')
        current=findings.get(fid)
        if ((original['project_id'],original['build_identity'],original['finding_id']) != (project,value['build_identity'],fid)
                or original['status'] not in {'RAW','VALIDATED','AUTHORIZED','REOPENED'}
                or (active and (not current or any(current[k]!=original[k] for k in original if k not in {'status','verification_status'})))):
            raise ValueError('FINDING_DISPOSITION_ORIGINAL_CHANGED ' + fid)
        assets(root,value['evidence_refs'])
        if not set(original['evidence']).issubset({r['path'] for r in value['evidence_refs']}):
            raise ValueError('FINDING_DISPOSITION_EVIDENCE_NOT_BOUND ' + fid)
        if not set(value['affected_check_ids']).issubset(checks):
            raise ValueError('FINDING_DISPOSITION_UNKNOWN_AFFECTED_CHECK ' + fid)
        covered={rid for cid in value['affected_check_ids'] for rid in checks[cid]['requirement_ids']}
        if not original['requirement_ids'] or not set(original['requirement_ids']).issubset(covered):
            raise ValueError('FINDING_DISPOSITION_REQUIREMENTS_UNCOVERED ' + fid)
        dispatch=dispatches.get(value['triage_dispatch_id'])
        if (not dispatch or dispatch.get('role_class')!='assurance'
                or dispatch.get('role') not in {'triage-lead','tut_triage_lead'}
                or ref['path'] not in dispatch.get('artifact_refs',[])
                or not dispatch.get('started_at') or not dispatch.get('completed_at') or not dispatch.get('outcome')):
            raise ValueError('FINDING_DISPOSITION_TRIAGE_PROVENANCE_REQUIRED ' + fid)
        checked=datetime.fromisoformat(value['checked_at'].replace('Z','+00:00'))
        started=datetime.fromisoformat(dispatch['started_at'].replace('Z','+00:00'))
        completed=datetime.fromisoformat(dispatch['completed_at'].replace('Z','+00:00'))
        if not started <= checked <= completed <= datetime.now(timezone.utc):
            raise ValueError('FINDING_DISPOSITION_TIME_MISMATCH ' + fid)
        if not active:
            continue
        if value['action']=='REJECT_WITH_EVIDENCE':
            if current['status']!='REJECTED' or current['verification_status']!='NOT_RUN' or value['canonical_finding_id'] is not None:
                raise ValueError('FINDING_REJECTION_STATUS_MISMATCH ' + fid)
        else:
            canonical=findings.get(value['canonical_finding_id'])
            if (current['status']!='SUPERSEDED' or current['verification_status']!='SUPERSEDED'
                    or not canonical or canonical['finding_id']==fid
                    or canonical['status'] in {'REJECTED','SUPERSEDED'}
                    or not set(original['requirement_ids']).issubset(canonical['requirement_ids'])):
                raise ValueError('FINDING_DUPLICATE_CANONICAL_INVALID ' + fid)
        result[fid]=value
    return result
