#!/usr/bin/env python3
from pathlib import Path
import json,re,sys,yaml
CLAUDE_DIR=Path(__file__).resolve().parents[1]; ROOT=CLAUDE_DIR.parent
SOURCE_MODE=(ROOT/'README.md').exists() and (ROOT/'.claude').exists()
errors=[]
core_skills={'turn-up-time','grill-me','omnidex','boil-the-ocean','easily-irritated','production-audit','its-not-you-its-me','plug-it-in','guard-before-write','eval-harness'}
skill_dirs={p.parent.name for p in (CLAUDE_DIR/'skills').glob('*/SKILL.md')}
missing=core_skills-skill_dirs; extra=skill_dirs-core_skills
if missing: errors.append(f'missing core skills: {sorted(missing)}')
if SOURCE_MODE and extra: errors.append(f'unregistered extra skills: {sorted(extra)}')
fm_re=re.compile(r'^---\n(.*?)\n---\n',re.S)
for p in list((CLAUDE_DIR/'skills').glob('*/SKILL.md'))+list((CLAUDE_DIR/'agents').glob('*.md')):
    text=p.read_text(encoding='utf-8'); m=fm_re.match(text)
    if not m: errors.append(f'{p.relative_to(ROOT)} missing frontmatter'); continue
    try: fm=yaml.safe_load(m.group(1)) or {}
    except Exception as e: errors.append(f'{p.relative_to(ROOT)} bad frontmatter: {e}'); continue
    for k in ('name','description'):
        if not fm.get(k): errors.append(f'{p.relative_to(ROOT)} missing {k}')
assurance_markers=('researcher','auditor','architect','integration-lead','irritated-domain-user','functional-qa','reviewer','triage-lead','ticket-verifier','judge')
for p in (CLAUDE_DIR/'agents').glob('*.md'):
    text=p.read_text(encoding='utf-8'); m=fm_re.match(text); fm=yaml.safe_load(m.group(1)) if m else {}
    name=fm.get('name',''); tools=set(fm.get('tools') or [])
    if any(marker in name for marker in assurance_markers) and name!='implementation-engineer':
        forbidden=tools & {'Edit','Write','MultiEdit','NotebookEdit'}
        if forbidden: errors.append(f'assurance role {name} has write tools {sorted(forbidden)}')
router=(CLAUDE_DIR/'hooks/skill-router.ps1').read_text(encoding='utf-8').lower()
if 'engineering-loop' in router: errors.append('router references retired workflow engineering-loop')
for required in ('turn-up-time','plug-it-in','its-not-you-its-me','guard-before-write'):
    if required not in router: errors.append(f'router missing {required}')
registry=yaml.safe_load((CLAUDE_DIR/'capabilities/registry.yaml').read_text(encoding='utf-8'))
if not isinstance(registry.get('capabilities'),dict): errors.append('capability registry missing capabilities map')
else:
    for name,cap in registry['capabilities'].items():
        for field in ('provider','stage','consumes','produces','conflicts','eval','uninstall'):
            if field not in cap: errors.append(f'capability {name} missing {field}')
for p in (CLAUDE_DIR/'schemas').glob('*.json'):
    try: json.loads(p.read_text(encoding='utf-8'))
    except Exception as e: errors.append(f'invalid JSON schema {p.name}: {e}')
constitution_path=ROOT/'CLAUDE.md' if SOURCE_MODE else CLAUDE_DIR/'CLAUDE.md'
constitution=constitution_path.read_text(encoding='utf-8')
for phrase in ('Loop contract','Separation of duties','Human-owned decisions','Capability routing'):
    if phrase not in constitution: errors.append(f'CLAUDE.md missing marker: {phrase}')
if errors:
    print('VALIDATION: RED'); [print(' -',e) for e in errors]; sys.exit(1)
print('VALIDATION: GREEN')
print(f' core_skills={len(core_skills)} agents={len(list((CLAUDE_DIR/"agents").glob("*.md")))} schemas={len(list((CLAUDE_DIR/"schemas").glob("*.json")))}')
