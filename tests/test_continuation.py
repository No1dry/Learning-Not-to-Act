"""Reuse completed failures too; restart only unfinished episodes in a new run."""
from copy import deepcopy
import pytest

from egrs import evaluate as ev
from egrs.continuation import collect
from tests.test_evaluate import setup,components


def only_basket(monkeypatch):
    from benchmark.remaining_goals.headless import planning
    baseline=deepcopy(planning.dry_plan(None))
    for index,row in enumerate(baseline['tasks']):
        if row['task_id']!='basket':
            baseline['tasks'][index]=dict(task_id=row['task_id'],suite=row['suite'],status='preparation_error',error='synthetic unavailable',episodes=[])
    baseline['ready_episodes']=10
    baseline['plan_sha256']=ev.digest({k:v for k,v in baseline.items() if k!='plan_sha256'})
    monkeypatch.setattr(planning,'dry_plan',lambda _:deepcopy(baseline))


def paused_after_two_failures(config,tmp_path,monkeypatch):
    parts,made,_=components(monkeypatch,violation=True)
    original=parts['policy'];calls=[0]
    def factory(cfg):
        policy=original(cfg);predict=policy.actor.predict
        def fail_third(*args):
            calls[0]+=1
            if calls[0]==3:raise RuntimeError('synthetic third episode technical failure')
            return predict(*args)
        policy.actor.predict=fail_third
        return policy
    parts['policy']=factory
    parent=tmp_path/'parent'
    with pytest.raises(RuntimeError):ev.run(config,parent,components=parts,allow_missing_sources=True)
    assert ev.inspect(parent)['counts']['classification_counts']['failure']==2
    return parent


def test_continue_retains_both_failures_runs_only_eight_and_displays_live_sr(setup,tmp_path,monkeypatch):
    only_basket(monkeypatch)
    parent=paused_after_two_failures(setup,tmp_path,monkeypatch)
    before={str(p.relative_to(parent)):ev.file_sha(p) for p in parent.rglob('*') if p.is_file()}
    parts,made,envs=components(monkeypatch)
    out=tmp_path/'continued'
    assert ev.run(setup,out,components=parts,allow_missing_sources=True,continue_from=parent)['status']=='completed_with_missing_sources'
    assert len(list(out.glob('tasks/*/raw/*.json')))==8
    assert len(made)==1 and len(envs)==1
    task=ev.read(out/'tasks/basket/task_run.json')
    assert task['inherited_episode_ids']==['basket_s000_10','basket_s001_10']
    assert task['results'][0]['episode_id']=='basket_s002_10'
    assert task['results'][0]['sidecar']=='method/episode-000001.jsonl'
    summary=ev.inspect(out)
    assert summary['counts']['successes']==8
    assert summary['counts']['classification_counts']==dict(success=8,failure=2,unknown=0,technical_error=0,missing=90)
    assert len(summary['continuation']['historical_attempts'])==1
    progress=ev.read(out/'progress.json')
    assert progress['completed']==10 and progress['inherited_completed']==2 and progress['completed_this_run']==8
    assert progress['live_success_percent']==80. and progress['successes']==8
    assert before=={str(p.relative_to(parent)):ev.file_sha(p) for p in parent.rglob('*') if p.is_file()}
    # A further explicit continuation must not instantiate models/environments
    # when all currently available outcomes have already been completed.
    again_parts,again_made,again_envs=components(monkeypatch)
    ev.run(setup,tmp_path/'all-inherited',components=again_parts,allow_missing_sources=True,continue_from=out)
    assert not again_made and not again_envs
    assert ev.inspect(tmp_path/'all-inherited')['counts']['successes']==8


def test_unverified_parent_cannot_trigger_a_new_model(setup,tmp_path,monkeypatch):
    only_basket(monkeypatch)
    parent=paused_after_two_failures(setup,tmp_path,monkeypatch)
    raw=parent/'tasks/basket/raw/basket_s000_10.json'
    raw.write_bytes(raw.read_bytes()+b' ')
    parts,made,envs=components(monkeypatch)
    with pytest.raises(ValueError,match='unverified'):
        ev.run(setup,tmp_path/'refuse',components=parts,allow_missing_sources=True,continue_from=parent)
    assert not made and not envs


def test_state_change_not_hidden_by_same_episode_id(setup,tmp_path,monkeypatch):
    only_basket(monkeypatch)
    parent=paused_after_two_failures(setup,tmp_path,monkeypatch)
    target=ev.plan(setup)
    target['tasks'][0]['episodes'][0]['state_sha256']='9'*64
    with pytest.raises(ValueError,match='source binding'):
        collect(parent,target)
