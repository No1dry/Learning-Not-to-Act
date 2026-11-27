"""User-started Task057 counterfactual probe build or evaluation; no training."""
import argparse
import json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build', help='construct exactly60 probe sources in a fresh directory')
    build.add_argument('--config', required=True)
    build.add_argument('--output', required=True)
    run = commands.add_parser('run', help='evaluate base on the fixed60 probe sources')
    run.add_argument('--config', required=True)
    run.add_argument('--output', required=True)
    run.add_argument('--model', default='base', choices=('base',))
    inspect = commands.add_parser('inspect', help='read probe bank evidence without native simulation')
    inspect.add_argument('--bank', required=True)
    args = parser.parse_args(argv)
    keys = ('ready', 'failed', 'pending', 'expected', 'ready_percent', 'complete', 'per_task')
    if args.command == 'build':
        from .preparation import prepare
        report = prepare(args.config, args.output)
        print(json.dumps({key: report[key] for key in keys}, indent=2))
        if not report['complete']:
            raise SystemExit(1)
        return 0
    if args.command == 'inspect':
        from .preparation import read_bank
        report = read_bank(args.bank)
        print(json.dumps({key: report[key] for key in keys}, indent=2))
        if not report['complete']:
            raise SystemExit(1)
        return 0
    from .evaluation import run
    result = run(args.config, args.output, args.model)
    print(json.dumps({'model': result['model'], 'counts': result['counts'],
                      'tasks': result['tasks']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
