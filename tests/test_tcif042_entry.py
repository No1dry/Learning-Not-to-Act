"""Task042 public entries preserve fixed recipes and never chain real phases."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


@pytest.mark.parametrize('arm', ['f0', 'f1'])
def test_actual_generated_config_keeps_exact_float_recipe(tmp_path, monkeypatch, arm):
    from egrs.tcif042.config import load_config
    from egrs.task_control.training import PRESET
    for name in ('LNA_ROOT', 'LNA_CORE', 'LNA_RUNTIME'):
        monkeypatch.setenv(name, str(tmp_path/name))
    path = Path(__file__).resolve().parents[1]/'configs/tcif042'/f'training.{arm}.example.json'
    config = load_config(path)
    assert config['experiment_arm'] == arm
    assert config['training_recipe'] == PRESET
    assert type(config['training_recipe']['photometric_probability']) is float
    assert 'task041-r0-train-001' in config['initial_adapter']
    assert 'teacher_adapter' not in config
    altered = deepcopy(json.loads(path.read_text()))
    altered['training_recipe']['photometric_probability'] = 0
    bad = tmp_path/'bad.json'; bad.write_text(json.dumps(altered))
    with pytest.raises(ValueError, match='preset|recipe'):
        load_config(bad)


def test_strict_config_rejects_duplicate_extra_unresolved_or_wrong_arm(tmp_path):
    from egrs.tcif042.config import load_config
    source = Path(__file__).resolve().parents[1]/'configs/tcif042/training.f0.example.json'
    original = source.read_text()
    path = tmp_path/'bad.json'
    for changed in (original.replace('"format":', '"format":"duplicate", "format":', 1),
                    original.replace('"f0"', '"r0"'), original):
        path.write_text(changed)
        with pytest.raises(ValueError): load_config(path)
    extra = json.loads(original); extra['teacher_adapter'] = None
    path.write_text(json.dumps(extra))
    with pytest.raises(ValueError): load_config(path)


def test_cli_trains_only_explicit042_and_never_evaluates(monkeypatch):
    from egrs.tcif042.__main__ import main
    calls = []
    monkeypatch.setitem(sys.modules, 'egrs.tcif042.training', SimpleNamespace(
        run=lambda args: calls.append((args.config, args.output_dir, args.resume)) or 'ok'))
    assert main(['train', '--config', 'f0.json', '--output-dir', 'new']) == 'ok'
    assert calls == [('f0.json', 'new', None)]


@pytest.mark.parametrize('arm', ['f0', 'f1'])
def test_cli_eval_explicit_arm(monkeypatch, arm):
    from egrs.tcif042.__main__ import main
    calls = []
    monkeypatch.setitem(sys.modules, 'egrs.tcif042.evaluation', SimpleNamespace(
        run=lambda config, out, *, experiment_arm: calls.append((config, out, experiment_arm))))
    main(['eval', '--experiment-arm', arm, '--config', 'eval.json', '--output', 'new'])
    assert calls == [('eval.json', 'new', arm)]
    with pytest.raises(SystemExit):
        main(['eval', '--experiment-arm', 'c1', '--config', 'x', '--out', 'y'])


def test_preflight_source_fails_before_model_construction(tmp_path, monkeypatch):
    from egrs.tcif042 import training
    cfg = {'experiment_arm':'f0', **{k:str(tmp_path/k) for k in
        ('index_dir', 'initial_adapter', 'benchmark_root', 'runtime')}}
    monkeypatch.setattr(training, 'load_config', lambda path: cfg)
    contexts = []
    def dataset(path, split, context):
        contexts.append(context)
        return SimpleNamespace(identity='actual-index')
    monkeypatch.setattr(training, 'StageDataset', dataset)
    def invalid(*a, **kw): raise ValueError('041 R0 source SHA mismatch')
    monkeypatch.setattr(training.adapter, 'read_source_identity', invalid)
    from egrs.augmentation import dependencies
    monkeypatch.setattr(dependencies, 'activate_core', lambda *a: pytest.fail('reached model construction'))
    with pytest.raises(ValueError, match='source SHA'):
        training.run(SimpleNamespace(config='cfg', output_dir=tmp_path/'new', resume=None))
    assert len(contexts) == 2 and contexts[0] is contexts[1]


def test_outputs_and_redirected_resume_refuse_before_data(tmp_path, monkeypatch):
    from egrs.tcif042 import training
    source = tmp_path/'source'; source.mkdir()
    cfg = {'experiment_arm':'f0', 'initial_adapter':str(source), **{k:str(tmp_path/k)
        for k in ('index_dir','benchmark_root','runtime')}}
    monkeypatch.setattr(training, 'load_config', lambda path: cfg)
    monkeypatch.setattr(training, 'StageDataset', lambda *a, **kw: pytest.fail('invalid output reached data'))
    with pytest.raises(FileExistsError):
        training.run(SimpleNamespace(config='cfg', output_dir=source, resume=None))
    with pytest.raises(ValueError, match='original output'):
        training.run(SimpleNamespace(config='cfg', output_dir=tmp_path/'new', resume=source/'update-001000'))
    with pytest.raises(ValueError, match='overlap'):
        training.run(SimpleNamespace(config='cfg', output_dir=source/'child', resume=None))
