"""User-started H0@3000 evaluation, nine Remain10 tasks times50 episodes."""
import argparse
from .evaluation import load_source_config, run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-config', required=True)
    parser.add_argument('--adapter', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    run(load_source_config(args.source_config), args.output, args.adapter)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
