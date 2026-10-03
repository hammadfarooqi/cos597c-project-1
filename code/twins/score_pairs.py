"""Score each no-action task together with its counterfactual twin.

Pair rule (decisions log, 2026-10-03): a no-action pass counts only if the
same agent also passes the twin. A twin pass with a failed no-action task is
a failure. Twin failures are labelled by cause, so a blanket refusal can be
told apart from a bad write.

Usage (from code/tau2-bench/):
  uv run python ../twins/score_pairs.py claude-sonnet-4.5 gpt-4.1 ...

Reads data/simulations/airline_<model>/results.json (the no-action runs) and
data/simulations/airline_twins_<model>/results.json (the twin runs).
"""

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "tau2-bench"
SIM = ROOT / "data" / "simulations"
AIRLINE = ROOT / "data" / "tau2" / "domains" / "airline"
WRITES = {
    "book_reservation",
    "cancel_reservation",
    "update_reservation_flights",
    "update_reservation_baggages",
    "update_reservation_passengers",
    "send_certificate",
}


def load(path: Path) -> dict:
    return {s["task_id"]: s for s in json.loads(path.read_text())["simulations"]}


def passed(sim: dict) -> bool:
    return sim["reward_info"]["reward"] == 1.0


def tool_calls(sim: dict) -> list[dict]:
    return [
        c
        for m in sim["messages"]
        if m["role"] == "assistant" and m.get("tool_calls")
        for c in m["tool_calls"]
    ]


def failure_cause(sim: dict, gold: dict) -> str:
    calls = tool_calls(sim)
    if any(
        c["name"] == gold["name"]
        and all(
            str(c["arguments"].get(k)) == str(v) for k, v in gold["arguments"].items()
        )
        for c in calls
    ):
        return "right write + other error"
    if any(c["name"] in WRITES for c in calls):
        return "wrong write"
    if any(c["name"] == "transfer_to_human_agents" for c in calls):
        return "transfer"
    return "no write"


def main(models: list[str]):
    twins = json.loads((AIRLINE / "tasks_twins.json").read_text())
    primary = json.loads((AIRLINE / "split_tasks_twins.json").read_text())["primary"]
    gold = {t["id"]: t["evaluation_criteria"]["actions"][-1] for t in twins}
    n = len(primary)
    print(f"{n} primary twins: {', '.join(t.split('_')[0] for t in primary)}\n")
    print(
        "| Model | No-op passes | Twin passes | Paired (both) | No-op only | "
        "Twin only | Neither | Twin failure causes |"
    )
    print("|---|---|---|---|---|---|---|---|")
    per_task = {}
    for m in models:
        orig = load(SIM / f"airline_{m}" / "results.json")
        twin = load(SIM / f"airline_twins_{m}" / "results.json")
        cells, causes = collections.Counter(), collections.Counter()
        per_task[m] = []
        for tid in primary:
            base = tid.split("_")[0]
            o, t = passed(orig[base]), passed(twin[tid])
            cells[(o, t)] += 1
            cause = "" if t else failure_cause(twin[tid], gold[tid])
            if cause:
                causes[cause] += 1
            per_task[m].append((base, o, t, cause))
        print(
            f"| {m} | {cells[(1, 1)] + cells[(1, 0)]}/{n} | "
            f"{cells[(1, 1)] + cells[(0, 1)]}/{n} | **{cells[(1, 1)]}** | "
            f"{cells[(1, 0)]} | {cells[(0, 1)]} | {cells[(0, 0)]} | "
            f"{', '.join(f'{k} {v}' for k, v in causes.items())} |"
        )
    print("\nPer task (no-op/twin, 1 = pass):\n")
    print("| Task | " + " | ".join(models) + " |")
    print("|---" * (len(models) + 1) + "|")
    for i, tid in enumerate(primary):
        cells = []
        for m in models:
            _, o, t, cause = per_task[m][i]
            cells.append(f"{int(o)}/{int(t)}" + (f" ({cause})" if cause else ""))
        print(f"| {tid.split('_')[0]} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main(sys.argv[1:])
