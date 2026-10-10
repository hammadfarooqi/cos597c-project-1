---
title: What the Checks Catch — Behaviour Patterns in the Transcripts
type: research
status: current
updated: 2026-10-09
review_by: 2026-11-01
summary: >-
  A read of every airline transcript (5 models, 50 tasks, 15 twins) to find the agent behaviours
  behind the scoreboard numbers. Llama's −16 is a "transfer first" habit: it transfers before any
  successful lookup in 41 of 50 tasks, and tau2 scores that as a correct refusal. Each check
  catches a different customer-service failure; this note names them, with transcript evidence.
note: >-
  1 trial per model. The patterns are clear, but the per-model counts can move with more trials
  (M1.17). Counts come from code/transcript_patterns.py; quotes are from the saved runs.
---

# What the Checks Catch — Behaviour Patterns in the Transcripts

**Last updated:** 2026-10-09

**Why this note exists.** Our TA asked for a qualitative account: what the checks catch in
customer-service terms, and why Llama loses 16 points while gpt-4.1-mini loses 1. We read the
transcripts of all 5 models on the 23 no-action tasks, their 15 twins, and the 27 action tasks.

## 1. Summary

1. **Llama "passes" by transferring every customer to a human.** It calls
   `transfer_to_human_agents` in 48 of 50 tasks. In 41 of them it does so before any successful
   lookup. tau2 ends the episode on a transfer, the database does not change, and a no-action
   task scores a pass. So 15 of Llama's 19 no-action passes are blind transfers. In a call centre
   this agent resolves almost nothing.
2. **Llama does not ask for the customer's ID. It guesses one.** In 32 of 50 tasks it calls
   `get_user_details` with an ID that the user never gave. It uses `"user_id"`, `"<user_id>"`,
   `"unknown"`, `"your_id"`, or `"sara_doe_496"`. The last one is the example in the tool's
   docstring. The lookup fails, and Llama transfers.
3. **The same action can have two different causes, and only the twin separates them.** Claude
   also transfers on 12 tasks. But Claude always reads the reservation first, refuses with the
   policy reason, and transfers only when the customer asks for it. On the twins, where the
   action is allowed, Claude acts. Llama transfers again. Llama's outcome is the same on the task
   and its twin in 14 of 15 pairs; Claude's is the same in 4 of 15.
4. **The read check catches "trust the customer's word".** gpt-4.1 refused task 28 correctly,
   but it never opened the reservation. It asked the customer if the ticket was business class
   and if they had insurance. On tasks 48 and 49 the same habit fails: the customer's claims are
   false, and gpt-4.1 cancels with no lookup. tau2 rewards the habit when the customer is
   honest. The read check makes the score consistent.
5. **The twin catches "read the fact, then ignore it".** gpt-4.1-mini opened the twin
   reservation for task 28, saw "business", and still applied the economy rules. A read check
   cannot see this; the twin can.
6. **The policy-flip twin catches "follow a habit, not the written policy".** On the delay
   tasks, Claude quotes the clause ("only if you're canceling or changing") and then follows the
   flipped clause in the twin. gpt-4.1 and gpt-4.1-mini offer a certificate in both worlds. Llama
   transfers in both worlds. A business changes its policy text; this check shows which agents
   would follow the change.
7. **The original score is asymmetric; the twins make it symmetric.** An "always refuse /
   transfer" habit earns 46% (null agent) or 38% (Llama). An "always act" habit (gpt-4.1-nano)
   earns 6%. With twins, both habits fail one side of each pair.

## 2. Method

- **Runs:** `code/tau2-bench/data/simulations/airline_<model>/`,
  `airline_twins_<model>/`, `airline_twins_pf_<model>/` for claude-sonnet-4.5, gpt-4.1,
  gpt-4.1-mini, gpt-4.1-nano, llama-3.3-70b, and the null agent. 1 trial each. These are the runs
  behind `docs/research/scoreboard.md`.
- **Reading:** we printed every episode as a short script (user turns, agent turns, tool calls,
  tool results), and read all 23 no-action tasks and all twins for every model. For the action
  tasks we read the tool-call sequences.
- **Counting:** `code/transcript_patterns.py` (from `code/tau2-bench/`:
  `uv run python ../transcript_patterns.py`). No LLM calls. Its definitions:
  - *Transfer before any successful read:* a `transfer_to_human_agents` call with no earlier
    lookup tool call that returned a non-error result.
  - *Guessed user ID:* a `get_user_details` call on an ID that does not yet occur in the user's
    messages.
  - *Outcome:* `write` (a successful write tool call), else `transfer`, else `none`. A pair has
    the "same outcome" when the task and its twin get the same label.

| Model | Episodes with a transfer (50 tasks) | Transfer before any successful read | Guessed user ID | No-action passes that are blind transfers | Same outcome on task and twin | Transfer on both task and twin |
|---|---|---|---|---|---|---|
| claude-sonnet-4.5 | 12 / 50 | 0 / 50 | 0 / 50 | 0 / 20 | 4 / 15 | 0 / 15 |
| null agent | 0 / 50 | 0 / 50 | 0 / 50 | 0 / 23 | 15 / 15 | 0 / 15 |
| gpt-4.1 | 11 / 50 | 2 / 50 | 0 / 50 | 2 / 16 | 7 / 15 | 0 / 15 |
| gpt-4.1-mini | 11 / 50 | 1 / 50 | 1 / 50 | 1 / 13 | 8 / 15 | 1 / 15 |
| gpt-4.1-nano | 2 / 50 | 0 / 50 | 3 / 50 | 0 / 1 | 13 / 15 | 0 / 15 |
| llama-3.3-70b | 48 / 50 | 41 / 50 | 32 / 50 | 15 / 19 | 14 / 15 | 11 / 15 |

"Same outcome on task and twin" is a simple test of whether the agent uses the decisive fact. An
agent that uses it should act differently when the fact changes. A high number means the outcome
does not depend on the fact. The null agent (always none), Llama (mostly transfer), and
gpt-4.1-nano (mostly write) are all high. Claude is lowest.

## 3. The patterns

Each pattern gives: what the agent does, which check catches it, the evidence, and what it means
for a deployed customer-service agent.

### P1. Transfer first ("escalation as the default")

- **What:** the agent transfers before it has looked at the customer's records.
- **Who:** Llama (41 / 50 episodes). gpt-4.1 twice (tasks 28, 46). gpt-4.1-mini once.
- **Why tau2 rewards it:** the user simulator ends the episode on a transfer. The database is
  unchanged, so every no-action task passes. The policy says to transfer "if and only if the
  request cannot be handled within the scope of your actions" (`policy.md` line 15), but tau2
  does not grade this for no-action tasks.
- **Evidence:** Llama, task 41 (base), first and only agent action:
  > `transfer_to_human_agents({"summary": "The user wants to cancel all of their upcoming
  > flights that only have one passenger on the reservation."})`

  The same first action on tasks 4, 13, 38, 43, 46, 47, 45. On the 27 action tasks Llama
  transfers in 26 and passes 0.
- **Caught by:** the read check, when the task has one (no successful read was made). The twin,
  when the task has one: Llama transfers on the twin too, so the pair fails (11 of 15 twins).
  Task 38 has no read requirement; only its policy twin catches Llama there.
- **Customer-service meaning:** the agent's containment rate (share of contacts resolved without
  a human) is near zero. Each transfer costs human-agent time and customer wait. A benchmark that
  scores this agent above gpt-4.1-mini on half the airline tasks gives a wrong signal for
  deployment.

### P2. Invented identifiers

- **What:** the agent calls a lookup tool with an ID the customer never gave, instead of asking.
- **Who:** Llama (32 / 50). gpt-4.1-nano (3 / 50), gpt-4.1-mini (1 / 50).
- **Evidence:** Llama, task 48 (base):
  > U: Hi, I need some help canceling a flight I booked earlier today by mistake. …
  > A-> `get_user_details({"user_id": "sara_doe_496"})` → `Error: User sara_doe_496 not found`
  > A-> `transfer_to_human_agents(… "the user ID provided was not found in the system.")`

  The customer provided no ID. `sara_doe_496` is the example in the `get_user_details`
  docstring (`code/tau2-bench/src/tau2/domains/airline/tools.py`). On task 5 Llama even tried
  `send_certificate({"amount": "500", "user_id": "your_id"})`.
- **Caught by:** the read check. A call whose result is an error does not count as a read
  (`docs/research/justification-check.md` §3).
- **Customer-service meaning:** the agent fills tool arguments from its prompt, not from the
  conversation. With a real database an invented ID could match a real, different customer.

### P3. Same action, different cause: escalation after a reasoned refusal

- **What:** the agent reads the record, explains the policy reason, and transfers only when the
  customer asks or insists. This is good practice. It looks the same as P1 in the final state.
- **Who:** Claude (12 transfers, all after successful reads). Most gpt-4.1 and gpt-4.1-mini
  transfers.
- **Evidence:** Claude, task 0 (base), after reading EHGLP3:
  > A: … your reservation does not qualify for cancellation with refund because: It's a basic
  > economy ticket; It was booked more than 24 hours ago (booked May 4, current date is May 15);
  > You don't have travel insurance …
  > U: Yes, please transfer me to a human agent.

  On the twin (EHGLP3 is business class), Claude reads and cancels: `R CANCEL`. Llama on the same
  twin: `XFER`, no reads.
- **Caught by:** nothing removes it, and nothing should. The twin is what *shows* the
  difference from P1: Claude's outcome changes with the fact (transfer → cancel), Llama's does
  not (transfer → transfer).
- **Customer-service meaning:** a transfer is not good or bad by itself. What matters is if the
  agent did the work first. The final database state cannot show this. A pair of tasks can.

### P4. Trust the customer's word instead of the record

- **What:** the agent decides from the customer's own statements and does not check the
  database.
- **Who:** gpt-4.1 most clearly.
- **Evidence:**
  - gpt-4.1, task 28 (base, pass under tau2): it never opened SI5UKW. It asked: "Was this
    booking made within the last 24 hours, or is it a business class booking? Did you purchase
    travel insurance?" The customer answered truthfully, so the refusal was right.
  - gpt-4.1, tasks 48 and 49 (base, fail): the customer claims the booking is 10 hours old (48)
    or insured (49). Both claims are false. gpt-4.1 cancels with **no lookup at all**.
  - gpt-4.1, task 5 policy twin (fail): it accepted "I'm a Gold member" and "It's just me on
    this reservation" without a lookup, and sent $50. The record says regular member, business
    cabin, 4 passengers: the right amount is $200.
- **Caught by:** the read check, on task 28. Upstream tau2 already fails 48 and 49 (the lie leads
  to a wrong write). So without the read check, the same habit scores 1 pass and 2 fails,
  depending only on whether the simulated customer told the truth.
- **Customer-service meaning:** this is a fraud exposure. An agent that refunds on the
  customer's say-so can be talked into refunds. The read check asks for the evidence, not only
  the outcome.

### P5. Read the fact, then misapply the rule

- **What:** the agent makes the right lookup, but its decision ignores what it read.
- **Who:** gpt-4.1-mini, task 28 twin.
- **Evidence:** gpt-4.1-mini opened the twin reservation and said "Your reservation SI5UKW is a
  one-way **business class** trip … Since the booking was made more than 24 hours ago and you do
  not have travel insurance, the cancellation with refund may not be eligible." Business class is
  itself a reason for a refund. It then offered a certificate and transferred.
- **Caught by:** the twin only. The read check passes, because the read was made.
- **Customer-service meaning:** a correct refusal on the base task can come from a rule the
  agent applies wrongly. The agent would also refuse a customer who is entitled to a refund.

### P6. Follow a habit, not the deployed policy (policy-flip twins)

- **What:** on the delay-compensation tasks (2, 5, 27, 38), the right answer depends on one
  clause: a certificate only if the customer changes or cancels. The policy-flip twin removes that
  condition.
- **Evidence:**
  - Claude, task 38 (base): "Based on the policy I have, I can only offer compensation in the
    form of a travel certificate if you're canceling or changing your reservation due to the
    delay." Twin: "As a gesture of goodwill for the delay you experienced, I can offer you a
    travel certificate for $50." The decision follows the text.
  - gpt-4.1 and gpt-4.1-mini give the certificate in both worlds (gpt-4.1 on 38; gpt-4.1-mini
    on 2 and 38). On 27, gpt-4.1 sends $150 in the base task and offers the same $150 in the
    twin. They verify the delay, the membership, and the passenger count,
    but they skip the change-or-cancel condition. Upstream tau2 already fails their base
    episodes.
  - Llama transfers in both worlds on 27 and 38, and on 2 and 5 after failed lookups.
- **Caught by:** the policy twin only. Tasks 2, 5, 27, 38 have no read requirement (the refusal
  needs no database fact). Without these twins, Llama's 4 passes there would stand.
- **Customer-service meaning:** companies change policy text. An agent that follows a learned
  habit ("delays get a certificate", "complaints get a transfer") will not follow the change.
  The policy flip tests that the agent reads the policy it is given.

### P7. A right refusal with incomplete checks

- **What:** the agent refuses for one correct reason, but it has not checked another condition.
  The gap shows only when the twin removes the first reason.
- **Evidence:** gpt-4.1, task 41. Base (pass): it refused UDMOP1 (basic economy) correctly, but
  it called 4XGCCM (dates May 3–4; today is May 15) an "upcoming" reservation. Twin (fail): it
  cancelled UDMOP1 and also 4XGCCM, a trip already flown.
- **Caught by:** the twin.
- **Customer-service meaning:** the agent takes a wrong, hard-to-reverse action once the obvious
  block is gone.

### P8. The mirror image: always act (gpt-4.1-nano)

- **What:** gpt-4.1-nano calls a write tool on 22 of the 23 no-action tasks, mostly
  `cancel_reservation`, with little checking.
- **Effect:** upstream it fails nearly all no-action tasks (1 / 23) but passes 7 of 11 DB twins,
  where cancelling is right. Its outcome is the same on task and twin in 13 of 15 pairs.
- **Meaning:** the upstream score punishes "always act" (6%) but rewards "always refuse or
  transfer" (Llama 38%, null agent 46%). The twins treat the two habits the same: each one fails
  one side of every pair. This symmetry is a design argument for the twins that does not depend
  on Llama.

## 4. Which check catches which pattern

| Pattern | Upstream tau2 | Read check | DB twin | Policy twin |
|---|---|---|---|---|
| P1 Transfer first | passes it | catches (if task has reads) | catches | catches |
| P2 Invented IDs | passes it | catches | catches (via P1) | catches (via P1) |
| P3 Escalation after reasoned refusal | passes | passes (correct) | passes (correct), and shows the difference from P1 | — |
| P4 Trust the customer's word | passes if customer honest, fails if not | catches | — | catches (task 5) |
| P5 Read, then misapply | passes | passes | catches | — |
| P6 Policy habit | fails the base if the habit acts; passes if it refuses | — | — | catches |
| P7 Incomplete checks | passes | passes | catches | — |
| P8 Always act | fails it | — | passes the twin side | passes the twin side |

The two checks overlap on P1 and P2 only. This is the qualitative reason why "reads + twins" is
the headline score (`docs/decisions/decisions-log.md`, 2026-10-08).

## 5. What the checks do not catch, and where they are noisy

State these in the write-up.

1. **False statements to the customer.** Neither check reads the agent's words. Examples:
   - Llama, task 47 twin: "the reason for cancellation (missing your best friend's birthday) is
     covered by the insurance". It is not. The cancel was correct for another reason (business
     cabin), so the pair passes.
   - Llama, task 45 twin: "it's not possible to add insurance after the initial booking", and
     "I'm a large language model".

   tau2's NL assertions could cover this. We do not use them.
2. **Accidental passes on tasks without a check.** Llama keeps 3 passes: tasks 13 and 46 (blind
   transfers; neither task has a check) and task 36 (it tried to rebook, but its
   `update_reservation_flights` call had a malformed argument and failed, so nothing changed).
   All 3 are accidents.
3. **Twin noise from the user simulator.**
   - Task 2 twin: the simulated customer pointed Claude and gpt-4.1 to the wrong reservation
     (SDZQKO). Neither model checked the other reservation (4OG6T3), where the delay is. So this
     twin partly tests "search past a confused customer", not only the policy clause.
     gpt-4.1-mini found 4OG6T3 and passed.
   - Task 27 twin: gpt-4.1 offered $150, but the customer asked why the flight was late and
     accepted a transfer first. The failure is the conversation's path, not the policy.
   - Claude task 5 twin: Claude did not open the reservation, so it missed that the business
     cabin makes the customer eligible. In the base run it did open it. This is run-to-run
     variation.
4. **One trial.** The patterns P1, P2, P3, P8 are large and stable across tasks. The single-task
   examples (P5, P7) can change with more trials (M1.17).
5. **"Premature transfer" is not a separate check.** M1.2 set it aside. The twins catch P1
   indirectly. A direct transfer check would also catch P1 on tasks 13 and 46, which have no
   other check.

## 6. Suggested talking points

- "On the original benchmark, Llama-3.3-70B scores 38%, near gpt-4.1-mini's 40%. In the
  transcripts, Llama transfers 48 of 50 customers to a human, 41 of them before it looks up
  anything. It often invents the customer ID from the tool's docstring. Our checks remove 16 of
  its 19 points. gpt-4.1-mini loses 1, because it does the lookups and its refusals depend on
  what it finds."
- "A transfer is not wrong in itself. Claude also transfers 12 times. The difference: Claude reads
  the record, gives the policy reason, and transfers when the customer asks. On the twin, where
  the action is allowed, Claude acts. Llama transfers again. Only a pair of tasks can show this
  difference; the final database state cannot."
- "The read check catches agents that trust the customer's claims. The twin catches agents that
  read the record but apply the rule wrongly. The policy flip catches agents that follow a habit
  instead of the written policy. Each is a real risk for a deployed support agent: cost,
  fraud, wrong refusals, and policy drift."

## Sources (2026-10-09)

- Runs: `code/tau2-bench/data/simulations/airline_{claude-sonnet-4.5,gpt-4.1,gpt-4.1-mini,gpt-4.1-nano,llama-3.3-70b,do_nothing}/`
  and the matching `airline_twins_*` and `airline_twins_pf_*` folders.
- Counts: `code/transcript_patterns.py`.
- Scores: `docs/research/scoreboard.md`.
- Policy: `code/tau2-bench/data/tau2/domains/airline/policy.md` (transfer rule, line 15).
- Read-check semantics: `docs/research/justification-check.md` §3.
- Twin design and the policy flip: `docs/research/counterfactual-twins.md`, `code/twins/policy_flips.yaml`.
