"""Independent038 adapters, original strict readers, all180 new episodes/arm."""
from pathlib import Path
from types import SimpleNamespace

from egrs.retention import evaluation as engine
from .adapter import read_adapter_identity

SCHEMA='task038-task-control-eval-v1'
GROUP='task_control_factorization'
FACTORY='egrs.task_control.policy:make_policy'


def validate_adapter(identity):
    required={'schema_version':'task038-oft-adapter-v1','group':GROUP,
              'recipe':GROUP,'update':1000,'final_update':1000}
    if (any(identity.get(key)!=value for key,value in required.items())
            or identity.get('arm') not in ('c0','c1')):
        raise ValueError('038 adapter must be c0/c1 at fixed final1000')


def _check_config(cfg,adapter,arm):
    if cfg.get('arm') not in ('c0','c1') or cfg['arm']!=adapter.get('arm'):
        raise ValueError('038 configuration and adapter arm differ')
    if arm is not None and cfg['arm']!=arm:
        raise ValueError('038 CLI arm differs from the frozen configuration')


def _check_plan(plan):
    if plan.get('policy_factory')!=FACTORY or plan.get('arm')!=plan['config']['arm']:
        raise ValueError('038 shared policy factory or arm differs')


def _spec(arm=None):
    if arm is not None and arm not in ('c0','c1'):
        raise ValueError('038 arm must be c0 or c1')
    return SimpleNamespace(schema=SCHEMA,group=GROUP,factory=FACTORY,label='038',
        extra_fields={'arm'},read_adapter=read_adapter_identity,validate_adapter=validate_adapter,
        check_config=lambda cfg,adapter:_check_config(cfg,adapter,arm),
        plan_extra=lambda cfg:{'arm':cfg['arm'],'policy_factory':FACTORY},check_plan=_check_plan,
        worker_extra=lambda plan:{'task_control_arm':plan['config']['arm']},make_report=make_report,
        save_report=_save_report)


def build_plan(config_path,*,arm=None):
    return engine.build_plan(config_path,contract=_spec(arm))


def make_report(records,adapter,issues=None):
    validate_adapter(adapter)
    report=engine.make_report(records,adapter,issues)
    report.update(schema_version=SCHEMA,group=GROUP,arm=adapter['arm'])
    return report


def inspect_run(directory,*,arm=None,progress=None):
    return engine.inspect_run(directory,progress=progress,contract=_spec(arm))


def _save_report(directory,report):
    from benchmark.remaining_goals.headless.workflow import write_json
    directory=Path(directory)
    write_json(directory/'summary.json',report,update=(directory/'summary.json').exists())
    body=engine.previous.render_report(report).split('\n',1)[1]
    (directory/'report.md').write_text(f"# Task038 {report['arm']}: dual-condition evaluation\n"+body,
                                    encoding='utf-8')


def run(config,output,*,arm):
    return engine.run(config,output,contract=_spec(arm))


def report_run(directory,output,*,arm):
    from egrs.augmentation.evaluation import _read
    source=Path(directory).resolve();target=Path(output).resolve()
    if target==source or source in target.parents or target in source.parents:
        raise ValueError('separate038 report output required')
    report=inspect_run(source,arm=arm,progress=lambda value:print(value,flush=True))
    batch=_read(source/'batch.json')
    report.update(cleanup_warning=batch.get('cleanup_warning'),execution_error=batch.get('execution_error'))
    target.mkdir(parents=True,exist_ok=False);_save_report(target,report)
    return report
