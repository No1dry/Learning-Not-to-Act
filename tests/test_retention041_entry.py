"""CLI/preflight must not start other phases or weaken fixed experiment roles."""
from types import SimpleNamespace
import sys

import pytest


def test_train_cli_selects_only_explicit_new041_stage(monkeypatch):
    from egrs.retention041.__main__ import main
    calls = []
    monkeypatch.setitem(sys.modules, 'egrs.retention041.training', SimpleNamespace(
        run=lambda args: calls.append((args.config, args.output_dir, args.resume)) or 'configured'))
    assert main(['train', '--config', 'r1.json', '--output-dir', 'new-r1']) == 'configured'
    assert calls == [('r1.json', 'new-r1', None)]


@pytest.mark.parametrize('arm', ['r0', 'r1'])
def test_eval_cli_passes_experiment_arm_to_single_student_contract(monkeypatch, arm):
    from egrs.retention041.__main__ import main
    calls = []
    monkeypatch.setitem(sys.modules, 'egrs.retention041.evaluation', SimpleNamespace(
        run=lambda config, out, *, experiment_arm: calls.append((config, out, experiment_arm))))
    main(['eval', '--experiment-arm', arm, '--mode', 'run', '--config', 'eval.json', '--output', 'eval-new'])
    assert calls == [('eval.json', 'eval-new', arm)]
    with pytest.raises(SystemExit):
        main(['eval', '--experiment-arm', 'c0', '--config', 'eval.json', '--output', 'bad'])


def test_preflight_wrong_source_identity_refuses_before_policy_construction(tmp_path, monkeypatch):
    from egrs.retention041 import training
    cfg = {'experiment_arm': 'r0', 'index_dir': str(tmp_path/'index'), 'initial_adapter': str(tmp_path/'initial'),
           'teacher_adapter': None, 'benchmark_root': str(tmp_path/'core'), 'runtime': str(tmp_path/'runtime')}
    contexts = []
    monkeypatch.setattr(training, 'load_config', lambda path: cfg)
    def dataset(path, split, context):
        contexts.append(context)
        return SimpleNamespace(identity='actual040-index')
    monkeypatch.setattr(training, 'StageDataset', dataset)
    def invalid(*a, **kw): raise ValueError('040 initialization SHA mismatch')
    monkeypatch.setattr(training.adapter, 'read_source_identity', invalid)
    from egrs.augmentation import dependencies
    monkeypatch.setattr(dependencies, 'activate_core', lambda *a: pytest.fail('bad source reached policy loading'))
    with pytest.raises(ValueError, match='initialization SHA'):
        training.run(SimpleNamespace(config='c', output_dir=tmp_path/'new', resume=None))
    assert len(contexts) == 2 and contexts[0] is contexts[1]


def test_same_run_resume_and_output_protection_before_any_data_read(tmp_path, monkeypatch):
    from egrs.retention041 import training
    old = tmp_path/'completed040'; old.mkdir()
    cfg = {'experiment_arm': 'r0', 'index_dir': str(tmp_path/'index'), 'initial_adapter': str(old),
           'teacher_adapter': None, 'benchmark_root': str(tmp_path/'core'), 'runtime': str(tmp_path/'runtime')}
    monkeypatch.setattr(training, 'load_config', lambda path: cfg)
    monkeypatch.setattr(training, 'StageDataset', lambda *a, **kw: pytest.fail('invalid output reached data'))
    with pytest.raises(FileExistsError):
        training.run(SimpleNamespace(config='c', output_dir=old, resume=None))
    with pytest.raises(ValueError, match='original output'):
        training.run(SimpleNamespace(config='c', output_dir=tmp_path/'new', resume=old/'update-001000'))
    with pytest.raises(ValueError, match='overlap'):
        training.run(SimpleNamespace(config='c', output_dir=old/'child', resume=None))
