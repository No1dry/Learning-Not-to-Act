"""New041 adapters use original fixed180 population, scoring and dual bridges."""
from pathlib import Path
from types import SimpleNamespace

from egrs.retention import evaluation as engine
from .adapter import GROUP, read_adapter_identity, validate_adapter_identity

SCHEMA = 'task041-old10-retention-eval-v1'
FACTORY = 'egrs.retention041.policy:make_policy'


def validate_adapter(identity):
    validate_adapter_identity(identity)
    if identity['update'] != 1000 or identity['final_update'] != 1000:
        raise ValueError('041 evaluation requires the fixed stage final1000 student adapter')


def _check_config(config, adapter, experiment_arm):
    if (config.get('arm') != 'c1' or config.get('experiment_arm') not in ('r0','r1')
            or config['experiment_arm'] != adapter.get('experiment_arm')):
        raise ValueError('041 configuration base or experiment arm differs from adapter')
    if experiment_arm is not None and config['experiment_arm'] != experiment_arm:
        raise ValueError('041 CLI experiment arm differs from frozen configuration')


def _check_plan(plan):
    if (plan.get('policy_factory') != FACTORY or plan.get('arm') != 'c1'
            or plan.get('experiment_arm') != plan['config']['experiment_arm']):
        raise ValueError('041 single-student factory, base or experiment arm differs')


def _spec(experiment_arm=None):
    if experiment_arm is not None and experiment_arm not in ('r0','r1'):
        raise ValueError('041 experiment arm must be r0 or r1')
    return SimpleNamespace(schema=SCHEMA, group=GROUP, factory=FACTORY, label='041',
        extra_fields={'arm','experiment_arm'}, read_adapter=read_adapter_identity,
        validate_adapter=validate_adapter,
        check_config=lambda cfg,adapter:_check_config(cfg,adapter,experiment_arm),
        plan_extra=lambda cfg:{'arm':'c1','experiment_arm':cfg['experiment_arm'],'policy_factory':FACTORY},
        check_plan=_check_plan,
        worker_extra=lambda plan:{'task_control_arm':'c1','experiment_arm':plan['config']['experiment_arm']},
        make_report=make_report,save_report=_save_report)


def build_plan(config_path, *, experiment_arm=None):
    return engine.build_plan(config_path,contract=_spec(experiment_arm))


def make_report(records, adapter, issues=None):
    validate_adapter(adapter)
    report = engine.make_report(records,adapter,issues)
    report.update(schema_version=SCHEMA,group=GROUP,arm='c1',experiment_arm=adapter['experiment_arm'])
    return report


def inspect_run(directory, *, experiment_arm=None, progress=None):
    return engine.inspect_run(directory,progress=progress,contract=_spec(experiment_arm))


def _save_report(directory, report):
    from benchmark.remaining_goals.headless.workflow import write_json
    directory = Path(directory)
    write_json(directory/'summary.json',report,update=(directory/'summary.json').exists())
    body = engine.previous.render_report(report).split('\n',1)[1]
    (directory/'report.md').write_text(
        f"# Task041 {report['experiment_arm']} (base c1): dual-condition evaluation\n"+body,encoding='utf-8')


def run(config, output, *, experiment_arm):
    return engine.run(config,output,contract=_spec(experiment_arm))


def report_run(directory, output, *, experiment_arm):
    from egrs.augmentation.evaluation import _read
    source=Path(directory).resolve();target=Path(output).resolve()
    if target==source or source in target.parents or target in source.parents:
        raise ValueError('Separate041 report output required')
    report=inspect_run(source,experiment_arm=experiment_arm,progress=lambda value:print(value,flush=True))
    batch=_read(source/'batch.json')
    report.update(cleanup_warning=batch.get('cleanup_warning'),execution_error=batch.get('execution_error'))
    target.mkdir(parents=True,exist_ok=False);_save_report(target,report)
    return report
