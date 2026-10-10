"""The tau2 adapter reproduces the hand-built airline results.

Run with tau2's environment, from code/tau2-bench/:
    uv run --extra dev python -m pytest ../doctor/tests
No API key is needed: only airline is scored here (no NL assertions).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pytest.importorskip("tau2")

from noop_doctor.adapters.tau2 import Tau2Adapter  # noqa: E402
from noop_doctor.core.calls import ObservedCall, ToolKind  # noqa: E402
from noop_doctor.core.flips import apply_flips  # noqa: E402
from noop_doctor.core.reads import draft_spec  # noqa: E402
from noop_doctor.core.twins import TwinSpec, validate_twin  # noqa: E402

TAU2 = Path(__file__).resolve().parents[2] / "tau2-bench"
AIRLINE = TAU2 / "data" / "tau2" / "domains" / "airline"


@pytest.fixture(scope="module")
def airline():
    return Tau2Adapter("airline")


def test_tool_kinds_come_from_tau2_labels(airline):
    assert airline.tool_kind("get_reservation_details") == ToolKind.READ
    assert airline.tool_kind("cancel_reservation") == ToolKind.WRITE
    assert airline.tool_kind("transfer_to_human_agents") == ToolKind.OTHER
    assert airline.tool_kind("no_such_tool") == ToolKind.OTHER
    assert "cancel_reservation" in airline.write_tools()
    assert airline.transfer_tools() == {"transfer_to_human_agents"}


@pytest.mark.parametrize("task_id,expected", [("0", 1.0), ("1", 1.0), ("7", 0.0)])
def test_null_reward_matches_the_null_agent_run(airline, task_id, expected):
    # docs/research/findings-log.md §1: tasks 0 and 1 pass, task 7 (a write task) fails
    assert airline.null_reward(task_id) == expected


def test_existing_twins_validate(airline):
    specs = airline.twin_specs_from_tasks(AIRLINE / "tasks_twins.json")
    by_id = {s.twin_id: s for s in specs}
    for twin_id in ("48_twin_business", "2_twin_pf_delay_no_change"):
        check = validate_twin(airline, by_id[twin_id])
        assert check.ok, (twin_id, check.failures())


def test_a_twin_with_the_wrong_write_is_rejected(airline):
    good = {
        s.twin_id: s
        for s in airline.twin_specs_from_tasks(AIRLINE / "tasks_twins.json")
    }["48_twin_business"]
    bad = TwinSpec(
        good.task_id,
        "wrong",
        ObservedCall("cancel_reservation", {"reservation_id": "NO_SUCH"}),
        good.patch,
    )
    assert not validate_twin(airline, bad).ok


def test_policy_flip_reproduces_the_committed_file():
    import yaml

    flips = yaml.safe_load((TAU2.parent / "twins" / "policy_flips.yaml").read_text())
    out = apply_flips((AIRLINE / "policy.md").read_text(), flips)
    committed = (AIRLINE / "policy_flips" / "delay_no_change.md").read_text()
    assert out["delay_no_change"] == committed


def test_draft_reads_from_gold(airline):
    d = draft_spec(["1"], airline.gold_calls, airline.tool_kind, ["get_user_details"])
    assert d["1"]["required_reads"][0]["match"] == {"reservation_id": "Q69X3R"}
