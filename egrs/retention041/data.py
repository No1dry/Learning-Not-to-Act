"""Immutable040 data view and explicit old003 train10 ancestry selection."""
from collections import Counter
import re

from egrs.coverage040.data import CoverageTaskControlDataset as Coverage040Dataset

OLD_TASKS = frozenset(('basket', 'basket_cheese_butter', 'bowl_drawer_close',
                       'dual_mugs', 'basket_soup_cheese', 'mug_microwave_close'))
# Private constants are patched only by synthetic CPU fixtures. No runtime opt-out.
_INDEX_IDENTITY = '8ef04d9164a5b8e522763b930e7fdad09c5ec07bf215cfed88a20c700ee6c7fe'
_POOL_COUNTS = {'ten': {'train': 289, 'dev': 81},
                'fresh': {'train': 78, 'dev': 27}, 'raw': {'train': 136, 'dev': 44}}
_PAIR_COUNTS = {'train': 289, 'dev': 81}
_ROW_COUNT = 143960
_BIND_FIELDS = ('parent_demo_id', 'source_group', 'split', 'task_key', 'file_sha256', 'variant')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _source_binding(source_id, retained, qualified):
    message = '041 ten source ' + source_id + ': '
    _require(retained.get('source_id') == source_id and qualified.get('domain') == '10',
             message + 'explicit ten source/domain binding differs')
    _require(all(retained.get(k) == qualified.get(k) and qualified.get(k) is not None for k in _BIND_FIELDS)
             and retained.get('file') == qualified.get('file'), message + 'parent/group/split/file identity differs')
    _require(qualified.get('split') in ('train', 'dev')
             and all(isinstance(qualified.get(k), str) and qualified[k] for k in ('parent_demo_id','source_group','task_key'))
             and re.fullmatch(r'[0-9a-f]{64}', str(qualified.get('file_sha256', ''))) is not None,
             message + 'explicit parent/group/split/hash evidence is missing')


def old10_source_ids(manifest, sources):
    """Return train-ten IDs proven through040→039→old003 metadata.

    A task name or path never establishes ancestry. New039 and explicit040
    sources are excluded even when they have one of the six historical tasks.
    """
    _require(isinstance(manifest.get('qualified_sources'), dict)
             and isinstance(manifest.get('new_sources'), dict), '041 requires explicit040 qualified/new source maps')
    eligible = set()
    for source_id, retained in sources.items():
        if retained.get('pool') != 'ten':
            continue
        message = '041 ten source ' + source_id + ': '
        qualified = retained.get('original_source')
        _require(isinstance(qualified, dict), message + 'original qualified source ancestry is unavailable')
        _source_binding(source_id, retained, qualified)
        if source_id in manifest['new_sources']:
            _require(qualified == manifest['new_sources'][source_id]
                     and 'coverage039_origin' not in qualified
                     and isinstance(qualified.get('source_id'), str)
                     and source_id == 'ten|new040|' + qualified['source_id'],
                     message + 'explicit new040 source binding conflicts')
            continue
        origin = qualified.get('coverage039_origin')
        _require(isinstance(origin, dict) and origin.get('release') in ('old003','new039'),
                 message + 'explicit039 old003/new039 ancestry is unavailable')
        original_id = origin.get('source_id')
        original = origin.get('original_source')
        gid = qualified.get('source_id')
        _require(isinstance(original_id, str) and original_id and isinstance(original, dict)
                 and original.get('source_id') == original_id
                 and gid == origin['release'] + '|' + original_id
                 and source_id == 'ten|' + gid
                 and manifest['qualified_sources'].get(gid) == qualified,
                 message + '040 qualified-source / original source_id ancestry differs')
        _require(original.get('domain') == '10'
                 and all(original.get(k) == qualified.get(k) for k in _BIND_FIELDS),
                 message + 'old003/new039 original parent/group/split/hash evidence differs')
        if origin['release'] == 'old003' and retained['split'] == 'train' and retained['task_key'] in OLD_TASKS:
            eligible.add(source_id)
    return eligible


def select_old10_positions(rows, indices, eligible_ids, limit=4):
    """Select original batch positions, counting repeats without RNG or resampling."""
    _require(type(limit) is int and 0 <= limit <= 4, '041 old10 selection limit must be an integer from0 to4')
    positions = []; eligible_count = 0
    for position, index in enumerate(indices):
        _require(type(index) is int and 0 <= index < len(rows), '041 old10 sampled row index is invalid')
        row = rows[index]
        if (row.get('source_id') in eligible_ids and row.get('pool') == 'ten'
                and row.get('split') == 'train' and row.get('role') not in ('pair','pair_only')
                and 'u' not in row and 'v' not in row):
            eligible_count += 1
            if len(positions) < limit:
                positions.append(position)
    return positions, eligible_count


class StageDataset(Coverage040Dataset):
    """Use the accepted040 reader unchanged, then bind041's fixed inputs."""
    def __init__(self, index_dir, split='train', context=None):
        super().__init__(index_dir, split=split, context=context)
        _require(self.identity == _INDEX_IDENTITY, '041 requires the fixed accepted040 index identity')
        counts = Counter((source.get('pool'), source.get('split')) for source in self.sources.values())
        expected = Counter({(pool, part): count for pool, parts in _POOL_COUNTS.items()
                            for part, count in parts.items()})
        _require(counts == expected, '041 accepted040 fixed ten/fresh/raw source counts differ')
        _require(self.report.get('rows') == self.retention.report.get('rows') == _ROW_COUNT,
                 '041 accepted040 fixed row count differs')
        _require(self.report.get('pairs', {}).get('valid') == sum(_PAIR_COUNTS.values())
                 and len(self.pairs) == _PAIR_COUNTS[split], '041 accepted040 fixed pair counts differ')
        self.old10_source_ids = old10_source_ids(self.manifest, self.sources)
