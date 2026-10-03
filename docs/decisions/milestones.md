---
title: Milestones
type: milestones
status: current
updated: 2026-10-03
summary: >-
  The master tracker. Every milestone, its owner, its status, and the evidence that it is done.
  Update it in the same commit as the work.
note: >-
  Due dates are TBD until we confirm the course deadlines. Owners marked "?" are not yet assigned.
---

# Milestones — Master Tracker

**Last updated:** 2026-10-03

**How to use this file** (rules in `CLAUDE.md` §5.3):

- Status is one of: `todo` · `in progress` · `blocked` · `done` · `dropped`.
- Change a row in the same commit as the work it describes.
- A `done` row must link to evidence: a findings-log entry, a results folder, or a commit.
- Never delete a row. Mark it `dropped` and add a decisions-log entry that says why.
- Add rows when the plan grows. Keep the IDs stable.

---

## Now

The next thing each person is doing. Keep this short.

| Who | Working on |
|---|---|
| Hammad | ? |
| Vatsal | ? |

---

## M0 — Setup and baselines

| ID | Milestone | Owner | Due | Status | Evidence |
|---|---|---|---|---|---|
| M0.1 | Shared repository with docs, code, and results | Hammad | — | done | this repository, 2026-10-03 |
| M0.2 | Do-nothing agent and scripted user in tau2 | Hammad | — | done | `code/tau2-bench/src/tau2/agent/do_nothing_agent.py` |
| M0.3 | Null-agent baseline, airline (23/50) | Hammad | — | done | `docs/research/findings-log.md` §1 · `code/tau2-bench/data/simulations/airline_do_nothing/` |
| M0.4 | Null-agent baseline, retail (6/114) | ? | — | todo | Number is in the proposal, but the results file is not in the repository. Re-run and commit it. |
| M0.5 | Commit the 5-model runs and hand grades behind the formalization table | ? | — | todo | Needed to validate any automatic grader (M1.4). |
| M0.6 | GPT-4.1 airline run through Prime Intellect (25/50) | Hammad | — | done | `docs/research/findings-log.md` §2 · `code/tau2-bench/data/simulations/airline_gpt41_check/` |

## M1 — Minimal goal: justified vs unjustified no-action in τ²-bench

| ID | Milestone | Owner | Due | Status | Evidence |
|---|---|---|---|---|---|
| M1.1 | List the airline no-action tasks and what each one expects (refusal, transfer, read-only answer) | ? | TBD | todo | |
| M1.2 | Settle the rubric: how to detect "necessary reads", "forbidden write", "premature transfer" (charter §6, Q1–Q3) | ? | TBD | todo | |
| M1.3 | Implement the grader in the tau2 evaluator, reported next to the existing reward | ? | TBD | todo | |
| M1.4 | Validate the grader against the hand grades (agreement rate, every disagreement) | ? | TBD | todo | needs M0.5 |
| M1.5 | Null agent: all no-action passes graded unjustified, airline and retail | ? | TBD | todo | |
| M1.6 | Re-score the 5 models; report accuracy and ranking before vs after | ? | TBD | todo | |
| M1.7 | Extend to retail | ? | TBD | todo | |
| M1.8 | Write-up of the Minimal result | ? | TBD | todo | |

## M2 — Target goal: 1–2 other benchmarks

| ID | Milestone | Owner | Due | Status | Evidence |
|---|---|---|---|---|---|
| M2.1 | Choose 1–2 benchmarks with the same outcome-validity issue | ? | TBD | todo | |
| M2.2 | Measure the null-agent pass rate on each | ? | TBD | todo | |
| M2.3 | Apply the grader and report before vs after | ? | TBD | todo | |

## M3 — Stretch goal: a general framework

| ID | Milestone | Owner | Due | Status | Evidence |
|---|---|---|---|---|---|
| M3.1 | Define the framework's interface (what a benchmark must supply) | ? | TBD | todo | |
| M3.2 | Show it on τ²-bench and one other benchmark without per-benchmark code | ? | TBD | todo | |

---

## Change history

Append one line per change to this file: date, who, which rows.

- 2026-10-03 — Hammad + Claude — created; M0.1, M0.2, M0.3, M0.6 done.
