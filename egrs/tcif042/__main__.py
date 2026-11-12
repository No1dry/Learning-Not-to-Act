"""Explicit042 training stages and single-student formal evaluation only."""
import argparse
import importlib
import json
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    train = commands.add_parser('train')
    train.add_argument('--config', required=True)
    train.add_argument('--output-dir', required=True)
    train.add_argument('--resume')
    evaluate = commands.add_parser('eval')
    evaluate.add_argument('--experiment-arm', choices=('f0', 'f1'), required=True)
    evaluate.add_argument('--mode', choices=('plan', 'run', 'report'), default='run')
    evaluate.add_argument('--config')
    evaluate.add_argument('--run-dir')
    evaluate.add_argument('--out', '--output', dest='out', required=True)
    args = parser.parse_args(argv)
    if args.command == 'train':
        return importlib.import_module('egrs.tcif042.training').run(args)
    if args.mode == 'report' and not args.run_dir:
        parser.error('eval --mode report requires --run-dir')
    if args.mode != 'report' and not args.config:
        parser.error('eval --mode plan/run requires --config')
    module = importlib.import_module('egrs.tcif042.evaluation')
    if args.mode == 'run':
        return module.run(args.config, args.out, experiment_arm=args.experiment_arm)
    if args.mode == 'report':
        return module.report_run(args.run_dir, args.out, experiment_arm=args.experiment_arm)
    result = module.build_plan(args.config, experiment_arm=args.experiment_arm)
    with Path(args.out).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    return result


if __name__ == '__main__':
    main()
