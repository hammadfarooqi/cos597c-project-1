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

**Last updated:** 2026-10-03 (§1–§3)

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
