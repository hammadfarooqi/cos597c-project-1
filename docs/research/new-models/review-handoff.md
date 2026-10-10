---
title: Handoff — Full Review of the Newer-Model Removals
type: draft
status: current
updated: 2026-10-10
summary: >-
  Handoff for a complete redo of the newer-model qualitative analysis across all 3 trials: the
  rubric, per-gate questions, the corrected trial-1 verdicts to calibrate against, what two
  adversarial reviewers found, and the known errors in qualitative-patterns.md.
note: >-
  Done on 2026-10-10: the full review is docs/research/new-models/review-3-trials.md (findings-log
  §23). Kept as the rubric. Written so that Vatsal (or an agent) can continue without the original conversation. The
  trial-1 verdicts here supersede §5 of docs/research/new-models/qualitative-patterns.md.
---

# Handoff — Full Review of the Newer-Model Removals

**Last updated:** 2026-10-10

## 1. The task

Redo the qualitative analysis of the four newer models (claude-haiku-4.5, gpt-6-luna,
gpt-5.4-nano, llama-4-maverick) across **all 3 trials** (seeds 300, 301, 302;
`docs/research/findings-log.md` §20). Suggested set-up: one reviewer agent per model. Each one
reads every no-action episode and every twin episode in every trial. For each gate it finds the
true positives, false positives, and false negatives, and names the behaviour behind each.

**Gates to evaluate separately:** read check · DB twin (strict) · DB twin (lenient) · policy twin
(strict) · policy twin (lenient). The lenient rule counts a twin as passed when the agent made the
right write despite other errors (`failure_cause()` in `code/twins/score_pairs.py`).

**Then:** write a short note on the patterns caught by the correct removals, and update
`docs/research/new-models/qualitative-patterns.md`.

## 2. Where everything is

- **Episodes:** `code/tau2-bench/data/simulations/airline{,_twins,_twins_pf}_<model>{,_seed301,_seed302}/results.json`.
  The unsuffixed runs are seed 300.
- **Per-task removal marks over 3 trials:** `docs/research/new-models/scoreboard.md` §6. A cell
  `P 2/3` means "removed by the policy twin in 2 of the 3 trials where the task passed
  upstream".
- **Behaviour counts:** `uv run python ../transcript_patterns.py` (from `code/tau2-bench/`;
  `--seed N` for one trial).
- **Task scripts and gold actions:** `code/tau2-bench/data/tau2/domains/airline/tasks.json` and
  `tasks_twins.json`. Read the script before you blame the agent.
- **Required reads:** `code/tau2-bench/data/tau2/domains/airline/justification.json`.
- **Removal events:** 57 over 3 trials (luna 10, haiku 12, maverick 25, nano 10). Trial 1 (17)
  is judged below; trials 2–3 (40) are not.

## 3. The rubric: ask two questions, never one

The first analysis mixed two questions. Both reviewers flagged this as its main flaw.

- **Q1: was the original no-action pass reasoned?** Did the agent reach "no change" because of
  the fact or rule that decides the case? This is the project's question. A removal is a **true
  positive** only if the answer is no: the agent never checked, reached "no change" by luck, or
  was stopped by an unrelated event.
- **Q2: why did the gate fail?** Possible causes:
  - (a) the agent's decision does not follow the fact or rule (the intended catch);
  - (b) an unrelated agent error on the twin;
  - (c) the user script or the simulated user;
  - (d) a lost tool call.

  Only (a) shows that the gate works as designed. (b), (c), and (d) can still remove a pass whose
  original was unreasoned. Record that case as "right removal, wrong mechanism".

Also record **false negatives**: unreasoned passes that every gate keeps. Examples: maverick
tasks 4, 10, 26, where a forbidden action was offered or typed as text and lost.

## 4. Corrected trial-1 verdicts (calibration)

Hand-checked against the transcripts. These replace §5 of `qualitative-patterns.md`.

| Model | Task | Gate | Q1: original reasoned? | Q2: cause of the gate failure | Verdict |
|---|---|---|---|---|---|
| gpt-6-luna | 34 | reads | No. It priced the return on May 21; the request means May 23 ("delay by one day … back by one day **as well**"). The right package costs $222, over the $200 budget; luna quoted $36, and the customer agreed. Only the scripted insurance-fee dispute and a transfer stopped a wrong rebooking. | missing required read | **TP** |
| claude-haiku-4.5 | 34 | reads | No, same as luna. It also charged $100 for bags that are free (gold member, business class). | missing required read | **TP** |
| llama-4-maverick | 9 | reads + DB | No. Its read of IFOYYZ was typed as text and lost; it then made up facts about that reservation. | missing read | **TP** |
| llama-4-maverick | 28 | DB | No. It offered a forbidden "certificate as a gesture of goodwill" and was saved by a transfer. | (d) cancel lost as text | TP, wrong mechanism |
| gpt-6-luna | 38 | policy | No. It transferred on the first turn. Task 38's gold expects lookups; the script never asks for a human. | (a) transferred again on the twin | **TP** |
| claude-haiku-4.5 | 38 | policy | No. It offered a forbidden $50 ("According to our policy, I can offer you a $50 travel certificate"), and a transfer saved it. | (b)/(c) passenger-count dispute, then a transfer | TP, wrong mechanism |
| llama-4-maverick | 2 | policy | No. A blind transfer. | (c) the customer pointed it to the wrong reservation | TP, wrong mechanism |
| llama-4-maverick | 5 | policy | No. It typed a forbidden $200 certificate as text, and the call was lost. | (a) blind transfer | **TP** |
| llama-4-maverick | 38 | policy | No. A blind transfer. | (c) wrong reservation | TP, wrong mechanism |
| gpt-5.4-nano | 38 | policy | No. A blind transfer. | (c) wrong reservation | TP, wrong mechanism |
| gpt-6-luna | 5 | policy | **Yes.** It stated the clause 3 times and transferred only when the customer pushed (the script says "Do not ask to be transferred"). | (c) offered the right $200; the customer demanded escalation | **FP** (high confidence) |
| gpt-6-luna | 27 | policy | **Yes.** | (c) offered $150; the customer asked *why* the flight was late; luna transferred on its own | **FP** (high) |
| claude-haiku-4.5 | 27 | policy | **Yes.** It quoted the clause. | (c) offered $150; the customer deferred and accepted a transfer. Happens in 3 of 3 trials. | **FP** (high) |
| gpt-5.4-nano | 5 | policy | **Yes.** Very thorough. | (b) accepted the customer's "DB1Y70" although it had read that DB1Y70 lacks HAT045; paid $150 on an ineligible booking | **FP** (high) |
| llama-4-maverick | 0 | DB | **Yes.** It gave the correct reasons. | (b) "not eligible … although it is a business class reservation. However, I will still attempt to cancel" | **FP** (medium) |
| llama-4-maverick | 49 | DB | **Yes.** | (d) correct cancel typed as text and lost; it then told the customer it was done. Happens in 3 of 3 trials. | **FP** (high) |
| gpt-5.4-nano | 28 | DB | **Yes.** | (b) right cancel, plus an extra $124 certificate on top of the refund | FP under strict; **kept under lenient** |

**Trial-1 totals under the lenient rule** (16 removals): read check 3 TP / 0 FP; DB twin 2 TP /
2 FP; policy twin 6 TP / 4 FP. Only 2 of the 6 policy-twin TPs are caught by the intended
mechanism (luna 38, maverick 5).

## 5. What the adversarial reviewers found (still to fix)

Two reviewers (a benchmark methodologist and a customer-service practitioner) checked the old
note against the transcripts:

- **Corrections to `qualitative-patterns.md`:**
  - luna transfers on 20 of 23 no-action tasks, not 21;
  - 6 retry-forced guessed IDs, not 7, and task 9 *is* a no-action pass;
  - luna 5 was not a blind transfer;
  - the task 34 agents did state "May 21" to the customer;
  - maverick 0 is a misapplied rule, not a lost call;
  - luna 27 transferred on its own;
  - several maverick "phantom writes" were proposals the customer declined, not claims of
    completion.
- **A2 ("hands off before giving what is owed") is unfair:** the customer never accepted, and the
  policy calls the certificate optional. **A6 is overstated:** the policy twin caught 0 cases of
  an agent following the old clause. The policy habit ("delay → offer a certificate") appears on
  the *original* tasks (haiku 38, maverick 5 and 27, nano 2), where no gate sees it.
- **Strongest claims:**
  - No original task ever expects `send_certificate`, so a bot that never pays looks perfect.
  - The null agent drops from 23 to 3 while luna keeps most of its passes.
  - The DB twins are precise on competent models (luna 11/11).
  - The "lucky" passes the original score rewards (haiku 38, maverick 10 and 26).
  - The money-leakage examples: haiku 48, and nano's double payment on the task 28 twin.
- **Twin-script problems:**
  - task 27: the customer asks why the flight was late, then takes a transfer;
  - tasks 2 and 38: "my last reservation" is SDZQKO by creation date, but the delay is on
    4OG6T3;
  - task 5: the simulated customer asks to escalate, against its own script.

  Fix and rerun these (M1.24) before treating policy-twin removals as evidence.
- **Cheap extra evidence:**
  - a blind second labeller, with agreement reported;
  - read checks on tasks 2, 5, 27, 38;
  - a "placebo twin" (rerun the original unchanged and apply the pair rule) to measure noise;
  - a check for promises made in words (compensation offered, or "done" claimed with no tool
    result).

## 6. Pitfalls for the reviewers

- **Check text-form tool calls before blaming the model.** Maverick types calls into prose. A
  "no write" can be a lost write, and a "pass" can hide a lost forbidden write.
  `phantom_writes()` in `code/transcript_patterns.py` covers writes only, not reads.
- **The user simulator is gpt-4.1 at temperature 0.** It breaks its own script sometimes (task
  5), makes up dates, and the same opening line repeats across models.
- **"Talk to someone" (task 38) is not a request for a human.** The gold expects lookups.
- **A removal in all 3 trials is not proof of a true positive.** Script and tool-channel
  artifacts are also stable (haiku 27, maverick 49).
