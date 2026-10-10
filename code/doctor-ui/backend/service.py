"""What the backend does for one benchmark: run the doctor, turn its output into review
items, validate edits, and export the approved items as the doctor's own spec files.

The benchmark itself is only touched through a worker (`worker.py`) in its own environment.
The doctor's benchmark-free core (`noop_doctor.core`) is imported here directly: it has no
benchmark imports, so it runs in the backend's environment.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from .benchmarks import DOCTOR, Registry
from .store import ReviewStore, now
from .workers import WorkerClient, WorkerError

sys.path.insert(0, str(DOCTOR))
from noop_doctor.core.flips import apply_flip  # noqa: E402
from noop_doctor.core.reads import parse_spec  # noqa: E402


class Job:
    def __init__(self, kind: str):
        self.kind, self.state, self.progress = kind, "running", [0, 0]
        self.message, self.error, self.log = "", "", []
        self.started_at, self.finished_at = now(), None

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class BenchService:
    def __init__(self, registry: Registry, workspace: Path, bench_id: str):
        self.registry, self.workspace, self.id = registry, workspace, bench_id
        self.store = ReviewStore(workspace, bench_id)
        self.worker: WorkerClient | None = None
        self.job: Job | None = None
        self.task_cache: dict[str, dict] = {}
        self._policy: str | None = None

    @property
    def config(self) -> dict:
        return self.registry.get(self.id)

    # --- worker ----------------------------------------------------------------------

    def get_worker(self) -> WorkerClient:
        b = self.config
        if b["status"] == "needs_adapter" or not b.get("adapter"):
            raise ValueError("this benchmark has no adapter yet")
        if b["status"] == "needs_setup":
            raise ValueError("this benchmark's environment is not set up yet")
        if self.worker is None:
            self.worker = WorkerClient(
                b["python"], Path(b["cwd"]), DOCTOR, b["adapter"], b["sys_path"], b["kwargs"]
            )
        return self.worker

    def reset_worker(self) -> None:
        if self.worker:
            self.worker.stop()
        self.worker = None
        self.task_cache.clear()
        self._policy = None

    def policy(self) -> str | None:
        if self._policy is None:
            try:
                self._policy = self.get_worker().call("policy")
            except (WorkerError, ValueError):
                return None
        return self._policy

    # --- jobs ------------------------------------------------------------------------

    def start_job(self, kind: str, fn: Callable[[Job], None]) -> Job:
        if self.job and self.job.state == "running":
            raise ValueError(f"a {self.job.kind} job is already running")
        job = Job(kind)
        self.job = job

        def run():
            try:
                fn(job)
                job.state = "done"
            except Exception as e:
                job.state, job.error = "error", f"{type(e).__name__}: {e}"
                if isinstance(e, WorkerError) and e.trace:
                    job.log.append(e.trace)
                else:
                    job.log.append(traceback.format_exc()[-3000:])
            job.finished_at = now()

        threading.Thread(target=run, daemon=True).start()
        return job

    def run_setup(self, job: Job) -> None:
        b = self.config
        if not b.get("setup"):
            raise ValueError("no setup command for this benchmark")
        job.message = "running " + " ".join(b["setup"])
        proc = subprocess.Popen(
            b["setup"],
            cwd=b["cwd"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:  # type: ignore[union-attr]
            job.log = (job.log + [line.rstrip()])[-200:]
        if proc.wait() != 0:
            raise RuntimeError(f"setup failed (exit {proc.returncode})")
        for other in self.registry.items.values():  # every domain of the same checkout
            if other["cwd"] == b["cwd"] and other["status"] == "needs_setup":
                other["status"] = "ready"
        self.registry.save()
        job.message = "environment ready"

    def run_checkup(self, job: Job) -> None:
        self.reset_worker()
        w = self.get_worker()
        job.message = "starting the benchmark"
        w.call("ping")  # starts the worker, which loads the adapter
        self.store.data["adapter_info"] = w.info
        self.store.data["tools"] = w.call("tools")

        def prog(done, total):
            job.progress, job.message = [done, total], f"checkup: task {done} of {total}"

        result = w.call("checkup", {}, progress=prog)
        result["ran_at"] = now()
        self.store.data["checkup"] = result
        self.store.save()
        job.message = "drafting proposals"
        self.refresh_proposals()
        self.validate_all(job)
        s = result["summary"]
        job.message = f"{s['null_passes']} of {s['tasks']} tasks pass with a do-nothing agent"
        if s["errors"]:
            job.message += f"; {len(s['errors'])} could not be scored"

    def validate_all(self, job: Job, only_missing: bool = False) -> None:
        items = [
            it
            for it in self.store.data["items"].values()
            if not (only_missing and it.get("validation"))
        ]
        for i, it in enumerate(items):
            job.progress = [i + 1, len(items)]
            job.message = f"validating {it['kind']} {it['id']} ({i + 1} of {len(items)})"
            self.validate(it["id"])

    # --- proposals -------------------------------------------------------------------

    def noop_tasks(self) -> list[str]:
        ck = self.store.data.get("checkup")
        return list(ck["summary"]["passed"]) if ck else []

    def refresh_proposals(self) -> None:
        w = self.get_worker()
        src = self.config["sources"]
        noop = self.noop_tasks()

        # Read gate: drafted from gold reads; tasks without gold reads get an empty draft.
        draft = w.call("draft_reads", {"task_ids": noop, "skip_tools": src["skip_tools"]})
        ref = _load_json(src.get("reads_reference"))
        for tid in noop:
            entry = draft.get(tid) or {"required_reads": []}
            extra = {"reference": (ref or {}).get(tid)}
            how = "drafted from the gold trajectory"
            if src["skip_tools"]:
                how += f" (route-only reads left out: {', '.join(src['skip_tools'])})"
            if not entry["required_reads"] and extra["reference"]:
                # No gold reads, but a person already wrote a spec: propose that one.
                entry = {k: v for k, v in extra["reference"].items() if k == "required_reads"}
                how = "from the existing spec (the gold has no reads)"
            elif not entry["required_reads"]:
                how = "gold has no reads: a person must write the requirement"
            self.store.upsert_proposal(
                f"reads:{tid}", "reads", entry, task_id=tid, source=how, extra=extra
            )

        # Twins: from the adapter's twin task files and from doctor YAML specs.
        for path in src["twin_task_files"]:
            for spec in w.call("twins_from_tasks", {"path": path}):
                self._upsert_twin(spec, Path(path).name)
        for path in src["twin_yaml"]:
            for spec in yaml.safe_load(Path(path).read_text()) or []:
                spec["task"] = str(spec["task"])
                spec.setdefault("why", "")
                spec.setdefault("patch", {})
                spec.setdefault("policy_flip", None)
                self._upsert_twin(spec, Path(path).name)

        # Policy flips.
        for path in src["flips_yaml"]:
            for fid, flip in (yaml.safe_load(Path(path).read_text()) or {}).items():
                proposal = {
                    "original": flip["original"],
                    "replacement": flip["replacement"],
                    "extra": {
                        k: v for k, v in flip.items() if k not in ("original", "replacement")
                    },
                }
                self.store.upsert_proposal(
                    f"flip:{fid}", "flip", proposal, task_id=None, source=Path(path).name
                )
        self.store.save()

    def _upsert_twin(self, spec: dict, source: str) -> None:
        tid = f"{spec['task']}_twin_{spec['name']}"
        self.store.upsert_proposal(f"twin:{tid}", "twin", spec, task_id=spec["task"], source=source)

    # --- validation ------------------------------------------------------------------

    def validate(self, item_id: str) -> dict:
        it = self.store.get(item_id)
        fn = {"reads": self._check_reads, "twin": self._check_twin, "flip": self._check_flip}
        try:
            v = fn[it["kind"]](it)
        except WorkerError as e:
            v = {"ok": False, "failures": [str(e)], "trace": e.trace}
        except Exception as e:
            v = {"ok": False, "failures": [f"{type(e).__name__}: {e}"]}
        self.store.set_validation(item_id, v)
        return self.store.get(item_id)

    def _check_reads(self, it: dict) -> dict:
        reads = it["current"].get("required_reads") or []
        if not reads:
            return {"ok": False, "failures": ["no required reads: the task is not gated"]}
        try:
            parse_spec({it["task_id"]: it["current"]})
        except ValueError as e:
            return {"ok": False, "failures": [str(e)]}
        kinds = {t["name"]: t["kind"] for t in self.store.data.get("tools") or []}
        warnings = []
        for r in reads:
            for tool in [r["tool"]] if isinstance(r["tool"], str) else r["tool"]:
                if kinds and kinds.get(tool) != "read":
                    warnings.append(f"{tool} is not a READ tool ({kinds.get(tool, 'unknown')})")
        return {
            "ok": True,
            "failures": [],
            "warnings": warnings,
            "null_gated": True,  # the do-nothing agent makes no reads, so any read gates it
        }

    def _check_twin(self, it: dict) -> dict:
        spec = it["current"]
        v = self.get_worker().call("validate_twin", {"spec": spec})
        v["warnings"] = []
        if spec.get("policy_flip"):
            flip = self.store.data["items"].get(f"flip:{spec['policy_flip']}")
            if not flip:
                v["warnings"].append(f"policy flip '{spec['policy_flip']}' is not in the flips")
            elif flip["status"] == "rejected":
                v["warnings"].append(f"policy flip '{spec['policy_flip']}' is rejected")
        if it["task_id"] not in self.noop_tasks():
            v["warnings"].append("the original task is not a do-nothing pass")
        return v

    def _check_flip(self, it: dict) -> dict:
        policy = self.policy()
        cur = it["current"]
        if policy is None:
            return {"ok": False, "failures": ["the adapter gives no policy text"]}
        n = policy.count(cur["original"])
        failures = [] if n == 1 else [f"sentence found {n} times in the policy (need 1)"]
        if cur["original"] == cur["replacement"]:
            failures.append("replacement is the same as the original")
        at = policy.find(cur["original"])
        return {
            "ok": not failures,
            "failures": failures,
            "count": n,
            "context_before": policy[max(0, at - 300) : at] if at >= 0 else "",
            "context_after": policy[at + len(cur["original"]) :][:300] if at >= 0 else "",
            "twins": [
                i["id"]
                for i in self.store.data["items"].values()
                if i["kind"] == "twin" and i["current"].get("policy_flip") == it["id"][5:]
            ],
        }

    # --- task details ----------------------------------------------------------------

    def task_info(self, task_id: str) -> dict:
        if task_id not in self.task_cache:
            self.task_cache[task_id] = self.get_worker().call("task_info", {"task_id": task_id})
        return self.task_cache[task_id]

    # --- export ----------------------------------------------------------------------

    def export(self, dest: str | None = None) -> dict:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = Path(dest) if dest else self.workspace / "exports" / self.id / stamp
        out.mkdir(parents=True, exist_ok=True)
        items = self.store.data["items"].values()
        approved = [i for i in items if i["status"] == "approved"]
        reviewers = sorted(
            {h["who"] for i in approved for h in i["history"] if h["who"] != "doctor"}
        )
        files, skipped = [], []

        reads = {i["task_id"]: i["current"] for i in approved if i["kind"] == "reads"}
        if reads:
            spec = {tid: {k: v for k, v in entry.items() if v} for tid, entry in reads.items()} | {
                "_meta": {
                    "status": "reviewed in the doctor UI",
                    "benchmark": self.config["adapter"],
                    "reviewed_by": reviewers,
                    "exported_at": now(),
                }
            }
            parse_spec(spec)  # the same check the doctor and tau2 apply
            files.append(_write(out / "read-spec.json", json.dumps(spec, indent=2) + "\n"))

        twins = [i for i in approved if i["kind"] == "twin"]
        if twins:
            entries = [_twin_yaml(i["current"]) for i in twins]
            files.append(
                _write(out / "twins.yaml", yaml.safe_dump(entries, sort_keys=False, width=100))
            )
            built = []
            for i in twins:
                v = i.get("validation") or {}
                if not v.get("ok"):
                    skipped.append(f"{i['id']}: not validated OK, left out of twin-tasks.json")
                    continue
                try:
                    built.append(self.get_worker().call("build_twin", {"spec": i["current"]}))
                except (WorkerError, ValueError) as e:
                    skipped.append(f"{i['id']}: build failed: {e}")
            if built:
                files.append(_write(out / "twin-tasks.json", json.dumps(built, indent=2) + "\n"))

        flips = [i for i in approved if i["kind"] == "flip"]
        if flips:
            data = {
                i["id"][5:]: {
                    **(i["current"].get("extra") or {}),
                    "original": i["current"]["original"],
                    "replacement": i["current"]["replacement"],
                }
                for i in flips
            }
            files.append(
                _write(out / "flips.yaml", yaml.safe_dump(data, sort_keys=False, width=100))
            )
            policy = self.policy()
            for fid, f in data.items():
                try:
                    text = apply_flip(policy or "", f["original"], f["replacement"])
                    files.append(_write(out / "policy_flips" / f"{fid}.md", text))
                except ValueError as e:
                    skipped.append(f"flip:{fid}: {e}")

        log = [
            {
                k: i[k]
                for k in ("id", "kind", "task_id", "status", "edited", "note", "source", "history")
            }
            for i in items
        ]
        files.append(_write(out / "review-log.json", json.dumps(log, indent=2) + "\n"))
        return {"folder": str(out), "files": files, "skipped": skipped}


def _twin_yaml(spec: dict) -> dict:
    """The doctor's YAML twin format (`doctor.py twins --spec`)."""
    out: dict[str, Any] = {"task": spec["task"], "name": spec["name"]}
    if spec.get("patch"):
        out["patch"] = spec["patch"]
    out["write"] = spec["write"]
    if spec.get("why"):
        out["why"] = spec["why"]
    if spec.get("policy_flip"):
        out["policy_flip"] = spec["policy_flip"]
    return out


def _write(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return str(path)


def _load_json(path: str | None) -> Any:
    if not path or not Path(path).exists():
        return None
    return json.loads(Path(path).read_text())


def summary(svc: BenchService) -> dict[str, Any]:
    """The benchmark as the sidebar and header show it."""
    b = copy.deepcopy(svc.config)
    ck = svc.store.data.get("checkup")
    b["checkup"] = ck["summary"] if ck else None
    b["counts"] = svc.store.counts()
    b["job"] = svc.job.as_dict() if svc.job else None
    b["adapter_info"] = svc.store.data.get("adapter_info")
    return b
