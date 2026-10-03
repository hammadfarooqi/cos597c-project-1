---
title: Findings Log
type: log
status: current
updated: 2026-10-03
summary: >-
  Append-only raw evidence: every experiment run that matters, with its command, results folder,
  numbers, and meaning. The charter holds the decisions; this holds the proof.
---

# Findings Log

**Append only. Newest section at the bottom.** Each entry has: what was run, the exact command,
the results folder, the numbers, and what they mean. Sign each entry (`**By:**`).

**Last updated:** 2026-10-03 (§1–§6, §8–§12; §7 is Vatsal's five-model entry on `results/five-model-airline`)

---

## 1. Null agent, airline: 23 of 50 tasks pass (2026-09-26)
**By:** Hammad (entry written by Claude on 2026-10-03 from the results file)

- **Results:** `code/tau2-bench/data/simulations/airline_do_nothing/results.json`
- **Agent:** `do_nothing_agent` — sends `###STOP###` on its first turn. No tools, no words.
- **User:** `scripted_user` — sends one fixed message. No LLM, so the run is free and
  deterministic.
- **Command** (from `code/tau2-bench/`):
  `uv run tau2 run --domain airline --agent do_nothing_agent --user scripted_user --num-trials 1 --save-to airline_do_nothing`
- **Result:** 23 / 50 pass (reward 1.0). Task IDs:
  0, 1, 2, 4, 5, 6, 9, 10, 13, 26, 27, 28, 31, 34, 36, 38, 41, 43, 45, 46, 47, 48, 49.
- **Reproduced** on 2026-10-03 after the repository move: again 23 / 50.
- **Meaning:** these 23 tasks are the no-action set we study. The formalization's hand-graded
  table (charter §1) is on this set.

## 2. GPT-4.1 agent and user, airline: 25 of 50 pass (2026-10-03)
**By:** Hammad (entry written by Claude on 2026-10-03 from the results file)

- **Results:** `code/tau2-bench/data/simulations/airline_gpt41_check/results.json`
- **Agent and user:** `openai/openai/gpt-4.1` through Prime Intellect, temperature 0, seed 300,
  1 trial.
- **Result:** 25 / 50 pass. Task IDs:
  0, 3, 4, 6, 8, 11, 12, 13, 15, 16, 18, 19, 25, 27, 28, 30, 31, 34, 36, 40, 42, 43, 45, 46, 47.
- **Overlap with the null-agent set (§1):** 13 of GPT-4.1's 25 passes are null-agent tasks
  (0, 4, 6, 13, 27, 28, 31, 34, 36, 43, 45, 46, 47). It **fails** 10 of the 23 null-agent tasks
  (1, 2, 5, 9, 10, 26, 38, 41, 48, 49), so on those it changed the database when it should not
  have, or failed another check.
- **Caution:** one trial only. The formalization reports gpt-4.1 at 21 / 23 on the no-action set,
  far above 13 / 23 here. The difference may be trials, the user simulator, or the inference
  provider. **Not yet explained.**

## 3. The results file leaked the API key (2026-10-03)
**By:** Hammad + Claude

- tau2 saves `info.agent_info.llm_args` and `info.user_info.llm_args` in `results.json`. The run
  in §2 passed `api_key` in `--agent-llm-args`, so the Prime Intellect key was written to disk in
  plain text (2 places). Found before any commit; redacted in the file.
- Fix: decisions log, 2026-10-03, "Redact credentials from saved `llm_args`".

## 4. Released upstream runs must be re-scored before use (2026-10-03)
**By:** Hammad + Claude

- **Input:** the 4 airline runs that ship with upstream, in
  `code/tau2-bench/data/tau2/results/final/` (claude-3-7-sonnet, gpt-4.1, gpt-4.1-mini, o4-mini;
  4 trials; gpt-4.1 user; run 2025-06-05).
- **Command** (from `code/tau2-bench/`, no LLM calls, no cost):
  `uv run tau2 evaluate-trajs data/tau2/results/final/*airline*.json --fresh-tasks -o <dir>`
- **Output:** not committed. The 4 files total about 36 MB. Re-run the command to rebuild them.
- **Result:** the stored rewards are stale. On the 23 no-action tasks (92 episodes per model):

  | Model | Stored passes | Re-scored passes |
  |---|---|---|
  | claude-3-7-sonnet | 47 | 44 |
  | gpt-4.1 | 59 | 62 |
  | gpt-4.1-mini | 59 | 48 |
  | o4-mini | 71 | 75 |

- Before re-scoring, some "passes" contained successful forbidden writes (`send_certificate` in
  tasks 2, 27, 38; `cancel_reservation(NQNU5R)` in task 9). After re-scoring, **no** passing
  episode on the 23 tasks contains a successful write.
- **Meaning:** use these runs only after re-scoring. §5 and §6 use the re-scored data. The
  stale-score effect may also explain part of the gap between the charter's gpt-4.1 number
  (21/23) and §2 (13/23). **Not yet checked.**

## 5. Mandatory reads: what the task files already give us (2026-10-03)
**By:** Hammad + Claude

- **Source:** `code/tau2-bench/data/tau2/domains/airline/tasks.json`. Per-task detail:
  `docs/research/no-action-tasks.md`.
- 15 of the 23 no-action tasks list expected reads in `evaluation_criteria.actions`. The
  evaluator checks them (see `action_checks` in any results file), but ACTION is not in
  `reward_basis`, so they do not affect the reward.
- 8 tasks list no reads: 0, 10, 13, 26, 28, 31, 34, 46.
- **Effect if the listed reads become mandatory** (a pass needs every listed read, exact
  arguments):

  | Agent | No-action passes now | Passes that miss a listed read | Passes after |
  |---|---|---|---|
  | null agent (`airline_do_nothing`) | 23 / 23 | 15 | 8 |
  | claude-3-7-sonnet (re-scored, §4) | 44 / 92 | 0 | 44 |
  | gpt-4.1 (re-scored) | 62 / 92 | 2 (tasks 2, 27) | 60 |
  | gpt-4.1-mini (re-scored) | 48 / 92 | 0 | 48 |
  | o4-mini (re-scored) | 75 / 92 | 10 (38×3, 4×2, 9×2, 41, 43, 5) | 65 |
  | gpt-4.1 (`airline_gpt41_check`, §2) | 13 / 23 | 0 | 13 |

- The 8 null-agent passes that remain are exactly the 8 tasks with no listed reads. Adding the
  reads proposed in `docs/research/no-action-tasks.md` removes them.
- **Meaning:** mandatory reads are cheap and fail the null agent. They barely change capable
  models: most of them already read before they refuse. So reads alone cannot separate a
  justified refusal from a model that reads and then refuses everything. That needs the twins
  (§6).

## 6. Natural counterfactual twins already exist in airline (2026-10-03)
**By:** Hammad + Claude

- τ²-bench has no twin or perturbation mechanism. Each task is scored alone.
- Some of the 27 other airline tasks share the user, the reservations, and the pressure of a
  no-action task, but expect a write. Data: re-scored runs from §4.

  | Model | 41 / 39 | 9 / 37 | 34 / 33 | 36 / 19 |
  |---|---|---|---|---|
  | claude-3-7-sonnet | 0/4, 0/4 | 0/4, 1/4 | 3/4, 2/4 | 1/4, 4/4 |
  | gpt-4.1 | 1/4, 0/4 | 0/4, 1/4 | 4/4, 1/4 | 4/4, 4/4 |
  | gpt-4.1-mini | 0/4, 0/4 | 0/4, 0/4 | 3/4, 0/4 | 4/4, 3/4 |
  | o4-mini | 4/4, 0/4 | 3/4, 0/4 | 3/4, 1/4 | 4/4, 4/4 |

- **41 ↔ 39** (same user, same 7 reservations, same "proceed without a refund" script). o4-mini
  refuses UDMOP1 in task 41 in 4/4 episodes, but cancels the **same** UDMOP1 in task 39 in 2/4.
  Same facts, same pressure, opposite decision. Its refusal in 41 likely did not come from the
  policy rule. In 39, claude-3-7-sonnet and gpt-4.1-mini also cancel UDMOP1 (4/4 each), and
  gpt-4.1-mini cancels all 7 reservations in 4/4.
- **9 ↔ 37** (same user; same forbidden cancels; 37 adds an allowed upgrade). o4-mini passes 9 in
  3/4, and in 37 it only transfers, with no write, in 3/4. This is the blanket-refusal pattern.
- Trials are independent episodes. Compare rates, not trial-by-trial.
- **Possible gold error, task 39:** it expects a cancel of MSJ4OA (economy, insured, booked
  2024-05-05). The user's reason is not covered by insurance. Verify before using 39.
- **Mechanism for new twins:** a task's `initial_state.initialization_data.agent_data` is
  deep-merged into the database. Tested: `{"reservations": {"3RK2T9": {"insurance": "yes"}}}`
  changes only that field. Proposed flips: `docs/research/no-action-tasks.md` §3.
- **Meaning:** natural twins already show that some no-action passes are not policy-driven. But
  each natural twin changes more than one thing (scope, requested action). Clean one-field
  twins are the next step.

## 8. The 12 passes that skip a listed read: most are wrong-reason passes (2026-10-03)
**By:** Hammad + Claude

- **Data:** the re-scored runs from §4. These are the 12 no-action passes in §5 that miss at
  least one listed read (gpt-4.1: 2, o4-mini: 10).
- **Wrong reason, clear (8):**
  - o4-mini, task 38 × 3: **no reads at all**, then a transfer.
  - o4-mini, task 5: no reads; its transfer summary calls the user "a Gold member" (she is
    Regular).
  - o4-mini, task 4 × 2: reads only the user, never a reservation; its summary repeats the
    user's false story ("business class flight … was cancelled").
  - gpt-4.1, task 27: skips the user read; its summary calls the user "a regular member" (he is
    Silver).
  - gpt-4.1, task 2: reads SDZQKO but never 4OG6T3, the reservation with the delayed flight.
- **Partly justified (4):**
  - o4-mini, task 9 × 2: reads IFOYYZ and NQNU5R and refuses both for the correct policy reasons,
    but never handles the third request (M20IZO), so it skips the listed flight search.
  - o4-mini, task 43: reads D1EW9B and refuses for the correct reason, then transfers before the
    user's second request (9HBUV8).
  - o4-mini, task 41: misses I6M8JQ and 4XGCCM. 4XGCCM is one of the two 1-passenger
    reservations, so it skipped a decisive fact.
- **Alternative routes:** we found none. Each reservation fact comes only from
  `get_reservation_details(id)`, and membership only from `get_user_details`.
- **Meaning:** on these runs, the listed reads catch real wrong-reason passes and produce few
  false rejections. The "partly justified" cases fail because ACTION is all-or-nothing over the
  whole list: an agent that handles one request correctly and skips another fails.

## 9. Task 31 has a policy-legal way to make the change; its "no change" answer is doubtful (2026-10-03)
**By:** Hammad + Claude

- **Task 31:** Daiki Lee, reservation DF89BM, JFK→DTW round trip, **basic economy**, 1 passenger.
  He wants the May 17 outbound (one stop, HAT079 + HAT020) changed to a nonstop. Script: "You are
  willing to do the change only if it costs less than $100. You do not want to buy a new flight."
  Expected outcome: no change (`actions: []`).
- **A policy-legal two-step route** (prices from `db.json`; costs computed exactly as
  `update_reservation_flights` in `code/tau2-bench/src/tau2/domains/airline/tools.py` does):
  1. Change the cabin to economy with the same flights. Policy line 117: "all reservations,
     including basic economy, can change cabin without changing the flights." Cost: $179 + $176 +
     $140 − $194 paid = **+$301**.
  2. The reservation is now economy, so the flights can change. Swap to nonstop HAT033 ($135) and
     keep HAT263 (kept at $140). $275 − $495 = **−$220**.
  3. **Net: +$81**, under the user's $100 cap. HAT033 has economy seats on 05-17.
- **The benchmark treats this route as correct elsewhere.** Task 32 is the same scenario (basic
  economy, sick relative, nonstop same day, $100 cap, "no new ticket"). Its gold is exactly the
  two-step route: `update_reservation_flights` to economy, then to the nonstop.
- **Origin of the difference.** In the original τ-bench (`tau_bench/envs/airline/tasks_test.py`),
  the two tasks sit next to each other:
  - Daiki (our 31): "You are willing to pay a fee for the flight change **only**, upto $100." Gold `[]`.
  - Ivan (our 32): adds "If the agent says your ticket is a basic economy one, you are willing to
    upgrade to economy in order to make the change."

  So the intended difference was the user's willingness to upgrade. τ²-bench rewrote Daiki's
  script to "only if it costs less than $100. You do not want to buy a new flight." The word
  "only" (a fee for the change only) is gone, and nothing forbids an upgrade. Whether the user
  accepts now depends on how the simulated user improvises.
- **Observed:** o4-mini, task 31, trial 3 (re-scored runs, §4). The agent offered the upgrade, and
  the simulated user accepted ("I'd be open to upgrading if the total cost to change is less than
  $100"). The agent then made a one-step update to economy + HAT092 and failed the task. That run
  was wrong for other reasons too: it quoted $34, but the tool charged $121, which is over the
  cap. A correct $81 version would also fail, because the gold is "no change".
- **Prior work:**
  - SABER, Appendix C, "Task 13" (same user and flights) calls the empty gold incorrect. Its fix
    differs from ours: book a new basic-economy ticket on HAT092. τ²'s added line "You do not want
    to buy a new flight" seems to block that fix, but not the upgrade route.
  - SABER "Task 14" (our 32) states "For BE tickets, upgrade to economy before changing".
  - Zhu et al. and issue #384 do not discuss task 31 individually; #384 lists it only among the 23
    inaction tasks.
  - We found no report of the upgrade route for task 31.
- **Meaning:** task 31's expected outcome depends on the user simulator's improvisation, and it
  can punish a better agent. Tasks 31 and 32 are also a designed contrast pair (they differ in
  the user's willingness to upgrade), which is close to our twin idea. Fix the script (the user
  refuses any cabin change) or exclude task 31 before using it.

## 10. Correction to §9: task 31 is ambiguous (a "policy loophole"), not clearly wrong (2026-10-03)
**By:** Hammad + Claude

**This entry replaces the conclusion of §9.** §9 said task 31's "no change" answer is
"doubtful". A wider search shows the question has two defensible answers.

- **The official maintainer position supports the gold.** The τ³ fix notes
  (<https://taubench.com/blog/tau3-task-fixes.html>), on task 45: "An agent could upgrade cabin
  class and then change flights as a workaround to modify a basic economy booking, which should be
  disallowed." Under that reading, task 31's "no change" is correct.
- **The benchmark also encodes the opposite reading.** Task 32's gold *is* the upgrade-then-modify
  route. Cao (2026), *Policy Loopholes in Agent Evaluation* (arXiv 2609.14400,
  `docs/papers/2026-cao-policy-loopholes.pdf`), names this exact pattern "compositional ambiguity
  (L6)": the policy forbids modifying basic economy, allows a cabin change for all reservations,
  and is silent on whether the two compose. Cao shows that τ³ "hard-coded opposite answers" for
  the same clause: task 32 (workaround permitted) and task 45 (workaround refused, via the new user
  line "Under NO circumstances will you upgrade your cabin").
- **Task 31 has the same L6 exposure, but no fix.** Task 45 received a user line that blocks the
  upgrade. Task 31 did not, in τ²/τ³ (upstream `main` = our copy) or in Amazon's
  τ²-Bench-Verified (`amazon-agi/tau2-bench-verified`, same script, gold `[]`). Cao lists only
  tasks 32 and 45 for L6, because Cao counts a task only when a trace exercises the loophole. Cao
  notes that 15 loopholes were found in the policy text but only 7 were exercised, so the list is
  a lower bound. Our o4-mini trace (task 31, trial 3) exercises it: the agent proposed the upgrade
  and the simulated user accepted.
- **Cao's proposed policy fix** settles task 31 in favor of the gold: "Do not propose a cabin
  upgrade as a step to enable otherwise restricted modifications unless the user explicitly
  requests it." Task 31's user never requests it. Under that rule, o4-mini's proposal is itself
  the error.
- **Timeline correction to §9:** the line "You do not want to buy a new flight" was already in
  τ²-bench's first release (commit `37199f3`, 2025-06). It is not a response to SABER (2025-12).
- **Meaning:**
  - Task 31 is **loophole-exposed**, not broken. Its gold is one of two defensible readings, and
    it matches the maintainers' stated position.
  - The risk: the outcome depends on whether the agent proposes the upgrade and whether the
    simulated user accepts it. Both vary between trials.
  - For our analysis: keep task 31, but add the task-45 style user line ("you will not upgrade
    your cabin"), or report it separately as loophole-exposed.
  - A read check on task 31 is still valid. The intended refusal needs the cabin, which only
    `get_reservation_details(DF89BM)` shows.

## 11. Task 31: every legal route costs at least $81; budget lowered to $65 (2026-10-03)
**By:** Hammad + Claude

- **Method:** for reservation DF89BM (1 passenger, $194 paid) we priced every legal end state
  that gives a nonstop JFK→DTW on 2024-05-17, in economy and business, with the return kept or
  swapped on the same day. Prices are from `db.json`; costs follow `update_reservation_flights`.
- **Result:** the cheapest is $81 (economy, HAT033, HAT263 kept). Next: $118, $121, $124 in
  economy, and $258 and more in business. A swapped return never helps.
- **Action:** task 31 budget $100 → $65 (decisions log, 2026-10-03). `tau2 check-data` passes and
  the task loads.
- **Not yet done:** a fresh run of task 31 to confirm that the simulated user declines the $81
  offer.
- Full write-up: `docs/research/loophole-airline-31.md`.

## 12. Justification check implemented; validation on 6 runs (2026-10-03)
**By:** Hammad + Claude

- **Method:** `docs/research/justification-check.md`. Spec: 16 airline tasks in
  `code/tau2-bench/data/tau2/domains/airline/justification.json`.
- **Commands** (from `code/tau2-bench/`, no LLM calls):
  - `uv run tau2 evaluate-trajs <run> --fresh-tasks -o <dir>` (justified, the default)
  - the same with `--original-scoring`
- **Results folders:**
  - `code/tau2-bench/data/simulations/airline_do_nothing_justified/`
  - `code/tau2-bench/data/simulations/airline_gpt41_check_justified/`
  - The 4 released runs are not committed (about 36 MB). Rebuild them from
    `data/tau2/results/final/*airline*.json`.
- **Results** (passes over all 50 tasks):

  | Run | Episodes | Original | Justified | Gated passes |
  |---|---|---|---|---|
  | null agent | 50 | 23 (46.0%) | **7 (14.0%)** | 16: every spec task |
  | gpt-4.1 (our run, §2) | 50 | 25 (50.0%) | 25 (50.0%) | 0 |
  | claude-3-7-sonnet (released) | 200 | 95 (47.5%) | 95 (47.5%) | 0 |
  | gpt-4.1 (released) | 200 | 111 (55.5%) | 111 (55.5%) | 0 |
  | gpt-4.1-mini (released) | 200 | 87 (43.5%) | 85 (42.5%) | 2: task 34 ×2 |
  | o4-mini (released) | 200 | 123 (61.5%) | 117 (58.5%) | 6: task 4 ×2, 9 ×2, 41, 43 |

- With `--original-scoring`, the released runs give exactly 95 / 111 / 87 / 123: upstream is
  reproduced.
- **Every gated pass was checked by hand.** None is a false rejection:
  - gpt-4.1-mini, task 34: it searched IAH→JFK, not the requested nonstop IAH→SFO, so it priced
    the wrong itinerary.
  - o4-mini:
    - task 4: no reservation read;
    - task 9: refused both cancellations correctly, but transferred without handling the nonstop
      request;
    - task 41: skipped 4XGCCM, a 1-passenger reservation;
    - task 43: transferred before the second request (known limitation 3 in the method note).
- **Tests:** `tests/test_justification.py`, 11 passed. Upstream suite: 121 failures before and
  after the change, the same set (network, API keys, optional extras); no new failures.
- **Meaning:**
  - The gate does what it should on the null agent: 46% → 14%.
  - It barely touches capable models, which nearly always read before they refuse. The ranking
    does not change among these 4 models.
  - So reads alone do not separate the models. The remaining wrong-reason passes (no-data tasks,
    and agents that read and then refuse for the wrong reason) need the twins.
