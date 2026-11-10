"""User-started040 preparation, fixed C1 training and original formal evaluation."""
import argparse
import importlib
import json
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('plan', 'generate'):
        entry = commands.add_parser(name)
        entry.add_argument('--config', required=True)
        entry.add_argument('--out', '--output', dest='out', required=True)
    train = commands.add_parser('train')
    train.add_argument('--arm', choices=('c1',), default='c1')
    for name in ('config', 'runtime', 'benchmark-root', 'index-dir', 'output-dir'):
        train.add_argument('--'+name, required=True)
    train.add_argument('--resume')
    evaluate = commands.add_parser('eval')
    evaluate.add_argument('--arm', choices=('c1',), default='c1')
    evaluate.add_argument('--mode', choices=('plan', 'run', 'report'), default='run')
    evaluate.add_argument('--config')
    evaluate.add_argument('--run-dir')
    evaluate.add_argument('--out', '--output', dest='out', required=True)
    args = parser.parse_args(argv)
    if args.command == 'plan':
        result = importlib.import_module('egrs.coverage040.plan').build_plan(args.config)
        with Path(args.out).open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        return result
    if args.command == 'generate':
        result = importlib.import_module('egrs.coverage040.pipeline').generate(args.config, args.out)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return result
    if args.command == 'train':
        return importlib.import_module('egrs.coverage040.training').run(args)
    if args.mode == 'report' and not args.run_dir:
        parser.error('eval --mode report requires --run-dir')
    if args.mode != 'report' and not args.config:
        parser.error('eval --mode plan/run requires --config')
    module = importlib.import_module('egrs.task_control.evaluation')
    if args.mode == 'run':
        return module.run(args.config, args.out, arm='c1')
    if args.mode == 'report':
        return module.report_run(args.run_dir, args.out, arm='c1')
    result = module.build_plan(args.config, arm='c1')
    with Path(args.out).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    return result


if __name__ == '__main__':
    main()
