"""Fake worker used only by the installed-wheel isolation test."""
import numpy as np

INSTRUCTION = "please put cup on plate"
REGISTRY = {"instruction":INSTRUCTION,"goals":[{"goal_ref":"g0",
    "source_text":"put cup on plate","actor_text":"put cup on plate",
    "target":"cup","destination":"plate","kind":"transport"}]}


class Selector:
    metadata={"backend":"installed CPU fake; no research model"}
    def registry(self,instruction):
        assert instruction==INSTRUCTION
        return REGISTRY
    def predict(self,payload):
        q=payload["context"]["query_id"]
        self.last_input_audit={"snapshot_ids":[s["snapshot_id"] for s in payload["sensor"]],
                               "image_count":2*len(payload["sensor"])}
        return {"query_id":q,"goals":[{"goal_ref":"g0","entity_ref":"cup1",
            "association":"MATCHED","role":"TARGET","relation":"UNSAT" if q==1 else "SAT",
            "release":"RELEASED","interaction":"NOT_HELD","evidence":[{
                "goal_ref":"g0","entity_ref":"cup1","query_id":q,"snapshot_id":f"q{q}",
                "camera":"agentview","bbox":[.1,.1,.8,.8],"coordinate_system":"normalized_xyxy",
                "supports":["entity","role","relation","release","interaction"]}]}]}
    def reset(self):
        pass
    def close(self):
        pass


class Actor:
    metadata={"backend":"installed CPU fake actor"}
    def __init__(self):
        self.changes=0
    def reset(self):
        self.changes=0
    def on_goal_change(self,old,new):
        self.changes+=1
    def predict(self,observation,instruction):
        return np.full((8,7),self.changes,dtype=float)
    def close(self):
        pass


def selector(config):
    return Selector()


def actor(config):
    return Actor()
