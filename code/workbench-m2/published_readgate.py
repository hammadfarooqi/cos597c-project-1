"""The read gate on WorkBench's published runs (COS597C, M2). No model calls.

WorkBench publishes every tool call of 24 models from 2026 (WorkBench Revisited) and of
the 2024 paper models (data/results/item_level_results.csv.gz). We apply the read gate
(twins/readgate.py) to their no-op passes. Twins cannot be scored here: these models
never ran on our twins.

Run from code/workbench/:  uv run python ../workbench-m2/published_readgate.py [--out FILE]
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "twins"))
sys.path.insert(0, ".")

from readgate import is_read, revealing_reads  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    db = pd.read_csv(HERE / "data" / "twins_db_tasks_and_outcomes.csv")
    patch = {r.orig_task_id: json.loads(r.state_patch) for r in db.itertuples()}
    df = pd.read_csv("data/results/item_level_results.csv.gz")
    df = df[df.run_group.isin(["revisited_2026", "original_2024"])].copy()
    df["noop"] = df.ground_truth_actions.apply(lambda s: len(ast.literal_eval(s)) == 0)
    df["pred"] = df.predicted_actions.fillna("[]").apply(lambda s: ast.literal_eval(s) if s.startswith("[") else [])
    rows = []
    for (grp, model, ts), g in df.groupby(["run_group", "model", "tool_selection"]):
        n = g[g.noop]
        p = n[n.correct]
        gated = p[p.task_id.isin(patch)]
        kept = sum(bool(revealing_reads(r.pred, patch[r.task_id])) for r in gated.itertuples())
        no_read = sum(not any(map(is_read, r.pred)) for r in p.itertuples())
        removed = len(gated) - kept
        total = int(g.correct.sum())
        rows.append({"group": grp, "model": model + ("" if grp == "revisited_2026" else f" ({ts})"),
                     "score": total, "noop_pass": len(p), "no_read_at_all": no_read,
                     "removed_by_read_gate": removed, "after_gate": total - removed,
                     "change_pct": round(-100 * removed / total, 1) if total else 0.0,
                     "action_acc": round(100 * g[~g.noop].correct.mean(), 1),
                     "noop_acc": round(100 * len(p) / len(n), 1)})
    out = pd.DataFrame(rows).sort_values(["group", "score"], ascending=[False, False])
    lines = ["| Run | Model | Score (690) | No-op passes | No read at all | Removed by read gate | After gate | Change | Action-task acc % | No-op acc % |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in out.itertuples():
        lines.append(f"| {r.group} | {r.model} | {r.score} | {r.noop_pass} | {r.no_read_at_all} | {r.removed_by_read_gate} | "
                     f"{r.after_gate} | {r.change_pct:+.1f}% | {r.action_acc} | {r.noop_acc} |")
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        Path(args.out).write_text(text)


if __name__ == "__main__":
    main()
