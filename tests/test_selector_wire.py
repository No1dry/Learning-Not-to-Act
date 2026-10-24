"""Online JSON boundary and raw audit; synthetic outputs, no model/simulator."""
import copy
import io
import json

import numpy as np
import pytest

from tests.test_data_training import example


def selector(monkeypatch, outputs):
    import torch
    from egrs.selector import QwenSelector
    from egrs.selector import encoding
    from egrs.selector import structured
    monkeypatch.setattr(structured,'build_visual_filter',lambda *a:(lambda *a:[],object()))
    rows=iter(outputs)
    class Tokenizer:
        def decode(self,*args,**kwargs):return next(rows)
    class Model:
        calls=0
        def generate(self,**kwargs):
            self.calls+=1
            return torch.tensor([[1,2,3,4,5,6,7]])
    value=QwenSelector({'device':'cpu'})
    value._processor=type('Processor',(),{'tokenizer':Tokenizer()})()
    value._model=Model()
    monkeypatch.setattr(encoding,'encode_messages',lambda *a,**kw:(
        {'input_ids':torch.tensor([[1,2,3,4]])},'',[]))
    return value


@pytest.mark.parametrize('wrap,strategy',[
    ('{}','bare_json'),(' \n```json\n{}\n```\n','fenced_json'),('```\r\n{}\r\n```','fenced_untyped')])
def test_exact_registry_wrapper_keeps_original_and_single_call(monkeypatch,wrap,strategy):
    reg=example()['payload']['context']['registry'];raw=wrap.format(json.dumps(reg))
    value=selector(monkeypatch,[raw])
    assert value.registry(reg['instruction'])==reg
    audit=value.last_input_audit
    assert audit['raw_output']==raw and audit['generated_tokens']==3
    assert audit['parsing']['strategy']==strategy
    assert audit['parsing']['stages']==dict.fromkeys(('wrapper','json','schema'),'passed')
    assert value._model.calls==1


@pytest.mark.parametrize('raw,stage',[
    ('Explanation\n```json\n{}\n```','wrapper'),('```json\n{}\n```\nDone.','wrapper'),
    ('```json\n{}\n```\n```json\n{}\n```','wrapper'),('```json\n{}','wrapper'),
    ('```python\n{}\n```','wrapper'),('invalid JSON','json'),('', 'json'),
    ('{}{}','json'),('```json\n{"instruction":\n```','json')])
def test_bad_output_retained_without_extraction_repair_or_retry(monkeypatch,raw,stage):
    value=selector(monkeypatch,[raw])
    with pytest.raises(ValueError,match='invalid JSON'):value.registry('put bowl in drawer')
    assert value._model.calls==1
    assert value.last_input_audit['raw_output']==raw
    assert value.last_input_audit['parsing']['failure_stage']==stage
    assert value.last_input_audit['parsing']['stages']['schema']=='not_run'


def test_valid_json_with_wrong_registry_schema_stays_invalid(monkeypatch):
    reg=example()['payload']['context']['registry']
    bad=copy.deepcopy(reg);bad['goals'][0]['kind']='transport|mechanism'
    raw='```json\n'+json.dumps(bad)+'\n```'
    value=selector(monkeypatch,[raw])
    with pytest.raises(ValueError,match='kind'):value.registry(reg['instruction'])
    assert value.last_input_audit['raw_output']==raw
    assert value.last_input_audit['parsing']['failure_stage']=='schema'
    assert value._model.calls==1


def test_fenced_visual_answer_uses_same_schema_and_resets_audit(monkeypatch):
    sample=example();reg=sample['payload']['context']['registry']
    raw='```json\n'+json.dumps(sample['answer'])+'\n```'
    value=selector(monkeypatch,[raw,json.dumps(reg)])
    sample['payload']['sensor'][0]['observation']={
        'agentview_image':np.zeros((2,2,3),np.uint8),'robot0_eye_in_hand_image':np.zeros((2,2,3),np.uint8)}
    assert value.predict(sample['payload'])==sample['answer']
    assert value.last_input_audit['image_count']==2
    assert value.last_input_audit['raw_output']==raw
    value.registry(reg['instruction'])
    assert value.last_input_audit['image_count']==0
    assert value.last_input_audit['snapshot_ids']==[]
    assert value.last_input_audit['raw_output']==json.dumps(reg)


@pytest.mark.parametrize('valid',[False,True])
def test_inference_cli_saves_raw_audit_on_success_and_error(monkeypatch,tmp_path,valid):
    from egrs.selector import infer
    reg=example()['payload']['context']['registry'];raw=json.dumps(reg) if valid else 'text instead of json'
    value=selector(monkeypatch,[raw]);monkeypatch.setattr(infer,'QwenSelector',lambda cfg:value)
    request=tmp_path/'input.json';request.write_text(json.dumps({'instruction':reg['instruction']}))
    answer=tmp_path/'answer.json';audit=tmp_path/'audit.json'
    args=['--mode','registry','--input',str(request),'--output',str(answer),'--audit-output',str(audit)]
    if valid:assert infer.main(args)==0
    else:
        with pytest.raises(ValueError,match='invalid JSON'):infer.main(args)
    report=json.loads(audit.read_text())
    assert report['input_audit']['raw_output']==raw
    assert bool(report['error'])!=valid and answer.exists()==valid
    assert value._closed
    with pytest.raises(ValueError,match='already exists'):infer.main(args)


def test_worker_error_frame_transports_exact_raw_generation(monkeypatch):
    from egrs import worker
    import egrs.selector as module
    from benchmark.remaining_goals.policy_transport import write_frame,read_frame
    raw='unexpected output, no raw lost';value=selector(monkeypatch,[raw])
    monkeypatch.setattr(module,'QwenSelector',lambda config:value)
    source=io.BytesIO();sink=io.BytesIO()
    write_frame(source,{'command':'initialize','config':{'device':'cpu'}})
    write_frame(source,{'command':'registry','instruction':'put bowl in drawer'})
    source.seek(0)
    assert worker.serve(source,sink)==1
    sink.seek(0);assert read_frame(sink)['ok']
    failed=read_frame(sink)
    assert not failed['ok'] and failed['input_audit']['raw_output']==raw
    assert failed['input_audit']['parsing']['failure_stage']=='json'
