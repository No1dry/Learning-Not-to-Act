"""Explicit user commands; importing the package never starts production."""
import argparse
import json


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--index-dir',required=True);p.add_argument('--output',required=True)
    p=sub.add_parser('train');p.add_argument('--config',required=True);p.add_argument('--output',required=True);p.add_argument('--resume')
    p=sub.add_parser('evaluate');p.add_argument('--config',required=True);p.add_argument('--output',required=True);p.add_argument('--arm',choices=('h0','h1'),required=True)
    args=parser.parse_args(argv)
    if args.command=='prepare':
        from .prepare import build_sidecar
        manifest=build_sidecar(args.index_dir,args.output)
        result={k:manifest[k] for k in ('format','identity','rows','training_ready')}
    elif args.command=='train':
        from .training import run
        result=run(args.config,args.output,resume=args.resume)
    else:
        from .evaluation import run
        report=run(args.config,args.output,arm=args.arm)
        result={'schema_version':report['schema_version'],'arm':report['arm'],
                'formal_complete':report['formal_complete'],
                'formal_SR':{k:report['conditions'][k]['formal_SR'] for k in ('10','00')}}
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
