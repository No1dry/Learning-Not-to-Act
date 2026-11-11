"""One explicit039 preparation: new attempts -> bound reuse -> both indices."""
import json
from pathlib import Path
import time

from egrs.augmentation.data import identity
from .generation import generate as generate_sources
from .io import HashContext, Progress
from .plan import build_plan
from .merge import merge_exports
from .index import build_indices


def _write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def generate(config_path,output,*,source_generator=None):
    output=Path(output).resolve()
    if output.exists():
        raise FileExistsError('039 preparation requires a new output; old attempts are never overwritten')
    progress=Progress('coverage039_preparation')
    context=HashContext(progress=Progress('coverage039_files'))
    started=time.monotonic()
    plan=build_plan(config_path,context=context)
    protected=[Path(plan['config'][key]).resolve() for key in
               ('generation_config','old003_export','old_retention_index')]
    protected.append(Path(plan['data_root']).resolve())
    protected.extend(Path(value).resolve() for value in plan.get('old_dependencies',{}).get('data_roots',{}).values())
    if any(output==path or output in path.parents or path in output.parents for path in protected):
        raise ValueError('039 preparation output overlaps an immutable source/dependency')
    output.mkdir(parents=True)
    _write(output/'preparation_plan.json',plan)
    progress.update(phase='generation',completed=0,total=4)
    try:
        options={'context':context}
        if source_generator is not None:
            options['source_generator']=source_generator
        generated=generate_sources(config_path,output/'generated',**options)
        progress.update(phase='merge',completed=1,total=4)
        merged=merge_exports(plan['config']['old003_export'],generated['export'],
                             output/'merged-export',context=context)
        progress.update(phase='indices',completed=2,total=4)
        indices=build_indices(output/'merged-export',plan['config']['old_retention_index'],
                              output/'indices',context=context)
        control=indices['task_control_report']
        added=control.get('coverage039',{}).get('new_qualified_train10')
        if type(added) is not int or added < 0:
            raise ValueError('039 prepared index must bind actual new qualified training10 count')
        report={'format':'task039-coverage-preparation-report-v1','plan_identity':plan['identity'],
            'generation_export':generated['export'],'merged_export':str(output/'merged-export'),
            'retention_index':indices['retention'],'task_control_index':indices['task_control'],
            'new_qualified_train10':added,'training_ready':added>0,
            'status':'ready_for_user_training' if added else 'no_new_training10_recovered_do_not_train',
            'source_errors':generated.get('source_errors',0),
            'hash_files':context.files_read,'hash_bytes':context.bytes_read,
            'completion_percent':100.,'elapsed_seconds':time.monotonic()-started,
            'training_started':False,'evaluation_started':False,'model_loaded':False}
        report['identity']=identity(report)
        _write(output/'preparation_report.json',report)
        progress.finish(phase='prepared',completed=4,total=4,training_ready=added>0,
                        new_qualified_train10=added,files=context.files_read,bytes=context.bytes_read)
        return report
    except BaseException as error:
        _write(output/'preparation_error.json',{'error':f'{type(error).__name__}: {error}',
            'plan_identity':plan['identity'],'elapsed_seconds':time.monotonic()-started,
            'hash_files':context.files_read,'hash_bytes':context.bytes_read,
            'training_started':False,'evaluation_started':False})
        progress.finish(phase='failed',completed=0,total=4,error=f'{type(error).__name__}: {error}')
        raise
