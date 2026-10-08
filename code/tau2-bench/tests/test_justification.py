"""Tests for the no-action justification check (COS597C).

Design: docs/research/justification-check.md in the project repository.
"""

import json

import pytest

from tau2.evaluator.justification_core import (
    ObservedCall,
    check_task,
    parse_spec,
)

SPEC = {
    "48": {
        "required_reads": [
            {
                "tool": "get_reservation_details",
                "match": {"reservation_id": "3RK2T9"},
                "why": "booking time decides the cancellation",
            }
        ]
    },
    "10": {
        "required_reads": [
            {"tool": "get_reservation_details", "match": {"reservation_id": "4NQLHD"}},
            {
                "tool": ["search_direct_flight", "search_onestop_flight"],
                "match": {"origin": "IAH", "destination": "SEA", "date": "2024-05-24"},
            },
        ]
    },
}


@pytest.fixture
def spec():
    return parse_spec(SPEC)


# --- core ---------------------------------------------------------------


def test_no_calls_is_unjustified(spec):
    verdict = check_task(spec["48"], [])
    assert verdict.justified is False
    assert len(verdict.missing) == 1
    assert verdict.found == []


def test_matching_read_is_justified(spec):
    calls = [ObservedCall("get_reservation_details", {"reservation_id": "3RK2T9"})]
    assert check_task(spec["48"], calls).justified is True


def test_extra_calls_and_order_are_ignored(spec):
    calls = [
        ObservedCall("get_user_details", {"user_id": "anya_garcia_5901"}),
        ObservedCall("transfer_to_human_agents", {"summary": "x"}),
        ObservedCall("get_reservation_details", {"reservation_id": "3RK2T9"}),
    ]
    assert check_task(spec["48"], calls).justified is True


def test_wrong_id_does_not_match(spec):
    calls = [ObservedCall("get_reservation_details", {"reservation_id": "JMO1MG"})]
    assert check_task(spec["48"], calls).justified is False


def test_failed_call_does_not_count(spec):
    calls = [
        ObservedCall(
            "get_reservation_details", {"reservation_id": "3RK2T9"}, succeeded=False
        )
    ]
    assert check_task(spec["48"], calls).justified is False


def test_tool_alternatives_and_partial_args(spec):
    calls = [
        ObservedCall("get_reservation_details", {"reservation_id": "4NQLHD"}),
        # one-stop search counts as well as direct; unlisted args are ignored
        ObservedCall(
            "search_onestop_flight",
            {"origin": "IAH", "destination": "SEA", "date": "2024-05-24", "x": 1},
        ),
    ]
    verdict = check_task(spec["10"], calls)
    assert verdict.justified is True
    assert len(verdict.found) == 2


def test_partially_met_lists_missing(spec):
    calls = [ObservedCall("get_reservation_details", {"reservation_id": "4NQLHD"})]
    verdict = check_task(spec["10"], calls)
    assert verdict.justified is False
    assert [r.tools for r in verdict.missing] == [
        ["search_direct_flight", "search_onestop_flight"]
    ]


def test_parse_spec_rejects_empty_requirements():
    with pytest.raises(ValueError):
        parse_spec({"1": {"required_reads": []}})


def test_parse_spec_rejects_missing_match():
    with pytest.raises(ValueError):
        parse_spec({"1": {"required_reads": [{"tool": "get_user_details"}]}})


# --- tau2 adapter -------------------------------------------------------


def _null_results():
    from tau2.data_model.simulation import Results
    from tau2.utils.utils import DATA_DIR

    path = DATA_DIR / "simulations" / "airline_do_nothing" / "results.json"
    if not path.exists():
        pytest.skip("null-agent results not available")
    return Results.load(path)


def _rescore(results, original_scoring):
    from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
    from tau2.scripts.evaluate_trajectories import (
        _build_eval_env_kwargs,
        get_communication_mode,
    )

    tasks = {t.id: t for t in results.tasks}
    domain = results.info.environment_info.domain_name
    out = {}
    for sim in results.simulations:
        out[sim.task_id] = evaluate_simulation(
            simulation=sim,
            task=tasks[sim.task_id],
            evaluation_type=EvaluationType.ALL,
            solo_mode=False,
            domain=domain,
            mode=get_communication_mode(results, sim),
            env_kwargs=_build_eval_env_kwargs(domain, tasks[sim.task_id]),
            strict_replay=False,
            original_scoring=original_scoring,
        )
    return out


def test_airline_spec_file_is_valid():
    from tau2.evaluator.evaluator_justification import load_domain_spec

    spec = load_domain_spec("airline")
    assert spec is not None
    assert len(spec) == 16
    tasks = json.load(
        open(
            __import__("tau2.utils.utils", fromlist=["DATA_DIR"]).DATA_DIR
            / "tau2"
            / "domains"
            / "airline"
            / "tasks.json"
        )
    )
    ids = {t["id"] for t in tasks}
    assert set(spec) <= ids


def test_null_agent_justified_vs_original():
    results = _null_results()
    justified = _rescore(results, original_scoring=False)
    original = _rescore(results, original_scoring=True)

    # Original scoring is unchanged: 23 passes.
    assert sum(r.reward for r in original.values()) == 23
    assert all(r.scoring_mode == "original" for r in original.values())

    # Justified scoring removes every pass on the 16 tasks in the spec.
    from tau2.evaluator.evaluator_justification import load_domain_spec

    spec = load_domain_spec("airline")
    for task_id, r in justified.items():
        assert r.scoring_mode == "justified"
        assert r.original_reward == original[task_id].reward
        if task_id in spec:
            assert r.justification is not None
            assert r.justification.justified is False
            assert r.reward == 0.0
        else:
            assert r.justification is None
            assert r.reward == original[task_id].reward
    assert sum(r.reward for r in justified.values()) == 23 - 16
