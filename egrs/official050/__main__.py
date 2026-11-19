"""User-started single500 native evaluation, no original/H1 rerun."""
import argparse
import json
from pathlib import Path

from egrs.official047 import contracts as c


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    run = subs.add_parser("run")
    run.add_argument("--config", required=True)
    run.add_argument("--output", required=True)
    progress = subs.add_parser("progress")
    progress.add_argument("--output", required=True)
    progress.add_argument("--brief", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "run":
        config = c.load_config(args.config)
        c.require(config["schema_version"] == c.H0_LIBERO10_SCHEMA, "050 requires its explicit H0 scope")
        from egrs.official047.runner import run_cell
        from egrs.official047.launch import verify_cell
        run_cell(args.config, args.output)
        summary, _ = verify_cell(args.output, config)
        print(f"[050] ALL COMPLETE 500/500 (100%); H0@3000 SR={summary['formal_SR']['percent']:.2f}%", flush=True)
    else:
        path = Path(args.output)/"progress.json"
        value = c.read(path) if path.is_file() else {"phase":"not_started", "total_completed":0,
                "total_expected":500, "total_percent":0.0}
        c.require(value.get("total_expected") == 500, "050 output has a different scope")
        if args.brief:
            n=value.get("cell_completed",0)
            sr=value.get("live_SR_percent",value.get("formal_SR",{}).get("percent"))
            print(f"H0@3000  {n}/500 ({100*n/500:.2f}%)  SR="+
                  ("--" if sr is None else f"{sr:.2f}%")+f"  [{value['phase']}]",flush=True)
        else:
            print(json.dumps(value, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
