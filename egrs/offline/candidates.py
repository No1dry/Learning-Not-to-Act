"""Sequential weak candidates with frozen legal history and explicit failures."""
import copy
import json
from .common import seal, verify, save, new_output
from .teacher import OfflineTeacher


def registry_candidates(inventory, output, *, teacher_factory=OfflineTeacher):
    verify(inventory, 'egrs.inventory.v1')
    output = new_output(output)
    result = {'format': 'egrs.registry-candidates.v1', 'inventory_id': inventory['identity'],
              'registries': {}, 'attempts': [], 'calls': 0}
    save(output / 'registries.partial.json', result)
    teacher = teacher_factory()
    result['teacher'] = teacher.metadata
    try:
        for source in inventory['sources']:
            key = source['instruction_id']
            if key in result['registries']:
                continue
            attempt = teacher.registry(source['instruction'])
            result['attempts'].append(dict(attempt, instruction_id=key))
            result['registries'][key] = {'instruction': source['instruction'], 'registry': attempt['answer'],
                'confirmed': False, 'provenance': 'weak', 'error': attempt['error']}
            result['calls'] = teacher.calls
            save(output / 'registries.partial.json', result)
    finally:
        teacher.close()
    save(output / 'registries.json', result)
    return seal(result)


def candidates(prepared, output, *, teacher_factory=OfflineTeacher, core_info=None):
    from egrs.memory import EvidenceMemory
    verify(prepared, 'egrs.windows.v1')
    output = new_output(output)
    result = {'format': 'egrs.candidates.v1', 'prepared_id': prepared['identity'], 'inventory_id': prepared['inventory_id'],
        'source_splits': prepared['source_splits'], 'planned_sources': prepared['planned_sources'],
        'windows': [{k: copy.deepcopy(v) for k, v in w.items() if k != 'samples'} for w in prepared['windows']],
        'gaps': copy.deepcopy(prepared['gaps']), 'core_dependency': core_info, 'samples': [], 'attempts': [],
        'counts': {'attempted': 0, 'succeeded': 0, 'failed': 0, 'unattempted': 0}}
    save(output / 'candidates.partial.json', result)
    teacher = teacher_factory()
    result['teacher'] = teacher.metadata
    # Append one completed attempt at a time: rewriting a full 3,600-query
    # multimodal audit after every query would make filesystem work quadratic.
    save(output / 'candidates.partial.json', {**result, 'journal': 'candidates.partial.jsonl'})
    try:
        for window in prepared['windows']:
            memory = EvidenceMemory(window['samples'][0]['payload']['context']['registry'])
            failed = False
            for original in window['samples']:
                sample = copy.deepcopy(original)
                sample['payload']['context']['history'] = copy.deepcopy(memory.records)
                sample['history_provenance'] = {str(h['query_id']): 'model_prediction' for h in memory.records}
                if failed:
                    attempt = {'attempted': False, 'answer': None, 'raw': None, 'error': 'unattempted: preceding query failed in this window', 'elapsed_seconds': 0}
                    result['counts']['unattempted'] += 1
                else:
                    attempt = teacher.predict(sample['payload'])
                    result['counts']['attempted'] += 1
                    if attempt['error'] is None:
                        sample['answer'] = attempt['answer']
                        sample['provenance'] = {'': 'weak'}
                        memory.update(sample['answer'])
                        result['counts']['succeeded'] += 1
                    else:
                        failed = True
                        result['counts']['failed'] += 1
                result['samples'].append(sample)
                result['attempts'].append(dict(attempt, sample_id=sample['sample_id']))
                with (output / 'candidates.partial.jsonl').open('a', encoding='utf-8') as journal:
                    journal.write(json.dumps({'sample': sample, 'attempt': result['attempts'][-1]}, ensure_ascii=False, allow_nan=False) + '\n')
    finally:
        teacher.close()
    save(output / 'candidates.json', result)
    return seal(result)
