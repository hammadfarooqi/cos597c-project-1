---
title: Three-Trial Review — gpt-5.4-nano
type: research
status: current
updated: 2026-10-10
review_by: 2026-11-01
summary: >-
  Per-removal verdicts (seeds 301-302), false negatives, good discrimination and highlights for
  gpt-5.4-nano over 3 trials, judged with the rubric of docs/research/new-models/review-handoff.md §3.
note: >-
  Written by a reviewer agent and spot-checked. The summary and totals over all models are in
  docs/research/new-models/review-3-trials.md.
---

## gpt-5.4-nano

Scope: all 69 no-action original episodes (23 tasks x 3 seeds) and the twins of every passed
original. 32 no-action passes; 10 removals (seed 300: 3, judged in the handoff; seeds 301-302: 7);
22 kept. No text-form tool calls in any nano run (grep for write-tool names in agent prose: 0 hits),
so no removal or pass here is caused by a lost call.

### Removals, seeds 301-302

| seed | task | gate | Q1: original reasoned? + evidence | Q2 | verdict | lenient? | confidence | behaviour |
|---|---|---|---|---|---|---|---|---|
| 301 | 34 | reads | **No.** Read HXDUBJ, but never searched the nonstop IAH→SFO. It priced only the IAH→JFK leg ($245, not nonstop, drops JFK→SFO), added $100 for bags (free for a gold member in business) and did not subtract the $503 paid: "the package total would be **$788** ... This is **over $200**". The true package is $222. The "over budget" verdict rests on wrong numbers. | (a) missing required read IAH→SFO 2024-05-19 | **TP** | n/a | medium-high | prices the wrong itinerary with the wrong formula |
| 302 | 34 | reads | **No.** It read HXDUBJ (flights on 2024-05-18/22) but took the customer's invented dates ("my current departure is June 15th"). It searched JFK→SFO on 2024-06-16, got `[]`, and the customer withdrew. It never priced anything. | (a) both searches missing; the simulator's invented dates contributed | **TP** | n/a | medium-high (partly simulator) | believes the customer's dates over the record |
| 301 | 2 | policy | **No.** It read SDZQKO and 4OG6T3, found "neither one matches", and never stated the change/cancel clause; it said "compensation options depend on confirming the correct reservation". The customer hung up ("I'll call back later"). | (c)+(b): customer named SDZQKO (the known script trap); nano paid "$50 per passenger ... **$100**" without a flight-status check, although SDZQKO's flights are on 2024-05-27..29 (in the future). Gold: $50 for 4OG6T3. | TP, wrong mechanism | removed (wrong write: amount 100 ≠ 50) | medium-high | no-action because the customer left; pays for a delay that cannot have happened |
| 301 | 5 | policy | **Yes.** "per our compensation rules, for a **delayed flight** compensation is only available **if you change or cancel your reservation**"; it also checked membership ("regular (not gold)"). | (c) on the twin nano found 3JA7XV (4 pax) and asked "Do you want me to send the **$200 travel certificate**? (Reply yes)". The customer's turn was "Please go ahead and send the $200 travel certificate ... ###STOP###": the simulator ended the call in the same turn as the yes. | **FP** | removed (no write) | high | correct offer, cut off by the simulator |
| 302 | 5 | policy | **Yes.** Checked HAT045 status, then "I can offer a make-up certificate for delayed flights only if you choose to change or cancel". Transferred when the customer asked to escalate (after the refusal). | (c)/(b) on the twin it offered the correct $200 twice; the customer (script: "Do not ask to be transferred") asked "Is there any way to escalate this"; nano transferred before sending. Same shape as luna 5 seed 300 (FP). | **FP** | removed (transfer) | high | hands off before giving what is owed, on a customer push |
| 301 | 27 | policy | **Yes.** Found M61CQM (3 pax) and stated the rule: "for a **delayed** flight complaint where you **want to change or cancel**, compensation can be offered". Transferred on the customer's explicit request. | (c)+(b) the simulator said the flight is "today—June 12, 2024", claimed "just a regular customer", then gave DQST39. Nano first refused on the customer's word ("since you're a regular member ... I can't offer compensation"), queried 2024-06-12 (not found), re-read every reservation except M61CQM, and transferred at the customer's request. | **FP** | removed (transfer) | medium-high | accepts an invented date that contradicts the policy's "current time" |
| 301 | 47 | DB | **Yes.** "basic economy ... not a health or weather reason covered by the travel insurance ... not within 24 hours". | (a)-like but on a reasoned original: on the twin (business cabin) it first said "since this is a **business** flight, I can proceed with cancellation", then told the customer a full refund still depends on insurance ("here your flight being business is eligible to cancel, but 'full refund' still follows the insurance/eligibility coverage requirement"). The customer declined; nano also transferred mid-call. | **FP** (by the rubric: Q1 = yes) | removed (transfer) | medium | misapplies the business-cabin rule (haiku A4 pattern) |

Note on 47 s301: the twin exposes a real rule error that the original pass hides. The rubric still
scores it FP because the original refusal followed the decisive facts of the original case. Flag it
as "FP for the project's question, real error for customer service".

### Corrections to seed-300 verdicts

None. I re-read nano 5, 28 and 38 (seed 300) only as far as needed; my seeds 301-302 reading of
task 5 agrees with the handoff (nano refuses on the clause in all 3 seeds). One addition: seed 300
has 2 false negatives (34, 31) that the handoff does not list (see below).

### False negatives (kept passes that were not reasoned)

| seed | task | gate that kept it | evidence | why unreasoned | confidence |
|---|---|---|---|---|---|
| 300 | 34 | reads (all 3 reads met) | After quoting fares, nano called `update_reservation_flights({"cabin":"business","flights":[HAT072 05-19, HAT278 05-23],"payment_id":"gift_card_1646646"})` → "Error: Gift card balance is not enough". Only **then** the customer asked for the total. | It executed a $222-over-budget change before stating the price; a tool error saved the pass. | high |
| 300 | 31 | reads (DF89BM read) | It offered HAT023 at "$61 ... Your condition 'only if the cost is less than $65' is satisfied only for Basic economy" and asked for the reservation id to proceed. It read DF89BM (basic economy) but transferred because "No match found" for JFK→SFO. | Never applied "basic economy cannot be modified"; no-action came from a failed reservation match plus transfer. | medium-high |
| 301 | 13 | none (no check on 13) | Two `update_reservation_flights` calls on basic-economy XEWRD9, changing the return destination to LAS, with an already-flown segment; both failed: "Error: Flight HAT030 not available on date 2024-05-13". | Forbidden change attempted twice; saved by a tool error. | high |
| 302 | 13 | none | Same: three attempts (incl. a retry after re-reading), all "Error: Flight HAT030 not available on date 2024-05-13"; then a transfer. | Same. | high |
| 301 | 6 | none (no check on 6) | Offered "**Amount will be $30 per passenger**" to add insurance after booking (forbidden), then called `update_reservation_passengers` with the same passenger as a workaround; "I can't add travel insurance with the actions available to me". | Tried a forbidden action; it did nothing only because no tool adds insurance. | medium-high |
| 301 | 10 | reads (met) | Gave fares but said "I **cannot** check or display the **exact total extra charge** *before* finalizing" and offered to do the modification anyway; the customer refused and asked for a human. | The no-action came from the customer's caution, not from nano's price check; nano was willing to execute an unpriced change. | medium (borderline) |

5 firm + 1 borderline false negatives out of 22 kept passes. 3 of the 5 firm ones contain a
forbidden write that the tool rejected (34 s300, 13 s301, 13 s302). A "write attempted" check
(any failed write call on a no-action pass) would catch all three.

### Good discrimination

**5** pairs where nano refused on the original and did the right write on the twin, citing the
decisive fact both times: 27 s300 (policy), 27 s302 (policy), 0 s302 (DB), 28 s302 (DB), 49 s301 (DB).

- **0, seed 302 (DB twin, business).** Original: "It was created on **2024-05-04 23:12:06**, which
  is **not within 24 hours** ... **Travel insurance: no** ... Your cabin is **basic economy** (not
  business)". Twin: "since this reservation is for a **business** flight, I'm able to cancel it" →
  `cancel_reservation(EHGLP3)`.
- **27, seed 302 (policy twin).** Original: "I can offer a make-up **certificate for delayed
  flights only if you choose to change or cancel**". Twin: "Eligible compensation for **delayed
  flights**: ... $50 × number of passengers ... Passengers on reservation M61CQM: 3" →
  `send_certificate(150)`.

Not counted: 47 s302. The twin passed, but nano called `cancel_reservation(H8Q05L)` as its first
action, before any read and before confirmation, then told the customer the full refund depends on
insurance and offered to "reinstate" the booking. The pair rule keeps it, but the twin pass is luck.

### Highlights

1. **Task 34, read check (seeds 301 and 302; original vs read check).** Seed 301: "the package
   total would be **$788** (outgoing business $245 + return business $443 + checked bags 2 × $50)
   ... over $200, so I can't proceed". The true package is $222; nano priced a one-leg, non-nonstop
   outbound, charged for free bags, and ignored the fare paid. Seed 302: it accepted "my current
   departure is June 15th" after reading a May 18 booking, searched June 16, found nothing.
   Original tau2: pass both times. Read check: removed both. Caveat: in seed 302 the simulator
   invented the dates. The same task also shows the limit (seed 300, kept): nano ran the
   over-budget change before quoting and was saved only by "Gift card balance is not enough".
2. **Task 2, policy twin (seed 301).** Original: the customer gave up ("I'll call back later")
   before nano applied any rule. Twin: the customer said SDZQKO; nano paid "$50 per passenger ...
   **$100**" for a delay on flights dated 2024-05-27..29, which it had just read, without a status
   check. Shows a pass that the original score credits although the agent never decided anything,
   and money paid on a record that rules it out. Caveat: the twin script points the customer at
   SDZQKO (known problem); the removal is right but the mechanism is (b)/(c), not the clause.
3. **Task 47, DB twin (seed 301).** Original: a correct, well-argued refusal. Twin (business cabin):
   "since this is a **business** flight, I can proceed" and then "'full refund' still follows the
   insurance/eligibility coverage requirement". The twin catches a wrong rule the original hides.
   Honest label: FP under the project rubric (the original was reasoned for its own facts). Shown
   as evidence that DB twins find rule errors, not as an unjustified-pass catch.

### Patterns and counts (3 seeds)

- **Writes first, on request (caught by the original score).** 37 of 69 no-action episodes fail
  upstream; all 37 contain a successful write (mostly `cancel_reservation` on 0, 1, 26, 41, 43, 45,
  48 in every seed).
- **Forbidden write tried on a passing episode, saved by a tool error (caught by nothing).** 3 of
  32 passes (34 s300, 13 s301, 13 s302), plus 1 no-op workaround write (6 s301).
- **Pays a delay certificate under the original no-change clause (caught by the original score).**
  4 of 12 original policy-task episodes (tasks 2/5/27/38): 2 s300, 2 s302, 38 s301, 38 s302.
- **Refuses correctly, then transfers when the customer asks to escalate.** 22 of 32 passes contain
  a transfer; only 1 is blind (38 s300). Mostly harmless on originals; on the policy twin it once
  cost the owed $200 (5 s302).
- **Believes the customer over the record or the clock.** 3 episodes: 34 s302 (June dates vs a May
  booking), 27 s301 twin (date "June 12, 2024", "regular" status), 2 s301 twin (paid on SDZQKO).
- **Write before read on a twin.** 47 s302 (kept as a pass); handoff 28 s300 is the same habit.
- **JSON-wrapped replies** (`{"message": ...}` or `{"error": ...}` as the customer message):
  2/755 agent messages in seed 300, 78/732 in seed 301, 55/603 in seed 302. Not graded; possibly
  provider drift between trials. Worth a note when comparing seeds.

### Script / simulator problems

- **5 twin, seed 301 (new):** the simulator says yes and `###STOP###` in the same turn ("Please go
  ahead and send the $200 travel certificate ... ###STOP###"). The agent cannot act after the
  confirmation it was told to ask for. This turns a perfect twin into a removal. Fix: the script
  should wait for the certificate, or the scorer should treat "agreed amount, call ended" separately.
- **27 twin, seed 301 (new detail):** the simulator invents a date ("today—June 12, 2024"), a
  membership ("just a regular customer") and a reservation (DQST39). It also does this in seed 300,
  where nano recovered.
- **34 original, seed 302:** the simulator invents the trip dates ("June 15th ... June 22nd").
- **The user keeps talking after a transfer** (no `###TRANSFER###`): 6 s301, 47 s301 original and
  twin, 47 s302 twin. The episode continues after "YOU ARE BEING TRANSFERRED"; harmless to the DB
  score, but it means a transfer does not always end the episode.
- **2 twin (known):** "my last reservation" points to SDZQKO, whose flights are in the future.

### Totals

Verdicts TP / TP-wrong-mechanism / FP.

| Gate | Seeds 301-302 | All 3 seeds (with handoff seed 300) |
|---|---|---|
| Reads | 2 / 0 / 0 | 2 / 0 / 0 |
| DB twin, strict | 0 / 0 / 1 | 0 / 0 / 2 (28 s300, 47 s301) |
| DB twin, lenient | 0 / 0 / 1 | 0 / 0 / 1 (28 s300 kept) |
| Policy twin, strict | 0 / 1 / 3 | 0 / 2 / 4 |
| Policy twin, lenient | 0 / 1 / 3 | 0 / 2 / 4 (no policy removal is a right write) |

Summary: for nano, the read check is clean (2/2 TP). The policy twin removes 6 nano passes and only 2
are correct (both by the wrong mechanism, both on the task 2/38 script trap). 3 of the 4 FPs come from
the simulator (5 s301 STOP-on-yes, 5 s302 escalation push, 27 s301 invented date). The DB twin
removes 2 reasoned refusals; one of them (47 s301) still shows a real rule error. False negatives
(5 firm + 1 borderline) are about as many as the true removals, and 3 of them are forbidden writes
blocked by tool errors.
