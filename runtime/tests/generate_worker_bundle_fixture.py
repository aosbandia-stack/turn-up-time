"""Regenerate cross-language fixtures through actual assemble/export CLI calls.

Uses a fully verified local staged generation. No downloads, provider calls, task
mutation, activation, or invented application receipts. --replace-fixture only
overwrites the five named generated fixture files after both CLI calls succeed.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.claude/scripts'))
import assemble_worker_bundle as bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--generation', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--replace-fixture', action='store_true')
    args = parser.parse_args()
    names = {'authorization.json','brief.txt','manifest.json','export.json','provenance.json'}
    if args.output_dir.exists():
        bundle.plain(args.output_dir)
        if not args.replace_fixture or any(p.name not in names for p in args.output_dir.iterdir()):
            raise ValueError('Fixture destination exists or contains unmanaged files')
        for path in args.output_dir.iterdir():
            bundle.plain(path)
    source = bundle.generation(args.home, args.generation)
    commands = []
    with tempfile.TemporaryDirectory(prefix='tut-crosslanguage-') as temporary:
        worktree = Path(temporary)
        project = worktree / 'worker-bundle-crosslanguage'
        project.mkdir()
        auth = dict(schema_version=1,generation_id=args.generation,project_id=project.name,
            task_id='fixture-studio-task',build_identity='fixture-source-' + args.generation,
            stage='BUILD',role='implementation-engineer',environment='local:win32',
            capability_ids=['backend-architecture','ponytail-implementation'],
            registry_sha256=bundle.digest((source/'registry.json').read_bytes()),
            lock_sha256=bundle.digest((source/'provider-lock.json').read_bytes()))
        (project/'authorization.json').write_text(json.dumps(auth,sort_keys=True,indent=2)+'\n',encoding='utf-8')
        (project/'brief.txt').write_text('Cross-language source fixture only. Validate delivery binding; this fixture grants no live task authority.\n',encoding='utf-8')
        script = ROOT/'.claude/scripts/assemble_worker_bundle.py'
        common = ['--project',str(project),'--authorization',str(project/'authorization.json')]
        def run(arguments):
            command = [sys.executable,str(script),*arguments]
            commands.append(command)
            completed = subprocess.run(command,check=True,capture_output=True,text=True)
            return json.loads(completed.stdout)
        assembled = run(['assemble',*common,'--home',str(args.home),'--role',auth['role'],'--stage','BUILD',
            '--build-identity',auth['build_identity'],'--capability','backend-architecture',
            '--capability','ponytail-implementation','--output','manifest.json'])
        exported = run(['export-task',*common,'--worktree',str(worktree),'--manifest','manifest.json',
            '--manifest-sha256',assembled['manifest']['sha256'],'--brief-file','brief.txt','--output','export.json'])
        provenance = {'kind':'actual-python-cli-source-fixture','generation_id':args.generation,
            'generation_manifest_sha256':bundle.digest((source/'generation.json').read_bytes()),
            'registry_sha256':auth['registry_sha256'],'lock_sha256':auth['lock_sha256'],
            'assembler_sha256':bundle.digest(script.read_bytes()),'manifest':assembled['manifest'],
            'export':exported['export'],'commands':commands,
            'limitations':'Fixture task identity; no actual worker, external provider use, owner approval, or activation.'}
        (project/'provenance.json').write_text(json.dumps(provenance,sort_keys=True,indent=2)+'\n',encoding='utf-8')
        args.output_dir.mkdir(parents=True,exist_ok=True)
        bundle.plain(args.output_dir)
        for name in sorted(names):
            shutil.copyfile(project/name,args.output_dir/name)
        print(json.dumps({'status':'READY','fixture':str(args.output_dir),'manifest':assembled['manifest'],'export':exported['export']}))


if __name__ == '__main__':
    main()
