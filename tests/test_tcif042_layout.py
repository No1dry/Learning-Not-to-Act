"""Only synthetic CPU tensors at the original OFT token-layout boundary."""
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest
import torch

from test_task_control_model import sensors, tiny_policy


class LayoutModel:
    def __init__(self, patches=2, images=2):
        self.vision_backbone = SimpleNamespace(get_num_patches=lambda: patches,
            get_num_images_in_input=lambda: images)

    def _process_action_masks(self, labels):
        return labels == 32001


def fused_fixture(prefix=7, stop=2, padding=0, patches=2, images=2):
    """BOS + prefix/scaffold, then 56 placeholders, stop/scaffold, padding.

    With prefix=7, V=4, inserted=5, action hidden states are 11..66:
    global 11 is the final prefix/scaffold slot, rather than the first placeholder.
    """
    raw_length = prefix + 56 + stop + padding
    ids = torch.arange(raw_length).reshape(1, -1)
    labels = torch.full_like(ids, -100)
    labels[:, prefix:prefix + 56] = 32001
    instruction = torch.zeros(1, prefix, dtype=torch.bool)
    instruction[:, 2:4] = True
    inserted = patches * images + 1
    embeddings = torch.arange((raw_length + inserted) * 3, dtype=torch.float32).reshape(1, -1, 3)
    projected = torch.tensor([[10., 20., 30.]])
    embeddings[:, inserted] = projected
    attention = torch.ones(1, raw_length + inserted, dtype=torch.long)
    if padding:
        attention[:, -padding:] = 0
    return SimpleNamespace(model=LayoutModel(patches, images), ids=ids, labels=labels, instruction=instruction,
        embeddings=embeddings, projected=projected, attention=attention)


def make_layout(fixture):
    from egrs.tcif042.layout import prepare_layout, build_layout
    prepared = prepare_layout(fixture.model, fixture.ids, fixture.labels, fixture.instruction)
    layout = build_layout(prepared, fixture.embeddings, fixture.attention, fixture.projected)
    return prepared, layout


def test_shifted_positions_keep_first_action_in_control_and_all_z_inputs_in_task():
    _, layout = make_layout(fused_fixture(stop=3, padding=2))
    assert layout.inserted == 5 and layout.visual == 4
    assert layout.proprio_position == 5
    assert layout.action_positions == tuple(range(11, 67))
    assert layout.visual_positions == (1, 2, 3, 4)
    assert layout.instruction_positions == (7, 8)
    assert tuple(i for i, flag in enumerate(layout.task) if flag) == (0, 1, 2, 3, 4, 6, 7, 8, 9, 10)
    assert layout.control[5] and layout.control[11]
    assert all(layout.task[i] for i in (*layout.visual_positions, *layout.instruction_positions))
    assert all(layout.control[i] for i in layout.action_positions)
    assert not any(layout.valid[-2:])


def test_f0_f1_final_masks_keep_native_control_access_and_padding_columns():
    from egrs.tcif042.layout import final_attention_mask
    _, layout = make_layout(fused_fixture(stop=3, padding=2))
    f0 = final_attention_mask(layout, 'f0', torch.float64)
    f1 = final_attention_mask(layout, 'f1', torch.float64)
    assert f0.shape == f1.shape == (1, 1, 73, 73)
    assert f0.dtype == f1.dtype == torch.float64
    assert (f0[0, 0, :, :71] == 0).all()  # Every native query reads every valid key.
    assert torch.isneginf(f0[..., 71:]).all()
    assert torch.isneginf(f1[0, 0, 1, 5]) and torch.isneginf(f1[0, 0, 1, 11])
    assert f1[0, 0, 11, 5] == 0  # First shifted A still reads proprio.
    assert f1[0, 0, 5, 67] == 0 and f1[0, 0, 1, 8] == 0
    assert torch.isfinite(f0).any(-1).all() and torch.isfinite(f1).any(-1).all()
    f1.fill_(17)
    assert final_attention_mask(layout, 'f1', torch.float64)[0, 0, 11, 5] == 0


def test_preparation_and_fused_layout_do_not_alias_mutable_sample_tensors():
    from egrs.tcif042.layout import prepare_layout, build_layout
    item = fused_fixture()
    prepared = prepare_layout(item.model, item.ids, item.labels, item.instruction)
    item.ids.zero_(); item.labels.zero_(); item.instruction.zero_()
    layout = build_layout(prepared, item.embeddings, item.attention, item.projected)
    item.attention.zero_()
    assert layout.action_positions == tuple(range(11, 67)) and layout.instruction_positions == (7, 8)
    assert all(layout.valid)
    with pytest.raises(FrozenInstanceError):
        prepared.raw_length = 1
    with pytest.raises(FrozenInstanceError):
        layout.sequence_length = 1


def test_actual_image_inventory_changes_proprio_and_all_shifted_global_positions():
    item = fused_fixture(patches=3, images=2)
    item.projected = item.projected.unsqueeze(1)  # Also accept the original appended token form.
    _, layout = make_layout(item)
    assert layout.inserted == layout.proprio_position == 7
    assert layout.visual_positions == (1, 2, 3, 4, 5, 6)
    assert layout.instruction_positions == (9, 10)
    assert layout.action_positions == tuple(range(13, 69))


def test_final_mask_rejects_empty_native_key_set_unknown_arm_and_integer_dtype():
    from egrs.tcif042.layout import final_attention_mask
    _, layout = make_layout(fused_fixture())
    with pytest.raises(ValueError, match='legal key'):
        final_attention_mask(replace(layout, valid=(False,) * 70), 'f0', torch.float32)
    with pytest.raises(ValueError, match='experiment_arm'):
        final_attention_mask(layout, 'c1', torch.float32)
    with pytest.raises(ValueError, match='floating'):
        final_attention_mask(layout, 'f1', torch.int64)


@pytest.mark.parametrize('prefix,stop,padding,first,length', [(8, 4, 0, 12, 73), (11, 1, 3, 15, 76)])
def test_variable_prefix_stop_scaffold_and_padding_use_shifted_label_map(prefix, stop, padding, first, length):
    _, layout = make_layout(fused_fixture(prefix=prefix, stop=stop, padding=padding))
    assert layout.sequence_length == length
    assert layout.action_positions == tuple(range(first, first + 56))
    assert layout.control[first] and not layout.task[first]
    assert sum(layout.valid) == length - padding


@pytest.mark.parametrize('mutation,match', [
    ('batch', 'one|batch'), ('labels', 'labels|shape'), ('count', '56'),
    ('instruction', 'instruction|context|task'), ('visual', 'insertion|layout'),
    ('proprio', 'proprio'), ('maskshape', 'mask|shape'), ('maskvalue', 'binary|mask'),
    ('allpadding', 'valid|padding|proprio'), ('pad_action', 'action|padding|valid'),
    ('pad_language', 'instruction|context|task|valid'), ('empty_instruction', 'instruction'),
])
def test_invalid_layout_fails_closed_before_final_attention(mutation, match):
    item = fused_fixture()
    if mutation == 'batch': item.ids = item.ids.expand(2, -1)
    elif mutation == 'labels': item.labels = item.labels[:, :-1]
    elif mutation == 'count': item.labels[:, 7] = -100
    elif mutation == 'instruction':
        item.instruction = torch.zeros_like(item.ids, dtype=torch.bool); item.instruction[:, 20] = True
    elif mutation == 'visual': item.embeddings = item.embeddings[:, :-1]; item.attention = item.attention[:, :-1]
    elif mutation == 'proprio': item.projected = item.projected + 1
    elif mutation == 'maskshape': item.attention = item.attention[:, :-1]
    elif mutation == 'maskvalue': item.attention[:, 0] = 2
    elif mutation == 'allpadding': item.attention.zero_()
    elif mutation == 'pad_action': item.attention[:, 11] = 0
    elif mutation == 'pad_language': item.attention[:, 7] = 0
    else: item.instruction.zero_()
    with pytest.raises(ValueError, match=match):
        make_layout(item)


def test_output_validation_uses_actual_projector_and_hidden_lengths():
    from egrs.tcif042.layout import validate_output
    _, layout = make_layout(fused_fixture())
    output = SimpleNamespace(hidden_states=[torch.zeros(1, 70, 3)], projector_features=torch.zeros(1, 5, 3))
    validate_output(layout, output)
    output.projector_features = torch.zeros(1, 4, 3)
    with pytest.raises(ValueError, match='projector|insertion|layout'):
        validate_output(layout, output)
    output.projector_features = torch.zeros(1, 5, 3)
    output.hidden_states = [torch.zeros(1, 69, 3)]
    with pytest.raises(ValueError, match='hidden|length|layout'):
        validate_output(layout, output)


def test_shared_forward_callback_keeps_original_hidden_selection_and_sensor_whitelist(monkeypatch):
    from egrs.task_control.oft import install, prediction
    policy = tiny_policy(monkeypatch); install(policy)
    calls = []
    def forward(model, *, instruction_mask, **kwargs):
        calls.append((model, instruction_mask.detach().clone(), set(kwargs)))
        return model(**kwargs)
    result = prediction(policy, dict(sensors(), actions='GT', task_id='GT'), forward=forward)
    assert len(calls) == policy.model.calls == 1
    assert calls[0][0] is policy.model and calls[0][1].nonzero()[:, 1].tolist() == [2, 3]
    assert calls[0][2] == {'input_ids', 'attention_mask', 'pixel_values', 'labels', 'proprio',
        'proprio_projector', 'use_film', 'output_hidden_states', 'output_projector_features', 'return_dict', 'use_cache'}
    assert result.h.shape == (1, 56, 3) and result.actions.shape == (1, 8, 7)
    assert torch.equal(result.actions, policy.action_head.predict_action(result.h))


def test_tcif_prediction_uses_controller_once_and_legacy_reference_bypasses_it(monkeypatch):
    from egrs.task_control.oft import install
    from egrs.tcif042.oft import prediction
    policy = tiny_policy(monkeypatch); install(policy)
    calls = []
    def forward(model, **kwargs):
        calls.append(kwargs.pop('instruction_mask'))
        return model(**kwargs)
    policy._tcif042 = SimpleNamespace(forward=forward)
    result = prediction(policy, dict(sensors(), partner='GT', completion_count=2))
    assert len(calls) == policy.model.calls == 1 and result.actions.shape == (1, 8, 7)
    policy.model.task_control.enabled = False
    from egrs.augmentation import oft
    monkeypatch.setattr(oft, 'training_prediction', lambda policy, item: torch.ones(1, 8, 7))
    reference = prediction(policy, sensors())
    assert len(calls) == 1 and reference.z is None
