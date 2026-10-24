"""Factory facade loaded inside the existing actor worker, not its parent."""
from copy import deepcopy
import importlib


AUDITED = {
    "openvla": "benchmark.remaining_goals.adapters.openvla:make_policy",
    "openvla_oft": "benchmark.remaining_goals.adapters.openvla_oft:make_policy",
    "univla": "benchmark.remaining_goals.adapters.univla:make_policy",
    "pi0": "benchmark.remaining_goals.adapters.openpi:make_policy",
    "pi05": "benchmark.remaining_goals.adapters.openpi:make_policy",
    "groot_n17": "benchmark.remaining_goals.adapters.groot:make_policy",
}


def facade_config(actor_config, capability, core):
    return {"policy_factory": "egrs.actor:make_policy",
            "runtime": deepcopy(actor_config["runtime"]),
            "execution": deepcopy(actor_config.get("execution", {})),
            "adapter_options": {"actor_config": deepcopy(actor_config),
                                "goal_change_capability": capability, "core": deepcopy(core)}}


class ActorFacade:
    def __init__(self, actor, capability, provenance):
        if capability not in AUDITED and capability != "custom_hook":
            raise ValueError("unknown goal-change capability")
        if capability == "custom_hook" and not callable(getattr(actor, "on_goal_change", None)):
            raise ValueError("custom adapter must declare a real on_goal_change hook")
        if capability == "univla" and (not hasattr(actor, "_history") or not callable(getattr(getattr(actor,"decoder",None), "reset",None))):
            raise ValueError("UniVLA history/decoder contract changed")
        self.actor, self.capability, self.previous = actor, capability, None
        self.metadata = {"method_facade": "egrs.actor/v1", "goal_change_capability": capability,
                         "actor": deepcopy(provenance), "episode_reset_only_reseeds": True}

    def reset(self):
        self.actor.reset()
        self.previous = None

    def predict(self, observation, instruction):
        if self.previous is not None and instruction != self.previous:
            if self.capability == "univla":
                self.actor._history = ""
                self.actor.decoder.reset()
            elif self.capability == "custom_hook":
                self.actor.on_goal_change(self.previous, instruction)
            # Audited stateless paths deliberately have no reset.
        result = self.actor.predict(observation, instruction)
        self.previous = instruction
        return result

    def close(self):
        self.actor.close()


def make_policy(config):
    from .core import activate
    options = config["adapter_options"]
    activate(options["core"])
    actor_config = deepcopy(options["actor_config"])
    capability = options["goal_change_capability"]
    factory = actor_config["policy_factory"]
    if capability != "custom_hook" and AUDITED.get(capability) != factory:
        raise ValueError("audited goal-change capability does not match the original actor factory")
    if factory in {"egrs.actor:make_policy", "egrs.policy:make_policy"}:
        raise ValueError("recursive actor facade is not allowed")
    from benchmark.remaining_goals.adapters.oft_transfer import validate_suite_transfer
    from benchmark.remaining_goals.policy_worker import provenance
    validate_suite_transfer(actor_config)
    module, sep, name = factory.partition(":")
    if not sep:
        raise ValueError("actor factory must be module:callable")
    actor = getattr(importlib.import_module(module), name)(actor_config)
    try:
        return ActorFacade(actor, capability, provenance(actor_config, actor))
    except BaseException:
        actor.close()
        raise
