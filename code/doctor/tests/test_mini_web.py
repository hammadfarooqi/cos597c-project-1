"""Every doctor step on a benchmark that is not tau2 (`examples/mini_web.json`).

Needs no tau2 and no API key. It runs the command line, as a user of a new benchmark would.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import doctor  # noqa: E402
from noop_doctor.adapters.mini_web import MiniWebAdapter  # noqa: E402

BENCH = f"mini_web:{ROOT / 'examples' / 'mini_web.json'}"
TWINS = str(ROOT / "examples" / "mini_web_twins.yaml")


def run(capsys, *argv):
    doctor.main(list(argv))
    return capsys.readouterr().out


def call(name, **args):
    return {"name": name, "arguments": args}


# Three agents. Each episode lists the agent's calls; the reward is the benchmark's grade.
AGENTS = {
    # does nothing
    "null": ({t: [] for t in "1234"}, []),
    # searches, then always says N/A
    "refuser": (
        {
            "1": [call("search", query="red mug"), call("answer", text="N/A")],
            "2": [call("search", query="blue teapot"), call("answer", text="N/A")],
            "3": [call("search", query="green vase"), call("answer", text="N/A")],
            "4": [call("search", query="gold spoon"), call("answer", text="N/A")],
        },
        [call("search", query="blue teapot"), call("answer", text="N/A")],
    ),
    # reads and answers correctly
    "good": (
        {
            "1": [
                call("search", query="red mug"),
                call("open", product_id="p1"),
                call("answer", text="12"),
            ],
            "2": [call("search", query="blue teapot"), call("answer", text="N/A")],
            "3": [
                call("search", query="green vase"),
                call("open", product_id="p2"),
                call("answer", text="40"),
            ],
            "4": [call("search", query="gold spoon"), call("answer", text="N/A")],
        },
        [
            call("search", query="blue teapot"),
            call("open", product_id="p4"),
            call("answer", text="30"),
        ],
    ),
}


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    """Write each agent's original and twin episodes, graded by the adapter."""
    from noop_doctor.core.calls import ObservedCall
    from noop_doctor.core.twins import TwinSpec

    ad = MiniWebAdapter(ROOT / "examples" / "mini_web.json")
    twin = ad.build_twin(
        TwinSpec(
            "2",
            "in_stock",
            ObservedCall("answer", {"text": "30"}),
            {"products": {"p4": {"name": "blue teapot", "price": 30}}},
        )
    )
    d = tmp_path_factory.mktemp("runs")

    def grade(task, calls):
        return ad.state_reward(
            task, [ObservedCall(c["name"], c["arguments"]) for c in calls]
        )

    for name, (orig, twin_calls) in AGENTS.items():
        rows = [
            {"task_id": t, "reward": grade(ad.task(t), c), "calls": c}
            for t, c in orig.items()
        ]
        (d / f"{name}_orig.json").write_text(json.dumps(rows))
        (d / f"{name}_twins.json").write_text(
            json.dumps(
                [
                    {
                        "task_id": "2_twin_in_stock",
                        "reward": grade(twin, twin_calls),
                        "calls": twin_calls,
                    }
                ]
            )
        )
    return d


def test_checkup_finds_the_na_tasks(capsys):
    out = run(capsys, "checkup", "--bench", BENCH)
    assert "2/4 tasks pass with a do-nothing agent" in out
    assert "passed, gold lists reads (read gate can be drafted): ['2']" in out
    assert "passed, gold lists no reads (needs a person): ['4']" in out


def test_draft_and_apply_the_read_gate(capsys, tmp_path, runs):
    spec = tmp_path / "spec.json"
    run(capsys, "draft-reads", "--bench", BENCH, "--out", str(spec))
    assert json.loads(spec.read_text())["2"]["required_reads"][0]["match"] == {
        "query": "blue teapot"
    }
    out = run(
        capsys,
        "check-reads",
        "--bench",
        BENCH,
        "--spec",
        str(spec),
        "--run",
        str(runs / "null_orig.json"),
    )
    assert "2 -> 1 after the read gate (1 gated)" in out  # task 4 has no gold read
    out = run(
        capsys,
        "check-reads",
        "--bench",
        BENCH,
        "--spec",
        str(spec),
        "--run",
        str(runs / "refuser_orig.json"),
    )
    assert "(0 gated)" in out  # the refuser reads, so only a twin catches it


def test_twin_is_valid(capsys):
    out = run(capsys, "twins", "validate", "--bench", BENCH, "--spec", TWINS)
    assert "1/1 twins valid" in out


def test_pairs_catch_the_refuser(capsys, runs):
    out = run(
        capsys,
        "pairs",
        "--bench",
        BENCH,
        "--spec",
        TWINS,
        "--orig",
        str(runs / "{m}_orig.json"),
        "--twins",
        str(runs / "{m}_twins.json"),
        "null",
        "refuser",
        "good",
    )
    lines = {ln.split("|")[1].strip(): ln for ln in out.splitlines() if "| all |" in ln}
    assert "**0**" in lines["refuser"] and "wrong write 1" in lines["refuser"]
    assert "**0**" in lines["null"] and "no write 1" in lines["null"]
    assert "**1**" in lines["good"]


def test_unsupported_step_is_reported():
    with pytest.raises(SystemExit, match="unknown benchmark"):
        doctor.make_adapter("nope:x", "checkup")
