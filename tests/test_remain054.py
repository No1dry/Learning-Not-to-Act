"""Targeted CPU/fake coverage; no real model or physics execution."""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture(autouse=True)
def core():
    from egrs.augmentation.dependencies import activate_core, activate_reporting
    activate_core(os.environ['EGRS049_CORE'])
    activate_reporting(os.environ['EGRS049_REPORTING'])


@pytest.mark.parametrize('arm,sha,ok', [
    ('h0', 'e361121756cc7ee25b90ccb1cb4aa296ce4ea93ac07bd0841409df09b0e16c20', True),
    ('h1', 'e361121756cc7ee25b90ccb1cb4aa296ce4ea93ac07bd0841409df09b0e16c20', False),
    ('h0', '0'*64, False)])
def test_fixed_h0_only(monkeypatch, arm, sha, ok):
    from egrs.remain054 import evaluation as e
    from egrs.hint043 import adapter, evaluation
    value = {'arm': arm, 'adapter_sha256': sha}
    monkeypatch.setattr(adapter, 'read_adapter_identity', lambda p: value)
    calls = []
    monkeypatch.setattr(evaluation, 'validate_final', lambda v, step: calls.append(step))
    if ok:
        assert e.adapter_identity('fake') == value
    else:
        with pytest.raises(ValueError, match='H0@3000'): e.adapter_identity('fake')
    assert calls == [3000]


def test_worker_h0_not_source_h1_and_no_hint_or_oracle():
    from egrs.remain054.evaluation import worker
    p = {'runtime': {'policy_factory': 'base:factory'},
         'config': {'adapter': 'source-h1'}, 'method_adapter': 'executed-h0'}
    before = deepcopy(p)
    w = worker(p)
    assert w['method_adapter'] == 'executed-h0'
    assert w['hint043_arm'] == 'h0' and w['hint043_checkpoint_step'] == 3000
    assert not {'initial_mask', 'goals', 'hint', 'remaining_goals', 'source_bank'} & w.keys()
    assert p == before


@pytest.mark.parametrize('position', ['equal', 'parent', 'child'])
def test_output_cannot_overwrite_h0(tmp_path, monkeypatch, position):
    from egrs.remain054 import evaluation as e
    monkeypatch.setattr(e.original, 'protect_output', lambda *a: None)
    adapter = tmp_path/'weights'/'h0'
    output = {'equal': adapter, 'parent': adapter.parent, 'child': adapter/'run'}[position]
    with pytest.raises(ValueError, match='H0 weights'): e.protect({}, output, adapter)


def fake_setup(tmp_path, monkeypatch, bank_sha=None):
    from egrs.remain054 import evaluation as e
    from egrs.remain049 import evaluation as old, sources
    from egrs.remain052 import scope, recovery
    cfg = {'source_bank': str(tmp_path/'bank'), 'adapter': 'immutable-source-h1'}
    population = sources.expected()
    frozen = {'schema_version': sources.SCHEMA, 'model': 'base', 'runtime': {},
        'expected': population, 'sources': [{'episodes': [x]} for x in population],
        'source_bank_sha256': bank_sha or e.BANK_SHA, 'config': deepcopy(cfg),
        'adapter_identity': None, 'plan_sha256': 'b'*64}
    monkeypatch.setattr(old, 'protect_output', lambda *a: None)
    monkeypatch.setattr(sources, 'activate', lambda *a: {})
    monkeypatch.setattr(scope, 'helpers', lambda: {})
    monkeypatch.setattr(recovery, 'validate_recovery', lambda *a: None)
    sources.write(tmp_path/'bank/sources.json', {'fake': 'bank'})
    calls = []
    def source_plan(c, model):
        assert c == cfg and model == 'base'
        calls.append(model)
        return deepcopy(frozen)
    monkeypatch.setattr(old, 'plan', source_plan)
    monkeypatch.setattr(old, '_verify_model', lambda *a: None)
    monkeypatch.setattr(e, 'adapter_identity', lambda p: {'arm': 'h0', 'adapter_sha256': e.ADAPTER_SHA})
    return e, old, sources, cfg, calls


def test_fake450_honest_binding_one_h0_worker_450_live_updates(tmp_path, monkeypatch, capsys):
    e, old, sources, cfg, plan_calls = fake_setup(tmp_path, monkeypatch)
    from benchmark.remaining_goals import isolated_policy
    from test_remain049 import _record
    workers, episodes = [], []
    class Policy:
        provenance = {}
        def __init__(self, c): workers.append(c)
        def close(self): pass
    monkeypatch.setattr(isolated_policy, 'SubprocessPolicy', Policy)
    def execute(folder, source, plan, *args):
        assert plan['model'] == 'h0' and plan['adapter_identity']['arm'] == 'h0'
        episode = source['episodes'][0]
        episodes.append(episode['episode_id'])
        folder.mkdir(parents=True)
        path = folder/'raw.json'; path.write_text('{}')
        return _record(episode, path, 'success' if episode['initial_state_index']%2 == 0 else 'failure')
    monkeypatch.setattr(old, 'execute_episode', execute)
    out = tmp_path/'run'
    report = e.run(cfg, out, tmp_path/'h0')
    assert plan_calls == ['base']  # source planning only, not a base worker
    assert len(workers) == 1 and workers[0]['hint043_arm'] == 'h0'
    assert len(episodes) == len(set(episodes)) == 450
    assert report['model'] == 'h0' and report['software_exit'] == 'success'
    assert report['counts']['formal_SR'] == {'numerator': 225, 'denominator': 450, 'percent': 50.0}
    assert len(report['tasks']) == 9 and all(t['formal_SR']['denominator'] == 50 for t in report['tasks'])
    frozen = sources.read(out/'plan.json')
    assert frozen['config'] == cfg and frozen['config']['adapter'] == 'immutable-source-h1'
    assert frozen['method_adapter'] == str(tmp_path/'h0')
    assert frozen['validation_extension']['index_domain'] == [0,49]
    assert capsys.readouterr().out.count('overall_SR=') == 450


def test_changed_bank_stops_before_any_worker(tmp_path, monkeypatch):
    e, old, sources, cfg, calls = fake_setup(tmp_path, monkeypatch, '0'*64)
    with pytest.raises(ValueError, match='exact completed053'): e.run(cfg, tmp_path/'out', tmp_path/'h0')
    assert not (tmp_path/'out').exists()


def test_fresh_cli_activates_before_adapter_or_benchmark_dependent_engine(tmp_path):
    from egrs.remain049.sources import SCHEMA, write
    repo = Path(__file__).resolve().parents[1]
    cfg = {'schema_version': SCHEMA, 'benchmark_root': os.environ['EGRS049_CORE'],
        'reporting_root': os.environ['EGRS049_REPORTING'], 'legacy_root': os.environ['EGRS049_LEGACY'],
        'reference_config': str(tmp_path/'inputs/ref.json'), 'base_runtime': str(tmp_path/'inputs/runtime.json'),
        'adapter': str(tmp_path/'h1'), 'source_bank': str(tmp_path/'bank')}
    config = tmp_path/'inputs/evaluation.json'; write(config, cfg)
    script = '''
import sys
from pathlib import Path
from egrs.remain054 import evaluation as e
from egrs.remain054.__main__ import main
assert 'benchmark' not in sys.modules
class CPUStop(Exception): pass
def stop(directory):
    assert 'benchmark' in sys.modules and 'torch' not in sys.modules
    assert not any(k.startswith('libero.libero.envs') for k in sys.modules)
    raise CPUStop()
e.adapter_identity = stop
try:
    main(['--source-config',sys.argv[1],'--adapter',sys.argv[2],'--output',sys.argv[3]])
except CPUStop:
    assert not Path(sys.argv[3]).exists()
    print('FRESH054_CLI_READY_NO_MODEL_OR_PHYSICS')
else: raise AssertionError('CPU stop bypassed')
'''
    env = {**os.environ, 'PYTHONPATH': str(repo), 'CUDA_VISIBLE_DEVICES': '', 'PYTHONDONTWRITEBYTECODE': '1'}
    r = subprocess.run([sys.executable, '-c', script, str(config), str(tmp_path/'h0'), str(tmp_path/'out')],
                       cwd=repo, env=env, text=True, capture_output=True)
    assert r.returncode == 0, r.stdout+r.stderr
    assert 'FRESH054_CLI_READY_NO_MODEL_OR_PHYSICS' in r.stdout
