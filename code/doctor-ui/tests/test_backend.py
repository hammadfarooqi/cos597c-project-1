"""Backend tests on the mini_web example: no API key, no tau2, a few seconds.

Run from code/doctor-ui/: uv run --extra dev pytest tests
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT.parent / "doctor"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DOCTOR))

from noop_doctor.core.reads import parse_spec  # noqa: E402

from backend.benchmarks import Registry, detect  # noqa: E402
from backend.service import BenchService  # noqa: E402


@pytest.fixture
def mini(tmp_path):
    reg = Registry(tmp_path)
    svc = BenchService(reg, tmp_path, "mini-web")
    job = svc.start_job("checkup", svc.run_checkup)
    for _ in range(200):
        if job.state != "running":
            break
        time.sleep(0.05)
    assert job.state == "done", job.error + "\n".join(job.log)
    yield svc
    svc.reset_worker()


def test_checkup_makes_proposals(mini):
    s = mini.store.data["checkup"]["summary"]
    assert s["passed"] == ["2", "4"]
    items = mini.store.data["items"]
    assert set(items) == {"reads:2", "reads:4", "twin:2_twin_in_stock"}
    assert items["reads:2"]["current"]["required_reads"] == [
        {"tool": "search", "match": {"query": "blue teapot"}, "why": "from gold"}
    ]
    # Task 4 has no gold reads: a person must write the requirement.
    assert items["reads:4"]["validation"]["ok"] is False
    twin = items["twin:2_twin_in_stock"]["validation"]
    assert twin["ok"] and twin["null_orig"] == 1 and twin["comply_twin"] == 1
    assert twin["diff"][0]["path"] == ["products", "p4"]


def test_edit_revalidates_and_review_survives_refresh(mini):
    item = mini.store.get("twin:2_twin_in_stock")
    # A patch that sets a field to the value it already has changes nothing.
    bad = dict(item["current"], patch={"products": {"p1": {"price": 12}}})
    mini.store.review(item["id"], "vatsal", current=bad)
    v = mini.validate(item["id"])["validation"]
    assert not v["ok"] and "patch changes nothing" in v["failures"]
    mini.store.review(item["id"], "vatsal", status="rejected", note="wrong price")
    mini.refresh_proposals()  # a refresh must not undo a person's review
    item = mini.store.get(item["id"])
    assert item["status"] == "rejected" and item["current"] == bad
    assert [h["action"] for h in item["history"]] == ["proposed", "edited", "rejected"]
    mini.store.review(item["id"], "vatsal", revert=True)
    assert mini.store.get(item["id"])["current"] == item["proposal"]


def test_export_round_trips_through_the_doctor(mini, tmp_path):
    mini.store.review("reads:2", "vatsal", status="approved")
    mini.store.review("twin:2_twin_in_stock", "vatsal", status="approved")
    out = mini.export(str(tmp_path / "export"))
    names = sorted(Path(f).name for f in out["files"])
    assert names == ["read-spec.json", "review-log.json", "twin-tasks.json", "twins.yaml"]
    spec = parse_spec(json.loads((tmp_path / "export" / "read-spec.json").read_text()))
    assert list(spec) == ["2"]
    # The exported twins file is valid input for the doctor's own command line.
    r = subprocess.run(
        [
            sys.executable,
            str(DOCTOR / "doctor.py"),
            "twins",
            "validate",
            "--bench",
            f"mini_web:{DOCTOR / 'examples' / 'mini_web.json'}",
            "--spec",
            str(tmp_path / "export" / "twins.yaml"),
        ],
        capture_output=True,
        text=True,
        cwd=DOCTOR,
    )
    assert r.returncode == 0, r.stderr
    assert "1/1 twins valid" in r.stdout


def test_manual_twin_and_flip_checks(mini):
    cur = {
        "task": "4",
        "name": "spoon",
        "patch": {"products": {"p9": {"name": "gold spoon", "price": 7}}},
        "write": {"name": "answer", "arguments": {"text": "7"}},
        "why": "The shop now sells a gold spoon.",
        "policy_flip": None,
    }
    mini.store.add_manual("twin:4_twin_spoon", "twin", cur, "4", "vatsal")
    assert mini.validate("twin:4_twin_spoon")["validation"]["ok"]
    # mini_web has no policy, so a flip cannot be checked.
    mini.store.add_manual("flip:x", "flip", {"original": "a", "replacement": "b"}, None, "v")
    v = mini.validate("flip:x")["validation"]
    assert not v["ok"] and "no policy text" in v["failures"][0]


def test_detect(tmp_path):
    src = {"kind": "local", "path": str(tmp_path)}
    # tau2-shaped checkout, one folder down (as in this repository)
    t = tmp_path / "a" / "code" / "tau2-bench"
    (t / "src" / "tau2").mkdir(parents=True)
    (t / "src" / "tau2" / "registry.py").write_text("")
    for d in ("airline", "retail"):
        (t / "data" / "tau2" / "domains" / d).mkdir(parents=True)
        (t / "data" / "tau2" / "domains" / d / "tasks.json").write_text("[]")
    found = detect(tmp_path / "a", "a", src)
    assert [b["adapter"] for b in found] == ["tau2:airline", "tau2:retail"]
    assert all(b["status"] == "needs_setup" for b in found)  # no .venv yet
    assert found[0]["sources"]["skip_tools"] == ["get_user_details"]
    # manifest
    m = tmp_path / "b"
    m.mkdir()
    (m / "noop-doctor.json").write_text(
        json.dumps(
            {
                "benchmarks": [
                    {"id": "x", "adapter": "py:pkg.mod:A:arg", "sources": {"twin_yaml": ["t.yaml"]}}
                ]
            }
        )
    )
    (b,) = detect(m, "b", src)
    assert b["adapter"] == "py:pkg.mod:A:arg" and b["status"] == "ready"
    assert b["sources"]["twin_yaml"] == [str(m / "t.yaml")]
    # anything else
    (tmp_path / "c").mkdir()
    (c,) = detect(tmp_path / "c", "c", src)
    assert c["status"] == "needs_adapter" and c["adapter"] is None


def test_add_repo_from_git_and_set_adapter(tmp_path):
    """Clone a git repo that has no adapter, then point it at the mini_web adapter."""
    repo = tmp_path / "bench"
    repo.mkdir()
    (repo / "README.md").write_text("a benchmark\n")
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    for cmd in (["git", "init", "-q"], ["git", "add", "."], ["git", "commit", "-qm", "x"]):
        subprocess.run(cmd, cwd=repo, check=True, env=env)
    ws = tmp_path / "ws"
    reg = Registry(ws)
    (b,) = reg.add_repo(f"file://{repo}", None, None)
    assert b["status"] == "needs_adapter" and (ws / "repos" / "bench" / "README.md").exists()
    reg.update(b["id"], {"adapter": f"mini_web:{DOCTOR / 'examples' / 'mini_web.json'}"})
    assert Registry(ws).get(b["id"])["status"] == "ready"  # saved


def test_twin_yaml_from_doctor_examples_loads():
    specs = yaml.safe_load((DOCTOR / "examples" / "mini_web_twins.yaml").read_text())
    assert specs[0]["task"] == "2"


def test_existing_spec_is_proposed_when_gold_has_no_reads(tmp_path):
    ref = tmp_path / "ref.json"
    read = {"tool": "open", "match": {"product_id": "p9"}, "why": "hand-written"}
    ref.write_text(json.dumps({"4": {"required_reads": [read]}}))
    reg = Registry(tmp_path)
    reg.update("mini-web", {"sources": {"reads_reference": str(ref)}})
    svc = BenchService(reg, tmp_path, "mini-web")
    job = svc.start_job("checkup", svc.run_checkup)
    for _ in range(200):
        if job.state != "running":
            break
        time.sleep(0.05)
    item = svc.store.get("reads:4")
    svc.reset_worker()
    assert item["current"]["required_reads"] == [read]
    assert item["source"].startswith("from the existing spec")
    assert item["validation"]["ok"]
