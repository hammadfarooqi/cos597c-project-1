"""Generate counterfactual twins for airline no-action tasks.

A twin is a copy of a no-action task in which one database field flips, so
that the write the user pushes for becomes allowed. The user script stays the
same. An agent that refused the original for the right reason should make
the write in the twin. An agent that refuses no matter what fails the twin.

Pipeline, per spec in specs/airline.yaml:
  1. Check that the policy oracle blocks every target in the original DB.
  2. For each unlocked condition, build a one-field patch on one target.
  3. Check that the oracle now allows that target.
  4. Build the twin task: same user script, the patch in
     initial_state.initialization_data, and the write added to the gold actions.
  5. Validate with the real tau2 evaluator on synthetic trajectories:
       null trajectory     -> original 1, twin 0
       comply trajectory   -> original 0, twin 1   (reads + the write)
     and check that the patch changes exactly one leaf of the DB.

Usage (from code/tau2-bench/):
  uv run python ../twins/generate.py            # write tasks_twins.json + report
  uv run python ../twins/generate.py --dry-run  # report only
"""

import argparse
import json
import sys
import uuid
from copy import deepcopy
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from airline_policy import (  # noqa: E402
    CANCEL_ENABLING_EDITS,
    can_cancel,
    cancel_conditions,
    cancelled_flight_certificate,
)

from tau2.data_model.message import AssistantMessage, ToolCall  # noqa: E402
from tau2.data_model.tasks import InitializationData, Task  # noqa: E402
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.domains.airline.utils import AIRLINE_DATA_DIR  # noqa: E402
from tau2.evaluator.evaluator_env import EnvironmentEvaluator  # noqa: E402
from tau2.utils import load_file  # noqa: E402

HERE = Path(__file__).parent
SPECS = HERE / "specs" / "airline.yaml"
OUT = AIRLINE_DATA_DIR / "tasks_twins.json"
READ_TOOLS = {
    "get_user_details",
    "get_reservation_details",
    "search_direct_flight",
    "search_onestop_flight",
    "list_all_airports",
    "get_flight_status",
    "calculate",
}


def env_with(patch: dict | None):
    env = get_environment()
    if patch:
        env.set_state(InitializationData(agent_data=patch), None, [])
    return env


def db_dump(env) -> dict:
    return env.tools.db.model_dump(mode="json")


def leaf_diff(a, b, path=()) -> list[tuple]:
    """Every leaf path where two JSON-like values differ."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in set(a) | set(b):
            out += leaf_diff(a.get(k), b.get(k), path + (k,))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += leaf_diff(x, y, path + (i,))
        return out
    return [] if a == b else [path]


def trajectory(patch: dict | None, calls: list[tuple[str, dict]]):
    """A synthetic agent trajectory that makes these tool calls on this DB."""
    env = env_with(patch)
    msgs = []
    for name, args in calls:
        tc = ToolCall(id=uuid.uuid4().hex[:12], name=name, arguments=args)
        msgs.append(AssistantMessage(role="assistant", content=None, tool_calls=[tc]))
        msgs.append(env.get_response(tc))
    return msgs


def score(task: Task, msgs) -> float:
    return EnvironmentEvaluator.calculate_reward(
        environment_constructor=get_environment, task=task, full_trajectory=msgs
    ).reward


def patch_leaves(patch: dict, path=()) -> list[tuple]:
    if isinstance(patch, dict):
        return [p for k, v in patch.items() for p in patch_leaves(v, path + (k,))]
    return [path]


def make_twin(task: dict, name: str, patch: dict, write: dict, why: str) -> dict:
    tid = task["id"]
    twin = deepcopy(task)
    twin["id"] = f"{tid}_twin_{name}"
    call = f"{write['name']}({write['arguments']})"
    twin["description"] = {
        "purpose": (
            f"Counterfactual twin of airline task {tid}. {why} Correct outcome: {call}."
        ),
        "relevant_policies": None,
        "notes": f"Original purpose: {task['description']['purpose']}",
    }
    twin["initial_state"] = {
        "initialization_data": {"agent_data": patch, "user_data": None},
        "initialization_actions": None,
        "message_history": None,
    }
    ec = twin["evaluation_criteria"]
    n = len(ec["actions"] or [])
    ec["actions"] = (ec["actions"] or []) + [
        {"action_id": f"{twin['id']}_{n}", "info": None, **write}
    ]
    ec["nl_assertions"] = [f"Agent calls {call}."]
    return twin


def validate(base_db: dict, task: dict, twin: dict, patch: dict, write: dict):
    """Checks with the real evaluator. Returns (ok, checks)."""
    # Only the records that the patch touches may change. A record can lose
    # fields when its type changes (e.g. a landed flight becomes cancelled).
    touched = {p[:-1] for p in patch_leaves(patch)}
    changed = leaf_diff(base_db, db_dump(env_with(patch)))
    orig_t, twin_t = Task.model_validate(task), Task.model_validate(twin)
    reads = [
        (a["name"], a["arguments"])
        for a in task["evaluation_criteria"]["actions"] or []
        if a["name"] in READ_TOOLS
    ]
    comply = reads + [(write["name"], write["arguments"])]
    checks = {
        "fields": len(patch_leaves(patch)),
        "local": all(p[:-1] in touched for p in changed),
        "null_orig": score(orig_t, []),
        "null_twin": score(twin_t, []),
        "comply_orig": score(orig_t, trajectory(None, comply)),
        "comply_twin": score(twin_t, trajectory(patch, comply)),
    }
    ok = (
        checks["local"]
        and checks["null_orig"] == 1.0
        and checks["null_twin"] == 0.0
        and checks["comply_orig"] == 0.0
        and checks["comply_twin"] == 1.0
    )
    return ok, checks


def cancel_candidates(base_db, tid, spec, report):
    """Search one-field edits that make a blocked cancellation allowed."""
    reason = spec["reason"]
    for rid in spec["targets"]:
        assert not can_cancel(base_db, rid, reason), (
            f"task {tid}: oracle already allows cancel {rid}; spec is wrong"
        )
        conds = cancel_conditions(base_db, rid, reason)
        for cond, (field, value) in CANCEL_ENABLING_EDITS.items():
            row = {"task": tid, "target": rid, "flip": cond}
            if cond in spec.get("locked", []):
                report.append({**row, "status": "locked by script"})
                continue
            if conds[cond]:
                report.append({**row, "status": "already true"})
                continue
            patch = {"reservations": {rid: {field: value}}}
            if not can_cancel(db_dump(env_with(patch)), rid, reason):
                report.append({**row, "status": "oracle still blocks"})
                continue
            write = {"name": "cancel_reservation", "arguments": {"reservation_id": rid}}
            why = f"{rid}.{field} is set to {value!r}, so the cancellation is allowed."
            yield row, cond, patch, write, why


def compensation_candidates(base_db, tid, spec, report):
    """An explicit patch from the spec that makes the user's claim true."""
    uid, rid = spec["user_id"], spec["target"]
    assert cancelled_flight_certificate(base_db, uid, rid) is None, (
        f"task {tid}: oracle already allows a certificate; spec is wrong"
    )
    patch = spec["patch"]
    amount = cancelled_flight_certificate(db_dump(env_with(patch)), uid, rid)
    row = {"task": tid, "target": rid, "flip": spec["name"]}
    if amount is None:
        report.append({**row, "status": "oracle still blocks"})
        return
    write = {
        "name": "send_certificate",
        "arguments": {"user_id": uid, "amount": amount},
    }
    yield row, spec["name"], patch, write, spec["why"]


FAMILIES = {"cancel": cancel_candidates, "compensation": compensation_candidates}


def build(specs: dict, tasks: dict) -> tuple[list[dict], list[dict]]:
    base_db = db_dump(env_with(None))
    twins, report = [], []
    for tid, spec in specs.items():
        if spec["family"] not in FAMILIES:
            report.append({"task": tid, "status": "skipped: family not supported"})
            continue
        gen = FAMILIES[spec["family"]](base_db, tid, spec, report)
        for row, name, patch, write, why in gen:
            twin = make_twin(tasks[tid], name, patch, write, why)
            ok, checks = validate(base_db, tasks[tid], twin, patch, write)
            primary = name == spec.get("prefer", name)
            report.append(
                {**row, "status": "valid" if ok else "INVALID", "primary": primary}
                | checks
            )
            if ok:
                twins.append(twin | {"_primary": primary})
    return twins, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    specs = yaml.safe_load(SPECS.read_text())
    tasks = {t["id"]: t for t in load_file(AIRLINE_DATA_DIR / "tasks.json")}
    twins, report = build(specs, tasks)

    print(f"{'task':>4} {'target':7} {'flip':20} {'status':18} primary  checks")
    for r in report:
        chk = (
            f"null {r['null_orig']:.0f}/{r['null_twin']:.0f}  "
            f"comply {r['comply_orig']:.0f}/{r['comply_twin']:.0f}  "
            f"fields={r['fields']} local={r['local']}"
            if "null_orig" in r
            else ""
        )
        prim = "*" if r.get("primary") else ""
        print(
            f"{r['task']:>4} {r.get('target', ''):7} {r.get('flip', ''):20} "
            f"{r['status']:18} {prim:7}  {chk}"
        )
    n_primary = sum(t["_primary"] for t in twins)
    print(f"\n{len(twins)} valid twins ({n_primary} primary) from {len(specs)} specs")

    if not args.dry_run:
        out = [{k: v for k, v in t.items() if k != "_primary"} for t in twins]
        OUT.write_text(json.dumps(out, indent=4) + "\n")
        split = {
            "base": [t["id"] for t in twins],
            "primary": [t["id"] for t in twins if t["_primary"]],
        }
        OUT.with_name("split_tasks_twins.json").write_text(
            json.dumps(split, indent=4) + "\n"
        )
        print(f"wrote {OUT} and split_tasks_twins.json")


if __name__ == "__main__":
    main()
