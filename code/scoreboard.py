"""Build the central scoreboard: every model, every scoring method, one table.

Methods (decisions log, 2026-10-03 and 2026-10-08):
  original      upstream tau2 reward
  reads         a no-action pass in justification.json counts only if every
                required read was made (the reward gate)
  twins         a no-action pass with a twin counts only if the same agent also
                passes the twin (strict pair rule); "lenient" also accepts a twin
                where the agent made the right write despite other errors
  reads+twins   both checks

The scoreboard is computed from saved trajectories only. It makes no LLM calls
and replays no environment: the read check is applied to the saved messages with
the same core logic as the evaluator (justification_core.py), and the upstream
reward is taken from the results file (original_reward if the run was gated,
else reward).

A model is included when both runs exist:
  data/simulations/airline_<model>/results.json         (all 50 tasks)
  data/simulations/airline_twins*_<model>/results.json  (DB and policy twins)
With several trials, a task's score is its mean over trials, and trial k of a
task is paired with trial k of its twin.

There is one scoreboard per model set (MODEL_SETS): the older models of the first
round, and the newer models the TA asked for (decisions log, 2026-10-10). The null
agent is in both as the baseline. Each set is written to its own file and never
mixed with the other.

Usage (from code/tau2-bench/):
  uv run python ../scoreboard.py               # rewrite every set's scoreboard
  uv run python ../scoreboard.py --set new     # one set only
  uv run python ../scoreboard.py --check       # exit 1 if any file is out of date
"""

import collections
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "twins"))

from score_pairs import AIRLINE, SIM, failure_cause  # noqa: E402

from tau2.evaluator.justification_core import (  # noqa: E402
    ObservedCall,
    check_task,
    parse_spec,
)

REPO = Path(__file__).resolve().parents[1]
RESEARCH = REPO / "docs" / "research"
# Each set: its output file, a title, a note for the header, and its models in the
# order of their run folders. The null agent is added to every set as the baseline.
MODEL_SETS = {
    "old": {
        "out": RESEARCH / "scoreboard.md",
        "title": "Scoreboard — older models",
        "about": "The five models of the first round (findings-log §7), released 2024–2025.",
        "models": [
            "claude-sonnet-4.5",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "llama-3.3-70b",
        ],
    },
    "new": {
        "out": RESEARCH / "new-models" / "scoreboard.md",
        "title": "Scoreboard — newer models",
        "about": "Four smaller, newer models (findings-log §15–§17). llama-4-maverick ran with "
        "the tool-call retry of findings-log §16; 18% of its turns needed it.",
        "models": [
            "claude-haiku-4.5",
            "gpt-6-luna",
            "gpt-5.4-nano",
            "llama-4-maverick",
        ],
    },
}
BASELINE = "do_nothing"
# The two dated header lines; ignored when checking whether a file is current.
DATED = r"(?m)^(updated: |\*\*Last updated:\*\* )\d{4}-\d{2}-\d{2}"
# The tasks the null agent passes (docs/research/findings-log.md §1).
NO_ACTION = [
    0,
    1,
    2,
    4,
    5,
    6,
    9,
    10,
    13,
    26,
    27,
    28,
    31,
    34,
    36,
    38,
    41,
    43,
    45,
    46,
    47,
    48,
    49,
]
LABELS = {"do_nothing": "null agent"}
METHODS = ["original", "reads", "twins", "twins_lenient", "reads+twins"]


def load_all(path: Path) -> dict:
    """task id -> {trial: simulation}."""
    sims = collections.defaultdict(dict)
    for s in json.loads(path.read_text())["simulations"]:
        sims[str(s["task_id"])][s.get("trial") or 0] = s
    return sims


def upstream_pass(sim: dict) -> bool:
    ri = sim["reward_info"]
    reward = ri.get("original_reward")
    return (ri["reward"] if reward is None else reward) == 1.0


def agent_calls(sim: dict) -> list[ObservedCall]:
    """Same extraction as evaluator_justification._calls_from_messages."""
    msgs = sim.get("messages") or []
    failed = {
        m["id"] for m in msgs if m["role"] == "tool" and m.get("error") and m.get("id")
    }
    return [
        ObservedCall(c["name"], dict(c["arguments"]), c["id"] not in failed)
        for m in msgs
        if m["role"] == "assistant" and m.get("tool_calls")
        for c in m["tool_calls"]
    ]


def twin_map() -> tuple[dict, dict, dict]:
    """task id -> primary twin id, twin id -> kind, twin id -> gold write."""
    split = json.loads((AIRLINE / "split_tasks_twins.json").read_text())
    twins = json.loads((AIRLINE / "tasks_twins.json").read_text())
    kinds = {t: "DB" for t in split["primary"]}
    for name, ids in split.items():
        if name.startswith("pf_"):
            kinds |= {t: "policy" for t in ids}
    of = {t.split("_")[0]: t for t in kinds}
    gold = {t["id"]: t["evaluation_criteria"]["actions"][-1] for t in twins}
    return of, kinds, gold


def models(set_name: str) -> list[str]:
    """The set's models plus the null agent. Every run must exist."""
    found = MODEL_SETS[set_name]["models"] + [BASELINE]
    for m in found:
        for run in [f"airline_{m}", f"airline_twins_{m}"]:
            if not (SIM / run / "results.json").exists():
                sys.exit(f"missing run {run} for set {set_name}")
    return found


def score_model(m: str, spec: dict, twin_of: dict, gold: dict) -> dict:
    """Per task: {method: mean pass over trials}, plus the per-task verdict code."""
    base = load_all(SIM / f"airline_{m}" / "results.json")
    twin = collections.defaultdict(dict)
    for d in sorted(SIM.glob(f"airline_twins*_{m}")):
        for tid, trials in load_all(d / "results.json").items():
            twin[tid] |= trials
    out = {}
    for tid, trials in base.items():
        per = collections.defaultdict(list)
        for k, sim in trials.items():
            orig = upstream_pass(sim)
            reads = orig and (
                tid not in spec or check_task(spec[tid], agent_calls(sim)).justified
            )
            if tid in twin_of:
                t = twin[twin_of[tid]].get(k)
                if t is None:
                    sys.exit(
                        f"{m}: no trial {k} of twin {twin_of[tid]}; pair trials must match"
                    )
                tw = upstream_pass(t)
                tw_len = (
                    tw
                    or failure_cause(t, gold[twin_of[tid]])
                    == "right write + other error"
                )
            else:
                tw = tw_len = True
            for name, v in zip(
                METHODS, [orig, reads, orig and tw, orig and tw_len, reads and tw]
            ):
                per[name].append(v)
        out[tid] = {name: sum(v) / len(v) for name, v in per.items()} | {
            "n": len(trials)
        }
    return out


def fmt(x: float, n: int) -> str:
    s = f"{x:g}" if x == int(x) else f"{x:.2f}"
    return f"{s} ({100 * x / n:.0f}%)"


def verdict(row: dict) -> str:
    """One mark per task: why a no-action pass was kept or removed."""
    if row["original"] == 0:
        return "·"
    lost_r, lost_t = row["reads"] < row["original"], row["twins"] < row["original"]
    return {
        (False, False): "✓",
        (True, False): "R",
        (False, True): "T",
        (True, True): "RT",
    }[(lost_r, lost_t)]


def ranks(totals: dict, method: str) -> dict:
    order = sorted(totals, key=lambda m: -totals[m][method])
    return {
        m: 1 + sum(totals[o][method] > totals[m][method] for o in order) for m in order
    }


def build(set_name: str) -> str:
    spec = parse_spec(json.loads((AIRLINE / "justification.json").read_text()))
    twin_of, kinds, gold = twin_map()
    ms = models(set_name)
    scores = {m: score_model(m, spec, twin_of, gold) for m in ms}
    ms.sort(key=lambda m: -sum(r["original"] for r in scores[m].values()))
    name = {m: LABELS.get(m, m) for m in ms}
    na = {str(t) for t in NO_ACTION}

    def totals(subset=None):
        return {
            m: {
                k: sum(
                    r[k] for t, r in scores[m].items() if subset is None or t in subset
                )
                for k in METHODS
            }
            for m in ms
        }

    tot_all, tot_na = totals(), totals(na)
    rk = {k: ranks(tot_all, k) for k in METHODS}
    n_tasks = {m: len(scores[m]) for m in ms}
    trials = {m: max(r["n"] for r in scores[m].values()) for m in ms}

    reads_t = sorted((int(t) for t in spec), key=int)
    db_t = sorted(int(t) for t, tw in twin_of.items() if kinds[tw] == "DB")
    pf_t = sorted(int(t) for t, tw in twin_of.items() if kinds[tw] == "policy")
    covered = set(reads_t) | set(db_t) | set(pf_t)

    L = []
    L.append("## 1. Full airline score (all 50 tasks)\n")
    L.append("Passes, with the share of tasks and the rank (#) under each method.\n")
    L.append(
        "| Model | Trials | Original | Reads | Twins | Twins (lenient) | **Reads + twins** | Change |"
    )
    L.append("|---|---|---|---|---|---|---|---|")
    for m in ms:
        n, t = n_tasks[m], tot_all[m]
        cells = [f"{fmt(t[k], n)} #{rk[k][m]}" for k in METHODS]
        cells[-1] = f"**{cells[-1]}**"
        diff = t["reads+twins"] - t["original"]
        L.append(
            f"| {name[m]} | {trials[m]} | " + " | ".join(cells) + f" | {diff:+g} |"
        )
    L.append("")
    L.append("## 2. The 23 no-action tasks only\n")
    L.append(
        "The other 27 tasks are scored the same under every method, so all change comes from here.\n"
    )
    L.append(
        "| Model | Original | Reads | Twins | Twins (lenient) | **Reads + twins** |"
    )
    L.append("|---|---|---|---|---|---|")
    for m in ms:
        t = tot_na[m]
        cells = [fmt(t[k], len(NO_ACTION)) for k in METHODS]
        cells[-1] = f"**{cells[-1]}**"
        L.append(f"| {name[m]} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("## 3. Per task: why each no-action pass was kept or removed\n")
    L.append(
        "`✓` kept by both checks · `R` removed by the read check · `T` removed by the twin · "
        "`RT` removed by both · `·` failed under upstream scoring. With several trials, a mark "
        "shows a loss in at least one trial.\n"
    )
    L.append("| Task | Checks | " + " | ".join(name[m] for m in ms) + " |")
    L.append("|---|---|" + "---|" * len(ms))
    for t in NO_ACTION:
        checks = (
            ", ".join(
                c
                for c, ok in [
                    ("reads", t in reads_t),
                    ("DB twin", t in db_t),
                    ("policy twin", t in pf_t),
                ]
                if ok
            )
            or "none"
        )
        L.append(
            f"| {t} | {checks} | "
            + " | ".join(verdict(scores[m][str(t)]) for m in ms)
            + " |"
        )
    L.append("")
    L.append("## 4. Coverage of the 23 no-action tasks\n")
    L.append("| Check | Tasks | Count |")
    L.append("|---|---|---|")
    for label, ts in [
        ("Read check (`justification.json`)", reads_t),
        ("DB-flip twin", db_t),
        ("Policy-flip twin", pf_t),
        (
            "Both a read check and a twin",
            sorted(set(reads_t) & (set(db_t) | set(pf_t))),
        ),
        ("No check", sorted(set(NO_ACTION) - covered)),
    ]:
        L.append(f"| {label} | {', '.join(map(str, ts)) or '—'} | {len(ts)} |")
    L.append("")
    L.append("## 5. Runs used\n")
    for m in ms:
        twin_dirs = ", ".join(
            f"`{d.name}`" for d in sorted(SIM.glob(f"airline_twins*_{m}"))
        )
        L.append(f"- **{name[m]}:** `airline_{m}` · {twin_dirs}")
    return "\n".join(L) + "\n"


HEADER = """---
title: {title}
type: research
status: current
updated: {date}
summary: >-
  {about} Each model under every scoring method (original, reads, twins, reads + twins).
  Generated by code/scoreboard.py from the saved runs. Do not edit by hand.
note: >-
  Generated file. Change the runs or the specs, then rerun code/scoreboard.py. The other model
  set has its own scoreboard ({other}); the two are not mixed.
---

# {title} — airline, all scoring methods

**Last updated:** {date} (generated)

**Models:** {about} The null agent is the baseline.

**Generated by `code/scoreboard.py`. Do not edit by hand.** From `code/tau2-bench/`:
`uv run python ../scoreboard.py`. No LLM calls; it reads the saved runs in
`code/tau2-bench/data/simulations/`.

**Methods** (rules: `docs/decisions/decisions-log.md`, 2026-10-03):

- **Original:** the upstream tau2 reward.
- **Reads:** a no-action pass counts only if the agent made every required read
  (`docs/research/justification-check.md`).
- **Twins:** a no-action pass counts only if the agent also passes its twin
  (`docs/research/counterfactual-twins.md`). **Lenient:** the twin also counts when the agent
  made the right write despite other errors.
- **Reads + twins:** both checks. This is the headline score.

A task with no check of a kind passes that check by default. The 27 action tasks are scored the
same under every method.

"""


def write(set_name: str, check: bool) -> bool:
    """Write one set's scoreboard. Returns False if --check finds it stale."""
    cfg = MODEL_SETS[set_name]
    out = cfg["out"]
    other = ", ".join(
        f"`{c['out'].relative_to(REPO)}`"
        for n, c in MODEL_SETS.items()
        if n != set_name
    )

    def text(date: str) -> str:
        return HEADER.format(
            date=date, title=cfg["title"], about=cfg["about"], other=other
        ) + build(set_name)

    old = out.read_text() if out.exists() else ""
    if re.sub(DATED, r"\1DATE", old) == text("DATE"):
        print(f"{out.relative_to(REPO)} is up to date.")
        return True
    if check:
        print(
            f"{out.relative_to(REPO)} is out of date. Run: uv run python ../scoreboard.py"
        )
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text(datetime.date.today().isoformat()))
    print(f"Wrote {out.relative_to(REPO)}.")
    return True


def main():
    sets = list(MODEL_SETS)
    if "--set" in sys.argv:
        sets = [sys.argv[sys.argv.index("--set") + 1]]
    ok = [write(s, "--check" in sys.argv) for s in sets]
    if not all(ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
