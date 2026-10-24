"""Individually invoked offline stages; never chains into another stage."""
import argparse
import json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('plan', help='static catalog and budgets; opens no data or model')
    diagnostic = commands.add_parser('diagnose', help='CPU-only analysis of existing raw outputs; no images or model calls')
    diagnostic.add_argument('--input', required=True, help='candidate/registry manifest JSON or candidate journal JSONL')
    diagnostic.add_argument('--output', required=True, help='new directory for derived report; originals stay unchanged')
    inventory = commands.add_parser('inventory', help='inspect local approved files; freeze all source splits')
    inventory.add_argument('--root', required=True)
    inventory.add_argument('--instruction-map')
    inventory.add_argument('--aliases')
    inventory.add_argument('--output', required=True)
    registry = commands.add_parser('registry-candidates', help='weak instruction-only registry candidates; one local teacher')
    registry.add_argument('--inventory', required=True)
    registry.add_argument('--config')
    registry.add_argument('--output', required=True)
    prepare = commands.add_parser('prepare', help='extract fixed existing RGB windows using confirmed registries')
    prepare.add_argument('--inventory', required=True)
    prepare.add_argument('--registries', required=True)
    prepare.add_argument('--output', required=True)
    candidate = commands.add_parser('candidates', help='weak visual candidates; one pinned offline teacher')
    candidate.add_argument('--windows', required=True)
    candidate.add_argument('--config')
    candidate.add_argument('--core-config', required=True, help='explicit pinned core dependency JSON; no simulator runs')
    candidate.add_argument('--output', required=True)
    for name in ('registry-review-export', 'review-export'):
        sub = commands.add_parser(name, help='export portable file-only HTML review package')
        sub.add_argument('--manifest', required=True)
        sub.add_argument('--output', required=True)
    for name in ('registry-review-import', 'review-import'):
        sub = commands.add_parser(name, help='validate explicit human confirmations against frozen originals')
        sub.add_argument('--manifest', required=True)
        sub.add_argument('--session', required=True)
        sub.add_argument('--output', required=True)
    build = commands.add_parser('build', help='build confirmed subset alongside all candidates, unreviewed and gaps')
    build.add_argument('--manifest', required=True)
    build.add_argument('--session', required=True)
    build.add_argument('--attestation', required=True)
    build.add_argument('--output', required=True)
    label_sim = commands.add_parser('label-sim', help='explicit isolated simulator annotation; never starts a teacher or training')
    for option in ('inventory', 'windows', 'registries', 'backend-config', 'output'):
        label_sim.add_argument('--' + option, required=True)
    export_sim = commands.add_parser('export-sim', help='verify immutable annotations and export existing fixed train/dev split')
    for option in ('annotations', 'windows', 'attestation', 'output'):
        export_sim.add_argument('--' + option, required=True)
    args = parser.parse_args(argv)
    from .common import read
    if args.command == 'plan':
        from .inventory import plan
        result = plan()
    elif args.command == 'diagnose':
        from .diagnostics import diagnose
        result = diagnose(args.input, args.output)
    elif args.command == 'inventory':
        from .inventory import inventory
        result = inventory(args.root, instruction_map=read(args.instruction_map) if args.instruction_map else None,
                           aliases=read(args.aliases) if args.aliases else None, output=args.output)
    elif args.command == 'prepare':
        from .windows import prepare
        result = prepare(read(args.inventory), read(args.registries), args.output)
    elif args.command == 'label-sim':
        from .sim import label_sim
        result = label_sim(read(args.inventory), read(args.windows), read(args.registries),
                           read(args.backend_config), args.output)
    elif args.command == 'export-sim':
        from .sim import export_sim
        result = export_sim(args.annotations, read(args.windows), read(args.attestation), args.output)
    elif args.command in {'registry-candidates', 'candidates'}:
        from .teacher import OfflineTeacher
        from .candidates import registry_candidates, candidates
        config = read(args.config) if args.config else None
        core_info = None
        if args.command == 'candidates':
            from egrs.core import activate
            core_info = activate(read(args.core_config))
        factory = lambda: OfflineTeacher(config)
        if args.command == 'candidates':
            result = candidates(read(args.windows), args.output, teacher_factory=factory, core_info=core_info)
        else:
            result = registry_candidates(read(args.inventory), args.output, teacher_factory=factory)
    elif args.command.endswith('-export'):
        from .review import export_review
        manifest = read(args.manifest)
        expected = 'egrs.registry-candidates.v1' if args.command.startswith('registry-') else 'egrs.candidates.v1'
        if manifest.get('format') != expected:
            raise ValueError('wrong manifest for review mode')
        export_review(manifest, args.output)
        result = {'review_html': str(__import__('pathlib').Path(args.output).resolve() / 'index.html')}
    elif args.command.endswith('-import'):
        from .review import import_review, import_registry_review
        importer = import_registry_review if args.command.startswith('registry-') else import_review
        result = importer(read(args.manifest), read(args.session), args.output)
    else:
        from .review import build_reviewed
        result = build_reviewed(read(args.manifest), read(args.session), args.output, attestation=read(args.attestation))
    # Large manifests remain on disk; stdout is a compact stage receipt.
    receipt = result if args.command == 'plan' else {key: result[key] for key in ('format', 'identity', 'counts', 'calls', 'ready', 'splits', 'review_html') if key in result}
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0
