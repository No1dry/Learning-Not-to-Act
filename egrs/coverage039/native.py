"""039 worker entry; reuse035's strict native pins without changing its default."""
from pathlib import Path
import sys

from egrs.augmentation.data import read_json
from egrs.trajectory_augmentation.native import NativeSession
from .generation import (AttemptLedger, Heartbeat, durable_write, generate_session,
                         initialization_failure, _recover_source)


def worker(request_path):
    request = read_json(request_path); source = request['source']; config = request['config']
    directory = Path(request['output_dir']); session = None
    ledger = AttemptLedger(config['_budget_ledger'])
    if not config.get('_normal_pre_reserved') or not ledger.contains(source['source_id'], 'normal', 'normal', 0):
        raise ValueError('039 worker requires durable parent reservation before native initialization')
    initialization_failure(source, directory, 'native_initialization_interrupted')
    try:
        with Heartbeat(directory, source['source_id']):
            session = NativeSession(source, config, request['data_root'])
        result = generate_session(session, source, config, directory)
    except Exception as error:
        result = _recover_source(source, directory, f'{type(error).__name__}: {error}')
    finally:
        if session is not None: session.close()
    durable_write(directory/'result.json', result)
    return result


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--request':
        raise SystemExit('Use python -m egrs.coverage039 generate.')
    worker(sys.argv[2])
