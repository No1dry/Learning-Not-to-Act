"""Synthetic original180 wiring; no policy or environment is constructed."""
from copy import deepcopy
import json
from types import ModuleType
import sys

import pytest

from test_trajectory_evaluation import core,ready_config
from test_retention_evaluation import config036
from test_hint043 import save_fake_adapter


@pytest.fixture
def config043(config036,tmp_path):
    from egrs.hint043 import evaluation as ev
    def make(arm):
        directory=tmp_path/('final-'+arm)
        _,identity=save_fake_adapter(directory,arm)
        cfg=json.loads(config036.read_text())
        cfg.update(schema_version=ev.SCHEMA,group=ev.GROUP,arm=arm,adapter=str(directory))
        target=tmp_path/('eval-'+arm+'.json');target.write_text(json.dumps(cfg))
        return target,identity
    return make


@pytest.mark.parametrize('arm',['h0','h1'])
def test_formal180_population_no_hints_and_fake_scoring(config043,tmp_path,monkeypatch,arm):
    from egrs.hint043 import evaluation as ev
    from egrs.retention import evaluation as engine
    from benchmark.remaining_goals import isolated_policy
    from benchmark.remaining_goals.headless import offline_scoring,planning,workflow
    config,identity=config043(arm)
    plan=ev.build_plan(config,arm)
    assert plan['budget']=={'10':90,'00':90,'total':180,'policy_seed':7,'max_chunk_steps':8,
        'horizon':520,'video':'all','raw_queries_actions':'all'}
    assert plan['deployment_hint'] is False and sum(len(t['source']['episodes']) for t in plan['tasks'])==180
    workers=[];episodes=[]
    class Policy:
        def __init__(self,cfg):
            assert cfg['policy_factory']==ev.FACTORY and cfg['hint043_arm']==arm
            assert not {'hint','sidecar','sidecar_dir','teacher_adapter','task_control_arm'} & cfg.keys()
            self.provenance={'policy_metadata':{'method_adapter':identity,'unnorm_key':'libero_10_no_noops'}}
            workers.append(self)
        def close(self):pass
    def execute(folder,item,plan,bind,policy):
        folder.mkdir(parents=True);refs=[]
        for i,e in enumerate(item['source']['episodes']):
            raw={'episode_id':e['episode_id'],'status':'completed'};p=folder/f'{i}.json';p.write_text(json.dumps(raw))
            refs.append({'path':p.name,'sha256':planning.file_sha(p)});episodes.append(e)
        meta={'status':'completed','error':None,'results':refs,'model_runtime':policy.provenance,
            'runtime_config':plan['base_runtime'],'protocol_version':'remaining-headless-normal00-control-v1'}
        (folder/'task_run.json').write_text(json.dumps(meta));(folder/'environment_dispatch.json').write_text('{}')
        bind({'actual':'same fake original base'});return meta
    def reader(folder,*args):
        meta=json.loads((folder/'task_run.json').read_text())
        return meta,[json.loads((folder/r['path']).read_text()) for r in meta['results']]
    def score(episode,raw,*,condition,source):
        row={**episode,'execution_status':'completed','classification':'failure' if condition=='10' else 'success',
            'official_goals_achieved':True,'failure_reasons':[],'unknown_reasons':[],'path_complete':False}
        return {'condition':condition,'primary':row,'legacy':dict(row),'source':source}
    monkeypatch.setattr(isolated_policy,'SubprocessPolicy',Policy)
    monkeypatch.setattr(engine,'_execute_task',execute);monkeypatch.setattr(engine,'_read_task',reader)
    monkeypatch.setattr(offline_scoring,'score_verified_result',score)
    output=tmp_path/('run-'+arm);report=ev.run(config,output,arm)
    assert len(workers)==1 and len(episodes)==180 and report['formal_complete']
    assert report['conditions']['10']['formal_SR']['numerator']==0
    assert report['conditions']['00']['formal_SR']['numerator']==90
    assert (output/'report.md').read_text().startswith('# Task043 '+arm)
    with pytest.raises(FileExistsError):ev.run(config,output,arm)


@pytest.mark.parametrize('arm',['h0','h1'])
def test_deployed_policy_strips_truth_does_not_load_status_or_teacher(tmp_path,monkeypatch,arm):
    from egrs.hint043 import policy,adapter
    p,v=save_fake_adapter(tmp_path/'adapter',arm);seen=[]
    p.close=lambda:None;p.reset=lambda:None;p.predict=lambda obs,text:seen.append((obs,text)) or 'actions'
    module=ModuleType('benchmark.remaining_goals.adapters.openvla_oft');module.OpenVLAOFTPolicy=lambda config:p
    transfer=ModuleType('benchmark.remaining_goals.adapters.oft_transfer');transfer.FACTORY='original:factory'
    monkeypatch.setitem(sys.modules,module.__name__,module);monkeypatch.setitem(sys.modules,transfer.__name__,transfer)
    # The fixture already installed LoRA; real runtime constructs a plain base.
    monkeypatch.setattr(adapter,'attach',lambda *args:v)
    wrapper=policy.make_policy({'method_adapter':str(tmp_path/'adapter'),'hint043_arm':arm})
    assert wrapper.predict({'images':['camera'],'proprio':[0]*8,'hint':'GT','goals':[True,False],'future':'GT'},'full instruction')=='actions'
    assert seen==[({'images':['camera'],'proprio':[0]*8},'full instruction')]
    with pytest.raises(ValueError,match='cannot receive'):
        policy.make_policy({'method_adapter':'unused','hint043_arm':arm,'sidecar_dir':'GT'})
