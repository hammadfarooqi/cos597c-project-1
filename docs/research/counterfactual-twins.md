---
title: Counterfactual Twins — Design and Coverage
type: research
status: current
updated: 2026-10-03
review_by: 2026-10-31
summary: >-
  How we generate counterfactual twins for the airline no-action tasks: the policy oracle, the
  per-task specs, the one-field DB search, and the validation with the real tau2 evaluator.
  Coverage of all 23 tasks, the exclusions, and the plan for policy-based tasks.
note: >-
  Extends docs/research/no-action-tasks.md §3 (per-task facts). Only DB-flip twins exist so far.
  Policy-flip twins are a plan, not built.
---

# Counterfactual Twins — Design and Coverage

**Last updated:** 2026-10-03

Decisions: `docs/decisions/decisions-log.md`, 2026-10-03 (twins; pair scoring rule).
Evidence: `docs/research/findings-log.md` §8. Code: `code/twins/`.

---

## 1. What a twin is

A twin is a copy of a no-action task in which **one** thing changes, so that the correct outcome
becomes a write. The user script stays the same. An agent that refused the original for the
right reason makes the write in the twin. An agent that refuses, or transfers, no matter what
fails the twin.

**Pair rule.** A no-action pass counts only if the same agent also passes the twin. A twin pass
with a failed no-action task is a failure (the agent writes no matter what).

## 2. Why the generator needs a policy oracle

The airline tools do not enforce the policy. `policy.md` says: "The API does not check that
cancellation rules are met." So a write tool always succeeds, whether or not policy allows it.
To know that a flip makes a write *allowed*, the generator needs the policy as code:
`code/twins/airline_policy.py`.

Encoded so far:

- **Cancellation:** not flown, and one of: booked within 24 h, airline cancelled a flight,
  business cabin, insured with a covered reason (health or weather).
- **Cancelled-flight certificate:** silver/gold, or insured, or business; $100 × passengers.

Not encoded: flight changes, cabin changes, baggage, delay certificates.

## 3. The pipeline

For each spec in `code/twins/specs/airline.yaml`:

1. **Spec** (hand-written, about 5 lines): the write the user pushes for, the stated reason,
   the facts the user's script **locks** (for example, task 0 admits the booking is more than
   24 h old, so that flip is banned), and the preferred flip.
2. **Oracle check:** the oracle must block the write in the original DB. If not, the spec is
   wrong and the generator stops.
3. **Search:** for each unlocked condition, apply a one-field edit (`created_at`, `cabin`, or
   `insurance`) and keep it if the oracle now allows the write.
4. **Build:** copy the task. Put the edit in `initial_state.initialization_data.agent_data`
   (tau2 deep-merges it into the DB). Append the write to the gold actions. The shared `db.json`
   does not change.
5. **Validate** with the real `EnvironmentEvaluator` on synthetic trajectories:
   - null trajectory: original 1, twin 0;
   - comply trajectory (the expected reads + the write): original 0, twin 1;
   - only the patched DB records change.
6. **Live check** (manual so far): run one strong model on the twin. Section 5 shows why.

Output: `code/tau2-bench/data/tau2/domains/airline/tasks_twins.json` and
`split_tasks_twins.json` (`base` = all valid twins, `primary` = one per task). They load as the
task set `airline_twins`:

```bash
uv run tau2 run --domain airline --task-set-name airline_twins --task-split-name primary ...
```

## 4. Coverage of the 23 no-action tasks

| Group | Tasks | Twin |
|---|---|---|
| DB-decided, twin built | 0, 1, 9, 26, 28, 41, 43, 45, 47, 48, 49 | One-field DB flip. 22 valid flips, 11 primary. |
| DB-decided, excluded | 31, 36 | The write is not unique: several flights fit, and the script names no payment method. |
| DB-decided, tried and dropped | 4 | See §5. |
| Policy rule + user intent | 2, 5, 27, 38 | Planned: policy flip (§6). |
| Policy rule alone | 6, 13, 46 | 6: request flip possible. 13: also blocked by basic economy; write not unique. 46: no tool and no rule. |
| Policy + price | 10, 34 | No clean twin. 10: the tool cannot change the cabin of one segment. 34: price-driven. |

Primary flip per built task: business cabin for 0, 9, 26, 28, 41, 45, 47; booked within 24 h
for 1, 43, 48; insurance for 49. In 48 and 49 the flip makes the user's own claim true
("booked 10 hours ago", "I have insurance").

## 5. Lesson from task 4: the user's goal must be reachable

The task 4 twin made the user's false story true (WUNA5K business, HAT271 on 05-10 cancelled).
It passed every static check. In live runs, all 5 models offered the $100 certificate or tried
to, but the user script wants more than policy allows. The user refused and asked for a
transfer, so no model could pass. The static checks prove that the write is allowed and that
the verdicts flip. They cannot prove that the simulated user accepts the correct outcome. A live
check with one strong model is needed for every new twin type.

## 6. Plan: policy-flip twins

For policy-based tasks no DB edit makes the request allowed. The decisive variable is the rule.
Three kinds of twin change one thing:

| Type | What changes | What it tests |
|---|---|---|
| Policy flip | One sentence of `policy.md` | Does the agent follow the written rule, or its prior? |
| Request flip | What the user asks for | Does the agent know which request the rule covers? |
| Intent flip | The user's stated condition | Does the agent track the condition the rule depends on? |

The policy flip is the cleanest: user, conversation, and DB stay the same. First target: tasks
2, 5, 27, and 38 all turn on one clause ("...and wants to change or cancel the reservation").
One edit gives 4 twins, each with one correct write that the user accepts:

| Task | Eligible because | Correct write in the twin |
|---|---|---|
| 27 | silver member | `send_certificate(ethan_martin_2396, 150)` (3 passengers) |
| 5 | business reservation 3JA7XV | `send_certificate(mei_brown_7075, 200)` (4 passengers) |
| 2, 38 | gold member | `send_certificate(noah_muller_9847, 50)` (1 passenger; the user claims 3) |

tau2 gives one policy per domain, so these twins can run under a second registered domain with
the same tools and DB and the one sentence replaced. Represent each rule as an ID, its exact
sentence, and a predicate, and flip the text and the predicate together.

The same idea applies to the DB-decided tasks: a **rule twin** (for example, "basic economy can
be cancelled within 14 days") next to the **fact twin**. Each task then has a 2×2 design, and a
failure can be attributed to the rule or to the fact.

## 7. Weak points

- Specs are hand-written. Most could be drafted from `nl_assertions` ("Agent does not cancel
  3RK2T9"); the oracle check catches a wrong spec.
- A twin also tests whether the agent can do the write correctly. A twin failure is not always
  a blanket refusal. `code/twins/score_pairs.py` reports the cause of each twin failure.
- The DB flips use business cabin for 7 of 11 tasks. A model that always agrees to cancel
  business bookings passes those twins without the right reason for the original.
- Single-trial runs vary (findings-log §7, §8). The pair rule needs two good episodes, so the
  noise compounds. Use several trials.
- Changing `cabin` without changing stored prices leaves the reservation's prices at their basic
  economy values. No cancel twin depends on price, but a change twin would.
