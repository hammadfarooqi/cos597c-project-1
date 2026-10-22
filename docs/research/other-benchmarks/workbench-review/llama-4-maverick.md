---
title: WorkBench Review — llama-4-maverick (3 Trials)
type: research
status: current
updated: 2026-10-22
summary: >-
  Hand review of all 106 WorkBench removal events (226 gate removals) for llama-4-maverick, seeds
  300–302. Read gate 81 TP. DB twin 9 TP / 84 WM / 6 FP. Request twin 3 TP / 43 WM / 0 FP.
  7 FNs and 1 possible FN. The extra no-op passes in seeds 301–302 are not provider drift: they
  are 23 crashes per trial whose error the resume step erased (inference.py writes error="").
note: >-
  After this review the erased errors were restored (findings-log §25). The 42 G1 events are
  no longer removals: those episodes are now failures. Corrected counts without them: read gate
  39 TP; DB twin 9 TP / 45 WM / 6 FP; request twin 3 TP / 19 WM / 0 FP (findings-log §26).
  Written by a reviewer agent from the rubric in
  docs/research/other-benchmarks/workbench-review-handoff.md. Not yet checked by a second
  labeller. The README index was not regenerated (the reviewer could edit only this file).
---

# WorkBench Review — llama-4-maverick

**Last updated:** 2026-10-22 · **By:** Hammad + Claude (reviewer agent)

## 1. Scope and method

- Model: `llama-4-maverick`. Seeds 300, 301, 302. Rubric:
  `docs/research/other-benchmarks/workbench-review-handoff.md` §3–§4. Calibration:
  `docs/research/new-models/review-handoff.md` §3, §4 and §6.
- Removal lists: `code/workbench-m2/data/trial_summary.json`. Evidence:
  `code/workbench-m2/data/episodes.jsonl`, the compact traces under `code/workbench-m2/runs/`,
  and the run logs under `code/workbench-m2/logs/`.
- Removal events (seed + task): **106**. Gate removals: **226**. Read gate (R) **81**, DB twin
  (D) **99**, request twin (Q) **46**.
- I read the original trace and every twin trace for each seed + task. For the 21 tasks of the
  crash group (§3, G1) I read the run log line and the twin error of every event, because those
  episodes have 0 steps.
- I also read every no-op pass that all gates kept (8 episodes), and every maverick episode of
  the 10 ungated tasks in all 3 seeds.
- The verdict follows Q1. Q2 only separates TP from WM. When Q1 = reasoned, the verdict is FP.
- No LLM or API calls were made. No git commands were run.

**Judgement rules that move counts.**

1. **A call typed as text on the twin is Q2 (d).** This follows the tau2 calibration (maverick
   task 28, "cancel lost as text" = TP, wrong mechanism). It applies when the agent did not get
   to the flipped fact because the tool channel failed, or when it saw the fact, decided to act,
   and typed the action as text.
2. **A twin read with a broken or invented argument is Q2 (a).** Examples:
   `query="from:yuki"` (never matches) and `assigned_to_email="fatima@example.com"` (invented).
   The agent cannot see the flip with these reads, so its no-op does not follow the fact. In
   multi_domain-081 and -085 the twin episode also ends on a call typed as text, so (d) is also
   present. **Uncertain:** if you count those as (d), D moves 6 TP → WM.
3. **An original pass that a lost or rejected write saved is not reasoned.** If the agent wrote
   "I will schedule …" or "I will still proceed to create the bar charts" and the call was typed
   as text or rejected, the pass is luck. This holds even when it read the right record.

## 2. Main finding: the extra no-op passes in seeds 301–302 are erased crashes

The brief says seeds 301 and 302 have about twice as many no-op passes (46, 45) as seed 300
(23), with no code change, so the cause is provider drift. **The evidence says otherwise.** The
cause is a resume step in our harness.

1. Only one run of maverick was resumed: `original_seed301/analytics` and
   `original_seed302/analytics`. Their `_meta.json` files say
   `"num_resumed_from_prior_run": 119` and `118`. No other maverick run was resumed.
2. `code/workbench/src/evals/inference.py`, `_load_existing_progress()`, keeps rows with a
   model-caused error (the comment says "they are failures under the upstream rule"). But it
   rebuilds each kept row with `"error": ""`. The error text is lost.
3. The run logs keep the error. Example, seed 301, analytics-030:
   `logs/original_seed301_llama-4-maverick.log` line 2285:
   `### Steps: 0 | Time: 4.6s | Error: Unterminated string starting at: line 1 column 40 (char 39)`.
   The CSV row and `episodes.jsonl` have `error: ""`, `calls: []`, `pass: true`.
4. In each of seeds 301 and 302, 56 analytics rows have an empty response and an empty error.
   In seed 300 the same rows carry their error. All 23 zero-step analytics no-op passes in
   seed 301, and all 23 in seed 302, have a logged error. In seed 300, 21 of the 23 tasks in
   each list crashed too, with the same kinds of error. analytics-115 and -117 were wrong
   writes in seed 300.

**Effect.** With the errors restored, maverick has 23 / 23 / 22 no-op passes, not 23 / 46 / 45.
"Original" drops from 127 → 104 (seed 301) and 125 → 102 (seed 302). Errors rise to about 245
and 240. The read gate removes 42 of the 46 erased crashes, so "Reads + twins" moves less:
85 → 83 and 82 → 80. The 4 that every gate kept are analytics-073 and -098 in seeds 301 and 302
(see §5).

Many of these crashes are on a **write**: `create_plot() got an unexpected keyword argument
'plot_type:'` (or `'plot_type='`, `'time_max '`) ends analytics-050, -083, -085, -093, -096,
-115, -117 and -118. On these no-op tasks maverick tried to plot. A crash discards the trace, so
I cannot tell whether a read ran before the plot call.

**What to fix (not done here; I could edit only this file):** in `_load_existing_progress()`, keep
`row.get("error", "")` for kept rows. Then rescore. The analytics runs need no new API calls.

## 3. Groups and the rule applied to each

| Group | Rule | Events (seed + task) | Gate removals |
|---|---|---|---|
| G1 erased crash | Original has 0 steps; run log shows a crash; resume erased it | 42 | R 42 · D 39 · Q 24 |
| G2 text plan | No call ran; the final answer is a plan with the first call typed as text | 30 | R 26 · D 26 · Q 15 |
| G3 broken read | Reads ran but could not show the fact (invented args, wrong window); a later step was lost or failed | 13 | R 13 · D 13 · Q 7 |
| G4 saved by a lost or rejected write | Read the fact (R kept it), then decided to act anyway or misread; the write was typed as text or rejected | 15 | D 15 |
| G5 reasoned | Read the fact and drew the right conclusion | 6 | D 6 |

**G1** (Q1 = no; R = TP; D/Q = WM (d), twin crashed too, except 302 analytics-118 D, a text call):
seed 301: analytics-030, 037, 050, 060, 062, 071, 072, 074, 076, 082, 083, 085, 092, 093, 094,
095, 096, 097, 111, 115, 117. Seed 302: analytics-030, 037, 050, 060, 062, 071, 072, 074, 076,
082, 083, 085, 092, 093, 094, 095, 096, 097, 111, 115, 118. All twin failures in this group are
errors of the same kind, for example the D twin of 301 analytics-037:
`total_visits_count() got an unexpected keyword argument 'time_max='`. The twin runs were not
resumed, so their errors are intact.

**G2** (Q1 = no; R = TP; D/Q = WM): calendar-058, -078, project_management-001, -005, -046,
-064, multi_domain-040, -056, -173 in all 3 seeds; calendar-066 in 301 and 302; calendar-073 in
302. Example, calendar-058 (all seeds), whole final answer starts:
"1. Find the next meeting with akira: [calendar_search_events(query="akira", …)] … 3. Delete
the event: [calendar_delete_event(event_id=event_id)]". project_management-046 also invents
data: "Let's assume the search result is: [{"task_id": "00000001"}, {"task_id": "00000002"}]",
then types two `update_task` calls to `fatima@example.com`. On the twins it does the same (d),
or crashes (d). Two twin failures are (b): 302 calendar-066 Q (it created the event, but with
`participant_email="akira@example.com"` at 09:00) and 300 calendar-078 Q (right deletes plus an
extra `delete_event(event_id="00000000")`; the lenient rule keeps this one, but R and D still
remove the task).

**G3** (Q1 = no; R = TP): email-010 (×3), calendar-062 (×3), calendar-066 (300),
multi_domain-081 (×3), multi_domain-085 (×3). D/Q: email-010, -081, -085 are (a) TP (rule 2);
calendar-062 and 300 calendar-066 are (d) WM.

**G4** (Q1 = no; R kept; D = WM): multi_domain-002 (300), multi_domain-004 (×3),
multi_domain-008 (×3), analytics-114 (×3), analytics-118 (301), multi_domain-134 (×3),
multi_domain-132 (302). Twin causes: (d) for 002, 004, 008, 114 (it read the flip, said it would
act, and typed the action as text) and for 301 analytics-118 (twin crash). (b) for 134 and 132
(`create_task` with an invented `@example.com` address, rejected by the tool).

**G5** (Q1 = yes; D = FP): calendar-068 (×3), analytics-113 (×3). See §6, pattern 5.

## 4. Counts (strict rule)

| Gate | Removals | TP | WM | FP |
|---|---|---|---|---|
| R (read gate) | 81 | **81** | 0 | 0 |
| D (DB twin) | 99 | **9** | 84 | 6 |
| Q (request twin) | 46 | **3** | 43 | 0 |

- Q1 = not reasoned in 100 of 106 events. Only calendar-068 and analytics-113 (3 seeds each)
  were reasoned, and only the DB twin removed them.
- D WM by cause: (d) 80 (G1 39 crashes, G2 26, G3 4, G4 11), (b) 4 (multi_domain-134 ×3, and
  multi_domain-132, which also has (a)). Q WM: (d) 41, (b) 2.
- **Lenient rule.** One gate removal is "right write + other difference": 300 calendar-078 Q.
  The lenient rule keeps that Q pass. It changes no total, because R and D also remove
  calendar-078 in seed 300.
- **If G1 is set aside** (those episodes are failures under the upstream rule once the error
  is restored): R 39 TP; D 9 TP / 45 WM / 6 FP; Q 3 TP / 19 WM / 0 FP.

## 5. False negatives (passes that every gate kept)

All 8 kept no-op passes of maverick are unreasoned or doubtful. None is a clean reasoned pass.

| Seed | Task | Why it is an FN | Why the gates kept it |
|---|---|---|---|
| 300 | calendar-073 | No call ran. Text only: `[calendar_search_events(query="owner_email = \"user@example.com\" and date = \"2023-12-05\"", …)]` | Ungated (9am rule). The request twin passed: on it the calls ran. |
| 301 | calendar-073 | Same text as seed 300 | Same; the request twin passed |
| 301 | analytics-073 | Erased crash: "Unterminated string starting at: line 1 column 40 (char 39)" | Ungated, no twin |
| 302 | analytics-073 | Erased crash, same error | Ungated, no twin |
| 301 | analytics-098 | Erased crash: "get_average_session_duration() got an unexpected keyword argument 'time_max='" | Ungated, no twin |
| 302 | analytics-098 | Erased crash, same error | Ungated, no twin |
| 301 | multi_domain-130 | Never read engaged users. "it is not more than the engaged users count (which is not available). However, we can still create a task as per the given instructions." Then `[project_management_create_task(… "chenwei@example.com" …)]` typed as text. A lost write saved it. | R kept it (it read session duration). The DB twin passed, because maverick creates the task whatever the data say. |
| 300 | analytics-077 | **Possible FN (low confidence).** It read 11-29 (20.5) and 11-22 (20.5), not Wednesday 11-29 against itself, and wrote "the average session duration on Thursday is not more than 3% higher than Wednesday". The label does not match what it read. The result holds for any data, because growth from a day to itself is 0%. | Ungated, no twin |

The 4 erased-crash FNs disappear when the error is restored (§2). That leaves 3 firm FNs and 1
possible FN.

## 6. Behaviour patterns

1. **Tool calls typed as text end the episode, and "no action" passes.** This is the main way
   maverick passes a no-op task (G2, 30 events). Example: seed 300 project_management-001, final
   answer: "First, let's search for tasks assigned to Aisha that are in progress.
   [company_directory_find_email_address(name=Aisha), project_management_search_tasks(…)]". No
   call ran. The retry in `_is_dropped_tool_call()` does not catch it, because the text is a
   plan with a call at the end, not a bare call.
2. **Crashes on invented argument names.** Keys such as `'time_max='`, `'plot_type:'`,
   `'time_max '` and broken JSON (`Unterminated string … column 40`). In seeds 301–302 the
   resume step turned 23 of these per trial into no-op passes (§2). Example: seed 301
   analytics-050 ends with `create_plot() got an unexpected keyword argument 'plot_type:'`.
3. **Saved by its own failed write.** The agent decides to act against the fact, and the write
   is lost as text or rejected. Example: analytics-114 (all seeds): "Since 34 is less than 186,
   we did not get more traffic from search engine than direct … However, since the task
   requires making bar charts if we got more traffic from search engine, I will still proceed to
   create the bar charts". Also multi_domain-134: `create_task(… "olga@example.com" …)` →
   "Assignee email not valid", then "we will not create a task. However … we need to find Olga's
   email address."
4. **Invented arguments in reads.** The read runs but cannot show the deciding record:
   `query="from:yuki"` (email-010; the twin adds a yuki email on 11-29 and the search still
   returns `[]`), `assigned_to_email="fatima@example.com"` (multi_domain-081), an inverted window
   (calendar-062), a window that starts one day late (300 calendar-066 misses the 11-23
   meeting). Then it invents IDs: `delete_email(email_id="12345678")`.
5. **When it does reason, the twin fails on the tool channel, not on the decision.** The only
   FPs. calendar-068 DB twin (all seeds): "Since there are no meetings with "raj" in the last 5
   days, I will now schedule a 30-minute meeting … [calendar_search_events(time_min="2023-12-01
   09:00:00", …)]", typed as text. analytics-113 DB twin: "Since 44 > 38, we will create bar
   charts for both. [analytics_create_plot(…)]", typed as text. These are stable in all 3
   trials (compare tau2 maverick task 49). The twin design is fine here: maverick believed the
   22-row patch of analytics-113. Note: its plot range (11-03..11-30) would also miss the gold
   start (11-02), so the twin would fail on (b) even if the call ran.
6. **It misreads an empty filtered result.** A CRM search with `last_contact_date_max` that
   returns `[]` means "contacted recently". Maverick reads it as "not contacted" (multi_domain-002:
   "Since Jessie Thomas was not contacted in the past fortnight, I will book a meeting") or as
   "the customer does not exist" (multi_domain-004: "we were unable to find Quinn Harris in the
   customer database"). In 004 the result is right and the reason is wrong.

## 7. Uncertainty

- **Rule 2 (broken read = (a)).** 6 D TPs (multi_domain-081, -085 × 3 seeds) and the 6
  email-010 TPs (D and Q) depend on it. Under a strict "(d) whenever the episode ends on a text
  call" rule, -081/-085 move to WM. email-010 stays (a): its twin ends with "there are no emails
  to delete" (301, 302) or a fake delete, not only a lost call.
- **multi_domain-008.** The CRM notes say the last call was 11-08, so "haven't spoken in the
  past fortnight" may be a fair reading. Q1 is still "no": maverick did not reach no-op; a lost
  write did.
- **multi_domain-132 (302).** Mixed (b) and (a). I counted WM. TP is also defensible.
- **The "due exactly 11-30" ambiguity** (project_management-064, multi_domain-081, -085) does
  not matter here. Maverick never read a valid record on those tasks.
- **Log parsing.** I matched log lines to tasks by the `### Task:` line. Three workers wrote to
  the same log, so a few lines interleave. The 46 G1 matches are exact (same task text, 0
  steps, error line follows). Two other mismatches I found were interleaving, not erased errors.
- **Twin-to-trace matching.** I matched traces to episodes by task text and order within each
  run file. All 2538 maverick episodes matched.

## 8. Every removal event

Gates: R = read gate, D = DB twin, Q = request twin. "s300" = seed 300. For G1 and G2 rows the
quote is from that seed. For other tasks that repeat over seeds, the quote is from the first seed
that passed; the other seeds do the same thing unless the cell says otherwise (I checked each).
Small number changes between seeds (for example "28" for "24" in 301 analytics-113) do not change
the verdict.

| # | Seed | Task | Gates | Q1: original reasoned? | Q2 and verdict per gate |
|---|---|---|---|---|---|
| 1 | 300 | analytics-113 | D | **Yes.** Read both sources 11-03..11-30: "referral … is 24 and from social media is 57. Since we did not get more traffic from referral than social media, we will not make bar charts". (s301/302 add a hypothetical text call: "If you want to create the plots anyway…".) | **D:** FP ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 2 | 300 | analytics-114 | D | No. "Since 34 is less than 186, we did not get more traffic … However, … I will still proceed to create the bar charts". The plot calls were typed as text. | **D:** WM ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 3 | 300 | calendar-058 | RD | No. No call ran. The final answer is a plan with a call typed as text: `calendar_search_events(query="akira", time_min="2023-11-30 00:00:00", time_max="2099-12-31 23:59:…`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |
| 4 | 300 | calendar-062 | RDQ | No. Inverted window `time_min="2023-12-01 00:00:00", time_max="2023-11-30 23:59:59"` → `[]`. Then: "Since you haven't met with Aisha in the last 9 days, I will schedule a 30-minute meeting called 'catch-up'". The next call was typed as text. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((d) twin ended on a call typed as text) |
| 5 | 300 | calendar-066 | RDQ | No. Window `2023-11-24`..`11-30` misses the 11-23 meeting. Then: "I will schedule a new meeting for the first available time slot, which is 9am. [calendar_create_event(...)]", typed as text. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text after it read the flip and decided to act)<br>**Q:** WM ((d) twin crashed: Unterminated string starting at: line 1 column 16 (char 15)) |
| 6 | 300 | calendar-068 | D | **Yes.** Read raj 11-25..11-30 → "monthly overview" on 11-29. "Since you have met with Raj in the last 5 days, there is no need to schedule a new meeting." | **D:** FP ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 7 | 300 | calendar-078 | RDQ | No. No call ran. The final answer is a plan with a call typed as text: `calendar_search_events(query=null, time_min="2023-12-05 15:00:00", time_max="2023-12-05 18:00:00")`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((b) right deletes plus an extra delete of invented id `00000000`; lenient rule keeps it) |
| 8 | 300 | email-010 | RDQ | No. `search_emails(query="from:yuki", date_min="2023-11-27", ...)` → `[]` (this query never matches; the DB twin returns `[]` with a yuki email present). Then `delete_email(email_id="12345678")` → "Email not found." The invented delete failed, so the state did not change. | **R:** TP<br>**D:** TP ((a) same broken search `query="from:yuki"` returns `[]`; deletes invented id `12345678`)<br>**Q:** TP ((a) same broken search `query="from:yuki"` returns `[]`; deletes invented id `12345678`) |
| 9 | 300 | multi_domain-002 | D | No. The revealing read returned `[]`, and the agent read it the wrong way: "Since Jessie Thomas was not contacted in the past fortnight, I will book a meeting". The next call was typed as text. | **D:** WM ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 10 | 300 | multi_domain-004 | D | No. The revealing read (`last_contact_date_max="2023-11-16"`) returned `[]`. The agent took this to mean "we were unable to find Quinn Harris in the customer database or company directory". Right result, wrong reason. | **D:** WM ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 11 | 300 | multi_domain-008 | D | No. It read `"last_contact_date": "2023-11-20"`, then said "Since we haven't spoken to Jordan Jones in the past fortnight, we need to book a meeting" and typed `calendar_create_event(...)` as text. (The CRM notes give 11-08, so booking may be defensible. The pass still came from a lost write.) | **D:** WM ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 12 | 300 | multi_domain-040 | RDQ | No. No call ran. The final answer is a plan with a call typed as text: `email_search_emails(query="from:yuki", date_min="2023-11-26", date_max="2023-11-30")`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((d) twin ended on a call typed as text) |
| 13 | 300 | multi_domain-056 | RDQ | No. No call ran. The final answer is a plan with a call typed as text: `company_directory_find_email_address(name=Yuki)`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((d) twin ended on a call typed as text) |
| 14 | 300 | multi_domain-081 | RD | No. `search_tasks(assigned_to_email="fatima@example.com", due_date="2023-11-30")` → `[]` (invented address). s300 then typed `calendar_create_event(... "2023-12-01 09:00:00" ...)` as text. s301/302 end on a text search. | **R:** TP<br>**D:** TP ((a) same reads with invented `@example.com` address return `[]`; ends on a text-form call (d) too) |
| 15 | 300 | multi_domain-085 | RD | No. `search_tasks(assigned_to_email="dmitri@example.com", due_date="2023-11-30")` → `[]` (invented address). Ends on text `[company_directory_find_email_address(name="Dmitri")]`. | **R:** TP<br>**D:** TP ((a) same reads with invented `@example.com` address return `[]`; ends on a text-form call (d) too) |
| 16 | 300 | multi_domain-134 | D | No. It called `create_task(... assigned_to_email="olga@example.com" ...)` and the tool rejected it ("Assignee email not valid"). Final: "we will not create a task. However, to complete the task as per the original request, we need to find Olga's email address." | **D:** WM ((b) acted, but `create_task` used invented `olga@example.com` (rejected)) |
| 17 | 300 | multi_domain-173 | Q | No. No call ran. The final answer is a plan with a call typed as text: `analytics_total_visits_count(time_min=2023-11-29, time_max=2023-11-29)`. | **Q:** WM ((d) twin ended on a call typed as text) |
| 18 | 300 | project_management-001 | RD | No. No call ran. The final answer is a plan with a call typed as text: `company_directory_find_email_address(name=Aisha)`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |
| 19 | 300 | project_management-005 | RD | No. No call ran. The final answer is a plan with a call typed as text: `company_directory_find_email_address(name="Kofi")`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |
| 20 | 300 | project_management-046 | RD | No. No call ran. The final answer is a plan with a call typed as text: `project_management_update_task(task_id="00000002", field="assigned_to_email", new_value="fatima@e…`. It also wrote "Let's assume the search result is: [{\"task_id\": \"00000001\"}…]". | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |
| 21 | 300 | project_management-064 | RD | No. No call ran. The final answer is a plan with a call typed as text: `project_management_search_tasks(assigned_to_email=carlos@example.com)`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |
| 22 | 301 | analytics-030 | RDQ | No. The episode crashed: "Unterminated string starting at: line 1 column 40 (char 39)" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: Unterminated string starting at: line 1 column 40 (char 39))<br>**Q:** WM ((d) twin crashed: Unterminated string starting at: line 1 column 40 (char 39)) |
| 23 | 301 | analytics-037 | RDQ | No. The episode crashed: "total_visits_count() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: total_visits_count() got an unexpected keyword argument 'tim)<br>**Q:** WM ((d) twin crashed: total_visits_count() got an unexpected keyword argument 'tim) |
| 24 | 301 | analytics-050 | RDQ | No. The episode crashed: "create_plot() got an unexpected keyword argument 'plot_type:'" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type )<br>**Q:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type:) |
| 25 | 301 | analytics-060 | RDQ | No. The episode crashed: "Unterminated string starting at: line 1 column 40 (char 39)" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: Unterminated string starting at: line 1 column 40 (char 39))<br>**Q:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti) |
| 26 | 301 | analytics-062 | RDQ | No. The episode crashed: "create_plot() got an unexpected keyword argument 'plot_type='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti)<br>**Q:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti) |
| 27 | 301 | analytics-071 | RD | No. The episode crashed: "get_average_session_duration() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: get_average_session_duration() got an unexpected keyword arg) |
| 28 | 301 | analytics-072 | RDQ | No. The episode crashed: "engaged_users_count() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti)<br>**Q:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti) |
| 29 | 301 | analytics-074 | RDQ | No. The episode crashed: "engaged_users_count() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti)<br>**Q:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti) |
| 30 | 301 | analytics-076 | RDQ | No. The episode crashed: "engaged_users_count() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti)<br>**Q:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti) |
| 31 | 301 | analytics-082 | RDQ | No. The episode crashed: "total_visits_count() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: total_visits_count() got an unexpected keyword argument 'tim)<br>**Q:** WM ((d) twin crashed: total_visits_count() got an unexpected keyword argument 'tim) |
| 32 | 301 | analytics-083 | RDQ | No. The episode crashed: "create_plot() got an unexpected keyword argument 'time_max '" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type:)<br>**Q:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type:) |
| 33 | 301 | analytics-085 | RDQ | No. The episode crashed: "create_plot() got an unexpected keyword argument 'plot_type='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type=)<br>**Q:** WM ((d) twin crashed: get_average_session_duration() got an unexpected keyword arg) |
| 34 | 301 | analytics-092 | RD | No. The episode crashed: "get_average_session_duration() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: get_average_session_duration() got an unexpected keyword arg) |
| 35 | 301 | analytics-093 | RD | No. The episode crashed: "create_plot() got an unexpected keyword argument 'plot_type:'" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type:) |
| 36 | 301 | analytics-094 | RD | No. The episode crashed: "get_average_session_duration() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: get_average_session_duration() got an unexpected keyword arg) |
| 37 | 301 | analytics-095 | RD | No. The episode crashed: "get_average_session_duration() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: get_average_session_duration() got an unexpected keyword arg) |
| 38 | 301 | analytics-096 | R | No. The episode crashed: "create_plot() got an unexpected keyword argument 'plot_type:'" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP |
| 39 | 301 | analytics-097 | RDQ | No. The episode crashed: "engaged_users_count() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti)<br>**Q:** WM ((d) twin crashed: get_average_session_duration() got an unexpected keyword arg) |
| 40 | 301 | analytics-111 | RD | No. The episode crashed: "Unterminated string starting at: line 1 column 72 (char 71)" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: Unterminated string starting at: line 1 column 72 (char 71)) |
| 41 | 301 | analytics-113 | D | **Yes.** Read both sources 11-03..11-30: "referral … is 24 and from social media is 57. Since we did not get more traffic from referral than social media, we will not make bar charts". (s301/302 add a hypothetical text call: "If you want to create the plots anyway…".) | **D:** FP ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 42 | 301 | analytics-114 | D | No. "Since 34 is less than 186, we did not get more traffic … However, … I will still proceed to create the bar charts". The plot calls were typed as text. | **D:** WM ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 43 | 301 | analytics-115 | RD | No. The episode crashed: "create_plot() got an unexpected keyword argument 'time_max '" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type:) |
| 44 | 301 | analytics-117 | RD | No. The episode crashed: "create_plot() got an unexpected keyword argument 'plot_type '" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type ) |
| 45 | 301 | analytics-118 | D | No. "Since 30 is not more than 43, the condition is not met. However, I will still create the bar charts as per your request." The plot calls were typed as text. | **D:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type ) |
| 46 | 301 | calendar-058 | RD | No. No call ran. The final answer is a plan with a call typed as text: `calendar_search_events(query="akira", time_min="2023-11-30 00:00:00", time_max="2099-12-31 23:59:…`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |
| 47 | 301 | calendar-062 | RDQ | No. Inverted window `time_min="2023-12-01 00:00:00", time_max="2023-11-30 23:59:59"` → `[]`. Then: "Since you haven't met with Aisha in the last 9 days, I will schedule a 30-minute meeting called 'catch-up'". The next call was typed as text. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((d) twin ended on a call typed as text) |
| 48 | 301 | calendar-066 | RDQ | No. No call ran. The final answer is a plan with a call typed as text: `calendar_search_events(query='akira', time_min='2023-11-23 00:00:00', time_max='2023-11-30 23:59:…`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((d) twin ended on a call typed as text) |
| 49 | 301 | calendar-068 | D | **Yes.** Read raj 11-25..11-30 → "monthly overview" on 11-29. "Since you have met with Raj in the last 5 days, there is no need to schedule a new meeting." | **D:** FP ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 50 | 301 | calendar-078 | RDQ | No. No call ran. The final answer is a plan with a call typed as text: `calendar_search_events(query="", time_min="2023-12-05 15:00:00", time_max="2023-12-05 18:00:00")`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((d) twin ended on a call typed as text) |
| 51 | 301 | email-010 | RDQ | No. `search_emails(query="from:yuki", date_min="2023-11-27", ...)` → `[]` (this query never matches; the DB twin returns `[]` with a yuki email present). Then `delete_email(email_id="12345678")` → "Email not found." The invented delete failed, so the state did not change. | **R:** TP<br>**D:** TP ((a) same broken search `query="from:yuki"` returns `[]`; deletes invented id `12345678`)<br>**Q:** TP ((a) same broken search `query="from:yuki"` returns `[]`; deletes invented id `12345678`) |
| 52 | 301 | multi_domain-004 | D | No. The revealing read (`last_contact_date_max="2023-11-16"`) returned `[]`. The agent took this to mean "we were unable to find Quinn Harris in the customer database or company directory". Right result, wrong reason. | **D:** WM ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 53 | 301 | multi_domain-008 | D | No. It read `"last_contact_date": "2023-11-20"`, then said "Since we haven't spoken to Jordan Jones in the past fortnight, we need to book a meeting" and typed `calendar_create_event(...)` as text. (The CRM notes give 11-08, so booking may be defensible. The pass still came from a lost write.) | **D:** WM ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 54 | 301 | multi_domain-040 | RDQ | No. No call ran. The final answer is a plan with a call typed as text: `email_search_emails(query="from:yuki", date_min="2023-11-26", date_max="2023-11-30")`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((d) twin ended on a call typed as text) |
| 55 | 301 | multi_domain-056 | RDQ | No. No call ran. The final answer is a plan with a call typed as text: `company_directory_find_email_address(name="Yuki")`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((d) twin ended on a call typed as text) |
| 56 | 301 | multi_domain-081 | RD | No. `search_tasks(assigned_to_email="fatima@example.com", due_date="2023-11-30")` → `[]` (invented address). s300 then typed `calendar_create_event(... "2023-12-01 09:00:00" ...)` as text. s301/302 end on a text search. | **R:** TP<br>**D:** TP ((a) same reads with invented `@example.com` address return `[]`; ends on a text-form call (d) too) |
| 57 | 301 | multi_domain-085 | RD | No. `search_tasks(assigned_to_email="dmitri@example.com", due_date="2023-11-30")` → `[]` (invented address). Ends on text `[company_directory_find_email_address(name="Dmitri")]`. | **R:** TP<br>**D:** TP ((a) same reads with invented `@example.com` address return `[]`; ends on a text-form call (d) too) |
| 58 | 301 | multi_domain-134 | D | No. It called `create_task(... assigned_to_email="olga@example.com" ...)` and the tool rejected it ("Assignee email not valid"). Final: "we will not create a task. However, to complete the task as per the original request, we need to find Olga's email address." | **D:** WM ((b) acted, but `create_task` used invented `olga@example.com` (rejected)) |
| 59 | 301 | multi_domain-173 | Q | No. No call ran. The final answer is a plan with a call typed as text: `analytics_total_visits_count(time_min=2023-11-29, time_max=2023-11-29)`. | **Q:** WM ((d) twin ended on a call typed as text) |
| 60 | 301 | project_management-001 | RD | No. No call ran. The final answer is a plan with a call typed as text: `company_directory_find_email_address(name=Aisha)`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |
| 61 | 301 | project_management-005 | RD | No. No call ran. The final answer is a plan with a call typed as text: `company_directory_find_email_address(name="Kofi")`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |
| 62 | 301 | project_management-046 | RD | No. No call ran. The final answer is a plan with a call typed as text: `project_management_update_task(task_id="00000002", field="assigned_to_email", new_value="fatima@e…`. It also wrote "Let's assume the search result is: [{\"task_id\": \"00000001\"}…]". | **R:** TP<br>**D:** WM ((d) twin crashed: update_task() got an unexpected keyword argument 'field_name) |
| 63 | 301 | project_management-064 | RD | No. No call ran. The final answer is a plan with a call typed as text: `project_management_search_tasks(assigned_to_email="carlos@example.com")`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |
| 64 | 302 | analytics-030 | RDQ | No. The episode crashed: "Unterminated string starting at: line 1 column 40 (char 39)" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: Unterminated string starting at: line 1 column 40 (char 39))<br>**Q:** WM ((d) twin crashed: Unterminated string starting at: line 1 column 40 (char 39)) |
| 65 | 302 | analytics-037 | RDQ | No. The episode crashed: "total_visits_count() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: total_visits_count() got an unexpected keyword argument 'tim)<br>**Q:** WM ((d) twin crashed: total_visits_count() got an unexpected keyword argument 'tim) |
| 66 | 302 | analytics-050 | RDQ | No. The episode crashed: "create_plot() got an unexpected keyword argument 'plot_type:'" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type )<br>**Q:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type:) |
| 67 | 302 | analytics-060 | RDQ | No. The episode crashed: "Unterminated string starting at: line 1 column 40 (char 39)" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: Unterminated string starting at: line 1 column 40 (char 39))<br>**Q:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti) |
| 68 | 302 | analytics-062 | RDQ | No. The episode crashed: "engaged_users_count() got an unexpected keyword argument 'time_max:'" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti)<br>**Q:** WM ((d) twin crashed: Unterminated string starting at: line 1 column 40 (char 39)) |
| 69 | 302 | analytics-071 | RD | No. The episode crashed: "get_average_session_duration() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: get_average_session_duration() got an unexpected keyword arg) |
| 70 | 302 | analytics-072 | RQ | No. The episode crashed: "engaged_users_count() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**Q:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti) |
| 71 | 302 | analytics-074 | RDQ | No. The episode crashed: "engaged_users_count() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti)<br>**Q:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti) |
| 72 | 302 | analytics-076 | RDQ | No. The episode crashed: "engaged_users_count() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti)<br>**Q:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti) |
| 73 | 302 | analytics-082 | RDQ | No. The episode crashed: "total_visits_count() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: total_visits_count() got an unexpected keyword argument 'tim)<br>**Q:** WM ((d) twin crashed: total_visits_count() got an unexpected keyword argument 'tim) |
| 74 | 302 | analytics-083 | RDQ | No. The episode crashed: "create_plot() got an unexpected keyword argument 'time_max '" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type:)<br>**Q:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type:) |
| 75 | 302 | analytics-085 | RDQ | No. The episode crashed: "create_plot() got an unexpected keyword argument 'plot_type='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type=)<br>**Q:** WM ((d) twin crashed: get_average_session_duration() got an unexpected keyword arg) |
| 76 | 302 | analytics-092 | RD | No. The episode crashed: "get_average_session_duration() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: get_average_session_duration() got an unexpected keyword arg) |
| 77 | 302 | analytics-093 | RD | No. The episode crashed: "create_plot() got an unexpected keyword argument 'plot_type:'" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type:) |
| 78 | 302 | analytics-094 | RD | No. The episode crashed: "get_average_session_duration() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: get_average_session_duration() got an unexpected keyword arg) |
| 79 | 302 | analytics-095 | RD | No. The episode crashed: "get_average_session_duration() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: get_average_session_duration() got an unexpected keyword arg) |
| 80 | 302 | analytics-096 | R | No. The episode crashed: "create_plot() got an unexpected keyword argument 'plot_type:'" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP |
| 81 | 302 | analytics-097 | RDQ | No. The episode crashed: "engaged_users_count() got an unexpected keyword argument 'time_max='" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: engaged_users_count() got an unexpected keyword argument 'ti)<br>**Q:** WM ((d) twin crashed: get_average_session_duration() got an unexpected keyword arg) |
| 82 | 302 | analytics-111 | RD | No. The episode crashed: "Unterminated string starting at: line 1 column 72 (char 71)" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: Unterminated string starting at: line 1 column 72 (char 71)) |
| 83 | 302 | analytics-113 | D | **Yes.** Read both sources 11-03..11-30: "referral … is 24 and from social media is 57. Since we did not get more traffic from referral than social media, we will not make bar charts". (s301/302 add a hypothetical text call: "If you want to create the plots anyway…".) | **D:** FP ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 84 | 302 | analytics-114 | D | No. "Since 34 is less than 186, we did not get more traffic … However, … I will still proceed to create the bar charts". The plot calls were typed as text. | **D:** WM ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 85 | 302 | analytics-115 | RD | No. The episode crashed: "create_plot() got an unexpected keyword argument 'time_max '" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin crashed: create_plot() got an unexpected keyword argument 'plot_type:) |
| 86 | 302 | analytics-118 | RD | No. The episode crashed: "create_plot() got an unexpected keyword argument 'plot_type:'" (run log). The resume step erased the error; 0 steps were kept. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |
| 87 | 302 | calendar-058 | RD | No. No call ran. The final answer is a plan with a call typed as text: `calendar_search_events(query="akira", time_min="2023-11-30 00:00:00", time_max="2099-12-31 23:59:…`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |
| 88 | 302 | calendar-062 | RDQ | No. Inverted window `time_min="2023-12-01 00:00:00", time_max="2023-11-30 23:59:59"` → `[]`. Then: "Since you haven't met with Aisha in the last 9 days, I will schedule a 30-minute meeting called 'catch-up'". The next call was typed as text. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((d) twin ended on a call typed as text) |
| 89 | 302 | calendar-066 | RDQ | No. No call ran. The final answer is a plan with a call typed as text: `calendar_search_events(query=akira, time_min=2023-11-23 00:00:00, time_max=2023-11-30 23:59:59)`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((b) acted, but invented `akira@example.com` and slot 09:00 (gold 13:00)) |
| 90 | 302 | calendar-068 | D | **Yes.** Read raj 11-25..11-30 → "monthly overview" on 11-29. "Since you have met with Raj in the last 5 days, there is no need to schedule a new meeting." | **D:** FP ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 91 | 302 | calendar-073 | Q | No. No call ran. The final answer is a plan with a call typed as text: `calendar_search_events(query="owner_email = \"user@example.com\" and date = \"2023-12-05\"", time…`. | **Q:** WM ((d) twin ended on a call typed as text) |
| 92 | 302 | calendar-078 | RDQ | No. No call ran. The final answer is a plan with a call typed as text: `calendar_search_events(query=null, time_min="2023-12-05 15:00:00", time_max="2023-12-05 18:00:00")`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((d) twin ended on a call typed as text) |
| 93 | 302 | email-010 | RDQ | No. `search_emails(query="from:yuki", date_min="2023-11-27", ...)` → `[]` (this query never matches; the DB twin returns `[]` with a yuki email present). Then `delete_email(email_id="12345678")` → "Email not found." The invented delete failed, so the state did not change. | **R:** TP<br>**D:** TP ((a) same broken search `query="from:yuki"` returns `[]`; deletes invented id `12345678`)<br>**Q:** TP ((a) same broken search `query="from:yuki"` returns `[]`; deletes invented id `12345678`) |
| 94 | 302 | multi_domain-004 | D | No. The revealing read (`last_contact_date_max="2023-11-16"`) returned `[]`. The agent took this to mean "we were unable to find Quinn Harris in the customer database or company directory". Right result, wrong reason. | **D:** WM ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 95 | 302 | multi_domain-008 | D | No. It read `"last_contact_date": "2023-11-20"`, then said "Since we haven't spoken to Jordan Jones in the past fortnight, we need to book a meeting" and typed `calendar_create_event(...)` as text. (The CRM notes give 11-08, so booking may be defensible. The pass still came from a lost write.) | **D:** WM ((d) twin ended on a call typed as text after it read the flip and decided to act) |
| 96 | 302 | multi_domain-040 | RDQ | No. No call ran. The final answer is a plan with a call typed as text: `email_search_emails(query="from:yuki", date_min="2023-11-26", date_max="2023-11-30")`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((d) twin ended on a call typed as text) |
| 97 | 302 | multi_domain-056 | RDQ | No. No call ran. The final answer is a plan with a call typed as text: `calendar_search_events(query="Yuki")`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text)<br>**Q:** WM ((d) twin ended on a call typed as text) |
| 98 | 302 | multi_domain-081 | RD | No. `search_tasks(assigned_to_email="fatima@example.com", due_date="2023-11-30")` → `[]` (invented address). s300 then typed `calendar_create_event(... "2023-12-01 09:00:00" ...)` as text. s301/302 end on a text search. | **R:** TP<br>**D:** TP ((a) same reads with invented `@example.com` address return `[]`; ends on a text-form call (d) too) |
| 99 | 302 | multi_domain-085 | RD | No. `search_tasks(assigned_to_email="dmitri@example.com", due_date="2023-11-30")` → `[]` (invented address). Ends on text `[company_directory_find_email_address(name="Dmitri")]`. | **R:** TP<br>**D:** TP ((a) same reads with invented `@example.com` address return `[]`; ends on a text-form call (d) too) |
| 100 | 302 | multi_domain-132 | D | No. It called `create_task(... "amir@example.com" ...)` (rejected) before it read total visits. Then it compared a growth % with a raw count and wrote "Let's create a task for amir@example.com". | **D:** WM ((b) `create_task` with invented `amir@example.com` (rejected); then miscalculated visits growth (383%) and said "we will not create a task" (a) too) |
| 101 | 302 | multi_domain-134 | D | No. It called `create_task(... assigned_to_email="olga@example.com" ...)` and the tool rejected it ("Assignee email not valid"). Final: "we will not create a task. However, to complete the task as per the original request, we need to find Olga's email address." | **D:** WM ((b) acted, but `create_task` used invented `olga@example.com` (rejected)) |
| 102 | 302 | multi_domain-173 | Q | No. No call ran. The final answer is a plan with a call typed as text: `analytics_total_visits_count(time_min=2023-11-29, time_max=2023-11-29)`. | **Q:** WM ((d) twin ended on a call typed as text) |
| 103 | 302 | project_management-001 | RD | No. No call ran. The final answer is a plan with a call typed as text: `company_directory_find_email_address(name=Aisha)`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |
| 104 | 302 | project_management-005 | RD | No. No call ran. The final answer is a plan with a call typed as text: `company_directory_find_email_address(name="Kofi")`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |
| 105 | 302 | project_management-046 | RD | No. No call ran. The final answer is a plan with a call typed as text: `project_management_update_task(task_id="00000002", field="assigned_to_email", new_value="fatima@e…`. It also wrote "Let's assume the search result is: [{\"task_id\": \"00000001\"}…]". | **R:** TP<br>**D:** WM ((d) twin crashed: update_task() got an unexpected keyword argument 'field_name) |
| 106 | 302 | project_management-064 | RD | No. No call ran. The final answer is a plan with a call typed as text: `project_management_search_tasks(assigned_to_email=carlos@example.com)`. | **R:** TP<br>**D:** WM ((d) twin ended on a call typed as text) |

## 9. Data used

- `code/workbench-m2/data/trial_summary.json`, `code/workbench-m2/data/episodes.jsonl`
- `code/workbench-m2/runs/{original,dbtwin,requesttwin}_seed30{0,1,2}/**/llama-4-maverick_all_*_traces.compact.json.gz` and `*_meta.json`
- `code/workbench-m2/logs/original_seed30{0,1,2}_llama-4-maverick.log`
- `code/workbench-m2/data/twins_db_tasks_and_outcomes.csv`, `code/workbench-m2/data/twins_request_tasks_and_outcomes.csv` (`why` column)
- `code/workbench/src/evals/inference.py` (`_load_existing_progress`), `code/workbench/src/evals/agent.py` (`_is_dropped_tool_call`)
