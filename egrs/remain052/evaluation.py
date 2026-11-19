"""Unchanged original450 rollout and scoring, with explicit source-version route."""
from pathlib import Path
from egrs.remain049 import sources as old, evaluation as original
from . import scope, recovery


def engine():
    namespace = old._namespace(original)
    namespace.update(helpers=scope.helpers, extension_identity=scope.extension_identity)
    original_plan = namespace['plan']
    def plan(cfg, model):
        old.activate(cfg)
        report = old.read(Path(cfg['source_bank'])/'sources.json')
        recovery.validate_recovery(report,cfg)
        return original_plan(cfg,model)
    namespace['plan'] = plan
    return namespace


load_config = original.load_config


def run(cfg,output,model):
    return engine()['run'](cfg,output,model)


def compare(base,h1,output):
    return original.compare(base,h1,output)
