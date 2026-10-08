---
title: Task 31 — A Policy Loophole and Our Fix
type: research
status: current
updated: 2026-10-08
review_by: 2026-12-01
summary: >-
  Airline task 31 expects "no change", but a policy-legal route (upgrade the cabin, then change
  the flight) cost $81 and fit the user's $100 budget. We lowered the budget to $65. This note
  explains the loophole, the evidence, what we changed, and what to say in the write-up.
note: >-
  Important finding. Any result on task 31 from our copy is NOT comparable with upstream
  τ²/τ³-bench results on task 31.
---

# Task 31 — A Policy Loophole and Our Fix

**Last updated:** 2026-10-08 (findings-log references renumbered)

Decision: `docs/decisions/decisions-log.md`, 2026-10-03, "Lower task 31's budget to $65".
Raw evidence: `docs/research/findings-log.md` §11 (first analysis) and §12 (correction).

---

## 1. Summary

- **Task 31:** Daiki Lee has a **basic economy** round trip, JFK→DTW (reservation DF89BM). He
  wants his May 17 outbound (one stop) changed to a nonstop. The expected outcome is **no
  change**, because "basic economy flights cannot be modified".
- **The loophole:** the policy also says "all reservations, including basic economy, can change
  cabin without changing the flights". So an agent can:
  1. upgrade the cabin to economy (same flights), then
  2. change the now-economy reservation to a nonstop.

  Each step obeys the policy. The cheapest version costs **$81 net**, which was under the user's
  $100 budget.
- **Why it matters:** a capable agent can find this route, the simulated user can accept it, and
  the task then scores 0. This happened in a released o4-mini run.
- **Our fix:** the user's budget is now **$65**. Every legal route costs at least $81, so the
  user declines all of them. The expected outcome ("no change") is now correct under both
  readings of the policy.

## 2. The loophole in detail

### 2.1 The two readings of the policy

| Reading | Rule | Task 31 outcome |
|---|---|---|
| A, "no workaround" | Basic economy cannot be modified; upgrading first is a workaround | No change (the gold) |
| B, "composition is legal" | Cabin change is allowed; then the reservation is economy, and economy can be modified | Change for $81 |

- The policy text supports both. Cao (2026) names this pattern "compositional ambiguity (L6)".
- The benchmark uses **both** readings:
  - **Task 32** (same scenario, sick mother): the gold *is* reading B.
  - **Task 45**: the maintainers chose reading A. Their τ³ fix notes say the workaround "should be
    disallowed". They blocked it with the user line "Under NO circumstances will you upgrade your
    cabin".
  - **Task 31** never got a fix like task 45's. Upstream `main` and Amazon's τ²-Bench-Verified
    have the same task 31 as the original.

### 2.2 Every legal route and its cost

Prices from `code/tau2-bench/data/tau2/domains/airline/db.json`. Costs computed the way
`update_reservation_flights` computes them (1 passenger; Daiki paid $194).

| Cabin | Outbound nonstop (05-17) | Return (05-24) | Net cost |
|---|---|---|---|
| economy | HAT033 | HAT263 (kept) | **$81** |
| economy | HAT088 / HAT092 / HAT212 | HAT263 | $118 / $121 / $124 |
| business | HAT092 | HAT240 (swapped) | $258 |
| business | others | — | $262 and more |

- A swap of the return flight on the same day does not help: the cheapest economy return is
  HAT263 itself ($140).
- Cancel-and-rebook is not legal: DF89BM is basic economy, has no insurance, and was booked
  more than 24 h ago.
- The user also says "You do not want to buy a new flight".

### 2.3 How the task drifted

- In the **original τ-bench**, the user said: "You are willing to pay a fee for the flight change
  **only**, upto $100." That "only" excluded paying for an upgrade.
- The next task, Ivan (our task 32), said the opposite: "If the agent says your ticket is a basic
  economy one, you are willing to upgrade to economy in order to make the change."
- So the original pair was a **designed contrast**: same situation, different willingness to
  upgrade.
- τ²-bench (first release, commit `37199f3`, 2025-06) rewrote Daiki's line to "only if it costs
  less than $100. You do not want to buy a new flight." The upgrade exclusion was lost.

### 2.4 Evidence that agents find the route

- **o4-mini, task 31, trial 3** (released upstream run, re-scored with `--fresh-tasks`):
  1. The agent said basic economy cannot be changed and offered an upgrade.
  2. The user replied "I'd be open to upgrading if the total cost to change is less than $100".
  3. The agent changed the reservation and scored 0.

  (That run also misquoted the price, $34 against a real $121 charge. A correct $81 run would
  still score 0.)
- **Cao (2026)** reports agents taking the same two-step route on tasks 32 and 45 ("Agents that attempt the two-step workaround … split with those that refuse").

## 3. What we changed

- **File:** `code/tau2-bench/data/tau2/domains/airline/tasks.json`, task `"31"`.
- **`user_scenario.instructions.task_instructions`:** "$100" → "**$65**". No other word changed.
- **`description.notes`:** a pointer to this document. Only the display code reads this field;
  the agent and the simulated user never see it.
- **Not changed:** the policy, the database, the gold (`actions: []`), and `reward_basis`.

### Why $65 and not another number

- **$80** would block the cheapest route ($81) by only $1. A simulated user (an LLM) could round
  $81 to "about $80" and accept.
- **$65** blocks it by $16 while staying a realistic budget.
- **A "no upgrade" user line** (the maintainers' fix for task 45) was the alternative. We did not
  choose it, because it takes reading A's side on the loophole. The budget fix keeps both readings
  valid: an agent may refuse (reading A) or offer the upgrade and quote $81 (reading B), and either
  way the user declines.

### Side effect to keep in mind

- An agent that offers the upgrade now ends with "no change" because of **price**, not policy.
  Both paths are now correct.
- The read check for task 31 still holds: both paths need `get_reservation_details(DF89BM)`.
- A **wrong** price quote is still caught. If the agent quotes under $65 and makes the change, the
  DB check fails.

## 4. What to write in the report

- "We changed one task. In airline task 31, a policy-legal two-step route (upgrade the cabin, then
  modify) cost $81 and fit the user's $100 budget, which contradicts the expected 'no change'
  outcome. The policy is ambiguous on whether these steps compose (Cao 2026, 'L6'), and the
  benchmark resolves the same ambiguity in opposite ways in tasks 32 and 45. We lowered the user's
  budget to $65, so that every legal route exceeds it and the expected outcome holds under both
  readings."
- Report task 31 results as **not comparable** with upstream task 31 results.
- Cite: Cao (2026) for the loophole taxonomy; SABER for the earlier flag on this task; the τ³ fix
  notes for the maintainers' position.

## 5. Open points

- Not yet verified by a fresh run. Run task 31 with 1–2 models after the change, and confirm that
  the simulated user declines the $81 offer.
- The route search covered the requested change (a nonstop outbound on 05-17) and same-day
  returns. An agent that also proposes moving the return to another day was not checked. The user
  did not ask for that.

## Sources

- `code/tau2-bench/data/tau2/domains/airline/tasks.json`, `db.json`, `policy.md`;
  `code/tau2-bench/src/tau2/domains/airline/tools.py`
- Original τ-bench task:
  <https://github.com/sierra-research/tau-bench/blob/main/tau_bench/envs/airline/tasks_test.py>
- τ³ task fixes: <https://taubench.com/blog/tau3-task-fixes.html>
- Cao (2026), *Policy Loopholes in Agent Evaluation*, arXiv 2609.14400
  (`docs/papers/2026-cao-policy-loopholes.pdf`)
- Cuadron et al., *SABER* / τ-Bench Verified, arXiv 2512.07850 (`docs/papers/2025-cuadron-saber.pdf`)
- Amazon τ²-Bench-Verified: <https://github.com/amazon-agi/tau2-bench-verified>
