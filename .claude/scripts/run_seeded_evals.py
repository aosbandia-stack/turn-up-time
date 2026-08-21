#!/usr/bin/env python3
from pathlib import Path
import sys, yaml, json
from jsonschema import validate, ValidationError

CLAUDE_DIR = Path(__file__).resolve().parents[1]
ROOT = CLAUDE_DIR.parent
router = (CLAUDE_DIR/'hooks/skill-router.ps1').read_text(encoding='utf-8').lower()
turn = (CLAUDE_DIR/'skills/turn-up-time/SKILL.md').read_text(encoding='utf-8')
omni = (CLAUDE_DIR/'skills/omnidex/SKILL.md').read_text(encoding='utf-8')
boil = (CLAUDE_DIR/'skills/boil-the-ocean/SKILL.md').read_text(encoding='utf-8')
closeout = (CLAUDE_DIR/'skills/its-not-you-its-me/SKILL.md').read_text(encoding='utf-8')
reg = yaml.safe_load((CLAUDE_DIR/'capabilities/registry.yaml').read_text(encoding='utf-8'))['capabilities']
results=[]
def check(id, ok, detail): results.append((id,bool(ok),detail))
check('router-build-single-control-plane','turn-up-time' in router and 'engineering-loop' not in router,'build route is centralized')
check('router-skill-install','plug-it-in' in router,'skill intake route exists')
check('ambiguous-product-before-research','/grill-me' in turn and 'human-owned' in turn.lower(),'clarification is conditional inside PM')
check('bounded-fix-no-discovery-fleet','Tier B' in turn,'Tier B is explicitly classified before Tier C')
check('unknown-must-blocks-discovery','EVIDENCE_BLOCKED' in turn and 'UNKNOWN' in turn,'MUST unknowns cannot silently pass')
check('pm-cannot-build-or-certify','do not conduct specialist research' in turn.lower() and 'certify' in turn.lower(),'PM boundaries present')
check('business-fork-human-owned','human' in omni.lower() and 'risk' in omni.lower(),'material forks are escalated')
check('repeated-ticket-failure-escalates','two materially different repairs' in boil,'repair loop has escalation')
check('closeout-cannot-auto-promote','human approval' in closeout.lower(),'self-improvement cannot auto-promote')
check('provider-conflict','taste-skill' in reg['frontend-operate']['conflicts'],'dashboard provider conflict declared')
check('destructive-command-blocked','git reset --hard' in (CLAUDE_DIR/'hooks/destructive-command-guard.ps1').read_text(encoding='utf-8'),'deterministic destructive guard present')
ticket_schema=json.loads((CLAUDE_DIR/'schemas/ticket.schema.json').read_text(encoding='utf-8'))
valid_ticket=json.loads((CLAUDE_DIR/'evals/fixtures/valid-ticket.json').read_text(encoding='utf-8'))
invalid_ticket=json.loads((CLAUDE_DIR/'evals/fixtures/invalid-ticket.json').read_text(encoding='utf-8'))
try: validate(valid_ticket,ticket_schema); valid_ok=True
except Exception: valid_ok=False
try: validate(invalid_ticket,ticket_schema); invalid_rejected=False
except ValidationError: invalid_rejected=True
check('ticket-valid-fixture',valid_ok,'valid executable ticket passes schema')
check('ticket-missing-traceability-rejected',invalid_rejected,'ticket without requirement_ids/checks is rejected')
check('capability-conflict-machine-readable',bool({'frontend-operate','taste-skill'} & set(reg['frontend-operate'].get('conflicts',[]))),'frontend-operate conflicts with taste-skill')
failed=[r for r in results if not r[1]]
for id,ok,detail in results: print(('PASS' if ok else 'FAIL'),id,'-',detail)
print(f'RESULT: {len(results)-len(failed)}/{len(results)} passed')
sys.exit(1 if failed else 0)
