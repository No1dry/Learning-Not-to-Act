"""Bind immutable055 manifests to the original headless rollout."""
from copy import deepcopy
from pathlib import Path

from egrs.composition055.evidence import digest, read_json, verified_artifacts
from .catalog import PROTOCOL, PROTOCOL_VERSION, TASK_SUITE, register, task_index


def adapt(manifest_path, row):
    from egrs.composition055.contracts import digest as json_digest, sha

    path = Path(manifest_path).resolve()
    raw = path.read_bytes()
    if sha(path) != row['source_manifest_sha256']:
        raise ValueError('056 source manifest bytes changed after bank inspection')
    manifest = read_json(raw)
    episode = deepcopy(manifest['episode'])
    if (episode['episode_id'] != row['episode_id'] or episode['task_id'] != row['task_id']
            or episode['initial_state_index'] != row['initial_state_index']
            or episode['initial_mask'] != [True, False] or episode['suite'] != TASK_SUITE):
        raise ValueError('056 source episode identity differs from the frozen population')
    index = task_index(episode['task_id'])
    episode.update(libero_task_id=index, policy_seed=7,
                   evaluation_track='composition_generalization', development_source=False)
    source = {
        'protocol': PROTOCOL,
        'protocol_version': PROTOCOL_VERSION,
        'environment_config': {
            'environment': deepcopy(manifest['environment']),
            'control_freq': 20,
            'image_size': 256,
        },
        'episodes': [episode],
        'source': {
            'manifest': str(path),
            'source_manifest_sha256': row['source_manifest_sha256'],
            'artifacts': deepcopy(manifest['artifacts']),
            'ancestry': deepcopy(manifest['ancestry']),
            'provenance': deepcopy(manifest['provenance']),
        },
    }
    source['source_plan_sha256'] = json_digest(source)
    return source


def archive(folder, source):
    from egrs.composition055.contracts import sha

    folder = Path(folder).resolve()
    original = Path(source['source']['manifest'])
    raw = original.read_bytes()
    if sha(original) != source['source']['source_manifest_sha256']:
        raise ValueError('056 source changed before episode archive')
    manifest = read_json(raw)
    if (manifest['episode']['episode_id'] != source['episodes'][0]['episode_id']
            or manifest['artifacts'] != source['source']['artifacts']):
        raise ValueError('056 archived source identity differs from its frozen plan')
    contents = verified_artifacts(original.parent, manifest['artifacts'])
    destination = folder / 'source'
    destination.mkdir(parents=True, exist_ok=False)
    for relative, payload in contents.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    (destination / 'source.json').write_bytes(raw)
    return destination


def validate_archive(folder, source, row, cfg):
    from egrs.composition055.preparation import inspect_source

    path = Path(folder) / 'source' / 'source.json'
    return inspect_source(path, row, cfg)


def make_environment(source, archived_directory):
    from benchmark.remaining_goals.headless.environment import HeadlessLiberoEnv

    registration = register(source, archived_directory)
    config = deepcopy(source['environment_config'])
    config.update(manifest_dir=str(archived_directory), protocol=PROTOCOL)
    env = HeadlessLiberoEnv(config)
    if env.identity != source['environment_config']['environment']:
        env.close()
        raise ValueError('056 actual environment identity differs from its source')
    return env, registration
