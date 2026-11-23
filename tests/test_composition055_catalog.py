import hashlib

import pytest


PROFILES = [
    (
        "composition_soup_butter",
        "put both the alphabet soup and the butter in the basket",
        "alphabet_soup_1", "alphabet soup", "butter_1", "butter",
    ),
    (
        "composition_tomato_cheese",
        "put both the tomato sauce and the cream cheese box in the basket",
        "tomato_sauce_1", "tomato sauce", "cream_cheese_1", "cream cheese box",
    ),
    (
        "composition_tomato_butter",
        "put both the tomato sauce and the butter in the basket",
        "tomato_sauce_1", "tomato sauce", "butter_1", "butter",
    ),
]
REGION = "basket_1_contain_region"


@pytest.mark.parametrize("task_id,instruction,completed,a_name,remaining,b_name", PROFILES)
def test_profiles_bind_the_full_instruction_and_two_ordered_roles(
    task_id, instruction, completed, a_name, remaining, b_name
):
    from egrs.composition055.catalog import get_task

    profile = get_task(task_id)
    assert profile["task_id"] == task_id
    assert profile["instruction"] == instruction
    assert profile["name"] == "LIVING_ROOM_SCENE2_" + instruction.replace(" ", "_")
    assert profile["completed_object"] == completed
    assert profile["remaining_object"] == remaining
    assert profile["raw_goals"] == [["in", completed, REGION], ["in", remaining, REGION]]
    assert profile["goals"] == [
        {
            "id": "A",
            "instruction": f"put the {a_name} in the basket",
            "predicates": [["in", completed, REGION]],
        },
        {
            "id": "B",
            "instruction": f"put the {b_name} in the basket",
            "predicates": [["in", remaining, REGION]],
        },
    ]
    profile["goals"][0]["predicates"][0][1] = "milk_1"
    profile["raw_goals"][1][1] = "milk_1"
    fresh = get_task(task_id)
    assert fresh["goals"][0]["predicates"][0][1] == completed
    assert fresh["raw_goals"][1][1] == remaining


@pytest.mark.parametrize("task_id", ["basket", "composition_soup_milk"])
def test_registry_and_renderer_reject_unregistered_combinations(task_id):
    from egrs.composition055.catalog import get_task, render_bddl

    with pytest.raises(ValueError, match="unknown Task055 task"):
        get_task(task_id)
    with pytest.raises(ValueError, match="unknown Task055 task"):
        render_bddl(b"", task_id)


# Minimal synthetic BDDL with the same three editable forms as the pinned source.
# The regions, inventory, and start are deliberately visible for bytewise comparison.
SCENE_START = """(define (problem LIBERO_Living_Room_Tabletop_Manipulation)
  (:domain robosuite)
"""
SCENE_ASSETS = """    (:regions
      (contain_region (:target basket_1))
    )

  (:fixtures
    living_room_table - living_room_table
  )

  (:objects
    alphabet_soup_1 - alphabet_soup
    cream_cheese_1 - cream_cheese
    tomato_sauce_1 - tomato_sauce
    milk_1 - milk
    butter_1 - butter
    basket_1 - basket
  )

"""
SCENE_INIT = """  (:init
    (On alphabet_soup_1 living_room_table_alphabet_soup_init_region)
    (On milk_1 living_room_table_milk_init_region)
    (On basket_1 living_room_table_basket_init_region)
  )

"""
CANONICAL_TEXT = (
    SCENE_START
    + "  (:language put both the alphabet soup and the tomato sauce in the basket)\n"
    + SCENE_ASSETS
    + "  (:obj_of_interest\n    alphabet_soup_1\n    tomato_sauce_1\n    basket_1\n  )\n\n"
    + SCENE_INIT
    + "  (:goal\n"
    + "    (And (In alphabet_soup_1 basket_1_contain_region) "
      "(In tomato_sauce_1 basket_1_contain_region))\n"
    + "  )\n\n)\n"
)


@pytest.mark.parametrize("task_id,instruction,completed,a_name,remaining,b_name", PROFILES)
def test_bddl_changes_only_language_object_interest_and_goal(
    monkeypatch, task_id, instruction, completed, a_name, remaining, b_name
):
    from egrs.composition055 import catalog

    canonical_bytes = CANONICAL_TEXT.encode("utf-8")
    monkeypatch.setattr(catalog, "CANONICAL_BDDL_SHA256", hashlib.sha256(canonical_bytes).hexdigest())
    expected_text = (
        SCENE_START + f"  (:language {instruction})\n"
        + SCENE_ASSETS
        + f"  (:obj_of_interest\n    {completed}\n    {remaining}\n    basket_1\n  )\n\n"
        + SCENE_INIT
        + f"  (:goal\n    (And (In {completed} {REGION}) (In {remaining} {REGION}))\n  )\n\n)\n"
    )
    assert catalog.render_bddl(canonical_bytes, task_id) == expected_text.encode("utf-8")
    assert catalog.render_bddl(CANONICAL_TEXT, task_id) == expected_text


@pytest.mark.parametrize(
    "tampered",
    [
        CANONICAL_TEXT.replace("LIBERO_Living_Room_Tabletop_Manipulation", "other_scene"),
        CANONICAL_TEXT.replace("milk_1 - milk", "other_1 - other"),
        CANONICAL_TEXT + "\n",
    ],
    ids=["wrong-scene", "wrong-inventory", "wrong-bytes"],
)
def test_bddl_rejects_a_source_with_the_wrong_digest(monkeypatch, tampered):
    from egrs.composition055 import catalog

    canonical_bytes = CANONICAL_TEXT.encode("utf-8")
    monkeypatch.setattr(catalog, "CANONICAL_BDDL_SHA256", hashlib.sha256(canonical_bytes).hexdigest())
    with pytest.raises(ValueError, match="canonical BDDL SHA-256"):
        catalog.render_bddl(tampered, "composition_soup_butter")


def test_bddl_uses_pinned_official_asset_identity():
    from egrs.composition055 import catalog

    assert catalog.CANONICAL_SUITE == "libero_10"
    assert catalog.CANONICAL_TASK_ID == 0
    assert catalog.CANONICAL_BDDL_SHA256 == (
        "2e661058917f683a25bce480015197f0a2c1911bcbc2b9dd9d947199069c9618"
    )
    assert catalog.CANONICAL_INITIAL_STATES_SHA256 == (
        "1899fe54c51e24a41d5f9e32254730d6777f4894ab68e0e873f1fa7ae2062030"
    )
    with pytest.raises(ValueError, match="canonical BDDL SHA-256"):
        catalog.render_bddl(CANONICAL_TEXT, "composition_soup_butter")


def test_population_is_fixed_and_binds_each_task_to_the_canonical_index():
    from egrs.composition055.catalog import expected, validate_population

    rows = expected()
    assert len(rows) == 150
    for task_position, (task_id, instruction, *_) in enumerate(PROFILES):
        for index in range(50):
            row = rows[task_position * 50 + index]
            assert row == {
                "task_id": task_id,
                "initial_state_index": index,
                "episode_id": f"{task_id}_s{index:03d}_10",
                "source_id": f"composition055_canonical_basket_{index:03d}",
                "instruction": instruction,
                "initial_mask": [True, False],
                "split": "test",
                "horizon": 520,
                "retention_steps": 150,
            }
    rows[0]["initial_mask"][0] = False
    assert rows[1]["initial_mask"] == [True, False]
    assert expected()[0]["initial_mask"] == [True, False]
    validate_population([dict(row, status="pending") for row in expected()])


@pytest.mark.parametrize(
    "broken",
    [
        lambda rows: rows[:-1],
        lambda rows: rows[:1] + rows[:-1],
        lambda rows: rows[1:2] + rows[0:1] + rows[2:],
        lambda rows: rows[:-1] + [dict(rows[-1], initial_state_index=50)],
        lambda rows: [dict(rows[0], initial_state_index=False)] + rows[1:],
        lambda rows: [dict(rows[0], initial_mask=[1, 0])] + rows[1:],
        lambda rows: [dict(rows[0], source_id=rows[1]["source_id"])] + rows[1:],
        lambda rows: [dict(rows[0], initial_mask=[False, True])] + rows[1:],
    ],
    ids=[
        "missing", "duplicate", "reordered", "out-of-range", "boolean-index",
        "integer-mask", "wrong-source", "wrong-role",
    ],
)
def test_population_validation_rejects_invalid_rows(broken):
    from egrs.composition055.catalog import expected, validate_population

    with pytest.raises(ValueError, match="Task055 population"):
        validate_population(broken(expected()))
