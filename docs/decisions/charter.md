---
title: Project Charter
type: charter
status: current
updated: 2026-10-08
summary: >-
  What we are doing, why the problem is real, how we grade a "justified" no-action verdict
  (mandatory necessary reads + counterfactual twin tasks), the three goal tiers, and the open
  questions. Authoritative on scope.
note: >-
  Built from the two proposals in docs/external/. The formalization (2026-10-02) narrowed the
  initial proposal. On 2026-10-03 the formalization's three-check rubric was replaced by two
  mechanisms; see the decisions log.
---

# Project Charter — Differentiating No-Action Outcomes in Agent Evaluations

**Last updated:** 2026-10-08 (§6 Q1 reads answered for airline; Q2–Q4 settled: pair scoring, policy flips)

Hammad Farooqi, Vatsal Parikh · COS597C, Fall 2026

---

## 0. The whole thing in one paragraph

Zhu et al. showed that τ-bench gives credit to agents that do nothing. τ²-bench still does. Our
null agent takes no action and says nothing, and it passes **23 of 50 airline tasks (46%)** and
**6 of 114 retail tasks (5.3%)**. On many of these tasks, doing nothing **is** the correct
outcome: the user pushes the agent to break policy, and the agent must refuse. But the evaluator
only checks that the database did not change, so a refusal for the right reasons and an accident
look the same. We will change τ²-bench so that a no-action verdict is graded as **justified** or
**unjustified**.

---

## 1. Why this matters

A hand-graded pilot on the 23 no-action airline tasks (from the formalization, 2026-10-02):

| Model | Evaluator passes | Hand-graded true passes | Passes for the wrong reason | Main wrong-reason pattern |
|---|---|---|---|---|
| claude-sonnet-4.5 | 21 | 17 | 4 | mixed |
| gpt-4.1 | 21 | 12 | 9 | agreed to a forbidden write (6) |
| gpt-4.1-mini | 20 | 11 | 9 | agreed to a forbidden write (5) |
| llama-3.3-70b | 21 | 0 | 21 | unneeded transfer (17) |
| gpt-4.1-nano | 4 | 0 | 4 | 19 harmful writes (evaluator caught) |

The padding is **not equal across models**. llama-3.3-70b gets 21 wrong-reason passes (42% of
airline). claude-sonnet-4.5 gets 4 (8%). Unequal padding can reorder a leaderboard.

**Weak points:**

- The trajectories and grades behind this table are not yet in this repository. See
  `docs/decisions/milestones.md`, M0.5.
- The grades were made with Opus 5.5 against the formalization's three-check rubric, which §2 no
  longer uses. Two of its wrong-reason patterns ("agreed to a forbidden write", "unneeded
  transfer") are not what our mechanisms measure directly. Treat agreement with this table as a
  sanity check, not as ground truth.

---

## 2. How we grade a no-action verdict

Decision: `docs/decisions/decisions-log.md`, 2026-10-03. Per-task detail:
`docs/research/no-action-tasks.md`.

We use two mechanisms. Both are deterministic. Neither uses an LLM judge.

1. **Mandatory necessary reads.** For each no-action task we list the reads that reveal the
   decisive fact (for example `get_reservation_details(3RK2T9)` shows that the booking is
   13 days old). A no-action pass counts only if the agent ran every listed read. 15 of the 23
   tasks already list these reads, but the evaluator does not count them today
   (`docs/research/findings-log.md` §5).
2. **Counterfactual twin tasks.** For each no-action task we build a copy in which **only the
   decisive fact** flips (for example, reservation 3RK2T9 now has insurance), so the correct
   outcome becomes a write. The user script stays the same where possible. An agent that refused
   for the right reason passes both tasks. An agent that refuses or transfers no matter what
   fails the twin. tau2 supports the per-task database patch already
   (`initial_state.initialization_data`).

A no-action pass is **justified** when the agent ran the mandatory reads **and** passes the
twin. The read check is implemented: `docs/research/justification-check.md` (rule, spec format,
scoring modes, code, and how to reuse it on another benchmark). Reads alone are not enough: an agent that reads everything and then refuses everything
passes them. That agent is the reason the twins exist.

Not every task can have a clean twin. Tasks 6 and 46 have no write tool at all, and the
compensation tasks (2, 5, 27, 38) turn on the user's intent, not on a database field. For these,
only the mandatory reads apply, or the twin must change the user script.

**Set aside** (decisions log, 2026-10-03): the formalization's "no forbidden writes" and "no
premature transfer" checks.

---

## 3. Goals

| Tier | Goal |
|---|---|
| **Minimal** | Modify τ²-bench so that no-action verdicts are differentiated as justified or unjustified. |
| **Target** | Look at 1–2 other benchmarks and fix similar outcome-validity issues. |
| **Stretch** | Create a generalizable framework that targets this validity issue for any benchmark. |

Concrete steps and status: `docs/decisions/milestones.md`.

---

## 4. How we will know it works

- **Null agent:** under the new evaluator, its no-action passes are all **unjustified**. (The
  mandatory reads alone do this. It is a necessary test, not a strong one.)
- **Scripted blanket refuser:** a scripted agent that runs every listed read and then refuses
  every request must also be graded **unjustified** on every task that has a twin. This is the
  test that the twins earn their cost.
- **No false rejections:** a correct refusal that reaches the decisive fact through a different
  valid sequence of reads is still graded justified. A twin fails only when the agent does not
  make the correct write.
- **Capable models:** report each model's pass rate on the originals, on the twins, and on the
  pairs. Compare with the pilot grades in §1 as a sanity check.
- **Ranking effect:** report each model's accuracy before and after, and whether the ranking
  changes.

All scoring stays automatic and rule-based.

---

## 5. Environment

- Benchmark: our copy of τ²-bench in `code/tau2-bench/` (upstream commit in `code/README.md`).
- Domains: **airline** first, then **retail**.
- Inference: Prime Intellect's OpenAI-compatible API, through LiteLLM. See `code/README.md`.

---

## 6. Open questions

1. **Which reads are "necessary"?** Answered for airline: the rule in
   `docs/research/justification-check.md` §2.1 and the 16-task spec. Background: start from the reads listed in the task
   files (15 of 23 tasks) and add reads for the other 8 (`docs/research/no-action-tasks.md` §3).
   Still open: in tasks 2, 5, 6, 27, 38 the policy blocks the request without any data, so the
   listed reads reflect the author's intent, not necessity. We have not decided whether to keep
   them, or whether reads must happen *before* the refusal.
2. **How do we score a pair?** Settled (decisions log, 2026-10-03): the original counts only if
   its twin also passes. Report original, twin, and paired rates side by side.
3. **What counts as a twin failure?** A twin can fail because the agent refused, transferred, or
   made the wrong write. Report the reason. Only the first two show a blanket refuser.
   Partly settled: any twin failure removes the credit (strict); the lenient rate, which
   accepts the right write despite other errors, is reported next to it.
4. **Twins for the compensation tasks (2, 5, 27, 38)** need a script change, not a database flip.
   Settled (decisions log, 2026-10-03): a policy flip changes one sentence of `policy.md` and
   keeps the user, the script, and the DB the same (`docs/research/counterfactual-twins.md` §6).
5. **Retail.** We have not yet checked which retail no-action tasks allow twins.
6. The initial proposal targeted τ³-bench and a general detector of reward/criteria mismatches.
   The formalization narrowed to no-action verdicts. Does the detector idea come back for the
   Target or Stretch tier?

## Sources

- `docs/external/2026-10-02-initial-proposal.pdf`
- `docs/external/2026-10-02-proposal-formalization.pdf`
- `docs/papers/index.md`
