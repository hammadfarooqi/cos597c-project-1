"""Score WorkBench runs under the original rule, the read gate and the twins (COS597C, M2).

Same method as our tau2 newer-model scoring (code/twins/score_pairs.py,
code/twins/average_trials.py, code/scoreboard.py; findings-log §20–§23):

- Original: WorkBench's own scorer (src/evals/evaluation.py::is_correct), all 690 tasks.
- Read gate: a no-op pass counts only if the agent made a read whose output differs
  between the start state and the DB twin's start state (twins/readgate.py).
- Twins: a no-op pass counts only if, IN THE SAME TRIAL, the agent also passes the task's
  DB twin and (if the task has one) its request twin. Strict rule: the upstream scorer
  on the twin's start state. Lenient rule: also accept a twin when every gold write was
  made, despite other differences (as in tau2, decisions log 2026-10-03).
- "Reads + twins": all gates together. This is the headline score.

Run from code/workbench/:
    uv run python ../workbench-m2/score.py [--seeds 300 301 302] [--out ../../docs/...md]
It also writes code/workbench-m2/data/episodes.jsonl (one line per episode) for review.
"""

from __future__ import annotations

import argparse
import ast
import glob
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "twins"))
sys.path.insert(0, ".")

from readgate import is_read, is_write, parse_call, revealing_reads  # noqa: E402
from src.evals.evaluation import accept_either_chart_end_date, is_correct  # noqa: E402
from src.tools.state import set_state_patch  # noqa: E402

MODELS = ["gpt-6-luna", "claude-haiku-4.5", "gpt-5.4-nano", "llama-4-maverick"]
# Prime Intellect list prices, USD per million tokens (input, output), read from
# GET /models on 2026-10-22.
PRICES = {
    "claude-haiku-4.5": (1.0, 5.0),
    "gpt-5.4-nano": (0.2, 1.25),
    "gpt-6-luna": (0.1, 0.5),
    "llama-4-maverick": (0.35, 1.15),
}
DOMAINS = ["email", "calendar", "analytics", "project_management", "customer_relationship_manager", "multi_domain"]
TASKS_DIR = Path("data/processed/tasks_and_outcomes")
DATA = HERE / "data"
RUNS = HERE / "runs"


def load_original_tasks() -> list[dict]:
    out = []
    for d in DOMAINS:
        df = pd.read_csv(TASKS_DIR / f"{d}_tasks_and_outcomes.csv")
        for i, r in enumerate(df.itertuples()):
            out.append({"task_id": f"{d}-{i:03d}", "domain": d, "task": r.task, "gold": ast.literal_eval(r.outcome),
                        "base_template": r.base_template, "patch": None, "file_domain": d, "row": i})
    return out


def load_twin_tasks(kind: str) -> list[dict]:
    path = DATA / f"twins_{kind}_tasks_and_outcomes.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    return [{"task_id": r.twin_id, "orig_task_id": r.orig_task_id, "task": r.task, "gold": ast.literal_eval(r.outcome),
             "base_template": r.base_template, "why": r.why,
             "patch": json.loads(r.state_patch) if isinstance(r.state_patch, str) and r.state_patch.strip() else None,
             "file_domain": f"twins_{kind}", "row": i} for i, r in enumerate(df.itertuples())]


def load_run(run: str, model: str, file_domain: str, tasks: list[dict]) -> list[dict] | None:
    # Raw .csv (local) or its tracked .csv.gz copy (compact_traces.py writes both copies).
    files = sorted(glob.glob(str(RUNS / run / file_domain / f"{model}_all_*.csv")))
    if not files:
        files = sorted(glob.glob(str(RUNS / run / file_domain / f"{model}_all_*.csv.gz")))
    if not files:
        return None
    meta = Path(files[-1].replace(".csv.gz", ".csv").replace(".csv", "_meta.json"))
    task_file = TASKS_DIR / f"{file_domain}_tasks_and_outcomes.csv" if not file_domain.startswith("twins_") \
        else DATA / f"{file_domain}_tasks_and_outcomes.csv"
    if meta.exists():
        recorded = json.loads(meta.read_text()).get("tasks_sha256")
        current = hashlib.sha256(task_file.read_bytes()).hexdigest()
        if recorded and recorded != current:
            raise ValueError(f"{files[-1]}: the task file changed after this run ({task_file})")
        if not recorded and file_domain.startswith("twins_"):
            raise ValueError(f"{files[-1]}: twin run without a task-file hash")
    df = pd.read_csv(files[-1], dtype=str).fillna("")
    if len(df) != len(tasks) or any(a != b["task"] for a, b in zip(df["task"], tasks)):
        raise ValueError(f"{files[-1]}: rows do not match the task file ({len(df)} vs {len(tasks)})")
    rows = []
    for r, t in zip(df.to_dict("records"), tasks):
        calls = ast.literal_eval(r["function_calls"]) if r["function_calls"].startswith("[") else []
        rows.append({**r, "calls": calls, "prompt_tokens": int(float(r.get("prompt_tokens") or 0)),
                     "completion_tokens": int(float(r.get("completion_tokens") or 0)),
                     "empty_tool_retries": int(float(r.get("empty_tool_retries") or 0))})
    return rows


def correct(calls: list[str], gold: list[str], error: str, patch) -> bool:
    set_state_patch(patch)
    try:
        return is_correct(calls, gold, error)
    finally:
        set_state_patch(None)


def canon(action: str):
    """A write call as (tool, sorted lower-cased kwargs), so argument order does not matter."""
    action = accept_either_chart_end_date([action])[0]
    parsed = parse_call(action)
    if parsed is None:
        return action.lower()
    name, kwargs = parsed
    return name, tuple(sorted((k, str(v).lower()) for k, v in kwargs.items()))


def lenient(calls: list[str], gold: list[str], error: str, patch, strict: bool) -> bool:
    """tau2's lenient rule: every gold write was made, despite other differences."""
    if strict:
        return True
    if error or not gold:
        return False
    made = {canon(c) for c in calls if is_write(c)}
    return all(canon(g) in made for g in gold)


def failure_cause(calls: list[str], gold: list[str], error: str, strict: bool, lenient_ok: bool) -> str:
    if strict:
        return "pass"
    if error:
        return "error: " + error[:50]
    writes = [c for c in calls if is_write(c)]
    if not writes:
        return "no write"
    if lenient_ok:
        return "right write + other difference"
    return "wrong write"


TEXT_CALL = re.compile(r"\b(email|calendar|analytics|project_management|customer_relationship_manager|company_directory)[._]\w+\s*\(")


def text_form_call(full_response: str) -> bool:
    """A tool call typed into the final answer instead of called (tau2 M1.25 analogue)."""
    m = re.search(r"output=(['\"])(.*?)\1, intermediate_steps", full_response, re.S)
    return bool(m and TEXT_CALL.search(m.group(2)))


def pass_hat_k(c: int, n: int, k: int) -> float:
    return math.comb(c, k) / math.comb(n, k) if n >= k else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", nargs="+", type=int, default=[300, 301, 302])
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-missing-twins", action="store_true",
                    help="score trials whose twin runs are missing; their twin columns are then not meaningful")
    args = ap.parse_args()

    orig = load_original_tasks()
    by_domain = defaultdict(list)
    for t in orig:
        by_domain[t["file_domain"]].append(t)
    db = load_twin_tasks("db")
    req = load_twin_tasks("request")
    db_by_orig = {t["orig_task_id"]: t for t in db}
    # Patches of excluded DB twins still define the read gate (build.py EXCLUDE_DB).
    gate_patch = {t["orig_task_id"]: t["patch"] for t in db + load_twin_tasks("db_gate_only")}
    # A request twin may serve several originals ("a;b"), or be an existing benchmark task
    # whose original episode is reused (twins_request_reuse.json).
    req_by_orig = {o: t for t in req for o in t["orig_task_id"].split(";")}
    reuse_path = DATA / "twins_request_reuse.json"
    req_reuse = json.loads(reuse_path.read_text()) if reuse_path.exists() else {}
    noop_ids = [t["task_id"] for t in orig if not t["gold"]]

    episodes = []
    results = {}  # (model, seed) -> dict
    for model in args.models + ["null agent"]:
        for seed in args.seeds if model != "null agent" else [0]:
            ep = {}
            missing = []
            for kind, tasks_by_file in (("original", by_domain), ("db", {"twins_db": db}), ("request", {"twins_request": req})):
                for fd, tasks in tasks_by_file.items():
                    if not tasks:
                        continue
                    if model == "null agent":
                        rows = [{"calls": [], "error": "", "full_response": "", "prompt_tokens": 0,
                                 "completion_tokens": 0, "empty_tool_retries": 0} for _ in tasks]
                    else:
                        run = f"{'original' if kind == 'original' else kind + 'twin'}_seed{seed}"
                        rows = load_run(run, model, fd, tasks)
                        if rows is None:
                            missing.append(f"{run}/{fd}")
                            continue
                    for t, r in zip(tasks, rows):
                        s = correct(r["calls"], t["gold"], r["error"], t["patch"])
                        l_ok = lenient(r["calls"], t["gold"], r["error"], t["patch"], s)
                        e = {"model": model, "seed": seed, "kind": kind, "task_id": t["task_id"],
                             "orig_task_id": t.get("orig_task_id", t["task_id"]), "base_template": t["base_template"],
                             "task": t["task"], "gold": t["gold"], "calls": r["calls"], "error": r["error"],
                             "pass": s, "pass_lenient": l_ok,
                             "cause": failure_cause(r["calls"], t["gold"], r["error"], s, l_ok),
                             "n_reads": sum(map(is_read, r["calls"])), "n_writes": sum(map(is_write, r["calls"])),
                             "text_form_call": text_form_call(r.get("full_response", "")),
                             "empty_tool_retries": r["empty_tool_retries"],
                             "cost": (r["prompt_tokens"] * PRICES.get(model, (0, 0))[0]
                                      + r["completion_tokens"] * PRICES.get(model, (0, 0))[1]) / 1e6}
                        if kind == "request":
                            for o in t["orig_task_id"].split(";"):
                                ep[("request", o)] = e
                        if kind == "original" and not t["gold"] and t["task_id"] in gate_patch:
                            rr = revealing_reads(r["calls"], gate_patch[t["task_id"]])
                            e["revealing_reads"] = rr
                            e["read_gate"] = bool(rr)
                        ep[(kind, e["orig_task_id"])] = e
                        episodes.append(e)
            if model != "null agent" and missing:
                print(f"{model} seed {seed}: missing {missing}")
                if any(m.startswith("original") for m in missing):
                    continue
                if not args.allow_missing_twins:
                    print(f"  -> trial skipped: twin runs missing (use --allow-missing-twins to score originals only)")
                    continue
                ep["_twins_missing"] = True
            for o, src in req_reuse.items():  # request twin = an original task of this trial
                if ("original", src) in ep:
                    ep[("request", o)] = {**ep[("original", src)], "kind": "request", "reused_original": src}
            results[(model, seed)] = ep

    # ---- per trial
    lines = ["---", "title: WorkBench Scoreboard — Newer Models", "type: research", "status: current",
             f"updated: {pd.Timestamp.now().date()}", "summary: >-",
             "  Generated by code/workbench-m2/score.py. Scores of the 4 newer models over 3 trials under the",
             "  original rule, the read gate and the twins; pass^k, stability, behaviour, twin failure causes.",
             "---", "", "# WorkBench Scoreboard — Newer Models", "",
             "Generated by `code/workbench-m2/score.py`. Do not edit by hand.", ""]
    trial_rows = []
    for (model, seed), ep in results.items():
        twins_missing = bool(ep.pop("_twins_missing", False))
        orig_eps = [e for (k, _), e in ep.items() if k == "original"]
        if len(orig_eps) != len(orig):
            continue
        noop = [ep[("original", i)] for i in noop_ids]
        noop_pass = [e for e in noop if e["pass"]]
        removed_reads, removed_db, removed_req, removed_all, removed_all_len, removed_all_act = [], [], [], [], [], []
        for e in noop_pass:
            i = e["task_id"]
            # No DB twin (not flippable): the read gate does not apply, as for tau2 tasks 6, 13, 46.
            rg = e.get("read_gate", False) if i in gate_patch else True
            dbe, rqe = ep.get(("db", i)), ep.get(("request", i))
            # A task without a DB-twin run yet is not removed by the twin (reported as missing).
            db_ok = dbe["pass"] if dbe else True
            db_ok_l = dbe["pass_lenient"] if dbe else True
            rq_ok = rqe["pass"] if rqe else True
            rq_ok_l = rqe["pass_lenient"] if rqe else True
            e["kept"] = {"reads": rg, "db": db_ok, "request": rq_ok if rqe else None}
            if not rg:
                removed_reads.append(i)
            if dbe and not db_ok:
                removed_db.append(i)
            if rqe and not rq_ok:
                removed_req.append(i)
            if not (rg and db_ok and rq_ok):
                removed_all.append(i)
            if not (rg and db_ok_l and rq_ok_l):
                removed_all_len.append(i)
            # Sensitivity ("acted" rule, not the headline): a twin counts if the agent made any
            # write, i.e. it acted on the flipped fact even if a detail was wrong.
            acted = lambda x: x is None or x["pass"] or x["cause"] in ("wrong write", "right write + other difference")
            if not (rg and acted(dbe) and acted(rqe)):
                removed_all_act.append(i)
        n_orig = sum(e["pass"] for e in orig_eps)
        cost = sum(e["cost"] for e in ep.values())
        trial_rows.append({
            "model": model, "seed": seed, "twins_missing": twins_missing, "original": n_orig, "reads": n_orig - len(removed_reads),
            "db_pairs": sum(1 for e in noop_pass if ep.get(("db", e["task_id"])) and ep[("db", e["task_id"])]["pass"]),
            "req_pairs": sum(1 for e in noop_pass if ep.get(("request", e["task_id"])) and ep[("request", e["task_id"])]["pass"]),
            "all": n_orig - len(removed_all), "all_lenient": n_orig - len(removed_all_len),
            "all_acted": n_orig - len(removed_all_act),
            "noop_pass": len(noop_pass), "action_pass": n_orig - len(noop_pass),
            "removed_reads": removed_reads, "removed_db": removed_db, "removed_req": removed_req,
            "removed_all": removed_all, "cost": cost,
            "errors": sum(1 for e in orig_eps if e["error"]),
            "retries": sum(e["empty_tool_retries"] for e in ep.values()),
            "db_twins_passed": sum(e["pass"] for (k, _), e in ep.items() if k == "db"),
            "req_twins_passed": sum(e["pass"] for (k, _), e in ep.items() if k == "request"),
        })
    n_req = len(req)
    lines += ["## 1. Per trial", "",
              f"690 tasks; {len(noop_ids)} no-op tasks; {len(db)} DB twins; {n_req} request twins.", "",
              "Scores are out of 690. \"DB pairs\" and \"Request pairs\" count no-op tasks passed together with their twin.",
              "\"Twins missing\" marks a trial scored without its twin runs: its twin columns are not meaningful.", "",
              "| Model | Seed | Original | Reads gate | DB pairs | Request pairs | **Reads + twins** | Lenient | No-op passes | Errors | Lost-call retries | Cost $ | Twins missing |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in trial_rows:
        lines.append(f"| {r['model']} | {r['seed'] or '—'} | {r['original']} | {r['reads']} | {r['db_pairs']} | {r['req_pairs']} | "
                     f"**{r['all']}** | {r['all_lenient']} | {r['noop_pass']} | {r['errors']} | {r['retries']} | {r['cost']:.2f} | {'YES' if r['twins_missing'] else ''} |")

    # ---- means
    lines += ["", "## 2. Mean over trials (min–max)", "",
              "\"Acted\" is a sensitivity rule, not the headline: a twin counts if the agent made any write.", "",
              "| Model | Trials | Original | Reads gate | DB pairs | Request pairs | **Reads + twins** | Lenient | Acted | No-op passes | Reads change | **All gates change** | Cost, all trials |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    by_model = defaultdict(list)
    for r in trial_rows:
        by_model[r["model"]].append(r)

    def mm(rs, k):
        v = [r[k] for r in rs]
        return f"{sum(v)/len(v):.1f} ({min(v)}–{max(v)})"
    for model, rs in by_model.items():
        o = sum(r["original"] for r in rs) / len(rs)
        rd = sum(r["reads"] for r in rs) / len(rs)
        al = sum(r["all"] for r in rs) / len(rs)
        lines.append(f"| {model} | {len(rs)} | {mm(rs,'original')} | {mm(rs,'reads')} | {mm(rs,'db_pairs')} | {mm(rs,'req_pairs')} | "
                     f"**{mm(rs,'all')}** | {mm(rs,'all_lenient')} | {mm(rs,'all_acted')} | {mm(rs,'noop_pass')} | {100*(rd-o)/o:+.1f}% | **{100*(al-o)/o:+.1f}%** | "
                     f"${sum(r['cost'] for r in rs):.2f} |")

    # ---- pass^k
    lines += ["", "## 3. pass^k over the trials (sum over tasks of C(c,k)/C(n,k))", "",
              "| Model | Original pass^1 → pass^k | Reads + twins pass^1 → pass^k | No-op tasks, reads + twins, pass^1 → pass^k |",
              "|---|---|---|---|"]
    for model, rs in by_model.items():
        n = len(rs)
        seeds = [r["seed"] for r in rs]
        rem = {r["seed"]: set(r["removed_all"]) for r in rs}
        po = defaultdict(int)
        pa = defaultdict(int)
        for s in seeds:
            ep = results[(model, s)]
            for t in orig:
                e = ep[("original", t["task_id"])]
                po[t["task_id"]] += e["pass"]
                pa[t["task_id"]] += e["pass"] and t["task_id"] not in rem[s]
        def ph(cnt, ids, k):
            return sum(pass_hat_k(cnt[i], n, k) for i in ids)
        all_ids = [t["task_id"] for t in orig]
        lines.append(f"| {model} | {ph(po, all_ids, 1):.1f} → {ph(po, all_ids, n):.0f} | {ph(pa, all_ids, 1):.1f} → {ph(pa, all_ids, n):.0f} | "
                     f"{ph(pa, noop_ids, 1):.1f} → {ph(pa, noop_ids, n):.0f} |")

    # ---- stability of removals
    lines += ["", "## 4. Stability of removals (no-op tasks passed upstream in at least one trial)", "",
              "| Model | Tasks | Removed in every trial it passed | Removed in some trials | Never removed | Removal events |",
              "|---|---|---|---|---|---|"]
    for model, rs in by_model.items():
        passed = defaultdict(int)
        removed = defaultdict(int)
        for r in rs:
            ep = results[(model, r["seed"])]
            for i in noop_ids:
                if ep[("original", i)]["pass"]:
                    passed[i] += 1
                    removed[i] += i in r["removed_all"]
        always = [i for i in passed if removed[i] == passed[i]]
        some = [i for i in passed if 0 < removed[i] < passed[i]]
        never = [i for i in passed if removed[i] == 0]
        lines.append(f"| {model} | {len(passed)} | {len(always)} | {len(some)} | {len(never)} | {sum(removed.values())} |")

    # ---- behaviour counts
    lines += ["", "## 5. Behaviour on no-op tasks (all trials)", "",
              "| Model | No-op episodes | Passes | Passes with no read at all | Gated passes with no revealing read | Passes with a write attempted | Text-form calls (all episodes) | Errors (all original episodes) |",
              "|---|---|---|---|---|---|---|---|"]
    for model, rs in by_model.items():
        ne = [results[(model, r["seed"])][("original", i)] for r in rs for i in noop_ids]
        ps = [e for e in ne if e["pass"]]
        allo = [e for r in rs for (k, _), e in results[(model, r["seed"])].items() if k == "original"]
        lines.append(f"| {model} | {len(ne)} | {len(ps)} | {sum(e['n_reads'] == 0 for e in ps)} | "
                     f"{sum(('read_gate' in e) and not e['read_gate'] for e in ps)} | {sum(e['n_writes'] > 0 for e in ps)} | "
                     f"{sum(e['text_form_call'] for e in allo)} | {sum(bool(e['error']) for e in allo)} |")

    # ---- twin failure causes
    lines += ["", "## 6. Why twins failed (all trials; twins of no-op tasks the model passed in that trial)", "",
              "| Model | Twin | Failures | No write | Wrong write | Right write + other difference | Error |", "|---|---|---|---|---|---|---|"]
    for model, rs in by_model.items():
        for kind in ("db", "request"):
            causes = defaultdict(int)
            for r in rs:
                ep = results[(model, r["seed"])]
                for i in noop_ids:
                    if ep[("original", i)]["pass"] and (kind, i) in ep and not ep[(kind, i)]["pass"]:
                        c = ep[(kind, i)]["cause"]
                        causes["error" if c.startswith("error") else c] += 1
            tot = sum(causes.values())
            lines.append(f"| {model} | {kind} | {tot} | {causes['no write']} | {causes['wrong write']} | "
                         f"{causes['right write + other difference']} | {causes['error']} |")

    # ---- per-task removal marks
    lines += ["", "## 7. Per no-op task: passes and removals over trials", "",
              "Cell: `passes/trials`, then the gates that removed it (R = reads, D = DB twin, Q = request twin) with counts.", "",
              "| Task | Template | " + " | ".join(by_model) + " |", "|---|---|" + "---|" * len(by_model)]
    tmpl = {t["task_id"]: t["base_template"] for t in orig}
    for i in noop_ids:
        cells = []
        for model, rs in by_model.items():
            p = sum(results[(model, r["seed"])][("original", i)]["pass"] for r in rs)
            marks = []
            for g, key in (("R", "removed_reads"), ("D", "removed_db"), ("Q", "removed_req")):
                c = sum(i in r[key] for r in rs)
                if c:
                    marks.append(f"{g}{c}")
            cells.append(f"{p}/{len(rs)}" + (" " + " ".join(marks) if marks else ""))
        lines.append(f"| {i} | {tmpl[i][:50]} | " + " | ".join(cells) + " |")

    # ---- control: twin pass rate vs the template's own action tasks
    lines += ["", "## 8. Control: twin pass rate vs the same template's action tasks (all trials)", "",
              "If a model fails twins about as often as it fails the template's ordinary action tasks, twin failures",
              "reflect general difficulty (rubric Q2 b/c), not the no-op decision. Cells: pass % (episodes).", "",
              "| Template | Model | Action tasks | DB twins | Request twins |", "|---|---|---|---|---|"]
    noop_templates = sorted({t["base_template"] for t in orig if not t["gold"]})
    for base in noop_templates:
        for model, rs in by_model.items():
            cells = []
            for kind in ("original", "db", "request"):
                es = [e for r in rs for (k, _), e in results[(model, r["seed"])].items()
                      if k == kind and e["base_template"] == base and (kind != "original" or e["gold"])]
                es = list({id(e): e for e in es}.values())
                cells.append(f"{100 * sum(e['pass'] for e in es) / len(es):.0f}% ({len(es)})" if es else "—")
            lines.append(f"| {base[:55]} | {model} | " + " | ".join(cells) + " |")

    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        Path(args.out).write_text(text)
    (DATA / "episodes.jsonl").write_text("".join(json.dumps(e, default=str) + "\n" for e in episodes))
    (DATA / "trial_summary.json").write_text(json.dumps(trial_rows, indent=1, default=str))


if __name__ == "__main__":
    main()
