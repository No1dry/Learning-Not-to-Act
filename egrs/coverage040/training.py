"""Use the unchanged038 C1 preset with the explicit040 train-only data view."""
from egrs.coverage039.io import HashContext, Progress
from .data import CoverageTaskControlDataset


def run(args):
    if args.arm != 'c1':
        raise ValueError('Task040 permits only the fixed C1 arm')
    from egrs.task_control import training as previous
    context = HashContext(progress=Progress('task040_training_inputs'))
    def factory(index_dir, split):
        dataset = CoverageTaskControlDataset(index_dir, split=split, context=context)
        added = dataset.report.get('coverage040', {}).get('new_qualified_train10')
        if type(added) is not int or added < 0:
            raise ValueError('040 index must bind actual new qualified train10 count')
        if split == 'train' and added == 0:
            raise ValueError('No new qualified train10 from new train parents; do not repeat same coverage training')
        return dataset
    return previous.run(args, dataset_factory=factory, compact_logging=True)
