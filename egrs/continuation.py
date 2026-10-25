"""Explicit, file-verified continuation; never resume an uncompleted trajectory."""
from pathlib import Path

FORMAT='egrs.completed-episode-continuation.v1'


def collect(parent_run,target_plan,*,visited=None):
    from .evaluate import (read,validate_plan,_validate_task,method_config,file_sha,digest,BATCH)
    parent=Path(parent_run).resolve(strict=True)
    seen=set() if visited is None else set(visited)
    if str(parent) in seen or len(seen)>=16:raise ValueError('cyclic/too-deep continuation lineage')
    seen.add(str(parent))
    plan=validate_plan(read(parent/'plan.json'));batch=read(parent/'batch.json')
    if (batch.get('format')!=BATCH or batch.get('status') not in
            {'technical_pause','completed','completed_with_missing_sources'} or
            batch.get('identity_sha256')!=plan['identity_sha256'] or batch.get('plan_sha256')!=plan['plan_sha256']):
        raise ValueError('continuation parent must be a closed, bound evaluation run')
    if plan['expected']!=target_plan['expected']:
        raise ValueError('continuation cannot change planned episodes or sources')
    if plan['ready_episodes']!=target_plan['ready_episodes']:
        raise ValueError('continuation cannot silently change the available source cohort')
    for old,new in zip(plan['tasks'],target_plan['tasks']):
        if old['task_id']!=new['task_id'] or old['status']!=new['status']:
            raise ValueError('continuation source task/availability changed')
        if old['status']=='ready':
            for key in ('episodes','source_files','source_acceptance','environment_config'):
                if old.get(key)!=new.get(key):raise ValueError('continuation source binding changed: '+key)
    for key in ('core','baseline_identity','baseline_actor_identity','selector','selector_checkpoint'):
        if plan['identity'][key]!=target_plan['identity'][key]:
            raise ValueError('continuation experiment identity differs: '+key)
    inherited={};origins={};historical=[]
    if batch.get('continuation') is not None:
        manifest=validate(batch['continuation'],plan,visited=seen)
        inherited.update(manifest[1]);origins.update({r['episode_id']:r for r in manifest[0]['completed']})
        historical.extend(manifest[0]['historical_attempts'])
    target_sources={s['task_id']:s for s in target_plan['tasks']}
    for source in plan['tasks']:
        directory=parent/'tasks'/source['task_id']
        if not directory.exists():continue
        meta,rows,issues=_validate_task(plan,source,directory)
        if issues:raise ValueError('unverified parent artifacts cannot be inherited: '+str(issues))
        expected_skip=[e['episode_id'] for e in source.get('episodes',[]) if e['episode_id'] in inherited]
        if meta.get('inherited_episode_ids',[])!=expected_skip:
            raise ValueError('parent task continuation binding differs')
        if meta['method_config']!=method_config(target_plan,target_sources[source['task_id']],meta['method_config']['output_dir']):
            raise ValueError('continuation cannot change actor, selector or memory configuration')
        references={r['episode_id']:r for r in meta['results']}
        for row in rows:
            name=row['episode_id']
            if row['status']!='completed':
                historical.append(dict(run=str(parent),episode_id=name,status=row['status'],n_steps=row['n_steps']))
                continue
            if name in inherited:raise ValueError('completed episode duplicated across lineage: '+name)
            ref=references[name]
            inherited[name]=row
            origins[name]=dict(episode_id=name,run=str(parent),
                task_id=source['task_id'],raw=ref['path'],raw_sha256=ref['sha256'],
                sidecar=ref['sidecar'],sidecar_sha256=ref['sidecar_sha256'],
                method_source_sha256=plan['identity']['method_source_sha256'])
    order={e['episode_id']:i for i,e in enumerate(target_plan['expected'])}
    manifest=dict(format=FORMAT,parent_run=str(parent),parent_plan_sha256=plan['plan_sha256'],
        parent_batch_sha256=file_sha(parent/'batch.json'),
        completed=sorted(origins.values(),key=lambda r:order[r['episode_id']]),historical_attempts=historical)
    manifest['sha256']=digest(manifest)
    return manifest,inherited


def validate(manifest,target_plan,*,visited=None):
    from .evaluate import digest
    if (manifest.get('format')!=FORMAT or manifest.get('sha256')!=digest(
            {k:v for k,v in manifest.items() if k!='sha256'})):
        raise ValueError('continuation manifest changed')
    actual,rows=collect(manifest['parent_run'],target_plan,visited=visited)
    if actual!=manifest:raise ValueError('continuation parent/verified artifacts changed')
    return actual,rows
