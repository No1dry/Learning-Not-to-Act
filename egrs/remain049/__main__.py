"""Explicit prepare/run/compare entrypoints; no real work runs on import."""
import argparse
import json
from pathlib import Path

from .evaluation import compare, load_config, run
from .preparation import prepare


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    p = subs.add_parser('prepare')
    p.add_argument('--config', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--continue', dest='continuation', action='store_true')
    p = subs.add_parser('run')
    p.add_argument('--config', required=True, type=Path)
    p.add_argument('--model', required=True, choices=('base', 'h1'))
    p.add_argument('--output', required=True, type=Path)
    p = subs.add_parser('compare')
    p.add_argument('--base', required=True, type=Path)
    p.add_argument('--h1', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == 'compare':
        result = compare(args.base, args.h1, args.output)
    else:
        cfg = load_config(args.config)
        if args.command == 'prepare':
            if args.output.resolve() != Path(cfg['source_bank']).resolve():
                raise ValueError('049 prepare output must match configured new source bank')
            result = prepare(cfg, args.output, continuation=args.continuation)
            if not result['complete']:
                raise SystemExit('049 preparation incomplete: failed sources retained; model evaluation not started')
        else:
            result = run(cfg, args.output, args.model)
    print(json.dumps({k: result[k] for k in ('schema_version', 'complete', 'ready', 'failed', 'counts',
                    'base', 'h1', 'delta_pp') if k in result}, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
