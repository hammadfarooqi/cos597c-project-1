---
title: Older vs Newer Models — Short Comparison
type: research
status: current
updated: 2026-10-10
review_by: 2026-11-01
summary: >-
  One page that sets the older five models beside the newer four. The older set showed the
  failure patterns in exaggerated form (llama-3.3-70b's blanket transfers). The newer set has
  smaller, model-specific failures, and it exposed problems in three twin scripts.
note: >-
  Secondary. The main analyses are separate: docs/research/qualitative-patterns.md (older) and
  docs/research/new-models/qualitative-patterns.md (newer). 1 trial per model.
---

# Older vs Newer Models — Short Comparison

**Last updated:** 2026-10-10

The two sets are analysed separately. This page only lines them up. Scores:
`docs/research/scoreboard.md` (older) and `docs/research/new-models/scoreboard.md` (newer).

## 1. Points removed by reads + twins (all 50 tasks)

| Older model | Original → reads + twins | Newer model | Original → reads + twins |
|---|---|---|---|
| claude-sonnet-4.5 | 37 → 35 (−2) | claude-haiku-4.5 | 24 → 21 (−3) |
| gpt-4.1 | 30 → 26 (−4) | gpt-6-luna | 37 → 33 (−4) |
| gpt-4.1-mini | 20 → 19 (−1) | gpt-5.4-nano | 15 → 12 (−3) |
| gpt-4.1-nano | 3 → 2 (−1) | llama-4-maverick | 23 → 16 (−7) |
| llama-3.3-70b | 19 → 3 (−16) | | |

The null agent loses 20 in both (23 → 3).

## 2. Which patterns appear where

Plain names for each behaviour. The two analyses describe each one in detail.

| Pattern | Older set | Newer set |
|---|---|---|
| Transfer before any lookup | llama-3.3: 41 / 50 | at most 4 / 50 (luna) |
| Guessed customer IDs | llama-3.3: 32 / 50 | maverick 8 / 50, 7 caused by the forced-tool retry |
| Explain, then escalate on request (good) | sonnet (all 12 transfers) | haiku (14 of 15) |
| Believe the customer over the record | gpt-4.1 (28, 48, 49, 5 twin) | haiku 48, gpt-5.4-nano 2 twin |
| Read the fact, then misapply the rule | gpt-4.1-mini 28 twin | haiku 47 twin |
| Follow a habit, not the written policy | gpt-4.1, mini, llama-3.3 | mostly absent; the newer models follow the changed clause |
| Incomplete checks | gpt-4.1 41 twin | gpt-5.4-nano 41, maverick 9 |
| Always act / act first, check later | gpt-4.1-nano (always); gpt-4.1 48, 49 | gpt-5.4-nano, 5 / 65 writes before a read |
| Says it acted, but the action never ran | — | maverick, 13 / 65 episodes |
| Escalate instead of saying no (silent handoff) | (llama-3.3: 3) | luna, 6 / 23 silent; 21 / 23 transfer |
| Hand off before finishing the allowed action | (gpt-4.1 27 twin) | luna, haiku on policy twins |
| State the facts, then give in | — | haiku 26, 43, 47 |

## 3. Three family comparisons

- **llama-3.3-70b → llama-4-maverick.** Transfers fall from 48 to 14 of 50; blind transfers
  from 41 to 3; action-task passes rise from 0 to 7. The new failure: on Prime Intellect, maverick
  types tool calls into its text and says the action is done, but it never runs. Llama-3.3's
  drop measured the model; much of maverick's drop measures the serving stack.
- **claude-sonnet-4.5 → claude-haiku-4.5.** Both read first and explain refusals. Haiku gives
  in more often after it has stated the facts.
- **gpt-4.1-nano → gpt-5.4-nano.** Both lean toward acting. gpt-4.1-nano wrote on 22 of 23
  no-action tasks with little checking; gpt-5.4-nano writes on 15, reasons well when it
  refuses, but often writes before it reads.

## 4. What the newer set taught us about the checks

- The older set showed that the checks work on an extreme case. The newer set shows their
  limits: 5 of 17 removals come from our twin scripts (task 27) or lost tool calls, not from
  the agent.
- The same twin-script problems appear in both sets: the task 27 twin ("why was my flight
  delayed?" ends in a transfer) and the tasks 2 and 38 twins (the customer points to the wrong
  reservation). Fix these before more runs.
