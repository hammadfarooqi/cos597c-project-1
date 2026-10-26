"""Restore errors that a resume erased (COS597C, M2; one-off repair, kept for the record).

Before the fix of 2026-10-22, _load_existing_progress() rebuilt every kept row with
error "". The resume of llama-4-maverick original_seed301/302 analytics (to retry 3
gateway timeouts) kept the model-error rows and so erased their errors. This script
takes each task's error from the run's log (the first, pre-resume run of that task)
and writes it back into the CSV row. Calls and other columns of those rows are
unchanged (crashed episodes have no calls).
"""
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
for seed in (301, 302):
    log = (HERE / "logs" / f"original_seed{seed}_llama-4-maverick.log").read_text().splitlines()
    # Authoritative signal: the exception handler's "Unexpected error with task: <task>" line
    # (logger.exception), printed once per crashed episode. The message is the last line
    # of the traceback that follows. Worker output can interleave, so we do not rely on the
    # "### Task" / "### Steps" pairing.
    err_by_task = {}
    for i, line in enumerate(log):
        k = line.find("Unexpected error with task: ")
        if k < 0:
            continue
        task = line[k + len("Unexpected error with task: "):]
        msg = "model error (restored from the run log)"
        for nxt in log[i + 1:i + 80]:
            m = re.match(r"^([A-Za-z_.]+(?:Error|Exception)): (.*)$", nxt)
            if m:
                msg = m.group(2)
                break
        err_by_task.setdefault(task, msg)
    (csv_path,) = (HERE / "runs" / f"original_seed{seed}" / "analytics").glob("llama-4-maverick_all_*[0-9].csv")
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    fix = (df.error == "") & df.task.map(lambda t: t in err_by_task) & (df.function_calls == "[]")
    df.loc[fix, "error"] = df.loc[fix, "task"].map(err_by_task)
    print(seed, "restored", int(fix.sum()), "errors;", "rows with error now", int((df.error != "").sum()))
    if "--write" in sys.argv:
        import csv
        df.to_csv(csv_path, index=False, quoting=csv.QUOTE_ALL)
