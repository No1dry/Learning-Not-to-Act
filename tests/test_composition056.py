import hashlib
import json
import os
import sys
import types
from collections import namedtuple
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from egrs.augmentation.dependencies import activate_core, activate_reporting

activate_core(Path(os.environ['LNA_CORE']))
activate_reporting(Path(os.environ.get('LNA_REPORTING', Path(__file__).resolve().parents[3] / 'implementations/LIBERO-Remain-task034')))

from egrs.composition055.catalog import TASK_ORDER, get_task
from egrs.composition056.catalog import ADAPTER_SHA256, BANK_SHA256, PREPARATION_IDENTITY, TASK_SUITE
from egrs.composition056 import evaluation


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def make_source(directory, task_id='composition_soup_butter', index=0):
    directory.mkdir(parents=True, exist_ok=True)
    profile = get_task(task_id)
    names = ['task.bddl', 'state.npy', 'construction.npz', 'candidate_00_construction.json',
             'candidate_00_static.json', 'replay_0.json', 'replay_1.json', 'replay_0.npz', 'replay_1.npz']
    for name in names:
        path = directory / name
        if name == 'state.npy':
            np.save(path, np.zeros(123), allow_pickle=False)
        else:
            path.write_bytes((name + ' fixture').encode())
    episode = {
        'episode_id': f'{task_id}_s{index:03d}_10',
        'task_id': task_id,
        'suite': TASK_SUITE,
        'task_name': profile['name'],
        'instruction': profile['instruction'],
        'initial_state_index': index,
        'initial_mask': [True, False],
        'source_id': f'composition055_canonical_basket_{index:03d}',
        'seed': index,
        'horizon': 520,
        'retention_steps': 150,
        'goal_specs': profile['goals'],
        'bddl_sha256': 'a' * 64,
        'model_xml_sha256': 'b' * 64,
        'state_path': 'state.npy',
        'state_sha256': 'c' * 64,
        'initial_observation': {'path': 'construction.npz', 'sha256': 'd' * 64},
    }
    manifest = {
        'schema_version': 'remaining-composition055-source-v1',
        'episode': episode,
        'environment': {'name': 'libero', 'fingerprint': 'e' * 64, 'lock': {'control_freq': 20}},
        'ancestry': {'fixture': True},
        'provenance': {'fixture': True},
        'construction_window': {},
        'replay_windows': [],
        'controls': {},
        'artifacts': {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in names},
    }
    raw = json.dumps(manifest).encode()
    manifest_path = directory / 'source.json'
    manifest_path.write_bytes(raw)
    row = {'episode_id': episode['episode_id'], 'task_id': task_id,
           'initial_state_index': index, 'source_manifest': str(manifest_path),
           'source_manifest_sha256': hashlib.sha256(raw).hexdigest()}
    return manifest_path, row


@pytest.mark.parametrize('task_id,expected_index', [
    ('composition_soup_butter', 0),
    ('composition_tomato_cheese', 1),
    ('composition_tomato_butter', 2),
])
def test_private_task_registration_binds_new_suite_bddl_and_roles(tmp_path, monkeypatch, task_id, expected_index):
    from egrs.composition056.catalog import register

    native = types.ModuleType('libero.libero.benchmark')
    native.Task = namedtuple('Task', 'name language problem problem_folder bddl_file init_states_file')
    native.task_maps = {}
    native.BENCHMARK_MAPPING = {}

    class Benchmark:
        def __init__(self, task_order_index=0):
            self.task_order_index = task_order_index

        def _make_benchmark(self):
            self.tasks = list(native.task_maps[self.name].values())
            self.n_tasks = len(self.tasks)

        def get_task(self, index):
            return self.tasks[index]

    native.Benchmark = Benchmark
    parent = types.ModuleType('libero.libero')
    parent.benchmark = native
    parent.__path__ = []
    root = types.ModuleType('libero')
    root.__path__ = []
    monkeypatch.setitem(sys.modules, 'libero', root)
    monkeypatch.setitem(sys.modules, 'libero.libero', parent)
    monkeypatch.setitem(sys.modules, 'libero.libero.benchmark', native)
    from benchmark.remaining_goals.headless import roles

    old_basket = roles.TASKS['basket']
    manifest, row = make_source(tmp_path, task_id)
    source = {'episodes': [json.loads(manifest.read_text())['episode']]}
    registration = register(source, manifest.parent)
    assert registration['libero_task_id'] == expected_index
    assert registration['problem_folder'] == str(manifest.parent)
    task = native.BENCHMARK_MAPPING[TASK_SUITE]().get_task(0)
    assert task.name == get_task(task_id)['name']
    assert task.language == get_task(task_id)['instruction']
    assert task.problem_folder == str(manifest.parent)
    assert roles.TASKS[task_id]['goals'] == get_task(task_id)['goals']
    assert roles.TASKS['basket'] == old_basket


def test_adapt_and_archive_preserve_all_source_bytes(tmp_path):
    from egrs.composition056.source import adapt, archive

    manifest, row = make_source(tmp_path / 'original')
    source = adapt(manifest, row)
    episode = source['episodes'][0]
    assert episode['libero_task_id'] == 0
    assert episode['policy_seed'] == 7
    assert episode['evaluation_track'] == 'composition_generalization'
    assert episode['instruction'] == get_task('composition_soup_butter')['instruction']
    assert source['source']['source_manifest_sha256'] == row['source_manifest_sha256']
    run = tmp_path / 'episode'
    run.mkdir()
    archived = archive(run, source)
    assert (archived / 'source.json').read_bytes() == manifest.read_bytes()
    for name in source['source']['artifacts']:
        assert (archived / name).read_bytes() == (manifest.parent / name).read_bytes()


def test_adapt_rejects_tampered_manifest(tmp_path):
    from egrs.composition056.source import adapt

    manifest, row = make_source(tmp_path)
    manifest.write_bytes(b'changed')
    with pytest.raises(ValueError, match='bytes changed'):
        adapt(manifest, row)


def config_fixture(tmp_path):
    bank = tmp_path / 'bank'
    bank.mkdir()
    runtime = tmp_path / 'runtime.json'
    runtime.write_text('{}')
    h0 = tmp_path / 'h0'
    h1 = tmp_path / 'h1'
    h0.mkdir()
    h1.mkdir()
    protected = tmp_path / 'old-results'
    protected.mkdir()
    cfg = {
        'schema_version': 'task056-composition-eval-v1',
        'source_bank': str(bank),
        'base_runtime': str(runtime),
        'reporting_root': os.environ['LNA_REPORTING'],
        'adapter_h0': str(h0),
        'adapter_h1': str(h1),
        'protected_roots': [str(protected)],
    }
    path = tmp_path / 'evaluation.json'
    write_json(path, cfg)
    return path, cfg


def fake_frozen(rows, model):
    sources = [{'episodes': [dict(row)]} for row in rows]
    return {
        'schema_version': 'task056-composition-eval-v1',
        'model': model,
        'runtime': {'fixture': True},
        'method_adapter': None if model == 'base' else model,
        'adapter_identity': None if model == 'base' else {'arm': model},
        'expected': [dict(row) for row in rows],
        'sources': sources,
        'source_bank_sha256': BANK_SHA256,
        'preparation_identity': PREPARATION_IDENTITY,
        'evaluation_scope': 'fake056',
        'source_config': {},
        'source_config_population': rows,
        'plan_sha256': 'fake-plan',
    }


def fake_record(folder, episode, model, success):
    folder.mkdir(parents=True, exist_ok=True)
    proof = folder / 'task_run.json'
    proof.write_text('{}')
    policy = {
        'checkpoint_source': {'repository': 'fake'},
        'checkpoint_training_suites': ['libero_10'],
        'repo_commit': 'fake',
        'unnorm_key': 'libero_10_no_noops',
        'dataset_statistics_sha256': 'a' * 64,
        'normalization_statistics_sha256': 'b' * 64,
        'inference_source_sha256': {},
        'component_checkpoint_sha256': {},
        'inference_configuration': {},
        'prepared_checkpoint_code_sha256': {},
        'method_adapter': None if model == 'base' else {'arm': model, 'update': 3000},
    }
    primary = {
        'episode_id': episode['episode_id'],
        'task_id': episode['task_id'],
        'suite': episode['suite'],
        'initial_state_index': episode['initial_state_index'],
        'initial_mask': episode['initial_mask'],
        'classification': 'success' if success else 'failure',
        'success': success,
        'execution_status': 'completed',
        'failure_reasons': [] if success else ['goal_not_confirmed_by_horizon'],
        'unknown_reasons': [],
        'official_goals_achieved': success,
        'n_steps': 10,
        'path_complete': True,
        'path_length_m': 1.0,
        'goal_confirmed_step': 10 if success else None,
    }
    source = {
        'model_identity': {'checkpoint': 'fake', 'checkpoint_source': {'repository': 'fake'},
                           'policy_metadata': policy, 'model_runtime_sha256': 'fake-runtime'},
        'input_evidence_level': 'fake',
        'run_path': str(folder),
        'verified_files': [{'path': str(proof), 'sha256': hashlib.sha256(proof.read_bytes()).hexdigest()}],
        'new_execution': True,
    }
    return {'condition': '10', 'legacy': {}, 'primary': primary, 'source': source}


def install_fake_run(monkeypatch, cfg):
    from benchmark.remaining_goals import isolated_policy

    class Policy:
        def __init__(self, config):
            self.provenance = {'policy_metadata': {'method_adapter': config.get('method_adapter')}}

        def close(self):
            return None

    monkeypatch.setattr(isolated_policy, 'SubprocessPolicy', Policy)
    monkeypatch.setattr(evaluation, 'load_config', lambda path: cfg)
    monkeypatch.setattr(evaluation, 'verify_model', lambda *args: None)
    monkeypatch.setattr(evaluation, 'plan', lambda config, model: fake_frozen(config['_rows'], model))

    def execute(folder, source, frozen, policy):
        episode = source['episodes'][0]
        model = frozen['model']
        index = episode['initial_state_index']
        success = index % 5 == 0 if model == 'base' else index % 2 == 0 if model == 'h0' else True
        return fake_record(folder, episode, model, success)

    monkeypatch.setattr(evaluation, 'execute_episode', execute)


def test_three_model_run_and_comparison_is_exactly_450_new_episodes(tmp_path, monkeypatch):
    rows = []
    for task in TASK_ORDER:
        for index in range(50):
            rows.append({'episode_id': f'{task}_s{index:03d}_10', 'task_id': task,
                         'suite': TASK_SUITE, 'initial_state_index': index, 'initial_mask': [True, False]})
    config, cfg = config_fixture(tmp_path)
    cfg['_rows'] = rows
    write_json(tmp_path / 'bank' / 'sources.json', {'rows': rows})
    install_fake_run(monkeypatch, cfg)
    outputs = {}
    for model in ('base', 'h0', 'h1'):
        output = tmp_path / ('eval-' + model)
        report = evaluation.run(config, output, model)
        assert report['counts']['expected'] == report['counts']['completed'] == 150
        assert report['counts']['unresolved_jobs'] == 0
        assert report['execution_errors'] == []
        assert report['integrity_errors'] == []
        assert report['ordinary_episodes'] == 0 and report['source_generation'] == 0
        outputs[model] = output
    assert outputs['base'].joinpath('summary.json').is_file()
    comparison = evaluation.compare(outputs['base'], outputs['h0'], outputs['h1'], tmp_path / 'comparison.json')
    assert [comparison['rates'][model]['numerator'] for model in ('base', 'h0', 'h1')] == [30, 75, 150]
    assert comparison['paired']['base_to_h0']['gains'] == 60
    assert comparison['paired']['base_to_h0']['losses'] == 15
    assert comparison['paired']['h0_to_h1']['gains'] == 75
    assert comparison['paired']['h0_to_h1']['losses'] == 0
    assert len(comparison['tasks']) == 3
    assert all(task['base']['numerator'] == 10 and task['h0']['numerator'] == 25 and task['h1']['numerator'] == 50
               for task in comparison['tasks'])


def test_execution_failure_is_preserved_not_a_complete_model_score(tmp_path, monkeypatch):
    rows = [{'episode_id': f'{TASK_ORDER[0]}_s000_10', 'task_id': TASK_ORDER[0],
             'suite': TASK_SUITE, 'initial_state_index': 0, 'initial_mask': [True, False]}]
    config, cfg = config_fixture(tmp_path)
    cfg['_rows'] = rows
    write_json(tmp_path / 'bank' / 'sources.json', {'rows': rows})
    install_fake_run(monkeypatch, cfg)
    monkeypatch.setattr(evaluation, 'execute_episode', lambda *args: (_ for _ in ()).throw(RuntimeError('synthetic stop')))
    with pytest.raises(RuntimeError, match='synthetic stop'):
        evaluation.run(config, tmp_path / 'failed', 'base')
    report = json.loads((tmp_path / 'failed' / 'summary.json').read_text())
    assert report['software_exit'] == 'incomplete'
    assert report['execution_errors'][0]['phase'] == 'execution'
    assert report['counts']['formal_SR'] is None


def test_plan_separates_base_h0_h1_and_rejects_incomplete_bank(tmp_path, monkeypatch):
    from egrs.composition055 import preparation
    from benchmark.remaining_goals.headless import nine_planning

    config, cfg = config_fixture(tmp_path)
    rows = []
    for task in TASK_ORDER:
        for index in range(50):
            rows.append({'episode_id': f'{task}_s{index:03d}_10', 'task_id': task,
                         'initial_state_index': index, 'source_manifest': f'fake/{task}/{index}',
                         'source_manifest_sha256': '0' * 64})
    bank = {'complete': True, 'ready': 150, 'failed': 0, 'pending': 0,
            'preparation_identity': PREPARATION_IDENTITY, 'snapshot': {'config': {}}, 'rows': rows}
    write_json(tmp_path / 'bank' / 'sources.json', bank)
    monkeypatch.setattr(evaluation, 'sha', lambda path: BANK_SHA256)
    monkeypatch.setattr(preparation, 'read_bank', lambda path: bank)
    monkeypatch.setattr(nine_planning, 'load_runtime', lambda path: {'runtime': Path(path).name})
    monkeypatch.setattr(evaluation, 'adapter_identity', lambda directory, model: {'arm': model, 'adapter_sha256': ADAPTER_SHA256[model]})
    monkeypatch.setattr(evaluation, 'adapt', lambda path, row: {
        'episodes': [{'episode_id': row['episode_id'], 'task_id': row['task_id'], 'suite': TASK_SUITE,
                      'initial_state_index': row['initial_state_index'], 'initial_mask': [True, False]}]})
    for model in ('base', 'h0', 'h1'):
        frozen = evaluation.plan(cfg, model)
        assert len(frozen['sources']) == len(frozen['expected']) == 150
        assert frozen['source_bank_sha256'] == BANK_SHA256
        if model == 'base':
            assert frozen['adapter_identity'] is None
            assert 'policy_factory' not in evaluation.worker(frozen)
        else:
            assert frozen['adapter_identity']['adapter_sha256'] == ADAPTER_SHA256[model]
            worker = evaluation.worker(frozen)
            assert worker['method_adapter'] == cfg['adapter_' + model]
            assert worker['hint043_arm'] == model and worker['hint043_checkpoint_step'] == 3000
    monkeypatch.setattr(preparation, 'read_bank', lambda path: {**bank, 'complete': False})
    with pytest.raises(ValueError, match='complete immutable055'):
        evaluation.plan(cfg, 'base')


def test_template_expands_and_output_protection_refuses_bank_overlap(tmp_path, monkeypatch):
    config, cfg = config_fixture(tmp_path)
    template = Path(__file__).resolve().parents[1] / 'configs/composition056/evaluation.example.json'
    for key, value in {'LNA055_BANK': cfg['source_bank'], 'LNA_BASE_RUNTIME': cfg['base_runtime'],
                       'LNA_REPORTING': cfg['reporting_root'],
                       'LNA_H0_ADAPTER': cfg['adapter_h0'], 'LNA_H1_ADAPTER': cfg['adapter_h1'],
                       'LNA_EXISTING_DATA_ROOT': cfg['protected_roots'][0],
                       'LNA_EXISTING_RUNS_ROOT': cfg['protected_roots'][0]}.items():
        monkeypatch.setenv(key, value)
    loaded = evaluation.load_config(template)
    assert loaded['source_bank'] == cfg['source_bank']
    monkeypatch.delenv('LNA_H0_ADAPTER')
    with pytest.raises(ValueError, match='Unresolved'):
        evaluation.load_config(template)
    with pytest.raises(ValueError, match='overlaps'):
        evaluation.protect(cfg, Path(cfg['source_bank']) / 'new', config)
    with pytest.raises(FileExistsError):
        evaluation.protect(cfg, tmp_path / 'bank', config)


def test_fresh_cli_help_does_not_import_native_or_model_modules():
    import subprocess

    code = """
import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'torch','mujoco','libero','benchmark'}:raise AssertionError(fullname)
sys.meta_path.insert(0,Block())
sys.argv=['composition056','--help']
from egrs.composition056.__main__ import main
main()
"""
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert '{run,compare}' in result.stdout


def test_raw_result_creates_parent_directory(tmp_path):
    result = {'status': 'completed', 'episode_id': 'composition_soup_butter_s000_10', 'trace': []}
    episode = {'episode_id': 'composition_soup_butter_s000_10'}
    path = evaluation.write_raw_result(tmp_path / 'episode', result, episode)
    assert path == tmp_path / 'episode' / 'raw' / 'composition_soup_butter_s000_10.json'
    assert path.is_file()
    assert json.loads(path.read_text()) == result
