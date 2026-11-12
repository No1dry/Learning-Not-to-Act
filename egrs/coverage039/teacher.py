"""Bounded physical teacher closure; admission remains the original V2 policy.

This module imports no simulator.  It uses the original Attempt tracker so the
projected executable action, controller goal, and next observation share the
same T/T+1 recorder as source replay and continuation.
"""
from copy import deepcopy

import numpy as np

from egrs.trajectory_augmentation.generation import _guard


ALGORITHM='physical_release_clearance_v3'


def _confirmed(qualification):
    return bool(qualification.get('qualified')) or qualification.get('core_release_confirmation_streak',0)>=5


def _full_task(frame):
    facts=frame['facts'];goals=facts.get('goals',[])
    return facts.get('official_success') is True and len(goals)==2 and all(v is True for v in goals)


def _check_prefix(attempt,qualification):
    if qualification.get('core_analysis',{}).get('confirmed_events'):
        raise ValueError('confirmed_core_violation')
    if any(f.get('penetration') is True for f in attempt.frames):
        raise ValueError('teacher_release_penetration')
    if attempt.domain=='10':
        for frame in attempt.frames:_guard(frame,'teacher_release')


def finish_attempt(attempt):
    """Persist an Attempt after at most 10 open + 20 retreat + 10 hold steps.

    The fixed anchor is read once from the actual end effector pose.  Every
    command goes through ``Attempt.track`` (and therefore its ActionProjector
    and non-audit recorder).  Only ``session.qualify`` supplies the five-frame
    release certificate; open fingers or clearance never stand in for it.
    ``closure_summary`` is set before persist for callers' lineage writers.
    """
    start=len(attempt.steps)
    summary={'algorithm':ALGORITHM,'admission_policy':getattr(attempt,'teacher_policy',None),
        'start_step':start,'added_steps':0,'phase_steps':{'open':0,'retreat':0,'hold':0},
        'maximum_added_steps':40,'maximum_retreat_m':.10,'episode_horizon':520,
        'anchor':None,'stop_reason':None}
    attempt.closure_summary=summary

    def qualify():
        if not attempt.frames:return {'qualified':False,'failure_reason':'initialization_failed'}
        return attempt.session.qualify(attempt.frames,attempt.domain)

    qualification=qualify()
    try:
        if attempt.error:
            summary['stop_reason']='prior_error'
        elif not attempt.frames:
            summary['stop_reason']='initialization_failed'
        else:
            _check_prefix(attempt,qualification)
            if not _full_task(attempt.frames[-1]):
                summary['stop_reason']='native_full_task_unfinished'
            elif _confirmed(qualification):summary['stop_reason']='existing_release_confirmation'
            else:
                horizon=min(520,int(attempt.recipe.get('horizon',520)))
                if horizon<0:raise ValueError('invalid attempt horizon')
                summary['episode_horizon']=horizon
                position,rotation=attempt.session.pose()
                anchor=(np.asarray(position,dtype=float).copy(),np.asarray(rotation,dtype=float).copy())
                summary['anchor']={'position':anchor[0].tolist(),'rotation':anchor[1].tolist()}
                opened=attempt.source['mapping']['gripper']['input_open']
                if opened!=-1:raise ValueError('original gripper input_open must be -1')
                for stage,count in (('open',10),('retreat',20),('hold',10)):
                    for index in range(1,count+1):
                        if len(attempt.steps)>=horizon:
                            summary['stop_reason']='attempt_horizon_exhausted'
                            break
                        target=anchor[0].copy()
                        if stage=='retreat':target[2]+=.10*index/20
                        elif stage=='hold':target[2]+=.10
                        before=len(attempt.steps)
                        try:
                            frame=attempt.track((target,anchor[1]),opened,'teacher_release_'+stage)
                        finally:
                            summary['phase_steps'][stage]+=len(attempt.steps)-before
                        qualification=qualify()
                        _check_prefix(attempt,qualification)
                        if not _full_task(frame):
                            summary['stop_reason']='native_full_task_regressed'
                            break
                        if _confirmed(qualification):
                            summary['stop_reason']='release_confirmed'
                            break
                    if summary['stop_reason']:break
                if summary['stop_reason'] is None:summary['stop_reason']='bounded_release_unconfirmed'
    except Exception as exc:
        # Keep the complete executed prefix and the original concrete exception.
        attempt.error=attempt.error or type(exc).__name__+': '+str(exc)
        summary['stop_reason']='closure_error'

    qualification=qualify()
    if attempt.frames and not _full_task(attempt.frames[-1]):
        qualification.update(qualified=False,failure_reason=qualification.get('failure_reason') or 'native_full_task_unfinished')
    if attempt.error:qualification.update(qualified=False,failure_reason=attempt.error)
    if not attempt.actions:qualification.update(qualified=False,failure_reason=attempt.error or 'empty_trajectory')
    summary.update(added_steps=len(attempt.steps)-start,end_step=len(attempt.steps),
        final_release_confirmation_streak=qualification.get('core_release_confirmation_streak'),
        qualified=bool(qualification['qualified']),failure_reason=qualification.get('failure_reason'))
    result=attempt.persist(qualification)
    if isinstance(result,dict):result['closure_summary']=deepcopy(summary)
    return result
