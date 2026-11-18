import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="047: original OFT pipeline, optional frozen H1@3000")
    commands = parser.add_subparsers(dest="command", required=True)
    all_parser = commands.add_parser("run-all")
    all_parser.add_argument("--config-dir", required=True)
    all_parser.add_argument("--output", required=True)
    cell_parser = commands.add_parser("run-cell")
    cell_parser.add_argument("--config", required=True)
    cell_parser.add_argument("--output", required=True)
    cell_parser.add_argument("--completed-before", type=int, default=0)
    progress_parser = commands.add_parser("progress")
    progress_parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "run-all":
        from .launch import run_all
        run_all(args.config_dir, args.output)
    elif args.command == "run-cell":
        from .runner import run_cell
        run_cell(args.config, args.output, completed_before=args.completed_before)
    else:
        from .launch import progress
        print(json.dumps(progress(args.output), ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
