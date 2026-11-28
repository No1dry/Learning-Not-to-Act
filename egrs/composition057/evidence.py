"""File and numerical evidence helpers for the isolated source builder."""

from hashlib import sha256
import io
import json
from pathlib import Path, PurePosixPath
from pickletools import genops
from zipfile import ZipFile

import numpy as np


def digest(raw):
    return sha256(raw).hexdigest()


def array_digest(value):
    return digest(np.asarray(value, dtype='<f8').tobytes())


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate evidence key: {key}')
        result[key] = value
    return result


def read_json(raw):
    def invalid(value):
        raise ValueError(f'nonfinite JSON evidence value: {value}')

    return json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=invalid)


def write_json(path, value):
    raw = (json.dumps(value, sort_keys=True, allow_nan=False, indent=2) + '\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)


def canonical_rows(raw):
    """Decode the SHA-pinned legacy NumPy payload without executing pickle."""
    with ZipFile(io.BytesIO(raw)) as archive:
        payload = archive.read('archive/data.pkl')
    operations = [(opcode.name, arg) for opcode, arg, _ in genops(payload)]
    strings = [arg for op, arg in operations if op == 'BINUNICODE']
    dimensions = [('BININT1', 1), ('BININT1', 50), ('BININT1', 123), ('TUPLE2', None)]
    if operations[23:27] != dimensions or strings[:4] != ['b', 'latin1', 'f8', '<'] or len(strings) != 5:
        raise ValueError('canonical archive is not the pinned 50x123 little-endian float64 layout')
    flat = strings[-1].encode('latin1')
    if len(flat) != 50 * 123 * 8:
        raise ValueError('canonical archive vector payload has wrong size')
    result = np.frombuffer(flat, dtype='<f8').reshape(50, 123)
    if not np.isfinite(result).all():
        raise ValueError('canonical archive contains nonfinite state')
    return result


def vector(raw):
    value = np.load(io.BytesIO(raw), allow_pickle=False)
    if not isinstance(value, np.ndarray) or value.dtype != np.float64 or value.shape != (123,) or not np.isfinite(value).all():
        raise ValueError('selected state must be a finite 123-value float64 NPY vector')
    return value


def verified_artifacts(directory, hashes):
    """Read exact hashed bytes within a source directory, once per artifact."""
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError('source artifact hashes are required')
    contents = {}
    for relative, expected in hashes.items():
        path = PurePosixPath(relative)
        if path.is_absolute() or path.as_posix() != relative or any(
            part == '..' or '\\' in part or ':' in part for part in path.parts
        ):
            raise ValueError('invalid relative source artifact path')
        target = (directory / Path(*path.parts)).resolve()
        if not target.is_relative_to(directory) or target == directory:
            raise ValueError('source artifact path escapes its pack')
        raw = target.read_bytes()
        if digest(raw) != expected:
            raise ValueError(f'source artifact hash mismatch: {relative}')
        contents[relative] = raw
    return contents
