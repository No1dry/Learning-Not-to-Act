"""Read-only pinned dependencies; never edits or merges an external checkout."""
import hashlib
import importlib
import json
from pathlib import Path
import sys


def _activate(root, manifest_name, package):
    root = Path(root).resolve()
    manifest = json.loads(Path(__file__).with_name(manifest_name).read_text(encoding="utf-8"))
    for name, expected in manifest["files"].items():
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"pinned {package} core dependency differs: {name}")
    for name, module in list(sys.modules.items()):
        if name == package or name.startswith(package + "."):
            file = getattr(module, "__file__", None)
            if file and not Path(file).resolve().is_relative_to(root):
                raise ValueError(f"another {package} checkout is already imported; use a fresh interpreter")
    # A report checkout also contains its older `benchmark` package. Load only
    # the requested package, without adding that checkout to global sys.path.
    # Otherwise report activation can shadow the verified execution core.
    if package not in sys.modules:
        package_root = root / package
        spec = importlib.util.spec_from_file_location(package, package_root / "__init__.py",
            submodule_search_locations=[str(package_root)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[package] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(package, None)
            raise
    return manifest["revision"]


def activate_core(root):
    return _activate(root, "core_files.json", "benchmark")


def activate_reporting(root):
    return _activate(root, "reporting_files.json", "libero_remain_reporting")
