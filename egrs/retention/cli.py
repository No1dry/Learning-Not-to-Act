"""User-invoked metadata index for task036; no policy or environment calls."""
import argparse
import json

from .data import build_index


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('index',))
    parser.add_argument('--config',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    print(json.dumps(build_index(args.config,args.output),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
