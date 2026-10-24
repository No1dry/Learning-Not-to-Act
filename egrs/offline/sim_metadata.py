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


NAME_RULE_VERSION = 'egrs.sim.historical-bddl-names.v1'
NAME_EVIDENCE = 'collaboration/tasks/021_runtime_compatibility_examples.json'
# Explicit source-bound evidence rows. Instructions are frozen identities, not
# inferred language substitutions or permission to change native goal atoms.
_HISTORICAL_NAMES = (
    ('open_the_middle_layer_of_the_drawer.bddl',
     'open_the_middle_drawer_of_the_cabinet.bddl',
     'open_the_middle_drawer_of_the_cabinet_demo.hdf5',
     'open the middle drawer of the cabinet'),
    ('open_the_top_layer_of_the_drawer_and_put_the_bowl_inside.bddl',
     'open_the_top_drawer_and_put_the_bowl_inside.bddl',
     'open_the_top_drawer_and_put_the_bowl_inside_demo.hdf5',
     'open the top drawer and put the bowl inside'),
    ('put_the_bowl_on_the_top_of_the_drawer.bddl',
     'put_the_bowl_on_top_of_the_cabinet.bddl',
     'put_the_bowl_on_top_of_the_cabinet_demo.hdf5',
     'put the bowl on top of the cabinet'),
    ('put_the_cream_cheese_on_the_bowl.bddl',
     'put_the_cream_cheese_in_the_bowl.bddl',
     'put_the_cream_cheese_in_the_bowl_demo.hdf5',
     'put the cream cheese in the bowl'),
    ('put_the_wine_bottle_on_the_top_of_the_drawer.bddl',
     'put_the_wine_bottle_on_top_of_the_cabinet.bddl',
     'put_the_wine_bottle_on_top_of_the_cabinet_demo.hdf5',
     'put the wine bottle on top of the cabinet'),
)


def validate_dataset_identity(identity):
    if (not isinstance(identity,dict) or set(identity)!={'dataset','revision'}
            or any(not isinstance(v,str) or not v.strip() for v in identity.values())):
        raise ValueError('dataset_identity requires nonempty dataset and revision strings')
    return deepcopy(identity)


def _historical_binding(fields, *, suite, source, dataset_identity, registry):
    rows=[row for row in _HISTORICAL_NAMES
          if any(field.get('basename')==row[0] for field in fields.values())]
    if not rows:
        return None
    if len(rows)!=1 or suite!='libero_goal':
        raise ValueError('historical BDDL name task/suite conflict')
    old,canonical,filename,instruction=rows[0]
    from .inventory import DATASET, REVISION, catalog
    from .sim_contract import mapping_for
    if validate_dataset_identity(dataset_identity)!={'dataset':DATASET,'revision':REVISION}:
        raise ValueError('historical BDDL dataset/revision conflict')
    relative=suite+'/'+filename
    if (not isinstance(source,dict) or source.get('file')!=relative
            or source.get('task_group')!=relative
            or not re.fullmatch(r'demo_[0-9]',str(source.get('episode','')))
            or source.get('source_id')!=relative+'#'+source['episode']
            or source.get('instruction')!=instruction):
        raise ValueError('historical BDDL source task/episode/instruction conflict')
    if not any(item=={'suite':suite,'file':filename} for item in catalog()['files']):
        raise ValueError('historical BDDL source absent from frozen catalog')
    if not isinstance(registry,dict) or registry.get('instruction')!=instruction:
        raise ValueError('historical BDDL registry instruction conflict')
    mapping_for(registry)
    if fields['data.attrs.bddl_file_name'].get('basename')!=canonical:
        raise ValueError('historical BDDL requires explicit canonical data.attrs.bddl_file_name')
    for name,field in fields.items():
        if field['status']=='missing': continue
        if field['basename'] not in {old,canonical}:
            raise ValueError('historical BDDL identifier conflict')
        if field['basename']==old:
            if name=='data.attrs.bddl_file_name':
                raise ValueError('historical BDDL data attribute must be canonical')
            field.update(status='normalized',normalized_basename=canonical,
                         normalization_rule=NAME_RULE_VERSION)
    return {'version':NAME_RULE_VERSION,'evidence_source':NAME_EVIDENCE,
            'dataset_identity':deepcopy(dataset_identity),'suite':suite,'source_file':relative,
            'task_group':source['task_group'],'source_id':source['source_id'],
            'episode':source['episode'],'instruction':instruction,
            'historical_basename':old,'canonical_basename':canonical}


def _audit_identifier(value):
    if isinstance(value,bytes):
        try: return value.decode('utf-8')
        except UnicodeError: return {'bytes_hex':value.hex()}
    return deepcopy(value)


def resolve_bddl_metadata(env_args, data_attrs, *, suite, source=None, dataset_identity=None, registry=None):
    if suite not in SUITES: raise ValueError('fixed inventory suite required')
    kwargs=env_args.get('env_kwargs',{})
    if not isinstance(kwargs,dict): raise ValueError('saved env_kwargs object required')
    sources=[('data.attrs.bddl_file_name',data_attrs,'bddl_file_name'),
             ('env_args.bddl_file',env_args,'bddl_file'),
             ('env_args.env_kwargs.bddl_file_name',kwargs,'bddl_file_name')]
    fields={}
    try:
        for field,container,key in sources:
            fields[field]={'status':'present' if key in container else 'missing'}
            if key in container: fields[field]['value']=_audit_identifier(container[key])
        for field,container,key in sources:
            if key not in container: continue
            try: value,basename=_identifier(container[key],suite)
            except ValueError:
                fields[field]['status']='malformed'
                raise
            fields[field].update(value=value,basename=basename,status='validated')
        # Detect observed old names even when every present field has the same
        # old basename: uniqueness cannot bypass the explicit canonical field.
        compatibility=_historical_binding(fields,suite=suite,source=source,
            dataset_identity=dataset_identity,registry=registry)
        names={field.get('normalized_basename',field['basename']) for field in fields.values()
               if 'basename' in field}
        if not names: raise ValueError('no unique BDDL identifier')
        if len(names)!=1: raise ValueError('BDDL identifier conflict')
    except ValueError as error:
        if not any(field['status']=='malformed' for field in fields.values()):
            for field in fields.values():
                if field['status'] in {'validated','normalized'}: field['status']='conflicting'
        error.metadata_fields=fields
        raise
    result={'suite':suite,'basename':names.pop(),'fields':fields}
    if compatibility is not None: result['name_compatibility']=compatibility
    return result


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
