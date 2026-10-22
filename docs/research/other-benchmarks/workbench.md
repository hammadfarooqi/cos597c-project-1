---
title: WorkBench — The No-Action Gates on a Second Benchmark
type: research
status: current
updated: 2026-10-22
review_by: 2026-11-15
summary: >-
  M2 result. The read gate, DB twins and request twins applied to WorkBench (690 tasks, 122
  no-op) for the 4 newer models over 3 trials. Same ranking and same pattern as on tau2. The
  read gate is exact (65/65 removals right); the twins mostly penalise WorkBench's exact-match
  gold for strong models. Method, results, review, weak points, and how to reproduce.
---

# WorkBench — The No-Action Gates on a Second Benchmark

**Last updated:** 2026-10-22 · **By:** Hammad + Claude

## 1. Summary

- **The problem exists in WorkBench.** 122 of its 690 tasks (17.7%) have an empty gold outcome.
  A null agent scores **124/690**. All 122 no-op tasks are the τ² "possible" type: a condition
  is false ("if Yuki hasn't emailed me…"), or a set is empty ("move Ann's in-progress tasks";
  Ann has none).
- **Our gates transfer with almost no benchmark-specific code.** The read gate needs no
  hand-written read list: a no-op pass needs a read whose output differs between the start
  state and the DB twin's start state. The null agent falls from 124 to **7**.
- **The ranking holds, and the drops follow the τ² pattern** (findings-log §24, §25). Mean over
  3 trials, out of 690:

  | Model | Original | Reads gate | **Reads + twins** | Change (all gates) | τ² airline change (§20) |
  |---|---|---|---|---|---|
  | gpt-6-luna | 611.7 | 611.7 | **599.0** | −2.1% | −8.5% |
  | claude-haiku-4.5 | 510.0 | 509.0 | **494.0** | −3.1% | −16.4% |
  | gpt-5.4-nano | 352.3 | 344.7 | **331.7** | −5.9% | −20.0% |
  | llama-4-maverick | 104.7 | 91.7 | **83.3** | −20.4% | −36.8% |
  | null agent | 124 | 12 | **7** | −94.4% | 23 → 3 |

  The drops are smaller than on τ², because no-op tasks are 18% of WorkBench and 46% of
  airline.
- **The read gate is exact.** All 65 of its removals are true positives (TP) in a full hand
  review. On WorkBench's 32 published runs it removes nothing from frontier models, 0.4–6% of
  the score from mid-tier 2026 models, and 10–60% from the 2024 paper models. For example,
  mixtral-8x7b drops from 111 to 45 (§4.3).
- **The twins work for weak models, but they mostly penalise template strictness for strong
  ones.**
  - DB twin: 93 of 181 removals are false positives (FP). Request twin: 43 of 73.
  - In a typical FP, the agent saw the flipped fact and acted. WorkBench's exact-match gold then
    rejected a detail: an event name the text does not give, the first free slot, a plot range,
    a missing participant.
  - This is the τ² lesson again (decisions log, 2026-10-10 and 2026-10-22): lead with the read
    gate, and report twins only with their FP rates.

## 2. Why WorkBench

We checked four famous benchmarks first (`docs/research/other-benchmarks/plan.md` §4):

- **AgentDojo** puts its no-op credit in the security metric, and already reports it next to
  utility.
- **WebArena-Verified** already fixed the hole, partly with our own mechanism: a required page
  visit on 9 of its 40 failure tasks.
- **BFCL**'s no-ops are "impossible" ones: no fitting function exists, so only a twin could
  apply.

WorkBench (Styles et al., COLM 2024) fits best. It is less famous (about 60 citations), but its
no-ops depend on the data, as τ²'s do. It runs on a laptop, and it publishes every tool call of
32 runs (decisions log, 2026-10-21).

## 3. Method

The decisions-log entry of 2026-10-22 gives the full method. In short, it follows our τ²
newer-model method (findings §20–§23).

### 3.1 Runs

- **Models and settings:**
  - claude-haiku-4.5, gpt-5.4-nano, gpt-6-luna and llama-4-maverick, through Prime Intellect,
    at temperature 0;
  - WorkBench Revisited settings: all tools, native tool calls, act without confirmation;
  - the τ² §16 retry for tool calls that the gateway loses.
- **Trials:** 3 trials, labelled seeds 300, 301 and 302. WorkBench has no seed and no simulated
  user, so trials differ only through provider non-determinism.
- **Checks on our runs:**
  - Our haiku run reproduces WorkBench's published haiku run: 510 against 516, with 93 against
    93 no-op passes.
  - haiku's calls are identical across our trials in 688–690 of 690 tasks.
- **Upstream rule kept:** a tool call with an unknown argument ends the episode with an error.
  maverick loses about a third of its episodes this way.

### 3.2 Twins

- **Gold rules, verified.** For each of the 31 no-op templates, the gold rule is re-implemented
  as a function of the generator's exact parameters. We recover the parameters by re-running
  the seeded generators: all 690 tasks reproduce. Each rule must give the official outcome of
  **every** task of its template, including the action tasks, before any twin is used.
- **DB twin.** A minimal start-state patch makes the action correct. For example: a new email
  from the sender, one task set to "In Progress", or one day's visits changed. The twin's gold
  comes from the same verified rule.
- **Mechanical checks** (`code/workbench-m2/twins/build.py`):
  - the patch applies;
  - the gold runs, and has no phantom action;
  - doing nothing fails the twin;
  - the reads that strong published models made on the task can reveal the flip.
- **Request twin** (the policy-twin analogue; WorkBench has no policy text). One slot of the
  request changes: a threshold, a number of days, a comparison word or a start day. The action
  then becomes correct on the unchanged data. It is a request flip, not a policy flip.
- **Design and review.** Three designer agents built the twins, and two adversarial reviewers
  checked every twin before any paid run. The reviewers dropped 3 twins and fixed 1.
- **The final set:**
  - 110 DB twins and 46 request twins, plus 1 request twin that is benchmark task CRM-070 and
    reuses its episode;
  - 9 no-op tasks cannot be flipped (growth from a day to itself), and calendar-073 follows
    from the system prompt's 9am rule alone. These 10 have no read gate.

### 3.3 Scoring

- **Pair rule, as in τ²:** a no-op pass counts only if, in the same trial, it passes the read
  gate, the DB twin and the request twin (where each exists).
- **Rules:** strict (the headline), lenient, and "acted" (a sensitivity rule).
- **Reported:** means with ranges, pass^k, stability of removals, behaviour counts, failure
  causes, and a control that compares each template's twins with its ordinary action tasks.

## 4. Results

### 4.1 Scores

The full tables are in `docs/research/other-benchmarks/workbench-scoreboard.md`, which is
generated. The summary in §1 above uses the corrected maverick data (findings-log §25).

- **pass^3, reads + twins:** luna 550, haiku 494, nano 238, maverick 77.
- **Stability of removals.** haiku's removals repeat in every trial, because it is
  deterministic. maverick's removals are stable: 23 of 26 tasks are removed in every trial in
  which they passed. luna's are mostly in some trials only.

### 4.2 The review of every removal

One reviewer agent per model judged all 3 trials (findings-log §26, `workbench-review/`), and a
blind second labeller judged 40 sampled events.

| Gate | Removals | TP | WM | FP |
|---|---|---|---|---|
| Read gate | 65 | **65** | 0 | **0** |
| DB twin | 181 | 33 | 55 | 93 |
| Request twin | 73 | 4 | 26 | 43 |

- luna: 0 TP in 44 twin removals.
- haiku: 12 of 14 distinct DB-twin removals are FP.
- maverick's original passes are almost never reasoned (6 of 106 events).

Patterns:
1. A tool error, not the agent, stops a forbidden write. The tool rejected luna's 34
   `send_email` calls with an empty recipient, and nano's and maverick's `@example.com`
   addresses.
2. Deferring to the user ends the episode with no change, so it scores as a correct no-op.
3. Tool calls typed as text end the episode (maverick, 609 final answers).
4. Words and actions disagree.
5. "Growth from a day to itself" is never reasoned. The ungated "since Wednesday" tasks are the
   main source of false negatives (FN).

### 4.3 The read gate on WorkBench's published runs (no model calls)

`code/workbench-m2/published_readgate.py`:

| Run group | Models | Removed by the read gate |
|---|---|---|
| 2026, frontier | fable-5, opus-4.8, gemini-3.1-pro, gpt-5.5, gpt-5, sonnet-4.6, … | 0 |
| 2026, mid-tier | gpt-4-turbo −26, gpt-4o −20, gpt-5.1 −18, mistral-small −14, gpt-5.4-nano −14, gpt-5.2 −13 | 0.4–6.1% of score |
| 2024 paper | gpt-4 −35 (−10%), claude-2 −33 (−18%), mixtral-8x7b 111 → 45 (−60%), llama2-70b 11 → 5 | 10–60% |

claude-2 reads, but not where the deciding record is. A crude "made any read" check keeps its
passes; the twin-defined gate does not.

## 5. Weak points

- **The twins measure template accuracy as well as the decision.** WorkBench's gold is exact.
  The "acted" rule removes most twin FPs, but it would also accept a wrong action. It is a
  candidate rule, not adopted.
- **Ungated tasks.**
  - 10 of 122 no-op tasks have no read gate.
  - Abstention ("I cannot calculate growth from today") scores as a correct no-op. Whether that
    is reasoned is not settled; both readings are reported.
- **The reviewers are LLM agents.** A blind second labeller (40 sampled events) agrees on 52 of
  55 verdicts (94.5%, Cohen's kappa 0.908) and on Q1 for 34 of 36 events. The raters never
  mixed TP with FP; all 3 disagreements are on the WM boundary
  (`code/workbench-m2/data/review_agreement.json`, findings-log §27).
- **A harness bug.** A resume erased 112 maverick crash errors, and §24 first reported the
  result as provider drift. It is fixed and corrected (findings-log §25). No other run was
  resumed.
- **Cost.** $124.51 recorded (tokens × Prime Intellect list prices), of a $250 budget: haiku
  $89.59, maverick $17.09, nano $11.74, luna $6.09. Trial 1's crashed episodes have no token
  counts.
- **Request twins are not policy flips.** Some change a comparison word (higher ↔ lower) or the
  start day of a window. The reviewers accepted both as one-slot rule changes.

## 6. Reproduce

From `code/workbench/` (`uv sync --frozen` first). Set `PI_ENV_FILE` to the `.env` that holds
`PI_KEY` and `PI_API_BASE`.

```bash
uv run python ../workbench-m2/capture_params.py               # task parameters (no LLM)
uv run python ../workbench-m2/twins/build.py --write           # build and check the twins (no LLM)
uv run python ../workbench-m2/run.py --model gpt-6-luna --run original_seed300
uv run python ../workbench-m2/run.py --model gpt-6-luna --run dbtwin_seed300 \
  --tasks ../workbench-m2/data/twins_db_tasks_and_outcomes.csv
uv run python ../workbench-m2/run.py --model gpt-6-luna --run requesttwin_seed300 \
  --tasks ../workbench-m2/data/twins_request_tasks_and_outcomes.csv
uv run python ../workbench-m2/score.py --out ../../docs/research/other-benchmarks/workbench-scoreboard.md
uv run python ../workbench-m2/published_readgate.py           # read gate on published runs (no LLM)
```

## Sources (accessed 2026-10-22)

- WorkBench paper: https://arxiv.org/abs/2405.00823 ; repo (our copy at `49c7dfd`):
  https://github.com/olly-styles/WorkBench
- WorkBench Revisited (2026), `retro/main.pdf` in the repo.
- Prime Intellect model prices: `GET https://api.pinference.ai/api/v1/models`, 2026-10-22.
