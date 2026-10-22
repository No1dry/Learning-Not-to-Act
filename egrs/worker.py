"""Independent selector worker. --help never imports model/native packages."""
from __future__ import annotations
import argparse
import importlib
import json
import os
import random
import sys
import traceback


def seed_selector(seed):
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    if "torch" in sys.modules:
        sys.modules["torch"].manual_seed(seed)


def serve(source,sink):
    from benchmark.remaining_goals.policy_transport import read_frame,write_frame
    from .contracts import keys, text, validate_registry, validate_payload, validate_prediction
    backend=None
    try:
        first=read_frame(source)
        keys(first,{"command","config"},"initialize")
        if first["command"]!="initialize":
            raise ValueError("initialize required")
        config=first["config"]
        seed=config.get("seed",0)
        if type(seed) is not int or not 0<=seed<2**32:
            raise ValueError("invalid selector seed")
        seed_selector(seed)
        factory=config.get("factory","egrs.selector:QwenSelector")
        module,sep,name=factory.partition(":")
        if not sep:
            raise ValueError("selector factory must be module:callable")
        backend=getattr(importlib.import_module(module),name)(config)
        seed_selector(seed)
        registry=None
        query=0
        write_frame(sink,{"ok":True,"metadata":backend.metadata})
        while True:
            request=read_frame(source)
            command=request.get("command")
            if command=="close":
                keys(request,{"command"},"close")
                break
            if command=="reset":
                keys(request,{"command"},"reset")
                backend.reset()
                seed_selector(seed)
                registry=None
                query=0
                result=None
            elif command=="registry":
                keys(request,{"command","instruction"},"registry request")
                if registry is not None:
                    raise ValueError("registry already initialized; reset for a new episode")
                instruction=text(request["instruction"],"instruction",4096)
                registry=validate_registry(backend.registry(instruction),instruction)
                result=registry
            elif command=="predict":
                keys(request,{"command","payload"},"predict request")
                payload=validate_payload(request["payload"])
                if registry is None or payload["context"]["registry"]!=registry:
                    raise ValueError("fixed episode registry mismatch")
                if payload["context"]["query_id"]!=query+1:
                    raise ValueError("nonconsecutive selector query")
                query+=1
                result=validate_prediction(backend.predict(payload),registry,query,payload["sensor"])
            else:
                raise ValueError("unknown selector command")
            response={"ok":True,"result":result}
            if command in {"registry","predict"}:
                response["input_audit"]=getattr(backend,"last_input_audit",None)
            write_frame(sink,response)
    except BaseException as error:
        traceback.print_exc(file=sys.stderr)
        try:
            write_frame(sink,{"ok":False,"error":f"{type(error).__name__}: {error}",
                              "input_audit":getattr(backend,"last_input_audit",None)})
        except BaseException:
            pass
        return 1
    finally:
        if backend is not None:
            backend.close()
    return 0


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-config",required=True,help="JSON object naming exact local core dependency")
    args=parser.parse_args(argv)
    protocol=os.fdopen(os.dup(sys.stdout.fileno()),"wb",buffering=0)
    os.dup2(sys.stderr.fileno(),sys.stdout.fileno())
    from .core import activate
    with protocol:
        activate(json.loads(args.core_config))
        return serve(sys.stdin.buffer,protocol)


if __name__=="__main__":
    raise SystemExit(main())
