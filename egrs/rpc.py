"""Dedicated selector RPC over the core's bounded JSON/NumPy frame transport."""
from __future__ import annotations
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
from .configuration import runtime_config
from .contracts import validate_payload
from .core import activate


class SelectorProcess:
    def __init__(self, config, core):
        activate(core)
        from benchmark.remaining_goals.policy_transport import read_frame, write_frame
        runtime=config["runtime"]
        runtime_config(runtime)
        executable=Path(os.path.abspath(Path(runtime["python_executable"]).expanduser()))
        if not executable.is_file():
            raise ValueError("selector interpreter does not exist")
        env=os.environ.copy()
        env.pop("PYTHONHOME",None)
        env.pop("PYTHONPATH",None)
        env["PYTHONUNBUFFERED"]="1"
        seed=config.get("seed",0)
        if type(seed) is not int or not 0<=seed<2**32:
            raise ValueError("invalid selector seed")
        env["PYTHONHASHSEED"]=str(seed)
        if runtime.get("cuda_visible_devices") is not None:
            env["CUDA_VISIBLE_DEVICES"]=str(runtime["cuda_visible_devices"])
        self.timeout=float(runtime.get("predict_timeout_seconds",180))
        self.closed=False
        self.last_input_audit=None
        self.lock=threading.Lock()
        self.inbox=queue.Queue()
        self.outbox=queue.Queue()
        self.process=subprocess.Popen([str(executable),"-m","egrs.worker","--core-config",json.dumps(core)],
            env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=None,bufsize=0)
        def receive():
            try:
                while True:
                    self.inbox.put(read_frame(self.process.stdout))
            except BaseException as error:
                self.inbox.put(error)
        def send():
            try:
                while True:
                    payload=self.outbox.get()
                    if payload is None:
                        return
                    write_frame(self.process.stdin,payload)
            except BaseException as error:
                self.inbox.put(error)
        self.reader=threading.Thread(target=receive,daemon=True,name="egrs-selector-read")
        self.writer=threading.Thread(target=send,daemon=True,name="egrs-selector-write")
        self.reader.start()
        self.writer.start()
        try:
            self.metadata=self.call({"command":"initialize","config":config},
                                    float(runtime.get("startup_timeout_seconds",1200)))["metadata"]
        except BaseException:
            try:
                self.close()
            except Exception:
                pass
            raise

    def call(self,payload,timeout=None):
        if self.closed:
            raise RuntimeError("selector worker is closed")
        if not self.lock.acquire(blocking=False):
            raise RuntimeError("concurrent selector calls are not supported")
        try:
            if payload.get("command") in {"registry","predict"}:
                self.last_input_audit=None
            self.outbox.put(payload)
            try:
                response=self.inbox.get(timeout=self.timeout if timeout is None else timeout)
            except queue.Empty as error:
                raise TimeoutError("selector worker timed out; no retry performed") from error
            if isinstance(response,BaseException):
                raise RuntimeError("selector worker disconnected") from response
            if isinstance(response,dict):
                self.last_input_audit=response.get("input_audit")
            if not isinstance(response,dict) or response.get("ok") is not True:
                raise RuntimeError(f"selector worker failed: {response}")
            return response
        except BaseException:
            try:
                self.close()
            except Exception:
                pass
            raise
        finally:
            self.lock.release()

    def reset(self):
        self.call({"command":"reset"})

    def registry(self,instruction):
        return self.call({"command":"registry","instruction":instruction})["result"]

    def predict(self,payload):
        return self.call({"command":"predict","payload":validate_payload(payload)})["result"]

    def close(self):
        if self.closed:
            return
        self.closed=True
        if self.process.poll() is None:
            self.outbox.put({"command":"close"})
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
        self.outbox.put(None)
        for stream in (self.process.stdin,self.process.stdout):
            if stream is not None:
                stream.close()
        self.reader.join(timeout=1)
        self.writer.join(timeout=1)
        if self.process.returncode not in (None,0):
            raise RuntimeError(f"selector worker exited with code {self.process.returncode}")
