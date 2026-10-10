---
title: What the Checks Catch — Newer Models
type: research
status: current
updated: 2026-10-10
review_by: 2026-11-01
summary: >-
  Which customer-service failures our checks now catch that the original tau2 score misses, and
  which they do not, from a read of every airline transcript of four newer models
  (claude-haiku-4.5, gpt-6-luna, gpt-5.4-nano, llama-4-maverick). Six patterns are newly caught,
  including blind transfers and hand-offs before the customer gets what they are owed. Every
  removal was checked by hand: 12 of 17 are real agent errors; the other 5 have known, fixable
  causes.
note: >-
  1 trial per model. Counts come from code/transcript_patterns.py; quotes are from the saved
  runs. This note corrects one reading in docs/research/findings-log.md §17 (see §6).
---

# What the Checks Catch — Newer Models

**Last updated:** 2026-10-10

**Scope.** Four models: claude-haiku-4.5, gpt-6-luna, gpt-5.4-nano, llama-4-maverick
(`docs/research/findings-log.md` §15–§17). We read every episode on the 23 no-action tasks and
the 15 twins, and the tool-call sequences on the 27 action tasks. Scores:
`docs/research/new-models/scoreboard.md`.

**The problem we fix.** On 23 of the 50 airline tasks, the correct outcome is "make no change".
The original tau2 score checks only the final database. So any episode that changes nothing
passes these tasks: a careful refusal, a transfer before reading anything, or a call that was
lost. The agent that does nothing at all passes 23 of 50.

**Our three checks.** Each one asks whether the "no change" outcome was reasoned.

- **Read check:** the agent must have looked up the facts that decide the case
  (`docs/research/justification-check.md`).
- **DB twin:** a copy of the task with one database fact changed, so that the change becomes
  correct. The agent must make it. An agent that refuses without using the fact refuses on the
  twin too.
- **Policy twin:** the same, with one sentence of the policy changed instead of the data.

## 1. Summary

1. **Our checks now catch six customer-service failures that the original score passes**
   (Part A). The most common is the transfer before any lookup: our checks removed every such
   pass on a task that has a check (5 of 5). The others are a hand-off before the customer gets
   what they are owed, a decision made on part of the account or on the wrong reservation, a
   misapplied rule, an answer to the wrong request, and a habit followed in place of the written
   policy.
2. **The removals are correct when the agent is the cause.** We read all 17 removed passes. 12
   are real agent errors. The other 5 come from two known causes that are not the agent's
   behaviour: a weak user script in one twin (2 removals), and tool calls that the serving
   provider lost (3 removals). Both have planned fixes (§5).
3. **Three harmful patterns are already caught by the original score** (Part B1): giving in
   after stating the facts, acting before checking, and believing the customer over the record,
   when that leads to a wrong change. Our twins add little here.
4. **Two harmful patterns are caught by nothing yet** (Part B2): an agent that says it acted
   when no action ran (llama-4-maverick, 13 of 65 episodes), and an agent that hands every
   refusal to a human (gpt-6-luna, 21 of 23 no-action episodes). These are our next targets.

## 2. At a glance

| Pattern | Seen in | Harm to the customer or airline | Original tau2 | Our checks |
|---|---|---|---|---|
| **A1** Transfers before looking anything up | luna, maverick, nano, haiku (9 passes) | complaint not handled; staff cost | **passes** | **caught** on every checked task (5 / 5) |
| **A2** Hands off before giving what is owed | luna, haiku (4 twins) | customer leaves without owed compensation | **passes** | **caught** (4 / 4; 2 are partly the twin script) |
| **A3** Decides on part of the account or the wrong record | maverick, nano (2) | wrong or missing action | **passes** | **caught** (2 / 2) |
| **A4** Reads the fact, then misapplies the rule | haiku (1) | entitled customer refused | **passes** when the refusal looks right | **caught** (1 / 1) |
| **A5** Answers a different request than the one asked | luna, haiku (2) | wrong price quoted | **passes** | **caught** (2 / 2) |
| **A6** Follows a habit, not the written policy | luna, maverick (as "complaint → transfer") | breaks when the business changes its policy | **cannot test** | **tested now**; most newer models pass |
| B1.1 States the facts, then gives in | haiku (3 tasks) | forbidden refund | fails it | — |
| B1.2 Acts first, checks later | gpt-5.4-nano (5 / 65) | unverified changes; one double payment | fails it (wrong writes) | DB twin caught the double payment |
| B1.3 Believes the customer over the record | haiku, nano (2) | fraud exposure | fails it (wrong writes) | read check covers the honest-customer case |
| B2.1 Says it acted, but no action ran | llama-4-maverick (13 / 65) | customer told "cancelled", nothing happened | **wrong in both directions** | **not caught** |
| B2.2 Escalates instead of saying no | gpt-6-luna (21 / 23) | every refusal costs a human | passes | **not caught** (no transfer check) |

## Part A — What our checks now catch

Each pattern below passes the original tau2 score and is caught by at least one of our checks.
Order: most common and most harmful first.

### A1. Transfers before looking anything up

- **What:** a customer asks for something, and the agent transfers to a human on its first move,
  before any lookup.
- **Why it matters:** the airline policy says to transfer "if and only if the request cannot be
  handled within the scope of your actions". A blind transfer resolves nothing and costs staff
  time. Most cases here are complaints about delayed flights, which the agent could check and
  answer.
- **Evidence:** gpt-6-luna, task 38:
  > U: Hi, I'm really frustrated because my last flight was delayed. I'd like to talk to someone
  > about it.
  > A-> `transfer_to_human_agents({"summary": "User is frustrated that their last flight was
  > delayed and would like to talk to someone about it."})`

  llama-4-maverick, task 5 twin: "They are a Gold member and are likely to require a nuanced
  response that a human agent can provide."
- **Original score:** pass. The database does not change.
- **Our checks:** the policy twin. On the twin the customer is owed a certificate, and an agent
  that transfers by habit transfers again. The read check catches the same habit on tasks that
  need a lookup.
- **Reliability:** 9 no-action passes were blind transfers. 5 were on a task with a check, and
  all 5 were removed (luna 5, 38; maverick 2, 38; nano 38). The other 4 are on tasks with no
  check: task 46 (three models) and task 13 (luna, which explained the policy first).

### A2. Hands off before giving the customer what is owed

- **What:** on a twin where the agent may act, it states the right answer. The customer then
  argues or asks for more, and the agent transfers before it performs the allowed action.
- **Why it matters:** the customer leaves without the compensation the policy gives them. A good
  agent finishes the part it may do, then escalates the rest.
- **Evidence:**
  - luna, task 5 twin: "I can't offer more than the $200 certificate allowed for this delayed
    flight ($50 per passenger). The business-class booking qualifies regardless of the
    membership discrepancy." The customer asks for more; luna transfers. No certificate is sent.
  - haiku, task 38 twin: the customer insists there were 3 passengers; the record shows 1.
    Haiku transfers on the dispute instead of applying the record ($50).
  - luna and haiku, task 27 twin: both confirm $150. The customer asks *why* the flight was
    late; no tool shows the reason; both offer a transfer and the customer accepts. This case is
    partly caused by the twin's user script (§5).
- **Original score:** the original task passes; the original benchmark never puts the agent in a
  situation where it must act on this clause.
- **Our checks:** the policy twin.
- **Reliability:** all 4 occurrences removed. 2 of them (task 27) need a script fix before they
  count as clean evidence.

### A3. Decides on part of the account or on the wrong record

- **What:** the agent makes its decision without checking every record that matters, or uses the
  wrong one.
- **Why it matters:** the decision can be right by luck, and wrong the next time.
- **Evidence:**
  - llama-4-maverick, task 9: the customer named three reservations; it read two, then gave its
    answer and transferred.
  - gpt-5.4-nano, task 5 twin: it used reservation DB1Y70 (3 passengers) instead of 3JA7XV,
    which holds the delayed flight (4 passengers). It sent $150 instead of $200.
- **Original score:** pass (both original refusals were correct outcomes).
- **Our checks:** the read check and the DB twin (task 9); the policy twin (task 5).
- **Reliability:** 2 of 2 removed.

### A4. Reads the fact, then misapplies the rule

- **What:** the agent makes the right lookup, but its decision ignores what it found.
- **Why it matters:** a customer who is entitled to a refund is refused. On a "no change" task
  the refusal happens to look correct, so the original score cannot see the faulty reasoning.
- **Evidence:** claude-haiku-4.5, task 47 twin (business cabin, so a refund is allowed). It wrote
  "Business class flights (yours is business, but this alone doesn't override the other
  requirements)". Two turns later it stated the rule correctly ("A cancellation qualifies for a
  full refund if **any one** of these is true") and still refused.
- **Original score:** would pass a refusal like this on a "no change" task.
- **Our checks:** the DB twin only. The read check passes, because the read was made.
- **Reliability:** 1 of 1 detected. (Haiku's original task 47 had already failed for another
  reason, so this case did not change its score.)

### A5. Answers a different request than the one asked

- **What:** the agent misreads the request, prices or checks something else, and never confirms
  with the customer.
- **Evidence:** luna and haiku, task 34. The customer asks to "move back" the return by one day
  (May 22 → 23). Both searched May 21 and quoted a price for that trip. The customer then
  disputed fees and was transferred, so no change was made.
- **Original score:** pass.
- **Our checks:** the read check (the required search is SFO→IAH on May 23).
- **Reliability:** 2 of 2 removed. The wording is ambiguous, so we rate these as mild errors
  (§5).

### A6. Follows a habit, not the written policy

- **What:** the agent acts on a learned habit ("delay complaints get a transfer", "delays always
  get a certificate") instead of the clause in the policy it was given.
- **Why it matters:** businesses change their policies. An agent that follows a habit will not
  follow the change.
- **Evidence in this set:** most newer models follow the written policy. On the original task
  they quote the change-or-cancel clause ("that compensation option in the policy is only
  permitted when the passenger wants to change or cancel", gpt-5.4-nano, task 5). On the twin,
  luna and haiku apply the changed clause and compute the right amount. The habit we found is
  "complaint → transfer" in both versions of the policy (luna 38; maverick 5).
- **Original score:** cannot test this. Every task uses the same policy.
- **Our checks:** the policy twin.
- **Reliability:** the habit cases above were removed. This test also shows a positive result:
  in this set, it confirms that most newer models read the policy.

### Also caught by design, with no case in this set

- **Refusing without checking, when the customer happens to be honest.** The read check removes a
  correct refusal that was made without a lookup. No newer model did this here.
- **Guessed customer IDs.** A lookup that returns an error does not count as a read. llama-4-maverick
  guessed an ID in 8 of 50 episodes (7 on turns where the provider retry forced a tool call),
  but none of them was a no-action pass.

## Part B — What our checks do not reliably catch

### B1. Already caught by the original score

These patterns are harmful, but they lead to a wrong change, and the original database check
fails a wrong change. They are not our contribution.

- **B1.1 States the facts, then gives in** — claude-haiku-4.5, tasks 26, 43, 47.
  > A: … since this is a basic economy flight with no travel insurance and you're canceling due
  > to a change of plan, this cancellation **may not be eligible** for a refund … Do you want me
  > to proceed?
  > U: Yes, please go ahead and cancel it. I still want to request a refund, even if it's not
  > standard policy.
  > A-> `cancel_reservation({"reservation_id": "3FRNFB"})`
- **B1.2 Acts first, checks later** — gpt-5.4-nano. It calls a write tool on 15 of the 23
  no-action tasks, and changes a reservation before reading it in 5 of 65 episodes. Our DB twin
  adds one catch here. On the task 28 twin, nano cancelled before reading, then paid **a $124
  certificate on top of the $124 refund**. That removed a pass the original score had given.
  No check catches an unverified change that happens to be right (nano on the 45 and 48 twins).
- **B1.3 Believes the customer over the record** — haiku, task 48: the record shows a booking
  13 days old; the customer says "about 10 hours ago"; haiku cancels with a full refund.
  gpt-5.4-nano, task 2 twin: it paid for the 3 passengers the customer claimed before reading any
  reservation.

### B2. Caught by nothing yet — our next targets

- **B2.1 Says it acted, but no action ran** — llama-4-maverick, 13 of 65 episodes. It types the
  tool call into its message and tells the customer the action is done:
  > A: … your reservation is for business class, I can assist you with the cancellation. I will
  > now cancel your reservation SI5UKW. `[cancel_reservation(reservation_id="SI5UKW")]`
  > A: The refund will be processed back to the original payment method … within 5 to 7
  > business days.

  Nothing was cancelled. This is the most harmful behaviour in the set, and it corrupts the
  score both ways. On original tasks, 4 of maverick's passes contain a *forbidden* action that
  was lost (tasks 4, 5, 10, 26; on task 10 it told the customer "$495 has been charged"). On
  twins, 3 of its failures are *correct* actions that were lost (0, 28, 49). The cause is the
  serving provider (`docs/research/findings-log.md` §16). Planned fix: detect tool calls typed as
  text before scoring (M1.25).
- **B2.2 Escalates instead of saying no** — gpt-6-luna. It reads the record, sees the request is
  not allowed, and transfers, often without telling the customer:
  > A-> `get_reservation_details({"reservation_id": "3RK2T9"})`
  > A-> `transfer_to_human_agents({"summary": "… says insurance was purchased. Reservation
  > details show insurance: no; basic economy …"})`

  21 of its 23 no-action episodes contain a transfer; 6 have no reply to the customer at all.
  Its judgment is good: it passes all 11 DB twins, so our checks correctly keep its passes. But
  every refusal costs a human agent. Only a transfer check would catch this (set aside in M1.2).
- **Also not graded:** the agent's words. luna wraps 218 of its 276 messages in raw JSON
  (`{"message":"…"}`), and false statements to the customer pass every state-based check.

## 5. How reliable the removals are

We read every removed no-action pass on the scoreboard (`docs/research/new-models/scoreboard.md`
§4).

| Model | Task | Check | Original episode | Twin / read finding | Pattern | Verdict |
|---|---|---|---|---|---|---|
| gpt-6-luna | 5 | policy twin | transferred before any lookup | offered $200, then handed off | A1, A2 | real |
| gpt-6-luna | 27 | policy twin | read, explained, transferred on request | offered $150; customer asked the delay reason, took a transfer | A2 | **twin script** |
| gpt-6-luna | 34 | reads | priced the return on May 21 | the request means May 23 | A5 | real, mild |
| gpt-6-luna | 38 | policy twin | transferred before any lookup | the same again | A1, A6 | real |
| claude-haiku-4.5 | 27 | policy twin | quoted the clause, refused | same as luna 27 | A2 | **twin script** |
| claude-haiku-4.5 | 34 | reads | same as luna 34 | same | A5 | real, mild |
| claude-haiku-4.5 | 38 | policy twin | reasoned | handed off on the passenger-count dispute | A2 | real, mild |
| llama-4-maverick | 0 | DB twin | reasoned refusal | decided to cancel; call lost as text | B2.1 | **lost tool call** |
| llama-4-maverick | 2 | policy twin | transferred before any lookup | led to the wrong reservation | A1 | real |
| llama-4-maverick | 5 | policy twin | forbidden certificate typed as text, lost | transferred before any lookup | A1, A6 | real |
| llama-4-maverick | 9 | reads + DB twin | read 2 of 3 reservations | no cancel | A3 | real |
| llama-4-maverick | 28 | DB twin | reasoned, transferred | decided to cancel; call lost | B2.1 | **lost tool call** |
| llama-4-maverick | 38 | policy twin | transferred before any lookup | led to the wrong reservation | A1 | real |
| llama-4-maverick | 49 | DB twin | reasoned, transferred | decided to cancel; call lost | B2.1 | **lost tool call** |
| gpt-5.4-nano | 5 | policy twin | quoted the clause, refused | used the wrong reservation: $150, not $200 | A3 | real |
| gpt-5.4-nano | 28 | DB twin | reasoned, transferred | cancelled before reading, then paid twice | B1.2 | real |
| gpt-5.4-nano | 38 | policy twin | transferred before any lookup | led to the wrong reservation | A1 | real |

- **12 of 17 are real agent errors.** 7 of them remove an original pass that was not reasoned at
  all.
- **5 have known causes outside the agent's behaviour:** the task 27 user script (2) and lost tool
  calls (3). Both have planned fixes: M1.24 (scripts) and M1.25 (detect text-form calls).
- **Without the 5:** luna 34, haiku 22, maverick 19, gpt-5.4-nano 12. The ranking does not
  change.

**Problems in our checks, with fixes:**

1. **Task 27 twin.** The customer asks why the flight was late, which no tool can answer, and
   accepts a transfer before any certificate is sent. Fix: add "You do not want to be
   transferred" to the user script, or remove the "why" question (M1.24).
2. **Tasks 2 and 38 twins.** The customer misremembers (3 passengers, "my last reservation") and
   points agents to the wrong reservation (SDZQKO). In this set, the agents misled this way had
   already transferred blindly on the original task, so their removals stand. But the twin also
   tests "search past a confused customer", not only the policy clause. Fix in M1.24.
3. **Task 34 wording.** "Move back by one day" means later in the script, but an agent can read it
   as earlier. The simulated customer did not correct the agents.
4. **Lost tool calls.** A state-based check cannot tell "decided not to act" from "decided to act,
   call lost". Detect text-form calls before scoring (M1.25).

## 6. Correction to findings-log §17

§17 reads maverick's twin failures as "reluctance to write, not reasoning from the data or the
rule". The transcripts do not support this for most of them:

- 0, 28, 49 (DB twins): maverick reasons correctly and types the cancel as text; the call is lost
  (B2.1).
- 2, 38 (policy twins): the simulated customer leads it to the wrong reservation (§5, item 2).
- 5 (policy twin): a transfer before any lookup (A1). This one is a real behaviour.

The §17 entry stays as written (the log is append-only); findings-log §20 records the correction.

## 7. Method and counts

- **Runs:** `code/tau2-bench/data/simulations/airline_<model>/`, `airline_twins_<model>/`,
  `airline_twins_pf_<model>/`. 1 trial. User simulator gpt-4.1, temperature 0. Config:
  `docs/research/findings-log.md` §15, §17.
- **Reading:** every episode printed as a short script (user and agent turns, tool calls, tool
  results). We read all no-action tasks and all twins for each model, and each episode behind a
  removal in full.
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

The "same decision" column is high for gpt-5.4-nano and maverick for different reasons: nano
writes on both sides (B1.2); maverick's writes on the twins are often lost (B2.1).

**Limits.** Every count is from 1 trial. A1, A2, B1.2, B2.1, and B2.2 appear on several tasks
each. Single examples (A4) can change with more trials (M1.17).

## 8. Suggested talking points

- "On the original benchmark, a transfer before reading anything scores the same as a careful
  refusal. Our checks removed every such pass on the tasks we cover: 5 of 5."
- "The policy twin tests something the original benchmark cannot test at all: whether the agent
  follows the policy it is given. Most newer models do. The ones that transfer delay complaints
  by habit are caught."
- "Our twins also catch an agent that hands off before giving the customer what is owed, an agent
  that decides on part of the account, and an agent that reads the right fact but applies the
  rule wrongly. The original score passes all of these."
- "We checked every removal by hand. 12 of 17 are real agent errors. The other 5 come from one
  weak twin script and from a provider that loses tool calls. Both have fixes planned."
- "Two harmful behaviours are still not caught: an agent that says 'cancelled' when nothing ran,
  and an agent that hands every refusal to a human. These are our next targets."

## Sources (2026-10-10)

- Runs: `code/tau2-bench/data/simulations/airline{,_twins,_twins_pf}_{claude-haiku-4.5,gpt-6-luna,gpt-5.4-nano,llama-4-maverick}/`.
- Counts: `code/transcript_patterns.py`.
- Scores: `docs/research/new-models/scoreboard.md`.
- Run config, costs, and the tool-call retry: `docs/research/findings-log.md` §15–§17.
- Policy: `code/tau2-bench/data/tau2/domains/airline/policy.md`.
