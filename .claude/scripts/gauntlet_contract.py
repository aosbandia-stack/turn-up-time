#!/usr/bin/env python3
"""Verify the gauntlet component against an independently pinned acceptance matrix."""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from gauntlet_common import assets, confined, read, strict_json, unique, validate
from gauntlet_dispositions import dispositions, recorded_dispositions, recorded_finding_history

OBLIGATION_SCHEMA = 'gauntlet-repair-obligation.schema.json'

def recorded_obligations(ledger):
    """All obligations are controller inputs, never a worker-selected result subset."""
    entries=[a for a in ledger.get('artifacts',{}).values() if a['schema']==OBLIGATION_SCHEMA]
    if any(a['status'] not in {'CURRENT','APPROVED'} for a in entries):
        raise ValueError('REPAIR_OBLIGATION_HISTORY_CANNOT_BE_DROPPED')
    refs=[{'path':a['path'],'sha256':a['sha256']} for a in entries]
    unique([r['path'].casefold() for r in refs],'OBLIGATION_PATH')
    dispatches={d['id']:d for d in ledger['spawn_log'] if d['role_class']=='production'}
    return refs,dispatches

def append_repair_obligations(root, refs, dispatches, cases, contract, digest, project):
    for reference in refs:
        obligation=read(root,reference,OBLIGATION_SCHEMA)
        fid=obligation['finding_id']
        if fid in cases:
            raise ValueError('REPAIR_OBLIGATION_OVERWRITES_HISTORY ' + fid)
        if obligation['project_id']!=project or obligation['contract_sha256']!=digest:
            raise ValueError('REPAIR_OBLIGATION_CONTRACT_MISMATCH ' + fid)
        original=read(root,obligation['original_finding'],'finding.schema.json')
        if (original['project_id'],original['finding_id'],original['build_identity']) != (project,fid,obligation['original_build']):
            raise ValueError('REPAIR_ORIGINAL_FINDING_MISMATCH ' + fid)
        if (original['status'] not in {'VALIDATED','AUTHORIZED','REOPENED'}
                or set(original['requirement_ids'])!=set(obligation['requirement_ids'])
                or not set(obligation['requirement_ids']).issubset(contract['requirements'])
                or hashlib.sha256(original['acceptance_criteria'].encode()).hexdigest()!=obligation['acceptance_sha256']):
            raise ValueError('REPAIR_ORIGINAL_ACCEPTANCE_MISMATCH ' + fid)
        check_requirements={rid for c in contract['checks'] if c['required'] and c['id'] in obligation['affected_check_ids'] for rid in c['requirement_ids']}
        if not set(obligation['requirement_ids']).issubset(check_requirements):
            raise ValueError('REPAIR_AFFECTED_REQUIREMENT_COVERAGE ' + fid)
        authority=read(root,obligation['repair_authority'],'triage-authority.schema.json')
        confined(root,authority['approval_ref'])
        if ((authority['project_id'],authority['build_identity'])!=(project,obligation['original_build'])
                or fid not in authority['finding_ids'] or obligation['owner_role'] not in authority['owner_roles']
                or not set(obligation['requirement_ids']).issubset(authority['requirement_ids'])):
            raise ValueError('REPAIR_OBLIGATION_AUTHORITY_MISMATCH ' + fid)
        dispatch=dispatches.get(obligation['implementer'])
        if (not dispatch or dispatch.get('role_class')!='production' or dispatch.get('role')!=obligation['owner_role']
                or reference['path'] not in dispatch.get('artifact_refs',[])
                or not dispatch.get('started_at') or not dispatch.get('completed_at') or not dispatch.get('outcome')):
            raise ValueError('REPAIR_CONTROLLER_DISPATCH_REQUIRED ' + fid)
        recorded=datetime.fromisoformat(obligation['recorded_at'].replace('Z','+00:00'))
        started=datetime.fromisoformat(dispatch['started_at'].replace('Z','+00:00'))
        completed=datetime.fromisoformat(dispatch['completed_at'].replace('Z','+00:00'))
        if recorded > started or started > completed or completed > datetime.now(timezone.utc):
            raise ValueError('REPAIR_OBLIGATION_MUST_PRECEDE_DISPATCH ' + fid)
        failure=proof(root,obligation['original_failure'],project,obligation['original_build'],'finding:'+fid,'FAIL')
        if (datetime.fromisoformat(failure['checked_at'].replace('Z','+00:00')) > recorded
                or not set(original['evidence']).issubset({e['path'] for e in failure['evidence_refs']})):
            raise ValueError('REPAIR_ORIGINAL_FAILURE_NOT_BOUND ' + fid)
        cases[fid]=obligation

def proof(root, ref, project, build, check_id, status='PASS'):
    value = read(root, ref, 'verification-receipt.schema.json')
    if (value['project_id'], value['build_identity'], value['check_id'], value['status']) != (project, build, check_id, status):
        raise ValueError('PROOF_IDENTITY_OR_STATUS_MISMATCH ' + check_id)
    assets(root, value['evidence_refs'])
    if datetime.fromisoformat(value['checked_at'].replace('Z','+00:00')) > datetime.now(timezone.utc):
        raise ValueError('FUTURE_PROOF ' + check_id)
    return value

def evaluate(root: Path, contract_path: str, expected_hash: str, results_path: str,
             *, project_id: str, build: str, round_events: list[str], assurance_ids: list[str],
             finding_paths: list[str] | None = None, assurance_proofs: dict | None = None,
             repair_obligations: list | None = None, repair_dispatches: dict | None = None,
             finding_dispositions: list | None = None, triage_dispatches: dict | None = None,
             finding_history: list | None = None) -> dict:
    report = dict(status='BLOCKED', component='gauntlet', project_id=project_id, build_identity=build,
                  contract_sha256=expected_hash, required_total=0, required_passed=0, errors=[])
    try:
        contract = read(root, {'path':contract_path,'sha256':expected_hash}, 'gauntlet-contract.schema.json')
        result = validate(strict_json(confined(root, results_path).read_bytes()), 'gauntlet-results.schema.json')
        checks = contract['checks']
        report['required_total'] = sum(c['required'] for c in checks)
        if contract['project_id'] != project_id or (result['project_id'],result['build_identity'],result['contract_sha256']) != (project_id,build,expected_hash):
            raise ValueError('CANDIDATE_OR_CONTRACT_MISMATCH')
        for values, label in (([c['id'] for c in checks], 'CONTRACT_CHECK'),
                              ([c['id'] for c in result['checks']], 'RESULT_CHECK'),
                              (contract['requirements'],'REQUIREMENT'),
                              (contract['mandatory_finding_ids'],'MANDATORY_FINDING'),
                              ([r['finding_id'] for r in contract['repair_cases']],'REPAIR_CASE'),
                              ([r['finding_id'] for r in result['repairs']],'REPAIR_RESULT'),
                              (round_events,'ROUND_EVENT')):
            unique(values, label)
        if not any(c['required'] for c in checks):
            raise ValueError('EMPTY_REQUIRED_DENOMINATOR')
        covered = {r for c in checks if c['required'] for r in c['requirement_ids']}
        if covered != set(contract['requirements']) or any(not set(c['requirement_ids']).issubset(contract['requirements']) for c in checks):
            raise ValueError('REQUIREMENT_COVERAGE_MISMATCH')
        if set(c['id'] for c in checks) != set(c['id'] for c in result['checks']):
            raise ValueError('CHECK_SET_MISMATCH')
        budget = contract['budget']
        unique(budget['baseline_event_ids'],'BASELINE_EVENT')
        if (budget['baseline_used'] != len(budget['baseline_event_ids'])
                or result['budget']['used'] != len(round_events)
                or result['budget']['event_ids'] != round_events
                or round_events[:budget['baseline_used']] != budget['baseline_event_ids']
                or len(round_events) > budget['max_rounds'] or not round_events):
            raise ValueError('BUDGET_RESET_OR_EXCEEDED')
        rows = {c['id']:c for c in result['checks']}
        required = {c['id'] for c in checks if c['required']}
        for check in checks:
            row = rows[check['id']]
            if check['required'] and row['status'] != 'PASS':
                report['errors'].append('REQUIRED_CHECK_' + row['status'] + ' ' + check['id'])
            if row['status'] == 'PASS':
                if not row['proof']:
                    raise ValueError('MISSING_PASS_PROOF ' + row['id'])
                proof(root,row['proof'],project_id,build,check['id'])
                report['required_passed'] += int(check['required'])
        assets(root, result['findings'])
        if finding_paths is not None and set(finding_paths) != {r['path'] for r in result['findings']}:
            raise ValueError('FINDING_INVENTORY_MISMATCH')
        findings = [read(root,r,'finding.schema.json') for r in result['findings']]
        unique([f['finding_id'] for f in findings],'FINDING')
        by_id = {f['finding_id']:f for f in findings}
        disposition_map=dispositions(root,finding_dispositions or [],triage_dispatches or {},by_id,contract,expected_hash,project_id,build)
        mandatory = set(contract['mandatory_finding_ids'])
        historical_material=set()
        for original in finding_history or []:
            validate(original,'finding.schema.json')
            if original['project_id']!=project_id or original['finding_id'] not in by_id:
                raise ValueError('RECORDED_FINDING_HISTORY_MISSING_OR_WRONG_PROJECT')
            if original['severity'] in {'S0','S1','S2'}:
                historical_material.add(original['finding_id'])
        if not mandatory.issubset(by_id):
            raise ValueError('MISSING_MANDATORY_FINDING')
        for f in findings:
            if f['project_id'] != project_id or f['build_identity'] != build:
                raise ValueError('STALE_FINDING ' + f['finding_id'])
            if not set(f['requirement_ids']).issubset(contract['requirements']):
                raise ValueError('UNKNOWN_FINDING_REQUIREMENT')
            for evidence in f['evidence']:
                confined(root,evidence)
            disposition=disposition_map.get(f['finding_id'])
            if disposition:
                if f['finding_id'] in contract['mandatory_finding_ids']:
                    raise ValueError('DISPOSITION_CANNOT_ERASE_LOCKED_MANDATORY ' + f['finding_id'])
                if disposition['action']=='LINK_DUPLICATE' and (f['severity'] in {'S0','S1','S2'} or f['finding_id'] in historical_material):
                    mandatory.add(disposition['canonical_finding_id'])
                continue
            if f['status'] in {'REJECTED','SUPERSEDED'}:
                raise ValueError('FINDING_DISPOSITION_REQUIRED ' + f['finding_id'])
            if f['severity'] in {'S0','S1','S2'} or f['finding_id'] in mandatory or f['finding_id'] in historical_material:
                mandatory.add(f['finding_id'])
        for fid in mandatory:
            if by_id[fid]['status'] != 'VERIFIED' or by_id[fid]['verification_status'] != 'VERIFIED':
                report['errors'].append('UNRESOLVED_MANDATORY_FINDING ' + fid)
        cases = {c['finding_id']:c for c in contract['repair_cases']}
        append_repair_obligations(root,repair_obligations or [],repair_dispatches or {},cases,contract,expected_hash,project_id)
        if set(cases) & set(disposition_map):
            raise ValueError('DISPOSITION_CANNOT_ERASE_REPAIR_OBLIGATION')
        repairs = {r['finding_id']:r for r in result['repairs']}
        if not mandatory.issubset(cases) or set(repairs) != set(cases):
            raise ValueError('REPAIR_COVERAGE_MISMATCH')
        for fid, case in cases.items():
            f = by_id.get(fid)
            repair = repairs[fid]
            if not f or hashlib.sha256(f['acceptance_criteria'].encode()).hexdigest() != case['acceptance_sha256']:
                raise ValueError('REPAIR_ACCEPTANCE_CHANGED ' + fid)
            if case.get('requirement_ids') and set(f['requirement_ids'])!=set(case['requirement_ids']):
                raise ValueError('REPAIR_FINDING_REQUIREMENTS_CHANGED ' + fid)
            if f['status']!='VERIFIED' or f['verification_status']!='VERIFIED':
                raise ValueError('REPAIR_OBLIGATION_UNRESOLVED ' + fid)
            if repair['verifier'] == case['implementer'] or repair['verifier'] not in assurance_ids or repair['verifier'] == contract['locked_by']:
                raise ValueError('INDEPENDENT_VERIFIER_REQUIRED ' + fid)
            attestation_ref = (assurance_proofs or {}).get(repair['verifier'])
            if not attestation_ref:
                raise ValueError('VERIFIER_PROVENANCE_REQUIRED ' + fid)
            attestation = proof(root,attestation_ref,project_id,build,'gauntlet-verifier:' + repair['verifier'])
            if repair['replay'] not in attestation['evidence_refs']:
                raise ValueError('VERIFIER_REPLAY_HASH_NOT_BOUND ' + fid)
            if not set(case['affected_check_ids']).issubset(required):
                raise ValueError('AFFECTED_JOURNEY_NOT_REQUIRED ' + fid)
            proof(root,case['original_failure'],project_id,case['original_build'],'finding:' + fid,'FAIL')
            replay=proof(root,repair['replay'],project_id,build,'finding:' + fid)
            replayed_at=datetime.fromisoformat(replay['checked_at'].replace('Z','+00:00'))
            attested_at=datetime.fromisoformat(attestation['checked_at'].replace('Z','+00:00'))
            if attested_at < replayed_at:
                raise ValueError('VERIFIER_ATTESTATION_PREDATES_REPLAY ' + fid)
            if case.get('recorded_at'):
                completed_at=datetime.fromisoformat(repair_dispatches[case['implementer']]['completed_at'].replace('Z','+00:00'))
                if replayed_at < completed_at or attested_at < completed_at:
                    raise ValueError('REPAIR_VERIFICATION_PREDATES_COMPLETION ' + fid)
            for cid in case['affected_check_ids']:
                if rows[cid]['status'] != 'PASS':
                    report['errors'].append('AFFECTED_JOURNEY_FAILED ' + cid)
                elif case.get('recorded_at'):
                    journey_proof=proof(root,rows[cid]['proof'],project_id,build,cid)
                    if datetime.fromisoformat(journey_proof['checked_at'].replace('Z','+00:00')) < completed_at:
                        raise ValueError('AFFECTED_JOURNEY_PREDATES_REPAIR ' + cid)
        if not report['errors']:
            report['status'] = 'COMPONENT_PASS'
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report['errors'].append(str(exc))
    return report

def check_project_gauntlet(project, definition, packet, build, errors):
    """Existing approved Definition of Good anchors the optional contract digest."""
    anchors = [r for r in (definition or {}).get('requirements',[]) if r['acceptance']['check'] == 'gauntlet-contract']
    if not anchors:
        return
    if len(anchors) != 1 or anchors[0]['priority'] != 'MUST' or not anchors[0]['acceptance']['expected'].startswith('sha256:'):
        errors.append('GAUNTLET_INVALID_APPROVED_ANCHOR')
        return
    try:
        digest = anchors[0]['acceptance']['expected'][7:]
        contract = read(project,{'path':'gauntlet/contract.json','sha256':digest},'gauntlet-contract.schema.json')
        must_ids = {r['id'] for r in definition['requirements'] if r['priority']=='MUST' and r['acceptance']['check']!='gauntlet-contract'}
        if set(contract['requirements']) != must_ids:
            raise ValueError('GAUNTLET_DEFINITION_COVERAGE_MISMATCH')
        ledger = strict_json((project/'project-ledger.json').read_bytes())
        obligations,production_dispatches=recorded_obligations(ledger)
        disposition_refs,triage_dispatches=recorded_dispositions(ledger)
        finding_history=recorded_finding_history(project,ledger)
        completed_assurance = [r for r in ledger['spawn_log'] if r['role_class'] == 'assurance' and r.get('completed_at') and r.get('outcome')]
        assurance = [r['id'] for r in completed_assurance]
        attestations = {}
        for dispatch in completed_assurance:
            for name in dispatch.get('artifact_refs',[]):
                path=confined(project,name)
                if path.suffix != '.json':
                    continue
                document=strict_json(path.read_bytes())
                if isinstance(document,dict) and document.get('check_id') == 'gauntlet-verifier:' + dispatch['id']:
                    if dispatch['id'] in attestations:
                        raise ValueError('DUPLICATE_VERIFIER_ATTESTATION')
                    recorded=[a for a in ledger.get('artifacts',{}).values() if a['path']==name and a['status'] in {'CURRENT','APPROVED'} and a['schema']=='verification-receipt.schema.json']
                    if len(recorded)!=1:
                        raise ValueError('VERIFIER_TRUSTED_ARTIFACT_HASH_REQUIRED')
                    attestations[dispatch['id']]={'path':name,'sha256':recorded[0]['sha256']}
        results_path = 'gauntlet/results.json'
        receipt_path = 'gauntlet/verification.json'
        if receipt_path not in packet['evidence_refs']:
            raise ValueError('GAUNTLET_TERMINAL_REFERENCE_REQUIRED')
        receipt = validate(strict_json(confined(project,receipt_path).read_bytes()), 'verification-receipt.schema.json')
        result_ref = {'path':results_path,'sha256':hashlib.sha256(confined(project,results_path).read_bytes()).hexdigest()}
        if result_ref not in receipt['evidence_refs']:
            raise ValueError('GAUNTLET_RESULT_NOT_BOUND_TO_RECEIPT')
        proof(project,{'path':receipt_path,'sha256':hashlib.sha256(confined(project,receipt_path).read_bytes()).hexdigest()},project.name,build,'gauntlet-contract')
        inventory = [p.relative_to(project).as_posix() for p in (project/'closeout'/'findings').glob('*.json')]
        log = project/'closeout'/'findings.jsonl'
        if log.exists():
            latest = {}
            for line in log.read_bytes().splitlines():
                if line.strip():
                    finding=validate(strict_json(line),'finding.schema.json')
                    finding_history.append(finding)
                    latest[finding['finding_id']]=finding
            snapshots=[validate(strict_json(confined(project,p).read_bytes()),'finding.schema.json') for p in inventory]
            if latest != {f['finding_id']:f for f in snapshots}:
                raise ValueError('GAUNTLET_FINDING_LOG_PROJECTION_MISMATCH')
        report = evaluate(project,'gauntlet/contract.json',digest,results_path,project_id=project.name,build=build,
                          round_events=packet['round_history'],assurance_ids=assurance,finding_paths=inventory,assurance_proofs=attestations,
                          repair_obligations=obligations,repair_dispatches=production_dispatches,
                          finding_dispositions=disposition_refs,triage_dispatches=triage_dispatches,finding_history=finding_history)
        errors.extend('GAUNTLET ' + e for e in report['errors'])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append('GAUNTLET ' + str(exc))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,required=True)
    parser.add_argument('--project-id',required=True)
    parser.add_argument('--build',required=True)
    parser.add_argument('--contract',default='gauntlet/contract.json')
    parser.add_argument('--contract-sha256',required=True,help='Digest pinned by independent approved definition, not calculated from results')
    parser.add_argument('--results',default='gauntlet/results.json')
    parser.add_argument('--round-event',action='append',required=True)
    parser.add_argument('--assurance-id',action='append',required=True)
    parser.add_argument('--assurance-proof',action='append',default=[],help='Controller-bound verifier=path@sha256; mandatory for repairs')
    parser.add_argument('--controller-ledger',help='Trusted project-relative ledger containing all recorded repair obligations and dispatches')
    args=parser.parse_args()
    attestations={}
    for argument in args.assurance_proof:
        who,sep,reference=argument.partition('=');name,hash_sep,digest=reference.rpartition('@')
        if not sep or not hash_sep or who in attestations:
            parser.error('Invalid or duplicate --assurance-proof')
        attestations[who]={'path':name,'sha256':digest}
    try:
        ledger=strict_json(confined(args.project_root,args.controller_ledger).read_bytes()) if args.controller_ledger else {'artifacts':{},'spawn_log':[]}
        obligations,dispatches=recorded_obligations(ledger)
        disposition_refs,triage_dispatches=recorded_dispositions(ledger)
        finding_history=recorded_finding_history(args.project_root,ledger)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'BLOCKED','errors':[str(exc)]}));return 2
    result=evaluate(args.project_root,args.contract,args.contract_sha256,args.results,project_id=args.project_id,
                    build=args.build,round_events=args.round_event,assurance_ids=args.assurance_id,assurance_proofs=attestations,
                    repair_obligations=obligations,repair_dispatches=dispatches,
                    finding_dispositions=disposition_refs,triage_dispatches=triage_dispatches,finding_history=finding_history)
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='COMPONENT_PASS' else 2

if __name__ == '__main__':
    raise SystemExit(main())
