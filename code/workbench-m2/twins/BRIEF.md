# Brief: write WorkBench twin specs (for subagents)

Read this whole file first. Then read `framework.py`, `build.py`, `readgate.py` and the
worked example `specs_calendar_email.py` (template "Cancel future {event_name} meetings")
in this folder.

## Context

COS597C project. τ²-bench gives credit to agents that do nothing. We grade a no-action
verdict as justified only if (1) the agent read the deciding fact and (2) it acts
correctly on a **twin**: a copy of the task where one fact changes so the correct outcome
becomes an action. We now apply this to **WorkBench** (690 tasks; 122 have an empty gold
outcome, from 31 templates). Paid model runs will execute every twin you design, 3 times,
for 4 models. A bad twin wastes money and corrupts results. Be careful and conservative.

Working directory for every command: `/Users/hammadfarooqi/Documents/Code/cos597c/project1-workbench/code/workbench`
(WorkBench copy). Run Python with `uv run python ...`.

- Tasks with their exact generator parameters: `../workbench-m2/data/task_params.jsonl`
  (fields: task_id, task, base_template, chosen_template, outcome, domains, params).
- Upstream generators (the gold rules you must mirror):
  `scripts/data_generation/task_outcome_generation/generate_*_task_and_outcome.py`.
- Sandbox data: `data/processed/*.csv`, loaded as `ToolState` (`src/tools/state.py`).
  All columns are strings, except `analytics_data.user_engaged` (bool).
- Tools: `src/tools/*.py`. Upstream scorer: `src/evals/evaluation.py::is_correct`.
- Patch format: see `_patched` in `src/tools/state.py` (ops `append`, `set`, `delete`;
  `where` must match exactly one row).

## Your job

For each template assigned to you, add a `register(base_template, gold, db_flip,
request_flip)` call in your module (named in your task). For each template:

1. **`gold(p, s)`**: the upstream logic function's rule, as a pure function of the
   parameters `p` (from task_params.jsonl) and the state `s`. Return action strings in
   upstream format, e.g. `calendar.delete_event.func(event_id="00000170")`. Read the
   upstream logic function and mirror it exactly (filters, `>` vs `>=`, dates relative to
   `HARDCODED_CURRENT_TIME` = 2023-11-30 00:00:00, rounding, case handling, how params are
   transformed for the text). Check G1 proves it: on the unchanged state it must give the
   official outcome for **all 10 tasks** of the template, not only the no-op ones.
2. **`db_flip(p, s)`**: returns `(patch, why)`. A start-state patch that makes the action
   correct for this no-op task, and one plain sentence saying what changed and why the
   action is now right. The DB twin's gold is computed by `gold(p, patched state)`. Do
   not hand-write it.
3. **`request_flip(p, s)`**: returns `(new_params, why)`, or `None`. It changes ONE slot of
   the request (a threshold, a number of days or weeks, a comparison word) so that the
   action is correct on the UNCHANGED state. `new_params` is `p` with one slot changed;
   the twin text is `chosen_template.format(**new_params)`. Return `None` when no single
   slot change gives a clean flip. Pass `request_flip=None` to `register` if the template
   never has one.

## Design rules for flips (lessons from τ²-bench; follow them)

- **Minimal.** Change one fact: one appended row or one changed cell, where possible. If
  the condition needs more (e.g. two recent meetings must both go), touch the fewest rows
  and say so in `why`.
- **Realistic.** The patched world must be a plausible state of the same workplace: a new
  email arrives, a task's status or due date differs, a meeting exists, one day's metric
  value differs. New rows copy an existing row's format exactly (ids unique and zero-padded
  like the others, the same date format, emails that exist in the data, dtypes). Do not
  create impossible data.
- **Unambiguous, with margin.** After the patch, a careful agent that follows the task text
  must reach exactly the twin gold. No borderline values: keep a clear margin from any
  threshold, larger than any rounding the task or tools apply. No ties (e.g. "the person
  with the most completed tasks", "the latest email"). The patch must not change any other
  part of the answer by accident (e.g. the first free slot tomorrow).
- **Do not make the twin hard for unrelated reasons.** Keep the twin gold small (1–2
  actions where possible). In τ²-bench, twins that failed for unrelated reasons gave false
  removals. The twin should differ from the original only in the deciding fact.
- **Visible where the agent looks.** The flipped record must appear in the output of the
  reads a reasonable agent makes for this task. Check D5 reports how many of 5 strong
  published models' reads would have revealed your flip. Aim for 5/5, and never accept 0/5.
  Remember that search tools may cap their number of results (read the tool code).
- **Request flips:** the new slot value must be one the generator itself could produce
  (same format and range), and it must flip with clear margin. Prefer the value nearest the
  original that flips cleanly. Do not use a request flip that also changes which records the
  task is about (e.g. a different person), because that is a different task, not a rule
  change.

## How to check

`uv run python ../workbench-m2/twins/build.py --only "<distinctive substring of the base template>"`

You need 0 failures for your templates. G1 must hold for all tasks of each template. Look at
the `D5_strong_reveal` value of each twin: run the script with `--write` disabled, and print
the values from inside a small script of your own if you need to (do NOT pass `--write`). You
may import `build`, `framework` and `readgate` in your own scratch scripts.

## Hard rules

- No LLM calls, no paid API calls, and no network access are needed. Do not run models.
- Do not edit `framework.py`, `build.py`, `readgate.py`, anything under `code/workbench/`,
  or another group's spec module. If you need a change there, say so in your report.
- Do not run git commands.
- Write only your own spec module, plus scratch files under `/tmp` if you need them.

## Report (your final message)

For each template: the rule you mirrored (the upstream function name), the flip design, and
any request flip (or why there is none). For each no-op task: task_id, rows touched, the twin
gold, D5. List every judgement call or doubt plainly. A doubt you state is better than a
hidden one.
