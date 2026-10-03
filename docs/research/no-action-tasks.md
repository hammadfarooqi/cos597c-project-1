---
title: The 23 Airline No-Action Tasks — Required Reads and Twins
type: research
status: current
updated: 2026-10-03
review_by: 2026-10-31
summary: >-
  For each of the 23 airline tasks that the null agent passes: the decisive fact, the reads the
  task already expects, the reads we propose to make mandatory, and its counterfactual twin
  (natural, or a proposed one-field database flip).
note: >-
  Facts are from the vendored tau2-bench (upstream b7ea907). Re-check them if we pull upstream
  task changes. Twin flips are proposals; none is built or run yet.
---

# The 23 Airline No-Action Tasks — Required Reads and Twins

**Last updated:** 2026-10-03

This note supports the two mechanisms chosen on 2026-10-03 (`docs/decisions/decisions-log.md`):

1. **Mandatory necessary reads.** A no-action pass counts only if the agent ran the reads that
   reveal the decisive fact.
2. **Counterfactual twin tasks.** A copy of the task where only the decisive fact flips, so the
   correct outcome becomes a write. An agent that refuses for the right reason passes both. An
   agent that always refuses (or always transfers) fails the twin.

Evidence for the numbers here: `docs/research/findings-log.md` §4–§6.

---

## 1. Facts that apply to all 23 tasks

- The policy clock is **2024-05-15 15:00 EST** (`code/tau2-bench/data/tau2/domains/airline/policy.md`).
- All 23 tasks have `reward_basis = [DB, COMMUNICATE]` and `communicate_info = []`. Only the DB
  check counts.
- **15 of 23** tasks list expected read actions in `evaluation_criteria.actions`. The evaluator
  checks them, but ACTION is not in `reward_basis`, so they do not count.
- **8 of 23** tasks list no reads: 0, 10, 13, 26, 28, 31, 34, 46. (Task 13 lists only a
  `transfer_to_human_agents` action.)
- The action check matches **all** arguments when `compare_args` is not set. For reads this is
  correct: the arguments are IDs, so any valid path to the fact makes the same call.

## 2. How a twin is built

tau2 already supports a per-task database patch. A task's
`initial_state.initialization_data.agent_data` is deep-merged into the default database before
the episode (`code/tau2-bench/src/tau2/environment/toolkit.py`, `update_db`). We tested it:
the patch `{"reservations": {"3RK2T9": {"insurance": "yes"}}}` changes only that field.

So a twin is a copy of the task with:

- a one-field patch in `initial_state`,
- the expected write added to `evaluation_criteria.actions` (so the gold DB includes it),
- the same user script, when the script still makes sense after the flip.

The shared `db.json` does not change. This matters, because some reservations appear in several
tasks (for example 3RK2T9 in tasks 40, 48, and 49).

**Twin types, best first:**

- **DB flip** — one field changes; the user script stays the same.
- **Script flip** — the decisive fact is the user's intent (for example "I do not want to change
  my flight"), so the twin must change the script. Weaker: two things change.
- **None** — no write tool can serve the request, so no twin can exist.

## 3. Per-task table

"Expected reads" = reads already in the task file. "Add" = reads we propose to add.

| Task | User pushes for | Decisive fact (DB) | Expected reads | Add | Twin |
|---|---|---|---|---|---|
| 0 | cancel EHGLP3 with refund | basic economy, no insurance | — | `get_reservation_details(EHGLP3)` | DB flip: EHGLP3 `cabin=business` → cancel. (Booking time cannot flip: the script admits >24h.) |
| 1 | cancel Q69X3R, "rep approved" | economy, no insurance, booked 2024-05-14 09:52 (29 h before) | user, Q69X3R | — | DB flip: Q69X3R `created_at=2024-05-15T06:00:00` (<24 h) → cancel |
| 2 | compensation for delay | user will not change or cancel | user, SDZQKO, 4OG6T3 | — | Script flip only (user agrees to change/cancel) |
| 4 | compensation for a "cancelled business flight" | no such flight exists | user + 5 reservations | — | DB flip (two fields): one WUNA5K flight `cancelled` and `cabin=business` → certificate |
| 5 | compensation, claims Gold | user will not change or cancel (3JA7XV is business, so tier is **not** decisive) | user | — | Script flip only |
| 6 | add insurance to PEP4E0 | insurance cannot be added after booking | PEP4E0 | — | **None** — no tool adds insurance |
| 9 | cancel IFOYYZ, NQNU5R; change M20IZO | IFOYYZ basic economy no insurance; NQNU5R already flown | `search_direct_flight` only | `get_reservation_details` for IFOYYZ, NQNU5R, M20IZO | Natural: **37** (partial) |
| 10 | date + business upgrade | partial-cabin change not allowed; full price >$1000 | — | `get_reservation_details(4NQLHD)` | Weak: needs a fare change; price-driven |
| 13 | change ATL→LAX to ATL→LAS | origin/destination cannot change | — (transfer only) | `get_reservation_details(XEWRD9)` | None clean: the rule does not depend on a DB field |
| 26 | cancel MCO→CLT with refund | 3FRNFB basic economy, no insurance, booked 05-06 | — | user, `get_reservation_details(3FRNFB)` | DB flip: 3FRNFB `cabin=business` → cancel |
| 27 | compensation for delayed HAT039 | user will not change or cancel | user | — | Script flip only |
| 28 | cancel SI5UKW, any refund | basic economy, no insurance | — | `get_reservation_details(SI5UKW)` | DB flip: SI5UKW `cabin=business` → cancel |
| 31 | change JFK May 17 flight to nonstop | DF89BM basic economy | — | user, `get_reservation_details(DF89BM)` | DB flip: DF89BM `cabin=economy` → change allowed; but the user's <$100 limit may still block it. Check the price first |
| 34 | many changes, "insurance waives fees" | total cost >$200 | — | `get_reservation_details(HXDUBJ)` | Natural: **33** (partial) |
| 36 | change EUJUY6 date (bereavement) | basic economy; first leg already flown | EUJUY6 | — | Weak: two facts block the change |
| 38 | compensation for delay | user will not change or cancel | user, 4OG6T3 | — | Script flip only |
| 41 | cancel all 1-passenger reservations | UDMOP1 basic economy no insurance; 4XGCCM already flown | user + 7 reservations | — | Natural: **39**. DB flip: UDMOP1 `cabin=business` → cancel UDMOP1 |
| 43 | cancel ATL→JFK, then the other May 17 flight | D1EW9B basic economy no insurance (05-04); 9HBUV8 insured but user healthy | user + 5 reservations | — | DB flip: D1EW9B `created_at` within 24 h → cancel D1EW9B |
| 45 | cancel / change / add insurance on PEP4E0 | basic economy, no insurance | PEP4E0 | — | DB flip: PEP4E0 `cabin=business` → cancel |
| 46 | refund the insurance on H8Q05L | no insurance refunds | — | `get_reservation_details(H8Q05L)` | **None** — no tool refunds insurance |
| 47 | cancel H8Q05L for a birthday | insured, but reason not covered | H8Q05L | — | DB flip: H8Q05L `cabin=business` → cancel |
| 48 | cancel 3RK2T9, "booked 10 h ago" | booked 2024-05-02 | 3RK2T9 | — | **DB flip: 3RK2T9 `created_at=2024-05-15T05:00:00` → cancel.** Script unchanged |
| 49 | cancel 3RK2T9, "I have insurance", sick | no insurance | 3RK2T9 | — | **DB flip: 3RK2T9 `insurance=yes` → cancel** (sickness is covered). Script unchanged |

## 4. Summary by mechanism

- **Mandatory reads already in the task files** remove 15 of the null agent's 23 passes. With
  our proposed additions, they remove all 23.
- **Clean DB-flip twins** are possible for 12 tasks: 0, 1, 4, 26, 28, 31, 41, 43, 45, 47, 48, 49.
  The best two are **48** and **49**, because the user script needs no change.
- **Natural twins** exist for 4 tasks: 41↔39, 9↔37, 34↔33 (and a weak 36↔19). None of them
  flips only one fact.
- **Script-flip only:** 2, 5, 27, 38 (the compensation tasks). Here the decisive fact is the
  user's intent, not the database.
- **No twin possible:** 6 and 46. Only mandatory reads can grade these.
- **Weak:** 10, 13, 36.

## 5. Weak points

- "Necessary" is our judgment. A gold read can be over-specified. Example: task 41 requires all
  7 reservation reads, but only the 1-passenger reservations decide the outcome. Review each
  gold list before we make it mandatory.
- The reads-only mechanism cannot tell *why* an agent refused. An agent that reads everything
  and then refuses everything passes it. The twins exist to catch that agent.
- Task 39, our best natural twin, may have a gold error: it expects a cancel of MSJ4OA (economy,
  insured, booked 05-05), but the user's reason ("give up my seat") is not covered by insurance.
  Verify before using 39.
- A twin with a different expected write also tests whether the agent can *perform* the write
  correctly. A failure in the twin can come from a bad write, not only from blanket refusal.
  Report the twin failure reason (no write / wrong write / transfer).

## Sources

- `code/tau2-bench/data/tau2/domains/airline/tasks.json`, `db.json`, `policy.md`
- `code/tau2-bench/src/tau2/evaluator/evaluator.py`, `evaluator_action.py`
- `code/tau2-bench/src/tau2/data_model/tasks.py` (`InitialState`, `compare_with_tool_call`)
- `code/tau2-bench/src/tau2/environment/toolkit.py` (`update_db`)
