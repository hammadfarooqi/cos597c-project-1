---
title: WorkBench — Review Handoff (Rubric for Every Removal)
type: research
status: current
updated: 2026-10-22
summary: >-
  The rubric and data pointers for the qualitative review of every WorkBench no-op pass that a
  gate removes (4 newer models, 3 trials). It is the two-question rubric of the tau2 review,
  adapted to WorkBench, which has no simulated user and no policy text.
note: >-
  Written for reviewer agents. It follows docs/research/new-models/review-handoff.md §3.
---

# WorkBench — Review Handoff

**Last updated:** 2026-10-22 · **By:** Hammad + Claude

## 1. The task

Judge **every removal event**: a no-op task that a model passed in one trial (WorkBench's own
scorer) and that a gate removed in the same trial. Also skim the no-op passes that every gate
kept, to find false negatives. Do this for one model per reviewer. Use all 3 trials (seeds 300,
301, 302).

Gates: **read gate** (R) · **DB twin** (D) · **request twin** (Q). Judge each gate separately.
Report the strict rule. Also note when the lenient rule would keep the pass ("right write +
other difference").

## 2. Where everything is

All paths are relative to the repository root.

- **Episodes:** `code/workbench-m2/data/episodes.jsonl`, one line per episode.
  - Fields: model, seed, kind (original, db, request), task_id, orig_task_id, task, gold,
    calls, error, pass, pass_lenient, cause.
  - Originals also have revealing_reads and read_gate.
  - Request twins may have `orig_task_id` "a;b" (one twin shared by two originals).
- **Per-trial removals:** `code/workbench-m2/data/trial_summary.json` (fields removed_reads,
  removed_db, removed_req, removed_all for each model and seed).
- **Scoreboard:** `docs/research/other-benchmarks/workbench-scoreboard.md`. Its §7 marks the
  removals for each task.
- **Full step-by-step traces:**
  `code/workbench-m2/runs/<run>/<domain>/<model>_all_*_traces.compact.json.gz`.
  - Each record is `{"task", "steps": [{action, action_input, observation, llm_output}]}`. The
    model's final answer is the step with action "Final Answer".
  - Runs: `original_seed30N` (folders by domain), `dbtwin_seed30N/twins_db`,
    `requesttwin_seed30N/twins_request`.
- **Twin designs:** `code/workbench-m2/data/twins_db_tasks_and_outcomes.csv`,
  `code/workbench-m2/data/twins_request_tasks_and_outcomes.csv` and
  `code/workbench-m2/data/twins_report.json`. Each twin has a `why` column that says what was
  flipped.
- **Task parameters and the official gold:** `code/workbench-m2/data/task_params.jsonl`.
- **Agent system prompt:** "Today's date is Thursday, 2023-11-30 and the current time is
  00:00:00. Remember the current date and time when completing tasks. Meetings must not start
  before 9am or end after 6pm. Do not ask for confirmation before executing actions. Execute
  actions immediately and continue until the task is fully complete. Do not stop after a search
  or lookup step." The agent has all 26 tools.

## 3. The rubric: ask two questions, never one

- **Q1: was the original no-op pass reasoned?** Did the agent reach "no change" *because of*
  the fact or rule that decides the case? It must have looked at the right records and drawn
  the right conclusion from them.

  The removal is a **true positive (TP)** only if the answer is no. Examples:
  - the agent never checked;
  - it checked the wrong person, metric or window;
  - it misread the data and still landed on "no change" by luck;
  - a crash, an empty turn, or a tool call typed as text ended the episode before any action.
- **Q2: why did the gate fail?**
  - **(a)** The agent's decision does not follow the fact or rule. This is the intended catch:
    on the twin it still does nothing, or it does the wrong thing *because it ignores the
    flipped fact*.
  - **(b)** An unrelated agent error on the twin. The agent saw that it must act, but got a
    detail wrong. Examples: a wrong meeting slot, an event name the text did not give, a wrong
    plot date range, a participant left out.
  - **(c)** The twin's design or the template's wording. The twin text or gold is ambiguous,
    or a search cap hid records.
  - **(d)** A lost tool call (a call typed as text, an empty turn), or a crash (an error).

  For the read gate (R), Q2 is just "no read revealed the deciding record". Check whether the
  agent found the fact another way that the rule misses. For example: a read that would have
  shown the flip, but with a different argument format.

Verdicts:
- **TP:** Q1 = not reasoned, and Q2 = (a), or R with no valid read.
- **WM (right removal, wrong mechanism):** Q1 = not reasoned, but Q2 = (b), (c) or (d).
- **FP:** Q1 = reasoned. The original pass was justified, and the gate removed it anyway.
- **FN (false negative):** an unreasoned pass that every gate kept. List these separately.

## 4. Known issues to check before you blame a model

These come from the twin reviews (2026-10-22) and the first twin trial.

- **Inherited template strictness.** WorkBench's scorer needs exact arguments. Several twin
  failures are "acted, but a detail is wrong". These are Q2 (b) or (c), not (a). Common cases:
  - **First free slot tomorrow.** It is 2023-12-01 13:00 in every twin. Meetings fill the day
    from 09:00 to 13:00.
  - **The "catch-up" event name.** The wording "I think I might need to catch up with X … schedule
    a 30-minute meeting" does not give the name, but the upstream gold uses "catch-up".
  - **"For us" templates.** Agents often leave out the participant (multi_domain-170, 172, 175).
  - **"Last N weeks" plot ranges.** Agents may end the range on 11-30 instead of 11-29 (both
    are accepted), or start it on another day (only one start is accepted).
  - **Meetings at a stated time that overlap existing meetings** (multi_domain-040 to -049).
- **Originals whose no-op verdict is itself ambiguous** (Q1 is hard here, so say so):
  - Tasks due exactly 2023-11-30 count as not overdue upstream: project_management-021, 022,
    027, 028, 064, 065 and multi_domain-081, 085, 087, 089. An agent that acts on these "fails"
    the original. An agent that passes may have been right for the wrong reason.
  - "Currently working on" means In Progress only upstream. leila and santiago also have In
    Review tasks (project_management-050, 056, 058).
  - multi_domain-179 ("Also schedule a half-hour meeting…"). The "Also" clause reads as
    unconditional.
  - The CRM notes disagree with `last_contact_date` in multi_domain-005 and 008.
  - Agents read today's empty analytics bucket (11-30) as 0 (analytics-060, 064, 067, 074, 076).
- **Large DB patches.** The traffic-source twins (analytics-111: 59 rows, 113: 22, 114: 97,
  115: 41, 117: 27) are far from minimal. If one fails, check whether the agent simply did not
  believe the totals.
- **Search caps.** Calendar, email and CRM searches return at most 5 rows. A read gate removal
  where the agent searched by name, with no date range, and the deciding record was not among
  the first 5 is a **TP**: the agent did not see the fact. This happens for multi_domain-052
  and 056.
- **Ungated tasks.** 9 no-op tasks cannot be flipped (growth from a day to itself), and
  calendar-073 follows from the 9am rule alone. These have no read gate and no DB twin. 4 of
  the 9 have a request twin. Count their passes as kept, and list any FNs among them.
- **llama-4-maverick.** About a third of its episodes crash on invented tool arguments (the
  upstream rule). Many of its final answers contain a tool call typed into prose that never ran.
  Check `text_form_call` and the final answer before you call a pass reasoned.

## 5. Output

Write one file per model: `docs/research/other-benchmarks/workbench-review/<model>.md`.
- Give it frontmatter (type: research, status: current, updated: <date>, summary).
- Include a table of every removal event: seed, task, gate, Q1 with a short quote or step
  reference, Q2 cause, and verdict.
- Then add: counts of TP / WM / FP per gate; the FNs you found; and 3–6 behaviour patterns,
  each with an example episode.
- Quote the agent's words or calls. Do not paraphrase from memory. Say when a judgement is
  uncertain.
