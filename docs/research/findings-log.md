---
title: Findings Log
type: log
status: current
updated: 2026-10-22
summary: >-
  Append-only raw evidence: every experiment run that matters, with its command, results folder,
  numbers, and meaning. The charter holds the decisions; this holds the proof.
---

# Findings Log

**Append only. Newest section at the bottom.** Each entry has: what was run, the exact command,
the results folder, the numbers, and what they mean. Sign each entry (`**By:**`).

**Last updated:** 2026-10-22 (§1–§24; §10–§14 renumbered from §8–§12 at the 2026-10-08 merge; §15–§16 of the scoreboard branch renumbered §18–§19, and its §20 renumbered §21, at the 2026-10-10 merges)

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

## 15. Three newer models: reads gate, DB twins, policy twins (2026-10-09)
**By:** Vatsal + Claude

- **Models** (Prime ids): `anthropic/claude-haiku-4.5`, `openai/gpt-6-luna`,
  `openai/gpt-5.4-nano`. Chosen in the newer-models survey (not in the repository).
- **Config:** the same as §7–§9. User simulator `openai/gpt-4.1`, temperature 0, seed 300,
  1 trial, `--max-concurrency 5`, key in the process environment. Code at commit `3dc213a`
  (main), so the read gate is applied when each run is saved.
- **Runs:** for each model, three folders in `code/tau2-bench/data/simulations/`:
  `airline_<model>` (50 tasks), `airline_twins_<model>` (split `primary`, 11 DB twins),
  `airline_twins_pf_<model>` (domain `airline_pf_delay_no_change`, 4 policy twins). This is the
  same 15-twin set as §8–§9. `tasks_twins.json` holds 26 twins, but the other 11 DB twins are
  alternates that are not in `primary`, and `score_pairs.py` uses only `primary` and `pf_*`.
- **Commands** (from `code/tau2-bench/`):

  ```bash
  export OPENAI_API_KEY="$PI_KEY" OPENAI_API_BASE="$PI_API_BASE"
  C=(--agent-llm openai/<prime id> --agent-llm-args '{"temperature": 0.0}'
     --user-llm openai/openai/gpt-4.1 --user-llm-args '{"temperature": 0.0}'
     --num-trials 1 --seed 300 --max-concurrency 5)
  uv run tau2 run --domain airline "${C[@]}" --save-to airline_<model>
  uv run tau2 run --domain airline --task-set-name airline_twins --task-split-name primary \
    "${C[@]}" --save-to airline_twins_<model>
  uv run tau2 run --domain airline_pf_delay_no_change --task-set-name airline_twins \
    --task-split-name pf_delay_no_change "${C[@]}" --save-to airline_twins_pf_<model>
  uv run python ../twins/score_pairs.py <models>
  ```

- **Old models re-scored for comparison.** The §7 runs were saved before the read gate
  existed. They were re-scored with `uv run tau2 evaluate-trajs <run> --fresh-tasks` (no LLM
  calls; outputs not committed). `--fresh-tasks` uses the current `tasks.json`, so task 31 is
  graded with the $65 budget, but the old user simulator was told $100.
- **Cost** (saved tokens × list price; haiku at $1/$5 per M tokens, luna $0.10/$0.50,
  nano $0.20/$1.25; user gpt-4.1 at $2/$8): haiku $5.60, luna $1.01, nano $3.40.
  Total about $10. Agent tokens in/out: haiku 4.08 M / 0.105 M, luna 3.20 M / 0.119 M,
  nano 6.46 M / 0.113 M.
- **Result, all 8 models.** "Reads gate" = evaluator reward (justified scoring). "+ twins" =
  the reads-gate score with the 15 no-action verdicts replaced by the paired verdicts.
  "No-action" = the 23 tasks the null agent passes (§1).

  | Model | Original (50) | Reads gate | **Reads gate + twins** | No-action (23) | Transfers on no-action | Paired / 15 |
  |---|---|---|---|---|---|---|
  | claude-sonnet-4.5 | 37 | 37 | **35** | 20 | 12 | 10 |
  | gpt-6-luna | 37 | 36 | **33** | 22 | 20 | 11 |
  | gpt-4.1 | 30 | 29 | **26** | 16 | 9 | 5 |
  | claude-haiku-4.5 | 24 | 23 | **21** | 18 | 15 | 8 |
  | gpt-4.1-mini | 20 | 20 | **19** | 13 | 10 | 6 |
  | gpt-5.4-nano | 15 | 15 | **12** | 9 | 8 | 1 |
  | llama-3.3-70b | 19 | 7 | **3** | 19 | 22 | 0 |
  | gpt-4.1-nano | 3 | 2 | **2** | 1 | 2 | 0 |

- **Twins, new models** (DB 11 / policy 4):

  | Model | No-op passes | Twin passes | Paired | Twin failure causes |
  |---|---|---|---|---|
  | gpt-6-luna | 10 / 4 | 11 / 1 | 10 / 1 | transfer 3 (all policy) |
  | claude-haiku-4.5 | 6 / 4 | 10 / 2 | 6 / 2 | transfer 2, no write 1 |
  | gpt-5.4-nano | 1 / 3 | 7 / 1 | 0 / 1 | right write + other error 3, wrong write 2, no write 1, transfer 1 |

- **Read gate:** it removes one pass from haiku and one from luna, both task 34. It removes
  none from nano.
- **gpt-6-luna** ties sonnet-4.5 on the original score (37) at about 1/16 of the cost. It
  transfers on 20 of 23 no-action tasks, like llama. But unlike llama, it passes all 11 DB
  twins, so its refusals depend on the data. It fails 3 of 4 policy twins by a transfer: the
  rule-based refusals look less reasoned, the same pattern as sonnet in §9.
- **gpt-5.4-nano** is not a blanket refuser, and it is not a blanket writer like
  gpt-4.1-nano. It passes 7 DB twins but only 1 of their no-action originals; most of its
  failures are wrong or extra writes.
- **Ranking:** twins and the read gate do not change the order of the three new models.
  The large rank change in the table is still llama only.
- **Weak points:**
  - 1 trial only; §7 shows a single model can move 7 of 23 between identical runs.
    Differences of 1–3 tasks mean nothing.
  - gpt-6-luna wraps 218 of its text messages in JSON (`{"message": "..."}`). The user
    simulator still reads them. This can change how some episodes end.
  - gpt-5.4-nano hit `max_steps` on task 15 (counted as a failure).
  - The haiku price is Anthropic's list price; Prime's price was not checked.

## 16. llama-4-maverick on Prime Intellect loses its tool calls; retry added (2026-10-09)
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


## 17. llama-4-maverick on airline and twins; all 9 models in one table (2026-10-09)
**By:** Vatsal + Claude

- **Model:** `meta-llama/llama-4-maverick` (Prime), the successor of llama-3.3-70b. Run with the
  retry from §16 (commit `99f9bcf`).
- **Config:** the same as §7–§9 and §15. User simulator `openai/gpt-4.1`, temperature 0,
  seed 300, 1 trial, `--max-concurrency 5`. Same three commands as §15, with
  `--agent-llm openai/meta-llama/llama-4-maverick`.
- **Runs:** `code/tau2-bench/data/simulations/airline_llama-4-maverick/`,
  `airline_twins_llama-4-maverick/` (11 DB twins, split `primary`),
  `airline_twins_pf_llama-4-maverick/` (4 policy twins).
- **Cost:** $3.97 for all 65 episodes, agent and user (agent at $0.35/$1.15 per M tokens;
  agent tokens in/out 7.05 M / 0.079 M).
- **Retry from §16:** 153 of 849 agent turns needed it (airline 120/686, DB twins 27/117,
  policy twins 6/46). That is 120 of the 252 airline turns that made a tool call (48%), in 48
  of 50 tasks. No empty agent turn is left in the results. **Without the retry, maverick
  cannot be evaluated on Prime.** The three models in §15 ran without the retry and have no
  empty or text-form tool calls (0 of 2,236 agent turns), so they are not affected.
- **Old models re-scored** as in §15 (`tau2 evaluate-trajs <run> --fresh-tasks`, outputs not
  committed). Pair scores: `uv run python ../twins/score_pairs.py <9 models>` with the
  re-scored old runs in place. The numbers for the 8 models in §15 are reproduced exactly.
- **Result, all 9 models.** "Reads gate" = evaluator reward. "+ twins" = reads-gate score with
  the 15 no-action verdicts replaced by paired verdicts. "No-action" = the 23 tasks the null
  agent passes (§1), original scoring. Cost: old models are 50 tasks only (§7); new models are
  50 tasks + 15 twins. Both include the user simulator.

  | Model | Original (50) | Reads gate | DB pairs (11) | Policy pairs (4) | **Reads gate + twins** | No-action (23) | Transfers on no-action | Cost |
  |---|---|---|---|---|---|---|---|---|
  | claude-sonnet-4.5 | 37 | 37 | 8 | 2 | **35** | 20 | 12 | $16.42 |
  | gpt-6-luna | 37 | 36 | 10 | 1 | **33** | 22 | 20 | $1.01 |
  | gpt-4.1 | 30 | 29 | 4 | 0 | **26** | 16 | 9 | $7.16 |
  | claude-haiku-4.5 | 24 | 23 | 6 | 2 | **21** | 18 | 15 | $5.60 |
  | gpt-4.1-mini | 20 | 20 | 5 | 1 | **19** | 13 | 10 | $2.29 |
  | llama-4-maverick | 23 | 22 | 3 | 0 | **16** | 16 | 9 | $3.97 |
  | gpt-5.4-nano | 15 | 15 | 0 | 1 | **12** | 9 | 8 | $3.40 |
  | llama-3.3-70b | 19 | 7 | 0 | 0 | **3** | 19 | 22 | $3.65 |
  | gpt-4.1-nano | 3 | 2 | 0 | 0 | **2** | 1 | 2 | $1.01 |

- **maverick is not a null-agent model like llama-3.3.** It passes 7 of the 27 action tasks
  (llama-3.3: 0) and transfers on 9 of 23 no-action tasks (llama-3.3: 22). The read gate
  removes one pass (task 9).
- **But the twins remove the most credit from maverick: 22 → 16 (6 tasks), the largest drop of
  the 9.** 6 of its 9 no-action passes on the twinned tasks have a failed twin. 6 twin failures
  are "no write": it reads, then does not make the change the twin calls for. Of its 3 policy-flip
  no-action passes, 2 fail the twin by not writing (tasks 2, 38) and 1 by a transfer (task 5). So its refusals look like reluctance to write, not
  reasoning from the data or the rule.
- **Weak points:**
  - 1 trial only (§7: a model can move 7 of 23 between identical runs).
  - 18% of maverick's agent turns are decoded with a forced tool choice (§16). This is not
    exactly the model's own output. A "no write" failure can still come from the model: the
    retry fires only when the model already produced a tool call.
  - The maverick numbers depend on Prime's gateway; another provider may give different
    results.

## 18. Scoreboard: 5 models and the null agent under all scoring methods (2026-10-08)
**By:** Hammad + Claude

- **Table:** `docs/research/scoreboard.md`, generated by `code/scoreboard.py` (code/README.md).
  No LLM calls; it re-scores the saved runs from §7–§9 and the null agent.
- **New runs (free, no LLM):** the null agent on all 15 twins,
  `code/tau2-bench/data/simulations/airline_twins_do_nothing/` and `airline_twins_pf_do_nothing/`.
  It passes **0 / 15**. Before, the null agent's twin score was an assumption for the policy
  twins (§8 ran only the DB twins and did not commit the results).
- **Cross-check:** the scoreboard applies the read check to the saved messages in-process. For all
  5 models it gives the same scores as `tau2 evaluate-trajs --fresh-tasks` (the evaluator path),
  and the same upstream rewards as the saved files. The twin column equals §9.
- **Result** (all 50 tasks, 1 trial; rank in brackets):

  | Model | Original | Reads | Twins | Twins (lenient) | **Reads + twins** |
  |---|---|---|---|---|---|
  | claude-sonnet-4.5 | 37 [1] | 37 [1] | 35 [1] | 35 [1] | **35 [1]** |
  | gpt-4.1 | 30 [2] | 29 [2] | 27 [2] | 28 [2] | **26 [2]** |
  | null agent | 23 [3] | 7 [4] | 8 [4] | 8 [4] | **3 [4]** |
  | gpt-4.1-mini | 20 [4] | 20 [3] | 19 [3] | 19 [3] | **19 [3]** |
  | llama-3.3-70b | 19 [5] | 7 [4] | 7 [5] | 8 [4] | **3 [4]** |
  | gpt-4.1-nano | 3 [6] | 2 [6] | 3 [6] | 3 [6] | **2 [6]** |

- **Meaning:**
  - Under upstream scoring the null agent ranks 3rd, above gpt-4.1-mini and llama. With both
    checks it falls to 3 / 50, level with llama.
  - llama loses 16 of its 19 points. Each check alone leaves it 7. Together they leave 3: the
    reads catch it on 12 tasks and the policy twins on 4 more (2, 5, 27, 38), where no read is
    required.
  - The capable models lose 1–4 points. The checks rarely remove a pass that was reasoned.
  - The 3 passes left for llama and the null agent are tasks 6, 13, 46, which have no check.
- **Weak points:** 1 trial. The read counts differ from §7 ("Reads kept": llama 8, gpt-4.1 16):
  §7 used the reads listed in the task files, the scoreboard uses the final spec in
  `justification.json`. Task 31 ran with the old $100 budget (decisions log, 2026-10-08).

## 19. Transcript patterns: what each check catches (2026-10-09)
**By:** Hammad + Claude

- **Why:** the TA asked for a qualitative account of the scoreboard (§18): what the checks catch
  in customer-service terms.
- **Method:** read every episode of the 5 models on the 23 no-action tasks, the 15 twins, and the
  tool-call sequences of the 27 action tasks. Same runs as §18, 1 trial. Counts:
  `uv run python ../transcript_patterns.py` (from `code/tau2-bench/`), no LLM calls.
- **Results** (50 base tasks unless stated):

  | Model | Transfers | Transfer before any successful read | Guessed user ID | Same outcome, task vs twin (15 pairs) |
  |---|---|---|---|---|
  | claude-sonnet-4.5 | 12 | 0 | 0 | 4 |
  | gpt-4.1 | 11 | 2 | 0 | 7 |
  | gpt-4.1-mini | 11 | 1 | 1 | 8 |
  | gpt-4.1-nano | 2 | 0 | 3 | 13 |
  | llama-3.3-70b | 48 | 41 | 32 | 14 (11 are a transfer on both) |

- **Meaning:**
  - Llama's −16 is a transfer-first habit. 15 of its 19 no-action passes are transfers before any
    successful lookup. It often guesses the user ID; `sara_doe_496` comes from the tool
    docstring. It passes 0 of the 27 action tasks.
  - Claude also transfers 12 times, but always after a lookup and a stated policy reason. Its
    outcome changes on the twin. The twin is what separates the two kinds of transfer.
  - The read check catches agents that trust the customer's claims (gpt-4.1 task 28: right
    refusal, no lookup). The DB twin catches a misapplied rule after a correct read (gpt-4.1-mini
    task 28 twin) and incomplete checks (gpt-4.1 task 41 twin cancels a flown trip). The policy
    twin catches agents that follow a habit, not the policy text (gpt-4.1, gpt-4.1-mini, Llama
    on tasks 2, 5, 27, 38).
  - Upstream scoring rewards "always refuse or transfer" (Llama 38%) but punishes "always act"
    (gpt-4.1-nano 6%). The twins make both fail.
- **Weak points:** 1 trial. Neither check reads the agent's words (Llama makes false policy
  claims that pass). Some twin failures are user-simulator noise (task 2 twin: Claude and gpt-4.1
  were pointed to the wrong reservation; task 27 twin: gpt-4.1's customer took a transfer).
  Llama's 3 kept passes (13, 46, 36) are accidents on tasks with no check or a failed tool call.
- Full analysis: `docs/research/qualitative-patterns.md`.

## 20. Three trials of the four newer models; mean scores and change from the gates (2026-10-10)
**By:** Vatsal + Claude

- **Models:** gpt-6-luna, claude-haiku-4.5, gpt-5.4-nano, llama-4-maverick (§15, §17).
- **Config:** the same as §15 and §17, except the seed. Trial 1 is the seed 300 run in §15 and
  §17. Trials 2 and 3 use seeds 301 and 302. User simulator `openai/gpt-4.1`, temperature 0,
  `--num-trials 1`, `--max-concurrency 5`. Code at commit `27f9472` (main, with the §16 retry).
  The four models ran at the same time.
- **Runs:** for each model and seed `N` in {301, 302}, three folders in
  `code/tau2-bench/data/simulations/`: `airline_<model>_seed<N>` (50 tasks),
  `airline_twins_<model>_seed<N>` (split `primary`, 11 DB twins),
  `airline_twins_pf_<model>_seed<N>` (4 policy twins). Same three commands as §15, with
  `--seed <N>` and `--save-to` names with the `_seed<N>` suffix.
- **Scoring:** `code/twins/average_trials.py` (new). It scores each trial with the pair rule of
  `code/twins/score_pairs.py` and averages over trials. It reproduces the §17 numbers for the
  seed 300 runs exactly, cost included. Command (from `code/tau2-bench/`):

  ```bash
  uv run python ../twins/average_trials.py gpt-6-luna:300,301,302 \
    claude-haiku-4.5:300,301,302 gpt-5.4-nano:300,301,302 llama-4-maverick:300,301,302
  ```

- **Per trial:**

  | Model | Seed | Original (50) | Reads gate | DB pairs (11) | Policy pairs (4) | Reads gate + twins | No-action (23) | Transfers on no-action | Cost $ |
  |---|---|---|---|---|---|---|---|---|---|
  | gpt-6-luna | 300 | 37 | 36 | 10 | 1 | 33 | 22 | 20 | 1.01 |
  | gpt-6-luna | 301 | 40 | 39 | 11 | 2 | 37 | 23 | 21 | 0.94 |
  | gpt-6-luna | 302 | 40 | 39 | 11 | 2 | 37 | 23 | 22 | 1.01 |
  | claude-haiku-4.5 | 300 | 24 | 23 | 6 | 2 | 21 | 18 | 15 | 5.60 |
  | claude-haiku-4.5 | 301 | 24 | 23 | 7 | 1 | 20 | 18 | 15 | 5.78 |
  | claude-haiku-4.5 | 302 | 25 | 25 | 4 | 2 | 20 | 19 | 15 | 5.65 |
  | gpt-5.4-nano | 300 | 15 | 15 | 0 | 1 | 12 | 9 | 8 | 3.40 |
  | gpt-5.4-nano | 301 | 18 | 17 | 1 | 0 | 13 | 12 | 9 | 2.93 |
  | gpt-5.4-nano | 302 | 17 | 16 | 3 | 1 | 15 | 11 | 8 | 2.05 |
  | llama-4-maverick | 300 | 23 | 22 | 3 | 0 | 16 | 16 | 9 | 3.97 |
  | llama-4-maverick | 301 | 22 | 19 | 2 | 0 | 12 | 16 | 10 | 4.92 |
  | llama-4-maverick | 302 | 23 | 20 | 6 | 0 | 15 | 19 | 13 | 3.69 |

- **Mean over 3 trials (min–max):**

  | Model | Original (50) | Reads gate | DB pairs (11) | Policy pairs (4) | **Reads gate + twins** | No-action (23) | Transfers on no-action | Cost, 3 trials |
  |---|---|---|---|---|---|---|---|---|
  | gpt-6-luna | 39.0 (37–40) | 38.0 (36–39) | 10.7 (10–11) | 1.7 (1–2) | **35.7 (33–37)** | 22.7 (22–23) | 21.0 (20–22) | $2.95 |
  | claude-haiku-4.5 | 24.3 (24–25) | 23.7 (23–25) | 5.7 (4–7) | 1.7 (1–2) | **20.3 (20–21)** | 18.3 (18–19) | 15.0 (15–15) | $17.03 |
  | llama-4-maverick | 22.7 (22–23) | 20.3 (19–22) | 3.7 (2–6) | 0.0 (0–0) | **14.3 (12–16)** | 17.0 (16–19) | 10.7 (9–13) | $12.58 |
  | gpt-5.4-nano | 16.7 (15–18) | 16.0 (15–17) | 1.3 (0–3) | 0.7 (0–1) | **13.3 (12–15)** | 10.7 (9–12) | 8.3 (8–9) | $8.39 |

- **Change from the original score (means):**

  | Model | Original | Reads gate | Reads gate + twins | Reads gate change | **Both gates change** |
  |---|---|---|---|---|---|
  | gpt-6-luna | 39.0 | 38.0 | 35.7 | -2.6% | **-8.5%** |
  | claude-haiku-4.5 | 24.3 | 23.7 | 20.3 | -2.7% | **-16.4%** |
  | gpt-5.4-nano | 16.7 | 16.0 | 13.3 | -4.0% | **-20.0%** |
  | llama-4-maverick | 22.7 | 20.3 | 14.3 | -10.3% | **-36.8%** |

- **Strict and lenient twin rules** (decisions log 2026-10-03). All "reads gate + twins"
  numbers above use the strict rule: any twin failure removes the credit. The lenient rule
  also counts a twin when the agent made the right write despite other errors. It changes one
  trial only: gpt-5.4-nano at seed 300, twin `28_twin_business`, 12 → 13. The nano mean goes
  13.3 → 13.7, and its change from the original score goes -20.0% → -18.0%. The other three
  models are the same under both rules. `code/twins/average_trials.py` prints both.

- **What it means:**
  - The §17 order of these four models holds in every trial on "reads gate + twins":
    luna > haiku > maverick, nano. maverick and nano overlap (12–16 vs 12–15).
  - On the original score, maverick (22.7) is close to haiku (24.3). After both gates it is
    6 points below haiku. maverick loses the most credit (-36.8%), and luna the least (-8.5%).
    This is the §17 result, now over 3 trials.
  - The reads gate alone removes 2.6–4.0% for luna, haiku and nano, and 10.3% for maverick.
    Most of the drop comes from the twins.
  - maverick passes 0 of 4 policy pairs in all 3 trials.
  - Trial 1 was luna's lowest run (37 vs 40, 40).
- **Retry from §16 (maverick):** seed 301: 149 of 921 agent turns; seed 302: 140 of 822
  (16–17%, about the same as trial 1). No empty agent turn is left in any new run.
- **Weak points:**
  - Temperature is 0 for both agent and user. The trials differ because the seed changes and
    the providers are not deterministic. They are not independent samples at a higher
    temperature.
  - 3 trials only. A range of 3–4 points (nano, maverick) means a difference of 1–2 points
    in the means is not reliable.
  - `max_steps` (counted as a failure): gpt-5.4-nano task 15 at seed 301 (also at seed 300,
    §15), llama-4-maverick task 6 at seed 301.
  - Cost is saved tokens × the list prices of §15 and §17. Prime's real price was not checked.

## 21. Newer models: scoreboard and transcript patterns; correction to §17 (2026-10-10)
**By:** Hammad + Claude

- **Why:** the TA's two requests: qualitative explanations (§19) and newer models (§15–§17). This
  entry applies §18 (scoreboard) and §19 (transcript analysis) to the four newer models only.
  The two sets are kept apart (decisions log, 2026-10-10).
- **Runs:** the §15 and §17 runs for claude-haiku-4.5, gpt-6-luna, gpt-5.4-nano,
  llama-4-maverick. No new runs, no LLM calls.
- **Commands** (from `code/tau2-bench/`):
  `uv run python ../scoreboard.py --set new` → `docs/research/new-models/scoreboard.md`;
  `uv run python ../transcript_patterns.py` (counts).
- **Scores** (all 50 tasks; reproduce §17 exactly):

  | Model | Original | Reads | Twins | **Reads + twins** |
  |---|---|---|---|---|
  | gpt-6-luna | 37 | 36 | 34 | **33** |
  | claude-haiku-4.5 | 24 | 23 | 22 | **21** |
  | llama-4-maverick | 23 | 22 | 16 | **16** |
  | gpt-5.4-nano | 15 | 15 | 12 | **12** |
  | null agent | 23 | 7 | 8 | **3** |

- **Transcript counts** (`code/transcript_patterns.py`):
  - Transfers before any successful read: luna 4/50, maverick 3, haiku 1, nano 1
    (llama-3.3-70b had 41).
  - Silent transfers (read, then transfer, no reply) on no-action tasks: luna 6/23, others 0.
  - Writes typed as text and never run: maverick 13/65 episodes; 4 of its 16 no-action passes
    contain such a write of a *forbidden* action (tasks 4, 5, 10, 26). Others 0.
  - Writes on a reservation before reading it: gpt-5.4-nano 5/65, haiku 1, maverick 1.
  - Guessed user IDs: maverick 8/50, of which 7 are on turns forced by the §16 retry.
- **Every one of the 17 removed no-action passes was read by hand.** 12 are real agent errors (7
  of them remove an unreasoned base pass). 2 come from the task 27 twin script (the customer asks
  why the flight was late and accepts a transfer before any certificate): haiku and luna. 3 are
  maverick cancels typed as text on the 0, 28, 49 twins. Without the 5 doubtful removals: luna
  34, haiku 22, maverick 19, nano 12. The ranking does not change.
- **Correction to §17.** §17 says maverick's twin failures show "reluctance to write". Of its 6
  twin removals: 3 are correct cancels lost as text (it says, e.g., "your reservation is for
  business class, I can assist you with the cancellation. [cancel_reservation(...)]" and then
  confirms a refund), 2 are the tasks 2/38 twin script (the customer leads it to the wrong
  reservation), and 1 (task 5) is a real blind transfer. The §16 retry does not catch a call
  that is embedded in prose.
- **New patterns:** P9 phantom write (maverick), P10 silent handoff (luna), P11 hand off under
  pushback before the allowed action (luna, haiku), P12 hedge and comply (haiku), P13 act first,
  check later (gpt-5.4-nano). The policy flip seldom finds a policy habit here: the newer models
  quote and follow the flipped clause.
- **Problems found in our checks:** the task 27 twin script; the tasks 2/38 twin scripts (also
  seen in the older set); task 34's "move back by one day" wording; no detection of text-form
  tool calls; no transfer check.
- **Weak points:** 1 trial. The silent-transfer and text-call counts are pattern matches; every
  case used in the analysis was also read by hand.
- Full analysis: `docs/research/new-models/qualitative-patterns.md`. Comparison with the older
  set: `docs/research/new-models/old-vs-new.md`.

## 22. Newer models over 3 trials: pass^k, stability of removals, behaviour counts (2026-10-10)
**By:** Hammad + Claude

- **Why:** §20 added trials 2 and 3 and reported means and ranges. This entry adds measures that
  use the trials: pass^k, how stable each removal is, and the behaviour counts of §21 over all
  trials. No new runs, no LLM calls.
- **Commands** (from `code/tau2-bench/`): `uv run python ../scoreboard.py --set new`
  (`docs/research/new-models/scoreboard.md`, §1–§6) and `uv run python ../transcript_patterns.py`.
  The scoreboard's means equal §20 exactly.
- **pass^k** (the chance of passing a task in all k trials, summed over tasks; C(c, k) / C(n, k)):

  | Model | Original pass^1 → pass^3 (50 tasks) | **Reads + all twins** pass^1 → pass^3 (50 tasks) | No-action tasks, reads + all twins, pass^1 → pass^3 (of 23) |
  |---|---|---|---|
  | gpt-6-luna | 39 → 33 | **35.7 → 29** | 19.3 → 18 |
  | claude-haiku-4.5 | 24.3 → 17 | **20.3 → 13** | 14.3 → 10 |
  | llama-4-maverick | 22.7 → 14 | **14.3 → 5** | 8.7 → 3 |
  | gpt-5.4-nano | 16.7 → 9 | **13.3 → 6** | 7.3 → 3 |
  | null agent | 23 → 23 | **3 → 3** | 3 → 3 |

- **Stability of removals** (no-action tasks that passed upstream in at least one trial):

  | Model | Tasks | Removed in every trial it passed | Removed in some trials | Never removed | Removal events |
  |---|---|---|---|---|---|
  | gpt-6-luna | 23 | 2 (34, 38) | 2 (5, 27) | 19 | 10 |
  | claude-haiku-4.5 | 21 | 2 (27, 47) | 5 | 14 | 12 |
  | llama-4-maverick | 21 | 8 | 5 | 8 | 25 |
  | gpt-5.4-nano | 16 | 3 | 4 | 9 | 10 |

- **Behaviour counts over 3 trials** (§21 counts, now per 150 base or 195 base + twin episodes):
  luna silent transfers 18 / 69 no-action episodes (6, 6, 6); gpt-5.4-nano writes before
  reading 15 / 195; maverick writes typed as text and never run 35 / 195, and 12 of its 51
  no-action passes contain one; maverick guessed user IDs 24 / 150. The per-model styles of
  §21 are stable across trials.
- **Meaning:**
  - pass^3 widens the gaps the checks make. maverick keeps 5 tasks it passes in all 3 trials
    under both checks (14 upstream). The null agent's 3 come from tasks 6, 13, 46, which have no
    check.
  - A removal in every trial is not proof of a correct removal. Two of the stable removals are
    known artifacts: haiku task 27 (the task 27 twin script, §21) and maverick task 49 (its
    correct cancel is typed as text in every trial). Stability separates noise from a
    systematic cause; it does not say whose fault the cause is.
- **Weak points:** temperature 0, so the trials differ only through the seed and provider
  non-determinism (§20). The 40 removal events of trials 2 and 3 (57 over all 3 trials) are not yet read by hand; the
  verdicts in §21 cover trial 1 only.


## 23. Newer models: every removal judged over 3 trials; attempted writes on no-action passes (2026-10-10)
**By:** Vatsal + Claude

- **Why:** §21 and §22 left the 40 removal events of trials 2 and 3 unread. The handoff
  (`docs/research/new-models/review-handoff.md`) asked for a full review with a two-question
  rubric: was the original pass reasoned (Q1), and why did the gate fail (Q2).
- **What was done:** one reviewer agent per model read every removal in seeds 301–302 and skimmed
  every kept no-action pass in all 3 seeds. Seed 300 uses the handoff §4 verdicts; none needed a
  change. No new runs, no LLM calls in the scoring. Full note:
  `docs/research/new-models/review-3-trials.md`; per-model files in
  `docs/research/new-models/review/`.
- **New count** (from `code/tau2-bench/`): `uv run python ../transcript_patterns.py` now reports
  "No-action passes with a write call attempted (failed or no-op)".
- **Results, all 3 seeds, 4 models** (TP / right removal by the wrong mechanism / FP):

  | Gate | Removals | TP | WM | FP |
  |---|---|---|---|---|
  | Read check | 14 | 14 | 0 | 0 |
  | DB twin (strict) | 17 | 3 | 4 | 10 |
  | DB twin (lenient) | 16 | 3 | 4 | 9 |
  | Policy twin | 29 | 5 | 11 | 13 |

- **Attempted writes:** 20 of 206 newer-model no-action passes contain a write call that failed
  or changed nothing, or a write typed as text: luna 0 / 68, haiku 3 / 55, nano 4 / 32, maverick
  13 / 51, null agent 0 / 23. 15 of the 20 are kept by every current gate. Example: haiku, task
  13, 3 of 3 seeds, a forbidden destination change that failed only with "Flight HAT030 not
  available". In the older set: llama-3.3-70b 2 / 19, the others 0.
- **Meaning:**
  - The read check is exact on this set. It is the result to lead with.
  - The DB twin does not punish reasoning: luna has 0 DB-twin removals and passes 33 of 33 DB
    twins. Half of its FPs are maverick's (3 lost text calls on task 49, 2 rule errors).
  - The policy twin is not evidence until the scripts are fixed (M1.24). 13 of its 29 removals are
    FPs, from the task 5, 27 and 2 scripts and the simulated user.
  - A "no write attempted" gate would remove the 15 kept attempted-write passes, with no new runs
    (M1.27). Hand projection of the headline: haiku 20.3 → 19.3, maverick 14.3 → 11.7, nano
    13.3 → 12.0, luna and the null agent unchanged.
- **Open question:** haiku recites the business-cabin refund rule on the original tasks 47 and 28,
  then refuses on the twins where the cabin is business (3 removals). Q1 as written calls these
  FPs. If "the decisive fact did not change the decision" counts as unreasoned, they are TPs, and
  the DB twin scores 6 / 4 / 7.
- **Weak points:** the reviewers are LLM agents with no blind second labeller. The attempted-write
  projection is by hand, not computed by `code/scoreboard.py`.

## 24. WorkBench: phase 1 checkups, and the 4 newer models over 3 trials under the read gate and twins (2026-10-22)
**By:** Hammad + Claude

- **Why:** M2 (charter §3, Target tier). We apply the τ² method to a second benchmark
  (decisions log, 2026-10-21 and 2026-10-22). The plan and the checkups of the dropped
  candidates (AgentDojo, WebArena, BFCL) are in `docs/research/other-benchmarks/plan.md`.
- **Benchmark:** WorkBench (Styles et al., COLM 2024), our copy at upstream `49c7dfd` in
  `code/workbench/`. 690 tasks. **122 (17.7%) have an empty gold outcome.** All of these are the
  τ² "possible" type: a false condition or an empty set.
- **Runs:** claude-haiku-4.5, gpt-5.4-nano, gpt-6-luna and llama-4-maverick through Prime
  Intellect, at temperature 0. 3 trials, labelled seeds 300/301/302. WorkBench Revisited
  settings: all tools, native tool calls, act without confirmation.
  - Originals: 690 tasks per model and trial.
  - DB twins: 110, of 113 built. Request twins: 46, plus CRM-070, which is reused.
  - Command, from `code/workbench/`:
    `uv run python ../workbench-m2/run.py --model <m> --run original_seed<N>`. For twins, add
    `--run dbtwin_seed<N>` or `requesttwin_seed<N>` and
    `--tasks ../workbench-m2/data/twins_{db,request}_tasks_and_outcomes.csv`.
  - Runs are in `code/workbench-m2/runs/`.
  - Scoring: `uv run python ../workbench-m2/score.py` writes
    `docs/research/other-benchmarks/workbench-scoreboard.md`.
- **Our pipeline reproduces the benchmark.**
  - haiku trial 1: 510/690, against 516 in WorkBench's published haiku run. No-op passes are
    93 against 93, and per-task agreement is 642/690.
  - nano: 353 against 335. We use temperature 0; the published run used the default.
- **Null agent:** 124/690 (122 no-op tasks, plus CRM 031 and 032, where the gold reassigns a
  customer to the person who already owns them).
  - After the read gate: 12. After all gates: 7.
  - The 7 are CRM 031 and 032, plus 5 no-op tasks that no DB flip can reach (§ weak points).
- **Mean over 3 trials (min–max), out of 690:**

  | Model | Original | Reads gate | **Reads + twins** | Lenient | Acted (sensitivity) | No-op passes | Reads change | **All gates change** | Cost, 3 trials |
  |---|---|---|---|---|---|---|---|---|---|
  | gpt-6-luna | 611.7 (608–615) | 611.7 | **599.0 (596–602)** | 600.0 | 610.3 | 113.7 | +0.0% | **−2.1%** | $6.09 |
  | claude-haiku-4.5 | 510.0 (510–510) | 509.0 | **494.0 (494–494)** | 495.0 | 506.0 | 93.0 | −0.2% | **−3.1%** | $89.59 |
  | gpt-5.4-nano | 352.3 (342–362) | 344.7 | **331.7 (325–343)** | 332.7 | 340.0 | 48.7 | −2.2% | **−5.9%** | $11.74 |
  | llama-4-maverick | 120.0 (108–127) | 93.0 | **84.7 (82–87)** | 84.7 | 86.0 | 38.0 | −22.5% | **−29.4%** | $17.09 |
  | null agent | 124 | 12 | **7** | 7 | 7 | 122 | −90.3% | **−94.4%** | $0 |

  "Acted" counts a twin as passed when the agent made any write. It is a sensitivity rule, not
  the headline.
- **The ranking does not change, and the size of the drop follows the τ² pattern.** luna
  loses least and maverick most, as on τ² airline (findings §20: −8.5% to −36.8%). The drops
  are smaller here because no-op tasks are 18% of WorkBench and 46% of airline.
- **pass^3, reads + twins:** luna 599 → 550, haiku 494 → 494, nano 331.7 → 238, maverick
  84.7 → 77.
  - On the no-op tasks alone: luna 101 → 87, haiku 77 → 77, nano 28 → 18, maverick 2.7 → 0.
- **Stability of removals:**
  - **haiku is deterministic.** Its tool calls are identical in 688–690 of 690 tasks across
    trials, so every haiku removal repeats in all 3 trials.
  - **maverick:** 44 of its 49 tasks are removed in every trial in which they passed.
  - **luna:** 19 of its 22 removed tasks are removed in only some trials.
- **Twin failure causes** (all trials):

  | Model | DB twin failures | No write | Wrong write | Right write + other | Error | Request twin failures | No write | Wrong write |
  |---|---|---|---|---|---|---|---|---|
  | luna | 25 | 3 | 22 | 0 | 0 | 19 | 1 | 15 |
  | haiku | 42 | 12 | 27 | 3 | 0 | 15 | 0 | 15 |
  | nano | 54 | 27 | 23 | 4 | 0 | 17 | 7 | 10 |
  | maverick | 99 | 51 | 7 | 0 | 41 | 46 | 16 | 4 |

  For luna and haiku, most failures are "acted, but a detail is wrong" against WorkBench's
  exact-match gold. Examples: the first free slot tomorrow (13:00), an event name the text does
  not state, a plot range, a participant left out. The same strictness applies to the template's
  own action tasks (scoreboard §8). The qualitative review (findings §25) judges each one.
- **Read gate on the 32 published WorkBench runs** (no model calls;
  `code/workbench-m2/published_readgate.py`):
  - 0 removals for the frontier 2026 models: fable-5, opus-4.8, gemini-3.1-pro, gpt-5.5, gpt-5
    and others.
  - 0.4–6% of the score for mid-tier 2026 models: gpt-4-turbo −26, gpt-4o −20, gpt-5.1 −18,
    nano −14.
  - 10–60% for the 2024 paper models: gpt-4 −10%, claude-2 −18%, mixtral-8x7b 111 → 45 (−59.5%).
  - claude-2 reads, but not the deciding record. A crude "any read" check keeps its passes; the
    twin-defined gate removes 33.
- **llama-4-maverick:**
  - About a third of its episodes crash on invented tool arguments (upstream rule: an error,
    counted as a failure).
  - 609 final answers contain a tool call typed as text.
  - Its trial 1 had 23 no-op passes; trials 2–3 had 46 and 45, with twice as many episodes that
    end with no call and no error. The code was the same, so this is provider drift.
  - The read gate removes the extra passes: after all gates maverick scores 87, 85, 82.
  - The τ² §16 retry fired 258–298 times per trial, for maverick only.
- **Weak points:**
  - 9 no-op tasks cannot be flipped. Example: growth "since Wednesday", where Wednesday is the
    last day of data, so the growth is 0 on every state.
  - calendar-073 follows from the system prompt's 9am rule alone.
  - These 10 tasks have no read gate and no DB twin (as τ² tasks 6, 13, 46). 4 of the 9 have a
    request twin.
  - 3 twins were not run after the twin reviews; 2 of them still define the read gate.
  - Trials differ only through provider non-determinism. For haiku that is none.
  - 3 maverick episodes ended in a gateway timeout that persisted on retry; they count as
    errors.
  - Cost is tokens × Prime Intellect list prices (GET /models, 2026-10-22). Trial 1's crashed
    episodes have no token counts, because the counter fix came after trial 1.
  - WorkBench's request twin is our policy-twin analogue (no policy text exists). It is a
    one-slot request change, and it must not be read as a policy flip.
