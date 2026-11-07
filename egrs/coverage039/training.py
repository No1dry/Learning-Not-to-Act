"""Bind the new039 index to the unchanged038 model, losses and budgets."""
from .data import CoverageTaskControlDataset
from .io import HashContext, Progress


def run(args):
    from egrs.task_control import training as previous
    context=HashContext(progress=Progress('training_input_validation'))
    def factory(index_dir,split):
        dataset=CoverageTaskControlDataset(index_dir,split=split,context=context)
        added=dataset.report.get('coverage039',{}).get('new_qualified_train10')
        if type(added) is not int or added < 0:
            raise ValueError('039 index must declare its actual new qualified training10 count')
        if split=='train' and added==0:
            raise ValueError('No new qualified training10 recovered; do not retrain the same old data')
        return dataset
    return previous.run(args,dataset_factory=factory,compact_logging=True)
