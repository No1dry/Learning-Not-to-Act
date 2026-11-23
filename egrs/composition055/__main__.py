"""Explicit user-run055 build or read-only inspection; no training/evaluation."""
import argparse
import json


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    build=commands.add_parser('build',help='construct exactly150 precompleted sources in a fresh directory')
    build.add_argument('--config',required=True);build.add_argument('--output',required=True)
    inspect=commands.add_parser('inspect',help='read existing evidence without native simulation or repair')
    inspect.add_argument('--bank',required=True)
    args=parser.parse_args(argv)
    from .preparation import prepare,read_bank
    report=prepare(args.config,args.output) if args.command=='build' else read_bank(args.bank)
    print(json.dumps({k:report[k] for k in ('ready','failed','pending','expected','ready_percent','complete','per_task')},indent=2))
    if not report['complete']:raise SystemExit(1)


if __name__=='__main__':main()
