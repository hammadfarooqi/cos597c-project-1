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

**Last updated:** 2026-10-03 (§1–§7)

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
