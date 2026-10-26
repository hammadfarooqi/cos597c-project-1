"""Run one model on WorkBench task files through Prime Intellect (COS597C, M2).

Run from code/workbench/:
    uv run python ../workbench-m2/run.py --model gpt-6-luna --run original_seed300 \
        [--tasks data/processed/tasks_and_outcomes/email_tasks_and_outcomes.csv ...]

Without --tasks it runs all six upstream task files (690 tasks). Results go to
runs/<run>/<domain>/<model>_all_<timestamp>.csv (+ _meta.json, _traces.json), under
code/workbench-m2/. Settings are WorkBench Revisited's (all tools, native tool calls,
act without confirmation) at temperature 0, as in our tau2 runs. The key is read
from code/tau2-bench/.env in Python and never written to disk or to the command line.
"""

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# PI_ENV_FILE overrides the path (e.g. when running from a git worktree, which has no .env).
ENV_FILE = Path(os.environ.get("PI_ENV_FILE", HERE.parent / "tau2-bench" / ".env"))
UPSTREAM_TASKS = [
    f"data/processed/tasks_and_outcomes/{d}_tasks_and_outcomes.csv"
    for d in ("email", "calendar", "analytics", "project_management", "customer_relationship_manager", "multi_domain")
]


def load_key() -> None:
    for line in ENV_FILE.read_text().splitlines():
        key, _, value = line.partition("=")
        if key.strip() in ("PI_KEY", "PI_API_BASE"):
            os.environ[key.strip()] = value.strip().strip("'\"")
    for k in ("PI_KEY", "PI_API_BASE"):
        if not os.environ.get(k):
            sys.exit(f"{k} not found in {ENV_FILE}")
    os.environ["WORKBENCH_ROUTE"] = "prime"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--run", required=True, help="run folder name, e.g. original_seed300")
    ap.add_argument("--tasks", nargs="*", default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    load_key()
    sys.path.insert(0, os.getcwd())
    from src.evals.inference import generate_results

    for tasks_path in args.tasks or UPSTREAM_TASKS:
        print(f"=== {args.model} {args.run} {tasks_path}", flush=True)
        generate_results(
            tasks_path,
            args.model,
            "all",
            workers=args.workers,
            log_traces=True,
            act_without_confirmation=True,
            structured_outputs=True,
            resume=args.resume,
            save_dir=str(HERE / "runs" / args.run),
        )


if __name__ == "__main__":
    main()
