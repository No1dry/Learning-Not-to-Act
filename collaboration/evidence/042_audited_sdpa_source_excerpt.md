# 042审计附件：现存OFT LlamaSdpaAttention源片段

2026-11-12，Codex。只读复制自已存在worker安装文件，Transformers4.40.1、PyTorch2.4.1+cu121，**完整原文件SHA-256**：`3aac24cec583a6ef5f60b6ec634a8bd3c8377784c5c63c8cc14cb6790554c52e`。本片段保留原版权/许可证说明；只用于解释native mask和受影响CPU/fake合同，不是042生产实现。没有导入/实例化7B来证明历史run实际类，服务器私有路径不公开。

关键点是最后的last-row expand与is_causal=False：即便上游给了query-specific mask，原SDPA实现也可能将其抹成padding-only双向。X的042必须在方法命名空间实现最终有效mask，不编辑安装包或OFT旧源码；F0等价原规则，F1只增加T←C禁边。不要把output_attentions=True导致的manual/eager fallback当成等价native执行。

~~~python
# coding=utf-8
# Copyright 2022 EleutherAI and the HuggingFace Inc. team. All rights reserved.
#
# This code is based on EleutherAI's GPT-NeoX library and the GPT-NeoX
# and OPT implementations in this library. It has been modified from its
# original forms to accommodate minor architectural differences compared
# to GPT-NeoX and OPT used by the Meta AI team that trained the model.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class LlamaSdpaAttention(LlamaAttention):
    """
    Llama attention module using torch.nn.functional.scaled_dot_product_attention. This module inherits from
    `LlamaAttention` as the weights of the module stays untouched. The only changes are on the forward pass to adapt to
    SDPA API.
    """

    # Adapted from LlamaAttention.forward
    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.LongTensor] = None,
        past_key_value: Optional[Cache] = None,
        output_attentions: bool = False,
        use_cache: bool = False,
        cache_position: Optional[torch.LongTensor] = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[Tuple[torch.Tensor]]]:
        if output_attentions:
            # TODO: Improve this warning with e.g. `model.config.attn_implementation = "manual"` once this is implemented.
            logger.warning_once(
                "LlamaModel is using LlamaSdpaAttention, but `torch.nn.functional.scaled_dot_product_attention` does not support `output_attentions=True`. Falling back to the manual attention implementation, "
                'but specifying the manual implementation will be required from Transformers version v5.0.0 onwards. This warning can be removed using the argument `attn_implementation="eager"` when loading the model.'
            )
            return super().forward(
                hidden_states=hidden_states,
                attention_mask=attention_mask,
                position_ids=position_ids,
                past_key_value=past_key_value,
                output_attentions=output_attentions,
                use_cache=use_cache,
                cache_position=cache_position,
            )

        bsz, q_len, _ = hidden_states.size()

        query_states = self.q_proj(hidden_states)
        key_states = self.k_proj(hidden_states)
        value_states = self.v_proj(hidden_states)

        query_states = query_states.view(bsz, q_len, self.num_heads, self.head_dim).transpose(1, 2)
        key_states = key_states.view(bsz, q_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)
        value_states = value_states.view(bsz, q_len, self.num_key_value_heads, self.head_dim).transpose(1, 2)

        cos, sin = self.rotary_emb(value_states, position_ids)
        query_states, key_states = apply_rotary_pos_emb(query_states, key_states, cos, sin)

        # In case static cache is used, it is an instance attribute.
        past_key_value = getattr(self, "past_key_value", past_key_value)

        if past_key_value is not None:
            # sin and cos are specific to RoPE models; cache_position needed for the static cache
            cache_kwargs = {"sin": sin, "cos": cos, "cache_position": cache_position}
            key_states, value_states = past_key_value.update(key_states, value_states, self.layer_idx, cache_kwargs)

        key_states = repeat_kv(key_states, self.num_key_value_groups)
        value_states = repeat_kv(value_states, self.num_key_value_groups)

        causal_mask = attention_mask
        if attention_mask is not None:
            causal_mask = causal_mask[:, :, :, : key_states.shape[-2]]

        # SDPA with memory-efficient backend is currently (torch==2.1.2) bugged with non-contiguous inputs with custom attn_mask,
        # Reference: https://github.com/pytorch/pytorch/issues/112577.
        if query_states.device.type == "cuda" and causal_mask is not None:
            query_states = query_states.contiguous()
            key_states = key_states.contiguous()
            value_states = value_states.contiguous()

        # In case we are not compiling, we may set `causal_mask` to None, which is required to dispatch to SDPA's Flash Attention 2 backend, rather
        # relying on the `is_causal` argument.

        # NOTE (Moo Jin):
        # We must set `is_causal` == False (to disable the default lower triangular causal mask) and `attn_mask` to the correct attention mask.
        #
        # This is a bit tricky given that we have pad tokens due to collation with samples of different lengths. If there weren't any pad tokens,
        # we could just set `attn_mask` to all zeros, which represents a non-causal bi-directional mask (i.e. attend to all tokens). However,
        # given that we have pad tokens, we need to actually mask out the pad tokens (i.e. set certain attention weights to negative infinity)
        # so that we don't attend to pad tokens.
        #
        # The default causal mask logic produces a `causal_mask` where the lower triangle is all zeros if there are no pad tokens in the sample,
        # and the rest of the elements are negative infinity.
        # If there are K pad tokens in the sample, then the last K columns in `causal_mask` (which has shape (B, 1, seq_len, seq_len)) are
        # additionally negative infinity.
        # Example:
        #
        # No pad tokens:
        #   0 -inf -inf
        #   0   0  -inf
        #   0   0    0
        # 1 pad token:
        #   0 -inf -inf
        #   0   0  -inf
        #   0   0  -inf
        # 2 pad tokens:
        #   0 -inf -inf
        #   0 -inf -inf
        #   0 -inf -inf
        #
        # Intuitively, this stops the last few tokens from attending to the last K tokens which are pad tokens.
        #
        # Okay so the above is what the default causal mask logic returns. But what we want is a mask that is all 0s except for the positions corresponding to pad tokens.
        # What we want is illustrated below.
        #
        # No pad tokens:
        #   0   0    0
        #   0   0    0
        #   0   0    0
        # 1 pad token:
        #   0   0  -inf
        #   0   0  -inf
        #   0   0  -inf
        # 2 pad tokens:
        #   0 -inf -inf
        #   0 -inf -inf
        #   0 -inf -inf
        #
        # Trick: To get this mask, we just take the last row of the old `causal_mask` and duplicate it all the way through to get the new mask. You can see that this trick
        # works by looking at the matrices above.
        if causal_mask is not None:
            D = causal_mask.shape[-1]
            last_row = causal_mask[:, :, -1, :].clone()
            new_mask = last_row.unsqueeze(2).expand(-1, -1, D, -1)
            causal_mask = new_mask

        attn_output = torch.nn.functional.scaled_dot_product_attention(
            query_states,
            key_states,
            value_states,
            attn_mask=causal_mask,
            dropout_p=self.attention_dropout if self.training else 0.0,
            is_causal=False,
        )

        attn_output = attn_output.transpose(1, 2).contiguous()
        attn_output = attn_output.view(bsz, q_len, self.hidden_size)

        attn_output = self.o_proj(attn_output)

        return attn_output, None, past_key_value
~~~

来源链：[只读审计](042_existing_attention_audit_and_proposal.json)、[用户批准](042_budget_approval_and_dispatch.json)、[实施工单](../tasks/042_task_control_information_firewall.md)。本段依赖原文件中的torch、Cache、apply_rotary_pos_emb、repeat_kv等上下文，不是可脱离上下文直接运行的脚本，也不授权真实模型/仿真预跑。
