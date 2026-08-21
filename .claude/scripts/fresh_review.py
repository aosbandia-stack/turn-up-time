#!/usr/bin/env python3
from pathlib import Path
import re, json, yaml, sys

ROOT = Path(__file__).resolve().parents[2]
checks=[]
def add(name, ok, detail): checks.append((name,bool(ok),detail))

readme=(ROOT/'README.md').read_text(encoding='utf-8')
add('readme-skill-count', '9 user-facing skills plus 1 internal eval provider' in readme, 'README matches ten skill directories')
add('readme-agent-count', '17 role-specific agents' in readme, 'README matches agent inventory')
add('lite-combined-researcher', (ROOT/'.claude/agents/combined-engineering-researcher.md').exists(), 'lite profile provider exists')
claude=(ROOT/'CLAUDE.md').read_text(encoding='utf-8')
arch=(ROOT/'docs/ARCHITECTURE.md').read_text(encoding='utf-8')
add('single-constitution', 'one constitution' in claude.lower() and 'Canonical Operating Contract' in claude, 'CLAUDE.md declares itself canonical')
for stage in ('Route/intake','Discovery','Definition/tickets','Seam review','Build','Product closeout','Release','Workflow closeout'):
    add('owner-'+stage.lower().replace('/','-').replace(' ','-'), stage in arch, f'architecture names owner row for {stage}')
fm_re=re.compile(r'^---\n(.*?)\n---\n',re.S)
assurance_tokens=('researcher','auditor','architect','integration-lead','irritated-domain-user','functional-qa','reviewer','triage-lead','ticket-verifier','judge')
for p in sorted((ROOT/'.claude/agents').glob('*.md')):
    m=fm_re.match(p.read_text(encoding='utf-8')); fm=yaml.safe_load(m.group(1)) if m else {}
    name=fm.get('name',''); tools=set(fm.get('tools') or [])
    if any(t in name for t in assurance_tokens) and name!='implementation-engineer':
        add('readonly-'+name, not (tools & {'Edit','Write','MultiEdit','NotebookEdit'}), f'tools={sorted(tools)}')
router=(ROOT/'.claude/hooks/skill-router.ps1').read_text(encoding='utf-8').lower()
add('router-control-plane', "route = 'turn-up-time'" in router, 'build work routes to turn-up-time')
add('router-no-engineering-loop', 'engineering-loop' not in router, 'retired router absent')
add('router-no-direct-omnidex', "route = 'omnidex'" not in router, 'router does not bypass control plane')
add('router-no-direct-boil', "route = 'boil-the-ocean'" not in router, 'router does not bypass control plane')
loop_markers={'turn-up-time':['EVIDENCE_BLOCKED','two materially different repairs','Two failed repair waves'],'omnidex':['Repair once','stop and reframe'],'boil-the-ocean':['two materially different repairs','at most two waves'],'easily-irritated':['max_rounds','Terminal states'],'its-not-you-its-me':['Promote or retire']}
for skill, markers in loop_markers.items():
    text=(ROOT/f'.claude/skills/{skill}/SKILL.md').read_text(encoding='utf-8')
    for marker in markers: add(f'loop-{skill}-{marker[:18]}', marker.lower() in text.lower(), marker)
reg=yaml.safe_load((ROOT/'.claude/capabilities/registry.yaml').read_text(encoding='utf-8'))['capabilities']
for name,cap in reg.items():
    add('cap-'+name+'-eval', bool(cap.get('eval')), cap.get('eval'))
    add('cap-'+name+'-uninstall', bool(cap.get('uninstall')), cap.get('uninstall'))
    if cap.get('bundled'): add('cap-'+name+'-provider-present', (ROOT/f".claude/skills/{cap['provider']}/SKILL.md").exists(), cap['provider'])
install=(ROOT/'scripts/install.ps1').read_text(encoding='utf-8')
add('install-dry-run-default', '[switch]$Apply' in install and 'if ($Apply)' in install, 'Apply is opt-in')
add('install-backup', 'BackupRoot' in install and 'Copy-Item $settingsPath' in install, 'conflicts/settings backed up')
add('install-preserve-settings', 'ConvertFrom-Json' in install and 'UserPromptSubmit' in install, 'settings merged, not replaced')
add('install-copies-runtime-scripts', "'.claude\\scripts'" in install, 'validator/scaffolder installed')
add('install-manifest', 'turn-up-time-install-manifest.json' in install, 'exact installed file list recorded')
add('install-notify-preserved', 'KEEP existing notification provider' in install, 'existing notification implementation is not overwritten')
patterns={'github_pat':re.compile(r'gh[pousr]_[A-Za-z0-9_]{20,}'),'openai_key':re.compile(r'sk-[A-Za-z0-9]{20,}'),'aws':re.compile(r'AKIA[0-9A-Z]{16}'),'private_key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),'windows_user':re.compile(r'C:\\Users\\[^\\\s]+',re.I),'company_domain':re.compile(r'teamtag\.com',re.I)}
alltext='\n'.join(p.read_text(encoding='utf-8',errors='replace') for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts)
for name,pat in patterns.items(): add('scan-'+name, not pat.search(alltext), 'no match')
broken=[]; link_re=re.compile(r'\[[^\]]+\]\(([^)]+)\)')
for p in ROOT.rglob('*.md'):
    if '.git' in p.parts: continue
    for target in link_re.findall(p.read_text(encoding='utf-8')):
        if target.startswith(('http://','https://','#','mailto:')): continue
        path=target.split('#',1)[0]
        if path and not (p.parent/path).resolve().exists(): broken.append(f'{p.relative_to(ROOT)} -> {target}')
add('relative-links', not broken, '; '.join(broken[:5]) or 'all resolved')
for p in ROOT.joinpath('.claude/schemas').glob('*.json'):
    try: json.loads(p.read_text(encoding='utf-8')); ok=True; detail='valid JSON'
    except Exception as e: ok=False; detail=str(e)
    add('schema-'+p.stem,ok,detail)
failed=[c for c in checks if not c[1]]
for name,ok,detail in checks: print(('PASS' if ok else 'FAIL'),name,'-',detail)
print(f'FRESH REVIEW: {len(checks)-len(failed)}/{len(checks)} passed')
report=['# Fresh review report','', 'Reviewer contract: `.claude/agents/fresh-workflow-reviewer.md`. This automated cold pass reads the final tree rather than the build script.','', f'**Verdict: {"GREEN" if not failed else "RED"} — {len(checks)-len(failed)}/{len(checks)} checks passed.**','', '## Checks','']
for name,ok,detail in checks: report.append(f'- [{"x" if ok else " "}] `{name}` — {detail}')
report += ['', '## Limits', '', '- PowerShell parser and behavior checks require Windows PowerShell 5.1; the included GitHub Actions workflow runs them on `windows-latest`.', '- This deterministic pass is not a substitute for a separate model reviewing design judgment. The repository includes a read-only fresh reviewer agent for that cold model pass.', '- External capability providers are intentionally not vendored and must be evaluated through `/plug-it-in` before activation.','']
(ROOT/'docs/REVIEW-REPORT.md').write_text('\n'.join(report),encoding='utf-8')
sys.exit(1 if failed else 0)
