---
title: Milestones
type: milestones
status: current
updated: 2026-10-10
summary: >-
  The master tracker. Every milestone, its owner, its status, and the evidence that it is done.
  Update it in the same commit as the work.
note: >-
  Due dates are TBD until we confirm the course deadlines. Owners marked "?" are not yet assigned.
---

# Milestones — Master Tracker

**Last updated:** 2026-10-10

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
| M0.5 | Commit the 5-model runs and hand grades behind the formalization table | Vatsal | — | in progress | Runs: re-run and committed (M0.7). Hand grades: not yet in the repository. Needed for M1.4. |
| M0.6 | GPT-4.1 airline run through Prime Intellect (25/50) | Hammad | — | done | `docs/research/findings-log.md` §2 · `code/tau2-bench/data/simulations/airline_gpt41_check/` |
| M0.7 | Five-model airline runs, all 50 tasks, 1 trial (sonnet-4.5, gpt-4.1, mini, nano, llama-3.3-70b) | Vatsal + Claude | — | done | `docs/research/findings-log.md` §7 · `code/tau2-bench/data/simulations/airline_<model>/` |
| M0.8 | Newer models (claude-haiku-4.5, gpt-6-luna, gpt-5.4-nano): 50 airline tasks + 15 twins, 1 trial | Vatsal + Claude | — | done | `docs/research/findings-log.md` §15 · `code/tau2-bench/data/simulations/airline*_<model>/` |
| M0.9 | llama-4-maverick: 50 airline tasks + 15 twins, 1 trial, with the tool-call retry; one table for all 9 models | Vatsal + Claude | — | done | `docs/research/findings-log.md` §16–§17 · `code/tau2-bench/data/simulations/airline*_llama-4-maverick/` |

## M1 — Minimal goal: justified vs unjustified no-action in τ²-bench

| ID | Milestone | Owner | Due | Status | Evidence |
|---|---|---|---|---|---|
| M1.1 | List the airline no-action tasks and what each one expects (refusal, transfer, read-only answer) | Hammad + Claude | — | done | `docs/research/no-action-tasks.md` · `docs/research/findings-log.md` §5–§6 |
| M1.2 | Settle the rubric: how to detect "necessary reads", "forbidden write", "premature transfer" (charter §6, Q1–Q3) | Hammad + Claude | — | done | `docs/decisions/decisions-log.md` 2026-10-03: mandatory reads + twins; forbidden-write and transfer checks set aside |
| M1.3 | Implement the grader in the tau2 evaluator, reported next to the existing reward | Hammad + Vatsal + Claude | TBD | in progress | Read gate: done, in the evaluator (`docs/research/justification-check.md` · `docs/research/findings-log.md` §14). Pair scoring: a script only (`code/twins/score_pairs.py`), not yet in the evaluator |
| M1.4 | Validate the grader against the hand grades (agreement rate, every disagreement) | ? | TBD | todo | needs M0.5. Sanity check only: the pilot grades used the old rubric (charter §1) |
| M1.5 | Null agent: all no-action passes graded unjustified, airline and retail | Hammad + Claude | — | in progress | Airline done: 23 → 7, all 16 spec tasks gated (findings-log §14). The 7 left are no-data tasks + 38, by design. Retail not started. |
| M1.6 | Re-score the 5 models; report accuracy and ranking before vs after | ? | TBD | in progress | Reads: 4 released models re-scored (findings-log §14), ranking unchanged. Twins: 5 new-run models paired (findings-log §9), llama 19 → 7. Still needed: one scoreboard with all three scores, more trials (M1.17). |
| M1.7 | Extend to retail | ? | TBD | todo | |
| M1.8 | Write-up of the Minimal result | ? | TBD | todo | |
| M1.9 | Finalize the mandatory-read list per task | Hammad + Claude | — | done | `code/tau2-bench/data/tau2/domains/airline/justification.json` · `docs/research/justification-check.md` §7 |
| M1.10 | Score the natural twins as pairs (41↔39, 9↔37, 34↔33) on fresh runs; verify the task 39 gold (MSJ4OA) first | ? | TBD | todo | first look: `docs/research/findings-log.md` §6 |
| M1.11 | Build the first clean DB-flip twins (tasks 48, 49) with `initial_state` patches; run them | Vatsal + Claude | — | done | `docs/research/findings-log.md` §8 · `code/twins/` |
| M1.12 | Build the remaining DB-flip twins (0, 1, 4, 26, 28, 31, 41, 43, 45, 47) | Vatsal + Claude | — | done | Built 0, 1, 9, 26, 28, 41, 43, 45, 47 (+48, 49). Excluded 31, 36 (write not unique) and 4 (user goal unreachable). `docs/research/counterfactual-twins.md` §4 |
| M1.13 | Scripted blanket-refuser agent (reads everything, refuses everything) as a test agent | ? | TBD | todo | charter §4 |
| M1.14 | Re-score the 4 released upstream airline runs with `--fresh-tasks` before any use | Hammad + Claude | — | done | `docs/research/findings-log.md` §4 (outputs not committed, ~36 MB; command given) |
| M1.15 | Twin generator: policy oracle, specs, one-field search, validation with the evaluator, `airline_twins` task set | Vatsal + Claude | — | done | `code/twins/` · `docs/research/counterfactual-twins.md` |
| M1.16 | Policy-flip twins for the delay-compensation clause (tasks 2, 5, 27, 38) | Vatsal + Claude | — | done | `docs/research/findings-log.md` §9 · `code/twins/policy_flips.yaml` |
| M1.17 | Re-run no-action tasks and twins with 4 trials; paired scores per trial | ? | TBD | todo | single-trial noise: findings-log §7, §8 |
| M1.18 | More policy flips: rule twins for the DB-decided tasks (2×2 fact/rule design); request flip for task 6 | ? | TBD | todo | `docs/research/counterfactual-twins.md` §6 |
| M1.19 | Close the task 31 loophole (budget $100 → $65) | Hammad + Claude | — | done | `docs/research/loophole-airline-31.md` · decisions log 2026-10-03 |
| M1.20 | Verify the task 31 fix with a fresh run (user declines the $81 offer) | ? | TBD | todo | `docs/research/loophole-airline-31.md` §5 |

## M2 — Target goal: 1–2 other benchmarks

| ID | Milestone | Owner | Due | Status | Evidence |
|---|---|---|---|---|---|
| M2.1 | Choose 1–2 benchmarks with the same outcome-validity issue | ? | TBD | todo | |
| M2.2 | Measure the null-agent pass rate on each | Vatsal + Claude | — | in progress | tau2 retail 6/114, telecom 0/114: `docs/research/findings-log.md` §18. Non-tau2 benchmark not chosen yet (M2.1). |
| M2.3 | Apply the grader and report before vs after | ? | TBD | todo | |

## M3 — Stretch goal: a general framework

| ID | Milestone | Owner | Due | Status | Evidence |
|---|---|---|---|---|---|
| M3.1 | Define the framework's interface (what a benchmark must supply) | Hammad + Claude | — | in progress | First version: a JSON spec + a list of `ObservedCall` (`docs/research/justification-check.md` §3, §10). Not yet tried on a second benchmark. |
| M3.2 | Show it on τ²-bench and one other benchmark without per-benchmark code | ? | TBD | todo | |
| M3.3 | No-op doctor: one tool for checkup, read gate, DB twins, policy flips, with an adapter per benchmark | Vatsal + Claude | — | in progress | Built for tau2 in `code/doctor/`; reproduces the airline results (`docs/research/findings-log.md` §19). Not yet: LLM proposer, non-tau2 adapter, agent runs on non-airline twins. |

---

## Change history

Append one line per change to this file: date, who, which rows.

- 2026-10-03 — Hammad + Claude — created; M0.1, M0.2, M0.3, M0.6 done.
- 2026-10-03 — Hammad + Claude — M1.1, M1.2, M1.14 done; M1.4 note; added M1.9–M1.13 (mandatory reads and twins).
- 2026-10-03 — Vatsal + Claude — added M0.7 (done); M0.5 in progress (runs committed, hand grades missing).
- 2026-10-03 — Vatsal + Claude — M1.11, M1.12 done (with exclusions); M1.3 in progress; added M1.15 (done), M1.16, M1.17.
- 2026-10-03 — Vatsal + Claude — M1.16 done; added M1.18.
- 2026-10-03 — Hammad + Claude — M1.15 done (task 31 budget fix); added M1.16. (Renumbered M1.19, M1.20 at the 2026-10-08 merge.)
- 2026-10-03 — Hammad + Claude — M1.3, M1.9 done; M1.5, M1.6, M3.1 in progress (justification check implemented).
- 2026-10-08 — Hammad + Claude — merged all branches: M1.3 set to in progress (read gate done, pair scoring still a script); Hammad's M1.15, M1.16 renumbered M1.19, M1.20; M1.5, M1.6 evidence updated.
- 2026-10-09 — Vatsal + Claude — added M0.8 (done): three newer models, airline + twins.
- 2026-10-09 — Vatsal + Claude — added M0.9 (done): llama-4-maverick, airline + twins; 9-model table.
- 2026-10-09 — Vatsal + Claude — M2.2 in progress (retail, telecom checkup); added M3.3 (no-op doctor design).
- 2026-10-10 — Vatsal + Claude — M3.3: first build of the no-op doctor (`code/doctor/`).
