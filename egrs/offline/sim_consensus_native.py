"""Native implementation of the user-approved observable consensus protocol."""
from copy import deepcopy
import numpy as np

from .sim_native import NativeAdapter,evaluate_atoms,make_evidence
from .sim_diagnostic_worker import measure_rgb
from .sim_consensus import FORMAT,RULES,CAMERAS,ORIENTATIONS,camera_decision,validate_consensus_fact,unresolved_alignment


class ConsensusAdapter(NativeAdapter):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.config['rgb_threshold']!=.03 or self.config['min_visible_pixels']!=16:
            raise ValueError('consensus keeps the approved RGB/visibility gates fixed')
        self.execution_errors=[]

    def align(self):
        # Per-frame camera certificates replace the source-wide veto. Never
        # manufacture a unique physical correspondence or rerun old probes.
        return unresolved_alignment()

    def frame(self,frame,alignment):
        fact=dict(format=FORMAT,source_id=self.request['source']['source_id'],frame=frame,
                  T=self.episode.T,threshold=.03,min_visible_pixels=16,
                  boundary_gap=frame+1>=self.episode.T,candidates=[])
        audit=dict(frame=frame,protocol=FORMAT,candidates=[])
        if fact['boundary_gap']:return validate_consensus_fact(fact),audit
        originals={c:self._original(frame,c) for c in CAMERAS}
        for rule in RULES:
            candidate=dict(rule=rule,state_index=frame+(rule=='next_state'),
                           action_index=frame if rule=='replay_action' else None,cameras={},goals=[],error=None)
            try:
                self._restore(candidate['state_index'],candidate['action_index'])
                renders={};views={};depths={}
                for camera in CAMERAS:
                    try:
                        rgb,raw=self._render(camera);support=self._foreground(raw)
                        report=dict(error=None,orientations={})
                        for o in ORIENTATIONS:
                            image=rgb if o=='identity' else rgb[::-1]
                            mask=support if o=='identity' else support[::-1]
                            report['orientations'][o]=measure_rgb(originals[camera],image,mask,min_pixels=16)
                        candidate['cameras'][camera]=report;views[camera]=camera_decision(report)
                        renders[camera]=(rgb,raw)
                    except Exception as error:
                        candidate['cameras'][camera]=dict(error=type(error).__name__+': '+str(error)[:800],orientations={})
                        views[camera]=dict(status='unknown',orientation=None,score=None)
                        self.execution_errors.append(dict(stage='candidate_camera',frame=frame,rule=rule,camera=camera,reason=str(error)[:800]))
                matched=[c for c in CAMERAS if views[c]['status']=='pass']
                if matched:
                    truths,atoms=evaluate_atoms(self.inner,self.goals)
                    if any(g['kind']=='transport' for g in self.goals):
                        for camera in matched:
                            try:depths[camera]=self._depth_world(camera)
                            except Exception as error:audit['candidates'].append(dict(rule=rule,camera=camera,depth_error=str(error)[:500]))
                    for goal in self.goals:
                        evidence=[];grasp='unknown';record=dict(rule=rule,goal_ref=goal['goal_ref'],gaps=[])
                        if goal['kind']=='transport':
                            try:
                                released,cert=self.release(self.env,self.inner,self.env.robots[0].gripper,
                                                           self.inner.objects_dict[goal['atom'][1]])
                                grasp='dual_pad' if cert.get('dual_pad_grasp') is True else 'released' if released is True else 'unknown'
                                record['release_certificate']=cert
                            except Exception as error:record['gaps'].append('release_certificate_unavailable:'+str(error)[:500])
                        for camera in matched:
                            try:
                                masks,gaps=self._parts(goal,renders[camera][1],depths.get(camera))
                                record['gaps'].extend(camera+':'+g for g in gaps)
                                record[camera+'_visible_pixels']={name:int(mask.sum()) for name,mask in masks.items()}
                                evidence.extend(make_evidence(goal,masks,camera,views[camera]['orientation'],grasp,min_pixels=16))
                            except Exception as error:record['gaps'].append(camera+':evidence_unavailable:'+str(error)[:500])
                        candidate['goals'].append(dict(goal_ref=goal['goal_ref'],kind=goal['kind'],
                            entity_ref=self.aliases[goal['atom'][1]],native_truth=truths[goal['goal_ref']],grasp=grasp,evidence=evidence))
                        audit['candidates'].append(record)
                    audit['candidates'].append(dict(rule=rule,atoms=atoms))
                else:
                    candidate['goals']=[dict(goal_ref=g['goal_ref'],kind=g['kind'],entity_ref=self.aliases[g['atom'][1]],
                        native_truth=None,grasp='unknown',evidence=[]) for g in self.goals]
            except Exception as error:
                candidate['error']=type(error).__name__+': '+str(error)[:1000]
                self.execution_errors.append(dict(stage='candidate',frame=frame,rule=rule,reason=candidate['error']))
            fact['candidates'].append(candidate)
        audit['image_bindings']=[self.image_bindings[f'{frame}:{c}'] for c in CAMERAS]
        return validate_consensus_fact(fact),audit
