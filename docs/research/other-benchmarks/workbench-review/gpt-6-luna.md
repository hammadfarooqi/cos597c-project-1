---
title: WorkBench Review — gpt-6-luna (3 Trials)
type: research
status: current
updated: 2026-10-22
summary: >-
  Hand review of all 44 WorkBench removal events for gpt-6-luna (seeds 300–302): read gate 0,
  DB twin 25, request twin 19. 0 TP; 3 WM (request twin); 41 FP. Almost every removed luna
  no-op pass was reasoned. The twins fail on template strictness (the "catch-up" name, first
  free slot, plot ranges, "for us"). 2 FNs, both "since Wednesday" growth tasks.
note: >-
  Written by a reviewer agent from the rubric in
  docs/research/other-benchmarks/workbench-review-handoff.md. Not yet blind-checked by a second
  labeller. The README index was not regenerated (the reviewer could edit only this file).
---

# WorkBench Review — gpt-6-luna

**Last updated:** 2026-10-22 · **By:** Hammad + Claude (reviewer agent)

## 1. Scope and method

- Model: `gpt-6-luna`. Seeds 300, 301, 302. Rubric:
  `docs/research/other-benchmarks/workbench-review-handoff.md` §3–§4. Calibration:
  `docs/research/new-models/review-handoff.md` §3–§4.
- Removal lists: `code/workbench-m2/data/trial_summary.json`. Evidence:
  `code/workbench-m2/data/episodes.jsonl` and the compact traces under `code/workbench-m2/runs/`.
- Removal events: **44**. Read gate (R): **0**. DB twin (D): **25** (13 tasks). Request twin
  (Q): **19** (11 tasks).
- I read every original and every twin trace for each event. I also read the final answer of
  every no-op original in all 3 seeds (122 no-op tasks), to find false negatives.
- The verdict follows Q1 (was the original no-op reasoned?). Q2 (why did the gate fail?) only
  separates TP from WM. When Q1 = reasoned, the verdict is FP, whatever Q2 is.
- No LLM or API calls were made. No git commands were run.

**Two judgement rules I applied.** State them, because they move counts.

1. **Abstention on missing data counts as reasoned (medium confidence).** On "growth since
   Wednesday" tasks, luna often says "no Thursday data, so I can't tell" and does nothing. The
   upstream reason for no-op is that growth from a day to itself is 0%. Luna never states 0%, but
   it reads the right window and declines *because* no later data exists. I treat this as a
   reasoned decision, not luck. A stricter reader would call it unreasoned. §5 gives the counts
   under that stricter rule.
2. **A wrong substitute window is not reasoned.** When luna replaces "since Wednesday" with
   "Tuesday to Wednesday" and decides from that, Q1 = no.

## 2. Every removal event

Seeds in one row have **identical call lists** unless the row says "distinct calls". Every
event is counted on its own in §3. "Lenient keeps" means the cause is "right write + other
difference".

### 2.1 DB twin (D) — 25 events

| Seed(s) | Task | Q1: original reasoned? (evidence) | Q2: cause of the twin failure | Verdict |
|---|---|---|---|---|
| 300, 301, 302 (distinct calls) | calendar-060 | **Yes.** Read `search_events(query="Sofia", 2023-11-27 … 2023-11-30)`. 300: "you met with Sofia on November 27, within the last three days." | (c) Created `event_name="Catch up with Sofia"` (302: "Catch-up with Sofia") at 13:00. Gold name is "catch-up". Slot and participant are right. | FP ×3 (high) |
| 301, 302 (distinct calls) | calendar-062 | **Yes.** "You met with Aisha on November 24, within the last 9 days." | (b) Named it "catch-up" correctly, but wrong slot: 301 `14:00`, 302 `11:00` (11:00 overlaps the 10:00–12:00 event). Gold 13:00. | FP ×2 (high) |
| 300, 301, 302 (distinct calls) | calendar-065 | **Yes.** 301: "two meetings with Sofia on November 27 … The event on November 30 is later today, not a past meeting." | (c) "Catch up with Sofia" at 13:00; gold "catch-up". | FP ×3 (high) |
| 300, 301, 302 (distinct calls) | calendar-068 | **Yes.** 301: "a 60-minute meeting with Raj ('monthly overview') on November 29 … within the last five days." | (c) "Catch up with Raj". 301 also booked 14:00, then `update_event(… "2023-12-01 13:00:00")`. | FP ×3 (high) |
| 301 | calendar-078 | **Yes.** Searched with `query=""` over 15:00–23:59; "no meetings scheduled to start after 3:00 p.m. … Your Project Initiation Meeting ends at 3:00 p.m. exactly." | (b) On the twin it searched `query="meeting"`, which hides the new "sync up" event. It never saw the flipped record. Seeds 300 and 302 used `query=""` and passed. | FP (high) |
| 300 | analytics-052 | **Yes.** Read 11-23..11-30: max 8. "Engaged users never exceeded 11 during the last week." | (b)/(c) Plotted `time_min="2023-11-28"` (the day it exceeded 11), reading "since then" as "since the spike". Gold starts 11-23. | FP (high) |
| 300, 301 (distinct calls) | analytics-111 | **Yes.** "referral brought **22 visits**, compared with **128 from direct**." (Sum checked: correct.) | (a) on the twin, with a reasoned original. 300: "No. … referral brought **81** … direct **69**? Actually, referral is higher … I'll make bar charts for both." It then ended with no call. 301: "referral was higher. Since you asked for charts only if referral was higher, I haven't made any." Luna believed the 59-row patch; it failed to act on its own numbers. | FP ×2 (medium-high) |
| 301, 302 (identical calls) | analytics-113 | **Yes.** 302: "referral had **29 visits**, while social media had **65**." | (b) Plots start `2023-11-03`; gold 11-02 ("last 4 weeks" start). Both seeds plotted the right series. | FP ×2 (high) |
| 302 | analytics-117 | **Yes.** "social media brought **87 visits**, compared with **42** from search engines." | (b) Plots start `2023-10-27`; gold 10-26. | FP (high) |
| 301, 302 (distinct calls) | multi_domain-002 | **Yes.** All seeds: "Jessie Thomas was contacted on November 29, within the past fortnight." | (b) Booked 09:00. It checked only Raj's calendar (`search_events(query="raj.patel@atlas.com", …)`), not the user's. Gold 13:00. | FP ×2 (high) |
| 300, 302 (identical calls) | multi_domain-008 | **Yes, on the field the gold uses.** "Jordan Jones was last contacted on November 20." The CRM notes disagree (known issue); luna used `last_contact_date`, as the gold does. | (b) Booked 09:00 after `search_events(query="nadia.moreau@atlas.com", …)` returned `[]`. Gold 13:00. | FP ×2 (medium; Q1 ambiguous upstream) |
| 301 | multi_domain-087 | **Yes, under the upstream rule.** "He has two tasks due today, November 30, but they aren't overdue yet." (A known ambiguous task; luna states the rule.) | (b) Booked 12:00 (overlaps "project checkpoint" 12:00–13:00). Gold 13:00. | FP (medium) |
| 300, 302 (distinct calls) | multi_domain-172 | **Yes.** "Average session duration **decreased 18%** … Engaged users increased **150%**." | (c) "For us" template: `create_event(…, participant_email="", …)` → "Participant email not provided." The task was created correctly. | FP ×2 (high) |

### 2.2 Request twin (Q) — 19 events

| Seed(s) | Task | Q1: original reasoned? (evidence) | Q2: cause of the twin failure | Verdict |
|---|---|---|---|---|
| 300, 301, 302 (distinct calls) | calendar-060 | **Yes** (see D). | (c) "Catch up with Sofia" at 13:00; gold "catch-up". | FP ×3 (high) |
| 300, 301, 302 | calendar-065 | **Yes** (see D). | (c) Same episodes as the calendar-060 row: the shared twin `calendar-060_req` removes both originals. | FP ×3 (high) |
| 301, 302 (identical calls) | analytics-054 | **Yes.** All seeds: "Total visits were at least 6 on every … day from Nov 23–29." | (b) Read and plotted from `2023-11-24`; gold 11-23. Seed 300 read from 11-23 and passed. | FP ×2 (high) |
| 300, 301 (distinct calls) | analytics-057 | **Yes.** "stayed above 2 seconds on every reported day from November 16–29." | (b) Right plot plus extra plots (`2023-11-17`, and in 301 also `2023-11-16..11-29`). | FP ×2 (high); **lenient keeps** |
| 301 | analytics-068 | **Yes, with a broader reading.** "October 21 were 11 … No later date … exceeded it; the maximum was 10." It tests any day, not the end day; both readings give no-op. | (b) Plot starts `2023-10-22`; gold 10-21. | FP (medium-high) |
| 300 | analytics-076 | **Yes.** "Engaged users increased from **2 on Sunday, Nov 26** to **5 on Wednesday, Nov 29**." It does not treat the empty 11-30 bucket as 0. | (b) Right plot plus an extra `11-26..11-30` plot. | FP (high); **lenient keeps** |
| 302 | multi_domain-110 | **Yes.** "the highest was exactly 21 on October 24." | (b)/(c) `due_date="2023-12-01"`; gold 12-08. "Next Friday" on a Thursday is ambiguous. Seeds 300/301 used 12-08. | FP (high) |
| 300 | multi_domain-115 | **Yes.** "Engaged users peaked at 11 on October 21, which is not more than 11." | (b)/(c) `due_date="2023-12-01"`; gold 12-08. | FP (high) |
| 302 | multi_domain-133 | **Yes.** "engaged users went from 8 to 5: **−37.5%** … Total visits … **−28.6%**." | (a) on the twin, with a reasoned original: "a **150% increase**. Total visits over Nov 26–29 were **41**, so the growth percentage was not greater than total visits." It compared a percent with a raw count. | FP (medium-high) |
| 300 (distinct calls) | multi_domain-170 | **No.** Before it decided, it called `calendar.create_event(event_name="Discuss engaged users", participant_email="", event_start="2023-12-01 11:00:00", …)`. The tool rejected it: "Participant email not provided." Only then: "I couldn't determine the growth." The tool error saved the no-op. | (c) "For us": task created right; meeting `participant_email=""` rejected. | **WM** (high on Q1) |
| 302 (distinct calls) | multi_domain-170 | **No.** Same: `create_event(… participant_email="", event_start="2023-12-01 11:00:00" …)` rejected. Final: "I couldn't schedule 'Discuss engaged users' because the calendar requires a participant email." It meant to book the meeting with the condition unresolved. | (c) Same "for us" failure. | **WM** (high on Q1) |
| 300 | multi_domain-175 | **Reasoned by abstention** (rule 1). "Since I can't verify the condition, I didn't create the task or schedule the meeting." | (c)/(b) Task right. Meeting: first `participant_email=""` (rejected), then an invented `participant_email="sam@example.com"`. | FP (low-medium). Under the strict rule: WM. |
| 301 | multi_domain-175 | **No.** Wrong window: "From Tuesday to Wednesday, total visits fell … (**−47.4%**), while engaged users fell … (**−37.5%**). Total visits didn't grow more … so I didn't create the task." | (c) "For us": `participant_email=""` rejected. | **WM** (medium) |

## 3. Counts (strict rule)

| Gate | Events | TP | WM | FP | FP that the lenient rule keeps |
|---|---|---|---|---|---|
| Read gate (R) | 0 | 0 | 0 | 0 | — |
| DB twin (D) | 25 | 0 | 0 | 25 | 0 |
| Request twin (Q) | 19 | 0 | 3 | 16 | 3 (analytics-057 ×2, analytics-076) |
| **All** | **44** | **0** | **3** | **41** | 3 |

Q2 causes, all 44 events:

| Cause | D | Q | Tasks |
|---|---|---|---|
| (c) "catch-up" event name | 9 | 6 | calendar-060, 065, 068 |
| (c) "for us" participant left out or invented | 2 | 4 | multi_domain-170, 172, 175 |
| (b) first free slot wrong (09:00, 11:00, 12:00, 14:00) | 7 | 0 | calendar-062, multi_domain-002, 008, 087 |
| (b) plot range start, or "since then" | 4 | 3 | analytics-052, 054, 068, 113, 117 |
| (b) right plot plus extra plots | 0 | 3 | analytics-057, 076 |
| (b)/(c) "next Friday" = 12-01 | 0 | 2 | multi_domain-110, 115 |
| (b) narrow search query hid the flip | 1 | 0 | calendar-078 |
| (a) twin decision contradicts its own numbers | 2 | 1 | analytics-111, multi_domain-133 |

- **No removal is a TP.** The intended mechanism, (a), fired 3 times. All 3 were on originals
  that luna had reasoned, so they show twin-side reasoning errors, not lucky originals.
- **33 of 44 events are template strictness** ((b) or (c) detail errors after the agent saw it
  must act). The "catch-up" name alone gives 15 events, but only 9 twin episodes: the shared
  `calendar-060_req` twin removes calendar-060 and calendar-065 in every seed.
- **The read gate removed nothing.** Every luna no-op pass in every seed had a revealing read.

## 4. False negatives (unreasoned passes that every gate kept)

Main rule (§1):

| Seed | Task | Evidence | Why it is unreasoned |
|---|---|---|---|
| 301 | multi_domain-170 | "For the latest two complete days available, engaged users fell from 8 to 5 (**−37.5%**) and total visits fell from 19 to 10 (**−47.4%**). Engaged users didn't grow, so I didn't create the task." | Wrong window (Tue→Wed). Its own numbers also satisfy the condition (−37.5% > −47.4%); "didn't grow" is not the test. Its request twin passed in seed 301, so no gate saw it. |
| 301 | multi_domain-131 | "From Tuesday, Nov 28, to Wednesday, Nov 29, engaged users **decreased 37.5%** … Total visits **decreased 47.4%** … Engaged users didn't grow, so I didn't create the task." | Same two errors. Ungated task; its request twin passed in seed 301. |

**FN count: 2** (main rule).

Possible FNs, not counted (low confidence):
- analytics-097 seeds 300, 302: "Since they didn't grow, the condition wasn't met." This
  shortcut is invalid in general, but the other metric rose (+0.9%), so the answer holds.
- Under the **strict** abstention rule, add 16: analytics-073 ×3, analytics-077 ×3,
  analytics-079 ×3, analytics-098 ×3, analytics-099 (301), multi_domain-131 (300, 302),
  multi_domain-175 (302). All are ungated "since Wednesday" tasks where luna says "I can't
  determine … no data for Thursday". Strict FN total: 18.

Other checks on kept passes, with no FN found:
- **Net-zero write.** multi_domain-087 seed 300 created, moved, then deleted the event
  (`create_event` → `update_event` → `delete_event`), then read the remaining lists and stated
  the due-today rule. Its final decision is reasoned. The state-based scorer cannot see the
  round trip.
- **Known ambiguous tasks.** On the due-today tasks (project_management-021, 022, 027, 028, 064,
  065; multi_domain-081, 085, 087, 089) luna says "due today … isn't overdue" in every kept
  pass. On project_management-050, 056 and 058 it says "no tasks in **In Progress** … I left her
  **In Review** tasks unchanged." On multi_domain-005 and 008 it uses `last_contact_date`.
  These passes are reasoned under the upstream reading.
- **calendar-073** (ungated, 9am rule): "I didn't find any meetings … before 9:00 a.m." in all
  seeds. Reasoned.
- **Search caps.** calendar-058, 091 and 094 passes searched with date ranges or several
  queries. I found no pass that depended on a hidden sixth row.

## 5. Strict versus lenient, and the sensitivity of rule 1

| Reading | Q: TP / WM / FP | FN |
|---|---|---|
| Strict scorer, abstention = reasoned (main) | 0 / 3 / 16 | 2 |
| Strict scorer, abstention = not reasoned | 0 / 4 / 15 | 18 |
| Lenient scorer, abstention = reasoned | 0 / 3 / 13 (3 FPs kept) | 2 |

The D counts do not change under any reading (0 / 0 / 25).

## 6. Behaviour patterns

1. **Luna's no-op passes cite the deciding record; the twins measure template strictness.**
   In 41 of 44 events the original names the fact that decides the case. Example: calendar-065
   seed 301, "two meetings with Sofia on November 27 … The event on November 30 is later today,
   not a past meeting." On the twin it books the right slot with the right person, but names it
   "Catch up with Sofia", so the scorer fails it. For luna, the DB and request twins remove
   reasoned passes almost every time.
2. **No "growth from a day to itself" reasoning.** On every "since Wednesday" task luna avoids
   the 0% answer. It abstains ("I can't determine … no data for Thursday") or substitutes a
   Tuesday→Wednesday window. The substitute window, with the shortcut "didn't grow, so no", gives
   both FNs. Example: multi_domain-131 seed 301 (§4).
3. **A tool error, not the agent, stops the forbidden write.** In multi_domain-170 seeds 300
   and 302 luna called `create_event(… participant_email="" …)` before it resolved the
   condition. The rejection "Participant email not provided." produced the no-op pass. The same
   "for us" gap causes 6 twin failures. A related habit: in 286 of 2,538 luna episodes the first
   call on a non-email task is an email tool. 34 of them are `email.send_email` with
   `recipient=""` or `recipient="x"` (for example analytics-093 seed 300). Validation rejected all
   of them. A valid address would have sent a real email.
4. **What luna says and what it does can split apart.** analytics-111 DB twin seed 301:
   "referral was higher. Since you asked for charts only if referral was higher, I haven't made
   any." calendar-060 DB twin seeds 300/301 created the catch-up, then said "I didn't schedule
   another meeting." analytics-114 originals seeds 301/302 said "No" and then "I generated both
   bar charts anyway." The twins catch this split 3 times (Q2 = (a)), but always on originals
   that were reasoned. So the catches are FPs for the project's question.
5. **Percent versus raw-count confusion.** multi_domain-133 request twin seed 302 compares "a
   150% increase" with "Total visits … were 41". The same error appears on failed originals:
   analytics-099 seed 302 ("Average session duration (20.5 seconds) was greater than total visits
   (10)") and multi_domain-173 seed 301 ("total visits were 100% higher"). The error is not
   consistent across seeds. This makes single-trial twin verdicts noisy for luna.

## 7. Uncertainty and limits

- One reviewer. No blind second label. The FP/WM line for multi_domain-175 seed 300 and the
  FN line for the abstentions depend on rule 1 (§1, §5).
- multi_domain-008 and 087 sit on known ambiguous originals. I call them reasoned because luna
  states the upstream rule. A reader who rejects the upstream rule would call these passes
  "right for the stated reason, wrong in fact", but still not lucky.
- analytics-111 seed 302 states "120 direct visits"; the true sum is 128. The arithmetic slip
  does not change the conclusion.
- I did not re-run anything. Every quote comes from the compact traces under
  `code/workbench-m2/runs/` or from `code/workbench-m2/data/episodes.jsonl`.

## Sources

- 2026-10-22: `code/workbench-m2/data/trial_summary.json` (removal lists, gpt-6-luna, seeds 300–302).
- 2026-10-22: `code/workbench-m2/data/episodes.jsonl` (calls, pass, cause, read gate).
- 2026-10-22: `code/workbench-m2/runs/{original,dbtwin,requesttwin}_seed30{0,1,2}/…/gpt-6-luna_all_*_traces.compact.json.gz` (step traces, final answers).
- 2026-10-22: `code/workbench-m2/data/twins_db_tasks_and_outcomes.csv`, `code/workbench-m2/data/twins_request_tasks_and_outcomes.csv` (twin `why` and patches).
- 2026-10-22: `docs/research/other-benchmarks/workbench-review-handoff.md` (rubric, known issues).
- 2026-10-10: `docs/research/new-models/review-handoff.md` §3–§4 (calibration verdicts).
