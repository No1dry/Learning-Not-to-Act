"""Reuse049 complete450 rollout/scorer with repaired private source admission."""
from pathlib import Path

from egrs.remain049 import evaluation as original
from egrs.remain049 import sources as old
from . import scope,recovery


def engine():
    namespace=old._namespace(original)
    namespace.update(helpers=scope.helpers,extension_identity=scope.extension_identity)
    original_plan=namespace['plan']
    def plan(cfg,model):
        old.activate(cfg)
        report=old.read(Path(cfg['source_bank'])/'sources.json')
        recovery.validate_recovery(report,cfg)
        return original_plan(cfg,model)
    namespace['plan']=plan
    return namespace


load_config=original.load_config


def run(cfg,output,model):return engine()['run'](cfg,output,model)
def compare(base,h1,output):return original.compare(base,h1,output)
