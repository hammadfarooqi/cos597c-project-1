"""Tests for the benchmark-free core. No benchmark is imported."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from noop_doctor.core import checkup, pairs  # noqa: E402
from noop_doctor.core.calls import Episode, ObservedCall, ToolKind  # noqa: E402
from noop_doctor.core.flips import apply_flip, apply_flips  # noqa: E402
from noop_doctor.core.reads import (  # noqa: E402
    check_task,
    compare_specs,
    draft_spec,
    parse_spec,
)
from noop_doctor.core.state import leaf_diff, patch_leaves  # noqa: E402
from noop_doctor.core.twins import TwinSpec, validate_twin  # noqa: E402

KINDS = {"get": ToolKind.READ, "lookup_user": ToolKind.READ, "cancel": ToolKind.WRITE}


def kind(name):
    return KINDS.get(name, ToolKind.OTHER)


# --- reads ---------------------------------------------------------------------------


def test_read_gate_needs_every_read_and_ignores_failed_calls():
    spec = parse_spec(
        {
            "_meta": {"x": 1},
            "7": {"required_reads": [{"tool": ["get", "get2"], "match": {"id": "A"}}]},
        }
    )
    assert set(spec) == {"7"}
    ok = [ObservedCall("get2", {"id": "A", "extra": 1})]
    assert check_task(spec["7"], ok).justified
    assert not check_task(spec["7"], [ObservedCall("get", {"id": "B"})]).justified
    assert not check_task(
        spec["7"], [ObservedCall("get", {"id": "A"}, False)]
    ).justified


def test_parse_spec_rejects_empty_match():
    with pytest.raises(ValueError):
        parse_spec({"1": {"required_reads": [{"tool": "get", "match": {}}]}})


def test_draft_spec_keeps_reads_drops_writes_skips_and_duplicates():
    gold = {
        "1": [
            ObservedCall("lookup_user", {"u": 1}),
            ObservedCall("get", {"id": "A"}),
            ObservedCall("get", {"id": "A"}),
            ObservedCall("cancel", {"id": "A"}),
        ],
        "2": [ObservedCall("transfer", {"summary": "x"})],
    }
    d = draft_spec(["1", "2"], gold.__getitem__, kind, skip_tools=["lookup_user"])
    assert d["1"]["required_reads"] == [
        {"tool": "get", "match": {"id": "A"}, "why": "from gold"}
    ]
    assert d["_meta"]["no_gold_reads"] == ["2"]
    parse_spec(d)  # a draft is a valid spec


def test_compare_specs():
    a = parse_spec({"1": {"required_reads": [{"tool": "get", "match": {"id": "A"}}]}})
    b = parse_spec(
        {
            "1": {
                "required_reads": [
                    {"tool": "get", "match": {"id": "A"}},
                    {"tool": "get", "match": {"id": "B"}},
                ]
            }
        }
    )
    assert compare_specs(a, b) == {"1": {"both": 1, "draft_only": 0, "ref_only": 1}}


# --- state and flips -----------------------------------------------------------------


def test_leaf_diff_and_patch_leaves():
    assert leaf_diff({"a": {"b": 1, "c": [1, 2]}}, {"a": {"b": 1, "c": [1, 3]}}) == [
        ("a", "c", 1)
    ]
    assert patch_leaves({"r": {"X": {"cabin": "business"}}}) == [("r", "X", "cabin")]
    assert patch_leaves({}) == []


def test_flip_needs_exactly_one_occurrence():
    assert apply_flip("a. b. c.", "b.", "B!") == "a. B! c."
    with pytest.raises(ValueError):
        apply_flip("b. b.", "b.", "x")
    with pytest.raises(ValueError, match="flip f1"):
        apply_flips("abc", {"f1": {"original": "z", "replacement": "y"}})


# --- twins, with a toy benchmark -----------------------------------------------------


class ToyAdapter:
    """State: {"orders": {id: {"refundable": bool, "status": str}}}. As in tau2, the
    tools do not enforce the policy, and the grader compares the final state with the
    state the gold calls produce. The original task's gold is "no change"."""

    name = "toy"
    base = {"orders": {"A": {"refundable": False, "status": "open"}}}

    def task(self, tid):
        return {"id": tid, "patch": {}, "gold": []}

    def gold_reads(self, tid):
        return [ObservedCall("get", {"id": "A"})]

    def build_twin(self, spec):
        return {"id": spec.twin_id, "patch": spec.patch, "gold": [spec.write]}

    def state(self, patch):
        import copy

        s = copy.deepcopy(self.base)
        for oid, fields in (patch or {}).get("orders", {}).items():
            s["orders"][oid].update(fields)
        return s

    def _run(self, patch, calls):
        s = self.state(patch)
        for c in calls:
            o = s["orders"][c.arguments["id"]]
            if c.name == "cancel":
                o["status"] = "cancelled"
        return s

    def state_reward(self, task, calls):
        want = self._run(task["patch"], task["gold"])
        return float(self._run(task["patch"], calls) == want)


def test_validate_twin_accepts_a_good_flip_and_rejects_a_useless_one():
    ad = ToyAdapter()
    write = ObservedCall("cancel", {"id": "A"})
    good = validate_twin(
        ad, TwinSpec("1", "refundable", write, {"orders": {"A": {"refundable": True}}})
    )
    assert good.ok, good.failures()
    useless = validate_twin(
        ad, TwinSpec("1", "noop", write, {"orders": {"A": {"status": "open"}}})
    )
    assert not useless.ok
    assert useless.failures() == ["patch changes nothing"]


# --- pairs and checkup ---------------------------------------------------------------


def test_pair_scoring_and_failure_causes():
    w = ObservedCall("cancel", {"id": "A"})
    info = {"1_twin_x": ("1", "DB", w), "2_twin_y": ("2", "policy", w)}
    orig = {"1": Episode("1", 1.0), "2": Episode("2", 1.0)}
    twins = {
        "1_twin_x": Episode("1_twin_x", 1.0),
        "2_twin_y": Episode("2_twin_y", 0.0, [ObservedCall("transfer_x", {})]),
    }
    res = pairs.score_pairs(orig, twins, info, {"cancel"}, {"transfer_x"})
    s = pairs.summarize(res)
    assert (s["paired"], s["noop_only"], s["credit_removed"]) == (1, 1, 1)
    assert s["causes"] == {"transfer": 1}
    assert pairs.failure_cause(
        [ObservedCall("cancel", {"id": "A"})], w, {"cancel"}, set()
    ) == ("right write + other error")
    assert pairs.failure_cause(
        [ObservedCall("cancel", {"id": "B"})], w, {"cancel"}, set()
    ) == ("wrong write")


def test_checkup_summary():
    class A:
        def task_ids(self):
            return ["1", "2", "3"]

        def gold_calls(self, tid):
            return {
                "1": [ObservedCall("get", {"id": 1})],
                "2": [],
                "3": [ObservedCall("cancel", {})],
            }[tid]

        tool_kind = staticmethod(kind)

        def null_reward(self, tid):
            if tid == "3":
                raise RuntimeError("no key")
            return 1.0

    s = checkup.summarize(checkup.run_checkup(A()))
    assert s["null_passes"] == 2
    assert s["passed_with_gold_reads"] == ["1"]
    assert s["passed_without_gold_reads"] == ["2"]
    assert "3" in s["errors"]
