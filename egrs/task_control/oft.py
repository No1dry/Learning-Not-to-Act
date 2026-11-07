"""One pinned OFT forward shared by training and evaluation.

The e4287e9 implementation inserts projected image patches and then one proprio
token after BOS. Its projector_features output reports the actual inserted
length. Instruction tokens are mapped from tokenizer character offsets, checked
against the exact processor token IDs. Placeholder labels contain no targets.
"""
from dataclasses import dataclass

import torch

from egrs.augmentation.oft import inject_language_lora, LoRALinear
from .model import TaskControlModules


@dataclass
class Prediction:
    actions: torch.Tensor
    h: torch.Tensor | None
    z: torch.Tensor | None
    proprio: torch.Tensor | None
    count_logits: torch.Tensor | None


def install(policy):
    """Install once on the original SOG10, freezing everything except new weights."""
    if hasattr(policy.model, 'task_control'):
        raise ValueError('task_control is already installed')
    if any(isinstance(module, LoRALinear) for module in policy.model.modules()):
        raise ValueError('task_control must start from the original base without an adapter')
    targets = inject_language_lora(policy)
    dim = getattr(policy.model, 'llm_dim', None)
    if dim is None:
        dim = policy.model.language_model.config.hidden_size
    device = next(policy.model.parameters()).device
    policy.model.task_control = TaskControlModules(dim).to(device=device)
    return targets


def _instruction_mask(processor, prompt, instruction, ids, attention):
    """Fail closed if the tokenizer cannot supply a verified token/character map."""
    prefix = 'In: What action should the robot take to '
    start, end = len(prefix), len(prefix) + len(instruction)
    try:
        mapped = processor.tokenizer(prompt, return_offsets_mapping=True)
    except (NotImplementedError, TypeError, ValueError) as exc:
        raise ValueError('OFT tokenizer must provide exact instruction offset mapping') from exc
    mapped_ids = torch.as_tensor(mapped['input_ids'], device=ids.device)
    if mapped_ids.ndim == 1:
        mapped_ids = mapped_ids.unsqueeze(0)
    offsets = torch.as_tensor(mapped['offset_mapping'], device=ids.device)
    if offsets.ndim == 2:
        offsets = offsets.unsqueeze(0)
    # Processor padding need not be present in the tokenizer's unpadded call.
    valid = attention.bool()
    actual_ids = ids[valid]
    if mapped_ids.shape == ids.shape:
        mapped_ids = mapped_ids[valid]
        offsets = offsets[valid]
    else:
        mapped_ids, offsets = mapped_ids.flatten(), offsets.reshape(-1, 2)
    if not torch.equal(mapped_ids, actual_ids) or offsets.shape != (actual_ids.numel(), 2):
        raise ValueError('instruction offsets do not match actual processor input tokens')
    mask = (offsets[:, 0] < end) & (offsets[:, 1] > start)
    mask[0] = False  # BOS, independently of tokenizer special-token offsets.
    if not mask.any():
        raise ValueError('Original instruction has no verified prefix tokens')
    return mask.reshape(1, -1)


def decode(policy, encoded, z=None):
    """Reuse the receiver's cached H/proprio and optionally exchange only z."""
    if encoded.h is None or encoded.proprio is None or encoded.z is None:
        raise ValueError('decode requires a student encoded observation')
    context = encoded.z if z is None else z
    if context.shape != (1, 128):
        raise ValueError('task context must have shape (1, 128)')
    hidden = policy.model.task_control(encoded.h, context, encoded.proprio)
    actions = policy.action_head.predict_action(hidden)
    if actions.shape != (1, 8, 7):
        raise ValueError('Original OFT action head must return (1, 8, 7)')
    return actions


def prediction(policy, item):
    """Only images, full original instruction and normalized proprio enter OFT."""
    clean = {key: item[key] for key in ('images', 'instruction', 'proprio')}
    modules = policy.model.task_control
    if not modules.enabled:
        from egrs.augmentation.oft import training_prediction
        return Prediction(training_prediction(policy, clean), None, None, None, None)
    from experiments.robot.openvla_utils import prepare_images_for_vla, resize_image_for_policy
    if len(clean['images']) != 2 or not isinstance(clean['instruction'], str) or not clean['instruction'].strip():
        raise ValueError('OFT requires two images and the complete nonempty instruction')
    model = policy.model
    device = next(model.parameters()).device
    images = [resize_image_for_policy(image, policy.resize_size) for image in clean['images']]
    images = prepare_images_for_vla(images, policy.cfg)
    instruction = clean['instruction'].lower()
    prompt = f'In: What action should the robot take to {instruction}?\nOut:'
    primary, wrist = [policy.processor(prompt, image).to(device, dtype=torch.bfloat16) for image in images]
    ids, attention = primary['input_ids'], primary['attention_mask']
    if ids.ndim != 2 or ids.shape[0] != 1 or attention.shape != ids.shape:
        raise ValueError('Only one current observation is supported')
    instruction_mask = _instruction_mask(policy.processor, prompt, instruction, ids, attention)
    ids = ids[attention.bool()].reshape(1, -1)
    attention = torch.ones_like(ids)
    if ids[0, -1] != 29871:
        ids = torch.cat((ids, ids.new_full((1, 1), 29871)), dim=1)
        attention = torch.cat((attention, attention.new_ones((1, 1))), dim=1)
        instruction_mask = torch.cat((instruction_mask, instruction_mask.new_zeros((1, 1))), dim=1)
    labels = torch.full_like(ids, -100)
    ids, attention = model._prepare_input_for_action_prediction(ids, attention)
    labels = model._prepare_labels_for_action_prediction(labels, ids)
    proprio = torch.as_tensor(clean['proprio'], device=device, dtype=torch.bfloat16)
    if proprio.numel() != 8 or not torch.isfinite(proprio).all():
        raise ValueError('Current normalized proprio must contain eight finite values')
    proprio = proprio.reshape(1, 8)
    output = model(input_ids=ids, attention_mask=attention,
        pixel_values=torch.cat((primary['pixel_values'], wrist['pixel_values']), dim=1),
        labels=labels, proprio=proprio, proprio_projector=policy.proprio_projector,
        use_film=False, output_hidden_states=True, output_projector_features=True,
        return_dict=True, use_cache=False)
    states = output.hidden_states[-1]
    inserted = output.projector_features.shape[1]
    visual = model.vision_backbone.get_num_patches() * model.vision_backbone.get_num_images_in_input()
    if inserted != visual + 1 or states.shape[1] != ids.shape[1] + inserted:
        raise ValueError('Actual OFT image/proprio insertion differs from pinned layout')
    visual_hidden = states[:, 1:1 + visual]
    raw_instruction_indices = instruction_mask[0].nonzero().flatten()
    instruction_hidden = states[:, raw_instruction_indices + inserted]
    # Shifted action supervision selects the state immediately before each raw
    # placeholder token, exactly as the original L1 OFT training/inference path.
    action_mask = model._process_action_masks(labels[:, 1:])
    if int(action_mask.sum()) != 56:
        raise ValueError('OFT must expose exactly 56 shifted action states')
    h = states[:, inserted:-1][action_mask].reshape(1, 56, -1)
    z = modules.encode_context(visual_hidden, instruction_hidden)
    result = Prediction(None, h, z, proprio, modules.count_head(z))
    result.actions = decode(policy, result)
    return result
