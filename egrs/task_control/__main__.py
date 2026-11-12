"""Explicit038 operations. No operation is performed while importing this CLI."""
import argparse
import importlib
import json
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    index=commands.add_parser('index',help='user-started file-only index; no new simulation')
    index.add_argument('--generated-export',required=True)
    index.add_argument('--retention-index',required=True)
    index.add_argument('--out',required=True)
    train=commands.add_parser('train',help='real training only after separate budget authorization')
    train.add_argument('--arm',choices=('c0','c1'),required=True)
    for name in ('config','runtime','benchmark-root','index-dir','output-dir'):
        train.add_argument('--'+name,required=True)
    train.add_argument('--resume')
    evaluate=commands.add_parser('eval',help='plan by default; run/report selected explicitly')
    evaluate.add_argument('--arm',choices=('c0','c1'),required=True)
    evaluate.add_argument('--mode',choices=('plan','run','report'),default='plan')
    evaluate.add_argument('--config')
    evaluate.add_argument('--run-dir')
    evaluate.add_argument('--out',required=True)
    args=parser.parse_args(argv)
    if args.command=='index':
        module=importlib.import_module('egrs.task_control.index')
        result=module.build_index(args.generated_export,args.retention_index,args.out)
        print(json.dumps(result,ensure_ascii=False))
        return result
    if args.command=='train':
        return importlib.import_module('egrs.task_control.training').run(args)
    if args.mode=='report' and not args.run_dir:
        parser.error('eval --mode report requires --run-dir')
    if args.mode!='report' and not args.config:
        parser.error('eval --mode plan/run requires --config')
    module=importlib.import_module('egrs.task_control.evaluation')
    if args.mode=='run':
        return module.run(args.config,args.out,arm=args.arm)
    if args.mode=='report':
        return module.report_run(args.run_dir,args.out,arm=args.arm)
    result=module.build_plan(args.config,arm=args.arm)
    with Path(args.out).open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
    return result


if __name__=='__main__':
    main()
