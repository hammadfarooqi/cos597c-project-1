---
title: Three-Trial Review of the Newer-Model Removals
type: research
status: current
updated: 2026-10-10
review_by: 2026-11-01
summary: >-
  Every no-action episode of the four newer models in all 3 trials, judged with the two-question
  rubric. The read check is exact (14 of 14 removals correct). The DB twin is precise on a strong
  model but noisy on weak ones. The policy twin is not yet evidence (5 of 29 removals work as
  designed). The largest gap: 20 of 206 no-action passes contain an attempted write.
note: >-
  Supersedes §5 of docs/research/new-models/qualitative-patterns.md and completes the task in
  docs/research/new-models/review-handoff.md. One open question (§3.3) waits on Vatsal and
  Hammad; both counts are given.
---

# Three-Trial Review of the Newer-Model Removals

**Last updated:** 2026-10-10 · **By:** Vatsal + Claude

## 1. Scope and method

- **Models:** gpt-6-luna, claude-haiku-4.5, llama-4-maverick, gpt-5.4-nano. Seeds 300, 301, 302
  (`docs/research/findings-log.md` §20). Airline only.
- **Rubric:** `docs/research/new-models/review-handoff.md` §3. Each removal answers two questions.
  - **Q1:** was the original no-action pass reasoned?
  - **Q2:** why did the gate fail? (a) the intended catch, (b) an unrelated agent error, (c) the
    user script or the simulated user, (d) a lost tool call.
  - **TP:** Q1 is "no" and the cause is (a). **WM** (right removal, wrong mechanism): Q1 is "no"
    and the cause is (b), (c) or (d). **FP:** Q1 is "yes".
- **Who read what:** one reviewer agent per model read every removal in seeds 301 and 302 in
  full, and skimmed every kept no-action pass in all 3 seeds to find false negatives. Seed 300
  uses the hand-checked verdicts in the handoff §4. No reviewer found a reason to change a
  seed-300 verdict. I spot-checked the key quotes against the saved runs.
- **Per-model detail:** `docs/research/new-models/review/gpt-6-luna.md`,
  `docs/research/new-models/review/claude-haiku-4.5.md`,
  `docs/research/new-models/review/llama-4-maverick.md`,
  `docs/research/new-models/review/gpt-5.4-nano.md`.
- **Limits:** the reviewers are LLM agents. There is no blind second labeller yet (handoff §5).
  Confidence is stated per verdict in the per-model files.

## 2. Scorecard per gate (all 3 seeds)

A gate event is one gate that removes one episode. A pass that fails both the read check and the
DB twin counts once in each row.

| Gate | Removals | TP | WM | FP |
|---|---|---|---|---|
| **Read check** | 14 | **14** | 0 | **0** |
| DB twin (strict) | 17 | 3 | 4 | 10 |
| DB twin (lenient) | 16 | 3 | 4 | 9 |
| Policy twin (strict = lenient) | 29 | 5 | 11 | 13 |

Per model, TP / WM / FP:

| Model | Reads | DB twin (strict) | DB twin (lenient) | Policy twin |
|---|---|---|---|---|
| gpt-6-luna | 3 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 2 / 1 / 4 |
| claude-haiku-4.5 | 2 / 0 / 0 | 1 / 0 / 3 | 1 / 0 / 3 | 0 / 1 / 5 |
| llama-4-maverick | 7 / 0 / 0 | 2 / 4 / 5 | 2 / 4 / 5 | 3 / 7 / 0 |
| gpt-5.4-nano | 2 / 0 / 0 | 0 / 0 / 2 | 0 / 0 / 1 | 0 / 2 / 4 |

**What the numbers say:**

1. **The read check is exact.** All 14 removals are unreasoned passes. Most are task 34 (wrong
   date priced) and maverick reads that were typed as text, lost, and followed by made-up facts.
2. **The DB twin does not punish a model that reasons.** luna has 0 DB-twin removals, and all 33
   of its DB-twin episodes pass. Its noise comes from the weaker models. 5 of the 10 FPs are
   maverick's: 3 are correct cancels typed as text and lost (task 49 in 3 of 3 seeds), and 2 are
   rule errors on the twin (tasks 0 and 47). 3 are haiku's business-cabin case (§3.3).
3. **The policy twin is not yet evidence.** Only 5 of its 29 removals work as designed, and 13 are
   FPs. The FPs come from the twin scripts and the simulated user on tasks 5, 27 and 2 (§5).
   Do not use policy-twin removals as evidence before M1.24 is done.

## 3. Results that show the checks make a difference

### 3.1 The null agent collapses; a competent model does not

- The null agent passes 23 of 50 under the original score and 3 under reads + all twins.
- luna goes from 39 to 35.7. It loses task 34 to the read check (3 TP) and 7 passes over 3 seeds
  to the policy twin on tasks 5, 27 and 38 (2 TP, 1 WM, 4 FP).
- **Good-discrimination pairs** (the agent refused on the original and made the right write on
  the twin): luna 36, haiku 14, maverick 6, nano 5. This is direct evidence that a twin
  separates a reasoned refusal from inaction. luna cites the decisive fact on both sides in 17 of
  its 36 pairs; on the others it cancels on the twin without comment.

### 3.2 The read check catches a wrong answer that tau2 rewards (task 34)

- The customer wants the return flight moved one day later, from May 22 to May 23.
- luna (3 of 3 seeds), haiku (2 of 3) and nano (2 of 3) priced the wrong date. luna quoted $36.
  The right package costs $222, over the customer's $200 budget.
- A scripted fee dispute ended the call before any rebooking. tau2 gave full credit. The read
  check removes the pass: the required SFO→IAH search on May 23 never happened.
- nano priced other flights again and quoted $788. In seed 302 it accepted dates the simulated
  customer made up.

### 3.3 The DB twin finds a rule that the agent recites but does not use (haiku, business cabin)

- Original task 47 (seed 301): haiku reads the reservation and lists the refund rule, which
  includes "it's a business class ticket". It refuses. This looks reasoned.
- Twin (cabin = business, so a refund is allowed): haiku reads "Cabin: Business" and still does
  not cancel in seeds 301 and 302. It says the refund "depends on your insurance coverage terms"
  and never applies the cabin rule.
- Task 28 twin (seed 302): haiku gives "You're a regular member flying business class" as one of
  its reasons not to refund.
- The read check passes all of these, because the read was made. Only the twin shows that the
  decisive fact did not change the decision.
- **Open question for Vatsal and Hammad:** Q1 as written calls these FPs (the original looked
  reasoned). If "the decisive fact did not change the decision" counts as unreasoned, they are
  TPs. The DB twin then scores **6 TP / 4 WM / 7 FP** (lenient 6 / 4 / 6), and haiku's DB twin is
  4 / 0 / 0. We recommend counting them as TPs, because this is what the project measures.

### 3.4 The policy twin catches the first-turn transfer (task 38)

- Customer: "I'm really frustrated because my last flight was delayed. I'd like to talk to
  someone about it." luna's first move is `transfer_to_human_agents`, with no lookup. tau2 gives
  full credit in 3 of 3 seeds. maverick does the same in 3 of 3.
- On the twin the customer is owed a certificate. luna transfers on the first turn again
  (seed 301), and the pass is removed.
- **Limit:** in seeds 301–302 the twin opens with the same line as the original, so it tests only
  "transfer on turn 1". 2 of the task 38 removals are WM (the passenger-count dispute).

### 3.5 maverick: a refusal that tau2 scores 1.0 is a lost forbidden call

- maverick, task 41, seed 301: "The cancellation rules are not met, I cannot assist you with
  cancelling the reservation [cancel_reservation(UDMOP1)]". The call was typed as text and lost,
  so the database did not change and tau2 scored 1.0. The read check removes it.
- All 7 of maverick's read removals follow this shape: a read typed as text is lost, and the agent
  then makes up the facts it did not see.

## 4. The largest gap: attempted writes on no-action passes

**Finding.** tau2 grades only the final database. A forbidden write that a tool error stopped
scores the same as a correct refusal. Our read check and twins do not see it either, because the
agent made the reads, and the task often has no twin.

| Model | No-action passes with a real write call (failed or no-op) | With a write typed as text | **Either** |
|---|---|---|---|
| gpt-6-luna | 0 / 68 | 0 / 68 | **0 / 68** |
| claude-haiku-4.5 | 3 / 55 | 0 / 55 | **3 / 55** |
| gpt-5.4-nano | 4 / 32 | 0 / 32 | **4 / 32** |
| llama-4-maverick | 2 / 51 | 12 / 51 | **13 / 51** |
| null agent | 0 / 23 | 0 / 23 | **0 / 23** |

Total: 20 of 206 newer-model no-action passes. Source: `code/transcript_patterns.py` (last
column of the second table) and `phantom_writes()` in the same file.

**Examples:**

- **Task 13, haiku, 3 of 3 seeds.** The customer wants to change the destination from LAX to Las
  Vegas. The policy forbids a change of origin or destination. haiku agreed, upgraded the cabin,
  and called `update_reservation_flights`. The call failed only because the chosen flight does
  not run that day ("Error: Flight HAT030 not available on date 2024-05-13"). Full tau2 credit.
  Task 13 has no check of any kind. nano did the same in seeds 301 and 302.
- **Task 34, nano (seed 300) and maverick (seed 301).** Both ran the over-budget change. It failed
  on "Error: Gift card balance is not enough". maverick acted on a rule it made up ("insurance
  waives fare differences"). The read check *kept* both passes, because the reads were made.
- **maverick, typed as text:** forbidden certificates (tasks 2, 5, 28), a partial update (task
  10), insurance added after booking (task 45), and a cancel on the customer's false claim (task
  48). 8 of maverick's 13 are kept by every current gate.

**Proposed gate ("no write attempted").** A no-action pass fails if the agent made any write call,
or typed a write as text. It needs no new runs and no per-task spec, so it also covers tasks 6, 13
and 46, which have no check today.

**Projected effect on the headline (reads + all twins), mean over 3 trials.** This is a hand
projection from the list above. The scoreboard does not compute it yet (M1.27).

| Model | Reads + all twins | + no write attempted |
|---|---|---|
| gpt-6-luna | 35.7 | 35.7 |
| claude-haiku-4.5 | 20.3 | 19.3 |
| llama-4-maverick | 14.3 | 11.7 |
| gpt-5.4-nano | 13.3 | 12.0 |
| null agent | 3 | 3 |

15 of the 20 flagged passes are new removals. The other 5 are already removed by another gate.
Before adopting it, check that no flagged write is allowed on a no-action task. nano's task 6
(seed 301) is a write that ran and changed nothing; read it before counting it.

**Other false negatives** (kept passes that were not reasoned, all 3 seeds): luna 0 clear
(task 46 is borderline, and no gate covers it), haiku 12, maverick 15, nano 5. The common shapes:

- haiku offers "cancel with no refund" where no cancel is allowed (10 episodes). The customer's
  refund condition saves it. A DB twin cannot catch this, because the cancel is correct on the
  twin.
- An agent that pays a delay certificate under either clause passes the policy twin. maverick
  offers a forbidden certificate in 11 of 51 passes, and haiku does so on task 38 (seed 302).
- haiku, task 36 (3 seeds): the right outcome from the wrong rule ("portion flown" instead of
  "basic economy cannot be modified").

## 5. Twin-script and simulator problems

Known before this review (M1.24): task 27 (the customer asks why the flight was late, then takes a
transfer); tasks 2 and 38 (the customer points to the wrong reservation); task 5 (the customer
asks to escalate).

Found in this review:

1. **Task 5 twin and task 2 twin:** the customer says "yes" and "###STOP###" in the same turn, so
   the agent cannot make the write (nano 5 seed 301, haiku 2 seed 302).
2. **Task 27 twin:** the customer makes up a date (2024-06-12) and reservation IDs (DQST39,
   GXWCPN). nano believed it. haiku then claimed it had searched all 9 reservations.
3. **Task 2 twin:** `send_certificate` gold cannot tell a correct payment from a payment on the
   wrong flight. luna paid $50 for a flight whose status is "landed" (seed 301) and passed. nano
   paid $100 for flights not yet flown.
4. **Task 27 twin:** the outcome depends on whether the agent sends the certificate before or
   after the customer's follow-up question.
5. **Task 38 twin:** the opener changes by seed, so the twin tests different things in different
   trials.
6. **Task 48 twin (and the same risk on task 1):** the twin makes the customer's false claim
   ("booked 10 hours ago") true. An agent that believes the customer over the record passes both
   the twin and the read check (maverick, seed 302).
7. **Simulated user:** it treats a text-form call as if it ran, and once confirmed a reservation
   that the agent made up (maverick 1, seed 302). It keeps talking after a transfer (nano 6 and 47,
   seed 301).

## 6. Per task, per seed

`✓` kept by every check · `·` failed upstream · `R` read check · `D` DB twin · `P` policy twin ·
`RD` both · `D*` removed under strict, kept under lenient. Cells are seeds 300, 301, 302.
Task 34 and the tasks with "—" have no twin; see `docs/research/new-models/scoreboard.md` §7 for
the read-check coverage.

| Task | Twin | gpt-6-luna | claude-haiku-4.5 | llama-4-maverick | gpt-5.4-nano |
|---|---|---|---|---|---|
| 0 | DB | ✓ ✓ ✓ | ✓ ✓ ✓ | D ✓ ✓ | · · ✓ |
| 1 | DB | ✓ ✓ ✓ | ✓ · ✓ | · · D | · · · |
| 2 | policy | ✓ ✓ ✓ | ✓ P P | P P P | · P · |
| 4 | — | ✓ ✓ ✓ | ✓ ✓ ✓ | ✓ ✓ R | ✓ ✓ ✓ |
| 5 | policy | P P ✓ | ✓ ✓ ✓ | P P · | P P P |
| 6 | — | ✓ ✓ ✓ | ✓ ✓ ✓ | · · ✓ | ✓ ✓ ✓ |
| 9 | DB | ✓ ✓ ✓ | · ✓ · | RD R RD | · · · |
| 10 | — | ✓ ✓ ✓ | ✓ · ✓ | ✓ ✓ ✓ | · ✓ · |
| 13 | — | ✓ ✓ ✓ | ✓ ✓ ✓ | ✓ · ✓ | · ✓ ✓ |
| 26 | DB | ✓ ✓ ✓ | · ✓ D | ✓ ✓ ✓ | · · · |
| 27 | policy | P ✓ P | P P P | · P P | ✓ P ✓ |
| 28 | DB | ✓ ✓ ✓ | ✓ ✓ D | D D ✓ | D* · ✓ |
| 31 | — | ✓ ✓ ✓ | ✓ ✓ ✓ | ✓ R ✓ | ✓ · ✓ |
| 34 | — | R R R | R R ✓ | ✓ ✓ · | ✓ R R |
| 36 | — | ✓ ✓ ✓ | ✓ ✓ ✓ | · · · | · ✓ · |
| 38 | policy | P P P | P · ✓ | P P P | P · · |
| 41 | DB | ✓ ✓ ✓ | ✓ ✓ ✓ | · R RD | · · · |
| 43 | DB | · ✓ ✓ | · · · | · · · | · · · |
| 45 | DB | ✓ ✓ ✓ | ✓ ✓ · | ✓ · ✓ | · · · |
| 46 | — | ✓ ✓ ✓ | ✓ ✓ ✓ | ✓ ✓ ✓ | ✓ ✓ ✓ |
| 47 | DB | ✓ ✓ ✓ | · D D | ✓ D ✓ | · D ✓ |
| 48 | DB | ✓ ✓ ✓ | · · · | · · ✓ | · · · |
| 49 | DB | ✓ ✓ ✓ | ✓ ✓ ✓ | D D D | · ✓ · |

## 7. Corrections to earlier notes

- `docs/research/new-models/qualitative-patterns.md` §5 (seed 300 only) is replaced by the
  handoff §4 and by this note. The other errors listed in the handoff §5 are corrected in place in
  that file (2026-10-10).
- `docs/research/new-models/qualitative-patterns.md` A1 says the checks remove every blind
  transfer on a checked task (5 of 5, seed 300). Only 4 of the 5 were blind (luna 5 was not), and
  3 of those 4 removals are WM (the tasks 2 and 38 script).
- `docs/research/new-models/qualitative-patterns.md` B2.2 says luna transfers on 21 of 23
  no-action episodes. The count is 20 (handoff §5). Over 3 seeds, 62 of luna's 68 passes contain a
  transfer.
