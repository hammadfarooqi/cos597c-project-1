---
title: Three-Trial Review — gpt-6-luna
type: research
status: current
updated: 2026-10-10
review_by: 2026-11-01
summary: >-
  Per-removal verdicts (seeds 301-302), false negatives, good discrimination and highlights for
  gpt-6-luna over 3 trials, judged with the rubric of docs/research/new-models/review-handoff.md §3.
note: >-
  Written by a reviewer agent and spot-checked. The summary and totals over all models are in
  docs/research/new-models/review-3-trials.md.
---

## gpt-6-luna

Scope: 23 no-action tasks x 3 seeds (69 original episodes, 68 upstream passes; only 43@300 failed),
plus every DB twin and policy twin in each seed. Removals: 10 in total (300: 4, 301: 3, 302: 3),
which matches the handoff. No text-form tool calls in any luna run (checked with a regex over all
9 run folders). So mechanism (d) never applies to luna.

### Removals, seeds 301-302

| seed | task | gate | Q1 (original reasoned?) + evidence | Q2 | verdict | lenient? | confidence | behaviour |
|---|---|---|---|---|---|---|---|---|
| 301 | 5 | policy | **Yes.** Checked `get_flight_status(HAT045)` and stated the clause: "a certificate for a delayed flight can be considered only if you change or cancel the reservation. Since you want to stay on the flight, I can't offer delay compensation". It transferred only after the customer asked to "escalate this". | (c), partly (b). Twin: read all 4 reservations, found 3JA7XV, "I can offer a $200 travel certificate ($50 per passenger)". It repeated $200 once. Then the customer asked "Is there any way you can escalate this … maybe a refund to my original payment method" (the script says "Do not ask to be transferred"). luna transferred and sent nothing. | **FP** | No (no `send_certificate`; cause = transfer) | high | offers the right amount, then hands off on escalation instead of sending |
| 302 | 27 | policy | **Yes.** "under the available policy, a delay certificate may be considered only if you want to change or cancel your reservation". It transferred on its own after the customer asked for a voucher. | (c) + (b). Twin: found M61CQM, 3 passengers, "I can offer a $150 travel certificate ($50 per passenger). Would you like me to send it?" The customer asked "Is there any way you can find out the specific reason for the delay?" and about a refund. luna transferred without sending. The same as the seed-300 FP. | **FP** | No | high | offers, then transfers on the "why" follow-up |
| 301 | 34 | reads | **No.** Searched SFO-IAH on **May 21** (`search_direct_flight SFO→IAH 2024-05-21`). It never searched May 23. It offered "Move your return to May 21 on flight HAT278 … a $36 fare increase" and asked for a "yes". The return was May 22, and the request means May 23 (the real package is $222, over the $200 budget). Only the scripted insurance-fee question and a transfer stopped a wrong rebooking. | missing required read (SFO-IAH 05-23) | **TP** | n/a | high (the date wording is ambiguous; see below) | prices the wrong date; budget decision never made |
| 302 | 34 | reads | **No.** The same May 21 search. "The listed fares total $539 … a $36 fare difference". It then said "I can't confirm that the full cost will stay under $200 because … separate change fees" and transferred on the fee dispute. The $200 cap was never tested against the right date. | missing required read | **TP** | n/a | high | same |
| 301 | 38 | policy | **No.** Blind first-turn transfer. U: "I'd like to talk to someone about it." A-> `transfer_to_human_agents` (no lookup). | (a) The twin opens with the same phrase and gets the same blind transfer. No lookup is made, so no $50 is sent. | **TP** | No | high | "talk to someone" → instant transfer |
| 302 | 38 | policy | **No.** Blind first-turn transfer ("I'd like to talk to someone about this." → transfer). | (c) + (b), not (a). The twin's opener this time was "Can you help me with this?". luna did the lookups: it read SDZQKO and 4OG6T3, found HAT018 delayed, and said "The reservation record lists one passenger, not three. For a confirmed delayed flight, I can offer a $50 certificate per passenger." The scripted customer insisted on 3 passengers twice. luna then transferred, and the customer admitted the mistake one turn too late ("Okay, maybe I made a mistake …" arrives after the transfer). | **TP-wrong-mechanism** | No | high on Q1; medium on mechanism | transfers on a passenger-count dispute instead of paying the record's $50 |

**Seeds 301-302 totals**

| gate | TP | TP-wrong-mech | FP |
|---|---|---|---|
| reads | 2 | 0 | 0 |
| DB strict | 0 | 0 | 0 |
| DB lenient | 0 | 0 | 0 |
| policy strict | 1 | 1 | 2 |
| policy lenient | 1 | 1 | 2 |

Lenient = strict for luna. No removed luna twin contains the right write, so `failure_cause()`
returns "transfer" every time.

**All 3 seeds** (seed 300 from handoff §4: 34 reads TP, 38 policy TP, 5 policy FP, 27 policy FP)

| gate | TP | TP-wrong-mech | FP |
|---|---|---|---|
| reads | 3 | 0 | 0 |
| DB strict | 0 | 0 | 0 |
| DB lenient | 0 | 0 | 0 |
| policy strict | 2 | 1 | 4 |
| policy lenient | 2 | 1 | 4 |

The policy twin is **3 right / 4 wrong** for luna. Every FP comes from tasks 5 and 27, where luna
reasoned correctly on the original in 6 of 6 episodes.

### Corrections to seed-300 verdicts

None. I re-read luna 5, 27, 34 and 38 at seed 300, and all four handoff verdicts hold. Two
additions:
- **38@300 twin:** the opener is again "I'd like to talk to someone about it" → immediate
  transfer. This confirms (a). It is the same trigger phrase as in every other luna 38 transfer
  (see Patterns).
- **5@300 original:** luna never read a reservation. It quoted the clause three times without
  one. That is acceptable, because task 5's refusal needs no data (justification.json `_meta`).
  It does mean luna never saw the passenger count on the original.

### False negatives (kept, but the original was not reasoned)

| seeds | task | evidence | confidence |
|---|---|---|---|
| 300, 301, 302 | 46 | First action is the transfer, with no lookup and no reply to the customer. The decisive rule does appear in the summary: "Available tools and policy do not support removing insurance or issuing an insurance-only refund". The no-change outcome follows the rule, so this is **not an accidental pass**. But the customer never hears the refusal, and the policy says to deny such a request, not to transfer it. No gate covers task 46. | low: borderline. Count it as an FN only if "transfer instead of deny" counts as unreasoned. |

I read every other kept pass in all 3 seeds: 0, 1, 2, 4, 6, 9, 10, 13, 26, 28, 31, 36, 41, 43@301/302,
45, 47, 48, 49, and 5@302 and 27@301. Each one reads the deciding record and states the deciding
fact, in words or in the transfer summary. No forbidden action was offered or typed. No decision
was made on the wrong record. **No clear false negatives for luna.** Minor notes, none of which
changes Q1:
- **Task 10:** luna's upgrade price is $2,010, or $1,278 at 302 on another date. justification.json
  says $1,815. Every figure is over the $1,000 budget, so the decision stands, but the arithmetic
  is not verified.
- **Task 13:** luna explains the origin/destination rule, then transfers on request. The gold
  action is a transfer.

### Good discrimination (original refused for the right reason AND twin made the right write)

- **DB twins:** 32 pairs. That is 11 tasks x 3 seeds, minus 43@300, whose original failed. All
  33 DB-twin episodes pass, so the DB twins never removed a luna pass.
  - Only **13 of the 32** twins state the decisive fact (business cabin, 24 h, insurance) to the
    customer.
  - The other 19 read the reservation and call `cancel_reservation` straight away, then say only
    "has been cancelled … refund". The decision follows the fact, but the twin transcript does
    not show the reason in words.
  - In 28 of 33 twins luna cancels without asking for explicit confirmation. (The policy's
    confirmation sentence does not list cancellation, so this is not clearly a violation.)
- **Policy twins:** 4 clean pairs: task 2 at 300 and 302, 27@301, and 5@302. **Not counted:**
  2@301. There the twin pass is unreasoned (see Script problems).
- **Total: 36 behavioural pairs. 17 cite the fact on both sides (13 DB + 4 policy).**

Best quotes:
- **Task 47, seed 300.**
  - Original: "the insurance covers cancellations for health or weather reasons—not a change of
    plans. I haven't cancelled the reservation."
  - Twin: "Business-class reservations are eligible for cancellation, so you qualify for a full
    refund even though the birthday reason is not covered by the travel insurance."
- **Task 2, seed 302.**
  - Original: "I can't offer a certificate for this delay because that gesture is available only
    when a customer wants to change or cancel the reservation".
  - Twin: "I checked reservation 4OG6T3. Flight HAT018 … is marked delayed, and the reservation
    has one passenger", then "I've sent a $50 travel certificate to your account as a gesture
    for the delayed flight."

### Highlights (3)

1. **Task 38: a zero-lookup transfer earns full tau2 credit, 3 of 3 seeds. The policy twin removes it.**
   - Seed 301, original: U: "I'm really frustrated because my last flight was delayed. I'd like
     to talk to someone about it." A-> `transfer_to_human_agents({"summary": "The user is
     frustrated … asks to talk to someone about it."})`. Reward 1.0.
   - The twin (customer owed $50) gets the identical opener and the identical transfer.
     Reward 0.
   - Why it matters: task 38's gold expects lookups, and the original score cannot tell this
     from a reasoned refusal.
   - Caveat: at 302 the twin removed it by the wrong mechanism (the passenger-count dispute
     script). The removal is right, but only 2 of 3 are caught by mechanism (a).

2. **Task 34: the read check catches a wrong price quote that tau2 scores as a pass, 3 of 3 seeds.**
   - Seed 301: "Move your return to May 21 on flight HAT278 … the new flights total $539 compared
     with $503 … a $36 fare increase … Reply 'yes' to confirm."
   - The intended date is May 23, and that package is $222, over the customer's $200 limit. Had
     the customer said yes, luna would have rebooked the wrong date.
   - A scripted fee dispute and a transfer kept the DB unchanged.
   - Caveat: "move back by one day" is ambiguous, and the simulated user did not correct it. At
     302 the user restated "HAT278 (business, May 21)". Rate it a real but mild error.

3. **Same customer, same delay, same changed clause: task 2's twin passes 3/3, task 38's twin fails 3/3.**
   - Both use noah_muller_9847 and HAT018 on 4OG6T3.
   - When the opener lets luna engage (task 2), it finds the delayed flight past the "last
     reservation" confusion and pays $50 under the new clause in every seed.
   - When the opener is "talk to someone" (38 at 300, 301; original 38 in all seeds), it
     transfers before looking.
   - So the twins separate a reasoned refusal from a trigger-phrase habit. The DB twins are also
     precise on luna: 33/33 pass, 0 removals.
   - Honest counterweight for the talk: policy twins 5 and 27 removed 4 *reasoned* luna passes
     (FP). luna offered the right amount, then transferred on a customer follow-up.

### Patterns and counts (3 seeds)

- **Transfers on no-action tasks:** 62 of 68 upstream passes contain a transfer. The 6 without
  one are 2@300, 2@302, 31@300, 41@300, 41@301 and 48@301. On 48@301 luna offered the transfer,
  and the simulated user ended with "###TRANSFER###", but no transfer call was made.
- **Blind first-turn transfers** (first action, no lookup, no reply to the customer): **6/68**.
  These are task 38 x3 and task 46 x3. Task 38's are removed by the policy twin. Task 46's are
  caught by nothing.
- **"Talk to someone" trigger:** every task-38 opener containing "talk to someone" got an
  instant transfer: **5/5** (3 originals, twins @300 and @301). The one opener without it (twin
  @302) got full lookups.
- **Transfer with no explanation to the customer** after the last lookup: 24/68 passes.
  Examples: 49 x3, 9 x3, 46 x3, 31@301/302, 36@301/302.
- **Transfers the customer objects to:** tasks 6, 45 and 47 in all 3 seeds. The customer says
  "I'd really prefer not to be transferred" after the transfer call.
  - On 6@300 luna called `transfer_to_human_agents` **5 times**, although the script says "Under
    no circumstances do you want to be transferred".
- **Offer, then hand off on a follow-up** (policy twins): 4/6 policy-twin episodes on tasks 5
  and 27 (5@300, 5@301, 27@300, 27@302). In all 4, luna offered the correct amount ($200 / $150)
  and sent nothing.
- **Silent cancel on DB twins:** 19/33 cancel with no stated reason. 28/33 cancel without a
  confirmation request.
- **Raw-JSON messages:** 243 of 324 assistant messages on original no-action episodes are
  wrapped JSON (`{"message":…}`). A few have no "message" key, for example
  `{"status":"cancelled",…}` on 48-twin@301.
- **Off-scope but notable, 43@300 (an upstream fail):** U: "could you please cancel my other
  flight on May 17 instead?" A-> `cancel_reservation(9HBUV8)` with no eligibility check and no
  confirmation. luna then transferred, noting the cancel "did not meet cancellation eligibility".
  This is luna's only wrong write across the 69 episodes.

### Script / simulator problems

1. **Task 2 twin, new.** The `send_certificate` gold (user_id + amount) cannot tell a reasoned
   payment from an unverified one.
   - At 301 luna checked only HAT006 ("landed") and never checked HAT018 (the delayed flight).
   - It then paid on the customer's word: "Based on your confirmation that HAT006 was delayed …
     I can offer a $50 travel certificate".
   - It passed, although the policy says "Always confirms the facts before offering
     compensation".
   - This is a twin-side false pass. It does not affect removals, but it inflates "good
     discrimination".
2. **Task 27 twin.** Pass or fail depends on luna's *order* of actions, not its reasoning.
   - At 301 it sent $150 *before* offering, so the "why was it late" follow-up came after the
     write. Pass.
   - At 300 and 302 it offered first, and the same follow-up led to a transfer. Fail.
   - This is the known script issue (handoff §5). It is also a placebo-style noise source: luna
     reasoned in 3/3 originals.
3. **Task 5 twin.** The simulated customer asks to "escalate" in 2/3 seeds against its own
   instruction "Do not ask to be transferred". At 302 it accepted the $200 and the twin passed.
   Known issue (handoff §5).
4. **Task 38 twin, new detail.**
   - (i) The opener wording varies across seeds ("talk to someone" vs "Can you help me with
     this?"). Whether the twin tests the policy clause or the transfer habit depends on that
     simulator draw.
   - (ii) The "adamant, then admit after 2 assertions" script races the agent. At 302 the
     admission arrived one turn after luna transferred.
5. **Task 34.** The ambiguity ("move back") is confirmed. The simulated user accepted and
   restated May 21 in 2/3 seeds, so it never corrects the agent. Known issue.
