"""File-only047 configuration and input binding; no native/ML imports."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

SCHEMA = "task047-official-cross-suite-v1"
REVISION = "e4287e94541f459edc4feabc4e181f537cd569a8"
BASE_SOURCE = {
    "repository": "moojink/openvla-7b-oft-finetuned-libero-spatial-object-goal-10",
    "revision": "638918f3d1c2e43a39a8a20772bdb8b91835e4b7",
}
ADAPTER_SHA = "78a96aa79fc996f22fda3dd1680a6edc0ff0dd59312c501d1aa4f96be740201d"
H0_ADAPTER_SHA = "e361121756cc7ee25b90ccb1cb4aa296ce4ea93ac07bd0841409df09b0e16c20"
STATS_SHA = "6ec6ef68d0d5bae4cb5f9fc9acb715a22b9f4545e9e9b300d0d88695cd7afec3"
SOURCE_HASHES = {
    "experiments/robot/libero/run_libero_eval.py": "701a20b6ca2942aa36e0e7d567b25647268b936a23af79c5893534f10bec7802",
    "experiments/robot/libero/libero_utils.py": "489c16dc8220845b2936ddb81aafd7469061d2009b0edddb2f85703bc51a204f",
    "experiments/robot/openvla_utils.py": "eed754d7c5f9821aae2fe0531dbe01df8c11df0d5c79b4aeeb9bb4452124bdf5",
    "experiments/robot/robot_utils.py": "93541b01edd4de49fcc9a1d9249e11fea008b9502fd755096503aaec93773da0",
}
COMPONENT_HASHES = {
    "action_head--300000_checkpoint.pt": "f9647226ca9a1ee64ff8ed1ec380c89110afc6fc2bf6d0ae463cc4023165b4dc",
    "proprio_projector--300000_checkpoint.pt": "1792c6e19381d3c7c814e2d49836a855d3a38b0693919416f52b3c5af39505c8",
}
CODE_HASHES = {
    "config.json": "bcb688a66f3e94a42311b77d37b7e1484886701f7b2aa8e36d165dfccac92ae6",
    "modeling_prismatic.py": "b5431a074c0025a12e46dc954a5e18d1d73477babb5ae42e3a12ab4b907f33a6",
    "configuration_prismatic.py": "68cc5ae34f1b46af3168d8d479cb81bb776965653453fd904aa8eefb6c8f9f68",
}
HORIZONS = {"libero_spatial": 220, "libero_object": 280, "libero_goal": 300}
CELLS = tuple((arm, suite) for suite in HORIZONS for arm in ("base", "h1"))
EPISODES = 500
TOTAL = 3000
LIBERO10_SCHEMA = "task048-official-libero10-v1"
H0_LIBERO10_SCHEMA = "task050-official-h0-libero10-v1"


def protocol(scope="three-suites"):
    require(scope in ("three-suites", "libero10", "h0-libero10"), "Unknown official evaluation scope")
    if scope == "h0-libero10":
        return {"schema": H0_LIBERO10_SCHEMA, "label": "050", "module": "egrs.official050",
                "horizons": {"libero_10": 520}, "total": 500,
                "cells": (("h0", "libero_10"),), "title": "H0 LIBERO-10"}
    ten = scope == "libero10"
    horizons = {"libero_10": 520} if ten else dict(HORIZONS)
    return {"schema": LIBERO10_SCHEMA if ten else SCHEMA, "label": "048" if ten else "047",
            "module": "egrs.official048" if ten else "egrs.official047",
            "horizons": horizons, "total": 1000 if ten else 3000,
            "cells": tuple((arm, suite) for suite in horizons for arm in ("base", "h1")),
            "title": "LIBERO-10" if ten else "three-suite retention"}


def config_protocol(config):
    if config.get("schema_version") == H0_LIBERO10_SCHEMA:
        return protocol("h0-libero10")
    require(config.get("schema_version") in (SCHEMA, LIBERO10_SCHEMA), "Unknown official config schema")
    return protocol("libero10" if config["schema_version"] == LIBERO10_SCHEMA else "three-suites")


def horizon(config):
    return config_protocol(config)["horizons"][config["suite"]]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON field: " + key)
        result[key] = value
    return result


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=object_pairs)


def write(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def config_name(arm, suite):
    return arm + "-" + suite.removeprefix("libero_") + ".json"


def cell_name(arm, suite):
    return arm + "-" + suite.removeprefix("libero_")


def load_config(path):
    value = read(path)
    require(isinstance(value, dict) and set(value) == {
        "schema_version", "arm", "suite", "repo_path", "checkpoint", "method_adapter"},
        "047 configuration fields differ")
    spec = config_protocol(value)
    require((value["arm"], value["suite"]) in spec["cells"],
            "Official evaluation schema/arm/suite mismatch")
    for key in ("repo_path", "checkpoint"):
        require(isinstance(value[key], str) and Path(value[key]).is_absolute(),
                "047 requires an absolute " + key)
    if value["arm"] == "base":
        require(value["method_adapter"] is None, "047 base must not load a research adapter")
    else:
        require(isinstance(value["method_adapter"], str) and Path(value["method_adapter"]).is_absolute(),
                "047 H1 adapter directory required")
    return value


def protected_paths(config):
    return [Path(config[k]).resolve() for k in ("repo_path", "checkpoint", "method_adapter") if config[k]]


def validate_output(config, output, inputs=()):
    target = Path(output).resolve()
    for path in [*protected_paths(config), *[Path(p).resolve() for p in inputs]]:
        require(not (target == path or target in path.parents or path in target.parents),
                "047 output overlaps immutable inputs: " + str(path))
    require(not target.exists(), "047 refuses an existing output: " + str(target))
    return target


def statistic_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def expected_key(suite, stats):
    key = suite if suite in stats else suite + "_no_noops"
    require(key in stats, "047 missing suite normalization statistics")
    return key


def read_h1(directory):
    from egrs.hint043.adapter import read_adapter_identity
    identity = read_adapter_identity(directory)
    require(identity["arm"] == "h1" and identity["update"] == identity["final_update"] == 3000
            and identity["adapter_sha256"] == ADAPTER_SHA, "047 requires frozen H1@3000 bytes")
    return identity


def read_h0(directory):
    from egrs.hint043.adapter import read_adapter_identity
    identity = read_adapter_identity(directory)
    require(identity["arm"] == "h0" and identity["update"] == identity["final_update"] == 3000
            and identity["adapter_sha256"] == H0_ADAPTER_SHA, "050 requires frozen H0@3000 bytes")
    return identity


def verify_inputs(config):
    repo, checkpoint = [Path(config[k]).resolve() for k in ("repo_path", "checkpoint")]
    revision = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    require(revision == REVISION, "047 official source revision differs")
    for name, digest in SOURCE_HASHES.items():
        require(sha(repo/name) == digest, "047 official source bytes differ: " + name)
    require(sha(checkpoint/"dataset_statistics.json") == STATS_SHA, "047 dataset statistics differ")
    for name, digest in {**COMPONENT_HASHES, **CODE_HASHES}.items():
        require(sha(checkpoint/name) == digest, "047 original checkpoint component differs: " + name)
    stats = read(checkpoint/"dataset_statistics.json")
    key = expected_key(config["suite"], stats)
    identity = (read_h0(config["method_adapter"]) if config["arm"] == "h0" else
                read_h1(config["method_adapter"]) if config["arm"] == "h1" else None)
    if identity:
        lineage = identity["base_lineage"]
        require(lineage["checkpoint_source"] == BASE_SOURCE and lineage["repo_commit"] == REVISION
                and lineage["dataset_statistics_sha256"] == STATS_SHA
                and lineage["component_checkpoint_sha256"] == COMPONENT_HASHES
                and statistic_sha(stats[lineage["unnorm_key"]]) == lineage["normalization_statistics_sha256"],
                "047 original H1 training lineage differs")
    return {"checkpoint_source": BASE_SOURCE, "repo_commit": REVISION,
            "dataset_statistics_sha256": STATS_SHA, "component_checkpoint_sha256": COMPONENT_HASHES,
            "source_sha256": SOURCE_HASHES, "prepared_checkpoint_code_sha256": CODE_HASHES,
            "evaluation_suite": config["suite"], "unnorm_key": key,
            "normalization_statistics_sha256": statistic_sha(stats[key]),
            "method_adapter": identity, "research_adapter_loaded": identity is not None}


@contextmanager
def checkpoint_view(checkpoint):
    """Same file protection as the accepted core loader, without its evaluator."""
    with tempfile.TemporaryDirectory(prefix="lnta047-checkpoint-") as directory:
        root = Path(directory)
        for source in Path(checkpoint).rglob("*"):
            destination = root/source.relative_to(checkpoint)
            if source.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            elif source.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                if source.suffix in (".json", ".py") or source.stat().st_size <= 16*1024*1024:
                    shutil.copy2(source, destination)
                else:
                    destination.symlink_to(source.resolve())
        yield str(root)
