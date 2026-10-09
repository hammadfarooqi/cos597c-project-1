---
title: Findings Log
type: log
status: current
updated: 2026-10-09
summary: >-
  Append-only raw evidence: every experiment run that matters, with its command, results folder,
  numbers, and meaning. The charter holds the decisions; this holds the proof.
---

# Findings Log

**Append only. Newest section at the bottom.** Each entry has: what was run, the exact command,
the results folder, the numbers, and what they mean. Sign each entry (`**By:**`).

**Last updated:** 2026-10-09 (§1–§15; §10–§14 renumbered from §8–§12 at the 2026-10-08 merge)

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

## 7. Five models, all 50 airline tasks, through Prime Intellect (2026-10-03)
**By:** Vatsal + Claude

- **Results:** `code/tau2-bench/data/simulations/airline_<model>/results.json` for
  `claude-sonnet-4.5`, `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`, `llama-3.3-70b`.
- **Config:** agent = the model; user simulator = `openai/gpt-4.1`; both through Prime
  Intellect; temperature 0; seed 300; 1 trial; all 50 tasks. Same models as the formalization
  pilot (charter §1). These are **new** runs, not the pilot trajectories.
- **Command** (from `code/tau2-bench/`; the key goes in the process environment, not in
  `llm_args`, so it never reaches `results.json`):

  ```bash
  export OPENAI_API_KEY=<Prime key> OPENAI_API_BASE=https://api.pinference.ai/api/v1
  uv run tau2 run --domain airline \
    --agent-llm openai/<prime model id> --agent-llm-args '{"temperature": 0.0}' \
    --user-llm openai/openai/gpt-4.1 --user-llm-args '{"temperature": 0.0}' \
    --num-trials 1 --seed 300 --max-concurrency 5 --save-to airline_<model>
  ```

  Prime model IDs: `anthropic/claude-sonnet-4.5`, `openai/gpt-4.1`, `openai/gpt-4.1-mini`,
  `openai/gpt-4.1-nano`, `meta-llama/llama-3.3-70b-instruct`. The 23 no-action tasks ran first
  (`--task-ids`); the other 27 were added to the same file with `--auto-resume`.
- **Cost:** $30.53 total (sonnet $16.42, gpt-4.1 $7.16, llama $3.65, mini $2.29, nano $1.01),
  from saved token counts × Prime list prices.
- **Result.** "No-action" = the 23 tasks the null agent passes (§1). "Reads kept" = no-action
  passes that also ran every read listed in the task file (the mandatory-read rule, §5):

  | Model | All 50 | No-action (23) | Other (27) | Reads kept | Transfers on no-action |
  |---|---|---|---|---|---|
  | claude-sonnet-4.5 | 37 | 20 | 17 | 20 | 12 |
  | gpt-4.1 | 30 | 16 | 14 | 16 | 9 |
  | gpt-4.1-mini | 20 | 13 | 7 | 13 | 10 |
  | llama-3.3-70b | 19 | 19 | **0** | **8** | 22 |
  | gpt-4.1-nano | 3 | 1 | 2 | 0 | 2 |

- **llama-3.3-70b passes no task that needs an action**, but ties gpt-4.1-mini on the full
  score (19 vs 20). All of its score comes from the no-action set. It transfers to a human in
  22 of 23 no-action tasks, and 11 of its 19 passes miss a listed read. The mandatory-read rule
  takes it from 19 to 8 and leaves the other models unchanged. This is the project's claim,
  now with committed data.
- **Single-trial scores are not stable.** On the 23 no-action tasks, against an earlier run of
  the same config (Vatsal's survey, 2026-09-26, not in this repository):

  | Model | Earlier | Now | Same verdict | Tasks that changed (earlier → now) |
  |---|---|---|---|---|
  | claude-sonnet-4.5 | 21 | 20 | 20/23 | 0 (0→1), 1 (1→0), 47 (1→0) |
  | gpt-4.1 | 21 | 16 | 18/23 | 1, 38, 43, 48, 49 (all 1→0) |
  | gpt-4.1-mini | 20 | 13 | 16/23 | 2, 10, 26, 36, 38, 43, 45 (all 1→0) |
  | llama-3.3-70b | 21 | 19 | 21/23 | 6, 47 (1→0) |
  | gpt-4.1-nano | 4 | 1 | 20/23 | 27, 31, 34 (1→0) |

  gpt-4.1 now has three samples on this set: 21 (survey), 13 (§2), 16 (here). The configs
  match, except that §2 passed the key in `llm_args`. This likely explains the gap noted in
  §2 as run-to-run noise, not a setup error.
- **Meaning:** the main effect (llama) is large enough to see in one trial. The smaller
  differences are not: one model moved by 7 of 23 between two identical runs. Any claim about
  ranking changes needs several trials per task (the released runs use 4).
- **Weak points:** 1 trial only. The hand grades from the pilot are not in this repository,
  so M1.4 still cannot run. The user simulator ends some episodes early (survey note); some
  passes and failures may depend on it.

## 8. DB-flip twins for 11 no-action tasks: paired scores (2026-10-03)
**By:** Vatsal + Claude

- **Design:** `docs/research/counterfactual-twins.md`. **Code:** `code/twins/`.
- **Twins:** `code/tau2-bench/data/tau2/domains/airline/tasks_twins.json`, split `primary`:
  one twin each for tasks 0, 1, 9, 26, 28, 41, 43, 45, 47, 48, 49. All pass the static checks
  (null: original 1, twin 0; comply: original 0, twin 1; only patched records change).
- **Runs:** `code/tau2-bench/data/simulations/airline_twins_<model>/results.json`, same config
  as §7 (Prime, gpt-4.1 user, temperature 0, seed 300, 1 trial), plus
  `--task-set-name airline_twins --task-split-name primary`. Cost $4.32. The no-action side is
  the §7 runs on the same 11 tasks.
- **Null agent** (`do_nothing_agent`, `scripted_user`, live run): 0 / 11 twins (originals 11/11).
- **Result** (`uv run python ../twins/score_pairs.py <models>` from `code/tau2-bench/`):

  | Model | No-op passes | Twin passes | **Paired** | No-op only | Twin only | Neither |
  |---|---|---|---|---|---|---|
  | claude-sonnet-4.5 | 8 | 11 | **8** | 0 | 3 | 0 |
  | gpt-4.1 | 6 | 9 | **5** | 1 | 4 | 1 |
  | gpt-4.1-mini | 6 | 7 | **5** | 1 | 2 | 3 |
  | llama-3.3-70b | 8 | 2 | **0** | 8 | 2 | 1 |
  | gpt-4.1-nano | 0 | 7 | **0** | 0 | 7 | 4 |

- **llama-3.3-70b:** all 8 of its no-action passes lose credit. In 7 of its 9 failed twins it
  transfers to a human again. It ties sonnet on no-action passes and has 0 paired passes.
- **gpt-4.1-nano** fails the other way: it writes no matter what (7 twin passes, 0 no-op).
- **Task 9 twin:** gpt-4.1, mini, nano, and llama cancel IFOYYZ (allowed) and then also
  NQNU5R (business, but already flown, so not allowed). Sonnet does not. A real agent error,
  not a twin defect.
- **Effect on the full 50 tasks** (the 11 verdicts replaced by the paired verdict):
  sonnet 37 → 37, gpt-4.1 30 → 29, mini 20 → 19, llama 19 → **11**, nano 3 → 3.
  With a lenient rule (the twin counts if the agent made the right write despite other
  errors): gpt-4.1 paired 6, llama 1; no other change.
- **Noise:** an earlier run of the first 10 twins (same config, not committed) gave the same
  twin verdict on 10/10 tasks for sonnet, 9/10 llama, 8/10 nano, 7/10 gpt-4.1 and mini. The
  large effects held. Differences of 1–2 tasks between gpt-4.1 and mini did not.
- **Task 4 twin, dropped:** the "claim true" twin (WUNA5K business, HAT271 on 05-10
  cancelled) passed all static checks, but all 5 models failed it live. The models offered
  the $100 certificate or tried to; the user script wants more, refuses, and asks for a
  transfer. The results files above still hold one `4_twin_claim_true` episode per model;
  `score_pairs.py` ignores it.
- **Meaning:** twins separate a justified refusal from a blanket refusal with outcome-only
  scoring and no LLM judge. The no-action score alone ranks llama level with sonnet on these
  tasks; the paired score ranks it last. 12 of the 23 tasks still have no twin.

## 9. Policy-flip twins for tasks 2, 5, 27, 38; combined paired scores (2026-10-03)
**By:** Vatsal + Claude

- **Design:** `docs/research/counterfactual-twins.md` §6. **Flip:** `code/twins/policy_flips.yaml`,
  id `delay_no_change`. One sentence of `policy.md` changes: a delay certificate no longer
  needs the user to change or cancel. The flipped policy differs from `policy.md` in that one
  line (`diff` checked). The DB and the user scripts do not change.
- **Twins:** `2_twin_pf_delay_no_change`, `5_…`, `27_…`, `38_…` in `tasks_twins.json`, split
  `pf_delay_no_change`. Correct writes: `send_certificate` for $50 (2, 38: noah_muller,
  1 passenger), $200 (5: mei_brown, 4 passengers, eligible by business cabin), $150 (27:
  ethan_martin, silver, 3 passengers). All pass the static checks.
- **Runs:** `code/tau2-bench/data/simulations/airline_twins_pf_<model>/results.json`. Same config
  as §7, plus `--domain airline_pf_delay_no_change --task-set-name airline_twins
  --task-split-name pf_delay_no_change`. The saved `environment_info.policy` holds the flipped
  sentence. Cost $1.96.
- **Validity:** each twin is passed by at least one model (27: sonnet; 38: sonnet, gpt-4.1,
  mini; 2: mini, nano; 5: mini), so each user goal is reachable (compare task 4, §8). The
  failures read so far are agent errors: gpt-4.1 sends $50 instead of $200 on 5; sonnet does
  not read reservation 3JA7XV on 5 and transfers; nano sends two certificates; llama sends
  $500 + $100. Twin 2 is noisier: the scripts of 2 and 38 point the user to "the last
  reservation", but the delay is in 4OG6T3, not the newest booking SDZQKO.
- **Result, policy twins only (4):**

  | Model | No-op passes | Twin passes | **Paired** |
  |---|---|---|---|
  | claude-sonnet-4.5 | 4 | 2 | **2** |
  | gpt-4.1-mini | 1 | 3 | **1** |
  | gpt-4.1 | 2 | 1 | **0** |
  | llama-3.3-70b | 4 | 0 | **0** |
  | gpt-4.1-nano | 0 | 1 | **0** |

- **Result, all 15 twins** (11 DB + 4 policy; `uv run python ../twins/score_pairs.py <models>`):

  | Model | No-op passes | Twin passes | **Paired** | No-op only | Twin only | Full score → paired |
  |---|---|---|---|---|---|---|
  | claude-sonnet-4.5 | 12 | 13 | **10** | 2 | 3 | 37 → **35** |
  | gpt-4.1 | 8 | 10 | **5** | 3 | 5 | 30 → **27** |
  | gpt-4.1-mini | 7 | 10 | **6** | 1 | 4 | 20 → **19** |
  | llama-3.3-70b | 12 | 2 | **0** | 12 | 2 | 19 → **7** |
  | gpt-4.1-nano | 0 | 8 | **0** | 0 | 8 | 3 → **3** |

  "Full score → paired": the 50-task score with the 15 no-action verdicts replaced by the paired
  verdicts. The other 35 tasks are unchanged.
- **Meaning:** llama loses 12 points; the other models lose 0–3. Before, llama was 1 point
  behind mini; now it is 12 behind. Sonnet passes all 11 DB twins but only 2 of 4 policy twins:
  refusals that depend on a rule look less often reasoned than refusals that depend on a fact.
  gpt-4.1 and mini transfer on task 27 although the flipped policy allows the certificate.
  With 4 twins and 1 trial this is a signal, not a result.
- **Coverage:** 15 of the 23 no-action tasks have a twin. Not covered: 4, 31, 36 (DB, excluded),
  6, 13, 46 (policy, no usable flip), 10, 34 (price).

## 10. The 12 passes that skip a listed read: most are wrong-reason passes (2026-10-03)
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

## 11. Task 31 has a policy-legal way to make the change; its "no change" answer is doubtful (2026-10-03)
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

## 12. Correction to §11: task 31 is ambiguous (a "policy loophole"), not clearly wrong (2026-10-03)
**By:** Hammad + Claude

**This entry replaces the conclusion of §11.** §11 said task 31's "no change" answer is
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
- **Timeline correction to §11:** the line "You do not want to buy a new flight" was already in
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

## 13. Task 31: every legal route costs at least $81; budget lowered to $65 (2026-10-03)
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

## 14. Justification check implemented; validation on 6 runs (2026-10-03)
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

## 15. llama-4-maverick on Prime Intellect loses its tool calls; retry added (2026-10-09)
**By:** Vatsal + Claude

- **Context:** survey of newer models to replace the five in §7. `meta-llama/llama-4-maverick` is
  the direct successor of llama-3.3-70b, which got 19/50 by doing nothing (§7).
- **Symptom.** With tools offered and `tool_choice="auto"` (what tau2 sends), Prime returns the
  model's tool call in one of two broken forms:
  1. an empty message: `content: null`, no `tool_calls`, but ~14 completion tokens spent;
  2. the call as plain text, for example `get_user_details(user_id=omar_davis_3817)`.

  Plain text replies come back correctly. With `tool_choice="required"` the same request gives a
  correct structured call (same tool, same arguments). Probes: 4/4 empty on a one-tool test;
  on 21 replayed gpt-4.1 conversation prefixes (from `airline_gpt-4.1`), 3 empty, all where gpt-4.1 called a tool, and
  each forced retry gave the expected `get_user_details` call.
- **Cause (inferred, not confirmed):** Llama 4 writes tool calls in its own format, and Prime's
  gateway fails to convert some of them to structured calls. The provider-routing parameter does
  not change it. No other shortlisted model shows this (all ten in the survey returned
  structured calls).
- **Effect without a fix:** a 2-task tau2 check (tasks 18, 22) ran with the agent "calling"
  `get_user_details` as text on every turn until the user gave up. Both tasks failed. A full run
  would grade a gateway bug as the model doing nothing.
- **Fix:** `generate()` in `code/tau2-bench/src/tau2/utils/llm_utils.py` re-asks once with
  `tool_choice="required"` when tools were offered with `"auto"` and the reply is empty (with
  output tokens) or is a bare call to an offered tool as text. Cost and tokens of both calls are
  summed. The turn is marked `raw_data["empty_tool_retry"] = true`. Tests:
  `code/tau2-bench/tests/test_empty_tool_retry.py` (5 passed, offline).
- **Check after the fix** (same tasks, same config as §7: user `openai/gpt-4.1`, temperature 0,
  seed 300; scratch run, not committed): task 22 reward 1.0, task 18 reward 0.0 (a full
  conversation with reads and writes; why it failed was not checked). 5 agent turns needed the retry; all 5
  gave sensible calls. The old results have no empty agent turns (0 of 4,306 assistant messages
  across all committed airline runs) and one call leaked as text: `airline_llama-3.3-70b`, one
  `search_direct_flight(...)` turn. So §7 is affected by at most one turn of llama-3.3-70b.
- **Weak points:** the retried turn is decoded with a forced tool choice, so it is not exactly
  what the model would have sent; it is used only when the model's output was already a tool
  call. Report the retry rate next to any maverick score. The retry also applies to every model,
  but triggers only on these two broken forms.

