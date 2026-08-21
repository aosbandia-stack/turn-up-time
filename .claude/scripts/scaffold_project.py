#!/usr/bin/env python3
from pathlib import Path
import json, sys
if len(sys.argv)!=2: raise SystemExit('usage: scaffold_project.py <project-id>')
project_id=sys.argv[1]
root=Path.cwd()/'.claude/projects'/project_id
root.mkdir(parents=True,exist_ok=False)
ledger={'project_id':project_id,'tier':'C','profile':'standard','stage':'INTAKE','status':'ACTIVE','objective':'','spawn_budget':5,'spawn_log':[],'decisions':[],'risks':[],'artifacts':{},'build_identity':None}
(root/'project-ledger.json').write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf-8')
print(root)
