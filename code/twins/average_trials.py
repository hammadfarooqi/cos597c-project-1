"""Average the airline + twin scores of one model over several trials.

A trial is one set of three runs with the same config and seed:
airline_<run>, airline_twins_<run> and airline_twins_pf_<run>, where <run> is
the model name for trial 1 (seed 300) and <model>_seed<N> for later trials.
Each trial is scored with the pair rule of score_pairs.py, then the trials are
averaged per model.

Usage (from code/tau2-bench/):
  uv run python ../twins/average_trials.py gpt-6-luna:300,301,302 ...

Seed 300 maps to the run without a suffix (the trial 1 folders).
"""

import json
import statistics
import sys

from score_pairs import (
    AIRLINE,
    SIM,
    failure_cause,
    load,
    passed,
    tool_calls,
    twin_runs,
)

# USD per million tokens (in, out): the Prime list prices used in findings §15, §17.
PRICES = {
    "claude-haiku-4.5": (1.00, 5.00),
    "gpt-6-luna": (0.10, 0.50),
    "gpt-5.4-nano": (0.20, 1.25),
    "llama-4-maverick": (0.35, 1.15),
}
USER_PRICE = (2.00, 8.00)  # user simulator openai/gpt-4.1
COLUMNS = [
    "Original (50)",
    "Reads gate",
    "DB pairs (11)",
    "Policy pairs (4)",
    "Reads gate + twins",
    "+ twins, lenient",
    "No-action (23)",
    "Transfers on no-action",
    "Cost $",
]


def run_name(model: str, seed: int) -> str:
    return model if seed == 300 else f"{model}_seed{seed}"


def cost(sims: list[dict], model: str) -> float:
    total = 0.0
    for s in sims:
        for m in s["messages"]:
            u = m.get("usage") or {}
            price = {"assistant": PRICES[model], "user": USER_PRICE}.get(m["role"])
            if price and u:
                total += (
                    u.get("prompt_tokens", 0) * price[0]
                    + u.get("completion_tokens", 0) * price[1]
                ) / 1e6
    return total


def score_trial(
    model: str, run: str, no_action: set[str], kinds: dict, gold: dict
) -> dict:
    orig = load(SIM / f"airline_{run}" / "results.json")
    twin = twin_runs(run)
    paired = {"DB": 0, "policy": 0}
    removed = lenient_removed = 0
    for tid, kind in kinds.items():
        o, t = passed(orig[tid.split("_")[0]]), passed(twin[tid])
        paired[kind] += o and t
        removed += o and not t
        # Lenient rule (decisions log 2026-10-03): the twin also counts if the
        # agent made the right write despite other errors.
        right_write = not t and (
            failure_cause(twin[tid], gold[tid]) == "right write + other error"
        )
        lenient_removed += o and not t and not right_write
    gate = sum(passed(s) for s in orig.values())
    return {
        "Original (50)": sum(
            s["reward_info"]["original_reward"] == 1.0 for s in orig.values()
        ),
        "Reads gate": gate,
        "DB pairs (11)": paired["DB"],
        "Policy pairs (4)": paired["policy"],
        "Reads gate + twins": gate - removed,
        "+ twins, lenient": gate - lenient_removed,
        "No-action (23)": sum(
            orig[t]["reward_info"]["original_reward"] == 1.0 for t in no_action
        ),
        "Transfers on no-action": sum(
            any(c["name"] == "transfer_to_human_agents" for c in tool_calls(orig[t]))
            for t in no_action
        ),
        "Cost $": cost(list(orig.values()) + list(twin.values()), model),
    }


def main(specs: list[str]):
    split = json.loads((AIRLINE / "split_tasks_twins.json").read_text())
    twins = json.loads((AIRLINE / "tasks_twins.json").read_text())
    gold = {t["id"]: t["evaluation_criteria"]["actions"][-1] for t in twins}
    kinds = {tid: "DB" for tid in split["primary"]}
    for name, ids in split.items():
        if name.startswith("pf_"):
            kinds |= {tid: "policy" for tid in ids}
    null = load(SIM / "airline_do_nothing" / "results.json")
    no_action = {t for t, s in null.items() if passed(s)}
    assert len(no_action) == 23, len(no_action)

    results = {}
    for spec in specs:
        model, seeds = spec.split(":")
        results[model] = {
            int(seed): score_trial(
                model, run_name(model, int(seed)), no_action, kinds, gold
            )
            for seed in seeds.split(",")
        }

    print("### Per trial (seed)\n")
    print("| Model | Seed | " + " | ".join(COLUMNS) + " |")
    print("|---" * (len(COLUMNS) + 2) + "|")
    for model, trials in results.items():
        for seed, r in trials.items():
            cells = [f"{r[c]:.2f}" if c == "Cost $" else str(r[c]) for c in COLUMNS]
            print(f"| {model} | {seed} | " + " | ".join(cells) + " |")

    print("\n### Mean over trials (min–max)\n")
    print("| Model | Trials | " + " | ".join(COLUMNS) + " |")
    print("|---" * (len(COLUMNS) + 2) + "|")
    for model, trials in results.items():
        cells = []
        for c in COLUMNS:
            v = [r[c] for r in trials.values()]
            if c == "Cost $":
                cells.append(f"{sum(v):.2f} total")
            else:
                cells.append(f"{statistics.mean(v):.1f} ({min(v)}–{max(v)})")
        print(f"| {model} | {len(trials)} | " + " | ".join(cells) + " |")

    print("\n### Change from the original score (mean over trials)\n")
    print(
        "| Model | Original | Reads gate | Reads gate + twins | + twins, lenient | "
        "Gate change | Gate + twins change | Lenient change |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for model, trials in results.items():
        o, g, t, lt = (
            statistics.mean(r[c] for r in trials.values())
            for c in (
                "Original (50)",
                "Reads gate",
                "Reads gate + twins",
                "+ twins, lenient",
            )
        )
        print(
            f"| {model} | {o:.1f} | {g:.1f} | {t:.1f} | {lt:.1f} | "
            f"{100 * (g - o) / o:+.1f}% | **{100 * (t - o) / o:+.1f}%** | "
            f"{100 * (lt - o) / o:+.1f}% |"
        )


if __name__ == "__main__":
    main(sys.argv[1:])
