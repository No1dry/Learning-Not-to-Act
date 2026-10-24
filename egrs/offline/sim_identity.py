"""Standard-library-only source identity shared by controller and bootstrap."""
import hashlib
from pathlib import Path

from .common import digest


def code_identity():
    """Source-byte identity avoids inventing a self-referential commit SHA."""
    root = Path(__file__).resolve().parents[1]
    paths = sorted([*root.rglob('*.py'), *root.joinpath('offline/assets').glob('*.json')])
    value = {p.relative_to(root.parent).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return {'format': 'egrs.sim.code.v1', 'files': value, 'identity': digest(value)}
