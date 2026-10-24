"""Pure, exact BDDL metadata reconciliation for offline source audit only."""
from copy import deepcopy
import hashlib
from pathlib import Path
import re

SUITES = frozenset(('libero_spatial','libero_object','libero_goal','libero_90','libero_10'))


def _identifier(value, suite):
    if isinstance(value,bytes):
        try: value=value.decode('utf-8')
        except UnicodeError as error: raise ValueError('invalid UTF-8 BDDL identifier') from error
    if not isinstance(value,str) or not value or value!=value.strip():
        raise ValueError('nonempty BDDL identifier required')
    normalized=value.replace(chr(92),'/')
    if (any(ord(c)<32 or c in '?*<>|"' for c in normalized) or '://' in normalized
            or normalized.endswith('/') or normalized.startswith('//')):
        raise ValueError('malformed BDDL identifier')
    parts=normalized.split('/')
    if any(p in ('.','..') for p in parts) or any(':' in p for p in parts[1:]):
        raise ValueError('malformed BDDL identifier traversal or colon')
    if ':' in parts[0] and not re.fullmatch('[A-Za-z]:',parts[0]):
        raise ValueError('malformed BDDL drive prefix')
    basename=parts[-1]
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*\.bddl',basename):
        raise ValueError('exact .bddl basename required')
    explicit=[p for p in parts[:-1] if p.lower() in SUITES]
    if any(p!=suite for p in explicit):
        raise ValueError('BDDL identifier suite conflict')
    return value,basename


def resolve_bddl_metadata(env_args, data_attrs, *, suite):
    if suite not in SUITES: raise ValueError('fixed inventory suite required')
    kwargs=env_args.get('env_kwargs',{})
    if not isinstance(kwargs,dict): raise ValueError('saved env_kwargs object required')
    sources=[('data.attrs.bddl_file_name',data_attrs,'bddl_file_name'),
             ('env_args.bddl_file',env_args,'bddl_file'),
             ('env_args.env_kwargs.bddl_file_name',kwargs,'bddl_file_name')]
    fields={}; names=set()
    try:
        for field,container,key in sources:
            fields[field]={'status':'present' if key in container else 'missing'}
        for field,container,key in sources:
            if key not in container: continue
            try: value,basename=_identifier(container[key],suite)
            except ValueError:
                fields[field]['status']='malformed'
                raise
            fields[field].update(value=value,basename=basename,status='validated')
            names.add(basename)
        if not names: raise ValueError('no unique BDDL identifier')
        if len(names)!=1:
            for value in fields.values():
                if value['status']=='validated': value['status']='conflicting'
            raise ValueError('BDDL identifier conflict')
    except ValueError as error:
        error.metadata_fields=fields
        raise
    return {'suite':suite,'basename':names.pop(),'fields':fields}


def validate_libero_source(identity):
    if (not isinstance(identity,dict) or set(identity)!={'revision','bddl_sha256'}
            or not isinstance(identity['revision'],str) or not re.fullmatch('[0-9a-f]{40}',identity['revision'])
            or not isinstance(identity['bddl_sha256'],dict)):
        raise ValueError('libero_source requires fixed revision and BDDL digest map')
    for key,digest in identity['bddl_sha256'].items():
        if not isinstance(key,str) or key.count('/')!=1:
            raise ValueError('invalid libero_source BDDL key')
        suite,basename=key.split('/')
        if suite not in SUITES or _identifier(basename,suite)[1]!=basename:
            raise ValueError('invalid libero_source BDDL key')
        if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):
            raise ValueError('invalid libero_source BDDL digest')
    return deepcopy(identity)


def resolve_installed_bddl(root, metadata, *, embedded, runtime_identity):
    root=Path(root).resolve(strict=True)
    suite=metadata['suite']; basename=metadata['basename']
    if suite not in SUITES or _identifier(basename,suite)[1]!=basename:
        raise ValueError('invalid resolved BDDL identity')
    suite_path=root/suite
    resolved_suite=suite_path.resolve(strict=True)
    # A suite alias can otherwise silently select a different task collection.
    if resolved_suite!=suite_path or not resolved_suite.is_relative_to(root):
        raise ValueError('BDDL suite symlink escape or alias')
    path=(resolved_suite/basename).resolve(strict=True)
    if path.parent!=resolved_suite or path.name!=basename or not path.is_file():
        raise ValueError('BDDL file escape, alias or non-exact basename')
    content=path.read_bytes(); digest=hashlib.sha256(content).hexdigest()
    source_digest=None if embedded is None else hashlib.sha256(embedded.encode('utf-8')).hexdigest()
    report={'format':'egrs.sim.bddl_provenance.v1',
        'mode':'metadata_resolved_installed_bddl' if embedded is None else 'source_embedded_bddl',
        'source_embedded_bddl_present':embedded is not None,
        'historical_source_byte_equality':'unverified','identity_check':'pending',
        'source_identifiers':deepcopy(metadata),'installed':{'path':str(path),'sha256':digest},
        'libero_source':None}
    if source_digest is not None: report['source_bddl_sha256']=source_digest
    try:
        if embedded is None and runtime_identity is None:
            raise ValueError('missing embedded BDDL requires libero_source identity lock')
        if runtime_identity is not None:
            identity=validate_libero_source(runtime_identity)
            expected=identity['bddl_sha256'].get(suite+'/'+basename)
            report['libero_source']={'revision':identity['revision'],
                'revision_basis':'deployment_declared_with_expected_file_digest_and_module_locks',
                'revision_verified_at_runtime':False,'expected_bddl_sha256':expected}
            if expected!=digest: raise ValueError('installed BDDL differs from expected libero_source digest')
        if source_digest is not None and source_digest!=digest:
            raise ValueError('saved and installed BDDL differ')
    except ValueError as error:
        report['identity_check']='failed'
        error.bddl_provenance=report
        raise
    report['identity_check']='passed'
    if embedded is not None: report['historical_source_byte_equality']='verified'
    return path,report
