"""Entry points select the new data contract without changing038 algorithms."""
from types import SimpleNamespace
import sys
import json
from pathlib import Path

import pytest


def test_train_binds_shared_hash_context_and_new_dataset_before_model_loading(monkeypatch):
    from egrs.coverage039 import training
    from egrs.task_control import training as previous
    contexts=[]
    class Dataset:
        def __init__(self,index_dir,split,context):
            assert index_dir=='actual-new039-index'
            contexts.append(context)
            self.report={'coverage039':{'new_qualified_train10':1}}
    monkeypatch.setattr(training,'CoverageTaskControlDataset',Dataset)
    def old_run(args,*,dataset_factory,compact_logging):
        assert compact_logging is True
        dataset_factory(args.index_dir,split='train')
        dataset_factory(args.index_dir,split='dev')
        return 'new039-bound-to-unchanged038'
    monkeypatch.setattr(previous,'run',old_run)
    assert training.run(SimpleNamespace(index_dir='actual-new039-index'))=='new039-bound-to-unchanged038'
    assert len(contexts)==2 and contexts[0] is contexts[1]


def test_no_new_qualified_training_ten_blocks_same_old_data_training(monkeypatch):
    from egrs.coverage039 import training
    from egrs.task_control import training as previous
    monkeypatch.setattr(training,'CoverageTaskControlDataset',lambda *a,**kw:
        SimpleNamespace(report={'coverage039':{'new_qualified_train10':0}}))
    monkeypatch.setattr(previous,'run',lambda args,**kw:kw['dataset_factory'](args.index_dir,split='train'))
    with pytest.raises(ValueError,match='new|新增|recovered'):
        training.run(SimpleNamespace(index_dir='no-recovery'))


def test_compact_sampling_does_not_serialize_large_hierarchy():
    from egrs.task_control.training import sampling_log
    sampler=SimpleNamespace(main=SimpleNamespace(counts={'ten':12,'fresh':4,'raw':4},
        bin_counts={'fresh|prefix':2},hierarchy_counts={'large':999}),
        pair=SimpleNamespace(draws=1),report=lambda:pytest.fail('full dictionary built for compact log'))
    result=sampling_log(sampler,compact=True)
    assert result['pool_draw_counts']=={'ten':12,'fresh':4,'raw':4}
    assert result['pair_draws']==1
    assert 'hierarchy_draw_counts' not in result


def test_generate_cli_dispatch_has_no_implicit_training(monkeypatch):
    from egrs.coverage039.__main__ import main
    calls=[]
    monkeypatch.setitem(sys.modules,'egrs.coverage039.pipeline',SimpleNamespace(
        generate=lambda config,out:calls.append((config,out)) or {'training_started':False}))
    main(['generate','--config','approved039.json','--out','new039-run'])
    assert calls==[('approved039.json','new039-run')]


def test_one_preparation_sequences_generation_merge_indices_and_never_trains(monkeypatch,tmp_path):
    from egrs.coverage039 import pipeline
    old=tmp_path/'old003';old.mkdir();retention=tmp_path/'old036';retention.mkdir()
    calls=[];contexts=[]
    monkeypatch.setattr(pipeline,'build_plan',lambda config,context=None:{'config':{
        'old003_export':str(old),'old_retention_index':str(retention),'generation_config':str(tmp_path/'original.json')},
        'data_root':str(tmp_path/'raw'),'identity':'a'*64})
    def generation(config,out,context=None):
        calls.append('generate');contexts.append(context);out.mkdir()
        export=out/'export';export.mkdir()
        return {'export':str(export),'actual_new_train_10':2,'source_errors':0}
    def merge(old_export,new_export,out,context=None):
        calls.append('merge');contexts.append(context);out.mkdir()
        assert old_export==str(old) and Path(new_export).parts[-2:]==('generated','export')
        return {'actual_new_train_10':2}
    def indices(merged,original,out,context=None):
        calls.append('indices');contexts.append(context);out.mkdir()
        assert str(merged).endswith('merged-export') and original==str(retention)
        return {'retention':str(out/'retention'),'task_control':str(out/'task_control'),
            'retention_report':{},'task_control_report':{'coverage039':{'new_qualified_train10':2}}}
    monkeypatch.setattr(pipeline,'generate_sources',generation)
    monkeypatch.setattr(pipeline,'merge_exports',merge)
    monkeypatch.setattr(pipeline,'build_indices',indices)
    out=tmp_path/'new039'
    result=pipeline.generate('approved039.json',out)
    assert calls==['generate','merge','indices']
    assert all(c is contexts[0] for c in contexts)
    assert result['training_ready'] and result['training_started'] is False
    assert result['model_loaded'] is False
    assert json.loads((out/'preparation_report.json').read_text())['training_ready']
    with pytest.raises(FileExistsError):pipeline.generate('approved039.json',out)
    assert calls==['generate','merge','indices']


def test_compact_logging_preserves_all_038_training_tensors(tmp_path):
    from copy import deepcopy
    import torch
    from test_task_control_training import TinyDataset,tiny_policy,tiny_prediction,tiny_reference
    from egrs.task_control import training
    source=tiny_policy();states=[]
    for compact in (False,True):
        output=tmp_path/str(compact)
        training._run_loaded(SimpleNamespace(output_dir=output,arm='c1',resume=None),
            dict(training.PRESET,updates=1,save_every=1),TinyDataset(),TinyDataset('dev'),deepcopy(source),
            predict=tiny_prediction,reference_predict=tiny_reference,compact_logging=compact)
        states.append(torch.load(output/'update-000001/adapter.pt',weights_only=True))
    assert set(states[0])==set(states[1])
    assert all(torch.equal(states[0][name],states[1][name]) for name in states[0])
