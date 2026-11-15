"""Two training views share native OFT. The deployed view has no hint input."""
import torch

from egrs.augmentation.oft import training_prediction
from .contracts import prompt, require, SENSOR_FIELDS


def prediction(policy, item, hint=None):
    require(set(item) == SENSOR_FIELDS, '043 model input must contain only current sensors and original instruction')
    require(len(item['images']) == 2 and len(item['proprio']) == 8, 'Two images and proprio8 required')
    kwargs = {} if hint is None else {'prompt_override':prompt(item['instruction'],hint)}
    result = training_prediction(policy,item,**kwargs)
    require(tuple(result.shape) == (1,8,7) and torch.isfinite(result).all().item(), 'Invalid normalized action block')
    return result
