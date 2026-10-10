---
title: No-op Doctor
type: index
status: current
updated: 2026-10-10
summary: >-
  The no-op doctor: one tool for the null-agent checkup, the read gate, counterfactual twins,
  policy flips and pair scoring, with a small adapter per benchmark. What each file does and
  how to run it.
note: >-
  First version. Only a tau2 adapter exists. Design and open choices:
  docs/research/noop-doctor-design.md.
---

# No-op Doctor

A benchmark gives credit to an agent that does nothing when the correct outcome of a task is
"no change". The doctor finds those tasks and applies our three treatments to them. It is kept
apart from `code/tau2-bench/`: it uses tau2 as a library and changes nothing in it.

Design and reasoning: `docs/research/noop-doctor-design.md`. Validation:
`docs/research/findings-log.md` §19.

## What each step does

| Step | Command | Needs from the benchmark | LLM? |
|---|---|---|---|
| Checkup | `checkup` | the do-nothing trajectory scored by its own grader | Only if the grader has an LLM judge (retail NL assertions) |
| Read gate, draft | `draft-reads` | gold tool calls, read/write tool labels | No |
| Read gate, apply | `check-reads` | the agent's tool calls in a results file | No |
| Twins | `twins validate`, `twins build` | a patchable initial state, a state grader | No. A person (or later an LLM) says what flips. |
| Policy flips | `flips` | the policy as text | No. A person says which sentence. |
| Pair scores | `pairs` | results of the original and the twin runs | No |

## Files

| File | What it does |
|---|---|
| `doctor.py` | The command line. |
| `noop_doctor/core/` | Benchmark-free logic. Imports no benchmark. |
| `noop_doctor/core/calls.py` | `ObservedCall`, `Episode`, `ToolKind`: the neutral records an adapter produces. |
| `noop_doctor/core/checkup.py` | Scores the do-nothing trajectory on every task; sorts the passes into "gold has reads" (a read gate can be drafted) and "no reads" (needs a person). |
| `noop_doctor/core/reads.py` | The read gate. Same rule and same JSON spec as `code/tau2-bench/src/tau2/evaluator/justification_core.py`, plus `draft_spec` (draft from gold reads) and `compare_specs`. |
| `noop_doctor/core/twins.py` | `TwinSpec` and `validate_twin`: null trajectory original 1 / twin 0, comply trajectory original 0 / twin 1, the patch changes the state and only the records it names. |
| `noop_doctor/core/flips.py` | One-sentence policy edits; the sentence must occur exactly once. |
| `noop_doctor/core/pairs.py` | Pair scoring and twin failure causes (no write, wrong write, transfer, right write + other error). |
| `noop_doctor/adapters/base.py` | The `Adapter` interface: what a benchmark must provide. |
| `noop_doctor/adapters/tau2.py` | τ²-bench adapter, any domain. Tool kinds come from tau2's `ToolType` labels. |
| `specs/retail-reads-draft.json` | Read-gate draft for the 6 retail no-op tasks, from gold reads. **Not audited.** |
| `tests/` | `test_core.py` (no benchmark), `test_tau2_adapter.py` (reproduces airline results). |

## Run

From `code/tau2-bench/`, so that tau2 and its data are found:

```bash
uv run python ../doctor/doctor.py checkup --bench tau2:telecom
uv run python ../doctor/doctor.py checkup --bench tau2:retail --nl-judge openai/openai/gpt-4.1   # needs a key, see below
uv run python ../doctor/doctor.py draft-reads --bench tau2:airline --skip-tool get_user_details \
  --compare data/tau2/domains/airline/justification.json
uv run python ../doctor/doctor.py check-reads --bench tau2:retail \
  --spec ../doctor/specs/retail-reads-draft.json --run data/simulations/retail_do_nothing/results.json
uv run python ../doctor/doctor.py twins validate --bench tau2:airline \
  --twin-tasks data/tau2/domains/airline/tasks_twins.json
uv run python ../doctor/doctor.py flips --policy data/tau2/domains/airline/policy.md \
  --flips ../twins/policy_flips.yaml --out-dir /tmp/flips
uv run python ../doctor/doctor.py pairs --bench tau2:airline \
  --twin-tasks data/tau2/domains/airline/tasks_twins.json \
  --orig 'data/simulations/airline_{m}' --twins 'data/simulations/airline_twins*_{m}' gpt-4.1 claude-sonnet-4.5
uv run --extra dev python -m pytest ../doctor/tests      # 17 tests, no API key
```

The retail NL judge reads its key from the environment. With Prime Intellect:
`export OPENAI_API_KEY="$PI_KEY" OPENAI_API_BASE="$PI_API_BASE"`. Do not put a key on the
command line.

`twins build` reads a YAML list of twin specs. This example rebuilds the airline twin
`48_twin_business`:

```yaml
- task: "48"
  name: business
  patch: {reservations: {3RK2T9: {cabin: business}}}
  write: {name: cancel_reservation, arguments: {reservation_id: 3RK2T9}}
  why: 3RK2T9.cabin is set to 'business', so the cancellation is allowed.
```

## Add a benchmark

Write one class with the methods in `noop_doctor/adapters/base.py`, and add its prefix to
`make_adapter` in `doctor.py`. Each step needs only part of the interface (see the table at
the top of `base.py`). The core does not change.

## Not built yet

- Running agents on twins and flipped policies for domains other than airline. Today that
  needs tau2 registry entries (`code/tau2-bench/src/tau2/registry.py`), which this tool
  does not touch.
- An LLM proposer for read specs and twins (design §7).
- An adapter for a benchmark other than τ²-bench.
