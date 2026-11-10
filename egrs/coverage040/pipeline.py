"""One explicit040 preparation, never an implicit model/training/eval launch."""
import os
from pathlib import Path
import re
import time

from egrs.augmentation.data import identity
from egrs.coverage039.generation import durable_write
from egrs.coverage039.io import HashContext, Progress
from .generation import generate as generate_sources
from .index import build_indices
from .plan import build_plan


def generate(config_path, output, *, source_generator=None):
    expanded = os.path.expandvars(os.path.expanduser(str(output)))
    if re.search(r'\$[A-Za-z_{]|%[^%]+%|<[^>]+>', expanded):
        raise ValueError('Unresolved environment variable/placeholder in040 output')
    output = Path(expanded).resolve()
    if output.exists():
        raise FileExistsError('040 preparation requires new output; old attempts remain immutable')
    context = HashContext(progress=Progress('task040_files'))
    progress = Progress('task040_preparation')
    started = time.monotonic()
    plan = build_plan(config_path, context=context)
    protected = [Path(p).resolve() for key, p in plan['config'].items()
                 if key in ('generation_config', 'old_task_control_index', 'old_retention_index', 'old_merged_export')]
    protected.append(Path(plan['data_root']).resolve())
    protected.extend(Path(p).resolve() for p in plan.get('protected_paths', []))
    if any(output == root or output.is_relative_to(root) or root.is_relative_to(output) for root in protected):
        raise ValueError('040 preparation output overlaps immutable source/dependency')
    output.mkdir(parents=True)
    durable_write(output/'preparation_plan.json', plan)
    progress.update(phase='fixed_train_plan', completed=0, total=3,
                    planned_train_parents=len(plan['sources']))
    try:
        options = {'context': context, 'plan': plan}
        if source_generator is not None:
            options['source_generator'] = source_generator
        generated = generate_sources(config_path, output/'generated', **options)
        progress.update(phase='delta_indices', completed=1, total=3)
        indices = build_indices(plan['config']['old_task_control_index'], generated['export'],
                                output/'indices', context=context)
        control = indices['task_control_report']
        coverage = control.get('coverage040', {})
        added = coverage.get('new_qualified_train10')
        if type(added) is not int or added < 0:
            raise ValueError('040 index must bind actual new qualified train10 count')
        report = {'format': 'task040-preparation-report-v1', 'plan_identity': plan['identity'],
                  'generation_export': generated['export'], 'retention_index': indices['retention'],
                  'task_control_index': indices['task_control'], 'coverage040': coverage,
                  'new_qualified_train10': added, 'training_ready': added > 0,
                  'status': 'ready_for_user_c1_training' if added else 'no_new_train10_do_not_train',
                  'source_errors': generated.get('source_errors', 0),
                  'hash_files': context.files_read, 'hash_bytes': context.bytes_read,
                  'completion_percent': 100., 'elapsed_seconds': time.monotonic()-started,
                  'training_started': False, 'evaluation_started': False, 'model_loaded': False}
        report['identity'] = identity(report)
        durable_write(output/'preparation_report.json', report)
        progress.finish(phase='prepared', completed=3, total=3, training_ready=added > 0,
                        new_qualified_train10=added, files=context.files_read, bytes=context.bytes_read)
        return report
    except BaseException as error:
        durable_write(output/'preparation_error.json', {'error': f'{type(error).__name__}: {error}',
                      'plan_identity': plan['identity'], 'elapsed_seconds': time.monotonic()-started,
                      'hash_files': context.files_read, 'hash_bytes': context.bytes_read,
                      'training_started': False, 'evaluation_started': False})
        progress.finish(phase='failed', error=f'{type(error).__name__}: {error}')
        raise
