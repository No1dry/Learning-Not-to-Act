"""040 main pools and an explicit, separately addressed normal pair source map."""
from types import SimpleNamespace
from pathlib import Path

from egrs.augmentation.data import AugmentationDataset, _require, read_json
from egrs.retention.data import RetentionDataset
from egrs.task_control.data import TaskControlDataset
from egrs.coverage039.io import HashContext
from egrs.coverage039.merge import _lines
from .index import read_index


class CoverageTaskControlDataset(TaskControlDataset):
    def __init__(self,index_dir,split='train',context=None):
        _require(split in ('train','dev'),'unknown040 task-control split')
        context=context or HashContext()
        self.manifest,self.report,labels,pairs=read_index(index_dir,context=context)
        self.identity=self.manifest['identity']
        # All files/records were checked by the040 reader. Reuse only the original
        # lazy item/normalization implementations, not036's strict constructor.
        self.retention=RetentionDataset.__new__(RetentionDataset)
        directory=Path(self.manifest['retention_index'])
        self.retention.manifest=read_json(directory/'sources.json')
        self.retention.report=read_json(directory/'report.json')
        self.retention.sources=self.retention.manifest['sources']
        self.retention.rows=[r for r in _lines(directory/'rows.jsonl') if r['split']==split]
        self.rows=self.retention.rows;self.sources=self.retention.sources
        self.pairs=[p for p in pairs if p['split']==split]
        self.pair_sources=self.manifest['pair_sources']
        self._labels={(r['source_id'],r['observation_index']):r['count_label'] for r in labels}
        _require(all((r['source_id'],r['observation_index']) in self._labels for r in self.rows),
                 '040 main observation label binding missing')

    def get_pair(self,index):
        pair=self.pairs[index];items=[]
        for name in ('u','v'):
            endpoint=pair[name];rid=endpoint['source_id'];sid=endpoint['generated_source_id']
            if rid in self.pair_sources:
                address=self.pair_sources[rid];root=address['data_root'];source=address['source']
            elif rid in self.manifest['new_sources']:
                root=self.manifest['delta_data_root'];source=self.manifest['new_sources'][rid]
            else:
                root=self.manifest['generated_data_root'];source=self.manifest['qualified_sources'][sid]
            view=SimpleNamespace(manifest={'data_root':root},sources={sid:source},rows=[endpoint['original_row']])
            item=AugmentationDataset.__getitem__(view,0)
            item['count_label']=self._labels[rid,endpoint['observation_index']]
            items.append(item)
        return tuple(items)

    def validate_normalization(self,stats,unnorm_key,stats_sha256):
        super().validate_normalization(stats,unnorm_key,stats_sha256)
        # Pair-only normals still use their own original sensor/action mapping.
        view=RetentionDataset.__new__(RetentionDataset);view.sources={}
        from egrs.retention.data import _obs_mapping
        for sid,address in self.pair_sources.items():
            source=address['source']
            view.sources[sid]={'pool':'ten','observation_mapping':_obs_mapping(source),'original_source':source}
        view.validate_normalization(stats,unnorm_key,stats_sha256)
