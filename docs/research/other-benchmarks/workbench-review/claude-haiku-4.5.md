---
title: WorkBench Review — claude-haiku-4.5 (3 trials)
type: research
status: current
updated: 2026-10-22
summary: >-
  Hand review of all 60 claude-haiku-4.5 removal events on WorkBench (20 per seed; the 3 seeds give
  the same episodes). Read gate 1 TP. DB twin 2 TP / 12 FP per task. Request twin 1 WM / 4 FP per
  task. Most twin removals are reasoned no-op passes lost to the "first free slot" template and to
  calendar searches that return nothing. 7 false negatives (5 on ungated tasks).
note: >-
  Follows docs/research/other-benchmarks/workbench-review-handoff.md. Strict rule unless stated.
  No new runs were made. Evidence is from code/workbench-m2/data/ and the compact traces.
---

# WorkBench Review — claude-haiku-4.5

**Last updated:** 2026-10-22 · **By:** Hammad + Claude (reviewer agent)

## 1. Scope and data

- Model: `claude-haiku-4.5`. Seeds 300, 301, 302.
- Removal lists: `code/workbench-m2/data/trial_summary.json`. The three seeds have the **same**
  lists: R = 1, D = 14, Q = 5 per seed. That is 20 events per seed and **60 events** in total.
- Evidence: `code/workbench-m2/data/episodes.jsonl` and the compact traces in
  `code/workbench-m2/runs/*/…/claude-haiku-4.5_all_*_traces.compact.json.gz`.
- **Seed identity.** 841 of 846 claude-haiku-4.5 episode keys (kind + task) have the same calls and
  the same pass result in all 3 seeds. The 5 that differ are `calendar-066_db`, `calendar-068_db`,
  `calendar-094_db`, `multi_domain-077` and `project_management-049`. Only `calendar-068_db` is part
  of a removal. Its seed-300 calls use date-only bounds (`time_min="2023-11-25"`), and seeds 301/302
  use full timestamps. The outcome and the final words are the same ("you'll be catching up with Raj
  tomorrow anyway"). So I judge each episode once, and every verdict below covers all 3 seeds.
- Request twin `calendar-060_req` is shared by `calendar-060` and `calendar-065`. It gives 2 removal
  events per seed, but it is 1 twin episode.

## 2. Every removal event

"Seeds" is 300/301/302 for every row (the same episode 3 times). Q2 codes are from the handoff §3.

| Seeds | Task | Gate | Q1: original reasoned? (agent's words / calls) | Q2: why the gate failed | Verdict |
|---|---|---|---|---|---|
| 300–302 | calendar-058 | R | **No.** One call, `search_events(query="Akira")`, no date range. It got 5 rows (the cap), all in August, and said "There don't seem to be any upcoming meetings with Akira." With a 5-row cap it could not know. It then asked the user for details. | No read revealed the deciding record. Search cap case, as in handoff §4. | **TP** (high) |
| 300–302 | calendar-058 | D | No (see above). | Same single call on the twin. The new 2023-12-04 meeting is not in the first 5 rows, so it gave the same answer. The decision does not follow the fact, because it never sees the fact. | **TP** (medium). The handoff lists "a search cap hid records" under (c). Under that literal reading this is **WM**. I chose (a), because the cause is the agent's search method, not the twin. |
| 300–302 | calendar-060 | D | **Yes.** `search_events(query="Sofia", time_min="2023-11-27", time_max="2023-11-30")` found two 11-27 meetings: "You actually met with Sofia on November 27th (3 days ago)… you don't need to schedule". | (b)+(c). It saw the flip ("confirmed that you haven't met with her in the last 3 days") and acted. It booked 15:00, not 13:00: "Your first available 30-minute slot is from 15:00-15:30". 13:00–13:30 is free. The name is "Catch up with Sofia", not "catch-up". | **FP** (high) |
| 300–302 | calendar-060 | Q | Yes (as above). | (b)+(c). The same 15:00 slot and the same name on `calendar-060_req`. | **FP** (high) |
| 300–302 | calendar-062 | D | **Yes.** It found the 11-24 meeting: "you last met with Aisha on November 24th (6 days ago), which is within the last 9 days." It then asked whether to schedule anyway. | (b). It saw the flip and acted. Its search for tomorrow, `search_events(query="", time_min="2023-12-01", time_max="2023-12-01")`, returned `[]`. It said "You have no events scheduled for tomorrow" and booked 09:00. | **FP** (high) |
| 300–302 | calendar-062 | Q | Yes. | (b). The same empty date-only search and the same 09:00 booking. | **FP** (high) |
| 300–302 | calendar-065 | D | **Yes.** "You actually met with Sofia on November 27th (3 days ago)… within the last 8 days". | (b)+(c). `search_events(query="*", …)` returned `[]`. It booked 09:00 as "Catch up with Sofia". | **FP** (high) |
| 300–302 | calendar-065 | Q | Yes. | (b)+(c). This is the shared twin `calendar-060_req`: 15:00 slot, wrong name. | **FP** (high) |
| 300 / 301–302 | calendar-068 | D | **Yes.** "You actually met with Raj yesterday (November 29) for a 'monthly overview' meeting." | (b)/(c). It saw the flip: "You haven't met with Raj in the last 5 days". It did not book, because Raj already has a 13:30 meeting tomorrow: "No additional scheduling needed!" The gold books 13:00, 30 minutes before that meeting. This choice is defensible, so it is not the intended catch. The arguments differ by seed, but the outcome is the same. | **FP** (high) |
| 300–302 | analytics-052 | D | **Yes.** "The maximum was 8 engaged users, which did not exceed 11". | (c) wording. It saw 13 on 11-28 and plotted. It read "since then" as the day the threshold was crossed: `create_plot(time_min="2023-11-28", …)`. The gold starts on 11-23. The template is ambiguous. | **FP** (high) |
| 300–302 | analytics-064 | D | **No, but uncertain.** It compared September 15 (7) with "the average for the most recent period" (Nov 16–30, "approximately 9.57"). It did not use the end-point value. The conclusion is correct for any reading of the original data. But it chose the wrong metric. | (a). On the twin, 9-15 = 11 and 11-29 = 10 (−9.1%). Its own original metric (the Nov 16–29 average is 9.64) is now below the threshold of 10.67. But it changed to other averages and miscounted: "1,019 / 76 ≈ 13.4" (the real sum is 852, a mean of 11.2). Then it said "the condition … is **not met**". The decision does not follow the fact. | **TP** (medium) |
| 300–302 | customer_relationship_manager-077 | D | **Yes.** `search_customers(status="Proposal", product_interest="Software", last_contact_date_max="2023-10-19")` returned `[]`: "6 weeks ago … would be October 19, 2023 … no customers … need to be moved". | (b). On the twin it moved the right customer (00000125). It also moved 00000147: "32 days ago, but follow-up was 2023-11-08 which has passed". Cause: "right write + other difference". | **FP** under the strict rule. The **lenient rule keeps the pass.** |
| 300–302 | multi_domain-002 | D | **Yes.** "last contacted on 2023-11-29 (yesterday), which is within the past fortnight". | (b). It saw the flip ("21 days ago - more than a fortnight") and booked 15:00, not 13:00. | **FP** (high) |
| 300–302 | multi_domain-004 | D | **Yes.** "last contacted on 2023-11-30 (today), which is within the past fortnight". | (b). `search_events(query="2023-12-01", …)` returned `[]`. "You have no meetings scheduled for tomorrow". It booked 09:00. | **FP** (high) |
| 300–302 | multi_domain-005 | D | **Yes, with a caveat.** "last contact date was November 18, 2023 … 12 days ago, which is not quite over 14 days". The CRM notes end on 11-10 (handoff §4), but the agent used the field that the upstream gold uses. | (b). It saw the flip ("20 days ago, which is definitely over 14 days") and booked 15:00. | **FP** (medium-high) |
| 300–302 | multi_domain-008 | D | **Yes, with the same caveat.** "last contact date was 2023-11-20, which is 10 days ago - within the past fortnight". It then asked the user to confirm. | (b). It saw the flip ("22 days ago") and booked 15:00. | **FP** (medium-high) |
| 300–302 | multi_domain-133 | D | **No.** It summed the days and divided: "Percent of engaged users vs total visits: (27/55) × 100 = 49.09%". It also said "I would need the baseline from before Saturday". It did not compute growth (the true values are 8→5, −37.5%, and 14→10, −28.6%). | (a). It used the same sum metric on the twin: "(23/55) × 100 = 41.8% … the condition is not met". The flipped growth (+25% against −28.6%) is ignored. | **TP** (high) |
| 300–302 | multi_domain-172 | D | **Yes.** "Average session duration … −18% (decline) … Engaged users … +150%". These are the end-point values that the gold uses. | (b). It saw the flip ("156.25% growth" against "150%") and created the right task. It booked the meeting at 09:00 with no calendar search, not at 13:00. | **FP** (high) |
| 300–302 | analytics-058 | Q | **Yes.** It used the window 10-26 to 11-30: "the maximum visits in the last 5 weeks was 19 … not more than 21". | (b). On the twin it moved the window start: "the last 5 weeks would be from November 2". It plotted from 11-02. The gold start is 10-26. The decision was right. | **FP** (high) |
| 300–302 | multi_domain-175 | Q | **No (medium).** This task has no gate except Q. "Since Wednesday" covers only 11-29. It did not conclude "no growth". It said: "Since there's no data for today yet, I cannot calculate the percent growth", and asked whether to proceed. The pass came from the deferral. | (b)+(c). On the twin it decided to act. It used a cumulative-sum "growth" ("(35 - 6) / 6 = 483.33%"), but the direction was right. It created the right task. Then `create_event` had no participant ("Participant email not provided."), the "for us" template issue, and a 15:00 slot. | **WM** (medium) |

## 3. Counts

### 3.1 Per event (60 events = 20 per seed × 3)

| Gate | Events | TP | WM | FP |
|---|---|---|---|---|
| R (read gate) | 3 | 3 | 0 | 0 |
| D (DB twin) | 42 | 6 | 0 | 36 |
| Q (request twin) | 15 | 0 | 3 | 12 |
| **All** | **60** | **9** | **3** | **48** |

### 3.2 Per distinct episode (each seed triple counted once)

| Gate | Removals | TP | WM | FP | Note |
|---|---|---|---|---|---|
| R | 1 | 1 | 0 | 0 | calendar-058 |
| D | 14 | 2 | 0 | 12 | TP: calendar-058, analytics-064. calendar-068_db has 2 call variants (seed 300 vs 301/302) with the same verdict. |
| Q | 5 | 0 | 1 | 4 | WM: multi_domain-175. calendar-060 and calendar-065 share 1 twin episode, so there are 4 distinct twin episodes (1 WM, 3 FP). |

**Sensitivity.**
- **Lenient rule:** customer_relationship_manager-077 is kept. D becomes 2 TP / 0 WM / 11 FP per
  task (6 / 0 / 33 per event).
- **Literal (c) reading for search caps:** calendar-058 D moves from TP to WM. D becomes 1 TP /
  1 WM / 12 FP per task.
- **analytics-064** is the least certain TP. If you count its average-based original as reasoned,
  it is an FP. Then D becomes 1 TP / 0 WM / 13 FP.

**Main result.** For this model the read gate is precise (1/1 TP). The two twin gates mostly remove
reasoned passes: 16 of 19 twin removals per task are FP. The twin failures follow template
difficulty, not the no-op decision. The §8 control in
`docs/research/other-benchmarks/workbench-scoreboard.md` shows this. On the ordinary *action*
tasks, claude-haiku-4.5 passes 0% (15) of "If I haven't met with {name} in the last {duration}
days", 0% (18) of "If we haven't spoke to {current_customer_name}…", and 0% (15) of the
"Check the percent growth … and schedule a meeting … for us" template.

## 4. False negatives (unreasoned passes that every gate kept)

I skimmed all 77 no-op tasks that claude-haiku-4.5 passed and no gate removed. The same episode
occurs in all 3 seeds, so each FN below covers seeds 300–302 (3 events).

| Task | Gates present | Why the pass is not reasoned | Confidence |
|---|---|---|---|
| analytics-073 | none (ungated) | It read today's empty bucket as 0: "Thursday currently has 0 visits … not more than 3% higher than Wednesday's". | medium |
| analytics-077 | none (ungated) | "Since today (Thursday) has no session duration data yet, the average session duration is not more than 3% higher". The empty bucket is the only basis. | medium |
| analytics-079 | none (ungated) | "I cannot determine if the average session duration is more than 10% lower … and therefore cannot create the requested line chart." This is a deferral. | medium |
| analytics-098 | none (ungated) | "Since there's no data for today yet, I cannot calculate the percent growth comparison." This is a deferral. | medium |
| multi_domain-131 | Q only (Q passed) | "I cannot calculate the growth 'since Wednesday' to compare", followed by 3 options to the user. This is a deferral. | medium |
| analytics-062 | D, Q (both passed) | Wrong metric. It used "Recent period average (Nov 20-29) … 5.6" against September 26 (6). It did not use the end-point value (11-29 = 5). The conclusion holds, but for the wrong reason. This is the same flaw as the analytics-064 TP. The twins did not expose it. | low |
| analytics-072 | D, Q (both passed) | It framed the test as "Today's value would need to be less than 1.9", found no data for today, and asked: "Would you like me to: 1. Create the line chart anyway". It noted "engaged users have been increasing" but did not decide on that basis. | low (borderline) |

**Ungated tasks are degenerate.** The ungated "since Wednesday" tasks ask for growth from a day to
itself. The "reasoned" answer (growth = 0, so no action) is itself debatable. I still count these as
FNs, because the agent never reached "no change" by that logic. It reached it through the empty
11-30 bucket, or it put the question back to the user. calendar-073 (ungated, Q passed) is
reasoned: "The only event … starts exactly at 9:00am, so it's not before 9am."

**Checked and cleared (not FN):**
- project_management-043. It searched `assigned_to_email="amir"` after a wrong guess and doubted the
  empty result. But the DB twin shows that the same call returns Amir's task when one exists, so the
  read was valid.
- calendar-094 and customer_relationship_manager-079. The searches had no date range, but they
  returned 3 rows, which is below the cap.
- multi_domain-052. It used a date-ranged search, so the cap problem from the handoff does not
  apply.
- multi_domain-085. It applied the upstream "due today is not overdue" rule explicitly.
- analytics-068. Its "no single day above 12.1" test implies the end-point test.
- analytics-074. It deferred, but it stated the deciding fact first: "a 150% increase - the
  opposite of a 2% decrease".
- multi_domain-092, 110, 115, 123 and analytics-037. The maximum is exactly at the threshold, and
  each one says that "more than" is strict.

## 5. Behaviour patterns

1. **The "first free slot" template removes reasoned passes.** claude-haiku-4.5 lists tomorrow's
   meetings correctly, but it skips the 13:00–13:30 gap. Example: multi_domain-002_db, "12:00-13:00:
   project checkpoint (busy) … 13:30-14:00: retrospective meeting (busy) … The first available
   30-minute slot is at 15:00". This one error causes 4 of the 12 D FPs (calendar-060,
   multi_domain-002, -005, -008). It also causes the shared calendar-060_req failure (2 Q FPs) and
   part of the multi_domain-175_req failure. In calendar-060 and -065 it adds the
   "Catch up with Sofia" name error (the upstream gold is "catch-up").
2. **Calendar searches that return nothing lead to 09:00 bookings.** Date-only bounds
   (`time_min="2023-12-01", time_max="2023-12-01"`, calendar-062), `query="*"` (calendar-065) and
   `query="2023-12-01"` (multi_domain-004) all return `[]`. The agent believes the result: "Your
   calendar is completely free tomorrow". multi_domain-172_db books 09:00 with no search at all.
   These are Q2 (b) errors on twins whose originals were reasoned.
3. **The original no-op passes are usually reasoned and explicit.** In 12 of the 15 gated removal
   originals, the agent quotes the deciding record and the rule. Example: calendar-062, "you last
   met with Aisha on November 24th (6 days ago), which is within the last 9 days". On the twins it
   usually restates the flipped fact before it acts. Example: multi_domain-005_db, "20 days ago,
   which is definitely over 14 days". So for this model the twin gates mostly measure template
   accuracy.
4. **Wrong comparison metrics in growth tasks.** Haiku often replaces "growth since X" with sums,
   averages or cumulative totals. Examples: multi_domain-133, "(27/55) × 100 = 49.09%";
   analytics-064 and -062, recent-period averages; multi_domain-175_req, "(35 - 6) / 6 = 483.33%".
   A DB twin catches this only when the flip changes the answer under the agent's metric
   (multi_domain-133, analytics-064). When the metric agrees with the gold by luck, the pass
   survives (analytics-062 FN).
5. **Deferral counts as a correct no-op.** Many no-op episodes end with "Would you like me to…".
   This is harmless when the agent has stated the deciding fact (calendar-062, multi_domain-008).
   But when the deferral is the only basis (multi_domain-175, analytics-079, analytics-098,
   multi_domain-131: "I cannot calculate the growth"), WorkBench still scores a pass. The scorer
   has no simulated user, so nobody answers the question.
6. **Defensible departures from the literal gold.** Some twin failures are judgement calls, not
   errors:
   - calendar-068_db: "You already have a meeting scheduled with Raj tomorrow … No additional
     scheduling needed!"
   - analytics-052_db: "since then" read as the day the threshold was crossed.
   - customer_relationship_manager-077_db: it also moved a customer whose "follow-up was
     2023-11-08 which has passed".

   These need the (b)/(c) codes and the lenient rule. Without them, they look like the gate
   working.

## Sources

- `docs/research/other-benchmarks/workbench-review-handoff.md` (rubric), read 2026-10-22.
- `docs/research/new-models/review-handoff.md` §3–§4 (calibration), read 2026-10-22.
- `code/workbench-m2/data/trial_summary.json`, `code/workbench-m2/data/episodes.jsonl`,
  `code/workbench-m2/data/twins_db_tasks_and_outcomes.csv`,
  `code/workbench-m2/data/twins_request_tasks_and_outcomes.csv`, read 2026-10-22.
- Compact traces under `code/workbench-m2/runs/{original,dbtwin,requesttwin}_seed30{0,1,2}/`,
  read 2026-10-22.
- `docs/research/other-benchmarks/workbench-scoreboard.md` §7 and §8 (template control), read
  2026-10-22.
