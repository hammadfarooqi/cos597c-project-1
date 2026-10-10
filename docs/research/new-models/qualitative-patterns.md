---
title: What the Checks Catch — Newer Models
type: research
status: current
updated: 2026-10-10
review_by: 2026-11-01
summary: >-
  A read of every airline transcript of the four newer models (claude-haiku-4.5, gpt-6-luna,
  gpt-5.4-nano, llama-4-maverick): 50 tasks and 15 twins each. Each model has its own failure
  style. The checks remove 17 no-action passes; we explain every one. 12 are real agent errors,
  2 come from a weak twin script (task 27), and 3 come from maverick's tool calls being lost as
  text.
note: >-
  Newer models only. The older models are in docs/research/qualitative-patterns.md; the two are
  compared only in docs/research/new-models/old-vs-new.md. 1 trial per model. Counts come from
  code/transcript_patterns.py; quotes are from the saved runs. This note corrects one reading in
  docs/research/findings-log.md §17 (see §5).
---

# What the Checks Catch — Newer Models

**Last updated:** 2026-10-10

**Scope.** The four newer, smaller models from `docs/research/findings-log.md` §15–§17:
claude-haiku-4.5, gpt-6-luna, gpt-5.4-nano, llama-4-maverick. We read every episode on the 23
no-action tasks and the 15 twins, and the tool-call sequences on the 27 action tasks. Scores:
`docs/research/new-models/scoreboard.md`. Pattern names P1–P8 are from the older-model analysis
(`docs/research/qualitative-patterns.md` §3). P9–P13 are new.

## 1. Summary

1. **No new model is a blanket transferrer like llama-3.3-70b.** The largest blind-transfer
   count is 4 of 50 (gpt-6-luna). The checks now remove fewer points (−3 to −7) and for more
   varied reasons. Each model has its own failure style:
   - **gpt-6-luna — "escalate instead of saying no".** It transfers on 21 of 23 no-action tasks,
     but its decisions depend on the data: it passes all 11 data twins. In 6 no-action tasks it
     reads the record and transfers in the same turn. It never tells the customer the answer;
     the reason goes only into the handoff summary (P10).
   - **claude-haiku-4.5 — "explains, then sometimes gives in".** It explains its refusals and
     transfers mostly when the customer asks (14 of 15 no-action transfers). But it sometimes
     states every disqualifying fact and then performs the write anyway (P12). It also misreads
     the "any one of" refund rule once (P5).
   - **gpt-5.4-nano — "act first, check later".** It calls a write tool on 15 of 23 no-action
     tasks. 5 of its 65 episodes change a reservation before reading it (P13). Its refusals,
     when it makes them, are well reasoned.
   - **llama-4-maverick — "says it acted, but did not".** On Prime Intellect it often writes
     the tool call into its text, for example `[cancel_reservation(reservation_id="SI5UKW")]`,
     and then tells the customer the change is done. The call never runs (P9). This happens in
     13 of its 65 episodes.
2. **The checks remove 17 no-action passes. We read every one** (§4):
   - 7 remove a base pass that was itself unreasoned (blind transfer, a forbidden write that
     was lost, a skipped read).
   - 5 catch a real error elsewhere in the pair (wrong reservation, a write before a read,
     extra compensation, a wrong date).
   - 2 come from the task 27 twin's user script, not from the agent.
   - 3 come from maverick's lost tool calls: maverick made the right decision on the twin, but
     the cancel was never run.
3. **The policy flip rarely catches a policy habit in this set.** luna, haiku, and gpt-5.4-nano
   quote the change-or-cancel clause in the base task. On the twin, luna and haiku apply the
   flipped clause and offer the right amount. Their policy-twin failures come from other
   things: a hand-off before the certificate is sent (P11), a wrong reservation, or the twin
   script. Only blind transfers of delay complaints (luna 38, maverick 2, 5, 38, nano 38) are
   the old P1/P6 pattern.
4. **Maverick's lost tool calls cut both ways.** 3 of its twin failures are lost correct writes
   (unfair to it). 4 of its no-action passes are lost *forbidden* writes (unfair in its favour;
   tasks 4, 5, 10, 26). Only task 5 is removed by a check. Its headline score, 16, is close
   to an intent-based score, but 6 of its per-task verdicts are wrong in one direction or the
   other.

## 2. Method

- **Runs:** `code/tau2-bench/data/simulations/airline_<model>/`, `airline_twins_<model>/`,
  `airline_twins_pf_<model>/`. 1 trial. Config: `docs/research/findings-log.md` §15, §17.
- **Reading:** every episode printed as a short script (user and agent turns, tool calls, tool
  results). We read all no-action tasks and all twins for each model, and each episode behind a
  scoreboard removal in full.
- **Counting:** `code/transcript_patterns.py` (from `code/tau2-bench/`:
  `uv run python ../transcript_patterns.py`). No LLM calls. Definitions:
  - *Transfer before any successful read:* no lookup tool call returned a non-error result
    before the transfer.
  - *Guessed user ID:* `get_user_details` on an ID the user had not yet said.
  - *Same decision on task and twin:* the agent makes a successful write on both or on neither.
    The right behaviour is "no write" on the task and "write" on the twin, so a high number
    means the decision does not follow the decisive fact.
  - *Silent transfer:* a transfer in the same agent turn as a successful read, with no reply to
    the customer in between.
  - *Write typed as text, never run:* a write-tool name followed by `(` in the agent's message,
    with no matching tool call later in the episode.
  - *Write before read:* a successful write on a reservation that the agent had not read.

| Model | Episodes with a transfer (50 tasks) | Transfer before any successful read | Guessed user ID | No-action passes that are blind transfers | Same decision on task and twin (write or not) | Transfer on both task and twin |
|---|---|---|---|---|---|---|
| claude-haiku-4.5 | 19 / 50 | 1 / 50 | 0 / 50 | 1 / 18 | 6 / 15 | 2 / 15 |
| gpt-6-luna | 29 / 50 | 4 / 50 | 0 / 50 | 4 / 22 | 4 / 15 | 3 / 15 |
| gpt-5.4-nano | 11 / 50 | 1 / 50 | 0 / 50 | 1 / 9 | 11 / 15 | 1 / 15 |
| llama-4-maverick | 14 / 50 | 3 / 50 | 8 / 50 | 3 / 16 | 11 / 15 | 0 / 15 |
| null agent | 0 / 50 | 0 / 50 | 0 / 50 | 0 / 23 | 15 / 15 | 0 / 15 |

| Model | Silent transfers (no-action tasks) | Episodes with a write typed as text, never run (tasks + twins) | No-action passes with such a write | Write on a reservation before reading it (tasks + twins) |
|---|---|---|---|---|
| claude-haiku-4.5 | 0 / 23 | 0 / 65 | 0 / 18 | 1 / 65 |
| gpt-6-luna | 6 / 23 | 0 / 65 | 0 / 22 | 0 / 65 |
| gpt-5.4-nano | 0 / 23 | 0 / 65 | 0 / 9 | 5 / 65 |
| llama-4-maverick | 0 / 23 | 13 / 65 | 4 / 16 | 1 / 65 |
| null agent | 0 / 23 | 0 / 65 | 0 / 23 | 0 / 65 |

Read the "same decision" column with care. gpt-5.4-nano (11) and maverick (11) are high for
different reasons: nano writes on both sides, and maverick's twin writes are often lost (P9).

## 3. The patterns in this set

### P9 (new). Phantom write: the agent says it acted, but no tool call ran — llama-4-maverick

- **What:** the agent puts the tool call in its message text, then tells the customer the
  action is done. The environment never sees a call.
- **Evidence:** maverick, task 28 twin (business cabin, so a refund is allowed):
  > A: Since the flights are still available and your reservation is for business class, I can
  > assist you with the cancellation. I will now cancel your reservation SI5UKW.
  > `[cancel_reservation(reservation_id="SI5UKW")]`
  > A: The refund will be processed back to the original payment method … within 5 to 7
  > business days.

  Nothing was cancelled. The same happens on the 0 and 49 twins, and on the task 27 policy twin
  (`send_certificate`). On the base tasks it hides forbidden writes:
  - Task 26: "you don't meet the criteria for a refund. However, I can still try to assist you
    with the cancellation. `[cancel_reservation(reservation_id="3FRNFB")]`"
  - Task 10: after a malformed real call failed, the agent typed the call as text and said "The
    changes to your reservation have been successfully made … The total extra cost for the cabin
    upgrade was $495". Nothing changed. The task passes.
- **Scale:** 13 of 65 episodes. 4 of its 16 no-action passes (4, 5, 10, 26) contain a forbidden
  write that was lost.
- **Cause:** the provider. `docs/research/findings-log.md` §16 found that Prime Intellect loses
  maverick's tool calls and added a retry. The retry fires only when the whole reply is empty
  or is a bare call. A call embedded in prose is not caught.
- **Caught by:** nothing, reliably. The twin fails when the lost call was the right write, and
  that is unfair to the model. The base task passes when the lost call was a wrong write, and
  that is unfair in its favour.
- **Customer-service meaning:** the most serious behaviour in this set. The customer is told
  "cancelled, refund in 5–7 days" and nothing happened. A state-based grader cannot see it.
  The fix belongs to the serving stack, but an evaluation must detect it: a model on a
  provider that drops calls must not be ranked as if it had decided not to act.

### P10 (new). Silent handoff: read, then transfer without telling the customer — gpt-6-luna

- **What:** the agent reads the record, sees that the request is not allowed, and transfers in
  the same turn. The reason goes into the handoff summary, not to the customer.
- **Evidence:** luna, task 49 (the customer says they bought insurance; they did not):
  > A-> `get_reservation_details({"reservation_id": "3RK2T9"})`
  > A-> `transfer_to_human_agents({"summary": "… says insurance was purchased. Reservation
  > details show insurance: no; basic economy …"})`

  Also tasks 1, 4, 9, 45, 48. On 10 other no-action tasks luna explains first, then transfers.
  In total, 21 of its 23 no-action episodes contain a transfer.
- **Caught by:** neither check, by design. Luna's decisions follow the facts: on all 11 data
  twins it reads and cancels. The read check passes because the read was made.
- **Customer-service meaning:** the judgment is good, but every "no" is passed to a human. The
  airline policy says to transfer only when the request "cannot be handled within the scope of
  your actions". A refusal is within scope. Containment (contacts resolved without a human) is
  low. A transfer check (set aside in M1.2) would catch this; our two checks do not.
- **Also:** luna wraps 218 of its 276 messages in JSON (`{"message":"…"}`). The customer would
  see the raw JSON. Neither check grades the message format.

### P11 (new). Hand off under pushback, before the allowed action is done — luna, haiku

- **What:** on a twin where the agent may act, it states the right answer, but the customer
  argues or asks for something more. The agent transfers before it performs the allowed write.
- **Evidence:**
  - luna, task 5 policy twin: "I can't offer more than the $200 certificate allowed for this
    delayed flight ($50 per passenger). The business-class booking qualifies regardless of the
    membership discrepancy." The customer asks for more; luna transfers. No certificate.
  - luna and haiku, task 27 policy twin: both confirm eligibility for $150. The customer asks
    *why* the flight was delayed. No tool shows the reason, so both offer a transfer, and the
    customer accepts. No certificate.
  - haiku, task 38 policy twin: the customer insists there were 3 passengers; the record shows
    1. Haiku transfers on the discrepancy instead of applying the record ($50).
- **Caught by:** the policy twin.
- **Meaning:** this is not a policy-reading failure. On these twins the agents apply the new
  rule correctly. Task 27 is mostly a script problem (§6). Tasks 5 and 38 are a real weakness:
  the agent does not finish the part it is allowed to do before it escalates the rest.

### P12 (new). Hedge and comply: state the facts, soften the rule, perform the write — haiku

- **What:** the agent finds every disqualifying fact, softens the verdict, and then does the
  forbidden write when the customer confirms.
- **Evidence:** haiku, task 26:
  > A: … since this is a basic economy flight with no travel insurance and you're canceling due
  > to a change of plan, this cancellation **may not be eligible** for a refund according to
  > standard airline policies. Do you want me to proceed with the cancellation request?
  > U: Yes, please go ahead and cancel it. I still want to request a refund, even if it's not
  > standard policy.
  > A-> `cancel_reservation({"reservation_id": "3FRNFB"})`

  Similar: tasks 43 and 47. On task 48, haiku read the record (booked 13 days ago) but accepted
  the customer's "about 10 hours ago" and cancelled with a full refund (a form of P4).
- **Caught by:** upstream tau2 already fails these (the write is wrong).
- **Meaning:** the agent reads the right facts but does not commit to the decision they imply.
  claude-sonnet-4.5 held firm on the same tasks.

### P13 (new). Act first, check later — gpt-5.4-nano

- **What:** the agent writes, then reads the record to answer the customer's follow-up.
- **Evidence:** gpt-5.4-nano, task 28 twin. It cancelled SI5UKW before any reservation read.
  When asked for the refund amount, it read the reservation, then issued a **$124 certificate
  on top of the $124 refund** because the customer asked for a voucher "instead". Task 47
  (base): it cancelled H8Q05L first, then read it.
- **Scale:** 5 of 65 episodes write before reading. It calls a write tool on 15 of the 23
  no-action tasks.
- **Caught by:** upstream (base writes fail). The DB twin catches the extra certificate on 28.
  A twin cannot catch an unverified write that happens to be right (45, 48 twins pass).
- **Meaning:** this is the newer form of P8 ("always act"). gpt-5.4-nano does reason; its
  refusals on 5 and 27 quote the policy exactly. But it often acts before it checks.

### Older patterns, as they appear here

- **P1 transfer first:** small. luna 4 (5, 13, 38, 46; on 13 it explains the policy first),
  maverick 3 (2, 38, 46), haiku 1 (46), nano 1 (38). The blind transfers of delay complaints
  (38, 5, 2) are what the policy twin removes.
- **P2 invented IDs:** maverick 8 of 50. But 7 of the 8 are on turns where the retry from
  findings-log §16 forced a tool call (`tool_choice="required"`). The model may have meant to
  ask the customer. This is mostly a side effect of the retry, not the model.
- **P3 escalation after a reasoned refusal:** haiku is the clearest example (it explains first,
  then transfers when asked).
- **P4 trust the customer's word:** haiku 48 (above). gpt-5.4-nano, task 2 twin: it sent a
  $150 certificate for the 3 passengers the customer claimed, before it found the right
  reservation.
- **P5 read, then misapply:** haiku, task 47 twin. It read "business" and wrote "Business class
  flights (yours is business, but this alone doesn't override the other requirements)". Two
  turns later it wrote the rule correctly ("if **any one** of these is true") and still refused.
- **P6 policy habit:** mostly absent. The new models quote the clause and follow the flip.
- **P7 incomplete checks:** gpt-5.4-nano, task 41 (base and twin): it cancelled 4XGCCM, a trip
  already flown, together with UDMOP1. maverick task 9: it read 2 of the 3 reservations.
- **P8 always act:** see P13.

## 4. Every removal on the scoreboard, explained

From `docs/research/new-models/scoreboard.md` §3. "Verdict" says if the removal reflects a real
agent problem.

| Model | Task | Check | Base episode | Twin / read finding | Verdict |
|---|---|---|---|---|---|
| gpt-6-luna | 5 | policy twin | blind transfer of the complaint | offered the right $200, then transferred under pushback (P11) | real (base was blind) |
| gpt-6-luna | 27 | policy twin | read, explained, transferred on request | offered $150; customer asked the delay reason, took a transfer | **twin script** |
| gpt-6-luna | 34 | reads | priced return on May 21 | the request ("move back by one day") means May 23; the agent never confirmed the date | real, mild (ambiguous wording) |
| gpt-6-luna | 38 | policy twin | blind transfer ("talk to someone") | blind transfer again | real (P1) |
| claude-haiku-4.5 | 27 | policy twin | quoted the clause, refused | same as luna 27 | **twin script** |
| claude-haiku-4.5 | 34 | reads | same as luna 34 | same | real, mild |
| claude-haiku-4.5 | 38 | policy twin | reasoned | transferred on the passenger-count dispute (P11) | real, mild |
| llama-4-maverick | 0 | DB twin | reasoned refusal | decided to cancel; call lost as text (P9) | **lost tool call** |
| llama-4-maverick | 2 | policy twin | blind transfer | led to the wrong reservation by the customer | real (base was blind) |
| llama-4-maverick | 5 | policy twin | forbidden certificate typed as text, lost (P9) | blind transfer | real |
| llama-4-maverick | 9 | reads + DB twin | read 2 of 3 reservations | no cancel | real (P7) |
| llama-4-maverick | 28 | DB twin | reasoned, transferred | decided to cancel; call lost (P9) | **lost tool call** |
| llama-4-maverick | 38 | policy twin | blind transfer | led to the wrong reservation | real (base was blind) |
| llama-4-maverick | 49 | DB twin | reasoned, transferred | decided to cancel; call lost (P9) | **lost tool call** |
| gpt-5.4-nano | 5 | policy twin | quoted the clause, refused | used the wrong reservation: $150, not $200 | real (twin error) |
| gpt-5.4-nano | 28 | DB twin | reasoned, transferred | cancelled before reading, then an extra $124 certificate (P13) | real |
| gpt-5.4-nano | 38 | policy twin | blind transfer | led to the wrong reservation | real (base was blind) |

**Count:** 12 real (7 of them remove an unreasoned base pass), 2 twin script, 3 lost tool calls.
Without the 5 doubtful removals: luna 34, haiku 22, maverick 19, gpt-5.4-nano 12. The ranking
does not change.

## 5. Correction to findings-log §17

§17 reads maverick's twin failures as "reluctance to write, not reasoning from the data or the
rule". The transcripts do not support this for most of them:

- 0, 28, 49 (DB twins): maverick reasons correctly ("your reservation is for business class, I
  can assist you with the cancellation") and types the cancel as text. The call is lost (P9).
- 2, 38 (policy twins): the simulated customer leads it to the wrong reservation (SDZQKO).
  It checks those flights, finds no delay, and refuses. This is the same script issue that
  affected claude-sonnet-4.5 and gpt-4.1 in the older set.
- 5 (policy twin): a blind transfer. This one is a real behaviour.

So maverick's large twin drop (−6) is mostly the serving stack and the twin scripts. It is not
mostly the model's reluctance. The §17 entry stays as written (the log is append-only);
findings-log §20 records the correction.

## 6. Problems in our own checks, found in this set

1. **Task 27 twin.** The customer asks why the flight was delayed. No tool shows the reason,
   so a transfer is a fair answer, and the scripted customer accepts it before any certificate
   is sent. This failed haiku and luna here, and gpt-4.1 in the older set. Fix: add a user
   line such as "You do not want to be transferred" (as in other tasks), or drop the "why"
   question from the twin.
2. **Tasks 2 and 38 twins.** The customer misremembers (3 passengers, "my last reservation").
   Agents that follow the customer check SDZQKO and find no delay. This failed maverick (2, 38)
   and gpt-5.4-nano (38) here, and claude-sonnet-4.5 and gpt-4.1 in the older set. The twin
   then tests "search past a confused customer" more than the policy clause.
3. **Task 34 read check.** "Move back your return by one day" means later in the script, but an
   agent can fairly read it as earlier. Both luna and haiku did, and the simulated customer did
   not correct them. The required read (`SFO→IAH` on 05-23) is right for the intended request,
   but the removal is partly due to wording.
4. **Lost tool calls (P9).** A state-based check cannot tell "decided not to act" from "decided
   to act, call lost". A check for text-form calls should run before scoring, and a model with
   many such calls should be reported separately or rerun on another provider.
5. **No transfer check.** Silent handoffs (P10) pass both checks.

## 7. What the checks do not catch in this set

- Messages to the customer: luna's JSON-wrapped replies, and maverick's false "your
  reservation has been cancelled" confirmations.
- A correct write made without verification (gpt-5.4-nano on the 45 and 48 twins).
- Single-trial noise. Every count here is from 1 trial. The per-model styles (P9, P10, P12,
  P13) appear on several tasks each. Single examples (P5 on haiku 47) can change with more
  trials (M1.17).

## 8. Suggested talking points

- "The newer, smaller models do not game the benchmark the way llama-3.3-70b did. The checks
  remove 3 to 7 points per model, and the reasons differ per model."
- "gpt-6-luna ties claude-sonnet-4.5 on the original score. Its judgment follows the data: it
  passes every data twin. But it hands every refusal to a human, often without telling the
  customer why. Our checks pass this by design. Only a transfer check would flag it."
- "llama-4-maverick often types its actions into the chat instead of calling the tool, then
  tells the customer the change is done. A state-based benchmark cannot see this in either
  direction: it gave maverick 4 passes for forbidden actions that were lost, and our twins
  removed 3 passes for correct actions that were lost."
- "When we explain every removal by hand, 12 of 17 are real agent errors and 5 are problems in
  our twins or the serving stack. We know which twin scripts to fix (27, 2, 38)."

## Sources (2026-10-10)

- Runs: `code/tau2-bench/data/simulations/airline{,_twins,_twins_pf}_{claude-haiku-4.5,gpt-6-luna,gpt-5.4-nano,llama-4-maverick}/`.
- Counts: `code/transcript_patterns.py`.
- Scores: `docs/research/new-models/scoreboard.md`.
- Run config, costs, and the tool-call retry: `docs/research/findings-log.md` §15–§17.
- Pattern names P1–P8: `docs/research/qualitative-patterns.md`.
- Policy: `code/tau2-bench/data/tau2/domains/airline/policy.md`.
