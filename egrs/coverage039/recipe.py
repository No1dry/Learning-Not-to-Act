"""039 action recipe; qualification remains the accepted035 teacher V2 policy."""
from copy import deepcopy

from egrs.trajectory_augmentation.generation import DEFAULT_RECIPE
from egrs.trajectory_augmentation.native import TEACHER_V2

ALGORITHM = 'physical_release_clearance_v3'
RECIPE_VERSION = 'task039-robot-rewind-release-v1'
TASKS = ('stove', 'mug_pudding', 'two_pots')
BUDGET = {'max_normal_replays': 60, 'max_robot_starts': 180, 'max_10_attempts': 360,
          'horizon_per_attempt': 520, 'max_control_steps': 218400,
          'closure_max_steps': 40, 'initialization_failures_counted': True,
          'implicit_retries': False}
RECIPE = {**DEFAULT_RECIPE, 'version': RECIPE_VERSION, 'generator_algorithm': ALGORITHM,
          'closure_max_steps': 40, 'release_open_steps': 10,
          'release_retreat_steps': 20, 'release_hold_steps': 10, 'release_retreat_m': .10,
          'initialization_transform': {'kind': 'two_pots_initial_freejoint_swap_v1',
              'allowlist': ['two_pots'], 'objects': ['moka_pot_1', 'moka_pot_2'],
              'timing': 'before_normal_first_capture'}}


def recipe_for(config):
    recipe = {**RECIPE, **config.get('recipe', {})}
    if (recipe['seed'] != 7 or recipe['variants'] != 3 or recipe['bridge_attempts'] != 2
            or type(recipe['horizon']) is not int or not 1 <= recipe['horizon'] <= 520
            or type(recipe['bridge_stage_steps']) is not int or not 1 <= recipe['bridge_stage_steps'] <= 40
            or not 0 <= recipe['joint_perturbation_rad'] <= .05
            or recipe['lift_m'] != .1 or recipe['position_tolerance_m'] != .005
            or recipe['rotation_tolerance_deg'] != 3.
            or any(recipe[k] != RECIPE[k] for k in RECIPE if k not in DEFAULT_RECIPE)):
        raise ValueError('invalid bounded039 generation recipe')
    return deepcopy(recipe)


def generation_context(plan_identity, *, normal_attempts=0, ten_attempts=0):
    return {'format': 'task039-generation-context-v1', 'task': '039',
            'generator_algorithm': ALGORITHM, 'recipe_version': RECIPE_VERSION,
            'teacher_policy': TEACHER_V2, 'plan_identity': plan_identity,
            'initialization_transform': {'kind': 'two_pots_initial_freejoint_swap_v1',
                'allowlist': ['two_pots'], 'objects': ['moka_pot_1', 'moka_pot_2'],
                'timing': 'before_normal_first_capture'},
            'normal_attempts': normal_attempts, 'ten_attempts': ten_attempts}
