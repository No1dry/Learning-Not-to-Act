"""Pure Task055 input identity, protected paths and durable JSON contracts."""
import hashlib
import json
import os
from pathlib import Path
import re
import time

SCHEMA='task055-composition-build-v1'
CORE_REVISION='d8541ef4a4bb4cc2e34c95b10227ea5fcaddaff9'


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block:=stream.read(1024*1024):digest.update(block)
    return digest.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),
        ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def read(path):
    def unique(pairs):
        value={}
        for key,item in pairs:
            if key in value:raise ValueError('Duplicate055 field: '+key)
            value[key]=item
        return value
    def invalid(value):raise ValueError('Nonfinite055 JSON value: '+value)
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,parse_constant=invalid)


def write(path,value):
    """Atomic durable checkpoint; retain an unfinished temporary on failure."""
    path=Path(path)
    temporary=path.with_name(path.name+'.tmp')
    with temporary.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())
    for attempt in range(5):
        try:
            os.replace(temporary,path)
            break
        except PermissionError as error:
            # A local Windows file-sharing lock can temporarily block rename.
            # Retry only the already-fsynced file rename, never native work.
            if getattr(error,'winerror',None) not in (5,32) or attempt==4:raise
            time.sleep(.02)


def _path(value,base):
    if not isinstance(value,str) or not value.strip():raise ValueError('055 requires nonempty paths')
    value=os.path.expandvars(os.path.expanduser(value))
    if re.search(r'\$[A-Za-z_{]|%[^%]+%|[<>]',value):raise ValueError('Unresolved055 path placeholder')
    return str((base/Path(value)).resolve())


def load_config(path):
    path=Path(path).resolve();cfg=read(path)
    fields={'schema_version','benchmark_root','canonical_bddl','canonical_initial_states',
            'environment_config','protected_roots'}
    if (not isinstance(cfg,dict) or set(cfg)!=fields or cfg['schema_version']!=SCHEMA
            or not isinstance(cfg['protected_roots'],list) or not cfg['protected_roots']):
        raise ValueError('Exact055 precompleted-only configuration required; no population/model/normal modes')
    for key in fields-{'schema_version','protected_roots'}:cfg[key]=_path(cfg[key],path.parent)
    cfg['protected_roots']=list(dict.fromkeys(_path(p,path.parent) for p in cfg['protected_roots']))
    return cfg


def input_identity(cfg):
    from . import catalog
    expected={'canonical_bddl':catalog.CANONICAL_BDDL_SHA256,
              'canonical_initial_states':catalog.CANONICAL_INITIAL_STATES_SHA256}
    for key,value in expected.items():
        if sha(cfg[key])!=value:raise ValueError('055 canonical asset SHA differs: '+key)
    environment=read(cfg['environment_config'])
    value=environment.get('environment') if isinstance(environment,dict) else None
    if (not isinstance(value,dict) or value.get('name')!='libero'
            or not isinstance(value.get('lock'),dict) or value['lock'].get('control_freq')!=20
            or not isinstance(value.get('fingerprint'),str) or not re.fullmatch('[0-9a-f]{64}',value['fingerprint'])):
        raise ValueError('055 requires original frozen environment config with explicit environment identity')
    return {**expected,'environment_config':sha(cfg['environment_config']),'environment':value}


def implementation_identity():
    root=Path(__file__).parent
    return {'core_revision':CORE_REVISION,'files':{p.name:sha(p) for p in sorted(root.glob('*.py'))},
        'core_manifest_sha256':sha(root.parent/'augmentation'/'core_files.json')}


def protect_output(cfg,output,config_path=None):
    target=Path(output).expanduser().resolve()
    if target.exists():raise FileExistsError('055 needs a fresh output; previous attempts cannot be overwritten or retried')
    roots=[Path(cfg['benchmark_root']),Path(__file__).resolve().parents[2],
        *[Path(p) for p in cfg['protected_roots']],
        *[Path(cfg[k]).parent for k in ('canonical_bddl','canonical_initial_states','environment_config')]]
    if config_path is not None:roots.append(Path(config_path).resolve())
    roots.extend(a for p in list(roots) for a in p.parents if a.name.lower() in ('data','datasets'))
    if any(target==p or p in target.parents or target in p.parents for p in roots):
        raise ValueError('055 output overlaps protected source, old bank/data/run or code')
    return target


def contained(root,relative):
    root=Path(root).resolve();path=(root/relative).resolve()
    if not path.is_relative_to(root) or path==root:raise ValueError('055 artifact escaped new output')
    return path
