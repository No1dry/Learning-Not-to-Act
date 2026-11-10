"""Actual039 recording/export/index consumed by the unchanged038 tiny trainer."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import subprocess
import sys

import numpy as np
import torch

from test_coverage039_data import coverage_inputs
from test_retention_data import prepared
from test_task_control_index import control_sources
from test_task_control_training import tiny_policy, tiny_prediction, tiny_reference


def test_recorded_export_merge_indices_and_both_038_arms_consume_new_data(coverage_inputs,tmp_path):
    from egrs.augmentation.data import read_json
    from egrs.coverage039.recipe import generation_context
    from egrs.coverage039.merge import merge_exports
    from egrs.coverage039.index import build_indices
    from egrs.coverage039.data import CoverageTaskControlDataset
    from egrs.coverage039.io import HashContext
    from egrs.trajectory_augmentation.data import export_generated
    from egrs.trajectory_augmentation.native import TEACHER_V2
    from egrs.task_control import training
    from egrs.task_control.adapter import read_adapter_identity
    from egrs.task_control.evaluation import validate_adapter
    old,_,retention=coverage_inputs
    original=read_json(old/'sources.json');parent=next(p for p in original['parents'] if p['split']=='train')
    old_lineage=next(iter(original['sources'].values()))
    layout=read_json(old.parent/old_lineage['lineage_path'])['native']['joint_layout']
    context=HashContext();root=tmp_path/'recorded039';root.mkdir()
    config={'teacher_policy':TEACHER_V2,'recipe':{'horizon':30,'bridge_stage_steps':2},
        'save_video':False,'_plan_identity':'f'*64,
        'stats_sha256':parent['mapping']['action_normalization']['stats_sha256'],
        'unnorm_key':'libero_10_no_noops'}
    # Match production's separate NumPy recorder and Torch trainer processes.
    # This host's two OpenMP distributions cannot safely coexist after SVD;
    # do not suppress the runtime's duplicate-library diagnostic.
    request=tmp_path/'fake_recorder_request.json';result_path=tmp_path/'fake_recorder_result.json'
    request.write_text(json.dumps({'parent':parent,'layout':layout,'config':config,
        'root':str(root),'result':str(result_path)}),encoding='utf-8')
    subprocess.run([sys.executable,str(Path(__file__).with_name('coverage039_recorded_worker.py')),str(request)],
        cwd=Path(__file__).resolve().parents[1],check=True,capture_output=True,text=True)
    generated=json.loads(result_path.read_text(encoding='utf-8'))
    assert len(generated['attempts'])==4 and all(a['qualified'] for a in generated['attempts'])
    export=root/'export'
    export_generated(original['parents'],generated['attempts'],root,export,
        generation_context=generation_context('f'*64,normal_attempts=1,ten_attempts=3),context=context)
    merged=tmp_path/'merged';merge_exports(old,export,merged,context=context)
    prepared=build_indices(merged,retention,tmp_path/'indices',context=context)
    train=CoverageTaskControlDataset(prepared['task_control'],'train',context=context)
    dev=CoverageTaskControlDataset(prepared['task_control'],'dev',context=context)
    assert train.report['coverage039']['new_qualified_train10']==3
    assert any(row['source_id'].startswith('ten|new039|') for row in train.rows)
    assert len(train.pairs)==3 and all(pair['evidence']['recorded_nonrobot_max_abs_difference']==0 for pair in train.pairs)
    source=tiny_policy();mapping=parent['mapping']
    source.model.norm_stats={'libero_10_no_noops':{kind:{key:mapping[kind+'_normalization'][key]
        for key in ('q01','q99','mask')} for kind in ('action','proprio')}}
    calls=[];identities=[]
    for arm in ('c0','c1'):
        seen=[]
        def predict(policy,item):
            seen.append((float(item['proprio'][0]),int(item['images'][0][0,0,0])))
            return tiny_prediction(policy,item)
        args=SimpleNamespace(arm=arm,output_dir=tmp_path/arm,resume=None)
        training._run_loaded(args,dict(training.PRESET,updates=1,save_every=1),train,dev,deepcopy(source),
            predict=predict,reference_predict=tiny_reference,compact_logging=True)
        saved=read_adapter_identity(tmp_path/arm/'update-000001');identities.append(saved)
        assert saved['index_identity']==train.identity and saved['arm']==arm
        assert saved['reference_calls']['train']==8
        # Fixed-final eval rejects this intentionally shortened CPU checkpoint.
        try:validate_adapter(saved)
        except ValueError:pass
        else:raise AssertionError('fake early checkpoint admitted to formal evaluation')
        calls.append(seen)
    assert calls[0]==calls[1]
    assert identities[0]['index_identity']==identities[1]['index_identity']
