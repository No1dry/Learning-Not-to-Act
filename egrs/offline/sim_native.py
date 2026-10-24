"""User-launched source-faithful LIBERO annotation, never imported by model code.

Native dependencies are imported only by NativeAdapter construction. All arrays,
native handles and contact certificates stay in this process. Importing this
module, source inspection and geometry helpers require no native simulator.
"""
from copy import deepcopy
import hashlib
import importlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np

from .sim_metadata import resolve_bddl_metadata, resolve_installed_bddl, validate_libero_source
from .sim_alignment import choose_alignment, frame_operation, visible_bbox, EQUIVALENCE_MAX_ATOL
from .sim_contract import entity_aliases, mapping_for, validate_native_mapping, validate_frame_facts

CAMERAS = {'agentview': ('agentview', 'agentview_rgb'),
           'wrist': ('robot0_eye_in_hand', 'eye_in_hand_rgb')}


def sha256(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode('utf-8')).hexdigest()


def text_attr(value):
    if isinstance(value, bytes):
        value = value.decode('utf-8')
    if not isinstance(value, str) or not value:
        raise ValueError('required nonempty UTF-8 text attribute missing')
    return value


def json_object(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError('duplicate metadata JSON key: '+key)
            result[key] = item
        return result
    result = json.loads(text_attr(value), object_pairs_hook=pairs,
                        parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    if not isinstance(result, dict):
        raise ValueError('metadata JSON object required')
    return result


class SourceEpisode:
    """Inspect exactly one designated episode; read numeric rows only on demand."""
    def __init__(self, root, source, *, emit=None):
        self.file = None
        self.inspection = {'source_id':source.get('source_id'),'episode':source.get('episode'),
                           'fields':{},'cameras':{}}
        stage='source.open'
        def snapshot():
            if emit is not None: emit('inspection',deepcopy(self.inspection))
        def phase(name):
            nonlocal stage
            stage='source.'+name
            self.inspection['stage']=stage
            snapshot()
        try:
            import h5py
            root = Path(root).resolve(strict=True)
            path = (root/source['file']).resolve(strict=True)
            if not path.is_relative_to(root):
                raise ValueError('source escapes inventory root')
            episode = source['episode']
            if not isinstance(episode, str) or '/' in episode or not episode.startswith('demo_'):
                raise ValueError('designated episode required')
            self.file = h5py.File(path, 'r')
            data = self.file['data']; self.ep = data[episode]
            self.inspection.update(data_keys=sorted(data.keys()),episode_keys=sorted(self.ep.keys()),
                data_attr_keys=sorted(data.attrs.keys()),episode_attr_keys=sorted(self.ep.attrs.keys()))
            for prefix,attrs,keys in [('data.attrs',data.attrs,('env_args','bddl_file_content','bddl_file_name',
                        'macros_image_convention','problem_info')),('episode.attrs',self.ep.attrs,('model_file','num_samples'))]:
                for key in keys:
                    self.inspection['fields'][prefix+'.'+key]={'status':'present' if key in attrs else 'missing'}
            snapshot()
            phase('attribute_summaries')
            self.inspection['data_attrs']=self._attrs(data.attrs)
            self.inspection['episode_attrs']=self._attrs(self.ep.attrs)
            phase('env_args')
            self.env_args = json_object(data.attrs['env_args'])
            self.inspection['env_args_sha256']=sha256(text_attr(data.attrs['env_args']))
            self.inspection['env_args_keys']=sorted(self.env_args)
            kwargs=self.env_args.get('env_kwargs')
            for key in ('bddl_file','problem_name','env_kwargs'):
                self.inspection['fields']['env_args.'+key]={'status':'present' if key in self.env_args else 'missing'}
            if isinstance(kwargs,dict):
                self.inspection['env_kwargs_keys']=sorted(kwargs)
                for key in ('bddl_file_name','robots','controller_configs','control_freq','camera_names',
                            'camera_heights','camera_widths','camera_depths','camera_segmentations'):
                    self.inspection['fields']['env_args.env_kwargs.'+key]={'status':'present' if key in kwargs else 'missing'}
            phase('model_file')
            self.xml = text_attr(self.ep.attrs['model_file'])
            self.inspection['xml_sha256']=sha256(self.xml)
            phase('bddl_metadata')
            self.bddl = text_attr(data.attrs['bddl_file_content']) if 'bddl_file_content' in data.attrs else None
            self.bddl_name = text_attr(data.attrs['bddl_file_name']) if 'bddl_file_name' in data.attrs else None
            self.bddl_attrs={} if self.bddl_name is None else {'bddl_file_name':self.bddl_name}
            self.inspection['source_embedded_bddl_present']=self.bddl is not None
            if self.bddl is not None: self.inspection['bddl_sha256']=sha256(self.bddl)
            phase('image_convention')
            self.orientation = text_attr(data.attrs['macros_image_convention'])
            if self.orientation not in ('opengl','opencv') or self.orientation != source['orientation']:
                raise ValueError('unknown or changed source image convention')
            self.inspection['image_convention']=self.orientation
            self.inspection['image_convention_origin']='data.attrs.macros_image_convention'
            phase('instruction')
            problem = json_object(data.attrs['problem_info']) if 'problem_info' in data.attrs else {}
            if 'language_instruction' in problem:
                if text_attr(problem['language_instruction']) != source['instruction']:
                    raise ValueError('source instruction metadata disagrees with inventory')
                provenance={'origin':'data.attrs.problem_info.language_instruction'}
            else:
                mapping=source.get('instruction_mapping')
                if (source.get('instruction_origin')!='explicit_human_mapping' or not isinstance(mapping,dict)
                        or mapping.get('instruction')!=source['instruction'] or not mapping.get('reviewer') or not mapping.get('basis')):
                    raise ValueError('missing source instruction: explicit frozen instruction mapping required')
                provenance={'origin':'explicit_human_mapping','mapping':deepcopy(mapping)}
            self.inspection['instruction_provenance']=provenance
            phase('num_samples')
            self.T = source['T']
            if type(self.T) is not int or self.T < 1:
                raise ValueError('invalid source T')
            if 'num_samples' in self.ep.attrs:
                count=self.ep.attrs['num_samples']
                if not isinstance(count,(int,np.integer)) or isinstance(count,(bool,np.bool_)) or int(count)!=self.T:
                    raise ValueError('num_samples differs from original RGB length')
            for name in ('states','actions'):
                phase(name)
                array = self.ep[name]
                if len(array.shape)!=2 or array.shape[0]!=self.T or not array.shape[1] or array.dtype.kind not in 'fiu':
                    raise ValueError(name+' must be numeric [T,D] matching original cameras')
                self.inspection[name] = {'shape':list(array.shape),'dtype':str(array.dtype)}
            for camera, (_, key) in CAMERAS.items():
                phase('camera.'+camera)
                array = self.ep['obs'][key]
                if len(array.shape)!=4 or array.shape[0]!=self.T or array.shape[-1]!=3 or array.dtype!=np.uint8 or min(array.shape)<=0:
                    raise ValueError('original camera shape/dtype mismatch')
                self.inspection['cameras'][camera] = {'shape':list(array.shape),'dtype':str(array.dtype)}
            phase('complete')
        except Exception as error:
            self.inspection['failure']={'stage':stage,'error_type':type(error).__name__}
            snapshot()
            self.close()
            wrapped=ValueError('source inspection gap at '+stage+': '+str(error))
            wrapped.inspection=deepcopy(self.inspection)
            wrapped.failure_stage=stage
            raise wrapped from error

    @staticmethod
    def _attrs(attrs):
        # Hash even optional array attributes; never return init_state or XML.
        result = {}
        for key in attrs:
            value = attrs[key]
            if isinstance(value, (str, bytes)):
                raw = value.encode('utf-8') if isinstance(value,str) else value
                result[key] = {'type':'text','bytes':len(raw),'sha256':sha256(raw)}
            else:
                array = np.asarray(value)
                result[key] = {'type':str(array.dtype),'shape':list(array.shape),
                               'sha256':sha256(array.tobytes())}
        return result

    def state(self, index):
        return self._row('states', index)

    def action(self, index):
        return self._row('actions', index)

    def _row(self, name, index):
        if type(index) is not int or not 0<=index<self.T:
            raise ValueError('row outside designated episode')
        row = np.asarray(self.ep[name][index])
        if not np.isfinite(row).all():
            raise ValueError('nonfinite '+name+' row')
        return row

    def rgb(self, frame, camera):
        if type(frame) is not int or not 0<=frame<self.T:
            raise ValueError('RGB frame outside designated episode')
        return np.asarray(self.ep['obs'][CAMERAS[camera][1]][frame])

    def close(self):
        if self.file is not None:
            self.file.close(); self.file = None

    def __enter__(self): return self
    def __exit__(self, *args): self.close()


def geom_mask(raw, ids, *, geom_type):
    raw = np.asarray(raw)
    if raw.ndim!=3 or raw.shape[-1]!=2 or raw.dtype.kind not in 'iu':
        raise ValueError('raw segmentation must contain native object type/id channels')
    return (raw[:,:,0]==geom_type) & np.isin(raw[:,:,1], ids)


def descendant_geoms(model, roots, allowed):
    roots = set(int(x) for x in roots)
    parents = np.asarray(model.body_parentid)
    def descendant(body):
        seen = set()
        while body not in seen:
            if body in roots: return True
            seen.add(body)
            if body == 0: return False
            body = int(parents[body])
        raise ValueError('cyclic native body topology')
    return [int(g) for g in allowed if descendant(int(model.geom_bodyid[g]))]


def image_residual(stored, rendered, foreground, *, min_pixels):
    """Max of whole-image and visible foreground mean absolute RGB /255."""
    stored, rendered, foreground = np.asarray(stored),np.asarray(rendered),np.asarray(foreground)
    if stored.shape!=rendered.shape or stored.ndim!=3 or stored.shape[-1]!=3 or stored.dtype!=np.uint8 or rendered.dtype!=np.uint8:
        raise ValueError('render and original RGB dimensions/dtype differ')
    if foreground.shape!=stored.shape[:2] or foreground.dtype!=bool or foreground.sum()<min_pixels:
        raise ValueError('insufficient visible foreground for correspondence')
    diff = np.abs(stored.astype(float)-rendered.astype(float))/255.
    return float(max(diff.mean(), diff[foreground].mean()))


def evaluate_atoms(inner, goals):
    truths, audit = {}, []
    for goal in goals:
        record = {'goal_ref':goal['goal_ref'],'atom':goal['atom'],
                  'annotation_only':goal['annotation_only'],'basis':goal['basis']}
        try:
            result = inner._eval_predicate(goal['atom'])
            if not isinstance(result,(bool,np.bool_)):
                raise ValueError('native atom did not return boolean')
            truths[goal['goal_ref']] = bool(result)
        except (KeyError,ValueError,TypeError,AttributeError,RuntimeError) as error:
            truths[goal['goal_ref']] = None
            record['gap'] = str(error)[:1000]
        record['truth'] = truths[goal['goal_ref']]
        audit.append(record)
    return truths, audit


def make_evidence(goal, masks, camera, orientation, grasp, *, min_pixels):
    visible = {name:mask for name,mask in masks.items() if np.count_nonzero(mask)>=min_pixels}
    groups = [(goal['identity_components'], ['entity','role']),
              (goal['relation_components'], ['relation'])]
    if grasp in ('dual_pad','released'):
        groups.append((goal['interaction_components'], ['interaction']+(['release'] if goal['kind']=='transport' else [])))
    evidence = []
    for components, supports in groups:
        if not set(components)<=set(visible): continue
        union = np.logical_or.reduce([visible[c] for c in components])
        box = visible_bbox(union, orientation=orientation)
        if box is not None:
            evidence.append({'camera':camera,'bbox':box,'components':list(components),'supports':supports})
    return evidence


def surface_support(world, visible, *, camera_position, center, rotation, half_size,
                    vertical_margin, inset=.002, normal_z_min=.7, max_neighbor_m=.03):
    """Visible upward support pixels inside native destination bounds.

    World points come only from rendered depth at original pixels. Central
    differences use four visible destination neighbours, reject discontinuities,
    orient the surface normal toward the camera and require upward-facing support.
    Thus an exterior vertical wall or a foreground occluder is not an interior.
    The bounds/thresholds gate observation only, never native predicate truth.
    """
    world=np.asarray(world,dtype=float); visible=np.asarray(visible,dtype=bool)
    center=np.asarray(center); rotation=np.asarray(rotation); half_size=np.asarray(half_size)
    if world.shape!=(*visible.shape,3) or center.shape!=(3,) or rotation.shape!=(3,3) or half_size.shape!=(3,):
        raise ValueError('invalid calibrated surface arrays')
    output=np.zeros(visible.shape,dtype=bool)
    if min(visible.shape)<3 or not np.isfinite(world).all() or not np.isfinite(half_size).all() or np.any(half_size<=0):
        return output
    middle=world[1:-1,1:-1]
    neighbours=[world[1:-1,:-2],world[1:-1,2:],world[:-2,1:-1],world[2:,1:-1]]
    valid=visible[1:-1,1:-1] & visible[1:-1,:-2] & visible[1:-1,2:] & visible[:-2,1:-1] & visible[2:,1:-1]
    for neighbour in neighbours: valid &= np.linalg.norm(neighbour-middle,axis=-1)<=max_neighbor_m
    normal=np.cross(neighbours[1]-neighbours[0],neighbours[3]-neighbours[2])
    length=np.linalg.norm(normal,axis=-1)
    normal=normal/np.maximum(length[...,None],1e-12)
    normal*=np.where(np.sum(normal*(camera_position-middle),axis=-1)>=0,1.,-1.)[...,None]
    valid &= (length>1e-12) & (normal[...,2]>=normal_z_min)
    # Native region local axes may be rotated (e.g. drawer site x is vertical).
    local=(middle-center)@rotation
    gravity_axis=int(np.argmax(np.abs(rotation[2,:])))
    if abs(rotation[2,gravity_axis])<.95: return output
    bounds=half_size.copy()
    for axis in range(3): bounds[axis]+=vertical_margin if axis==gravity_axis else -inset
    valid &= np.all(np.abs(local)<=bounds,axis=-1)
    output[1:-1,1:-1]=valid
    return output


def validate_config(config):
    allowed = {'core','bddl_root','asset_roots','versions','module_sha256','probe_count',
               'rgb_threshold','min_visible_pixels','max_reset_attempts','replay_state_atol','seed',
               'surface_inset_m','surface_normal_z_min','surface_neighbor_m','surface_vertical_margin_m',
               'table_vertical_margin_m','max_physics_substeps','libero_source'}
    if not isinstance(config,dict) or set(config)-allowed:
        raise ValueError('unknown native configuration keys')
    required = {'core','bddl_root','versions','module_sha256'}
    if not required<=set(config):
        raise ValueError('native config requires core, bddl_root, versions and module_sha256 lock')
    result = {'probe_count':3,'rgb_threshold':.03,'min_visible_pixels':16,
              'max_reset_attempts':3,'max_physics_substeps':100,'replay_state_atol':1e-6,'seed':0,
              'surface_inset_m':.002,'surface_normal_z_min':.7,'surface_neighbor_m':.03,
              'surface_vertical_margin_m':.005,'table_vertical_margin_m':.025, **deepcopy(config)}
    for key, lower, upper in [('probe_count',2,5),('min_visible_pixels',1,65536),('max_reset_attempts',1,10),
                               ('max_physics_substeps',1,1000),('seed',0,2**32-1)]:
        if type(result[key]) is not int or not lower<=result[key]<=upper:
            raise ValueError('invalid bounded '+key)
    for key in ('rgb_threshold','replay_state_atol'):
        if type(result[key]) not in (int,float) or not np.isfinite(result[key]) or not 0<=result[key]<=.1:
            raise ValueError('invalid '+key)
    for key,lower,upper in [('surface_inset_m',0,.01),('surface_normal_z_min',.5,1),
                            ('surface_neighbor_m',.001,.05),('surface_vertical_margin_m',0,.01),
                            ('table_vertical_margin_m',0,.03)]:
        if type(result[key]) not in (int,float) or not np.isfinite(result[key]) or not lower<=result[key]<=upper:
            raise ValueError('invalid visibility threshold '+key)
    if not {'numpy','h5py','robosuite','mujoco'}<=set(result['versions']):
        raise ValueError('versions must pin numpy/h5py/robosuite/mujoco')
    if not {'libero.libero.envs.bddl_base_domain','libero.libero.envs.predicates.base_predicates',
            'robosuite.environments.robot_env'}<=set(result['module_sha256']):
        raise ValueError('native source module hashes required')
    for name, digest in result['module_sha256'].items():
        if not isinstance(name,str) or not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('invalid native source hash')
    if 'libero_source' in result: validate_libero_source(result['libero_source'])
    return result


class NativeAdapter:
    """Concrete native task path. Construct ONLY in the explicitly run worker."""
    def __init__(self, request, *, emit=None):
        self.env = self.episode = None
        self.audit = []
        self._emit=emit
        self.request = request
        self.config = validate_config(request['config'])
        self.goals = mapping_for(request['registry'])
        self.aliases = entity_aliases(self.goals)
        self.images = {x['frame']:x['images'] for x in request['frames']}
        self.replay_corroborated = False
        self.image_bindings = {}
        try:
            self._stage('source_inspection')
            self.episode = SourceEpisode(request['source_root'],request['source'],emit=self._inspection_event)
            self.inspection = deepcopy(self.episode.inspection)
            if self._emit is not None: self._emit('inspection',self.inspection)
            self._stage('source_inspection','complete')
            self._stage('native_initialize')
            self._initialize()
            self._stage('native_initialize','complete')
        except Exception as error:
            report=getattr(error,'inspection',None) or getattr(self,'inspection',None)
            if report is not None:
                report=deepcopy(report)
                report.setdefault('failure',{'stage':getattr(self,'_current_stage','source_inspection'),
                                             'error_type':type(error).__name__})
                error.inspection=report
                error.failure_stage=report['failure']['stage']
                self._inspection_event('inspection',report)
            error.audit=deepcopy(self.audit)
            try: self.close()
            except Exception as close_error: error.audit.append({'close_error':str(close_error)[:1000]})
            raise

    def _inspection_event(self, kind, data):
        self.inspection=deepcopy(data)
        if self._emit is not None: self._emit(kind,deepcopy(data))

    def _stage(self, name, phase='begin'):
        self._current_stage=name
        if getattr(self,'inspection',None) is not None:
            self.inspection['stage']=name
            if self._emit is not None: self._emit('inspection',deepcopy(self.inspection))
        if self._emit is not None: self._emit('stage',{'stage':name,'phase':phase})

    def _initialize(self):
        self._stage('core_activation')
        from egrs.core import activate
        self.inspection['core'] = activate(self.config['core'])
        from benchmark.remaining_goals.libero_compat import apply_libero_compat, reset_scene
        from benchmark.remaining_goals.libero_env import restore_raw_state, fresh_observation
        from benchmark.remaining_goals.finish.environment import _release, _verify_demo_native_references, _layout
        from benchmark.remaining_goals.finish.xml_assets import resolve_xml
        self._stage('runtime_version_locks')
        versions = {name:importlib.metadata.version(name) for name in self.config['versions']}
        if versions != self.config['versions']:
            raise ValueError('annotation library version lock mismatch')
        self.inspection['versions'] = versions
        self._stage('native_imports')
        apply_libero_compat()
        # Direct task construction retains saved controller_configs and robot names.
        from libero.libero.envs import TASK_MAPPING
        from libero.libero.envs.bddl_base_domain import BDDLBaseDomain
        import mujoco
        self.geom_type = int(mujoco.mjtObj.mjOBJ_GEOM)
        self.inspection['modules'] = {}
        for name, expected in self.config['module_sha256'].items():
            module = importlib.import_module(name)
            path = Path(module.__file__).resolve()
            digest = sha256(path.read_bytes())
            if digest != expected: raise ValueError('native source lock mismatch: '+name)
            self.inspection['modules'][name] = {'path':str(path),'sha256':digest}
        self._stage('saved_native_settings')
        args = self.episode.env_args
        if not isinstance(args.get('problem_name'),str) or not isinstance(args.get('env_kwargs'),dict):
            raise ValueError('saved env_args problem_name/env_kwargs required')
        kwargs = deepcopy(args['env_kwargs'])
        parameters = set(inspect.signature(BDDLBaseDomain.__init__).parameters)-{'self','kwargs'}
        if set(kwargs)-parameters:
            raise ValueError('unsupported saved native kwargs: '+repr(sorted(set(kwargs)-parameters)))
        self._validate_kwargs(kwargs)
        self._stage('bddl_resolution')
        suite = self.request['source']['file'].replace('\\','/').split('/')[0]
        try:
            metadata=resolve_bddl_metadata(args,self.episode.bddl_attrs,suite=suite)
        except ValueError as error:
            self.inspection['bddl_identifier_fields']=getattr(error,'metadata_fields',{})
            raise
        self.inspection['bddl_identifier_fields']=metadata['fields']
        try:
            path,provenance=resolve_installed_bddl(self.config['bddl_root'],metadata,
                embedded=self.episode.bddl,runtime_identity=self.config.get('libero_source'))
        except ValueError as error:
            if hasattr(error,'bddl_provenance'):
                self.inspection['bddl_provenance']=error.bddl_provenance
            raise
        self.inspection['bddl_provenance']=provenance
        self.inspection['installed_bddl']=provenance['installed']
        overrides = {'bddl_file_name':str(path),'has_renderer':False,'has_offscreen_renderer':True,
                     'use_camera_obs':True,'camera_segmentations':None}
        self.inspection['operational_overrides'] = {key:{'saved':kwargs.get(key),'runtime':value} for key,value in overrides.items()}
        kwargs.update(overrides)
        task = TASK_MAPPING[args['problem_name'].lower()]
        self._stage('source_xml_assets')
        processed, asset_report = resolve_xml(self.episode.xml, roots=self.config.get('asset_roots'))
        self.inspection['xml_assets'] = asset_report
        if processed is None: raise ValueError('source XML asset resolution failed: '+repr(asset_report))
        self._verify_xml_topology(self.episode.xml, processed)
        if self._emit is not None: self._emit('inspection',self.inspection)
        self._stage('native_construct')
        if sha256(path.read_bytes())!=provenance['installed']['sha256']:
            raise ValueError('installed BDDL changed before native construction')
        self.env = task(**kwargs)
        self._stage('native_seed')
        self.env.seed(self.config['seed'])
        self._stage('native_reset')
        reset_scene(self.env,max_attempts=self.config['max_reset_attempts'])
        self._stage('source_xml_compile')
        self.env.reset_from_xml_string(processed)
        self._stage('native_reference_validation')
        self.inspection['native_references'] = _verify_demo_native_references(self.env)
        self.inspection['layout_sha256'] = sha256(json.dumps(_layout(self.env.sim.model),sort_keys=True))
        self.inspection['runtime_xml_sha256'] = sha256(self.env.sim.model.get_xml())
        self._verify_compiled_names(processed)
        self.restore = restore_raw_state
        self.refresh = fresh_observation
        self.release = _release
        self.inner = self.env
        self.model = self.env.sim.model
        self.inspection['physics_substeps_per_action']=self._check_substeps()
        validate_native_mapping(self.goals,self.inner.parsed_problem['goal_state'],self.inner.object_states_dict)
        self.inspection['goal_mapping'] = deepcopy(self.goals)
        self.inspection['entity_aliases'] = self.aliases
        self.inspection['visibility_rules']={key:value for key,value in self.config.items()
                                           if key.startswith(('surface_','table_','min_visible'))}
        if self.episode.inspection['states']['shape'][1] != len(self.env.sim.get_state().flatten()):
            raise ValueError('source state layout length differs from compiled source XML')
        if self.episode.inspection['actions']['shape'][1] != self.env.action_dim:
            raise ValueError('source actions differ from saved controller action dimension')

    def _validate_kwargs(self, kwargs):
        for key in ('robots','controller_configs','control_freq','camera_names','camera_heights','camera_widths','camera_depths','camera_segmentations'):
            if key not in kwargs: raise ValueError('saved native setting missing: '+key)
        if not isinstance(kwargs['controller_configs'],dict) or not isinstance(kwargs['controller_configs'].get('type'),str):
            raise ValueError('explicit saved controller config required')
        if kwargs['robots'] not in (['Panda'],'Panda'):
            raise ValueError('restore/release helpers require the saved Panda constructor')
        if type(kwargs['control_freq']) not in (int,float) or kwargs['control_freq']<=0:
            raise ValueError('invalid saved control frequency')
        names=kwargs['camera_names']
        if not isinstance(names,list) or len(names)!=2 or set(names)!={'agentview','robot0_eye_in_hand'}:
            raise ValueError('saved camera names must be exactly the two original cameras')
        if kwargs['camera_segmentations'] is not None:
            raise ValueError('saved segmentation configuration may have mutated site sizes')
        for field,axis in [('camera_heights',1),('camera_widths',2)]:
            values=kwargs[field] if isinstance(kwargs[field],list) else [kwargs[field]]*2
            if len(values)!=2: raise ValueError('invalid saved camera dimensions')
            aliases={native:camera for camera,(native,_) in CAMERAS.items()}
            for value,name in zip(values,names):
                camera=aliases[name]
                if type(value) is not int or value!=self.inspection['cameras'][camera]['shape'][axis]:
                    raise ValueError('saved camera dimensions disagree with source RGB')

    @staticmethod
    def _verify_xml_topology(original, runtime):
        def stripped(text):
            root=ET.fromstring(text)
            for element in root.findall('./asset/*'):
                element.attrib.pop('file',None)
            return ET.tostring(root)
        if stripped(original)!=stripped(runtime):
            raise ValueError('XML resolver changed scene topology')

    def _verify_compiled_names(self, xml):
        root=ET.fromstring(xml); model=self.env.sim.model
        for tag in ('body','joint','geom','site','camera'):
            names=[item.attrib['name'] for item in root.findall('.//worldbody//'+tag) if item.get('name')]
            if len(set(names))!=len(names): raise ValueError('duplicate source XML '+tag+' names')
            for name in names:
                if getattr(model,tag+'_name2id')(name)<0:
                    raise ValueError('source XML name missing from compiled scene: '+name)

    def _original(self, frame, camera):
        from PIL import Image
        descriptor=self.images[frame][camera]
        with Image.open(descriptor['path']) as image:
            if image.mode!='RGB' or image.size!=(descriptor['width'],descriptor['height']):
                raise ValueError('frozen image dimensions/mode changed')
            rgb=np.array(image)
        if not np.array_equal(rgb,self.episode.rgb(frame,camera)):
            raise ValueError('frozen original image differs from designated source frame')
        self.image_bindings[f'{frame}:{camera}']={'frame':frame,'camera':camera,
            'path':descriptor['path'],'width':descriptor['width'],'height':descriptor['height'],
            'file_sha256':sha256(Path(descriptor['path']).read_bytes()),
            'pixel_sha256':sha256(rgb.tobytes()),'hdf_pixel_equality':True}
        return rgb

    def _restore(self, index, action=None):
        self.restore(self.env,self.episode.state(index))
        if action is not None:
            # Reset episode bookkeeping only; physical/controller state comes from helper.
            self.env.done=False; self.env.timestep=0
            self._check_substeps()
            self.env.step(self.episode.action(action))
            self.refresh(self.env)

    def _check_substeps(self):
        control=float(self.env.control_timestep); model=float(self.env.model_timestep)
        if not np.isfinite(control) or not np.isfinite(model) or min(control,model)<=0:
            raise ValueError('invalid runtime physics substep durations')
        count=int(control/model)
        if not 1<=count<=self.config['max_physics_substeps']:
            raise ValueError('runtime physics substep count exceeds configured budget')
        return count

    def _render(self, camera):
        native,_=CAMERAS[camera]
        shape=self.inspection['cameras'][camera]['shape']
        kwargs={'camera_name':native,'height':shape[1],'width':shape[2]}
        rgb=np.asarray(self.env.sim.render(**kwargs,depth=False,segmentation=False))
        raw=np.asarray(self.env.sim.render(**kwargs,depth=False,segmentation=True))
        return rgb,raw

    def _ids(self, obj, visual=True):
        names=getattr(obj,'visual_geoms' if visual else 'contact_geoms',[])
        ids=[int(self.model.geom_name2id(name)) for name in names]
        if any(x<0 for x in ids): raise ValueError('unresolved native geom')
        return ids

    def _foreground(self, raw):
        ids=[]
        for obj in self.inner.objects_dict.values(): ids.extend(self._ids(obj))
        for goal in self.goals:
            if goal['kind']=='mechanism':
                masks,_=self._parts(goal,raw)
                # Include the actual active fixture, not the static background.
                part=masks.get('active_part')
                if part is not None: ids.extend(np.unique(raw[:,:,1][part]).tolist())
        for robot in self.env.robots: ids.extend(self._ids(robot.gripper))
        return geom_mask(raw,ids,geom_type=self.geom_type)

    def _compare(self, frame, renders, orientation):
        residuals=[]
        for camera,(rgb,raw) in renders.items():
            support=self._foreground(raw)
            if orientation=='flip_vertical': rgb=rgb[::-1]; support=support[::-1]
            residuals.append(image_residual(self._original(frame,camera),rgb,support,
                                           min_pixels=self.config['min_visible_pixels']))
        return residuals

    def align(self):
        # Deterministic subset of existing requested frames only, common to every rule.
        eligible=sorted(f for f in self.images if f+1<self.episode.T)
        count=min(len(eligible),self.config['probe_count'])
        probes=[eligible[i] for i in np.linspace(0,len(eligible)-1,count,dtype=int)] if count else []
        comparisons={o:[] for o in ('identity','flip_vertical')}
        failures=[]; corroboration=[]
        samples=[{'frame':f,'camera':c} for f in probes for c in CAMERAS]
        for rule in ('same_state','next_state','replay_action'):
            scores={o:[] for o in comparisons}
            failed=False
            for frame in probes:
                try:
                    self._restore(frame+(rule=='next_state'),frame if rule=='replay_action' else None)
                    if rule=='replay_action':
                        actual=np.asarray(self.env.sim.get_state().flatten())
                        expected=self.episode.state(frame+1)
                        residual=float(np.max(np.abs(actual-expected)))
                        corroboration.append({'frame':frame,'max_state_abs_residual':residual,
                                              'passed':residual<=self.config['replay_state_atol'],
                                              'next_state_sha256':sha256(expected.tobytes()),
                                              'replay_state_sha256':sha256(actual.tobytes())})
                    renders={camera:self._render(camera) for camera in CAMERAS}
                    for orientation in scores:
                        scores[orientation].extend(self._compare(frame,renders,orientation))
                except Exception as error:
                    failures.append({'rule':rule,'frame':frame,'reason':str(error)[:1000]})
                    failed=True; break
            if probes and not failed:
                for orientation in scores:
                    comparisons[orientation].append({'rule':rule,'residuals':scores[orientation],'samples':samples})
        basis=['runtime env_args/XML/BDDL inspected; exact frozen RGB equals source frame',
               'fixed existing two-camera probes; raw render orientation measured by RGB; no success criterion']
        decisions={o:choose_alignment(v,basis=basis,orientation=o,threshold=self.config['rgb_threshold'])
                   for o,v in comparisons.items()}
        # A candidate exception leaves that candidate unresolved, not disproven.
        passing=[(o,c['rule']) for o,cs in comparisons.items() for c in cs
                 if max(c['residuals'])<=self.config['rgb_threshold']]
        if len(passing)==1 and not failures:
            decision=decisions[passing[0][0]]
        elif (not failures and len(passing)==2 and len({o for o,_ in passing})==1
              and {rule for _,rule in passing}=={'next_state','replay_action'}):
            orientation=passing[0][0]
            try:
                equivalence=self._prove_equivalence(eligible,probes,comparisons[orientation],corroboration,orientation)
                decision=choose_alignment(comparisons[orientation],basis=basis,orientation=orientation,
                    threshold=self.config['rgb_threshold'],equivalence=equivalence)
                decisions[orientation]=decision
            except Exception as error:
                failures.append({'rule':'next_state~replay_action','frame':None,'reason':str(error)[:1000]})
                decision=deepcopy(decisions[orientation])
                decision.update(accepted=False,rule=None,reason='physical_equivalence_check_failed')
        else:
            decision=decisions['identity']; decision.update(accepted=False,rule=None,
                reason='candidate_failure_or_ambiguous_rule_or_orientation' if failures or len(passing)!=1 else 'no_alignment')
        self.replay_corroborated=len(corroboration)>=2 and all(x['passed'] for x in corroboration)
        self.audit.append({'type':'alignment_measurement','probes':probes,'orientation_candidates':decisions,
            'failures':failures,'metric':'max(whole RGB MAE, visible object/hand foreground RGB MAE)/255',
            'threshold':self.config['rgb_threshold'],'min_foreground_pixels':self.config['min_visible_pixels'],
            'producer_evidence':{'env_args_sha256':self.inspection['env_args_sha256'],
                                 'image_convention':self.episode.orientation,
                                 'producer_script_identity':'not supplied by source; no assumed shift'},
            'replay_corroboration':corroboration,'replay_state_atol':self.config['replay_state_atol'],
            'final_replay_certified':self.replay_corroborated,
            'image_bindings':list(self.image_bindings.values())})
        return decision

    def _prove_equivalence(self, eligible, probes, comparisons, corroboration, orientation):
        """Authorize only requested known-next frames checked physically and visually.

        Probe measurements are reused verbatim. Every remaining requested frame
        receives both direct-next and replay RGB checks plus a flattened-state
        comparison. No extrapolation to an untested frame or final boundary.
        """
        by_rule={item['rule']:item for item in comparisons}
        states={item['frame']:item for item in corroboration}
        checks=[]
        for frame in eligible:
            if frame in probes:
                index=probes.index(frame)*len(CAMERAS)
                rgb={rule:dict(zip(CAMERAS,by_rule[rule]['residuals'][index:index+len(CAMERAS)]))
                     for rule in ('next_state','replay_action')}
                state=states[frame]
            else:
                self._restore(frame+1)
                next_rgb=self._compare(frame,{c:self._render(c) for c in CAMERAS},orientation)
                expected=self.episode.state(frame+1)
                self._restore(frame,frame)
                actual=np.asarray(self.env.sim.get_state().flatten())
                replay_rgb=self._compare(frame,{c:self._render(c) for c in CAMERAS},orientation)
                rgb={'next_state':dict(zip(CAMERAS,next_rgb)),'replay_action':dict(zip(CAMERAS,replay_rgb))}
                state={'max_state_abs_residual':float(np.max(np.abs(actual-expected))),
                       'next_state_sha256':sha256(expected.tobytes()),'replay_state_sha256':sha256(actual.tobytes())}
            checks.append({'frame':frame,'next_state_index':frame+1,'replay_state_index':frame,'action_index':frame,
                'state_max_abs_residual':state['max_state_abs_residual'],
                'next_state_sha256':state['next_state_sha256'],'replay_state_sha256':state['replay_state_sha256'],
                'rgb_residuals':rgb})
        return {'format':'egrs.sim.equivalence.v1','rules':['next_state','replay_action'],
                'representative':'next_state','state_atol':min(self.config['replay_state_atol'],EQUIVALENCE_MAX_ATOL),
                'checks':checks}

    def _depth_world(self, camera):
        from robosuite.utils.camera_utils import get_real_depth_map, get_camera_intrinsic_matrix, get_camera_extrinsic_matrix
        native,_=CAMERAS[camera]; shape=self.inspection['cameras'][camera]['shape']
        _,depth=self.env.sim.render(camera_name=native,height=shape[1],width=shape[2],depth=True,segmentation=False)
        depth=np.asarray(depth)
        if depth.shape!=tuple(shape[1:3]) or not np.isfinite(depth).all() or np.any((depth<0)|(depth>1)):
            raise ValueError('invalid raw annotation depth')
        # Native raw render is bottom-up; camera_utils matrices are top-down.
        # This conversion concerns annotation depth only, never stored RGB.
        metric=get_real_depth_map(self.env.sim,depth[::-1])
        K=get_camera_intrinsic_matrix(self.env.sim,native,shape[1],shape[2])
        pose=get_camera_extrinsic_matrix(self.env.sim,native)
        rows,cols=np.indices(metric.shape)
        rays=np.stack((cols,rows,np.ones_like(cols)),axis=-1)@np.linalg.inv(K).T
        world=(rays*metric[...,None])@pose[:3,:3].T+pose[:3,3]
        return world[::-1],pose[:3,3]

    def _destination(self, goal, raw, world, camera_position):
        name=goal['atom'][2]; objects={**self.inner.objects_dict,**self.inner.fixtures_dict}
        model=self.model; data=self.env.sim.data
        site=self.inner.object_sites_dict.get(name)
        if site is not None:
            sid=int(model.site_name2id(name))
            if int(model.site_type[sid])!=6: raise ValueError('destination region is not a native box site')
            center=np.asarray(data.site_xpos[sid]); rotation=np.asarray(data.site_xmat[sid]).reshape(3,3)
            size=np.asarray(model.site_size[sid]); parent=site.parent_name
            if parent is None and name=='main_table_stove_front_region':
                owner=int(model.site_bodyid[sid])
                if owner<=0: raise ValueError('table site owner unavailable')
                ids=descendant_geoms(model,[owner],range(model.ngeom))
                margin=self.config['table_vertical_margin_m']
            else:
                ids=self._ids(objects[parent]); margin=self.config['surface_vertical_margin_m']
        elif name in ('plate_1','akita_black_bowl_1'):
            obj=objects[name]; bid=int(model.body_name2id(obj.root_body))
            rotation=np.asarray(data.body_xmat[bid]).reshape(3,3)
            if rotation[2,2]<.95: raise ValueError('destination plate/bowl is not upright')
            bottom=np.asarray(obj.bottom_offset); top=np.asarray(obj.top_offset)
            radius=float(obj.horizontal_radius)
            if radius<=0 or top[2]<=bottom[2]: raise ValueError('destination object bounds unavailable')
            center=np.asarray(data.body_xpos[bid])+rotation@np.array([0.,0.,(top[2]+bottom[2])/2])
            size=np.array([radius,radius,(top[2]-bottom[2])/2])
            ids=self._ids(obj); margin=0.
        else:
            raise ValueError('destination surface geometry unsupported')
        visible=geom_mask(raw,ids,geom_type=self.geom_type)
        return surface_support(world,visible,camera_position=camera_position,center=center,rotation=rotation,
            half_size=size,vertical_margin=margin,inset=self.config['surface_inset_m'],
            normal_z_min=self.config['surface_normal_z_min'],max_neighbor_m=self.config['surface_neighbor_m'])

    def _parts(self, goal, raw, depth=None):
        masks={}; gaps=[]; name=goal['atom'][1]
        objects={**self.inner.objects_dict,**self.inner.fixtures_dict}
        if goal['kind']=='transport':
            masks['target']=geom_mask(raw,self._ids(objects[name]),geom_type=self.geom_type)
            try:
                if depth is None: raise ValueError('calibrated destination depth unavailable')
                masks['destination']=self._destination(goal,raw,*depth)
                if masks['destination'].sum()<self.config['min_visible_pixels']:
                    gaps.append('insufficient_visible_destination_upward_support_inside_native_bounds')
                if 'reference' in goal['relation_components']:
                    masks['reference']=geom_mask(raw,self._ids(objects['flat_stove_1']),geom_type=self.geom_type)
            except (ValueError,KeyError,AttributeError,TypeError,IndexError) as error:
                gaps.append('destination_surface_gap:'+str(error))
        else:
            site=self.inner.object_sites_dict.get(name)
            obj=objects[site.parent_name] if site is not None else objects[name]
            joints=list(site.joints if site is not None else obj.joints)
            # Only articulated hinge/slide joints; a free root is never an active mechanism.
            jids=[int(self.model.joint_name2id(joint)) for joint in joints]
            if any(jid<0 for jid in jids): raise ValueError('active joint unresolved')
            jids=[jid for jid in jids if int(self.model.jnt_type[jid]) in (2,3)]
            roots=[int(self.model.jnt_bodyid[jid]) for jid in jids]
            ids=self._ids(obj)
            active=descendant_geoms(self.model,roots,ids) if roots else []
            active=self._mechanism_visual_ids(active)
            masks['active_part']=geom_mask(raw,active,geom_type=self.geom_type)
            all_jids=[int(self.model.joint_name2id(joint)) for joint in obj.joints]
            if any(jid<0 for jid in all_jids): raise ValueError('object joint unresolved')
            moving_roots=[int(self.model.jnt_bodyid[jid]) for jid in all_jids if int(self.model.jnt_type[jid]) in (2,3)]
            moving=descendant_geoms(self.model,moving_roots,ids)
            masks['reference']=geom_mask(raw,sorted(set(ids)-set(moving)),geom_type=self.geom_type)
            if not active: gaps.append('active_joint_visual_geoms_unavailable')
        gripper=self.env.robots[0].gripper
        masks['hand']=geom_mask(raw,self._ids(gripper),geom_type=self.geom_type)
        return masks,gaps

    def _mechanism_visual_ids(self, ids):
        # Source meshes explicitly distinguish drawer panel and handle. A handle
        # alone is insufficient even when close-up pixels exceed the threshold.
        result=[]
        for gid in ids:
            if int(self.model.geom_type[gid])==7:
                mesh=self.model.mesh_id2name(int(self.model.geom_dataid[gid])) or ''
                if '_handle_' in mesh: continue
            result.append(gid)
        return result

    def frame(self, frame, alignment):
        operation=frame_operation(alignment,frame,self.episode.T,replay_corroborated=self.replay_corroborated)
        frame_alignment=deepcopy(alignment)
        audit={'frame':frame,'operation':operation,'gaps':[],'goals':[]}
        truths={g['goal_ref']:None for g in self.goals}; renders={}; depths={}
        if operation is not None:
            self._restore(operation['state_index'],operation['action_index'])
            # Evaluate independently, refresh visual state, then use same render for match/evidence.
            truths,atom_audit=evaluate_atoms(self.inner,self.goals)
            self.refresh(self.env)
            audit['atoms']=atom_audit
            renders={camera:self._render(camera) for camera in CAMERAS}
            residuals=self._compare(frame,renders,alignment['orientation'])
            audit['frame_rgb_residuals']=dict(zip(CAMERAS,residuals))
            audit['image_bindings']=[self.image_bindings[f'{frame}:{c}'] for c in CAMERAS]
            if max(residuals)>self.config['rgb_threshold']:
                operation=None; audit['gaps'].append('per_frame_RGB_foreground_mismatch')
        else:
            audit['gaps'].append('alignment_or_boundary_gap')
        if operation is None:
            frame_alignment.update(accepted=False,rule=None,reason='frame_correspondence_or_boundary_gap')
        elif any(g['kind']=='transport' for g in self.goals):
            for camera in CAMERAS:
                try: depths[camera]=self._depth_world(camera)
                except Exception as error: audit['gaps'].append(camera+':depth_unavailable:'+str(error)[:1000])
        facts=[]
        for goal in self.goals:
            evidence=[]; grasp='unknown'; record={'goal_ref':goal['goal_ref'],'gaps':[]}
            if operation is not None:
                if goal['kind']=='transport':
                    released,certificate=self.release(self.env,self.inner,self.env.robots[0].gripper,
                                                       self.inner.objects_dict[goal['atom'][1]])
                    grasp='dual_pad' if certificate.get('dual_pad_grasp') is True else 'released' if released is True else 'unknown'
                    record['release_certificate']=certificate
                else:
                    record['gaps'].append('mechanism_grasp_not_certified; release_not_applicable')
                for camera,(_,raw) in renders.items():
                    masks,gaps=self._parts(goal,raw,depths.get(camera))
                    record['gaps'].extend(camera+':'+x for x in gaps)
                    record[camera+'_visible_pixels']={name:int(mask.sum()) for name,mask in masks.items()}
                    record[camera+'_visible_geom_ids']={name:sorted(int(x) for x in np.unique(raw[:,:,1][mask]))
                                                       for name,mask in masks.items()}
                    evidence.extend(make_evidence(goal,masks,camera,alignment['orientation'],grasp,
                                                  min_pixels=self.config['min_visible_pixels']))
            facts.append({'goal_ref':goal['goal_ref'],'kind':goal['kind'],'entity_ref':self.aliases[goal['atom'][1]],
                          'native_truth':truths[goal['goal_ref']],'grasp':grasp,'evidence':evidence})
            audit['goals'].append(record)
        return validate_frame_facts({'format':'egrs.sim.frame.v1','source_id':self.request['source']['source_id'],
                                    'frame':frame,'alignment':frame_alignment,'goals':facts}),audit

    def close(self):
        try:
            if self.env is not None: self.env.close()
        finally:
            self.env=None
            if self.episode is not None: self.episode.close()
            self.episode=None
