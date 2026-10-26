"""List WebArena-Verified's failure-status tasks and the page visit each one requires.

A failure-status task expects the agent to report that the task cannot be done
(NOT_FOUND_ERROR, ACTION_NOT_ALLOWED_ERROR, PERMISSION_DENIED_ERROR). Some of them
also have a NetworkEventEvaluator: the agent must have visited the page that holds the
deciding data. That is our read gate (docs/research/other-benchmarks/webarena-verified.md).
For each task, the script also prints how the original WebArena graded it.

Reads the two datasets that ship in the package. No sites, no model calls, no key:

    uvx --python 3.12 --with webarena-verified==1.2.3 python code/webarena-verified/failure_task_checks.py
"""

import json
from collections import Counter
from importlib.resources import files

DATASET = files("webarena_verified") / "assets" / "dataset"


def main() -> None:
    verified = json.loads((DATASET / "webarena-verified.json").read_text())
    original = {t["task_id"]: t for t in json.loads((DATASET / "test.raw.json").read_text())}

    failures = []
    for task in verified:
        status, visits = None, []
        for check in task["eval"]:
            if check["evaluator"] == "AgentResponseEvaluator":
                status = check["expected"].get("status")
            elif check["evaluator"] == "NetworkEventEvaluator":
                visits.append(check["expected"]["url"])
        if status and status != "SUCCESS":
            failures.append((task, status, visits))

    print(f"{len(verified)} tasks, {len(failures)} expect a failure status:")
    for status, n in Counter(s for _, s, _ in failures).most_common():
        print(f"  {status}: {n}")

    gated = [f for f in failures if f[2]]
    print(f"\n{len(gated)} of {len(failures)} also require a page visit:")
    for task, status, visits in gated:
        old = original[task["task_id"]]["eval"]
        print(f"  {task['task_id']:>4}  {status:<25} visit {', '.join(visits)}")
        print(f"        start {', '.join(task['start_urls'])} | {task['intent'][:80]}")
        print(f"        original WebArena: {old['eval_types']} {json.dumps(old['reference_answers'])}")

    ungated = [t["task_id"] for t, _, visits in failures if not visits]
    print(f"\n{len(ungated)} need the status only: {ungated}")


if __name__ == "__main__":
    main()
