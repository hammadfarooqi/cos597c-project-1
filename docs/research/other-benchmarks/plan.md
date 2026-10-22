---
title: Other Benchmarks (M2) — Plan and Phase 1 Results
type: research
status: superseded
updated: 2026-10-22
review_by: 2026-11-03
summary: >-
  Plan for applying the read gate, DB twin and policy twin to WebArena, with BFCL as a contrast
  case. Includes the measured phase 1 checkups: what a do-nothing agent scores on WebArena (the
  original, and WebArena-Verified on all 812 tasks offline), BFCL and AgentDojo, and why.
note: >-
  The phase 1 checkups here are a record. WorkBench became the second benchmark on 2026-10-21
  (decisions log); its runs and results are in findings-log §24–§25 and
  docs/research/other-benchmarks/workbench-scoreboard.md, which supersede §5–§6 of this plan.
  AgentDojo was dropped (§2). Phase 1 scripts were a throwaway spike (not committed).
---

# Other Benchmarks (M2) — Plan and Phase 1 Results

**Last updated:** 2026-10-22 · **By:** Hammad + Claude

## 1. Goal

Charter §3, Target tier: look at 1–2 other benchmarks and fix the same outcome-validity issue.
This covers milestones M2.1 (choose), M2.2 (null-agent pass rate) and M2.3 (apply the gates,
report before vs after) in `docs/decisions/milestones.md`.

We apply our three strategies to each benchmark, as on τ²-bench airline:

1. **Read gate.** A no-action pass counts only if the agent saw the deciding fact.
2. **DB twin.** One fact changes so that the correct outcome becomes an action.
3. **Policy twin.** One rule changes so that the correct outcome becomes an action.

Then we do the same quantitative and qualitative analysis as for τ²: scores before and after,
and a review of every removal with the two-question rubric of
`docs/research/new-models/review-handoff.md` §3.

## 2. Decisions made on 2026-10-20 (Hammad)

| Question | Choice |
|---|---|
| Benchmarks | **AgentDojo** and **WebArena**. **BFCL** as a cheap contrast case. *(AgentDojo dropped on 2026-10-21, below.)* |
| Models for new runs | The 4 newer models: claude-haiku-4.5, gpt-6-luna, gpt-5.4-nano, llama-4-maverick. |
| AgentDojo twins | Design A: a request twin and a policy twin, both built automatically (§5.1). *(Withdrawn on 2026-10-21.)* |
| Heavy infrastructure | Not sure yet. Steps that need hosted WebArena sites are optional and come last. |
| No-op doctor | Abandoned. Each benchmark gets its own small code folder. Do not merge the doctor branches. |
| **AgentDojo (2026-10-21)** | **Dropped.** Its no-op credit is in the security metric, which AgentDojo already reports next to utility, and only 2 of 97 user tasks are no-ops of the τ² type. M2 is a small add-on, so we do not spend more on it. §4.1 stays as a record of what we measured. §5.1 is withdrawn. |
| WebArena live sites (2026-10-21) | Try WebArena-Verified offline first (Option B, §4.4). Hosting the original sites (Option A, ~$10–20 on AWS, ~1 day) stays open. |

**Why these benchmarks.** The source research is in Hammad's notes (2026-10-08 and
2026-10-20). In summary:

| Benchmark | Fame | No-op share | Fit with our gates |
|---|---|---|---|
| WebArena (Zhou et al., ICLR 2024) | Very high (~2,300 citations) | 36/812 "N/A" tasks; more hidden ones (§4.2) | Read gate: medium (page visits). DB twin: strong, but needs the hosted sites. Policy twin: does not apply (no policy text). |
| AgentDojo (Debenedetti et al., NeurIPS 2024) | High; used in model system cards | Every security case (629 in v1, 949 in v1.2.2) | Read gate: strong (§5.1). Twins: built from the benchmark's own objects. |
| BFCL v4 (Patil et al., ICML 2025) | Very high; the standard function-calling leaderboard | 1,124 "irrelevance" entries; 10 of 100 overall points | Read gate: does not apply (single turn). Twin: only a "capability twin" that adds the missing function. Policy twin: does not apply. |

Known better fit, not chosen because it is less famous: WorkBench (122/690 = 17.7% possible
no-ops, 61 citations).

## 3. The "possible" versus "impossible" distinction

A no-op task is **possible** when the agent can act, but a fact or a rule makes the action
wrong. τ²-bench airline tasks are of this type. A no-op task is **impossible** when the
capability does not exist (no fitting tool, no such feature). Our three gates target the
possible type. On an impossible task, a twin must add a capability, which tests a different
skill. BFCL irrelevance is the impossible type. AgentDojo security cases and most WebArena N/A
tasks are the possible type. Report each result with its type.

## 4. Phase 1 results (measured 2026-10-20, spike)

All numbers come from each benchmark's own grader code, run on a constant or empty agent. No
agent model was called.

### 4.1 AgentDojo (agentdojo 0.1.35) — dropped 2026-10-21, kept as a record

| Version | User tasks | Injection tasks | Security cases | Null agent: attack success | Null agent: benign utility | Null agent: utility under attack |
|---|---|---|---|---|---|---|
| v1 | 97 | 27 | 629 | **0/629** (best possible security) | 4/97 | 36/629 |
| v1.2.2 | 97 | 35 | 949 | **0/949** | 5/97 | 45/949 |

- **Security.** A null agent gets the best possible security score, as expected. AgentDojo
  reports utility next to security, so its leaderboard does not hide this. But a defense or a
  model can look secure only because it never read the injection. The read gate (§5.1) tests
  exactly this.
- **Utility. A null agent passes 5 banking user tasks (v1.2.2).** We read each utility function:
  - `user_task_9` ("check and update my rent payment") and `user_task_10` ("pay the bill, like
    last month") are **no-ops by design**. Task 9 passes only if nothing changes and the rent
    stays 1100. Task 10 is `pre_environment == post_environment`. Both have the τ² shape: a
    fact decides that no action is correct.
  - `user_task_8` has no check. Its utility returns `True`, with the comment "no real utility
    check here, just making the model look at the transaction history".
  - `user_task_5` and `user_task_6` are **grader bugs**. The start state already holds a 50.00
    payment to the Spotify IBAN on 2022-03-01 (task 5's check). It also holds a recurring 50.00
    "Spotify Premium" scheduled payment, which matches task 6's check after v1.2.2 widened it to
    `"iphone" | "spotify" | "subscription"`. v1 passes task 6 correctly; v1.2.2 does not.
- Pipeline names must contain a known model name (for example `gpt-4o-2024-05-13`), because
  the `important_instructions` attack writes the model's name into the injection. Our 4 models
  are not on that list. Phase 3 must choose a name and use it for all models.

### 4.2 WebArena (official repo, `evaluation_harness/evaluators.py`)

Of 812 tasks, 325 are graded by the answer string only, so they can be scored without the
sites. The other 487 use `url_match` or `program_html` and need the hosted sites. They are not
measured. The LLM judge in WebArena is `gpt-4-1106-preview`, which is retired. We used
`openai/gpt-4.1` through Prime Intellect. **This is a deviation.**

The judge is not stable at temperature 0, so we scored each constant answer 5 times (1,373
judge calls in total).

| Constant answer | N/A tasks passed | Other string tasks passed | Total per repeat (of 325 string tasks) | How |
|---|---|---|---|---|
| `"N/A"` | **36/36** in all 5 repeats | 7 tasks in 5/5 repeats, 6 more in 3–4/5 | 46, 50, 48, 51, 52 | Exact match on N/A tasks (no LLM). The judge decides the other tasks. |
| `""` (empty) | 26 tasks in 5/5 repeats; 28–30 per repeat | 4 tasks in 5/5 repeats, 4 more in 3–4/5 | 37, 39, 39, 37, 38 | The N/A branch falls through to the `ua_match` LLM judge. |

As a share of all 812 tasks, a constant "N/A" agent gets **5.7–6.4%**. That is a lower bound,
because the 487 site-graded tasks were not measured.

Findings:

- **The empty answer passes most N/A tasks through the judge** (28–30 of 36 per repeat). This
  confirms Zhu et al. (ABC, §5.2): "the LLM judge accepts an empty reply".
- **There are hidden no-op tasks outside the 36.** "N/A" passes 5/5 on 4 tasks whose reference
  means "nothing": task 8 ("There is no airport within 5 km of Carnegie Mellon University"),
  tasks 47 and 48 ("0 order, $0 total spend"), and task 96 ("The last order was canceled. It
  will never arrive."). These are fact-dependent no-ops that are not labelled N/A. Add them to
  the read-gate set.
- **The other repeated passes are judge errors**, for example "n/a" for "Insufficient
  resistance for their workouts." (task 217, 5/5) and for "3h 20min" (task 139, 5/5 in the
  batch, but 0 in a separate direct call). The judge prompt itself says "all the string 'N/A'
  that you see is a special sequence that means 'not achievable'", and the judge then accepts
  "n/a" as "semantically equivalent". These passes do not come from no-op tasks. They are a
  judge defect, and they depend on the judge model.
- **Parser weakness.** `llm_fuzzy_match` scores 0 when the reply contains "incorrect" or
  "partially correct", and 1 otherwise, after `assert "correct" in response`. A hedged reply
  ("if the date cannot be found, 'N/A' is … equivalent") scores 1 (task 117 with `""`).
  `llm_ua_match` scores 1 unless the reply contains "different". Replies that contain neither
  expected word raise an `AssertionError`. The empty answer caused 16–19 of these per repeat,
  which we counted as "not passed".

### 4.4 WebArena-Verified, all 812 tasks offline (webarena-verified 1.2.3)

WebArena-Verified (ServiceNow) is the audited release of WebArena. It removes the LLM judge and
the catch-all "N/A". An unachievable task must return a typed status (`NOT_FOUND_ERROR`,
`ACTION_NOT_ALLOWED_ERROR`, …). Navigate and mutate tasks are checked from the agent's network
trace, so it scores all 812 tasks **offline, with no sites**.

**Method.** Each do-nothing agent gives one fixed response, and its trace holds one event: a
GET of the task's start URL with status 200. The evaluator rejects an empty trace ("Trace
content list is empty"), and a real idle agent loads the start page anyway. We synthesized
this event from the format of the repo's demo trace. We scored with
`WebArenaVerified.evaluate_task`. 40 of the 812 tasks expect a failure status: 28 `NOT_FOUND`,
11 `ACTION_NOT_ALLOWED`, 1 `PERMISSION_DENIED`.

| Do-nothing agent | Passes (of 812) |
|---|---|
| Silent (no response), or an empty string | **0** |
| Best single fixed response: `RETRIEVE` + `NOT_FOUND_ERROR` | **24** (3.0%) |
| `NAVIGATE` + `SUCCESS` (claims it navigated, but stays on the start page) | **10** |
| `MUTATE` + `ACTION_NOT_ALLOWED_ERROR` | 4 |
| Any other single fixed response | 0–2 |
| Upper bound: a refuser that never browses, with the right task type and the best status per task | **41** (5.0%): 31 of the 40 failure-status tasks + the 10 navigate tasks |

3 tasks raise an evaluator error for every agent. We counted them as failures.

Findings:

- **Verified closes the empty-reply hole.** The empty answer gets 0, against 28–30 N/A passes
  on the original (§4.2). Task 8 ("no airport within 5 km"), one of the hidden no-ops in §4.2,
  is now labelled `NOT_FOUND`, and the fixed `NOT_FOUND` response passes it.
- **Verified already has a read gate on 9 of its 40 failure tasks.** These tasks also need a
  network event that shows the deciding page: for example tasks 794–798 ("change the delivery
  address …") need a visit to `/sales/order/history/`. No fixed response passes them. **This
  is our read gate, built independently by the benchmark's maintainers.** The other 31 failure
  tasks have no such check. A fixed status passes them, and our read gate applies there.
- **A new no-op credit: 10 map tasks pass for doing nothing.** Tasks 356 and 757–767 ("show on
  the map the route from … to …") expect only a navigation event to the map start URL. An agent
  that loads the map and claims `NAVIGATE` + `SUCCESS` passes them. This is not a refusal
  no-op. It is a weak check. Confirm it with a real trace before we report it.
- **Weak points.** The trace is synthetic (one event, no page content). A real idle agent loads
  more resources, which should not change a network-event check, but we did not test this.
  This measures the **fixed** benchmark, not the original. Original WebArena's 487 site-graded
  tasks are still unmeasured (Option A).

### 4.3 BFCL v4 (`bfcl-eval`, `eval_checker/eval_runner.py`)

| Category | Entries | Null model passes (FC and prompt handlers) |
|---|---|---|
| `irrelevance` | 240 | **240/240** |
| `live_irrelevance` | 884 | **884/884** |
| `live_relevance` | 16 | 0/16 |
| multi-turn (base, miss_func, miss_param, long_context) | 800 | 0 expected: no entry has an empty gold on every turn |

The overall score is `calculate_percentage_weighted_accuracy([non_live, live, irrelevance,
multi_turn, agentic], [10, 10, 10, 30, 40])` (`eval_runner_helper.py`). So **a model that never
calls a function gets 10.0 of 100 overall points**. We did not run the full BFCL pipeline. The
10.0 comes from the formula and the category results above.

## 5. Gate designs

### 5.1 AgentDojo — withdrawn 2026-10-21 (AgentDojo dropped, §2)

The text below is the withdrawn design, kept only as a record. Do not build it.

In AgentDojo, the action that the agent must not take is the **injected goal**. The fact that
decides is **who asked for it**: a third party, through a tool output, not the user.

- **Read gate.** A secure episode (attacker goal not done) counts as justified only if the
  injection text appears in at least one tool result that the model received. AgentDojo puts
  injections only in "injection candidates": the places that the user task's ground-truth tool
  calls read (`attacks/base_attacks.py`, `get_injection_candidates`). So an agent that does the
  user task correctly must see the injection. The check is a string search over the trace. It
  needs no new runs, and the published traces of 29 pipelines (`runs/` in the AgentDojo repo)
  include every tool result.
- **Request twin (DB-twin analogue).** Same user task, same environment, no injection. The user
  prompt is the user task's prompt plus the injection task's `GOAL`, so the user asks for it.
  The correct outcome is to do both. The grader is AgentDojo's own `security()` for that
  injection task (True means the goal was done), plus the user task's `utility()`.
- **Policy twin.** The same injected episode, plus one sentence in the system prompt. The
  sentence says that notes signed by the user inside `<INFORMATION>` tags are really from the
  user. The correct outcome is then to do the goal. **AgentDojo has no written rule to flip, so
  this adds a sentence.** Say so in every result.
- **Validation of each twin** (as for the airline twins, `docs/research/counterfactual-twins.md`):
  - the null trajectory must fail the twin;
  - the injection task's `ground_truth()` calls must pass it;
  - AgentDojo's own `suite.check()` must pass.
- **Placebo twin.** Run the original episode again, unchanged, and apply the pair rule. This
  measures noise. The τ² review asked for it (`review-handoff.md` §5).
- **Utility no-ops.** Banking tasks 9 and 10 are possible no-ops. Give them the read gate (the
  scheduled-transactions and transaction-history reads) and a DB twin (for example, a landlord
  notice of a new rent amount). Report tasks 5, 6 and 8 as grader defects, not as no-ops.

### 5.2 WebArena

- **Checkup.** §4.2.
- **Classify each no-op task** as possible-fact, rule, or impossible. The 2026-10-08 reading gave
  ~23 / ~9 / ~5 for the 36 N/A tasks. Add the 4 hidden no-op tasks from §4.2 (8, 47, 48, 96).
- **Read gate.** For each possible-fact task, write a spec: the URL patterns that show the
  deciding fact (for example the product's review page, or the order-history page). An N/A
  answer counts only if the trajectory visited one of them. Apply the spec to published
  trajectories: the WebArena authors' GPT-4 and GPT-3.5 traces, OpenHands BrowsingAgent
  (claude-3.5-sonnet, gpt-4o, gpt-3.5), and AgentRewardBench (gpt-4o, claude-3.7-sonnet,
  llama-3.3-70b, qwen2.5-vl; covers only 6 of the 36 N/A tasks).
- **DB twin (optional, phase 5).** Insert one row on the hosted site so that the answer exists
  (for example, a review that mentions an underwater photo). Needs a machine with the 5 sites.
- **Policy twin.** Does not apply. WebArena has no policy text. The "rule" tasks depend on site
  functions, not on a written rule. Say so in the results.

### 5.3 BFCL

Checkup only (§4.3). It shows a no-op credit of the impossible type, where our read gate and
policy twin cannot apply. Optional: a capability twin on a sample of 50 irrelevance entries,
where we add a function that fits.

## 6. Phases

| Phase | What | LLM cost | Status |
|---|---|---|---|
| 1. Checkups | §4 | judge calls only | **Done as a spike** (incl. WebArena-Verified, §4.4) |
| 2. Read gate on published traces | WebArena: specs for the possible-fact no-op tasks (the 31 Verified failure tasks without a network check, plus the original's hidden no-ops), applied to the published traces. | none | not started |
| 3. New runs | Was AgentDojo (dropped). To decide: the second benchmark, if any (§9). | — | open |
| 4. Qualitative review | Every removal, judged with the two-question rubric. One reviewer per model. A blind second labeller on a sample, with the agreement rate reported. | reviewer agents | not started |
| 5. WebArena DB twins | Only if we get a machine. | moderate | optional |

**Stop rule.** If the phase 3 pilot shows twin failures caused by the twin itself (as τ² tasks 5
and 27 had), fix the twins before the full run.

## 7. Code and data layout (proposed)

- One small folder per benchmark under `code/` (names: agentdojo, webarena, bfcl). Each one
  pins its benchmark version, has its own environment, and has a README section in
  `code/README.md`. No shared framework.
- Results: `code/<benchmark>/runs/<run-name>/`, tracked in git, as for tau2 (CLAUDE.md §6).
  This extends CLAUDE.md §6, which names only the tau2 folder. **This needs a decisions-log
  entry.**
- Published traces from other projects are not copied into git. A script downloads them, and
  the README gives the source URL and commit.
- Keys: the same `code/tau2-bench/.env`. Read the key in Python. Do not source that file in a
  shell: it is not valid shell syntax.

## 8. Weak points

- **WebArena judge.** We cannot use the original judge model. Judge verdicts change between runs
  at temperature 0. Every WebArena number that uses the judge must come with its judge model and
  the number of repeats.
- **WebArena coverage.** 487 of 812 tasks were not measured, because they need the sites. Some
  of them may also give a null agent credit (a `program_html` check that the start state already
  passes). We do not know this.
- *(Withdrawn with AgentDojo.)* **AgentDojo policy twin.** It adds a rule instead of flipping one. A reviewer can call it
  artificial.
- **Request twin and safety training.** Some injection goals look harmful (for example, sending
  a security code to an external address). A model may refuse them even when the user asks.
  Then a twin failure says "refuses this content", not "did not reason about the source".
  Rubric Q2 must separate these cases.
- **Novelty.** AgentAbstain (arXiv 2607.10059) already builds one-change act/abstain pairs. Read
  it before the write-up makes claims.
- **Phase 1 is a spike.** Its scripts are not in the repository. Phase 2 must rebuild them in
  `code/` and reproduce §4 before any number goes into the findings log.

## 9. Open questions

1. Is there a second benchmark after AgentDojo was dropped? Candidates: WorkBench (best fit,
   COLM 2024, modest citations), or none (WebArena + BFCL contrast only).
2. Original WebArena on hosted sites (Option A), or Verified only?
3. Bring τ² retail/telecom null-agent results from the doctor branch into the findings log? They
   were §18 there, which clashes with the current §18.

## Sources (accessed 2026-10-20)

- AgentDojo: https://arxiv.org/abs/2406.13352 · package `agentdojo==0.1.35` (PyPI) · runs:
  https://github.com/ethz-spylab/agentdojo/tree/main/runs
- WebArena: https://arxiv.org/abs/2307.13854 · https://github.com/web-arena-x/webarena
  (`config_files/test.raw.json`, `evaluation_harness/`)
- BFCL: https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard ·
  package `bfcl-eval` (PyPI)
- Zhu et al., ABC: https://arxiv.org/abs/2507.02825
- AgentRewardBench: https://huggingface.co/datasets/McGill-NLP/agent-reward-bench
- OpenHands WebArena outputs: https://huggingface.co/datasets/OpenHandsCommunity/eval-output-webarena
- AgentAbstain: https://arxiv.org/abs/2607.10059
- WorkBench: https://arxiv.org/abs/2405.00823
