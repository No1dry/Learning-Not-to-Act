"""New040 orchestration without native/model work; fixed038 C1 remains shared."""
from types import SimpleNamespace
import json
import sys

import pytest


def test_generate_cli_dispatches_once_without_training(monkeypatch):
    from egrs.coverage040.__main__ import main
    calls = []
    monkeypatch.setitem(sys.modules, 'egrs.coverage040.pipeline', SimpleNamespace(
        generate=lambda config, out: calls.append((config, out)) or {'training_started': False}))
    main(['generate', '--config', 'new040.json', '--output', 'new-production'])
    assert calls == [('new040.json', 'new-production')]


@pytest.mark.parametrize('arm', ['c0', 's'])
def test_cli_refuses_any_arm_except_c1(arm):
    from egrs.coverage040.__main__ import main
    with pytest.raises(SystemExit):
        main(['train', '--arm', arm, '--config', 'c', '--runtime', 'r', '--benchmark-root', 'b',
              '--index-dir', 'i', '--output-dir', 'o'])


def test_cli_eval_reuses_038_c1_run(monkeypatch):
    from egrs.coverage040.__main__ import main
    calls = []
    monkeypatch.setitem(sys.modules, 'egrs.task_control.evaluation', SimpleNamespace(
        run=lambda config, out, arm: calls.append((config, out, arm)) or {'ok': True}))
    main(['eval', '--mode', 'run', '--config', 'new-model-only.json', '--output', 'new-eval'])
    assert calls == [('new-model-only.json', 'new-eval', 'c1')]


def test_c1_training_uses_new_index_and_one_hash_context(monkeypatch):
    from egrs.coverage040 import training
    from egrs.task_control import training as original
    contexts = []
    class Dataset:
        def __init__(self, index_dir, split, context):
            assert index_dir == 'new040-index'
            contexts.append(context)
            self.report = {'coverage040': {'new_qualified_train10': 1}}
    monkeypatch.setattr(training, 'CoverageTaskControlDataset', Dataset)
    def previous(args, *, dataset_factory, compact_logging):
        assert args.arm == 'c1' and compact_logging
        dataset_factory(args.index_dir, split='train')
        dataset_factory(args.index_dir, split='dev')
        return 'same038-forward'
    monkeypatch.setattr(original, 'run', previous)
    assert training.run(SimpleNamespace(index_dir='new040-index', arm='c1')) == 'same038-forward'
    assert len(contexts) == 2 and contexts[0] is contexts[1]


@pytest.mark.parametrize('new_count', [0, None, -1, True])
def test_no_genuinely_new_train_ten_refuses_before_model_load(monkeypatch, new_count):
    from egrs.coverage040 import training
    from egrs.task_control import training as original
    monkeypatch.setattr(training, 'CoverageTaskControlDataset', lambda *args, **kw:
        SimpleNamespace(report={'coverage040': {'new_qualified_train10': new_count}}))
    monkeypatch.setattr(original, 'run', lambda args, **kw: kw['dataset_factory'](args.index_dir, split='train'))
    with pytest.raises(ValueError, match='new|train10|新增'):
        training.run(SimpleNamespace(index_dir='no-new', arm='c1'))


def test_direct_training_cannot_bypass_c1_only():
    from egrs.coverage040 import training
    with pytest.raises(ValueError, match='C1|c1'):
        training.run(SimpleNamespace(arm='c0'))


def test_one_preparation_plans_generates_and_indexes_with_shared_context(monkeypatch, tmp_path):
    from egrs.coverage040 import pipeline
    calls = []; contexts = []
    plan = {'config': {'generation_config': str(tmp_path/'original.json'),
                      'old_task_control_index': str(tmp_path/'old039-control'),
                      'old_retention_index': str(tmp_path/'old039-retention'),
                      'old_merged_export': str(tmp_path/'old039-merged')},
            'data_root': str(tmp_path/'raw'), 'sources': [{'source_id': 'fixed-train-parent'}],
            'identity': 'a'*64}
    def planning(config, context=None):
        calls.append('plan'); contexts.append(context); return plan
    def generation(config, out, *, context=None, plan=None, **kwargs):
        calls.append('generate'); contexts.append(context); out.mkdir()
        assert plan['identity'] == 'a'*64
        return {'export': str(out/'export'), 'source_errors': 0}
    def indices(old, delta, out, context=None):
        calls.append('indices'); contexts.append(context); out.mkdir()
        assert old == plan['config']['old_task_control_index']
        assert str(delta).endswith('generated/export') or str(delta).endswith('generated\\export')
        return {'retention': str(out/'retention'), 'task_control': str(out/'task_control'),
                'task_control_report': {'coverage040': {'new_qualified_train10': 2}}}
    monkeypatch.setattr(pipeline, 'build_plan', planning)
    monkeypatch.setattr(pipeline, 'generate_sources', generation)
    monkeypatch.setattr(pipeline, 'build_indices', indices)
    output = tmp_path/'new040'
    report = pipeline.generate('040.json', output)
    assert calls == ['plan', 'generate', 'indices'] and all(c is contexts[0] for c in contexts)
    assert report['new_qualified_train10'] == 2 and report['training_ready']
    assert report['training_started'] is report['evaluation_started'] is report['model_loaded'] is False
    assert json.loads((output/'preparation_report.json').read_text())['completion_percent'] == 100
    with pytest.raises(FileExistsError): pipeline.generate('040.json', output)
    assert calls == ['plan', 'generate', 'indices']


def test_preparation_cannot_overlap_old_data_or_inputs(monkeypatch, tmp_path):
    from egrs.coverage040 import pipeline
    old = tmp_path/'immutable039'
    monkeypatch.setattr(pipeline, 'build_plan', lambda *args, **kw: {
        'config': {'old_task_control_index': str(old)}, 'data_root': str(tmp_path/'raw'),
        'identity': 'a'*64, 'sources': []})
    monkeypatch.setattr(pipeline, 'generate_sources', lambda *a, **kw: pytest.fail('input overlap reached generation'))
    with pytest.raises(ValueError, match='overlap|immutable'):
        pipeline.generate('040.json', old/'child')


def test_output_unexpanded_environment_variable_refuses_before_any_plan(monkeypatch):
    from egrs.coverage040 import pipeline
    monkeypatch.delenv('TASK040_UNDEFINED_OUTPUT', raising=False)
    monkeypatch.setattr(pipeline, 'build_plan', lambda *args, **kw: pytest.fail('unresolved output reached plan'))
    with pytest.raises(ValueError, match='variable|placeholder|unresolved'):
        pipeline.generate('040.json', '$TASK040_UNDEFINED_OUTPUT/new')
