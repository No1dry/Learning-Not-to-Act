"""Standalone user-started inference; JSON files contain the shared wire schema."""
import argparse
import json
from pathlib import Path

from . import QwenSelector
from .model import resolve_config


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="selector JSON; adapter points at a saved adapter/ directory")
    parser.add_argument("--core-config", help="optional explicit pinned eval core dependency JSON")
    parser.add_argument("--mode", choices=("registry", "predict"), required=True)
    parser.add_argument("--input", required=True, help="instruction-only JSON or sensor/context envelope with local image paths")
    parser.add_argument("--output", help="new prediction JSON file; defaults to stdout")
    parser.add_argument("--dry-run", action="store_true", help="inspect request/config without images or model loading")
    args = parser.parse_args(argv)
    config = resolve_config(json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else {})
    request = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if args.mode == "registry" and (set(request) != {"instruction"} or not isinstance(request["instruction"], str)):
        raise ValueError("registry request accepts only instruction")
    if args.mode == "predict" and set(request) != {"sensor", "context"}:
        raise ValueError("prediction requires sensor/context envelope")
    if args.dry_run:
        print(json.dumps({"mode": args.mode, "model_loaded": False, "images_loaded": False, "config": config}, indent=2))
        return 0
    if args.output and Path(args.output).exists():
        raise ValueError("output already exists")
    if args.core_config:
        from egrs.core import activate
        activate(json.loads(Path(args.core_config).read_text(encoding="utf-8")))
    selector = QwenSelector(config)
    try:
        if args.mode == "registry":
            result = selector.registry(request["instruction"])
        else:
            from .prompt import bounded_payload, IMAGE_KEYS
            from .encoding import load_images
            import numpy as np
            request, _ = bounded_payload(request, config["use_history"], config["max_images"])
            images = iter(load_images(request))
            for sensor in request["sensor"]:
                for key in IMAGE_KEYS:
                    if key in sensor["observation"]:
                        sensor["observation"][key] = np.asarray(next(images))
            result = selector.predict(request)
        content = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            with Path(args.output).open("x", encoding="utf-8") as file:
                file.write(content)
        else:
            print(content, end="")
    finally:
        selector.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
