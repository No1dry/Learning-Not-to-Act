"""Private absolute-script entry: bind method source before worker/native imports.

No configurable module or factory is accepted. Keep cwd unchanged so native
core, BDDL and asset paths retain their caller-relative interpretation.
"""
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    import egrs
    import egrs.offline
    if (Path(egrs.__file__).resolve() != root/'egrs/__init__.py'
            or Path(egrs.offline.__file__).resolve() != root/'egrs/offline/__init__.py'):
        raise ValueError('worker implementation identity mismatch: package root')
    from egrs.offline.sim_identity import code_identity
    if len(sys.argv) not in {2,3} or code_identity()['identity'] != sys.argv[1]:
        raise ValueError('worker implementation identity mismatch: source bytes')
    mode=sys.argv[2] if len(sys.argv)==3 else 'annotation'
    if mode not in {'annotation','alignment_diagnostic'}:
        raise ValueError('unsupported closed worker mode')
    if mode=='alignment_diagnostic':
        from egrs.offline import sim_diagnostic_worker
        if Path(sim_diagnostic_worker.__file__).resolve()!=root/'egrs/offline/sim_diagnostic_worker.py':
            raise ValueError('worker implementation identity mismatch: diagnostic worker root')
        return sim_diagnostic_worker.main()
    from egrs.offline import sim_worker
    if Path(sim_worker.__file__).resolve() != root/'egrs/offline/sim_worker.py':
        raise ValueError('worker implementation identity mismatch: worker root')
    return sim_worker.main()


if __name__ == '__main__':
    raise SystemExit(main())
