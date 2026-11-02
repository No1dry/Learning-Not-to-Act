"""User-started export: python -m egrs.augmentation.export --help."""
import argparse
import json
from pathlib import Path

from .data import export_dataset, read_json


def main(argv=None):
    parser=argparse.ArgumentParser(description='Index explicit expert HDF sources; no simulator/model/recovery.')
    parser.add_argument('--manifest',required=True,help='Explicit sources + field/time/normalization mapping JSON')
    parser.add_argument('--base-inventory',required=True,help='Original pinned 200-source inventory JSON')
    parser.add_argument('--evidence',help='Optional trusted offline local evidence JSON array')
    parser.add_argument('--evidence-provider',help='Optional hash-pinned local-window producer config JSON')
    parser.add_argument('--output',required=True,help='New output directory (must not already exist)')
    args=parser.parse_args(argv)
    manifest=read_json(args.manifest)
    root=Path(manifest['data_root'])
    if not root.is_absolute():manifest['data_root']=str((Path(args.manifest).resolve().parent/root).resolve())
    report=export_dataset(manifest,read_json(args.base_inventory),args.output,
                          evidence=read_json(args.evidence) if args.evidence else None,
                          evidence_provider=read_json(args.evidence_provider) if args.evidence_provider else None)
    print(json.dumps({'sources':report['sources'],'counts_by_view':report['counts_by_view'],
                      'augmentation_available':report['augmentation_available'],
                      'raw_fallback_sources':len(report['raw_fallback_sources'])},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
