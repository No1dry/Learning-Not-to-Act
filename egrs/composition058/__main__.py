"""Task058 G0b scripted-placement qualification; no training, no formal score."""
import argparse
import json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    q = commands.add_parser("qualify", help="run scripted placements over probe sources")
    q.add_argument("--bank", required=True)
    q.add_argument("--run", required=True)
    q.add_argument("--per-target", type=int, default=20)
    q.add_argument("--output", required=True)
    r = commands.add_parser("record", help="record successful scripted placements as ten HDFs")
    r.add_argument("--bank", required=True)
    r.add_argument("--output-dir", required=True)
    r.add_argument("--index", required=True)
    r.add_argument("--mapping", required=True)
    r.add_argument("--benchmark-root", required=True)
    r.add_argument("--limit", type=int, default=0)
    t = commands.add_parser("train", help="train one arm on the main recipe plus scripted aux pool")
    t.add_argument("--config", required=True)
    t.add_argument("--output", required=True)
    t.add_argument("--resume")
    t.add_argument("--target-updates", type=int)
    args = parser.parse_args(argv)
    if args.command == "train":
        from .training import run as train
        result = train(args.config, args.output, resume=args.resume,
                       target_updates=args.target_updates)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "record":
        from .record import run as record
        index = record(args.bank, args.output_dir, args.index, args.mapping,
                       args.benchmark_root, limit=args.limit)
        print(json.dumps(index["counts"], indent=2))
        return 0
    from .qualify import qualify
    report = qualify(args.bank, args.run, per_target=args.per_target, output=args.output)
    print(json.dumps({k: v for k, v in report["targets"].items()}, indent=2))
    return 0 if all(v["attempts"] for v in report["targets"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
