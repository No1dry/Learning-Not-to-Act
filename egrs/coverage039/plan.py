"""Pure JSON plan for the approved three-task recovery, without native replay."""
from collections import Counter
from copy import deepcopy
from pathlib import Path

from egrs.augmentation.data import identity, read_json
from egrs.trajectory_augmentation.cli import build_plan as original_plan
from egrs.trajectory_augmentation.native import TEACHER_V2
from .io import HashContext
from .recipe import ALGORITHM, BUDGET, RECIPE, TASKS, generation_context

CONFIG = 'task039-coverage-recovery-config-v1'


def _old_metadata(cfg, original, context):
    """Fail on unusable existing references before spending any new native slot.

    Only JSON/window bytes and filesystem stats are inspected. In particular,
    no HDF, RGB, audit facts, or teacher qualification is replayed or rejudged.
    """
    from egrs.augmentation.data import _require
    from egrs.retention import data as retention
    from .merge import _load_export, _lines
    old_dir = Path(cfg['old003_export']); ret_dir = Path(cfg['old_retention_index'])
    old, old_report, _, inputs = _load_export(old_dir, context)
    _require(dict(Counter(s['domain'] for s in old['sources'].values())) == {'10': 221, 'normal': 75},
             'old003 must retain approved221 ten/75 normal metadata')
    parents = {p['source_id']: p for p in original['sources']}
    old_parents = {p['source_id']: p for p in old['parents']}
    fields = ('source_id', 'parent_demo_id', 'source_group', 'split', 'task_key', 'file', 'file_sha256',
              'episode', 'instruction', 'physical_ancestry', 'mapping', 'active_goals', 'invariant_predicates')
    _require(len(old['parents']) == 180 and set(old_parents) == set(parents) and
             all(all(old_parents[sid].get(k) == p.get(k) for k in fields) for sid, p in parents.items()),
             'old003 complete original180 parent path/group/split identity differs')
    _require({s['task_key'] for s in old['sources'].values()} == {p['task_key'] for p in parents.values()}-set(TASKS),
             'old003 original six-task coverage metadata differs')
    manifest = read_json(ret_dir/'sources.json'); report = read_json(ret_dir/'report.json')
    _require(manifest.get('format') == retention.DATA_KIND and report.get('data_kind') == retention.DATA_KIND
             and identity(manifest) == manifest.get('identity') == report.get('sources_identity')
             and identity(report) == report.get('identity'), 'old036 retention metadata identity differs')
    context.verify(ret_dir/'rows.jsonl', report['rows_sha256'])
    inputs.update({str((ret_dir/name).resolve()): context.sha256(ret_dir/name)
                   for name in ('sources.json', 'report.json', 'rows.jsonl')})
    expected_inputs = {str(Path(original['config']['manifest']).resolve())}
    expected_inputs.update(str((old_dir/name).resolve()) for name in ('sources.json', 'report.json', 'windows.jsonl'))
    _require(set(manifest.get('inputs', {})) == expected_inputs, 'old036 original metadata references differ')
    for path, digest in manifest['inputs'].items(): context.verify(path, digest)
    roots = manifest.get('data_roots', {})
    _require(set(roots) == {'raw', 'generated'}
             and Path(roots['raw']).resolve() == Path(original['data_root']).resolve()
             and Path(roots['generated']).resolve() == Path(old['data_root']).resolve(),
             'old036 raw/generated root is not bound to original180/old003')
    _require(manifest.get('statistics') == {'key': retention.STATS_KEY, 'sha256': retention.STATS_SHA},
             'old036 original statistics binding differs')
    kept_parents = manifest.get('parents', {})
    parent_fields = ('source_id', 'parent_demo_id', 'source_group', 'split', 'task_key', 'file',
                     'file_sha256', 'episode', 'instruction', 'physical_ancestry')
    _require(set(kept_parents) == set(parents) and
             all(all(kept_parents[sid].get(k) == p.get(k) for k in parent_fields) for sid, p in parents.items()),
             'old036 complete original180 parent path/group/split identity differs')
    sources = manifest.get('sources', {})
    counts = {pool: {split: sum(s['pool'] == pool and s['split'] == split for s in sources.values())
                     for split in ('train', 'dev')} for pool in retention.POOLS}
    _require(counts == retention.EXPECTED_COUNTS == report.get('pool_counts'),
             'old036 approved161/60 ten55/20 fresh136/44 raw metadata counts differ')
    expected_generated = {('ten|' if s['domain'] == '10' else 'fresh|')+sid: s
                          for sid, s in old['sources'].items()}
    _require({sid for sid, s in sources.items() if s['pool'] != 'raw'} == set(expected_generated),
             'old036 generated sources are not the unchanged old003 set')
    _require({sid for sid, s in sources.items() if s['pool'] == 'raw'} == {'raw|'+sid for sid in parents},
             'old036 raw source set differs from original180')
    for sid, source in sources.items():
        _require(source.get('source_id') == sid, 'old036 source identity differs')
        before = parents[source['parent_demo_id']] if source['pool'] == 'raw' else expected_generated[sid]
        check_fields = ('file', 'file_sha256', 'episode', 'parent_demo_id', 'source_group', 'split', 'task_key', 'instruction')
        _require(all(source.get(k) == before.get(k) for k in check_fields),
                 'old036 source changed its original parent/archive evidence')
        if source['pool'] == 'ten':
            _require(source.get('original_source') == before, 'old036 original ten teacher evidence differs')
        _require(source.get('root_key') == ('raw' if source['pool'] == 'raw' else 'generated'),
                 'old036 source root key differs')
    rows = _lines(ret_dir/'rows.jsonl'); seen = set()
    for row in rows:
        source = sources.get(row.get('source_id')); index = row.get('observation_index')
        _require(source is not None and type(index) is int and 0 <= index < source['observation_count']
                 and all(row.get(k) == source.get(k) for k in
                         ('pool', 'parent_demo_id', 'source_group', 'split', 'task_key', 'instruction')),
                 'old036 retained observation row binding differs')
        _require((row['source_id'], index) not in seen, 'old036 duplicate observation row')
        seen.add((row['source_id'], index))
    _require(report.get('rows') == len(rows) and seen == {(sid, i) for sid, source in sources.items()
        for i in range(source['original_source']['length'] if source['pool'] == 'ten' else source['observation_count'])},
        'old036 retained observation rows are incomplete')
    # Bound paths and file existence now, leaving byte/shape verification to
    # the same run's merge/index stages with their shared live HashContext.
    checked = set()
    for source in old['sources'].values():
        for key in ('file', 'audit_path', 'lineage_path', 'qualification_path', 'journal_path'):
            if key in ('file', 'audit_path', 'lineage_path'):
                _require(source.get(key), 'old003 recorded HDF/audit/lineage reference missing')
            if source.get(key): checked.add(retention._contained(Path(old['data_root']).resolve(), source[key]))
    for source in sources.values():
        checked.add(retention._contained(Path(roots[source['root_key']]).resolve(), source['file']))
    for artifact in checked:
        _require(artifact.is_file(), 'old039 dependency artifact missing: '+str(artifact))
    return {'old003_identity': old['identity'], 'old_retention_identity': manifest['identity'],
            'metadata_inputs': inputs, 'artifact_files_stat_checked': len(checked),
            'hdf_contents_read': False, 'old_qualification_rejudged': False,
            'data_roots': {key: str(Path(value).resolve()) for key, value in roots.items()}}


def build_plan(config_path, context=None):
    """Validate the entire original180 before selecting natural first20 parents."""
    context = context if context is not None else HashContext()
    path = Path(config_path).expanduser().resolve(strict=True)
    cfg = read_json(path)
    if (set(cfg) != {'format', 'generation_config', 'old003_export', 'old_retention_index'}
            or cfg.get('format') != CONFIG):
        raise ValueError('explicit039 coverage recovery configuration required')
    for key in ('generation_config', 'old003_export', 'old_retention_index'):
        value = Path(cfg[key]).expanduser()
        cfg[key] = str((path.parent/value).resolve() if not value.is_absolute() else value.resolve())
    original = original_plan(cfg['generation_config'])
    parents = original['sources']
    if (len(parents) != 180 or len({s['source_id'] for s in parents}) != 180
            or sorted(Counter(s['task_key'] for s in parents).values()) != [20]*9):
        raise ValueError('complete original180, nine-task first20 parent manifest required')
    selected = [deepcopy(s) for s in parents if s['task_key'] in TASKS]
    if len(selected) != 60 or any(sorted(s['demo_index'] for s in selected if s['task_key'] == task)
                                  != list(range(20)) for task in TASKS):
        raise ValueError('exact first20 parents for each approved039 task required')
    old_dependencies = _old_metadata(cfg, original, context)
    execution = deepcopy(original['config'])
    execution.update(teacher_policy=TEACHER_V2, recipe=deepcopy(RECIPE))
    plan = {'format': 'task039-coverage-recovery-plan-v1', 'config': cfg,
            'execution_config': execution, 'original_plan': original,
            'parents': deepcopy(parents), 'sources': selected, 'data_root': original['data_root'],
            'generation_config_sha256': context.sha256(cfg['generation_config']),
            'seed_manifest_sha256': context.sha256(original['config']['manifest']),
            'old_dependencies': old_dependencies,
            'population': {'original_parent_sources': 180, 'recovery_parent_sources': 60,
                'recovery_split': dict(Counter(s['split'] for s in selected)), **BUDGET},
            'teacher_policy': TEACHER_V2, 'generator_algorithm': ALGORITHM,
            'generation_context': generation_context(None),
            'selection': 'original natural first20 for stove/mug_pudding/two_pots before outcomes',
            'simulation_created': False, 'model_loaded': False,
            'old_data_replay_required': False, 'old_data_requalification_required': False}
    plan['identity'] = identity(plan)
    return plan
