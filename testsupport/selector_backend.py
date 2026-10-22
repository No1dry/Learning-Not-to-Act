"""Synthetic protocol backend; never loads a research model."""
from pathlib import Path
import importlib.util

# Avoid the separately installed eval core's own tests namespace.
path=Path(__file__).resolve().parents[1]/"tests"/"test_runtime.py"
spec=importlib.util.spec_from_file_location("egrs_runtime_fixtures",path)
fixtures=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


class Backend:
    def __init__(self,config):
        self.metadata={"backend":"CPU fake","config_marker":config.get("marker")}
    def registry(self,instruction):
        return fixtures.registry()
    def predict(self,payload):
        return fixtures.prediction(payload["context"]["query_id"])
    def reset(self):
        pass
    def close(self):
        if self.metadata["config_marker"] == "close-fail":
            raise RuntimeError("synthetic close failure")


def make(config):
    return Backend(config)
