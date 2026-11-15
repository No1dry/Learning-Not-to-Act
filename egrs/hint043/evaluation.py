"""043 uses the original formal180 engine, bank, score definitions and videos."""
from pathlib import Path
from types import SimpleNamespace

from egrs.retention import evaluation as engine
from .adapter import read_adapter_identity,validate
from .contracts import GROUP,require

SCHEMA='task043-hint-eval-v1'
FACTORY='egrs.hint043.policy:make_policy'


def validate_final(value):
    validate(value)
    require(value['update']==1000,'Formal evaluation uses only fixed final1000')


def check_config(cfg,adapter,arm):
    require(cfg['arm']==adapter['arm'] and (arm is None or arm==cfg['arm']), '043 requested/config/adapter arm differs')


def check_plan(plan):
    require(plan['policy_factory']==FACTORY and plan['arm']==plan['config']['arm']
        and plan.get('deployment_hint') is False,'043 plan must use the single unhinted student')


def spec(arm=None):
    require(arm in (None,'h0','h1'),'Unknown043 arm')
    return SimpleNamespace(schema=SCHEMA,group=GROUP,factory=FACTORY,label='043',extra_fields={'arm'},
        read_adapter=read_adapter_identity,validate_adapter=validate_final,
        check_config=lambda c,a:check_config(c,a,arm),
        plan_extra=lambda c:{'arm':c['arm'],'policy_factory':FACTORY,'deployment_hint':False},
        check_plan=check_plan,worker_extra=lambda p:{'hint043_arm':p['arm']},
        make_report=make_report,save_report=save_report)


def make_report(records,adapter,issues=None):
    validate_final(adapter)
    report=engine.make_report(records,adapter,issues)
    report.update(schema_version=SCHEMA,group=GROUP,arm=adapter['arm'],deployment_hint=False,
        ancestor_updates=0,additional_updates=adapter['update'],total_ancestral_updates=adapter['update'])
    return report


def save_report(directory,report):
    from .contracts import write_json
    root=Path(directory)
    write_json(root/'summary.json',report)
    body=engine.previous.render_report(report).split('\n',1)[1]
    (root/'report.md').write_text(f"# Task043 {report['arm']}: unhinted dual-condition evaluation\n"+body,encoding='utf-8')


def build_plan(config,arm=None):return engine.build_plan(config,contract=spec(arm))
def run(config,output,arm=None):return engine.run(config,output,contract=spec(arm))
