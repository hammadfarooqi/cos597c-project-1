"""Score each no-action task together with its counterfactual twin.

Pair rule (decisions log, 2026-10-03): a no-action pass counts only if the
same agent also passes the twin. A twin pass with a failed no-action task is
a failure. Twin failures are labelled by cause, so a blanket refusal can be
told apart from a bad write.

Usage (from code/tau2-bench/):
  uv run python ../twins/score_pairs.py claude-sonnet-4.5 gpt-4.1 ...

Reads data/simulations/airline_<model>/results.json (the no-action runs) and
every data/simulations/airline_twins*_<model>/results.json (the twin runs:
DB flips, and one folder per policy flip).
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


def twin_runs(model: str) -> dict:
    """All twin episodes of one model, from every airline_twins*_<model> run.

    DB-flip twins run under --domain airline (airline_twins_<model>); each
    policy flip runs under its own domain (airline_twins_pf_<model>).
    """
    sims = {}
    for d in sorted(SIM.glob(f"airline_twins*_{model}")):
        sims |= load(d / "results.json")
    return sims


def main(models: list[str]):
    twins = json.loads((AIRLINE / "tasks_twins.json").read_text())
    split = json.loads((AIRLINE / "split_tasks_twins.json").read_text())
    # One primary twin per task: DB flips, then each policy flip.
    kinds = {tid: "DB" for tid in split["primary"]}
    for name, ids in split.items():
        if name.startswith("pf_"):
            kinds |= {tid: "policy" for tid in ids}
    pairs = list(kinds)
    gold = {t["id"]: t["evaluation_criteria"]["actions"][-1] for t in twins}
    print(
        f"{len(pairs)} twins: "
        + ", ".join(f"{t.split('_')[0]} ({kinds[t]})" for t in pairs)
        + "\n"
    )

    per_task, totals = {}, {}
    for m in models:
        orig = load(SIM / f"airline_{m}" / "results.json")
        twin = twin_runs(m)
        per_task[m] = []
        for tid in pairs:
            base = tid.split("_")[0]
            o, t = passed(orig[base]), passed(twin[tid])
            cause = "" if t else failure_cause(twin[tid], gold[tid])
            per_task[m].append((tid, o, t, cause))
        totals[m] = sum(passed(s) for s in orig.values()), len(orig)

    for subset in ("DB", "policy", "all"):
        ids = [t for t in pairs if subset == "all" or kinds[t] == subset]
        n = len(ids)
        print(f"### {subset} twins ({n})\n")
        print(
            "| Model | No-op passes | Twin passes | Paired (both) | No-op only | "
            "Twin only | Neither | Twin failure causes |"
        )
        print("|---|---|---|---|---|---|---|---|")
        for m in models:
            rows = [r for r in per_task[m] if r[0] in ids]
            cells = collections.Counter((o, t) for _, o, t, _ in rows)
            causes = collections.Counter(c for *_, c in rows if c)
            print(
                f"| {m} | {cells[(1, 1)] + cells[(1, 0)]}/{n} | "
                f"{cells[(1, 1)] + cells[(0, 1)]}/{n} | **{cells[(1, 1)]}** | "
                f"{cells[(1, 0)]} | {cells[(0, 1)]} | {cells[(0, 0)]} | "
                f"{', '.join(f'{k} {v}' for k, v in causes.items())} |"
            )
        print()

    print("### Full airline score, no-action verdicts replaced by paired verdicts\n")
    print("| Model | Score now | Paired score | Credit removed |")
    print("|---|---|---|---|")
    for m in models:
        removed = sum(1 for _, o, t, _ in per_task[m] if o and not t)
        now, n = totals[m]
        print(f"| {m} | {now}/{n} | **{now - removed}/{n}** | {removed} |")

    print("\n### Per task (no-op/twin, 1 = pass)\n")
    print("| Task | Twin | " + " | ".join(models) + " |")
    print("|---" * (len(models) + 2) + "|")
    for i, tid in enumerate(pairs):
        cells = []
        for m in models:
            _, o, t, cause = per_task[m][i]
            cells.append(f"{int(o)}/{int(t)}" + (f" ({cause})" if cause else ""))
        print(f"| {tid.split('_')[0]} | {kinds[tid]} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main(sys.argv[1:])
