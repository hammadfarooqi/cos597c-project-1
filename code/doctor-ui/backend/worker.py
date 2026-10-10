"""Doctor worker: runs the no-op doctor for one benchmark, in that benchmark's Python.

The UI backend starts one worker per benchmark (for example with
`uv run --project code/tau2-bench python worker.py --doctor code/doctor`), so the backend
never imports the benchmark and each benchmark keeps its own dependencies.

Protocol: one JSON object per line on stdin, `{"id": 1, "op": "...", "args": {...}}`.
The worker answers on stdout with `{"id": 1, "ok": true, "result": ...}` or
`{"id": 1, "ok": false, "error": "..."}`. Long operations also send
`{"id": 1, "progress": [done, total]}` lines before the answer.

This file must import only the standard library and the doctor: it runs inside the
benchmark's environment, where FastAPI is not installed.
"""

from __future__ import annotations

import argparse
import importlib
import io
import json
import math
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path

ADAPTERS = {
    "tau2": "noop_doctor.adapters.tau2:Tau2Adapter",
    "mini_web": "noop_doctor.adapters.mini_web:MiniWebAdapter",
}

# Gold trajectories and states can be big; the UI shows at most this much per value.
MAX_JSON = 4000


class Worker:
    def __init__(self, out):
        self.out = out
        self.ad = None
        self.base_state = None

    # --- protocol ----------------------------------------------------------------------

    def send(self, msg: dict) -> None:
        self.out.write(json.dumps(_clean(msg), default=_jsonable) + "\n")
        self.out.flush()

    def handle(self, req: dict) -> None:
        rid = req.get("id")
        fn = getattr(self, "op_" + str(req.get("op")), None)
        if fn is None:
            self.send({"id": rid, "ok": False, "error": f"unknown op {req.get('op')}"})
            return
        try:
            # The benchmark may print; keep stdout for the protocol.
            with redirect_stdout(io.StringIO()):
                result = fn(rid=rid, **(req.get("args") or {}))
            self.send({"id": rid, "ok": True, "result": result})
        except Exception as e:  # report every failure to the UI
            self.send(
                {
                    "id": rid,
                    "ok": False,
                    "error": f"{type(e).__name__}: {e}",
                    "trace": traceback.format_exc()[-3000:],
                }
            )

    def need(self):
        if self.ad is None:
            raise RuntimeError("no adapter: call init first")
        return self.ad

    # --- operations --------------------------------------------------------------------

    def op_init(self, rid, adapter: str, kwargs: dict | None = None):
        """`adapter` is `<builtin>:<arg>` or `py:<module>:<Class>:<arg>`, as in doctor.py."""
        _quiet_loguru()
        from noop_doctor.adapters.base import STEP_NEEDS, missing_methods

        kind, _, arg = adapter.partition(":")
        if kind == "py":
            module, cls, arg = (arg.split(":", 2) + ["", ""])[:3]
        elif kind in ADAPTERS:
            module, cls = ADAPTERS[kind].split(":")
        else:
            raise ValueError(f"unknown adapter '{kind}' (known: {', '.join(ADAPTERS)}, py:...)")
        kw = {k: v for k, v in (kwargs or {}).items() if v is not None}
        self.ad = getattr(importlib.import_module(module), cls)(arg, **kw)
        self.base_state = None
        steps = {s: missing_methods(self.ad, s) for s in STEP_NEEDS}
        try:  # flips need a policy text; an adapter may raise when there is none
            self.ad.policy_text()
            steps["flips"] = []
        except Exception:
            steps["flips"] = ["policy_text"]
        return {
            "name": self.ad.name,
            "missing": steps,
            "tasks": len(self.ad.task_ids()),
            "twin_task_files": hasattr(self.ad, "twin_specs_from_tasks"),
        }

    def op_tools(self, rid):
        """Every tool the adapter knows, with its kind (empty if it cannot list them)."""
        ad = self.need()
        names: list[str] = []
        if callable(getattr(ad, "agent_tools", None)):
            names = list(ad.agent_tools())
        else:
            seen = set()
            for tid in ad.task_ids():
                for c in ad.gold_calls(tid):
                    if c.name not in seen:
                        seen.add(c.name)
                        names.append(c.name)
        return [{"name": n, "kind": ad.tool_kind(n).value} for n in names]

    def op_checkup(self, rid, task_ids: list[str] | None = None):
        from noop_doctor.core import checkup as ck

        ad = self.need()
        ids = task_ids or ad.task_ids()
        rows = []
        for i, tid in enumerate(ids):
            rows += ck.run_checkup(ad, [tid])
            self.send({"id": rid, "progress": [i + 1, len(ids)]})
        return {
            "summary": ck.summarize(rows),
            "tasks": [
                {
                    "task_id": r.task_id,
                    "null_reward": None if math.isnan(r.null_reward) else r.null_reward,
                    "passed": r.passed,
                    "gold_writes": r.gold_writes,
                    "gold_reads": r.gold_reads,
                    "error": r.error,
                }
                for r in rows
            ],
        }

    def op_draft_reads(self, rid, task_ids: list[str], skip_tools: list[str] | None = None):
        from noop_doctor.core.reads import draft_spec

        ad = self.need()
        return draft_spec(task_ids, ad.gold_calls, ad.tool_kind, skip_tools or [])

    def op_task_info(self, rid, task_id: str):
        """What a reviewer needs to judge a proposal: the task text and its gold calls."""
        ad = self.need()
        task = ad.task(task_id)
        raw = _dump(task)
        return {
            "task_id": task_id,
            "summary": _task_summary(raw),
            "raw": _clip(raw),
            "gold": [
                {
                    "name": c.name,
                    "arguments": c.arguments,
                    "kind": ad.tool_kind(c.name).value,
                }
                for c in ad.gold_calls(task_id)
            ],
        }

    def op_twins_from_tasks(self, rid, path: str):
        ad = self.need()
        if not hasattr(ad, "twin_specs_from_tasks"):
            raise ValueError(f"{ad.name} cannot read a twin task file")
        # The twin file keeps the reason in the task description, not in a field.
        purposes = {
            str(t.get("id")): ((t.get("description") or {}).get("purpose") or "")
            for t in json.loads(Path(path).read_text())
        }
        out = []
        for s in ad.twin_specs_from_tasks(Path(path)):
            d = _spec_to_dict(s)
            d["why"] = d["why"] or purposes.get(s.twin_id, "")
            out.append(d)
        return out

    def op_validate_twin(self, rid, spec: dict):
        from noop_doctor.core.state import leaf_diff
        from noop_doctor.core.twins import validate_twin

        ad = self.need()
        s = _spec_from_dict(spec)
        check = validate_twin(ad, s)
        if self.base_state is None:
            self.base_state = ad.state(None)
        diff = []
        if s.patch:
            after = ad.state(s.patch)
            for path in sorted(leaf_diff(self.base_state, after), key=str)[:200]:
                diff.append(
                    {
                        "path": list(path),
                        "before": _clip(_get(self.base_state, path)),
                        "after": _clip(_get(after, path)),
                    }
                )
        return {
            "twin_id": check.twin_id,
            "kind": s.kind,
            "ok": check.ok,
            "failures": check.failures(),
            "fields": check.fields,
            "effective": check.effective,
            "local": check.local,
            "null_orig": check.null_orig,
            "null_twin": check.null_twin,
            "comply_orig": check.comply_orig,
            "comply_twin": check.comply_twin,
            "diff": diff,
        }

    def op_build_twin(self, rid, spec: dict):
        return _dump(self.need().build_twin(_spec_from_dict(spec)))

    def op_policy(self, rid):
        return self.need().policy_text()

    def op_ping(self, rid):
        return "pong"


# --- helpers ------------------------------------------------------------------------------


def _quiet_loguru():
    try:  # tau2 logs at DEBUG to stderr; keep only errors
        from loguru import logger

        logger.remove()
        logger.add(sys.stderr, level="ERROR")
    except ImportError:
        pass


def _spec_from_dict(d: dict):
    from noop_doctor.core.calls import ObservedCall
    from noop_doctor.core.twins import TwinSpec

    w = d["write"]
    return TwinSpec(
        str(d["task"]),
        d["name"],
        ObservedCall(w["name"], dict(w.get("arguments") or {})),
        d.get("patch") or {},
        d.get("why", ""),
        d.get("policy_flip"),
    )


def _spec_to_dict(s) -> dict:
    return {
        "task": s.task_id,
        "name": s.name,
        "patch": s.patch,
        "write": {"name": s.write.name, "arguments": s.write.arguments},
        "why": s.why,
        "policy_flip": s.policy_flip,
    }


def _dump(task):
    if hasattr(task, "model_dump"):
        return task.model_dump(mode="json")
    return task


def _task_summary(raw) -> str:
    """A short text for the reviewer: tau2 user instructions, or a `question` field."""
    if not isinstance(raw, dict):
        return str(raw)[:1500]
    us = raw.get("user_scenario") or {}
    ins = us.get("instructions") if isinstance(us, dict) else None
    if isinstance(ins, dict):
        parts = [
            f"{k.replace('_', ' ').capitalize()}: {v}"
            for k, v in ins.items()
            if v and k in ("reason_for_call", "known_info", "unknown_info", "task_instructions")
        ]
        if parts:
            return "\n\n".join(parts)
    for key in ("question", "intent", "instruction", "prompt", "description"):
        if isinstance(raw.get(key), str):
            return raw[key]
    return ""


def _get(obj, path):
    for p in path:
        if isinstance(obj, dict):
            obj = obj.get(p)
        elif isinstance(obj, list) and isinstance(p, int) and p < len(obj):
            obj = obj[p]
        else:
            return None
    return obj


def _clip(value):
    text = json.dumps(value, default=_jsonable)
    if len(text) <= MAX_JSON:
        return value
    return {"_clipped": text[:MAX_JSON] + " ..."}


def _clean(o):
    """NaN is not JSON; send null instead."""
    if isinstance(o, float) and math.isnan(o):
        return None
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    return o


def _jsonable(o):
    if isinstance(o, float) and math.isnan(o):
        return None
    if hasattr(o, "model_dump"):
        return o.model_dump(mode="json")
    if hasattr(o, "value"):
        return o.value
    return str(o)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--doctor", required=True, help="path of code/doctor")
    p.add_argument("--sys-path", action="append", default=[], help="extra import paths")
    a = p.parse_args()
    for path in [a.doctor, *a.sys_path]:
        sys.path.insert(0, str(Path(path).resolve()))
    out = sys.stdout
    w = Worker(out)
    w.send({"id": None, "ready": True})
    for line in sys.stdin:
        line = line.strip()
        if line:
            w.handle(json.loads(line))


if __name__ == "__main__":
    main()
