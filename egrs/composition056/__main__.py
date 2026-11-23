"""User-started056 evaluation or read-only three-model comparison."""
import argparse
import json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run', help='evaluate one model on the fixed150 sources')
    run.add_argument('--config', required=True)
    run.add_argument('--model', required=True, choices=('base', 'h0', 'h1'))
    run.add_argument('--output', required=True)
    compare = commands.add_parser('compare', help='compare three complete150 summaries')
    compare.add_argument('--base', required=True)
    compare.add_argument('--h0', required=True)
    compare.add_argument('--h1', required=True)
    compare.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    from .evaluation import compare as compare_reports, run
    if args.command == 'run':
        result = run(args.config, args.output, args.model)
        summary = {'model': result['model'], 'counts': result['counts'], 'tasks': result['tasks']}
    else:
        result = compare_reports(args.base, args.h0, args.h1, args.output)
        summary = {'rates': result['rates'], 'paired': result['paired']}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
