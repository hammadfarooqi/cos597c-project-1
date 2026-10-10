"""Benchmarks the UI knows: built-in presets, and repos added by git URL or local path.

Adding a repo detects how to run the doctor on it, in this order:

1. A manifest `noop-doctor.json` at the repo root names the adapter (any benchmark).
2. A tau2-bench checkout (`src/tau2/registry.py` and `data/tau2/domains/`, at the root or up
   to two folders down): one benchmark per domain, with the built-in tau2 adapter.
3. Anything else: the benchmark is added with status `needs_adapter`. Nothing runs until a
   person gives an adapter (`py:<module>:<Class>:<arg>`) and a Python command.

Configs live in `<workspace>/benchmarks.json`. Presets are rebuilt at each start.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
UI_ROOT = HERE.parent
CODE = UI_ROOT.parent  # code/
DOCTOR = CODE / "doctor"
MANIFEST = "noop-doctor.json"

# Read tools that only lead to an ID; dropped from read drafts (design §4 pruning rule).
TAU2_ROUTE_READS = {
    "airline": ["get_user_details"],
    "retail": ["get_user_details", "find_user_id_by_email", "find_user_id_by_name_zip"],
}


def _uv_python(project: Path, with_: tuple[str, ...] = ()) -> list[str]:
    extra = [a for w in with_ for a in ("--with", w)]
    return ["uv", "run", "--project", str(project), *extra, "python"]


# Upstream tau2 imports `websockets` from core code but lists it only in the `voice` extra
# (code/README.md). `uv run --with` adds it for the worker without changing the checkout.
TAU2_WITH = ("websockets",)


def _empty_sources() -> dict[str, Any]:
    return {
        "twin_task_files": [],  # adapter-specific twin files (tau2 tasks_twins.json)
        "twin_yaml": [],  # doctor YAML twin specs (any benchmark)
        "flips_yaml": [],  # one-sentence policy flips
        "reads_reference": None,  # an existing read spec to compare drafts with
        "skip_tools": [],  # route-only reads to leave out of drafts
    }


def tau2_benchmarks(root: Path, id_prefix: str, source: dict, label: str = "") -> list[dict]:
    """One benchmark per tau2 domain folder that has a tasks.json."""
    out = []
    domains = root / "data" / "tau2" / "domains"
    ready = (root / ".venv").exists()
    for d in sorted(p for p in domains.iterdir() if (p / "tasks.json").exists()):
        src = _empty_sources()
        if (d / "tasks_twins.json").exists():
            src["twin_task_files"].append(str(d / "tasks_twins.json"))
        if (d / "justification.json").exists():
            src["reads_reference"] = str(d / "justification.json")
        src["skip_tools"] = TAU2_ROUTE_READS.get(d.name, [])
        out.append(
            {
                "id": f"{id_prefix}-{d.name}",
                "label": f"{label or id_prefix} · {d.name}",
                "adapter": f"tau2:{d.name}",
                "python": _uv_python(root, TAU2_WITH),
                "cwd": str(root),
                "sys_path": [],
                "kwargs": {},
                "source": source,
                "sources": src,
                "status": "ready" if ready else "needs_setup",
                "setup": ["uv", "sync"],
                "detected": "tau2-bench checkout: built-in tau2 adapter",
            }
        )
    return out


def presets() -> list[dict]:
    """This repository's own tau2 copy and the mini_web toy."""
    out = []
    tau2 = CODE / "tau2-bench"
    if (tau2 / "src" / "tau2" / "registry.py").exists():
        out = tau2_benchmarks(
            tau2, "local", {"kind": "preset", "path": str(tau2)}, "tau2 (this repo)"
        )
        for b in out:
            if b["adapter"] == "tau2:airline":
                b["sources"]["flips_yaml"].append(str(CODE / "twins" / "policy_flips.yaml"))
    out.append(
        {
            "id": "mini-web",
            "label": "mini_web (toy, not tau2)",
            "adapter": f"mini_web:{DOCTOR / 'examples' / 'mini_web.json'}",
            "python": [sys.executable],
            "cwd": str(DOCTOR),
            "sys_path": [],
            "kwargs": {},
            "source": {"kind": "preset", "path": str(DOCTOR / "examples")},
            "sources": _empty_sources()
            | {"twin_yaml": [str(DOCTOR / "examples" / "mini_web_twins.yaml")]},
            "status": "ready",
            "setup": None,
            "detected": "doctor example benchmark",
        }
    )
    return out


def find_tau2_root(root: Path) -> Path | None:
    for cand in [root, *root.glob("*"), *root.glob("*/*")]:
        if (cand / "src" / "tau2" / "registry.py").exists() and (
            cand / "data" / "tau2" / "domains"
        ).is_dir():
            return cand
    return None


def detect(root: Path, slug: str, source: dict) -> list[dict]:
    """The benchmarks found in a checkout (see the module docstring)."""
    manifest = root / MANIFEST
    if manifest.exists():
        return _from_manifest(root, slug, source, json.loads(manifest.read_text()))
    tau2 = find_tau2_root(root)
    if tau2 is not None:
        return tau2_benchmarks(tau2, slug, source)
    return [
        {
            "id": slug,
            "label": slug,
            "adapter": None,
            "python": [sys.executable],
            "cwd": str(root),
            "sys_path": [str(root)],
            "kwargs": {},
            "source": source,
            "sources": _empty_sources(),
            "status": "needs_adapter",
            "setup": None,
            "detected": (
                f"no {MANIFEST} and not a tau2-bench checkout. Give an adapter "
                "(py:<module>:<Class>:<argument>) to run the doctor on it."
            ),
        }
    ]


def _from_manifest(root: Path, slug: str, source: dict, m: dict) -> list[dict]:
    """`noop-doctor.json`: {"benchmarks": [{"id", "label", "adapter", "python"?, "setup"?,
    "sys_path"?, "sources"?}]}. Relative paths are relative to the repo root."""
    out = []
    for b in m.get("benchmarks", []):
        src = _empty_sources()
        for k, v in (b.get("sources") or {}).items():
            if k in ("twin_task_files", "twin_yaml", "flips_yaml"):
                src[k] = [str(root / p) for p in v]
            elif k == "reads_reference" and v:
                src[k] = str(root / v)
            else:
                src[k] = v
        python = b.get("python") or (
            _uv_python(root) if (root / "pyproject.toml").exists() else [sys.executable]
        )
        ready = not b.get("setup") or (root / ".venv").exists()
        out.append(
            {
                "id": f"{slug}-{b['id']}",
                "label": b.get("label", b["id"]),
                "adapter": b["adapter"],
                "python": python,
                "cwd": str(root),
                "sys_path": [str(root / p) for p in b.get("sys_path", ["."])],
                "kwargs": b.get("kwargs", {}),
                "source": source,
                "sources": src,
                "status": "ready" if ready else "needs_setup",
                "setup": b.get("setup"),
                "detected": f"{MANIFEST}: adapter {b['adapter']}",
            }
        )
    return out


def slugify(text: str) -> str:
    text = re.sub(r"\.git$", "", text.rstrip("/")).split("/")[-1]
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "bench"


def clone(url: str, dest: Path, ref: str | None = None) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd += ["--branch", ref]
    r = subprocess.run(cmd + [url, str(dest)], capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"git clone failed: {r.stderr.strip()[-800:]}")


class Registry:
    """Benchmark configs: presets plus the ones a person added (saved in the workspace)."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.file = workspace / "benchmarks.json"
        workspace.mkdir(parents=True, exist_ok=True)
        added = json.loads(self.file.read_text()) if self.file.exists() else []
        self.items: dict[str, dict] = {b["id"]: b for b in presets()}
        self.items |= {b["id"]: b for b in added}

    def save(self) -> None:
        added = [b for b in self.items.values() if b["source"]["kind"] != "preset"]
        self.file.write_text(json.dumps(added, indent=2) + "\n")

    def get(self, bid: str) -> dict:
        if bid not in self.items:
            raise KeyError(bid)
        return self.items[bid]

    def add_repo(self, url: str | None, path: str | None, ref: str | None) -> list[dict]:
        if url:
            slug = slugify(url)
            dest = self.workspace / "repos" / slug
            clone(url, dest, ref)
            source = {"kind": "git", "url": url, "ref": ref, "path": str(dest)}
        elif path:
            dest = Path(path).expanduser().resolve()
            if not dest.is_dir():
                raise ValueError(f"not a folder: {dest}")
            slug = slugify(str(dest))
            source = {"kind": "local", "path": str(dest)}
        else:
            raise ValueError("give a git URL or a local path")
        found = detect(dest, slug, source)
        for b in found:
            self.items[b["id"]] = b
        self.save()
        return found

    def update(self, bid: str, changes: dict) -> dict:
        b = self.get(bid)
        for k in ("label", "adapter", "python", "cwd", "sys_path", "kwargs"):
            if k in changes:
                b[k] = changes[k]
        if "sources" in changes:
            b["sources"] = {**b["sources"], **changes["sources"]}
        if b["status"] == "needs_adapter" and b.get("adapter"):
            b["status"] = "ready"
        self.save()
        return b

    def remove(self, bid: str) -> None:
        b = self.get(bid)
        if b["source"]["kind"] == "preset":
            raise ValueError("built-in benchmarks cannot be removed")
        del self.items[bid]
        self.save()
