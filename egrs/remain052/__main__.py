"""User-started sparse-RGB recovery3, then original base/H1 evaluation450 each."""
import argparse
import json
from .evaluation import load_config, run, compare
from .recovery import recover


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command',required=True)
    p = subs.add_parser('recover')
    p.add_argument('--config',required=True); p.add_argument('--parent',required=True)
    p.add_argument('--output',required=True); p.add_argument('--continue',dest='continuation',action='store_true')
    p = subs.add_parser('run')
    p.add_argument('--config',required=True); p.add_argument('--model',required=True,choices=('base','h1')); p.add_argument('--output',required=True)
    p = subs.add_parser('compare')
    p.add_argument('--base',required=True); p.add_argument('--h1',required=True); p.add_argument('--output',required=True)
    args = parser.parse_args(argv)
    if args.command=='recover':
        result = recover(load_config(args.config),args.parent,args.output,continuation=args.continuation)
        print(json.dumps({k:result[k] for k in ('ready','failed','recovery_processed','complete')}),flush=True)
        if not result['complete']:
            raise SystemExit('052 incomplete; original failures retained, model evaluation NOT started')
    elif args.command=='run':
        run(load_config(args.config),args.output,args.model)
    else:
        print(json.dumps(compare(args.base,args.h1,args.output)),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
