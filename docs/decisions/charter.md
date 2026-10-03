---
title: Project Charter
type: charter
status: current
updated: 2026-10-03
summary: >-
  What we are doing, why the problem is real, the rubric for a "justified" no-action verdict, the
  three goal tiers, and the open questions. Authoritative on scope.
note: >-
  Built from the two proposals in docs/external/. The formalization (2026-10-02) narrowed the
  initial proposal; see the decisions log for that change.
---

# Project Charter — Differentiating No-Action Outcomes in Agent Evaluations

**Last updated:** 2026-10-03 (created from the two proposals)

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

**Weak point:** the trajectories and hand grades behind this table are not yet in this
repository. See `docs/decisions/milestones.md`, M0.5.

---

## 2. The rubric: what makes a no-action verdict "justified"

The formalization grades each no-action trajectory on three checks:

1. **Evidence:** the agent ran the read tools it needed to learn the facts behind the refusal.
2. **No forbidden writes:** the agent did not try, or agree, to run a write tool that policy
   forbids.
3. **No premature transfer:** the agent did not hand the user to a human before it did the
   expected reasoning.

A pass is **justified** only if all three checks pass.

**Open:** the formalization lists check 2 as "tried or agreed to run forbidden write tools",
which reads as the failure condition. This charter states each check as the condition to pass.
Confirm this reading.

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

- **Null agent:** under the new evaluator, its no-action passes are all **unjustified**.
- **Capable models:** the automatic justified/unjustified labels agree with the hand grades in
  §1. Report the agreement rate and every disagreement.
- **No false rejections:** a correct refusal that uses a different (valid) sequence of reads
  than the reference trajectory is still graded justified.
- **Ranking effect:** report each model's accuracy before and after, and whether the ranking
  changes.

All scoring stays automatic.

---

## 5. Environment

- Benchmark: our copy of τ²-bench in `code/tau2-bench/` (upstream commit in `code/README.md`).
- Domains: **airline** first, then **retail**.
- Inference: Prime Intellect's OpenAI-compatible API, through LiteLLM. See `code/README.md`.

---

## 6. Open questions

1. How do we decide automatically which read tools are "necessary" for a task? From the
   reference actions, from the policy, or from an LLM judge?
2. Is a transfer to a human ever a justified no-action outcome? Some airline tasks may expect it.
3. Do we grade with rules, an LLM judge, or both? An LLM judge adds cost and its own validity
   problem.
4. The initial proposal targeted τ³-bench and a general detector of reward/criteria mismatches.
   The formalization narrowed to no-action verdicts. Does the detector idea come back for the
   Target or Stretch tier?

## Sources

- `docs/external/2026-10-02-initial-proposal.pdf`
- `docs/external/2026-10-02-proposal-formalization.pdf`
- `docs/papers/index.md`
