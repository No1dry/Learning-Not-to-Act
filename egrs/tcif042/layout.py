"""Immutable token positions from the pinned OFT preparation and fused pass.

No pixels, expert actions, task identifiers, or extra projector forwards are
needed. The original shifted placeholder-label mask remains authoritative for
the 56 action hidden states, including the state before the first placeholder.
"""
from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class PreparedLayout:
    raw_length: int
    visual: int
    action_indices: tuple[int, ...]
    instruction_indices: tuple[int, ...]
    device: torch.device


@dataclass(frozen=True)
class TokenLayout:
    inserted: int
    visual: int
    sequence_length: int
    hidden_size: int
    proprio_position: int
    action_positions: tuple[int, ...]
    visual_positions: tuple[int, ...]
    instruction_positions: tuple[int, ...]
    valid: tuple[bool, ...]
    task: tuple[bool, ...]
    control: tuple[bool, ...]
    device: torch.device


def prepare_layout(model, input_ids, labels, instruction_mask):
    """Snapshot only positional metadata before the one multimodal forward."""
    if (not isinstance(input_ids, torch.Tensor) or input_ids.ndim != 2
            or input_ids.shape[0] != 1 or input_ids.shape[1] < 2):
        raise ValueError('TCIF supports exactly one current observation per batch')
    if input_ids.dtype not in (torch.int32, torch.int64):
        raise ValueError('TCIF input_ids must contain integer tokens')
    if (not isinstance(labels, torch.Tensor) or labels.shape != input_ids.shape
            or labels.device != input_ids.device or labels.dtype != input_ids.dtype):
        raise ValueError('TCIF placeholder labels must match actual input_ids shape and type')
    if (not isinstance(instruction_mask, torch.Tensor) or instruction_mask.ndim != 2
            or instruction_mask.shape[0] != 1 or instruction_mask.shape[1] > input_ids.shape[1]
            or instruction_mask.dtype != torch.bool or instruction_mask.device != input_ids.device):
        raise ValueError('TCIF requires the verified raw instruction token mask')
    instruction = tuple(instruction_mask[0].nonzero().flatten().tolist())
    if not instruction or instruction[0] == 0:
        raise ValueError('TCIF instruction must contain verified non-BOS context tokens')
    action_mask = model._process_action_masks(labels[:, 1:])
    if (not isinstance(action_mask, torch.Tensor) or action_mask.dtype != torch.bool
            or action_mask.shape != labels[:, 1:].shape):
        raise ValueError('TCIF original shifted action mask has an unsupported shape or type')
    actions = tuple(action_mask[0].nonzero().flatten().tolist())
    if len(actions) != 56:
        raise ValueError('TCIF requires exactly 56 original shifted action hidden states')
    patches = model.vision_backbone.get_num_patches()
    images = model.vision_backbone.get_num_images_in_input()
    if type(patches) is not int or type(images) is not int or patches < 1 or images < 1:
        raise ValueError('TCIF vision layout must report positive patch and image counts')
    return PreparedLayout(input_ids.shape[1], patches * images, actions, instruction, input_ids.device)


def build_layout(prepared, inputs_embeds, attention_mask, projected_proprio):
    """Validate the actual original fused embedding and its captured P token.

    OFT inserts [image patches, projected proprio] after BOS. Length is measured
    from the actual fused embedding, and P is checked against the output of the
    original proprio projector from this very pass (not a second invocation).
    Tuple snapshots cannot be changed by a later sample or tensor mutation.
    """
    if (not isinstance(inputs_embeds, torch.Tensor) or inputs_embeds.ndim != 3
            or inputs_embeds.shape[0] != 1 or inputs_embeds.shape[2] < 1
            or inputs_embeds.device != prepared.device or not inputs_embeds.is_floating_point()):
        raise ValueError('TCIF fused layout requires one floating embedding sequence on the original device')
    sequence_length, hidden_size = inputs_embeds.shape[1:]
    inserted = sequence_length - prepared.raw_length
    if inserted != prepared.visual + 1:
        raise ValueError('Actual OFT image/proprio insertion differs from pinned layout')
    if (not isinstance(attention_mask, torch.Tensor) or attention_mask.shape != (1, sequence_length)
            or attention_mask.device != inputs_embeds.device
            or not torch.all((attention_mask == 0) | (attention_mask == 1))):
        raise ValueError('TCIF fused attention mask must be binary and match the actual sequence shape')
    valid = tuple(bool(value) for value in attention_mask[0].tolist())
    proprio_position = 1 + prepared.visual
    if not isinstance(projected_proprio, torch.Tensor):
        raise ValueError('TCIF requires the actual projected proprio output from this forward')
    if projected_proprio.shape == (1, hidden_size):
        projected_proprio = projected_proprio.unsqueeze(1)
    if (projected_proprio.shape != (1, 1, hidden_size)
            or projected_proprio.device != inputs_embeds.device
            or not torch.isfinite(projected_proprio).all()
            or not torch.equal(inputs_embeds[:, proprio_position:proprio_position + 1].detach(),
                               projected_proprio.detach())):
        raise ValueError('Actual fused proprio token does not match this forward projector output')
    visual = tuple(range(1, 1 + prepared.visual))
    instruction = tuple(index + inserted for index in prepared.instruction_indices)
    actions = tuple(index + inserted for index in prepared.action_indices)
    # This is deliberately shifted by labels[:, 1:], not the tail of states.
    first_action = min(actions)
    task = tuple(flag and index < first_action and index != proprio_position
                 for index, flag in enumerate(valid))
    control = tuple(flag and not task[index] for index, flag in enumerate(valid))
    if not all(valid[index] for index in (0, proprio_position, *visual)):
        raise ValueError('Actual BOS/image/proprio insertion must be valid, never padding')
    if not all(task[index] for index in (*visual, *instruction)):
        raise ValueError('All visual and instruction context hidden states must be valid task positions')
    if not all(control[index] for index in actions):
        raise ValueError('All 56 shifted action hidden states must be valid control positions')
    if not any(task) or not any(valid):
        raise ValueError('TCIF task region and native legal-key set must be nonempty')
    return TokenLayout(inserted, prepared.visual, sequence_length, hidden_size, proprio_position,
        actions, visual, instruction, valid, task, control, inputs_embeds.device)


def final_attention_mask(layout, experiment_arm, dtype):
    """Fresh additive mask: padding-only native F0, plus T-query/C-key F1."""
    if experiment_arm not in ('f0', 'f1'):
        raise ValueError('TCIF experiment_arm must be f0 or f1')
    if not torch.empty((), dtype=dtype).is_floating_point():
        raise ValueError('TCIF additive attention mask requires a floating dtype')
    size = layout.sequence_length
    valid = torch.tensor(layout.valid, dtype=torch.bool, device=layout.device)
    allowed = valid.unsqueeze(0).expand(size, -1).clone()
    if experiment_arm == 'f1':
        task = torch.tensor(layout.task, dtype=torch.bool, device=layout.device)
        control = torch.tensor(layout.control, dtype=torch.bool, device=layout.device)
        allowed &= ~(task.unsqueeze(1) & control.unsqueeze(0))
    if not allowed.any(dim=-1).all():
        raise ValueError('TCIF final attention mask has a query without a legal key')
    mask = torch.zeros((1, 1, size, size), dtype=dtype, device=layout.device)
    return mask.masked_fill(~allowed.unsqueeze(0).unsqueeze(0), float('-inf'))


def validate_output(layout, output):
    """Check lengths again against actual outputs without another forward."""
    projected = getattr(output, 'projector_features', None)
    if (not isinstance(projected, torch.Tensor)
            or projected.shape != (1, layout.inserted, layout.hidden_size)):
        raise ValueError('TCIF output projector insertion differs from the observed fused layout')
    hidden = getattr(output, 'hidden_states', None)
    if (not isinstance(hidden, (tuple, list)) or not hidden
            or not isinstance(hidden[-1], torch.Tensor)
            or hidden[-1].shape != (1, layout.sequence_length, layout.hidden_size)):
        raise ValueError('TCIF output hidden length differs from the observed fused layout')
