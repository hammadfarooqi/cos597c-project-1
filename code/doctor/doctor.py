"""No-op doctor command line.

Run from `code/tau2-bench/` so the tau2 adapter finds tau2 and its data:

    uv run python ../doctor/doctor.py checkup --bench tau2:retail
    uv run python ../doctor/doctor.py draft-reads --bench tau2:retail --out draft.json
    uv run python ../doctor/doctor.py check-reads --bench tau2:airline --spec SPEC --run RESULTS
    uv run python ../doctor/doctor.py twins validate --bench tau2:airline --twin-tasks FILE
    uv run python ../doctor/doctor.py twins build --bench tau2:retail --spec SPEC.yaml --out FILE
    uv run python ../doctor/doctor.py flips --policy POLICY.md --flips FLIPS.yaml --out-dir DIR
    uv run python ../doctor/doctor.py pairs --bench tau2:airline --twin-tasks FILE \
        --orig 'data/simulations/airline_{m}' --twins 'data/simulations/airline_twins*_{m}' MODEL...

See code/doctor/README.md.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from noop_doctor.core import checkup as ck  # noqa: E402
from noop_doctor.core import pairs as pr  # noqa: E402
from noop_doctor.core.calls import ObservedCall  # noqa: E402
from noop_doctor.core.flips import apply_flips  # noqa: E402
from noop_doctor.core.reads import (  # noqa: E402
    check_task,
    compare_specs,
    draft_spec,
    parse_spec,
)
from noop_doctor.core.twins import TwinSpec, validate_twin  # noqa: E402

BUILTIN = {
    "tau2": "noop_doctor.adapters.tau2:Tau2Adapter",
    "mini_web": "noop_doctor.adapters.mini_web:MiniWebAdapter",
}


def make_adapter(bench: str, step: str, **kw):
    """`bench` is `<builtin>:<arg>` (e.g. `tau2:retail`) or `py:<module>:<Class>:<arg>` for
    an adapter that lives anywhere on the Python path. The adapter is built as Class(arg)."""
    try:  # tau2 logs at DEBUG; keep the doctor's output readable
        from loguru import logger

        logger.remove()
        logger.add(sys.stderr, level="ERROR")
    except ImportError:
        pass
    import importlib

    from noop_doctor.adapters.base import missing_methods

    kind, _, arg = bench.partition(":")
    if kind == "py":
        module, cls, arg = (arg.split(":", 2) + ["", ""])[:3]
    elif kind in BUILTIN:
        module, cls = BUILTIN[kind].split(":")
    else:
        raise SystemExit(
            f"unknown benchmark '{kind}' (known: {', '.join(BUILTIN)}, py:...)"
        )
    adapter = getattr(importlib.import_module(module), cls)(
        arg, **{k: v for k, v in kw.items() if v is not None}
    )
    missing = missing_methods(adapter, step)
    if missing:
        raise SystemExit(f"{adapter.name} cannot run '{step}': no {', '.join(missing)}")
    return adapter


def cmd_checkup(a):
    ad = make_adapter(a.bench, "checkup", task_set=a.task_set, nl_judge=a.nl_judge)
    results = ck.run_checkup(ad)
    s = ck.summarize(results)
    print(
        f"{ad.name}: {s['null_passes']}/{s['tasks']} tasks pass with a do-nothing agent "
        f"({100 * s['pass_rate']:.1f}%). {s['verdict']}."
    )
    print(f"  tasks whose gold has no write: {s['no_gold_write']}")
    print(
        f"  passed, gold lists reads (read gate can be drafted): {s['passed_with_gold_reads']}"
    )
    print(
        f"  passed, gold lists no reads (needs a person): {s['passed_without_gold_reads']}"
    )
    if s["passed_but_gold_writes"]:
        print(
            f"  WARNING: passed although the gold has a write: {s['passed_but_gold_writes']}"
        )
    if s["errors"]:
        print(
            f"  {len(s['errors'])} tasks could not be scored, e.g. "
            f"{next(iter(s['errors'].items()))}"
        )
    if a.json:
        rows = [
            r.__dict__
            | {"null_reward": None if math.isnan(r.null_reward) else r.null_reward}
            for r in results
        ]
        Path(a.json).write_text(
            json.dumps({"summary": s, "tasks": rows}, indent=2) + "\n"
        )


def cmd_draft_reads(a):
    ad = make_adapter(a.bench, "draft-reads", task_set=a.task_set, nl_judge=a.nl_judge)
    if a.tasks:
        ids = a.tasks
    else:
        ids = [r.task_id for r in ck.run_checkup(ad) if r.passed]
    draft = draft_spec(ids, ad.gold_calls, ad.tool_kind, a.skip_tool)
    print(
        f"drafted required reads for {len(draft) - 1} of {len(ids)} tasks; "
        f"no gold reads: {draft['_meta']['no_gold_reads']}"
    )
    if a.out:
        Path(a.out).write_text(json.dumps(draft, indent=2) + "\n")
    if a.compare:
        ref = parse_spec(json.loads(Path(a.compare).read_text()))
        cmp = compare_specs(parse_spec(draft), ref)
        print("| Task | Both | Draft only | Reference only |\n|---|---|---|---|")
        for tid, c in cmp.items():
            print(f"| {tid} | {c['both']} | {c['draft_only']} | {c['ref_only']} |")


def cmd_check_reads(a):
    ad = make_adapter(a.bench, "check-reads", task_set=a.task_set)
    spec = parse_spec(json.loads(Path(a.spec).read_text()))
    eps = ad.load_episodes(Path(a.run))
    gated = 0
    print("| Task | Passed (original) | Justified | Missing |\n|---|---|---|---|")
    for tid, ts in spec.items():
        if tid not in eps:
            continue
        v = check_task(ts, eps[tid].calls)
        missing = ", ".join(f"{r.tools[0]}{r.match}" for r in v.missing)
        ok = eps[tid].passed_originally
        print(f"| {tid} | {int(ok)} | {int(v.justified)} | {missing} |")
        gated += ok and not v.justified
    total = sum(e.passed_originally for e in eps.values())
    print(
        f"\npasses (original scoring): {total} -> {total - gated} "
        f"after the read gate ({gated} gated)"
    )


def _twin_specs_from_yaml(path: str) -> list[TwinSpec]:
    import yaml

    out = []
    for e in yaml.safe_load(Path(path).read_text()):
        w = e["write"]
        out.append(
            TwinSpec(
                str(e["task"]),
                e["name"],
                ObservedCall(w["name"], w["arguments"]),
                e.get("patch") or {},
                e.get("why", ""),
                e.get("policy_flip"),
            )
        )
    return out


def _report_twins(ad, specs):
    ok = 0
    print("| Twin | Kind | Fields | Local | Null orig/twin | Comply orig/twin | OK |")
    print("|---|---|---|---|---|---|---|")
    for s in specs:
        c = validate_twin(ad, s)
        ok += c.ok
        print(
            f"| {c.twin_id} | {s.kind} | {c.fields} | {int(c.local)} | "
            f"{c.null_orig:g}/{c.null_twin:g} | {c.comply_orig:g}/{c.comply_twin:g} | "
            f"{'yes' if c.ok else 'NO: ' + '; '.join(c.failures())} |"
        )
    print(f"\n{ok}/{len(specs)} twins valid")
    return ok


def _twin_specs(ad, a) -> list[TwinSpec]:
    """From a YAML spec list (any benchmark) or the adapter's own twin task file."""
    if getattr(a, "spec", None):
        return _twin_specs_from_yaml(a.spec)
    if a.twin_tasks:
        if not hasattr(ad, "twin_specs_from_tasks"):
            raise SystemExit(f"{ad.name} cannot read --twin-tasks; give --spec YAML")
        return ad.twin_specs_from_tasks(Path(a.twin_tasks))
    raise SystemExit("give --spec (a YAML list of twin specs) or --twin-tasks")


def _dump(task):
    return task.model_dump(mode="json") if hasattr(task, "model_dump") else task


def cmd_twins(a):
    ad = make_adapter(a.bench, "twins", task_set=a.task_set)
    specs = _twin_specs(ad, a)
    _report_twins(ad, specs)
    if a.action == "build" and a.out:
        tasks = [_dump(ad.build_twin(s)) for s in specs if validate_twin(ad, s).ok]
        Path(a.out).write_text(json.dumps(tasks, indent=2) + "\n")
        print(f"wrote {len(tasks)} valid twins to {a.out}")


def cmd_flips(a):
    import yaml

    flipped = apply_flips(
        Path(a.policy).read_text(), yaml.safe_load(Path(a.flips).read_text())
    )
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for fid, text in flipped.items():
        (out / f"{fid}.md").write_text(text)
        print(f"wrote {out / f'{fid}.md'}")


def cmd_pairs(a):
    ad = make_adapter(a.bench, "pairs", task_set=a.task_set)
    specs = _twin_specs(ad, a)
    info = {s.twin_id: (s.task_id, s.kind, s.write) for s in specs}
    writes, transfers = ad.write_tools(), ad.transfer_tools()
    print(
        "| Model | Kind | No-op passes | Twin passes | Paired | No-op only | Twin only "
        "| Neither | Twin failure causes |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for m in a.models:
        orig = ad.load_episodes(Path(a.orig.format(m=m)))
        twins = {}
        for d in sorted(glob.glob(a.twins.format(m=m))):
            twins |= ad.load_episodes(Path(d))
        results = pr.score_pairs(orig, twins, info, writes, transfers)
        for kind in ("DB", "policy", "all"):
            s = pr.summarize([r for r in results if kind == "all" or r.kind == kind])
            causes = ", ".join(f"{k} {v}" for k, v in s["causes"].items())
            print(
                f"| {m} | {kind} | {s['noop_passes']}/{s['n']} | {s['twin_passes']}/{s['n']} "
                f"| **{s['paired']}** | {s['noop_only']} | {s['twin_only']} | "
                f"{s['neither']} | {causes} |"
            )
        total = sum(e.passed for e in orig.values())
        removed = pr.summarize(results)["credit_removed"]
        print(
            f"| {m} | score | {total}/{len(orig)} -> **{total - removed}/{len(orig)}** "
            f"| | | | | | |"
        )


def main(argv=None):
    p = argparse.ArgumentParser(prog="doctor", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def bench(sp, judge=False):
        sp.add_argument("--bench", required=True, help="e.g. tau2:retail")
        sp.add_argument("--task-set", help="tau2 task set (default: the domain's)")
        if judge:
            sp.add_argument("--nl-judge", help="LLM judge model for NL assertions")

    s = sub.add_parser("checkup", help="which tasks pass with a do-nothing agent")
    bench(s, judge=True)
    s.add_argument("--json", help="write per-task results here")
    s.set_defaults(fn=cmd_checkup)

    s = sub.add_parser("draft-reads", help="draft a read-gate spec from gold reads")
    bench(s, judge=True)
    s.add_argument(
        "--tasks", nargs="*", help="task ids (default: the checkup's passes)"
    )
    s.add_argument(
        "--skip-tool", nargs="*", default=[], help="route-only read tools to drop"
    )
    s.add_argument("--out")
    s.add_argument("--compare", help="a reference spec to compare the draft with")
    s.set_defaults(fn=cmd_draft_reads)

    s = sub.add_parser("check-reads", help="apply a read-gate spec to a results file")
    bench(s)
    s.add_argument("--spec", required=True)
    s.add_argument("--run", required=True, help="a results.json")
    s.set_defaults(fn=cmd_check_reads)

    s = sub.add_parser("twins", help="validate or build counterfactual twins")
    s.add_argument("action", choices=["validate", "build"])
    bench(s)
    s.add_argument("--twin-tasks", help="the adapter's own twin task file (tau2)")
    s.add_argument("--spec", help="a YAML list of twin specs (any benchmark)")
    s.add_argument("--out", help="build: write the valid twins here")
    s.set_defaults(fn=cmd_twins)

    s = sub.add_parser("flips", help="write one-sentence policy flips")
    s.add_argument("--policy", required=True)
    s.add_argument("--flips", required=True)
    s.add_argument("--out-dir", required=True)
    s.set_defaults(fn=cmd_flips)

    s = sub.add_parser(
        "pairs", help="pair scores: no-action pass counts only with its twin"
    )
    bench(s)
    s.add_argument("--twin-tasks", help="the adapter's own twin task file (tau2)")
    s.add_argument("--spec", help="a YAML list of twin specs (any benchmark)")
    s.add_argument("--orig", required=True, help="results path pattern with {m}")
    s.add_argument("--twins", required=True, help="glob of twin results paths with {m}")
    s.add_argument("models", nargs="+")
    s.set_defaults(fn=cmd_pairs)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
