"""Promotion failure tests use disposable homes and explicit simulated pauses."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import promote_workflow as p


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    codex = tmp_path / 'codex'
    claude = tmp_path / 'claude'
    directory = tmp_path / 'release'
    rows = []
    values = [('codex', 'workflows/turn-up-time/run.py'), ('claude', 'skills/provider/SKILL.md'),
              ('claude', 'capabilities/registry.json'), ('claude', 'capabilities/provider-lock.json'),
              ('claude', 'provider-selection.json'), ('claude', 'capabilities/runtime-catalog.json')]
    for index, (side, relative) in enumerate(values):
        before = ('before-' + str(index)).encode() if index < 2 else None
        after = ('after-' + str(index)).encode()
        home = codex if side == 'codex' else claude
        if before:
            p.codex.atomic_write(home / relative, before)
            p.codex.atomic_write(directory / 'blobs' / (str(index) + '.before'), before)
        p.codex.atomic_write(directory / 'blobs' / (str(index) + '.after'), after)
        rows.append({'side':side,'relative':relative,'blob':str(index),
            'before_sha256':p.codex.digest(before) if before else None,'after_sha256':p.codex.digest(after)})
    plan = {'schema_version':1,'release_id':'test-release','codex_home':str(codex),'claude_home':str(claude),
            'rows':rows,'watched':{}}
    path = directory / 'release.json'
    p.codex.atomic_write(path, p.pack(plan))
    pause = tmp_path / 'controller-pause.json'
    p.codex.atomic_write(pause, p.pack({'admissions_paused':True,'release_id':'test-release'}))
    evidence = tmp_path / 'simulated-controller-status.json'
    p.codex.atomic_write(evidence, b'{"unit_test_only":true,"active_jobs":[]}')
    now = datetime.now(timezone.utc)
    receipt = dict(release_id='test-release',plan_sha256=p.hash_file(path),codex_home=str(codex),claude_home=str(claude),
        checked_at=now.isoformat(),expires_at=(now+timedelta(minutes=5)).isoformat(),active_jobs=[],interactive_sessions_paused=True,
        pause_lease={'path':str(pause),'sha256':p.hash_file(pause)},evidence=[{'path':str(evidence),'sha256':p.hash_file(evidence)}])
    quiescence = tmp_path / 'quiescence.json'
    p.codex.atomic_write(quiescence,p.pack(receipt))
    monkeypatch.setattr(p, 'verify_payload', lambda value:p.check_rows(value,'after'))
    return path, plan, quiescence


@pytest.mark.parametrize('fail_after', [1,2,6])
def test_interruption_blocks_admission_then_restores_both_homes(fixture, fail_after):
    path, plan, quiescence = fixture
    sha = p.hash_file(path)
    with pytest.raises(InterruptedError):
        p.apply(path,sha,quiescence,fail_after)
    with pytest.raises(ValueError,match='PROMOTION_ADMISSION_PAUSED'):
        p.admission_check(Path(plan['claude_home']))
    p.recover(path,sha,quiescence)
    p.check_rows(plan,'before')
    assert p.admission_check(Path(plan['claude_home'])) is None


def test_committed_cohort_and_complete_rollback(fixture):
    path, plan, receipt = fixture
    p.apply(path,p.hash_file(path),receipt)
    assert p.admission_check(Path(plan['claude_home']),'test-release')['state']=='COMMITTED'
    p.recover(path,p.hash_file(path),receipt)
    p.check_rows(plan,'before')


def test_modified_recovery_target_preserves_every_other_file(fixture):
    path, plan, receipt = fixture
    with pytest.raises(InterruptedError): p.apply(path,p.hash_file(path),receipt,2)
    target = Path(plan['claude_home'])/'skills/provider/SKILL.md'
    target.write_text('owner edit')
    prior = (Path(plan['codex_home'])/'workflows/turn-up-time/run.py').read_bytes()
    with pytest.raises(p.Error,match='Modified promotion target'): p.recover(path,p.hash_file(path),receipt)
    assert target.read_text()=='owner edit'
    assert (Path(plan['codex_home'])/'workflows/turn-up-time/run.py').read_bytes()==prior


def test_backup_corruption_refuses_before_first_recovery_write(fixture):
    path, plan, receipt = fixture
    with pytest.raises(InterruptedError): p.apply(path,p.hash_file(path),receipt,2)
    (path.parent/'blobs/0.before').write_bytes(b'corrupt')
    with pytest.raises(p.Error,match='backup/payload hash'): p.recover(path,p.hash_file(path),receipt)
    assert (Path(plan['codex_home'])/'workflows/turn-up-time/run.py').read_bytes()==b'after-0'


@pytest.mark.parametrize('field,value', [('active_jobs',['job']),('interactive_sessions_paused',False),('plan_sha256','0'*64)])
def test_quiescence_is_required_before_any_mutation(fixture,field,value):
    path, plan, receipt = fixture
    data=p.read(receipt); data[field]=value; receipt.write_bytes(p.pack(data))
    with pytest.raises(p.Error): p.apply(path,p.hash_file(path),receipt)
    p.check_rows(plan,'before')
    assert not (Path(plan['claude_home'])/p.BARRIER).exists()


def test_released_controller_pause_blocks(fixture):
    path,plan,receipt=fixture
    Path(p.read(receipt)['pause_lease']['path']).write_text('{}')
    with pytest.raises(p.Error,match='pause is not held'): p.apply(path,p.hash_file(path),receipt)
    p.check_rows(plan,'before')


@pytest.mark.parametrize('relative', ['capabilities/registry.json', 'capabilities/runtime-catalog.json'])
def test_committed_binding_tampering_blocks(fixture, relative):
    path,plan,receipt=fixture
    p.apply(path,p.hash_file(path),receipt)
    (Path(plan['claude_home'])/relative).write_text('different selected bytes')
    with pytest.raises(ValueError,match='BINDING_MISMATCH'): p.admission_check(Path(plan['claude_home']))


def test_missing_expected_release_blocks(fixture):
    _,plan,_=fixture
    with pytest.raises(ValueError,match='BINDING_MISSING'): p.admission_check(Path(plan['claude_home']),'test-release')


def test_overlap_must_match_candidate_core(tmp_path,monkeypatch):
    source=tmp_path/'source'; home=tmp_path/'provider'; generation='v1'
    root=home/'provider-generations'/generation
    for base in (source/'.claude',root):
        (base/'skills/eval-harness').mkdir(parents=True)
    (source/'.claude/skills/eval-harness/SKILL.md').write_text('core')
    (root/'skills/eval-harness/SKILL.md').write_text('wrong embedded snapshot')
    (source/'CLAUDE.md').write_text('constitution')
    (source/'.claude/capabilities').mkdir()
    for name in ['registry.json','provider-lock.json']:
        (source/'.claude/capabilities'/name).write_text('{}')
    sha=p.codex.digest(b'{}')
    monkeypatch.setattr(p.providers,'verify_generation',lambda *_:{'registry_sha256':sha,'lock_sha256':sha})
    with pytest.raises(p.Error,match='overlap mismatch'): p.claude_payload(source,home,generation)


def test_unmanaged_collision_refused_even_if_bytes_match(tmp_path,monkeypatch):
    source=tmp_path/'source'; home=tmp_path/'claude'
    p.codex.atomic_write(home/'skills/new/SKILL.md',b'new')
    monkeypatch.setattr(p,'claude_payload',lambda *_:{'skills/new/SKILL.md':b'new'})
    with pytest.raises(p.Error,match='Unmanaged Claude collision'):
        p.preflight(source,tmp_path/'codex',home,tmp_path/'providers','v1',None)


def test_unknown_sentinel_fields_refused(fixture):
    path,plan,receipt=fixture
    p.apply(path,p.hash_file(path),receipt)
    sentinel=Path(plan['claude_home'])/p.BARRIER
    value=p.read(sentinel);value['ignore_errors']=True;sentinel.write_bytes(p.pack(value))
    with pytest.raises(ValueError,match='INVALID_SENTINEL'): p.admission_check(Path(plan['claude_home']))


@pytest.mark.skipif(sys.platform != 'win32', reason='PowerShell installer is Windows-specific')
def test_shared_core_uninstall_refuses_before_mutation(tmp_path,monkeypatch):
    home=tmp_path/'claude';home.mkdir()
    sentinel=home/'owned.txt';sentinel.write_text('preserve')
    (home/p.CORE_MANIFEST).write_bytes(p.pack({'schema_version':4,'state':'shared-release','files':[]}))
    monkeypatch.setenv('TURN_UP_TIME_CLAUDE_HOME',str(home))
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/uninstall.ps1'),'-Apply'],capture_output=True,text=True)
    assert result.returncode != 0
    assert 'shared Codex + Claude release' in result.stderr
    assert sentinel.read_text()=='preserve'


@pytest.fixture
def catalog_fixture(tmp_path):
    if sys.platform != 'win32':
        pytest.skip('The qualified retained catalog is explicitly local:win32')
    runtime = tmp_path/'retained';engine=runtime/'engine';engine.mkdir(parents=True)
    executable=engine/'python.exe';executable.write_bytes(b'qualified fixture executable, never run')
    context=engine/'context.yml';context.write_bytes(b'fixed readonly context')
    codex=tmp_path/'codex.exe';codex.write_bytes(b'qualified fixture codex, never run')
    def ref(path):return {'path':path.as_posix(),'sha256':p.stream_hash(path)}
    inventory=tmp_path/'inventory.json'
    inventory.write_bytes(p.pack({'schema_version':1,'runtime_id':'test-tools','root':runtime.as_posix(),
        'managed_paths':['engine'],'exclusions':['.git'],'files':[
            {'path':path.relative_to(runtime).as_posix(),'sha256':p.stream_hash(path)} for path in [executable,context]]}))
    interpreter_inventory=tmp_path/'interpreter-inventory.json'
    interpreter=p.read(inventory);interpreter['managed_paths']=['.'];interpreter['exclusions']=['.git','Lib/site-packages']
    interpreter_inventory.write_bytes(p.pack(interpreter))
    catalog={'schema_version':1,'runtime_id':'test-tools','platform':'local:win32',
        'provider_generation':{'generation_id':'generation-v4','metadata_sha256':'1'*64},
        'codex':{'version':'0.162.1','executable':ref(codex)},'inventory':ref(inventory),
        'providers':{'rea':{'profile':'rea-javascript-v1','source_ref':'bddddccdee3129d0b1b11e32b751be2b6d501c23',
            'version':'6.3.0','node':ref(executable),'entrypoint':ref(context)},
        'serena':{'profile':'serena-readonly-v1','source_ref':'1de556f71569f3acfc0743e526dd60aca40a545e',
            'version':'2.0.0.dev0','python':ref(executable),'launcher':ref(context),'context':ref(context),
            'home_root':(tmp_path/'mutable-state').as_posix(),'interpreter_inventory':ref(interpreter_inventory)},
        'context7':{'profile':'context7-public-v1','source_ref':'522c4db4fa2e1e31f1b320f09fa8c8fab376987a',
            'endpoint':'https://mcp.context7.com/mcp','auth':'anonymous'}}}
    path=tmp_path/'catalog.json';path.write_bytes(p.pack(catalog))
    return path,engine,codex,inventory


def test_runtime_catalog_checks_full_inventory_and_generation(catalog_fixture):
    path,_,_,_=catalog_fixture
    result=p.verify_runtime_catalog(path,ROOT,'generation-v4','1'*64)
    assert result['runtime_id']=='test-tools'
    with pytest.raises(p.Error,match='generation mismatch'):
        p.verify_runtime_catalog(path,ROOT,'generation-v4','2'*64)


@pytest.mark.parametrize('injected', ['injected.py','__pycache__/injected.pyc'])
def test_runtime_inventory_rejects_unlisted_code_including_bytecode(catalog_fixture,injected):
    path,engine,_,_=catalog_fixture
    extra=engine/injected;extra.parent.mkdir(exist_ok=True);extra.write_bytes(b'injected')
    with pytest.raises(p.Error,match='inventory drift'):
        p.verify_runtime_catalog(path,ROOT,'generation-v4','1'*64)


def test_runtime_catalog_checks_external_codex_binary(catalog_fixture):
    path,_,codex,_=catalog_fixture
    codex.write_bytes(b'replaced executable')
    with pytest.raises(p.Error,match='reference drift'):
        p.verify_runtime_catalog(path,ROOT,'generation-v4','1'*64)


def test_runtime_catalog_rejects_changed_inventory_metadata(catalog_fixture):
    path,_,_,inventory=catalog_fixture
    inventory.write_bytes(b'{}')
    with pytest.raises(p.Error,match='inventory metadata changed'):
        p.verify_runtime_catalog(path,ROOT,'generation-v4','1'*64)


@pytest.fixture
def bound_install(tmp_path):
    generation = tmp_path/'codex/workflows/turn-up-time/generations/bound-test'
    source = generation/'source'
    home = tmp_path/'qualification/.claude'
    for name in ['scripts','schemas','capabilities']:
        shutil.copytree(ROOT/'.claude'/name, source/'.claude'/name)
    for relative in p.admission_check.__globals__['BINDINGS']:
        origin = ROOT/'.claude'/relative
        p.codex.atomic_write(home/relative, origin.read_bytes() if origin.is_file() else b'{}')
    p.codex.atomic_write(home/'skills/backend-architect/SKILL.md', b'Installed backend instructions')
    sentinel = {'schema_version':1,'state':'COMMITTED','release_id':'bound-test',
        'plan':str(tmp_path/'release.json'),'plan_sha256':'1'*64,
        'binding':{name:p.hash_file(home/name) for name in p.admission_check.__globals__['BINDINGS']}}
    p.codex.atomic_write(home/p.BARRIER,p.pack(sentinel))
    manifest = {'generation':str(generation),'shared_release_id':'bound-test','shared_claude_home':str(home),
        'source_inventory':{str(path.relative_to(source)).replace('\\','/'):p.hash_file(path)
            for path in (source/'.claude/scripts').glob('*.py')}}
    candidate = generation/'candidate-manifest.json'
    active = generation.parent.parent/'install-manifest.json'
    for path in [candidate,active]:p.codex.atomic_write(path,p.pack(manifest))
    return source,home,candidate,active


def test_bound_resolver_and_graph_contract_subprocess_never_consult_os_home(bound_install,tmp_path):
    source,home,_,_=bound_install
    scripts=source/'.claude/scripts'
    # Keep HOME/USERPROFILE unchanged. Even a Path.home() lookup would let stale
    # OS registries participate; make that forbidden lookup observable.
    prefix = ("from pathlib import Path\nimport sys,runpy\n"
        "Path.home=classmethod(lambda cls: (_ for _ in ()).throw(AssertionError('OS home consulted')))\n"
        f"sys.path.insert(0,{str(scripts)!r})\n")
    resolver=prefix+f"sys.argv=['resolve_capabilities','backend-architecture']\nrunpy.run_path({str(scripts/'resolve_capabilities.py')!r},run_name='__main__')"
    result=subprocess.run([sys.executable,'-B','-c',resolver],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)['status']=='READY'
    validator=prefix+("from project_contracts import check_capabilities\nerrors=[]\n"
        f"check_capabilities(Path({str(tmp_path)!r}),{{'execution_environment':'local:win32','ui':{{'applicable':False,'surfaces':[]}}}},"
        "[{'required_capabilities':['backend-architecture']}],None,False,errors)\nassert not errors,errors\n")
    result=subprocess.run([sys.executable,'-B','-c',validator],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('damage',['missing','moved-generation','wrong-home','changed-source','active-mismatch'])
def test_managed_binding_damage_fails_closed(bound_install,damage):
    source,home,candidate,active=bound_install
    value=p.read(candidate)
    if damage=='missing':candidate.unlink()
    elif damage=='changed-source':(source/'.claude/scripts/resolve_capabilities.py').write_text('modified')
    else:
        if damage=='moved-generation':value['generation']=str(source.parent.parent/'other')
        elif damage=='wrong-home':value['shared_claude_home']=str(home.parent/'absent')
        else:value['shared_release_id']='wrong-release'
        candidate.write_bytes(p.pack(value))
        if damage!='active-mismatch':active.write_bytes(p.pack(value))
    code=(f"import sys\nfrom pathlib import Path\nsys.path.insert(0,{str(source/'.claude/scripts')!r})\n"
        f"from promotion_admission import installed_home\ninstalled_home(Path({str(source/'.claude/scripts/resolve_capabilities.py')!r}))")
    result=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True)
    assert result.returncode!=0
    assert 'PROMOTION_' in result.stderr


def test_flat_shared_marker_requires_barrier(bound_install):
    _,home,_,_=bound_install
    p.codex.atomic_write(home/p.CORE_MANIFEST,p.pack({'state':'shared-release'}))
    (home/p.BARRIER).unlink()
    with pytest.raises(ValueError,match='BINDING_MISSING'):p.admission_check(home)


def test_legacy_powershell_bom_manifest_preserves_unmanaged_defaults(tmp_path,monkeypatch):
    home=tmp_path/'.claude';home.mkdir()
    (home/p.CORE_MANIFEST).write_text('{"schema_version":3,"state":"installed"}',encoding='utf-8-sig')
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    from promotion_admission import installed_home
    assert p.admission_check(home) is None
    assert installed_home(ROOT/'.claude/scripts/resolve_capabilities.py')==home


@pytest.mark.skipif(sys.platform != 'win32', reason='Actual Claude launcher is PowerShell')
def test_flat_graph_launcher_uses_own_shared_home(bound_install,monkeypatch):
    _,home,_,_=bound_install
    for name in ['promotion_admission.py','turn-up-time-graph.ps1']:
        p.codex.atomic_write(home/'scripts'/name,(ROOT/'.claude/scripts'/name).read_bytes())
    p.codex.atomic_write(home/'runtime/turn-up-time/runtime-manifest.json',p.pack({'venv_python':sys.executable}))
    value=p.read(home/p.BARRIER);value['state']='APPLYING'
    (home/p.BARRIER).write_bytes(p.pack(value))
    # An inherited legacy operator value cannot redirect a shared launcher.
    monkeypatch.setenv('TURN_UP_TIME_CLAUDE_HOME',str(home.parent/'wrong-home'))
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
        str(home/'scripts/turn-up-time-graph.ps1'),'validate-topology'],capture_output=True,text=True)
    assert result.returncode!=0
    assert 'PROMOTION_ADMISSION_PAUSED' in result.stdout+result.stderr
