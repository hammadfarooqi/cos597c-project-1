"""HTTP API of the doctor UI, and the built frontend.

Run from `code/doctor-ui/`:

    uv run uvicorn backend.app:app --port 8000

Set DOCTOR_UI_HOME to keep the workspace (clones, reviews, exports) somewhere other than
`code/doctor-ui/workspace/`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .benchmarks import UI_ROOT, Registry
from .service import BenchService, summary
from .workers import WorkerError

WORKSPACE = Path(os.environ.get("DOCTOR_UI_HOME", UI_ROOT / "workspace")).resolve()

app = FastAPI(title="No-op doctor review")
registry = Registry(WORKSPACE)
services: dict[str, BenchService] = {}


def svc(bid: str) -> BenchService:
    try:
        registry.get(bid)
    except KeyError:
        raise HTTPException(404, f"no benchmark {bid}") from None
    if bid not in services:
        services[bid] = BenchService(registry, WORKSPACE, bid)
    return services[bid]


def guard(fn, *a, **kw):
    """Turn user-facing errors into 400s with a readable message."""
    try:
        return fn(*a, **kw)
    except (ValueError, KeyError, WorkerError, RuntimeError) as e:
        raise HTTPException(400, str(e)) from e


# --- benchmarks ------------------------------------------------------------------------


class AddRepo(BaseModel):
    git_url: Optional[str] = None
    path: Optional[str] = None
    ref: Optional[str] = None


class UpdateBench(BaseModel):
    label: Optional[str] = None
    adapter: Optional[str] = None
    python: Optional[list[str]] = None
    cwd: Optional[str] = None
    sys_path: Optional[list[str]] = None
    sources: Optional[dict[str, Any]] = None


@app.get("/api/benchmarks")
def list_benchmarks():
    return [summary(svc(bid)) for bid in registry.items]


@app.post("/api/benchmarks")
def add_benchmark(body: AddRepo):
    found = guard(registry.add_repo, body.git_url, body.path, body.ref)
    return [summary(svc(b["id"])) for b in found]


@app.get("/api/benchmarks/{bid}")
def get_benchmark(bid: str):
    return summary(svc(bid))


@app.patch("/api/benchmarks/{bid}")
def update_benchmark(bid: str, body: UpdateBench):
    s = svc(bid)
    guard(registry.update, bid, body.model_dump(exclude_none=True))
    s.reset_worker()
    return summary(s)


@app.delete("/api/benchmarks/{bid}")
def delete_benchmark(bid: str):
    s = svc(bid)
    guard(registry.remove, bid)
    s.reset_worker()
    services.pop(bid, None)
    return {"ok": True}


# --- jobs ------------------------------------------------------------------------------


@app.post("/api/benchmarks/{bid}/setup")
def setup(bid: str):
    s = svc(bid)
    return guard(s.start_job, "setup", s.run_setup).as_dict()


@app.post("/api/benchmarks/{bid}/checkup")
def checkup(bid: str):
    s = svc(bid)
    return guard(s.start_job, "checkup", s.run_checkup).as_dict()


@app.post("/api/benchmarks/{bid}/validate-all")
def validate_all(bid: str):
    s = svc(bid)
    return guard(s.start_job, "validate", s.validate_all).as_dict()


@app.get("/api/benchmarks/{bid}/job")
def job(bid: str):
    s = svc(bid)
    return s.job.as_dict() if s.job else None


# --- review ----------------------------------------------------------------------------


@app.get("/api/benchmarks/{bid}/review")
def review(bid: str):
    s = svc(bid)
    d = s.store.data
    return {
        "checkup": d.get("checkup"),
        "items": list(d["items"].values()),
        "tools": d.get("tools") or [],
    }


@app.get("/api/benchmarks/{bid}/tasks/{task_id}")
def task(bid: str, task_id: str):
    return guard(svc(bid).task_info, task_id)


@app.get("/api/benchmarks/{bid}/policy")
def policy(bid: str):
    return {"text": svc(bid).policy()}


class ItemUpdate(BaseModel):
    reviewer: str = ""
    status: Optional[str] = None
    note: Optional[str] = None
    current: Optional[dict[str, Any]] = None
    revert: bool = False


class NewItem(BaseModel):
    reviewer: str = ""
    kind: str
    task_id: Optional[str] = None
    id: Optional[str] = None  # flips: the flip id
    current: dict[str, Any]


@app.put("/api/benchmarks/{bid}/items/{item_id:path}")
def update_item(bid: str, item_id: str, body: ItemUpdate):
    s = svc(bid)
    item = guard(
        s.store.review,
        item_id,
        body.reviewer,
        status=body.status,
        note=body.note,
        current=body.current,
        revert=body.revert,
    )
    if item["validation"] is None:  # edited: check it again before anyone relies on it
        item = s.validate(item_id)
    return item


@app.post("/api/benchmarks/{bid}/items")
def add_item(bid: str, body: NewItem):
    s = svc(bid)
    if body.kind == "reads":
        item_id = f"reads:{body.task_id}"
    elif body.kind == "twin":
        item_id = f"twin:{body.current['task']}_twin_{body.current['name']}"
    elif body.kind == "flip":
        if not body.id or not re.fullmatch(r"[a-z0-9_]+", body.id):
            raise HTTPException(400, "a flip id is lowercase letters, digits and _")
        item_id = f"flip:{body.id}"
    else:
        raise HTTPException(400, "kind must be reads, twin or flip")
    guard(s.store.add_manual, item_id, body.kind, body.current, body.task_id, body.reviewer)
    return s.validate(item_id)


@app.post("/api/benchmarks/{bid}/items/{item_id:path}/validate")
def validate_item(bid: str, item_id: str):
    return guard(svc(bid).validate, item_id)


@app.delete("/api/benchmarks/{bid}/items/{item_id:path}")
def delete_item(bid: str, item_id: str):
    guard(svc(bid).store.remove, item_id)
    return {"ok": True}


class ExportBody(BaseModel):
    dest: Optional[str] = None


@app.post("/api/benchmarks/{bid}/export")
def export(bid: str, body: ExportBody):
    return guard(svc(bid).export, body.dest)


# --- frontend --------------------------------------------------------------------------

DIST = UI_ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        return FileResponse(DIST / "index.html")
