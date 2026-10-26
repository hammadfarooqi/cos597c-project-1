"""Validate the template specs and build the WorkBench twin task files (COS597C, M2).

Run from code/workbench/:  uv run python ../workbench-m2/twins/build.py [--write]

Checks, per template and per no-op task (all must pass before --write):
  G1  gold(p, start state) equals the official outcome for EVERY task of the template
      (no-op and action tasks alike), compared as WorkBench compares: lower-cased,
      order-free. This proves the spec's rule is the benchmark's rule.
  D1  the DB patch applies, and its size (rows touched) is reported.
  D2  the DB twin's gold is not empty, and it runs cleanly on the patched state.
  D3  on the patched state, the upstream scorer rejects the empty action list (doing
      nothing fails the twin), and EVERY gold action, run alone, changes the state (no
      phantom action such as deleting an id that does not exist).
  D5  the read gate is satisfiable in practice: we replay the reads that five strong
      published 2026 runs made on this task and count how many reveal the flip.
  R1  (request twins) the new text differs from the original in exactly one slot, the
      gold on the unchanged state is not empty, runs cleanly, and is accepted by the
      upstream scorer while the empty list is rejected.

--write writes data/twins_db_tasks_and_outcomes.csv and data/twins_request_tasks_and_outcomes.csv (WorkBench task-file
format plus state_patch, orig_task_id and why) and data/twins_report.json.
"""

from __future__ import annotations

import argparse
import ast
import csv
import importlib
import json
import string
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, ".")

import framework as fw  # noqa: E402
from readgate import revealing_reads  # noqa: E402
from src.evals.actions import EXECUTED_STATE_FIELDS, execute_actions_and_reset_state  # noqa: E402
from src.evals.evaluation import is_correct  # noqa: E402
from src.tools.state import set_state_patch  # noqa: E402

SPEC_MODULES = ["specs_analytics", "specs_calendar_email", "specs_pm_crm"]
STRONG_MODELS = ["claude-fable-5", "claude-opus-4.8", "gemini-3.1-pro", "gpt-5.5", "claude-sonnet-4.6"]
ITEM_LEVEL = Path("data/results/item_level_results.csv.gz")


def correct_on(patch, predicted, gold) -> bool:
    set_state_patch(patch)
    try:
        return is_correct(predicted, gold, "")
    finally:
        set_state_patch(None)


def runs_cleanly(patch, actions) -> bool:
    set_state_patch(patch)
    try:
        ok, _ = execute_actions_and_reset_state(actions)
        return ok
    finally:
        set_state_patch(None)


def each_action_changes_state(patch, actions) -> bool:
    """True if every action, run alone on the (patched) start state, changes some table."""
    _, base = execute_actions_with(patch, [])
    for a in actions:
        _, after = execute_actions_with(patch, [a])
        if all(after[n].equals(base[n]) for n in EXECUTED_STATE_FIELDS):
            return False
    return True


def execute_actions_with(patch, actions):
    set_state_patch(patch)
    try:
        return execute_actions_and_reset_state(actions)
    finally:
        set_state_patch(None)


def rows_touched(patch) -> int:
    return len(patch)


def slots(template: str) -> list[str]:
    """Distinct slots of a template (a slot used twice is still one slot)."""
    return sorted({f for _, f, _, _ in string.Formatter().parse(template) if f})


# Twins excluded after the adversarial reviews (2026-10-22). An excluded DB twin keeps its
# patch for the read gate (the deciding fact is still where the patch puts it), but it is
# not run and not used as a pair. An excluded request twin is dropped.
EXCLUDE_REQUEST: dict[str, str] = {
    "analytics-096": "the text does not say 'percent'; by percent the action is right, by count it is not",
    "multi_domain-143": "gold deletes 7 leads but search_customers shows at most 5; strong models fail this "
                        "template's action tasks for that reason, unrelated to the decision",
}
EXCLUDE_DB: dict[str, str] = {
    "multi_domain-143": "gold deletes 7 leads but search_customers shows at most 5 (see EXCLUDE_REQUEST)",
    "analytics-096": "the text does not say 'percent'; by percent the action is right, by count it is not",
}
# Excluded with NO read gate: the original no-op follows from the system prompt alone.
EXCLUDE_DB_NO_GATE: dict[str, str] = {
    "calendar-073": "'before 9' on a work day: the system prompt says meetings must not start before 9am, "
                    "so no meeting can be cancelled whatever the data; the only flip needs an 08:00 meeting",
}

# Hidden parameters that are a fixed function of a visible slot: they must change with it.
DERIVED = {"time": "natural_language_time"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--only", default=None, help="substring of base templates to check")
    args = ap.parse_args()

    for m in SPEC_MODULES:
        try:
            importlib.import_module(m)
        except ModuleNotFoundError as e:
            if e.name != m:
                raise
            print(f"(spec module {m} not written yet)")
        except Exception as e:  # another group may be mid-edit; only --write must see all
            if args.write:
                raise
            print(f"(spec module {m} failed to import, skipped: {e!r})")
    tasks = fw.load_tasks()
    noop_templates = {t["base_template"] for t in tasks if not t["outcome"]}
    missing = sorted(noop_templates - set(fw.SPECS))
    extra = sorted(set(fw.SPECS) - noop_templates)
    print(f"no-op templates: {len(noop_templates)}; specs: {len(fw.SPECS)}; missing {len(missing)}; extra {len(extra)}")
    for m in extra:
        print("  EXTRA (not a no-op template):", m)

    item = pd.read_csv(ITEM_LEVEL)
    item = item[(item.run_group == "revisited_2026") & item.model.isin(STRONG_MODELS)]
    strong_actions = {
        (r.task_id, r.model): ast.literal_eval(r.predicted_actions) if isinstance(r.predicted_actions, str) and r.predicted_actions.startswith("[") else []
        for r in item.itertuples()
    }

    start = fw.state_with(None)
    failures: list[str] = []
    db_rows, req_rows, report = [], [], []
    for base, spec in sorted(fw.SPECS.items()):
        if args.only and args.only not in base:
            continue
        group = [t for t in tasks if t["base_template"] == base]
        # G1
        g1_bad = []
        for t in group:
            try:
                got = spec.gold(t["params"], start.copy())
            except Exception as e:
                got = [f"<exception {e!r}>"]
            if fw.norm(got) != fw.norm(t["outcome"]):
                g1_bad.append((t["task_id"], fw.norm(got)[:3], fw.norm(t["outcome"])[:3]))
        if g1_bad:
            failures.append(f"G1 {base[:60]}: {len(g1_bad)}/{len(group)} tasks differ, e.g. {g1_bad[0]}")
        for t in [t for t in group if not t["outcome"]]:
            tid, p = t["task_id"], t["params"]
            entry = {"task_id": tid, "base_template": base, "task": t["task"]}
            # D1–D4
            try:
                patch, why = spec.db_flip(p, start.copy())
                twin_state = fw.state_with(patch)
                twin_gold = spec.gold(p, twin_state)
            except Exception as e:
                if str(e).startswith("not flippable"):
                    # No data change can flip this task (e.g. growth from a day to itself).
                    # It gets no DB twin and so no read gate, like tau2 tasks 6, 13, 46.
                    entry["db"] = f"not flippable: {e}"
                    patch = None
                else:
                    failures.append(f"D1 {tid}: {e!r}")
                    report.append({**entry, "db": f"exception {e!r}"})
                    continue
            if patch is not None:
                d = {
                    "rows_touched": rows_touched(patch),
                    "gold": twin_gold,
                    "why": why,
                    "D2_nonempty": bool(twin_gold),
                    "D2_clean": runs_cleanly(patch, twin_gold),
                    "D3_no_phantom": each_action_changes_state(patch, twin_gold),
                    "D3_null_fails": not correct_on(patch, [], twin_gold),
                }
                reveal = sum(
                    bool(revealing_reads(strong_actions.get((tid, m), []), patch)) for m in STRONG_MODELS
                )
                d["D5_strong_reveal"] = f"{reveal}/{len(STRONG_MODELS)}"
                for k in ("D2_nonempty", "D2_clean", "D3_no_phantom", "D3_null_fails"):
                    if not d[k]:
                        failures.append(f"{k} {tid}")
                if reveal == 0:
                    failures.append(f"D5 {tid}: no strong model's reads reveal the flip")
                entry["db"] = d
                db_rows.append({
                    "task": t["task"], "outcome": twin_gold, "base_template": base,
                    "chosen_template": t["chosen_template"], "domains": str(t.get("domains") or ""),
                    "state_patch": json.dumps(patch), "orig_task_id": tid, "twin_id": f"{tid}_db", "why": why,
                })
            # R1
            if spec.request_flip is not None:
                rf = spec.request_flip(p, start.copy())
                if rf is not None:
                    new_p, rwhy = rf
                    new_text = t["chosen_template"].format(**new_p)
                    changed = [k for k in slots(t["chosen_template"]) if str(new_p.get(k)) != str(p.get(k))]
                    # Hidden parameters (not in the text) must not change either.
                    changed_any = {k for k in set(p) | set(new_p) if str(p.get(k)) != str(new_p.get(k))}
                    changed_any -= {k for k, v in DERIVED.items() if v in changed}
                    rgold = spec.gold(new_p, start.copy())
                    r = {
                        "text": new_text, "changed_slots": changed, "gold": rgold, "why": rwhy,
                        "R1_one_slot": len(changed) == 1 and changed_any == set(changed),
                        "R1_nonempty": bool(rgold),
                        "R1_clean": runs_cleanly(None, rgold),
                        "R1_no_phantom": each_action_changes_state(None, rgold),
                        "R1_null_fails": not correct_on(None, [], rgold),
                    }
                    for k in ("R1_one_slot", "R1_nonempty", "R1_clean", "R1_no_phantom", "R1_null_fails"):
                        if not r[k]:
                            failures.append(f"{k} {tid}")
                    entry["request"] = r
                    req_rows.append({
                        "task": new_text, "outcome": rgold, "base_template": base,
                        "chosen_template": t["chosen_template"], "domains": str(t.get("domains") or ""),
                        "state_patch": "", "orig_task_id": tid, "twin_id": f"{tid}_req", "why": rwhy,
                    })
            report.append(entry)

    n_noop = sum(1 for t in tasks if not t["outcome"] and (not args.only or args.only in t["base_template"]))
    print(f"DB twins built: {len(db_rows)} / {n_noop} no-op tasks; request twins: {len(req_rows)}")
    print(f"failures: {len(failures)}")
    for f in failures[:80]:
        print("  ", f)
    if missing and not args.only:
        print("missing specs:")
        for m in missing:
            print("  ", m)
    if args.write:
        if failures or (missing and not args.only):
            sys.exit("not writing: fix the failures and missing specs first")
        gate_only = [dict(r, excluded_because=EXCLUDE_DB[r["orig_task_id"]]) for r in db_rows if r["orig_task_id"] in EXCLUDE_DB]
        db_rows = [r for r in db_rows if r["orig_task_id"] not in EXCLUDE_DB and r["orig_task_id"] not in EXCLUDE_DB_NO_GATE]
        req_rows = [r for r in req_rows if r["orig_task_id"] not in EXCLUDE_REQUEST]
        print(f"excluded: {len(gate_only)} DB twins (kept for the read gate), {len(EXCLUDE_DB_NO_GATE)} with no gate, "
              f"{len(EXCLUDE_REQUEST)} request twins")
        # A request twin whose text is an existing benchmark task reuses that task's episode
        # (same trial); two request twins with the same text share one episode.
        orig_text = {t["task"]: t["task_id"] for t in tasks}
        reuse = {}
        merged: dict[str, dict] = {}
        for r in req_rows:
            if r["task"] in orig_text:
                assert fw.norm(r["outcome"]) == fw.norm(next(t["outcome"] for t in tasks if t["task_id"] == orig_text[r["task"]]))
                reuse[r["orig_task_id"]] = orig_text[r["task"]]
            elif r["task"] in merged:
                assert fw.norm(merged[r["task"]]["outcome"]) == fw.norm(r["outcome"])
                merged[r["task"]]["orig_task_id"] += ";" + r["orig_task_id"]
            else:
                merged[r["task"]] = dict(r)
        req_rows = list(merged.values())
        (fw.M2 / "data" / "twins_request_reuse.json").write_text(json.dumps(reuse, indent=1))
        print(f"request twins: {len(req_rows)} to run, {len(reuse)} reuse an original task: {reuse}")
        for name, rows in (("db", db_rows), ("request", req_rows)):
            texts = [r["task"] for r in rows]
            if len(texts) != len(set(texts)):
                # Runs and resume match rows by text; duplicates are allowed only for the DB
                # twins of tasks whose text repeats upstream (none do), so stop here.
                sys.exit(f"duplicate task texts in the {name} twins")
        out = fw.M2 / "data"
        for name, rows in (("twins_db", db_rows), ("twins_request", req_rows), ("twins_db_gate_only", gate_only)):
            if not rows:
                (out / f"{name}_tasks_and_outcomes.csv").unlink(missing_ok=True)
                continue
            df = pd.DataFrame(rows)
            df["outcome"] = df["outcome"].apply(str)
            df.to_csv(out / f"{name}_tasks_and_outcomes.csv", index=False, quoting=csv.QUOTE_ALL)
        (out / "twins_report.json").write_text(json.dumps(report, indent=1))
        print("written to", out)


if __name__ == "__main__":
    main()
