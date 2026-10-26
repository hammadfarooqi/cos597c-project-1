"""Record the generator parameters of every WorkBench task (COS597C, M2).

The upstream generators are seeded (random.seed(42), np.random.seed(42)), so running
them again in memory gives the same tasks. We wrap the per-task step to keep the
logic function's output (its parameters), intercept the CSV write, and check that
every regenerated task, template and outcome equals the committed task file.

Run from code/workbench/:  uv run python ../workbench-m2/capture_params.py
Writes code/workbench-m2/data/task_params.jsonl (one line per task, file order).
"""

import ast
import importlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
sys.path.insert(0, "scripts/data_generation/task_outcome_generation")
import src.data_generation.data_generation_utils as u  # noqa: E402

OUT = Path(__file__).resolve().parent / "data" / "task_params.jsonl"
MODULES = {
    "email": "generate_email_task_and_outcome",
    "calendar": "generate_calendar_task_and_outcome",
    "analytics": "generate_analytics_task_and_outcome",
    "project_management": "generate_project_management_task_and_outcome",
    "customer_relationship_manager": "generate_customer_relationship_manager_task_and_outcome",
    "multi_domain": "generate_multi_domain_task_and_outcome",
}

_orig_one = u.generate_task_and_outcome


def _with_params(template):
    # Same as upstream, but keep the logic output. Only the logic call and the
    # random.choice of the wording consume randomness, in the same order.
    logic = template["logic"]()
    possible = [template["task"]] + template["alternative_tasks"]
    chosen = u.random.choice(possible)
    return {
        "task": chosen.format(**logic),
        "outcome": logic["outcome"],
        "base_template": template["task"],
        "chosen_template": chosen,
        "domains": template["domains"],
        "params": {k: v for k, v in logic.items() if k != "outcome"},
    }


captured: dict[str, pd.DataFrame] = {}
u.generate_task_and_outcome = _with_params
u.write_task_outcome_csv = lambda df, path: captured.__setitem__(path, df)


def _jsonable(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    return str(v)


rows, bad = [], 0
for domain, mod_name in MODULES.items():
    mod = importlib.import_module(mod_name)
    mod.generate_task_and_outcome()
    (path, df), = [(p, d) for p, d in captured.items() if domain in p.split("/")[-1]]
    committed = pd.read_csv(path)
    assert len(df) == len(committed), (domain, len(df), len(committed))
    for i, (g, c) in enumerate(zip(df.to_dict("records"), committed.to_dict("records"))):
        same = (g["task"] == c["task"] and g["base_template"] == c["base_template"]
                and g["chosen_template"] == c["chosen_template"]
                and sorted(g["outcome"]) == sorted(ast.literal_eval(c["outcome"])))
        bad += not same
        rows.append({"domain": domain, "row": i, "task_id": f"{domain}-{i:03d}", "task": c["task"],
                     "base_template": c["base_template"], "chosen_template": c["chosen_template"],
                     "outcome": ast.literal_eval(c["outcome"]), "domains": ast.literal_eval(c["domains"]),
                     "params": _jsonable(g["params"]),
                     "regenerated_matches": same})
    print(f"{domain}: {len(df)} tasks, mismatches so far {bad}")
OUT.parent.mkdir(exist_ok=True)
OUT.write_text("".join(json.dumps(r) + "\n" for r in rows))
print(f"wrote {len(rows)} rows to {OUT}; mismatches {bad}")
