"""Explicit trained-H1@3000 046 evaluation or fail-stop two-arm launcher."""
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
        result=importlib.import_module('egrs.prompt046.evaluation').run(args.config,args.output)
        rate=result['formal_SR']
        print(f"046 {result['variant'].upper()} formal_SR={rate['percent']:.2f}% ({rate['numerator']}/90); P0 reused=68.89%",flush=True)
        return result
    values=vars(args);values.pop('command')
    return importlib.import_module('egrs.prompt046.launch').run_both(**values)


if __name__=='__main__':main()
