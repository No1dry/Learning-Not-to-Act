"""File-only method composition, dependency inspection and sidecar audit."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def relative_paths(config, base):
    """Resolve file-backed actor values without resolving Python symlinks."""
    config = deepcopy(config)
    for mapping, names in ((config.get("runtime", {}), ("python_executable",)),
                           (config.get("adapter_options", {}), ("repo_path", "checkpoint", "action_decoder_path"))):
        for key in names:
            if mapping.get(key):
                value = Path(mapping[key]).expanduser()
                mapping[key] = os.path.abspath(value if value.is_absolute() else base / value)
    return config


def inspect_config(config):
    from .core import inspect_core
    gaps = []
    identity = None
    try:
        identity = inspect_core(config["core"])
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        gaps.append("core: " + str(error))
    # inspect_core failures from git also remain a static dependency gap.
    for part in ("actor", "selector"):
        if part == "selector" and config["variant"] == "baseline":
            continue
        value = config[part]
        paths = {"runtime.python_executable": value["runtime"]["python_executable"]}
        if part == "actor":
            paths.update({"adapter_options." + k: v for k, v in value.get("adapter_options", {}).items()
                          if k in {"repo_path", "checkpoint", "action_decoder_path"}})
        else:
            paths.update({k: value[k] for k in ("adapter", "lora_path") if value.get(k)})
        for key, path in paths.items():
            if not Path(path).exists():
                gaps.append(f"{part}.{key}: missing {path}")
        if part == "selector" and value.get("adapter", value.get("lora_path")):
            try:
                from .selector.model import resolve_config, checkpoint_identity
                expected = dict(value, use_history=config["history"])
                checkpoint_identity(resolve_config(expected))
            except (OSError, ValueError, KeyError) as error:
                gaps.append("selector checkpoint: " + str(error))
    if Path(config["output_dir"]).exists():
        gaps.append("output_dir already exists; choose a new run directory")
    return {"configuration_valid": True, "local_dependencies_present": not gaps,
            "core": identity, "gaps": gaps, "models_loaded": False, "native_initialized": False,
            "batch_014_integration_verified": False,
            "note": "File presence does not verify installed packages, weights, GPU readiness or method performance."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    compose = sub.add_parser("compose", help="write a new config from an existing actor JSON; no model work")
    compose.add_argument("--actor", required=True, help="complete original actor JSON, including runtime/execution")
    compose.add_argument("--core", required=True, help="core dependency JSON with absolute root")
    compose.add_argument("--selector", help="selector training/inference configuration JSON")
    compose.add_argument("--selector-python", help="absolute selector interpreter with this package installed")
    compose.add_argument("--adapter", help="trained checkpoint-N/adapter directory; omit only for baseline/no_lora")
    from .actor import AUDITED
    compose.add_argument("--capability", required=True, choices=[*AUDITED, "custom_hook"])
    compose.add_argument("--variant", default="full", choices=["full", "baseline", "no_lora", "no_history", "no_role"])
    compose.add_argument("--run-dir", required=True, help="new method sidecar directory")
    compose.add_argument("--output", required=True, help="new method JSON file")
    inspect = sub.add_parser("inspect", help="check config and local file identities without native/model imports")
    inspect.add_argument("--config", required=True)
    sidecar = sub.add_parser("sidecar", help="audit a method episode and optionally join an original core result")
    sidecar.add_argument("--method", required=True)
    sidecar.add_argument("--core-result", help="JSON object returned by original core run_episode")
    args = parser.parse_args(argv)
    from .configuration import validate_config, load_config
    if args.command == "compose":
        actor_file = Path(args.actor).resolve()
        config = {"policy_factory": "egrs.policy:make_policy", "core": read(args.core),
                  "actor": relative_paths(read(actor_file), actor_file.parent),
                  "goal_change_capability": args.capability, "variant": args.variant,
                  "history": args.variant != "no_history", "output_dir": os.path.abspath(args.run_dir)}
        core_root = Path(config["core"]["root"]).expanduser()
        config["core"]["root"] = os.path.abspath(core_root if core_root.is_absolute() else Path(args.core).resolve().parent / core_root)
        if args.variant != "baseline":
            if not args.selector or not args.selector_python:
                parser.error("non-baseline variants require --selector and --selector-python")
            config["selector"] = read(args.selector)
            config["selector"].pop("lora_path",None)
            config["selector"]["runtime"] = {"python_executable": os.path.abspath(args.selector_python),
                "startup_timeout_seconds": 1200, "predict_timeout_seconds": 180}
            config["selector"]["adapter"] = os.path.abspath(args.adapter) if args.adapter else None
            config["selector"]["use_history"] = config["history"]
        config = validate_config(config)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(config, stream, ensure_ascii=False, indent=2, allow_nan=False)
        print(json.dumps({"created": str(output), "models_loaded": False}))
        return 0
    if args.command == "inspect":
        report = inspect_config(load_config(args.config))
        print(json.dumps(report, indent=2))
        return 0 if report["local_dependencies_present"] else 2
    from .sidecar import inspect_sidecar
    report = inspect_sidecar(args.method, read(args.core_result) if args.core_result else None)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
