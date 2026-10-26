"""Write a compact, gzipped copy of every WorkBench trace file (COS597C, M2).

WorkBench's *_traces.json repeat the whole prompt at every step (~40 MB per model and
trial). The compact copy keeps, per step, the action, its input, the observation and the
model's output, which is all the review needs. Raw traces stay local (git-ignored).

Run from anywhere:  python3 code/workbench-m2/compact_traces.py
"""

import gzip
import json
from pathlib import Path

RUNS = Path(__file__).resolve().parent / "runs"
for raw in sorted(RUNS.glob("*/*/*_traces.json")):
    out = raw.with_name(raw.name.replace("_traces.json", "_traces.compact.json.gz"))
    if out.exists() and out.stat().st_mtime >= raw.stat().st_mtime:
        continue
    data = json.loads(raw.read_text())
    compact = [{"task": e["task"], "steps": [{k: s.get(k) for k in ("action", "action_input", "observation", "llm_output")}
                                             for s in e["steps"]]} for e in data]
    with gzip.open(out, "wt") as f:
        json.dump(compact, f)
    print(out.relative_to(RUNS), f"{raw.stat().st_size / 1e6:.1f} MB -> {out.stat().st_size / 1e6:.2f} MB")

# Results CSVs embed the whole trace in full_response; track gzipped copies, as upstream does.
for csv_path in sorted(RUNS.glob("*/*/*_all_*.csv")):
    gz = csv_path.with_name(csv_path.name + ".gz")
    if gz.exists() and gz.stat().st_mtime >= csv_path.stat().st_mtime:
        continue
    with open(csv_path, "rb") as src, gzip.open(gz, "wb") as dst:
        dst.write(src.read())
