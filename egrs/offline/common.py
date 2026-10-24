"""Versioned, content-addressed operational sidecars (never model context)."""
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def seal(value):
    value = {k: v for k, v in value.items() if k != 'identity'}
    return dict(value, identity=digest(value))


def verify(value, format=None):
    if value.get('identity') != digest({k: v for k, v in value.items() if k != 'identity'}):
        raise ValueError('immutable manifest identity mismatch')
    if format and value.get('format') != format:
        raise ValueError('unsupported manifest format')
    return value


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    from egrs.data import write_json
    write_json(path, seal(value))


def new_output(path):
    path = Path(path).resolve()
    path.mkdir(parents=True, exist_ok=False)
    return path
