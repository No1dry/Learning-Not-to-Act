"""Explicit native-original044 evaluation or fail-stop two-arm launcher."""
import argparse
import importlib


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    evaluate=sub.add_parser('evaluate')
    evaluate.add_argument('--config',required=True)
    evaluate.add_argument('--output',required=True)
    both=sub.add_parser('run-both')
    for name in ('p1-config','p2-config','p1-output','p2-output','marker'):
        both.add_argument('--'+name,required=True)
    args=parser.parse_args(argv)
    if args.command=='evaluate':
        return importlib.import_module('egrs.prompt044.evaluation').run(args.config,args.output)
    values=vars(args);values.pop('command')
    return importlib.import_module('egrs.prompt044.launch').run_both(**values)


if __name__=='__main__':main()
