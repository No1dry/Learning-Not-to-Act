"""Task039 identities with the unchanged038 recorded-state label/pair algorithm."""
from pathlib import Path

from egrs.augmentation.data import _require,identity,read_json
from egrs.task_control.index import IndexContract,build_index as build_control,DATA_KIND
from .data import CoverageRetentionDataset,SOURCES_KIND,build_retention_index
from .io import HashContext,Progress
from .merge import read_merged,_lines

IDENTITY_KIND='task039-index-identity-v1'


def build_indices(merged_export,old_retention_index,out,context=None):
    context=context or HashContext();output=Path(out).resolve()
    if output.exists():raise FileExistsError('new039 indices directory required')
    merged,_,_=read_merged(merged_export,context)
    output.mkdir(parents=True)
    retention=output/'retention';control=output/'task_control'
    retention_report=build_retention_index(merged_export,old_retention_index,retention,context=context)
    contract=IndexContract(SOURCES_KIND,IDENTITY_KIND,CoverageRetentionDataset,
        {'coverage039':merged['coverage039'],'algorithm_contract':'task038-recorded-active-state-count-and-pair-v1',
         'merged_export_identity':merged['identity']},Progress('task_control_index'))
    control_report=build_control(merged_export,retention,control,contract=contract,context=context)
    return {'retention':str(retention),'task_control':str(control),
            'retention_report':retention_report,'task_control_report':control_report}


def read_index(directory,context=None):
    context=context or HashContext();directory=Path(directory).resolve()
    manifest,report,seal=(read_json(directory/name) for name in ('sources.json','report.json','identity.json'))
    _require(manifest.get('format')==SOURCES_KIND and report.get('data_kind')==DATA_KIND
             and seal.get('format')==IDENTITY_KIND
             and identity(manifest)==manifest.get('identity')==report.get('sources_identity')==seal.get('sources_identity')
             and identity(report)==report.get('identity')==seal.get('report_identity'), '039 task-control index identity differs')
    _require(manifest.get('algorithm_contract')==report.get('algorithm_contract')=='task038-recorded-active-state-count-and-pair-v1'
             and manifest.get('coverage039')==report.get('coverage039')
             and manifest.get('merged_export_identity')==report.get('merged_export_identity'),
             '039 task-control source/algorithm contract differs')
    for name in ('labels','pairs'):
        _require(report.get(name+'_sha256')==manifest.get(name+'_sha256'),'039 '+name+' byte identity differs')
        context.verify(directory/(name+'.jsonl'),report[name+'_sha256'])
    for path,digest in manifest['inputs'].items():context.verify(path,digest)
    merged,_,_=read_merged(manifest['generated_export'],context)
    _require(merged['identity']==manifest['merged_export_identity']
             and merged['sources']==manifest['qualified_sources']
             and merged['data_root']==manifest['generated_data_root']
             and merged['coverage039']==manifest['coverage039'], '039 merged label source identity differs')
    return manifest,report,_lines(directory/'labels.jsonl'),_lines(directory/'pairs.jsonl')
