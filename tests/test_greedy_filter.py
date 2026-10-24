"""Greedy fast-path equals full vocabulary masking, including forced/EOS steps."""
import torch
from lmformatenforcer import StringParser,UnionParser,TokenEnforcer
from lmformatenforcer.tokenenforcer import TokenEnforcerTokenizerData
from egrs.selector.structured import GreedyGrammarFilter


def test_fast_filter_exact_masked_argmax_equivalence():
    pieces=['a','b','x','ab','ax','z',' ','<eos>']
    class Tokenizer:
        all_special_ids=[7]
        eos_token_id=7
        def decode(self,ids,**kw):return ''.join(pieces[i] for i in ids)
    tokenizer=Tokenizer()
    data=TokenEnforcerTokenizerData([(i,t,False) for i,t in enumerate(pieces[:-1])],
        lambda ids:tokenizer.decode(ids),7,False,len(pieces))
    fast_steps=filtered_steps=0
    for seed in range(64):
        def grammar():return UnionParser([StringParser('ab'),StringParser('ax')])
        fast=GreedyGrammarFilter(tokenizer,grammar(),data,1)
        full=TokenEnforcer(data,grammar())
        prefix=[999]
        generator=torch.Generator().manual_seed(seed)
        for step in range(4):
            logits=torch.randn((1,len(pieces)),generator=generator)
            allowed=full.get_allowed_tokens(prefix).allowed_tokens
            mask=torch.full_like(logits,float('-inf'));mask[0,allowed]=0
            expected=int(torch.argmax(logits+mask))
            actual=int(torch.argmax(fast(torch.tensor([prefix]),logits.clone())))
            assert actual==expected
            if actual==7:break
            prefix.append(actual)
        else:raise AssertionError('grammar did not terminate')
        fast_steps+=fast.stats['fast_steps'];filtered_steps+=fast.stats['filtered_steps']
    assert fast_steps>0 and filtered_steps>0
