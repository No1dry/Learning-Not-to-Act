"""User-started index50 continuation; no construction/physics diagnosis entry."""
import argparse
import json
from .evaluation import load_config,run,compare


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='command',required=True)
    q=subs.add_parser('run');q.add_argument('--config',required=True)
    q.add_argument('--output',required=True);q.add_argument('--model',required=True,choices=('base','h1'))
    q.add_argument('--continue-from')
    q=subs.add_parser('compare');q.add_argument('--base',required=True)
    q.add_argument('--h1',required=True);q.add_argument('--output',required=True)
    a=p.parse_args(argv)
    if a.command=='run':run(load_config(a.config),a.output,a.model,continue_from=a.continue_from)
    else:print(json.dumps(compare(a.base,a.h1,a.output)),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
