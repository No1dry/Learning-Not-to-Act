"""043 uses the original formal180 engine, bank, score definitions and videos."""
from pathlib import Path
from types import SimpleNamespace

from egrs.retention import evaluation as engine
from .adapter import read_adapter_identity,validate
from .contracts import GROUP,require

SCHEMA='task043-hint-eval-v1'
FACTORY='egrs.hint043.policy:make_policy'


def validate_final(value,checkpoint_step=1000):
    validate(value)
    require(type(checkpoint_step) is int and checkpoint_step>=1000 and checkpoint_step%1000==0
            and value['update']==checkpoint_step,'Formal evaluation requires the explicitly requested thousand-step checkpoint')


def check_config(cfg,adapter,arm):
    require(cfg['arm']==adapter['arm'] and (arm is None or arm==cfg['arm']), '043 requested/config/adapter arm differs')


def check_plan(plan,checkpoint_step=1000):
    require(plan['policy_factory']==FACTORY and plan['arm']==plan['config']['arm']
        and plan.get('deployment_hint') is False,'043 plan must use the single unhinted student')
    require(plan.get('checkpoint_step',1000)==checkpoint_step,'Requested checkpoint step differs from frozen plan')


def spec(arm=None,checkpoint_step=1000):
    require(arm in (None,'h0','h1'),'Unknown043 arm')
    return SimpleNamespace(schema=SCHEMA,group=GROUP,factory=FACTORY,label='043',extra_fields={'arm'},
        read_adapter=read_adapter_identity,validate_adapter=lambda v:validate_final(v,checkpoint_step),
        check_config=lambda c,a:check_config(c,a,arm),
        plan_extra=lambda c:{'arm':c['arm'],'policy_factory':FACTORY,'deployment_hint':False,
                              **({'checkpoint_step':checkpoint_step} if checkpoint_step!=1000 else {})},
        check_plan=lambda p:check_plan(p,checkpoint_step),
        worker_extra=lambda p:{'hint043_arm':p['arm'],
                              **({'hint043_checkpoint_step':checkpoint_step} if checkpoint_step!=1000 else {})},
        make_report=lambda records,adapter,issues=None:make_report(records,adapter,issues,checkpoint_step=checkpoint_step),
        save_report=save_report)


def make_report(records,adapter,issues=None,*,checkpoint_step=1000):
    validate_final(adapter,checkpoint_step)
    report=engine.make_report(records,adapter,issues)
    report.update(schema_version=SCHEMA,group=GROUP,arm=adapter['arm'],deployment_hint=False,
        ancestor_updates=adapter.get('continuation_parent',{}).get('update',0),
        additional_updates=adapter['update']-adapter.get('continuation_parent',{}).get('update',0),
        total_ancestral_updates=adapter['update'])
    if checkpoint_step!=1000:report['checkpoint_step']=checkpoint_step
    return report


def save_report(directory,report):
    from .contracts import write_json
    root=Path(directory)
    write_json(root/'summary.json',report)
    body=engine.previous.render_report(report).split('\n',1)[1]
    (root/'report.md').write_text(f"# Task043 {report['arm']}: unhinted dual-condition evaluation\n"+body,encoding='utf-8')


def build_plan(config,arm=None,*,checkpoint_step=1000):return engine.build_plan(config,contract=spec(arm,checkpoint_step))
def run(config,output,arm=None,*,checkpoint_step=1000):return engine.run(config,output,contract=spec(arm,checkpoint_step))
