"""Original036 examples plus offline count labels and qualified pair endpoints."""
from types import SimpleNamespace

from egrs.augmentation.data import AugmentationDataset, _require
from egrs.retention.data import RetentionDataset
from .index import read_index


class TaskControlDataset:
    def __init__(self, index_dir, split='train'):
        _require(split in ('train','dev'), 'unknown task-control split')
        self.manifest, self.report, labels, pairs = read_index(index_dir)
        self.identity = self.manifest['identity']
        self.retention = RetentionDataset(self.manifest['retention_index'],split=split)
        _require(self.retention.manifest['identity'] == self.manifest['retention_identity'], 'original036 index identity differs')
        self.rows = self.retention.rows
        self.sources = self.retention.sources
        self.pairs = [p for p in pairs if p['split'] == split]
        self._labels = {(r['source_id'],r['observation_index']):r['count_label'] for r in labels}
        _require(all((r['source_id'],r['observation_index']) in self._labels for r in self.rows), 'count label row binding missing')

    def __len__(self):
        return len(self.rows)

    def validate_normalization(self, stats, unnorm_key, stats_sha256):
        return self.retention.validate_normalization(stats,unnorm_key,stats_sha256)

    def __getitem__(self, index):
        row = self.rows[index]
        return {**self.retention[index], 'count_label':self._labels[row['source_id'],row['observation_index']]}

    def get_pair(self, index):
        pair = self.pairs[index]
        items = []
        for name in ('u','v'):
            endpoint = pair[name]; sid = endpoint['generated_source_id']
            view = SimpleNamespace(manifest={'data_root':self.manifest['generated_data_root']},
                                   sources={sid:self.manifest['qualified_sources'][sid]},rows=[endpoint['original_row']])
            item = AugmentationDataset.__getitem__(view,0)
            item['count_label'] = self._labels[endpoint['source_id'],endpoint['observation_index']]
            items.append(item)
        return tuple(items)
