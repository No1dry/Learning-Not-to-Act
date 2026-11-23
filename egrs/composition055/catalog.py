"""Task055's isolated catalogue and pinned Scene2 BDDL derivatives."""

from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import overload


TASK_SUITE = "libero_remain_composition055"
CANONICAL_SCENE = "LIVING_ROOM_SCENE2"
CANONICAL_SUITE = "libero_10"
CANONICAL_TASK_ID = 0
CANONICAL_TASK_NAME = (
    "LIVING_ROOM_SCENE2_put_both_the_alphabet_soup_and_the_tomato_sauce_in_the_basket"
)
CANONICAL_BDDL_FILE = CANONICAL_TASK_NAME + ".bddl"
CANONICAL_INITIAL_STATES_FILE = CANONICAL_TASK_NAME + ".pruned_init"
CANONICAL_BDDL_SHA256 = "2e661058917f683a25bce480015197f0a2c1911bcbc2b9dd9d947199069c9618"
CANONICAL_INITIAL_STATES_SHA256 = (
    "1899fe54c51e24a41d5f9e32254730d6777f4894ab68e0e873f1fa7ae2062030"
)
SOURCE_COUNT = 50

_BASKET = "basket_1"
_REGION = "basket_1_contain_region"
_SOUP = ("alphabet_soup_1", "alphabet soup")
_TOMATO = ("tomato_sauce_1", "tomato sauce")
_CHEESE = ("cream_cheese_1", "cream cheese box")
_BUTTER = ("butter_1", "butter")
_TASKS = {
    "composition_soup_butter": (_SOUP, _BUTTER),
    "composition_tomato_cheese": (_TOMATO, _CHEESE),
    "composition_tomato_butter": (_TOMATO, _BUTTER),
}
TASK_ORDER = tuple(_TASKS)


def get_task(task_id: str) -> dict:
    """Return a detached profile with the completed and remaining goals in order."""
    if not isinstance(task_id, str) or task_id not in _TASKS:
        raise ValueError(f"unknown Task055 task {task_id!r}")

    (completed, completed_label), (remaining, remaining_label) = _TASKS[task_id]
    instruction = f"put both the {completed_label} and the {remaining_label} in the basket"
    return {
        "task_id": task_id,
        "name": CANONICAL_SCENE + "_" + instruction.replace(" ", "_"),
        "suite": TASK_SUITE,
        "scene": CANONICAL_SCENE,
        "instruction": instruction,
        "completed_object": completed,
        "remaining_object": remaining,
        "raw_goals": [["in", completed, _REGION], ["in", remaining, _REGION]],
        "goals": [
            {
                "id": "A",
                "instruction": f"put the {completed_label} in the basket",
                "predicates": [["in", completed, _REGION]],
            },
            {
                "id": "B",
                "instruction": f"put the {remaining_label} in the basket",
                "predicates": [["in", remaining, _REGION]],
            },
        ],
        "invariant_predicates": [],
    }


def expected() -> list[dict]:
    """Return the fixed task-major population of canonical source identities."""
    rows = []
    for task_id in TASK_ORDER:
        instruction = get_task(task_id)["instruction"]
        for index in range(SOURCE_COUNT):
            rows.append({
                "task_id": task_id,
                "initial_state_index": index,
                "episode_id": f"{task_id}_s{index:03d}_10",
                "source_id": f"composition055_canonical_basket_{index:03d}",
                "instruction": instruction,
                "initial_mask": [True, False],
                "split": "test",
                "horizon": 520,
                "retention_steps": 150,
            })
    return rows


def validate_population(rows: Sequence[Mapping]) -> None:
    """Require every population identity in its fixed position."""
    planned_rows = expected()
    if len(rows) != len(planned_rows):
        raise ValueError(f"Task055 population requires exactly {len(planned_rows)} rows")

    for index, (row, planned) in enumerate(zip(rows, planned_rows)):
        if not isinstance(row, Mapping):
            raise ValueError(f"Task055 population row {index} must be a mapping")
        for key, value in planned.items():
            actual = row.get(key)
            if type(actual) is not type(value) or actual != value:
                raise ValueError(f"Task055 population row {index} has wrong {key}")
        if any(type(value) is not bool for value in row["initial_mask"]):
            raise ValueError(f"Task055 population row {index} must use boolean initial_mask")


@overload
def render_bddl(canonical_text: str, task_id: str) -> str: ...


@overload
def render_bddl(canonical_text: bytes, task_id: str) -> bytes: ...


def render_bddl(canonical_text: str | bytes, task_id: str) -> str | bytes:
    """Derive the task from the byte-pinned official Scene2 basket BDDL."""
    task = get_task(task_id)
    is_bytes = isinstance(canonical_text, bytes)
    canonical_bytes = canonical_text if is_bytes else canonical_text.encode("utf-8")
    if sha256(canonical_bytes).hexdigest() != CANONICAL_BDDL_SHA256:
        raise ValueError("canonical BDDL SHA-256 does not match official Scene2 basket task 0")

    completed = task["completed_object"]
    remaining = task["remaining_object"]
    goal = " ".join(f"({predicate.capitalize()} {obj} {region})"
                    for predicate, obj, region in task["raw_goals"])
    changes = (
        (
            "(:language put both the alphabet soup and the tomato sauce in the basket)",
            f"(:language {task['instruction']})",
        ),
        (
            "(:obj_of_interest\n    alphabet_soup_1\n    tomato_sauce_1\n    basket_1\n  )",
            f"(:obj_of_interest\n    {completed}\n    {remaining}\n    {_BASKET}\n  )",
        ),
        (
            "(:goal\n    (And (In alphabet_soup_1 basket_1_contain_region) "
            "(In tomato_sauce_1 basket_1_contain_region))\n  )",
            f"(:goal\n    (And {goal})\n  )",
        ),
    )
    rendered = canonical_bytes.decode("utf-8")
    for original, replacement in changes:
        if rendered.count(original) != 1:
            raise ValueError("canonical BDDL does not have the expected editable forms")
        rendered = rendered.replace(original, replacement, 1)

    return rendered.encode("utf-8") if is_bytes else rendered
