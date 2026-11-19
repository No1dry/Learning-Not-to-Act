"""Reuse the existing exact native LoRA restore, with explicit H0 identity."""
from egrs.official047 import contracts as c
from egrs.official047.adapter import attach_h1


def attach_h0(model, action_head, proprio_projector, identity, directory, cfg):
    c.require(identity.get("arm") == "h0" and identity.get("adapter_sha256") == c.H0_ADAPTER_SHA
              and identity.get("update") == identity.get("final_update") == 3000,
              "050 requires the unchanged H0@3000 artifact")
    return attach_h1(model, action_head, proprio_projector, identity, directory, cfg)
