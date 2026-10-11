"""Worker delivery/use contracts: positive source fixtures plus adversarial cases."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.claude/scripts'))
import assemble_worker_bundle as b


def raw(value):
    return json.dumps(value, sort_keys=True).encode()


class WorkerBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.project = self.home / 'project'
        self.project.mkdir()
        self.gen = self.home / 'provider-generations/g1'
        skill = self.gen / 'skills/example'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_bytes(b'Apply the supplied requirement. Return observable result.\n')
        (skill / 'guide.md').write_bytes(b'Read the original acceptance before changing code.\n')
        self.cap = {'provider':'example', 'bundled':False, 'authority':'production', 'stages':['BUILD'],
                    'mode':'default', 'load_policy':'conditional', 'consumes':['ticket'], 'produces':['result'],
                    'requires':[], 'conflicts':[], 'evals':['seed'], 'uninstall':'Remove mapping.', 'provider_kind':'instruction-only'}
        self.reg = {'schema_version':3, 'capabilities':{'implement':self.cap}}
        self.lock = {'schema_version':1, 'repositories':{'example':{'url':'https://github.com/example/provider.git', 'commit':'a'*40}},
                     'packages':[{'name':'example','repository':'example','files':{p.name:{'sha256':b.digest(p.read_bytes()),'content':p.read_text()}
                                      for p in skill.iterdir()}}]}
        self.auth = {'schema_version':1, 'generation_id':'g1', 'project_id':'project', 'task_id':'ticket-1',
                     'build_identity':'build-1', 'stage':'BUILD', 'role':'implementation-engineer', 'capability_ids':['implement'],
                     'environment':'test', 'registry_sha256':'0'*64, 'lock_sha256':'0'*64}
        self.sync()
        # Unit fixtures test consumer logic; generation's own integrity checks have
        # independent provider-package tests. This stub never claims live qualification.
        self.mock = patch.object(b, 'generation', return_value=self.gen)
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def sync(self):
        for name, value, key in [('registry.json',self.reg,'registry_sha256'),('provider-lock.json',self.lock,'lock_sha256')]:
            payload = raw(value)
            (self.gen / name).write_bytes(payload)
            self.auth[key] = b.digest(payload)

    def assemble(self, **kwargs):
        args = dict(role='implementation-engineer',stage='BUILD',build_identity='build-1',requested=['implement'])
        args.update(kwargs)
        return b.assemble(self.home,self.project,self.auth,**args)

    def save(self, name, value):
        payload = value if isinstance(value,bytes) else raw(value)
        (self.project / name).write_bytes(payload)
        return {'path':name,'sha256':b.digest(payload)}

    def receipt(self):
        manifest = self.assemble()
        manifest_raw = raw(manifest)
        context = {k:self.auth[k] for k in b.IDENTITY}
        context.update(dispatch_id='dispatch-1',provider='example',manifest_sha256=b.digest(manifest_raw),
                       instruction_sha256=manifest['providers'][0]['instructions_sha256'])
        invocation = self.save('invocation.json',{**context,'worker_id':'worker-1','status':'COMPLETED'})
        output = self.save('output.txt',b'Observed useful output: the requested result.\n')
        consumer = self.save('consumer.json',{**context,'contract_id':'result','output_refs':[output],'status':'PASS'})
        verifier = self.save('verify.json',{**context,'worker_id':'worker-1','evaluator_id':'verifier-1',
                         'status':'PASS','evidence_refs':[invocation,output,consumer]})
        return manifest_raw, {**context,'schema_version':1,'capability_ids':['implement'],'status':'APPLIED',
                          'invocation_refs':[invocation],'output_refs':[output],'consumed_by':[consumer],'verification_ref':verifier}

    def validate(self, pair, **kwargs):
        options = dict(manifest_sha256=b.digest(pair[0]),dispatch_id='dispatch-1',worker_id='worker-1',evaluator_id='verifier-1')
        options.update(kwargs)
        return b.validate_receipt(self.project,*pair,self.auth,**options)

    def test_source_fixture_includes_referenced_resources_and_hashes(self):
        result = self.assemble()
        self.assertIn('original acceptance', result['providers'][0]['instructions_utf8'])
        self.assertEqual(result['required_outputs'],['result'])
        self.assertEqual(result['providers'][0]['required_outputs'],['result'])
        self.assertIsNone(result['providers'][0]['readiness_valid_until'])
        self.assertIsNone(result['providers'][0]['readiness_environment'])
        b.validate_dispatch_readiness(result,'any-local-environment')
        self.assertTrue(self.validate(self.receipt())['accepted'])

    def test_wrong_role_stage_build_or_capability(self):
        for change in [{'role':'triage-lead'},{'stage':'RELEASE'},{'build_identity':'other'},{'requested':['unknown']}]:
            with self.subTest(change=change), self.assertRaises(b.BundleError):
                self.assemble(**change)
        self.auth['stage']='RELEASE'
        with self.assertRaisesRegex(b.BundleError,'STAGE_NOT_ALLOWED'):
            self.assemble(stage='RELEASE')

    def test_absent_provider_or_unready_external_blocks(self):
        self.cap['provider_kind']='external'
        self.sync()
        with self.assertRaisesRegex(b.BundleError,'READINESS_PROOF_REQUIRED'):
            self.assemble()

    def test_external_current_readiness_is_required_and_accepted(self):
        self.cap['provider_kind']='external'
        self.cap['readiness_requirements']=['tool_access']
        self.sync()
        now=datetime.now(timezone.utc)
        evidence=self.save('readiness.txt',b'Fixture tool connectivity proof.')
        readiness={'schema_version':1,'project_id':'project','environment':'test','usage':[],
                   'receipts':[{'capability':'implement','provider':'example','status':'PASS',
                     'checked_at':now.isoformat(),'expires_at':(now+timedelta(hours=1)).isoformat(),
                     'evidence_refs':[evidence],'checks':{'tool_access':'PASS'}}]}
        manifest=self.assemble(readiness=readiness)
        self.assertEqual(manifest['providers'][0]['readiness_refs'],[evidence])
        self.assertEqual(manifest['providers'][0]['readiness_environment'],'test')
        self.assertEqual(manifest['providers'][0]['readiness_valid_until'],readiness['receipts'][0]['expires_at'])
        b.validate_dispatch_readiness(manifest,'test',now=now)
        with self.assertRaisesRegex(b.BundleError,'ENVIRONMENT_MISMATCH'):
            b.validate_dispatch_readiness(manifest,'different-host',now=now)
        with self.assertRaisesRegex(b.BundleError,'EXPIRED_BEFORE_DISPATCH'):
            b.validate_dispatch_readiness(manifest,'test',now=now+timedelta(hours=1))
        # Real TypeSafe mapping shares an external provider with its instruction
        # guidance dependency. Readiness remains required for the external cap.
        guidance={**self.cap,'provider_kind':'instruction-only','authority':'reference','requires':[]}
        self.reg['capabilities']['guidance']=guidance
        self.cap['requires']=['guidance']
        self.auth['capability_ids']=['implement','guidance']
        self.sync()
        manifest=self.assemble(readiness=readiness)
        self.assertEqual(len(manifest['providers']),1)
        self.assertEqual(manifest['providers'][0]['provider_kind'],'external')
        self.assertEqual(manifest['providers'][0]['authority'],'production')
        self.assertEqual(manifest['providers'][0]['capabilities'],['guidance','implement'])
        readiness['receipts'][0]['expires_at']=(now-timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(b.BundleError,'READINESS_EXPIRED_OR_FAILED'):
            self.assemble(readiness=readiness)
        self.cap['provider']='missing'
        self.sync()
        with self.assertRaisesRegex(b.BundleError,'REQUIRED_PROVIDER_MISSING'):
            self.assemble()

    def test_tampered_generation_pin_or_asset(self):
        (self.gen/'registry.json').write_bytes(raw({**self.reg,'unexpected':True}))
        with self.assertRaisesRegex(b.BundleError,'GENERATION_AUTHORIZATION_HASH_MISMATCH'):
            self.assemble()
        self.sync()
        (self.gen/'skills/example/guide.md').write_bytes(b'changed')
        with self.assertRaisesRegex(b.BundleError,'ARTIFACT_HASH_MISMATCH'):
            self.assemble()

    def test_case_collision_and_unknown_fields(self):
        self.lock['packages'][0]['files']['GUIDE.md']=self.lock['packages'][0]['files']['guide.md']
        self.sync()
        with self.assertRaisesRegex(b.BundleError,'COLLISION'):
            self.assemble()
        del self.lock['packages'][0]['files']['GUIDE.md']
        self.sync()
        pair=self.receipt()
        pair[1]['self_certified']=True
        with self.assertRaisesRegex(b.BundleError,'INVALID_CONTRACT'):
            self.validate(pair)

    def test_unknown_authorization_and_directory_case_collision(self):
        self.auth['grant_all']=True
        with self.assertRaisesRegex(b.BundleError,'UNKNOWN_OR_MISSING_FIELDS'):
            self.assemble()
        del self.auth['grant_all']
        (self.project/'Folder').mkdir()
        (self.project/'Folder/a').write_bytes(b'a')
        with self.assertRaisesRegex(b.BundleError,'COLLISION'):
            b.references(self.project,[{'path':'Folder/a','sha256':b.digest(b'a')},
                                       {'path':'folder/b','sha256':b.digest(b'b')}])

    def test_path_portability_and_symlink(self):
        for value in ['../secret','a/../b','/abs','C:/abs','a\\b','a//b','a/./b','a.','CON.txt','a:b','a b','a\x00b']:
            with self.subTest(value=value), self.assertRaises(b.BundleError):
                b.relative(value)
        target=self.project/'target'
        target.write_text('target')
        link=self.project/'link'
        try:
            link.symlink_to(target)
        except OSError:
            # Windows may disallow symlink creation; still exercise lstat guard.
            fake=type('Info',(),{'st_mode':0o120777,'st_file_attributes':0})()
            with patch.object(Path,'lstat',return_value=fake),self.assertRaisesRegex(b.BundleError,'SYMLINK'):
                b.plain(target)
        else:
            with self.assertRaisesRegex(b.BundleError,'SYMLINK'):
                b.confined(self.project,'link')

    def test_unused_or_empty_output_cannot_pass(self):
        for field in ['invocation_refs','output_refs','consumed_by']:
            pair=self.receipt()
            pair[1][field]=[]
            with self.subTest(field=field),self.assertRaisesRegex(b.BundleError,'EVIDENCE_REQUIRED'):
                self.validate(pair)
        pair=self.receipt()
        pair[1]['output_refs']=[self.save('empty.txt',b' \n')]
        with self.assertRaisesRegex(b.BundleError,'EMPTY_EVIDENCE'):
            self.validate(pair)

    def test_dispatch_independence_and_tamper(self):
        pair=self.receipt()
        for change in [{'manifest_sha256':'0'*64},{'dispatch_id':'other'},{'evaluator_id':'worker-1'},{'evaluator_id':'wrong'}]:
            with self.subTest(change=change),self.assertRaises(b.BundleError):
                self.validate(pair,**change)
        (self.project/'output.txt').write_bytes(b'tampered')
        with self.assertRaisesRegex(b.BundleError,'ARTIFACT_HASH_MISMATCH'):
            self.validate(pair)

    def test_incomplete_consumption_or_verification(self):
        pair=self.receipt()
        consumer=b.parse((self.project/'consumer.json').read_bytes())
        consumer['contract_id']='invented-success'
        pair[1]['consumed_by']=[self.save('consumer.json',consumer)]
        with self.assertRaisesRegex(b.BundleError,'CONSUMPTION_CONTRACT_MISMATCH'):
            self.validate(pair)

    def test_all_provider_output_contracts_must_be_consumed(self):
        self.cap['produces']=['result','security-report']
        self.sync()
        pair=self.receipt()
        with self.assertRaisesRegex(b.BundleError,'MISSING_REQUIRED_OUTPUT_CONTRACT'):
            self.validate(pair)
        context=b.parse((self.project/'consumer.json').read_bytes())
        security=self.save('security-report.txt',b'Checked the scoped threat cases; observations recorded.')
        context['contract_id']='security-report'
        context['output_refs']=[security]
        consumer=self.save('security-consumer.json',context)
        pair[1]['output_refs'].append(security)
        pair[1]['consumed_by'].append(consumer)
        verifier=b.parse((self.project/'verify.json').read_bytes())
        verifier['evidence_refs']=pair[1]['invocation_refs']+pair[1]['output_refs']+pair[1]['consumed_by']
        pair[1]['verification_ref']=self.save('verify.json',verifier)
        self.assertTrue(self.validate(pair)['accepted'])

    def test_provider_receipt_does_not_require_another_providers_outputs(self):
        other=self.gen/'skills/inspector'
        other.mkdir()
        (other/'SKILL.md').write_bytes(b'Inspect the designated requirement.\n')
        self.lock['packages'].append({'name':'inspector','repository':'example','files':{
            'SKILL.md':{'sha256':b.digest((other/'SKILL.md').read_bytes()),'content':(other/'SKILL.md').read_text()}}})
        self.reg['capabilities']['inspect']={**self.cap,'provider':'inspector','produces':['security-report'],'requires':[]}
        self.cap['requires']=['inspect']
        self.auth['capability_ids']=['implement','inspect']
        self.sync()
        pair=self.receipt()
        manifest=b.parse(pair[0])
        self.assertEqual(manifest['required_outputs'],['result','security-report'])
        self.assertEqual({p['provider']:p['required_outputs'] for p in manifest['providers']},
                         {'example':['result'],'inspector':['security-report']})
        self.assertTrue(self.validate(pair)['accepted'])
        consumer=b.parse((self.project/'consumer.json').read_bytes())
        consumer['contract_id']='security-report'
        pair[1]['consumed_by']=[self.save('consumer.json',consumer)]
        with self.assertRaisesRegex(b.BundleError,'CONSUMPTION_CONTRACT_MISMATCH'):
            self.validate(pair)

    def test_global_and_provider_contract_union_must_agree(self):
        pair=self.receipt()
        manifest=b.parse(pair[0])
        manifest['required_outputs'].append('security-report')
        with self.assertRaisesRegex(b.BundleError,'PROVIDER_OUTPUT_CONTRACT_COVERAGE_MISMATCH'):
            self.validate((raw(manifest),pair[1]))
        pair=self.receipt()
        proof=b.parse((self.project/'verify.json').read_bytes())
        proof['evidence_refs']=pair[1]['output_refs']
        pair[1]['verification_ref']=self.save('verify.json',proof)
        with self.assertRaisesRegex(b.BundleError,'VERIFICATION_COVERAGE_MISMATCH'):
            self.validate(pair)

    def test_failed_receipt_never_accepted(self):
        pair=self.receipt()
        pair[1]['status']='FAILED'
        self.assertFalse(self.validate(pair)['accepted'])

    def test_cli_receipt_and_structured_block(self):
        pair=self.receipt()
        self.save('manifest.json',pair[0])
        self.save('receipt.json',pair[1])
        self.save('auth.json',self.auth)
        cmd=[sys.executable,str(ROOT/'.claude/scripts/assemble_worker_bundle.py'),'validate-receipt',
             '--project',str(self.project),'--authorization',str(self.project/'auth.json'),
             '--manifest','manifest.json','--receipt','receipt.json','--dispatch-id','dispatch-1',
             '--manifest-sha256',b.digest(pair[0]),
             '--worker-id','worker-1','--evaluator-id','verifier-1']
        run=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertTrue(json.loads(run.stdout)['accepted'])
        cmd[cmd.index('dispatch-1')]='wrong-dispatch'
        run=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(run.returncode,2)
        self.assertEqual(json.loads(run.stdout)['status'],'BLOCKED')

    def test_cli_assembles_real_staged_generation_and_rejects_tampering(self):
        files={p.relative_to(self.gen).as_posix():b.digest(p.read_bytes()) for p in self.gen.rglob('*') if p.is_file()}
        meta={'schema_version':1,'generation_id':'g1','registry_sha256':self.auth['registry_sha256'],
              'lock_sha256':self.auth['lock_sha256'],'files':files}
        (self.gen/'generation.json').write_bytes(raw(meta))
        self.save('auth.json',self.auth)
        cmd=[sys.executable,str(ROOT/'.claude/scripts/assemble_worker_bundle.py'),'assemble',
             '--project',str(self.project),'--authorization',str(self.project/'auth.json'),
             '--home',str(self.home),'--role','implementation-engineer','--stage','BUILD',
             '--build-identity','build-1','--capability','implement','--output','bundle.json']
        run=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        result=json.loads(run.stdout)
        self.assertEqual(result['status'],'READY')
        self.assertEqual(result['manifest']['sha256'],b.digest((self.project/'bundle.json').read_bytes()))
        (self.gen/'skills/example/guide.md').write_bytes(b'Unexpected change')
        cmd[-1]='other-bundle.json'
        run=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(run.returncode,2,run.stdout+run.stderr)
        self.assertIn('MODIFIED',run.stdout)
        self.assertFalse((self.project/'other-bundle.json').exists())

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(b.BundleError,'DUPLICATE_JSON_KEY'):
            b.parse(b'{"id":1,"id":2}')

    def test_studio_binding_is_exact_manifest_identity(self):
        manifest_raw=raw(self.assemble())
        spec=b.studio_task_spec(manifest_raw,'Complete the authorized ticket.')
        self.assertEqual(spec['kind'],'tut-worker-task-v1')
        self.assertEqual(spec['authorization']['manifest_sha256'],b.digest(manifest_raw))
        self.assertEqual(spec['authorization']['selected_capabilities'],['implement'])

    def test_export_converts_project_relative_to_worktree_relative(self):
        manifest_raw=raw(self.assemble())
        self.save('manifest.json',manifest_raw)
        exported=b.export_task(self.home,self.project,'manifest.json',b.digest(manifest_raw),self.auth,'Apply ticket.')
        self.assertEqual(exported['worker_start_params']['tutCapabilityBundle']['manifestPath'],'project/manifest.json')
        self.assertEqual(exported['worker_start_params']['task'],'ticket-1')
        self.assertEqual(exported['task_spec']['authorization']['manifest_sha256'],b.digest(manifest_raw))
        outside=self.home/'different-worktree'
        outside.mkdir()
        with self.assertRaisesRegex(b.BundleError,'PROJECT_OUTSIDE_TRUSTED_WORKTREE'):
            b.export_task(outside,self.project,'manifest.json',b.digest(manifest_raw),self.auth,'Apply ticket.')
        with self.assertRaisesRegex(b.BundleError,'TRUSTED_MANIFEST_HASH_MISMATCH'):
            b.export_task(self.home,self.project,'manifest.json','0'*64,self.auth,'Apply ticket.')
        wrong={**self.auth,'task_id':'other-task'}
        with self.assertRaisesRegex(b.BundleError,'MANIFEST_AUTHORIZATION_MISMATCH'):
            b.export_task(self.home,self.project,'manifest.json',b.digest(manifest_raw),wrong,'Apply ticket.')
        with self.assertRaisesRegex(b.BundleError,'UNSAFE_PATH'):
            b.export_task(self.home,self.project,'../manifest.json',b.digest(manifest_raw),self.auth,'Apply ticket.')

    def test_cli_exports_coordinator_binding(self):
        manifest_raw=raw(self.assemble())
        self.save('manifest.json',manifest_raw)
        self.save('authorization.json',self.auth)
        self.save('brief.txt',b'Complete the already authorized test ticket.')
        cmd=[sys.executable,str(ROOT/'.claude/scripts/assemble_worker_bundle.py'),'export-task',
             '--worktree',str(self.home),'--project',str(self.project),
             '--authorization',str(self.project/'authorization.json'),'--manifest','manifest.json',
             '--manifest-sha256',b.digest(manifest_raw),'--brief-file','brief.txt','--output','coordinator-export.json']
        run=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        exported=json.loads((self.project/'coordinator-export.json').read_text())
        self.assertEqual(exported['worker_start_params']['tutCapabilityBundle']['manifestPath'],'project/manifest.json')
        self.assertEqual(exported['task_spec']['kind'],'tut-worker-task-v1')
        # Export never overwrites a previously reviewed artifact.
        run=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(run.returncode,2)
        self.assertEqual(json.loads(run.stdout)['status'],'BLOCKED')

    def test_controller_core_provenance_and_role_boundary(self):
        self.lock['repositories']['example']={'kind':'local-snapshot','source':'.claude/skills','revision':'sha256:'+'a'*64}
        self.cap['authority']='control'
        self.sync()
        with self.assertRaisesRegex(b.BundleError,'CONTROLLER_ONLY_CAPABILITY'):
            self.assemble()
        self.auth['role']='controller'
        manifest=self.assemble(role='controller')
        self.assertEqual(manifest['providers'][0]['source_ref'],'local-snapshot:.claude/skills@sha256:'+'a'*64)

    def test_canonical_frontend_21st_closure_and_missing_browser(self):
        source=b.parse((ROOT/'.claude/capabilities/registry.json').read_bytes())['capabilities']
        names=['frontend-operate','ui-operate','browser-e2e','21st-catalog']
        self.reg={'schema_version':3,'capabilities':{name:source[name] for name in names}}
        self.lock['packages']=[]
        for provider in sorted({source[name]['provider'] for name in names}):
            path=self.gen/'skills'/provider
            path.mkdir()
            payload=('Fixture instructions for '+provider).encode()
            (path/'SKILL.md').write_bytes(payload)
            self.lock['packages'].append({'name':provider,'repository':'example','files':{
                'SKILL.md':{'sha256':b.digest(payload),'content':payload.decode()}}})
        self.auth['capability_ids']=names
        self.auth['ui_surfaces']=[{'id':'app','platform':'web','purpose':'operate','stack':'react-tailwind',
                                   'flags':['21st-catalog'],'verification_capabilities':[]}]
        self.sync()
        now=datetime.now(timezone.utc)
        proof=self.save('frontend-readiness.txt',b'Fixture external readiness, no live service call.')
        readiness={'schema_version':1,'project_id':'project','environment':'test','usage':[],'receipts':[]}
        for name in ['browser-e2e','21st-catalog']:
            readiness['receipts'].append({'capability':name,'provider':source[name]['provider'],'status':'PASS',
                'checked_at':now.isoformat(),'expires_at':(now+timedelta(hours=1)).isoformat(),
                'evidence_refs':[proof],'checks':{check:'PASS' for check in {*source[name].get('readiness_requirements',[]),'tool_access'}}})
        manifest=self.assemble(requested=['frontend-operate','21st-catalog'],readiness=readiness)
        self.assertEqual(set(manifest['selected_capabilities']),set(names))
        self.assertEqual({p['provider'] for p in manifest['providers']},{'impeccable','gstack-qa-only','21st-ui'})
        readiness['receipts'][0]['checks']['browser_runtime']='FAIL'
        with self.assertRaisesRegex(b.BundleError,'READINESS_CHECK_REQUIRED:browser_runtime'):
            self.assemble(requested=['frontend-operate','21st-catalog'],readiness=readiness)
        self.auth['ui_surfaces'][0]['unexpected']=True
        with self.assertRaisesRegex(b.BundleError,'INVALID_AUTHORIZED_UI_SURFACES'):
            self.assemble(requested=['frontend-operate','21st-catalog'],readiness=readiness)


if __name__=='__main__':
    unittest.main()
