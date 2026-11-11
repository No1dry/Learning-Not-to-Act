"""Only explicitly selected CLI operations may execute work."""
import sys
from types import SimpleNamespace

import pytest


def test_index_dispatch_binds_all_three_paths(monkeypatch):
    from egrs.task_control.__main__ import main
    calls=[]
    monkeypatch.setitem(sys.modules,'egrs.task_control.index',SimpleNamespace(
        build_index=lambda *args:calls.append(args) or {'available':False}))
    main(['index','--generated-export','old003','--retention-index','old036','--out','new038'])
    assert calls==[('old003','old036','new038')]


def test_train_requires_arm_before_loading_training_module(monkeypatch):
    from egrs.task_control.__main__ import main
    with pytest.raises(SystemExit):
        main(['train','--config','recipe','--runtime','base','--benchmark-root','core',
              '--index-dir','index','--output-dir','new038'])


def test_eval_defaults_to_file_only_plan_and_keeps_arm(monkeypatch,tmp_path):
    from egrs.task_control.__main__ import main
    calls=[]
    monkeypatch.setitem(sys.modules,'egrs.task_control.evaluation',SimpleNamespace(
        build_plan=lambda config,**kwargs:calls.append((config,kwargs)) or {'simulation_created':False}))
    output=tmp_path/'plan.json'
    main(['eval','--arm','c1','--config','eval-c1.json','--out',str(output)])
    assert calls==[('eval-c1.json',{'arm':'c1'})]
    assert output.is_file()
    with pytest.raises(FileExistsError):
        main(['eval','--arm','c1','--config','eval-c1.json','--out',str(output)])
