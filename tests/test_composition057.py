import hashlib

import pytest


PROFILES = [
    (
        "probe_soup_milk",
        "put both the alphabet soup and the milk in the basket",
        "alphabet_soup_1", "alphabet soup", "milk_1", "milk",
    ),
    (
        "probe_soup_orange_juice",
        "put both the alphabet soup and the orange juice in the basket",
        "alphabet_soup_1", "alphabet soup", "orange_juice_1", "orange juice",
    ),
    (
        "probe_tomato_milk",
        "put both the tomato sauce and the milk in the basket",
        "tomato_sauce_1", "tomato sauce", "milk_1", "milk",
    ),
    (
        "probe_tomato_orange_juice",
        "put both the tomato sauce and the orange juice in the basket",
        "tomato_sauce_1", "tomato sauce", "orange_juice_1", "orange juice",
    ),
]
REGION = "basket_1_contain_region"


@pytest.mark.parametrize("task_id,instruction,completed,a_name,remaining,b_name", PROFILES)
def test_probe_profiles_bind_full_instruction_and_two_ordered_roles(
    task_id, instruction, completed, a_name, remaining, b_name
):
    from egrs.composition057.catalog import get_task

    profile = get_task(task_id)
    assert profile["task_id"] == task_id
    assert profile["instruction"] == instruction
    assert profile["name"] == "LIVING_ROOM_SCENE2_" + instruction.replace(" ", "_")
    assert profile["completed_object"] == completed
    assert profile["remaining_object"] == remaining
    assert profile["raw_goals"] == [["in", completed, REGION], ["in", remaining, REGION]]
    assert profile["goals"] == [
        {"id": "A", "instruction": f"put the {a_name} in the basket",
         "predicates": [["in", completed, REGION]]},
        {"id": "B", "instruction": f"put the {b_name} in the basket",
         "predicates": [["in", remaining, REGION]]},
    ]


def test_population_is_four_tasks_by_fifteen_and_ordered():
    from egrs.composition057 import catalog

    rows = catalog.expected()
    assert len(rows) == 60
    assert catalog.SOURCE_COUNT == 15
    assert catalog.TASK_ORDER == tuple(profile[0] for profile in PROFILES)
    counts = {task: sum(row["task_id"] == task for row in rows) for task in catalog.TASK_ORDER}
    assert set(counts.values()) == {15}
    assert [row["episode_id"] for row in rows[:2]] == [
        "probe_soup_milk_s000_10", "probe_soup_milk_s001_10"]
    assert all(row["initial_mask"] == [True, False] and row["split"] == "probe" for row in rows)


@pytest.mark.parametrize("size", [59, 61])
def test_population_rejects_wrong_size(size):
    from egrs.composition057 import catalog

    rows = (catalog.expected() + catalog.expected())[:size]
    with pytest.raises(ValueError, match="requires exactly 60 rows"):
        catalog.validate_population(rows)


def test_population_rejects_a_swapped_identity():
    from egrs.composition057 import catalog

    rows = catalog.expected()
    rows[0]["task_id"] = "probe_tomato_milk"
    with pytest.raises(ValueError, match="wrong task_id"):
        catalog.validate_population(rows)


@pytest.mark.parametrize("task_id", ["basket", "composition_soup_butter"])
def test_registry_rejects_non_probe_keys(task_id):
    from egrs.composition057.catalog import get_task, render_bddl

    with pytest.raises(ValueError, match="unknown Task057 probe"):
        get_task(task_id)
    with pytest.raises(ValueError, match="unknown Task057 probe"):
        render_bddl(b"", task_id)


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
    orange_juice_1 - orange_juice
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
def test_bddl_changes_only_language_interest_and_goal(
    monkeypatch, task_id, instruction, completed, a_name, remaining, b_name
):
    from egrs.composition057 import catalog

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


def test_bddl_rejects_wrong_digest(monkeypatch):
    from egrs.composition057 import catalog

    canonical_bytes = CANONICAL_TEXT.encode("utf-8")
    monkeypatch.setattr(catalog, "CANONICAL_BDDL_SHA256", hashlib.sha256(canonical_bytes).hexdigest())
    with pytest.raises(ValueError, match="canonical BDDL SHA-256"):
        catalog.render_bddl(CANONICAL_TEXT + "\n", "probe_soup_milk")


def test_bddl_rejects_goal_object_missing_from_inventory(monkeypatch):
    from egrs.composition057 import catalog

    text = CANONICAL_TEXT.replace("    orange_juice_1 - orange_juice\n", "")
    canonical_bytes = text.encode("utf-8")
    monkeypatch.setattr(catalog, "CANONICAL_BDDL_SHA256", hashlib.sha256(canonical_bytes).hexdigest())
    with pytest.raises(ValueError, match="not declared"):
        catalog.render_bddl(text, "probe_soup_orange_juice")


def test_only_base_is_an_allowed_probe_model():
    from egrs.composition057 import catalog

    assert catalog.MODEL_ORDER == ("base",)
    assert catalog.task_index("probe_tomato_orange_juice") == 3
    with pytest.raises(ValueError, match="unknown Task057 probe"):
        catalog.task_index("probe_milk_butter")


def test_probe_counts_are_sixty_with_fifteen_per_task():
    from egrs.composition057 import catalog, preparation

    rows = [{**row, "status": "pending"} for row in catalog.expected()]
    report = preparation._counts({"rows": rows})
    assert report["expected"] == 60 and report["ready"] == 0 and report["pending"] == 60
    assert report["complete"] is False and report["ready_percent"] == 0.0
    assert report["per_task"] == {
        task: {"ready": 0, "failed": 0, "pending": 15, "running": 0,
               "expected": 15, "ready_percent": 0.0}
        for task in catalog.TASK_ORDER
    }


def test_build_config_requires_the_exact_precompleted_only_fields():
    from egrs.composition057 import contracts

    base = {
        "schema_version": contracts.SCHEMA,
        "benchmark_root": "core", "canonical_bddl": "task.bddl",
        "canonical_initial_states": "task.pruned_init",
        "environment_config": "environment.json",
        "protected_roots": ["data"],
    }
    assert contracts.load_config(_write_config(base))["benchmark_root"].endswith("core")
    with pytest.raises(ValueError, match="Exact057"):
        contracts.load_config(_write_config({**base, "normal_bank": "x"}))
    with pytest.raises(ValueError, match="Exact057"):
        contracts.load_config(_write_config({**base, "schema_version": "task056-composition-eval-v1"}))


def test_probe_eval_config_has_no_adapter_fields():
    from egrs.composition057 import evaluation

    base = {
        "schema_version": evaluation.SCHEMA,
        "source_bank": "bank", "base_runtime": "runtime.json",
        "reporting_root": "reporting", "protected_roots": ["data"],
    }
    loaded = evaluation.load_config(_write_config(base))
    assert loaded["base_runtime"].endswith("runtime.json")
    with pytest.raises(ValueError, match="Exact057 probe"):
        evaluation.load_config(_write_config({**base, "adapter_h0": "h0"}))
    with pytest.raises(ValueError, match="Exact057 probe"):
        evaluation.load_config(_write_config({**base, "schema_version": "task056-composition-eval-v1"}))


def _write_config(value, name="config.json"):
    import json
    from pathlib import Path
    import tempfile

    root = Path(tempfile.mkdtemp())
    path = root / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path
