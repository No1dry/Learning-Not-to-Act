"""Offline catalog, annotation and local stored-image preparation."""
import argparse
import json
from pathlib import Path

from .data import build_dataset, export_annotations, import_annotations, load_records, write_json, extract_existing_images


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    catalog = commands.add_parser("catalog", help="inspect pinned candidate manifest; no download")
    import sys
    installed = Path(sys.prefix) / "share" / "egrs" / "catalog.json"
    source = Path(__file__).resolve().parents[1] / "data" / "catalog.json"
    catalog.add_argument("--catalog", default=str(installed if installed.is_file() else source))
    export = commands.add_parser("export", help="export editable external annotation package")
    export.add_argument("--manifest", required=True)
    export.add_argument("--output", required=True)
    imp = commands.add_parser("import", help="validate annotations against immutable source manifest")
    imp.add_argument("--manifest", required=True)
    imp.add_argument("--annotations", required=True)
    imp.add_argument("--output", required=True)
    build = commands.add_parser("build", help="build group-separated train/dev and gap report")
    build.add_argument("--manifest", required=True)
    build.add_argument("--attestation", required=True, help="JSON exclusion attestation")
    build.add_argument("--output", required=True)
    build.add_argument("--seed", type=int, default=0)
    extract = commands.add_parser("extract-images", help="extract existing RGB datasets only, never render")
    extract.add_argument("--hdf5", required=True)
    extract.add_argument("--episode", required=True)
    extract.add_argument("--frames", required=True, help="comma-separated stored frame indices")
    extract.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.command == "catalog":
        result = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    elif args.command == "export":
        if Path(args.output).exists():
            raise ValueError("output exists")
        result = export_annotations(load_records(args.manifest))
        write_json(args.output, result)
    elif args.command == "import":
        if Path(args.output).exists():
            raise ValueError("output exists")
        result = import_annotations(load_records(args.manifest), json.loads(Path(args.annotations).read_text(encoding="utf-8")))
        write_json(args.output, result)
    elif args.command == "build":
        result = build_dataset(load_records(args.manifest), args.output, attestation=json.loads(Path(args.attestation).read_text()), seed=args.seed)
    else:
        result = extract_existing_images(args.hdf5, args.output, episode=args.episode, frames=[int(x) for x in args.frames.split(",")])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
