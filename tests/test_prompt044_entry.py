"""Explicit044 entry and persistent fail-stop P1-to-P2 launch, CPU only."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from test_prompt044_evaluation import config044,core,ready_config,config036


def test_evaluate_cli_only_dispatches_requested_new_run(monkeypatch):
    from egrs.prompt044.__main__ import main
    calls=[]
    monkeypatch.setitem(sys.modules,'egrs.prompt044.evaluation',SimpleNamespace(
        run=lambda config,output:calls.append((config,output)) or {'ok':True}))
    assert main(['evaluate','--config','p1.json','--output','new'])=={'ok':True}
    assert calls==[('p1.json','new')]
    with pytest.raises(SystemExit):main(['train','--config','bad'])


def test_both_cli_preserves_explicit_paths(monkeypatch):
    from egrs.prompt044.__main__ import main
    calls=[]
    monkeypatch.setitem(sys.modules,'egrs.prompt044.launch',SimpleNamespace(
        run_both=lambda **kw:calls.append(kw)))
    main(['run-both','--p1-config','one','--p2-config','two','--p1-output','a',
          '--p2-output','b','--marker','m'])
    assert calls==[dict(p1_config='one',p2_config='two',p1_output='a',p2_output='b',marker='m')]


@pytest.fixture
def launch_inputs(tmp_path,monkeypatch):
    from egrs.prompt044 import launch
    cfg={};outputs={}
    for arm in ('p1','p2'):
        cfg[arm]=tmp_path/(arm+'.json');cfg[arm].write_text(json.dumps({'variant':arm,'same':'inputs'}))
        outputs[arm]=tmp_path/('run-'+arm)
    # Pure preflight seam; production validates frozen reference/source roots.
    monkeypatch.setattr(launch,'_preflight',lambda path,output:json.loads(Path(path).read_text()))
    return dict(p1_config=cfg['p1'],p2_config=cfg['p2'],p1_output=outputs['p1'],
                p2_output=outputs['p2'],marker=tmp_path/'exclusive-marker')


def finish(output,variant,*,complete=True):
    output=Path(output);output.mkdir()
    (output/'summary.json').write_text(json.dumps({'schema_version':'task044-prompt-eval-v1',
        'variant':variant,'formal_complete':complete,'software_exit':'success' if complete else 'verification_incomplete',
        'budget':{'total':90},'formal_SR':{'numerator':45,'denominator':90,'percent':50.0} if complete else None}))


def test_fake_full_two_groups_launch_fresh_processes_and_keep_complete_marker(launch_inputs,monkeypatch):
    from egrs.prompt044 import launch
    calls=[]
    def execute(command):
        calls.append(command)
        arm='p1' if len(calls)==1 else 'p2'
        finish(command[-1],arm)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(launch,'_execute',execute)
    report=launch.run_both(**launch_inputs)
    assert report['status']=='complete'
    assert len(calls)==2 and all(c[:4]==[sys.executable,'-u','-m','egrs.prompt044'] for c in calls)
    assert all(c[4]=='evaluate' for c in calls)
    assert json.loads((launch_inputs['marker']/'status.json').read_text())['status']=='complete'
    with pytest.raises(FileExistsError):launch.run_both(**launch_inputs)
    assert len(calls)==2


@pytest.mark.parametrize('mode',['exit','incomplete','missing','raises'])
def test_first_arm_failure_never_starts_second_and_preserves_marker(launch_inputs,monkeypatch,mode):
    from egrs.prompt044 import launch
    calls=[]
    def execute(command):
        calls.append(command)
        if mode=='raises':raise RuntimeError('synthetic launch failure')
        if mode not in ('missing','exit'):finish(command[-1],'p1',complete=False)
        return SimpleNamespace(returncode=7 if mode=='exit' else 0)
    monkeypatch.setattr(launch,'_execute',execute)
    with pytest.raises((RuntimeError,FileNotFoundError,ValueError)):launch.run_both(**launch_inputs)
    assert len(calls)==1 and not Path(launch_inputs['p2_output']).exists()
    assert json.loads((launch_inputs['marker']/'status.json').read_text())['status']=='failed'
    with pytest.raises(FileExistsError):launch.run_both(**launch_inputs)


@pytest.mark.parametrize('mode',['same','nested','marker_nested','existing','wrong_arm','different_inputs'])
def test_launch_rejects_overlaps_existing_or_unmatched_pair_before_process(launch_inputs,monkeypatch,mode):
    from egrs.prompt044 import launch
    args=dict(launch_inputs)
    if mode=='same':args['p2_output']=args['p1_output']
    if mode=='nested':args['p2_output']=args['p1_output']/'child'
    if mode=='marker_nested':args['marker']=args['p1_output']/'marker'
    if mode=='existing':Path(args['p2_output']).mkdir()
    if mode=='wrong_arm':Path(args['p2_config']).write_text(json.dumps({'variant':'p1','same':'inputs'}))
    if mode=='different_inputs':Path(args['p2_config']).write_text(json.dumps({'variant':'p2','same':'changed'}))
    monkeypatch.setattr(launch,'_execute',lambda *a:pytest.fail('invalid launch started process'))
    with pytest.raises((ValueError,FileExistsError)):launch.run_both(**args)
    assert not Path(args['marker']).exists()


def test_actual_templates_and_shell_wrapper_are_explicit_and_do_not_launch():
    root=Path(__file__).resolve().parents[1]
    for arm in ('p1','p2'):
        cfg=json.loads((root/f'configs/prompt044/evaluation.{arm}.example.json').read_text())
        assert cfg['variant']==arm and cfg['schema_version']=='task044-prompt-eval-v1'
        assert not {'adapter','method_adapter','training_recipe','new_sources_00'}&cfg.keys()
    shell=(root/'scripts/prompt044/run_both_sequential.sh').read_text()
    assert 'set -euo pipefail' in shell and 'egrs.prompt044 run-both' in shell
    assert 'train ' not in shell and 'ssh ' not in shell


@pytest.mark.parametrize('arm',['p1','p2'])
def test_actual_config_templates_load_strictly_with_existing_path_expansion(tmp_path,monkeypatch,arm):
    from egrs.prompt044.evaluation import load_config
    for key in ('LNA_REFERENCE_PLAN','LNA_CORE','LNA_REPORTING','LNA_RUNTIME','LNA_LEGACY_CORE'):
        monkeypatch.setenv(key,str(tmp_path/key))
    source=Path(__file__).resolve().parents[1]/f'configs/prompt044/evaluation.{arm}.example.json'
    cfg=load_config(source)
    assert cfg['variant']==arm and Path(cfg['prompt_manifest']).is_file()
    assert cfg['base_runtime']==str(tmp_path/'LNA_RUNTIME')
    bad=json.loads(source.read_text());bad['variant']=True
    path=tmp_path/'bad.json';path.write_text(json.dumps(bad))
    with pytest.raises(ValueError):load_config(path)


@pytest.mark.parametrize('pause',[False,True])
def test_complete_fake90_then90_uses_real_preflight_and_formal_reports(config044,tmp_path,monkeypatch,pause):
    from egrs.prompt044 import evaluation,launch
    from test_prompt044_evaluation import fake_execution
    path,created,executed,read=fake_execution(config044,tmp_path,monkeypatch,pause=pause)
    first=tmp_path/'p1.json';second=tmp_path/'p2.json'
    cfg=json.loads(path.read_text());first.write_text(json.dumps(cfg))
    second.write_text(json.dumps(dict(cfg,variant='p2')))
    calls=[]
    def execute(command):
        calls.append(command)
        try:evaluation.run(command[6],command[8])
        except RuntimeError:return SimpleNamespace(returncode=1)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(launch,'_execute',execute)
    args=dict(p1_config=first,p2_config=second,p1_output=tmp_path/'p1-run',
              p2_output=tmp_path/'p2-run',marker=tmp_path/'launch-marker')
    if pause:
        with pytest.raises(RuntimeError,match='exited'):launch.run_both(**args)
        assert len(calls)==len(created)==1 and not args['p2_output'].exists()
    else:
        state=launch.run_both(**args)
        assert state['status']=='complete' and len(created)==len(calls)==2
        assert len(executed)==72 and sum(len(t['source']['episodes']) for t in executed)==180
        assert all(v['formal_SR']['denominator']==90 for v in state['variants'].values())
    with pytest.raises(FileExistsError):launch.run_both(**args)


def test_real_launcher_preflight_protects_data_root_for_marker(config044,tmp_path,monkeypatch):
    from egrs.prompt044 import launch
    path,reference=config044
    cfg=json.loads(path.read_text());second=tmp_path/'p2.json';second.write_text(json.dumps(dict(cfg,variant='p2')))
    reference['tasks'][0]['source']['source']['manifest']=str(tmp_path/'data'/'bank'/'manifest.json')
    Path(cfg['reference_plan']).write_text(json.dumps(reference))
    monkeypatch.setattr(launch,'_execute',lambda *a:pytest.fail('protected marker started process'))
    marker=tmp_path/'data'/'new-launch'
    with pytest.raises(ValueError,match='overlap'):
        launch.run_both(p1_config=path,p2_config=second,p1_output=tmp_path/'p1',p2_output=tmp_path/'p2',marker=marker)
    assert not marker.exists()
