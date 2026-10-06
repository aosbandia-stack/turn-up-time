"""Semantic checks consumed by the existing project stage validator."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from contract_evidence import check_assets, check_identity, check_proof, local_path, read_contract, timestamp
from resolve_capabilities import capability_closure, resolve

CLAUDE_DIR = Path(__file__).resolve().parents[1]


def unique(items: list[str], label: str, errors: list[str]) -> None:
    if len(items) != len(set(items)):
        errors.append(f'DUPLICATE_ID {label}')


def design_ref(project: Path, reference: str, errors: list[str]) -> None:
    filename, _, anchor = reference.partition('#')
    path = local_path(project, filename, errors)
    if not path:
        return
    content = path.read_text(encoding='utf-8')
    if not any(line.strip() and not line.startswith('#') for line in content.splitlines()):
        errors.append(f'EMPTY_DESIGN {reference}')
    headings = {re.sub(r'[^a-z0-9 -]', '', line.lstrip('#').strip().lower()).replace(' ', '-') for line in content.splitlines() if line.startswith('#')}
    if anchor and anchor not in headings:
        errors.append(f'UNKNOWN_DESIGN_ANCHOR {reference}')


def check_definition(project: Path, definition: dict[str, Any], errors: list[str]) -> None:
    if definition['project_id'] != project.name:
        errors.append('PROJECT_ID_MISMATCH definition-of-good')
    if definition['status'] == 'APPROVED' and not (definition['approved_by'] and definition['approved_at']):
        errors.append('DEFINITION_APPROVAL_MISSING')
    unique([r['id'] for r in definition['requirements']], 'requirements', errors)
    journeys = [j['id'] for j in definition['critical_journeys']]
    unique(journeys, 'journeys', errors)
    if definition['ui']['applicable']:
        if definition['ui']['first_slice_journey_id'] not in journeys:
            errors.append('FIRST_SLICE_JOURNEY_UNKNOWN')
        routes = definition['ui']['route_states']
        unique([r['route'] for r in routes], 'routes', errors)
        for route in routes:
            if not {'loading', 'empty', 'error', 'success'}.issubset(route['states']):
                errors.append(f'UI_ROUTE_STATES_INCOMPLETE {route["route"]}')
        check_ui_definition(project, definition['ui'], errors)
    elif definition['ui'].get('surfaces') or definition['ui'].get('design_loop'):
        errors.append('UI_APPLICABILITY_CONFLICT surfaces or design loop selected')


def rubric_digest(loop: dict[str, Any]) -> str:
    value = {key:value for key,value in loop.items() if key != 'rubric_sha256'}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def check_ui_definition(project: Path, ui: dict[str, Any], errors: list[str]) -> None:
    surfaces = ui.get('surfaces', [])
    unique([surface['id'] for surface in surfaces], 'UI surfaces', errors)
    declared = {route['route'] for route in ui['route_states']}
    if {route for surface in surfaces for route in surface['routes']} != declared:
        errors.append('UI_SURFACE_ROUTE_COVERAGE_MISMATCH')
    for surface in surfaces:
        research = surface['research']
        if surface['change_scope'] in {'NEW','REDESIGN'} and surface['research_disposition'] != 'COMPARABLES':
            errors.append('UI_COMPARABLE_RESEARCH_REQUIRED ' + surface['id'])
        if surface['research_disposition'] == 'COMPARABLES' and not research:
            errors.append('UI_COMPARABLE_RESEARCH_REQUIRED ' + surface['id'])
        for row in research:
            check_assets(project, row['evidence_refs'], errors)
            design_ref(project, row['guide_ref'], errors)
            if row['guide_ref'].partition('#')[0] != ui['design_reference'].partition('#')[0]:
                errors.append('UI_RESEARCH_OUTSIDE_DESIGN_GUIDE ' + surface['id'])
    loop = ui.get('design_loop')
    if loop:
        unique([criterion['id'] for criterion in loop['criteria']], 'design criteria', errors)
        if rubric_digest(loop) != loop['rubric_sha256']:
            errors.append('DESIGN_RUBRIC_HASH_MISMATCH')
        guide = local_path(project, ui['design_reference'].partition('#')[0], errors)
        if guide and hashlib.sha256(guide.read_bytes()).hexdigest() != loop['guide_sha256']:
            errors.append('DESIGN_GUIDE_HASH_MISMATCH')


def source_ref(project: Path, reference: str, errors: list[str]) -> None:
    if ':' not in reference:
        local_path(project, reference, errors)
        return
    lane, claim = reference.split(':', 1)
    path = local_path(project, 'evidence/' + lane + '.json', errors)
    if not path:
        return
    pack = read_contract(path, 'evidence-pack.schema.json', errors)
    if pack and not any(c['id'] == claim for c in pack['claims']):
        errors.append(f'UNKNOWN_EVIDENCE_CLAIM {reference}')


def check_traceability(project: Path, definition: dict[str, Any], tickets: list[dict[str, Any]], build: str | None, integration: bool, errors: list[str]) -> None:
    design_ref(project, 'architecture.md', errors)
    design_ref(project, definition['maintainability']['layout_ref'], errors)
    if definition['ui']['applicable']:
        design_ref(project, definition['ui']['design_reference'], errors)
    trace = read_contract(project / 'traceability.json', 'traceability.schema.json', errors)
    if not trace:
        return
    if trace['project_id'] != project.name:
        errors.append('PROJECT_ID_MISMATCH traceability')
    unique([r['requirement_id'] for r in trace['requirements']], 'trace requirements', errors)
    unique([j['journey_id'] for j in trace['journeys']], 'trace journeys', errors)
    unique([t['ticket_id'] for t in tickets], 'tickets', errors)
    ticket_map = {t['ticket_id']:t for t in tickets}
    req_map = {r['id']:r for r in definition['requirements']}
    trace_map = {r['requirement_id']:r for r in trace['requirements']}
    if set(trace_map) != set(req_map):
        errors.append('REQUIREMENT_TRACE_COVERAGE_MISMATCH')
    for ticket in tickets:
        tid = ticket['ticket_id']
        if ticket['project_id'] != project.name:
            errors.append(f'PROJECT_ID_MISMATCH {tid}')
        unique([c['id'] for c in ticket['acceptance_checks']], tid + ' checks', errors)
        for dep in ticket['dependencies']:
            if dep not in ticket_map or dep == tid:
                errors.append(f'UNKNOWN_OR_SELF_DEPENDENCY {tid}:{dep}')
        for rid in ticket['requirement_ids']:
            if rid not in req_map or tid not in req_map[rid]['ticket_ids']:
                errors.append(f'NONRECIPROCAL_REQUIREMENT {tid}:{rid}')
        for reference in ticket['evidence_refs']:
            source_ref(project, reference, errors)
        if integration:
            receipt = ticket['build_receipt']
            if not receipt or receipt['build_identity'] != build:
                errors.append(f'TICKET_BUILD_MISMATCH {tid}')
            loop = definition['ui'].get('design_loop')
            if loop and receipt and timestamp(loop['locked_at']) > timestamp(receipt['completed_at']):
                errors.append('DESIGN_RUBRIC_LOCKED_AFTER_BUILD ' + tid)
            for check in ticket['acceptance_checks']:
                if not check['evidence']:
                    errors.append(f'ACCEPTANCE_EVIDENCE_MISSING {tid}:{check["id"]}')
                else:
                    check_proof(project, check['evidence'], build, errors, check['id'])
    def visit(tid: str, path: set[str]) -> None:
        if tid in path:
            errors.append(f'DEPENDENCY_CYCLE {tid}')
            return
        for dep in ticket_map[tid]['dependencies']:
            if dep in ticket_map:
                visit(dep, path | {tid})
    for tid in ticket_map:
        visit(tid, set())
    for rid, req in req_map.items():
        row = trace_map.get(rid)
        for reference in req['evidence_refs']:
            source_ref(project, reference, errors)
        if not row:
            continue
        design_ref(project, row['design_ref'], errors)
        if set(row['ticket_ids']) != set(req['ticket_ids']):
            errors.append(f'NONRECIPROCAL_TRACE {rid}')
        gate = row['human_gate']
        if not row['ticket_ids'] and not (gate in definition['human_gates'] and req['acceptance']['type'] == 'human_gate'):
            errors.append(f'UNOWNED_REQUIREMENT {rid}')
        if gate and (gate not in definition['human_gates'] or req['acceptance']['type'] != 'human_gate'):
            errors.append(f'INVALID_HUMAN_GATE {rid}')
        if row['ticket_ids'] and not row['acceptance_checks']:
            errors.append(f'ACCEPTANCE_MAPPING_MISSING {rid}')
        for tid in row['ticket_ids']:
            if tid not in ticket_map or rid not in ticket_map[tid]['requirement_ids']:
                errors.append(f'NONRECIPROCAL_TICKET {rid}:{tid}')
        for mapping in row['acceptance_checks']:
            ticket = ticket_map.get(mapping['ticket_id'])
            if mapping['ticket_id'] not in row['ticket_ids'] or not ticket or mapping['check_id'] not in {c['id'] for c in ticket['acceptance_checks']}:
                errors.append(f'UNKNOWN_ACCEPTANCE_CHECK {rid}:{mapping}')
    journey_map = {j['journey_id']:j for j in trace['journeys']}
    if set(journey_map) != {j['id'] for j in definition['critical_journeys']}:
        errors.append('JOURNEY_TRACE_COVERAGE_MISMATCH')
    for jid, row in journey_map.items():
        design_ref(project, row['design_ref'], errors)
        if set(row['ticket_ids']) - set(ticket_map):
            errors.append(f'UNKNOWN_JOURNEY_TICKET {jid}')
        if integration:
            if not row['evidence_refs']:
                errors.append(f'JOURNEY_EVIDENCE_MISSING {jid}')
            for ref in row['evidence_refs']:
                check_proof(project, ref, build, errors, jid)
    if definition['ui']['applicable']:
        first = journey_map.get(definition['ui']['first_slice_journey_id'], {})
        first_tickets = set(first.get('ticket_ids', []))
        for ticket in tickets:
            if any(c.startswith(('frontend-', 'ui-', '21st-')) for c in ticket['required_capabilities']) and ticket['ticket_id'] not in first_tickets and not first_tickets.intersection(ticket['dependencies']):
                errors.append(f'FIRST_SLICE_DEPENDENCY_MISSING {ticket["ticket_id"]}')


def check_capabilities(project: Path, definition: dict[str, Any], tickets: list[dict[str, Any]], build: str | None, integration: bool, errors: list[str]) -> None:
    registry = {}
    for path in (CLAUDE_DIR / 'capabilities' / 'registry.json', Path.home() / '.claude' / 'capabilities' / 'registry.json', project / 'capability-registry.json'):
        if path.is_file():
            value = read_contract(path, 'capability-registry.schema.json', errors)
            if value:
                registry.update(value['capabilities'])
    readiness_path = project / 'capability-readiness.json'
    readiness = read_contract(readiness_path, 'capability-readiness.schema.json', errors) if readiness_path.exists() else None
    requested = list(dict.fromkeys(c for t in tickets for c in t['required_capabilities']))
    roots = [project / '.claude' / 'skills', CLAUDE_DIR / 'skills', Path.home() / '.claude' / 'skills']
    _, result = resolve(requested, registry, roots, readiness=readiness, project=project, environment=definition['execution_environment'], build_identity=build, require_use=integration, ui_surfaces=definition['ui'].get('surfaces', []))
    ticket_capabilities, _ = capability_closure(requested, registry)
    missing = set(result['ui_required']) - set(ticket_capabilities)
    if missing:
        errors.append('UI_TICKET_CAPABILITY_COVERAGE_MISSING ' + ','.join(sorted(missing)))
    selected_frontend = [name for name in result['selected'] if name.startswith(('frontend-', 'ui-', '21st-')) or registry[name].get('ui_selector')]
    if selected_frontend and not definition['ui']['applicable']:
        errors.append('UI_APPLICABILITY_CONFLICT selected=' + ','.join(selected_frontend))
    for error in result['errors']:
        errors.append(f'CAPABILITY {error["code"]} {error.get("capability", "")}')


def check_design_loop(project: Path, ui: dict[str, Any], packet: dict[str, Any], build: str | None, errors: list[str]) -> None:
    """Consume the existing round receipts. Historical failures are valid evidence.

    Per-criterion floors and hard gates decide; no average can erase a failure.
    Budgets validate the record, not termination of an external worker process.
    """
    loop = ui.get('design_loop')
    if not loop:
        if packet.get('design_stop_reason'):
            errors.append('DESIGN_LOOP_NOT_CONFIGURED')
        return
    criteria = {row['id']:row for row in loop['criteria']}
    gates = set(loop['hard_gates'])
    history = packet['round_history']
    if len(history) > loop['max_rounds']:
        errors.append('DESIGN_ROUND_LIMIT_EXCEEDED')
    builds: set[str] = set()
    evaluators: set[str] = set()
    first_started = previous_checked = None
    previous_scores = previous_gates = None
    previous_cost = None
    stagnant = 0
    reason = None
    for index, reference in enumerate(history):
        if reason:
            errors.append('DESIGN_CONTINUED_AFTER_STOP ' + reason)
        path = local_path(project, reference, errors)
        receipt = read_contract(path, 'verification-receipt.schema.json', errors) if path else None
        if not receipt:
            continue
        check_identity(receipt, project, receipt['build_identity'], errors, reference)
        check_assets(project, receipt['evidence_refs'], errors)
        evaluation = receipt.get('design_evaluation')
        if not evaluation or receipt['check_id'] != 'design-evaluation':
            errors.append('DESIGN_EVALUATION_REQUIRED ' + reference)
            continue
        if evaluation['rubric_sha256'] != loop['rubric_sha256'] or evaluation['guide_sha256'] != loop['guide_sha256']:
            errors.append('DESIGN_EVALUATION_CONTRACT_MISMATCH ' + reference)
        if evaluation['evaluator_role'] != 'assurance' or not evaluation['evaluator_id'].strip():
            errors.append('DESIGN_INDEPENDENT_EVALUATOR_REQUIRED ' + reference)
        if evaluation['evaluator_id'] in evaluators:
            errors.append('DESIGN_FRESH_EVALUATOR_REQUIRED ' + reference)
        evaluators.add(evaluation['evaluator_id'])
        identity = receipt['build_identity']
        content_identity = identity.rsplit(':', 1)[-1] if identity.startswith('git:') else identity
        if content_identity in builds:
            errors.append('DESIGN_UNCHANGED_BUILD_REGRADED ' + reference)
        builds.add(content_identity)
        started, checked = timestamp(evaluation['started_at']), timestamp(receipt['checked_at'])
        if timestamp(loop['locked_at']) > started or started > checked or (previous_checked and started < previous_checked):
            errors.append('DESIGN_EVALUATION_TIME_ORDER ' + reference)
        first_started = first_started or started
        previous_checked = checked
        if checked > timestamp(packet['checked_at']):
            errors.append('DESIGN_CLOSEOUT_PREDATES_EVALUATION')
        scores = {row['id']:row for row in evaluation['criteria']}
        hard = {row['id']:row for row in evaluation['hard_gates']}
        unique([row['id'] for row in evaluation['criteria']], 'evaluated criteria', errors)
        unique([row['id'] for row in evaluation['hard_gates']], 'evaluated hard gates', errors)
        if set(scores) != set(criteria) or set(hard) != gates:
            errors.append('DESIGN_CRITERION_COVERAGE_MISMATCH ' + reference)
        for row in [*scores.values(), *hard.values()]:
            check_assets(project, row['evidence_refs'], errors)
        for key, row in scores.items():
            if key not in criteria:
                continue
            if row['status'] == 'UNKNOWN':
                consistent = row['score'] is None
            else:
                consistent = row['score'] is not None and (row['status'] == 'PASS') == (row['score'] >= criteria[key]['minimum'])
            if not consistent:
                errors.append('DESIGN_CRITERION_VERDICT_CONTRADICTION ' + key)
        threshold = set(scores) == set(criteria) and set(hard) == gates
        threshold = threshold and all(row['status'] == 'PASS' for row in hard.values())
        threshold = threshold and all(row['status'] == 'PASS' and row['score'] is not None and row['score'] >= criteria[key]['minimum'] for key,row in scores.items())
        if (receipt['status'] == 'PASS') != bool(threshold):
            errors.append('DESIGN_VERDICT_CONTRADICTION ' + reference)
        current_scores = {key:row['score'] if row['score'] is not None and row['status'] != 'UNKNOWN' else -1 for key,row in scores.items()}
        current_gates = {key:{'UNKNOWN':-1,'FAIL':0,'PASS':1}[row['status']] for key,row in hard.items()}
        regression = False
        if previous_scores is not None:
            regression = any(current_scores.get(key, -1) < score for key,score in previous_scores.items()) or any(current_gates.get(key, -1) < score for key,score in previous_gates.items())
            improved = any(score > previous_scores.get(key, -1) for key,score in current_scores.items()) or any(score > previous_gates.get(key, -1) for key,score in current_gates.items())
            stagnant = 0 if improved else stagnant + 1
        previous_scores, previous_gates = current_scores, current_gates
        cost_exceeded = False
        ceiling = loop['cost_ceiling']
        if ceiling:
            cost = evaluation['cumulative_cost']
            if cost is None or evaluation['cost_unit'] != ceiling['unit'] or not evaluation['cost_evidence_refs']:
                errors.append('DESIGN_ACTUAL_COST_REQUIRED ' + reference)
            else:
                check_assets(project, evaluation['cost_evidence_refs'], errors)
                if previous_cost is not None and cost < previous_cost:
                    errors.append('DESIGN_COST_REGRESSION')
                previous_cost = cost
                cost_exceeded = cost > ceiling['amount']
        if (checked - first_started).total_seconds() > loop['max_elapsed_seconds']:
            reason = 'TIME_LIMIT'
        elif cost_exceeded:
            reason = 'COST_LIMIT'
        elif regression:
            reason = 'REGRESSION'
        elif stagnant >= loop['max_stagnant_rounds']:
            reason = 'STAGNATION'
        elif threshold:
            reason = 'THRESHOLD_MET'
        elif index + 1 >= loop['max_rounds']:
            reason = 'ROUND_LIMIT'
        if index == len(history) - 1 and (receipt['build_identity'] != build or not threshold or receipt['status'] != 'PASS'):
            errors.append('DESIGN_FINAL_BUILD_NOT_PASS')
    expected = reason or packet.get('design_stop_reason')
    if packet.get('design_stop_reason') != expected or expected not in {'THRESHOLD_MET','ENVIRONMENT','DECISION','ROUND_LIMIT','TIME_LIMIT','COST_LIMIT','STAGNATION','REGRESSION'}:
        errors.append('DESIGN_STOP_REASON_MISMATCH')
    if expected != 'THRESHOLD_MET':
        errors.append('DESIGN_LOOP_BLOCKED ' + str(expected))


def check_cleanup_instruction(project: Path, cleanup: dict[str, Any], errors: list[str]) -> dict[str, Any] | None:
    instruction = cleanup['instruction']
    # Resolve only our known source/installed root. Never read a claimed arbitrary source path.
    source = (CLAUDE_DIR / 'skills' / 'swiper-dont-swpe-me' / 'SKILL.md').resolve()
    if instruction['source_path'] != str(source):
        errors.append('CLEANUP_INSTRUCTION_SOURCE_MISMATCH')
    try:
        actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    except OSError:
        errors.append('CLEANUP_INSTRUCTION_SOURCE_MISSING')
        return None
    if instruction['sha256'] != actual_hash:
        errors.append('CLEANUP_INSTRUCTION_HASH_MISMATCH')
    proof = check_proof(project, instruction['receipt_ref'], cleanup['baseline_identity'], errors, 'cleanup-instructions')
    if proof and not any(ref['sha256'] == actual_hash for ref in proof['evidence_refs']):
        errors.append('CLEANUP_INSTRUCTION_SNAPSHOT_MISSING')
    return proof


def check_cleanup_action(project: Path, action: dict[str, Any], cleanup: dict[str, Any], instruction: dict[str, Any] | None, checked_at: str, errors: list[str]) -> None:
    path = action['path']
    if not action.get('guard_ref') or not action.get('execution_ref'):
        errors.append(f'CLEANUP_ACTION_GUARD_REQUIRED {path}')
        return
    guard = check_proof(project, action['guard_ref'], cleanup['baseline_identity'], errors, 'cleanup-guard:' + path)
    execution = check_proof(project, action['execution_ref'], cleanup['build_identity'], errors, 'cleanup-execution:' + path)
    expected = {'path': path, 'decision': action['decision']}
    for label, proof in (('guard', guard), ('execution', execution)):
        if proof and proof.get('cleanup_action') != expected:
            errors.append(f'CLEANUP_ACTION_MISMATCH {label}:{path}')
    if guard:
        authority = guard.get('guard', {})
        # Removal is consequential under the existing guard contract. A caller cannot
        # waive human authority by relabeling this action NOT_REQUIRED.
        if authority.get('verdict') != 'PROCEED' or authority.get('authority_required') is not True or authority.get('authority_status') != 'APPROVED' or not (authority.get('by') or '').strip() or not authority.get('at'):
            errors.append(f'CLEANUP_ACTION_AUTHORITY_REQUIRED {path}')
        elif timestamp(authority['at']) > timestamp(guard['checked_at']):
            errors.append(f'CLEANUP_GUARD_PREDATES_APPROVAL {path}')
        if instruction and timestamp(instruction['checked_at']) > timestamp(guard['checked_at']):
            errors.append(f'CLEANUP_GUARD_PREDATES_INSTRUCTIONS {path}')
    if execution:
        if guard and timestamp(guard['checked_at']) > timestamp(execution['checked_at']):
            errors.append(f'CLEANUP_ACTION_PREDATES_GUARD {path}')
        if timestamp(execution['checked_at']) > timestamp(checked_at):
            errors.append(f'CLEANUP_CLOSEOUT_PREDATES_ACTION {path}')


def check_closeout(project: Path, definition: dict[str, Any] | None, build: str | None, errors: list[str]) -> dict[str, Any] | None:
    packet = read_contract(project / 'closeout' / 'terminal-state.json', 'terminal-state.schema.json', errors)
    if not packet:
        return None
    check_identity(packet, project, build, errors, 'closeout')
    if packet['terminal_state'] not in {'RELEASE_READY', 'YELLOW_ACCEPTANCE_REQUIRED'}:
        errors.append('CLOSEOUT_NOT_RELEASE_READY')
    if definition:
        check_design_loop(project, definition['ui'], packet, build, errors)
    cleanup = packet['cleanup']
    instruction = check_cleanup_instruction(project, cleanup, errors)
    if cleanup['build_identity'] != build:
        errors.append('STALE_CLEANUP_BUILD')
    if cleanup['outcome'] == 'NO_CHANGE':
        if cleanup['baseline_identity'] != build or any(a['decision'] in {'REMOVE','CONSOLIDATE'} for a in cleanup['actions']):
            errors.append('CONTRADICTORY_NO_CHANGE_CLEANUP')
    elif cleanup['baseline_identity'] == build or not cleanup['reproof_refs']:
        errors.append('CLEANUP_REPROOF_REQUIRED')
    for ref in cleanup['evidence_refs']:
        proof = check_proof(project, ref, build, errors, 'cleanup')
        if proof and instruction and timestamp(instruction['checked_at']) > timestamp(proof['checked_at']):
            errors.append('CLEANUP_PREDATES_INSTRUCTIONS')
    check_proof(project, cleanup['handoff_ref'], build, errors, 'handoff')
    refs = packet['evidence_refs'] + cleanup['reproof_refs']
    if definition and definition['ui']['applicable']:
        proofs = [check_proof(project, ref, build, errors) for ref in packet['evidence_refs']]
        ids = {proof['check_id'] for proof in proofs if proof}
        for route in definition['ui']['route_states']:
            expected = {f'ui:{route["route"]}:{viewport}' for viewport in definition['ui']['viewports']}
            expected.add(f'keyboard:{route["route"]}')
            if not expected.issubset(ids):
                errors.append(f'UI_CLOSEOUT_PROOF_MISSING {route["route"]}')
    for action in cleanup['actions']:
        uncertain = action['decision'] == 'INVESTIGATE' or action['dependencies'] == 'UNKNOWN' or action['external_callers'] == 'UNKNOWN'
        if (uncertain or action.get('risk_ref')) and action.get('risk_ref') not in packet['open_risks']:
            errors.append(f'CLEANUP_RISK_LINK_REQUIRED {action["path"]} owner={action["owner"]}')
        if action['decision'] in {'REMOVE','CONSOLIDATE'}:
            check_cleanup_action(project, action, cleanup, instruction, packet['checked_at'], errors)
        if action['decision'] in {'REMOVE','CONSOLIDATE'} and (action['dependencies'] != 'VERIFIED' or action['external_callers'] != 'VERIFIED'):
            errors.append(f'UNSAFE_CLEANUP_CALLERS {action["path"]}')
        for ref in action['dependency_evidence_refs']:
            check_proof(project, ref, build, errors, 'dependencies:' + action['path'])
        for ref in action['external_caller_evidence_refs']:
            check_proof(project, ref, build, errors, 'external-callers:' + action['path'])
    for reference in set(refs):
        check_proof(project, reference, build, errors)
    return packet


def check_release(project: Path, build: str | None, verdict: dict[str, Any], packet: dict[str, Any] | None, errors: list[str]) -> None:
    check_identity(verdict, project, build, errors, 'release-verdict')
    components = {}
    for name in ('production-audit', 'final-judge'):
        value = read_contract(project / 'release' / (name + '.json'), name + '.schema.json', errors)
        if not value:
            continue
        components[name] = value
        check_identity(value, project, build, errors, name)
        if value['blockers']:
            errors.append(f'RELEASE_COMPONENT_BLOCKERS {name}')
        for ref in value['evidence_refs']:
            check_proof(project, ref, build, errors)
        if packet and timestamp(value['checked_at']) < timestamp(packet['checked_at']):
            errors.append(f'RELEASE_COMPONENT_PREDATES_CLOSEOUT {name}')
    audit = components.get('production-audit', {})
    judge = components.get('final-judge', {})
    if verdict['production_audit'] != audit.get('status') or verdict['final_judge'] != judge.get('status'):
        errors.append('RELEASE_PACKET_MISMATCH')
    if audit.get('status') not in {'SHIP','SHIP_WITH_ACCEPTED_RISK'} or judge.get('status') != 'GREEN':
        errors.append('RELEASE_COMPONENT_BLOCKED')
    if audit.get('status') == 'SHIP_WITH_ACCEPTED_RISK' and verdict['status'] != 'SHIP_WITH_ACCEPTED_RISK':
        errors.append('RELEASE_RISK_STATUS_MISMATCH')
    all_risks = set(audit.get('accepted_risks', [])) | set(judge.get('accepted_risks', [])) | set((packet or {}).get('open_risks', []))
    if not all_risks.issubset(verdict['accepted_risks']):
        errors.append('RELEASE_RISKS_OMITTED')
    approval = verdict['human_approval']
    if verdict['accepted_risks'] and verdict['status'] != 'SHIP_WITH_ACCEPTED_RISK':
        errors.append('RELEASE_RISK_STATUS_MISMATCH')
    if (approval['required'] or all_risks or verdict['accepted_risks'] or verdict['status'] == 'SHIP_WITH_ACCEPTED_RISK') and not (approval['status'] == 'APPROVED' and approval['by'] and approval['at']):
        errors.append('RELEASE_APPROVAL_MISSING')
    required_refs = {'release/production-audit.json', 'release/final-judge.json'}
    if not required_refs.issubset(verdict['evidence_refs']):
        errors.append('RELEASE_COMPONENT_REFS_MISSING')
    for ref in verdict['evidence_refs']:
        if ref not in required_refs:
            check_proof(project, ref, build, errors)
    for value in components.values():
        if timestamp(verdict['decided_at']) < timestamp(value['checked_at']):
            errors.append('RELEASE_DECISION_PREDATES_COMPONENT')


def check_completion(project: Path, definition: dict[str, Any], build: str | None, packet: dict[str, Any] | None, verdict: dict[str, Any] | None, errors: list[str]) -> None:
    completion = (packet or {}).get('completion')
    if not completion:
        errors.append('COMPLETION_PROOF_REQUIRED closeout/terminal-state.json:completion')
        return
    check_identity(completion, project, build, errors, 'completion')
    scope = definition['deployment']
    if completion['scope'] != scope['scope']:
        errors.append('COMPLETION_SCOPE_MISMATCH')
    check_proof(project, completion['handoff_ref'], build, errors, 'handoff')
    if scope['scope'] == 'CANDIDATE_ONLY':
        if completion['status'] != 'CANDIDATE_VERIFIED' or completion['execution_ref'] or completion['live_verification_refs'] or completion['target'] or completion['environment']:
            errors.append('CANDIDATE_SCOPE_OVERCLAIM')
        return
    if completion['status'] != 'LIVE_VERIFIED' or completion['target'] != scope['target'] or completion['environment'] != scope['environment']:
        errors.append('DEPLOYMENT_TARGET_MISMATCH')
    guard = None
    if not verdict or verdict['human_approval']['status'] != 'APPROVED' or not verdict['human_approval']['by'] or not verdict['human_approval']['at'] or not verdict['guard_receipt_ref']:
        errors.append('DEPLOYMENT_APPROVAL_OR_GUARD_MISSING')
    elif verdict['guard_receipt_ref']:
        guard = check_proof(project, verdict['guard_receipt_ref'], build, errors, 'deployment-guard')
    if not completion['execution_ref'] or not completion['live_verification_refs']:
        errors.append('DEPLOYMENT_EXECUTION_OR_LIVE_PROOF_MISSING')
    else:
        execution = check_proof(project, completion['execution_ref'], build, errors, 'deployment-execution')
        if execution and guard and timestamp(guard['checked_at']) > timestamp(execution['checked_at']):
            errors.append('DEPLOYMENT_PREDATES_GUARD')
        expected_context = {'target': scope['target'], 'environment': scope['environment']}
        if execution and execution.get('context') != expected_context:
            errors.append('EXECUTION_TARGET_MISMATCH')
        if execution and verdict and timestamp(execution['checked_at']) < timestamp(verdict['decided_at']):
            errors.append('DEPLOYMENT_PREDATES_RELEASE')
        for ref in completion['live_verification_refs']:
            live = check_proof(project, ref, build, errors, 'live-verification')
            if live and live.get('context') != expected_context:
                errors.append('LIVE_TARGET_MISMATCH')
            if live and execution and timestamp(live['checked_at']) < timestamp(execution['checked_at']):
                errors.append('LIVE_PROOF_PREDATES_DEPLOYMENT')
