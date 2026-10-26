# Differentiating No-Action Outcomes in τ²-bench

**Hammad Farooqi · Vatsal Parikh** · Princeton COS597C, Fall 2026 · Project 1

τ²-bench gives credit to agents that do nothing. An agent that takes no action and says
nothing passes **23 of the 50 airline tasks**. On those tasks the correct outcome is "no change
to the database" (for example, the user asks for something the policy forbids). The evaluator
checks only the final database, so a careful refusal and an accident get the same score.

We change the benchmark so that a no-action pass counts only when it is **justified**:

1. **Read gate.** The agent must look up the facts that decide the task (for example, the
   reservation it refuses to cancel). A pass without those reads becomes a fail.
2. **Counterfactual twins.** For a no-action task, we build a twin task where one fact (a
   database field, or one sentence of the policy) changes so that the action becomes correct.
   The no-action pass counts only if the same agent also passes the twin. An agent that refuses
   everything fails the twin.

## Results at a glance

Airline domain, 50 tasks, 3 trials per model (seeds 300, 301, 302), user simulator gpt-4.1 at
temperature 0. Numbers are mean tasks passed out of 50.

| Agent | Original score | With read gate | With read gate + twins | Change |
|---|---|---|---|---|
| Null agent (does nothing) | 23 | 7 | not run | -70% (read gate) |
| gpt-6-luna | 39.0 | 38.0 | 35.7 | -8.5% |
| claude-haiku-4.5 | 24.3 | 23.7 | 20.3 | -16.4% |
| gpt-5.4-nano | 16.7 | 16.0 | 13.7 | -18.0% |
| llama-4-maverick | 22.7 | 20.3 | 14.3 | -36.8% |

Twin pairs use the lenient rule (a twin counts when the agent makes the right write, even with
other errors). The 7 null-agent passes left after the read gate are tasks whose refusal needs
no data. The gates remove different amounts of credit from each model, so the gap between
models changes: llama-4-maverick is close to claude-haiku-4.5 on the original score, and
6 points below it after both gates.

Full numbers, per trial, with both twin rules: `docs/research/findings-log.md` §20.

## Extension: WorkBench

As a small extension, we applied the same gates to [WorkBench](https://github.com/olly-styles/WorkBench)
(Styles et al., COLM 2024), a benchmark of workplace tasks (email, calendar, analytics, CRM and
project management). It has the same problem: 122 of its 690 tasks expect no change to the data,
and a null agent passes 124 of them (the 122, plus 2 tasks whose gold action changes nothing).
Each no-action task depends on the data. For example, "do X if Yuki hasn't emailed me" is a
no-action task when the data shows that Yuki did email the user. So the agent must look before
it can know that doing nothing is correct.

We use the same two gates, with two changes:

- **Read gate.** WorkBench has no list of required reads, and its search tools accept many
  different queries, so a fixed list would reject good reads. Instead, a no-action pass needs at
  least one read whose result changes between the task and its database twin. For the Yuki task,
  a search for Yuki's emails counts: it shows at least one email in the original task, and none
  in the twin.
- **Second twin.** WorkBench has no policy text, so the second twin changes one detail of the
  request (for example, a threshold) instead of one sentence of the policy.

Same 4 models, 3 trials each, temperature 0. Mean tasks passed out of 690. On WorkBench a twin
counts when the agent acts on the changed fact (makes any write), even if a detail is wrong:

| Agent | Original score | With read gate | With read gate + twins | Change |
|---|---|---|---|---|
| Null agent (does nothing) | 124 | 12 | 7 | -94.4% |
| gpt-6-luna | 611.7 | 611.7 | 610.3 | -0.2% |
| claude-haiku-4.5 | 510.0 | 509.0 | 506.0 | -0.8% |
| gpt-5.4-nano | 352.3 | 344.7 | 340.0 | -3.5% |
| llama-4-maverick | 104.7 | 91.7 | 84.7 | -19.1% |

The relative rankings of the real models do not change. As on airline, llama-4-maverick loses
by far the most credit; the other models change much less. The drops are smaller than on
airline, because no-action tasks are 18% of WorkBench and 46% of airline. An LLM reviewer judged
all 65 read-gate removals correct, and a blind second LLM labeller agreed on every read-gate
removal in its random sample. Under WorkBench's exact-match grading, many twin failures of the
strong models came from a wrong detail, not from the decision; the any-write rule counts those
twins as passed. Method, review and limits: `docs/research/other-benchmarks/workbench.md`. To
re-score the saved runs without a key: `code/README.md`.

WebArena-Verified, the audited release of WebArena, already uses the same idea, on 8 of its 40
unachievable tasks: a "cannot be done" answer counts only if the agent also opened the page with
the deciding data. Its other 32 unachievable tasks check only the answer
(`docs/research/other-benchmarks/webarena-verified.md`).

---

## Quick start

You need [uv](https://docs.astral.sh/uv/) and Python 3.12 or 3.13. Steps 1–3 need no API key.

**1. Install.**

```bash
git clone https://github.com/hammadfarooqi/cos597c-project-1.git
cd cos597c-project-1/code/tau2-bench
uv sync --extra dev
```

All commands below run from `code/tau2-bench/`.

**2. Reproduce the results table from the saved runs.** Every run we report is in
`code/tau2-bench/data/simulations/`, so you can score them again without any model calls.

```bash
uv run python ../twins/average_trials.py \
  gpt-6-luna:300,301,302 claude-haiku-4.5:300,301,302 \
  gpt-5.4-nano:300,301,302 llama-4-maverick:300,301,302
```

This prints the per-trial scores, the 3-trial means, and the change from the original score.

**3. Run the null agent and the tests.** The null agent and the scripted user make no LLM calls.

```bash
uv run tau2 run --domain airline --agent do_nothing_agent --user scripted_user \
  --num-trials 1 --save-to my_null_agent        # 7/50 (0.14) with the read gate
uv run tau2 run --domain airline --agent do_nothing_agent --user scripted_user \
  --num-trials 1 --save-to my_null_agent_orig --original-scoring   # 23/50, upstream scoring
uv run pytest tests/test_justification.py tests/test_empty_tool_retry.py -q
```

## Evaluate a model

We ran every model through [Prime Intellect](https://app.primeintellect.ai) inference, which is
OpenAI-compatible. Any provider that LiteLLM supports also works.

**1. Add your key.**

```bash
cp .env.example .env        # then set PI_KEY in .env
set -a; source .env; set +a
export OPENAI_API_KEY="$PI_KEY" OPENAI_API_BASE="$PI_API_BASE"
```

Keep the key in the environment, not in `--agent-llm-args`. tau2 saves those arguments in the
results file. (Our copy redacts key-like arguments, but the environment is safer.)

**2. Run one model on the airline tasks and on both twin sets.** Each model needs three runs.
LiteLLM needs the `openai/` prefix in front of the Prime model ID.

```bash
MODEL=gpt-6-luna                     # a short name for the results folders
AGENT=openai/openai/gpt-6-luna       # openai/<Prime model id>
C=(--agent-llm $AGENT --agent-llm-args '{"temperature": 0.0}'
   --user-llm openai/openai/gpt-4.1 --user-llm-args '{"temperature": 0.0}'
   --num-trials 1 --seed 300 --max-concurrency 5)

# 50 airline tasks (the read gate is applied when the results are saved)
uv run tau2 run --domain airline "${C[@]}" --save-to airline_$MODEL
# 11 database twins
uv run tau2 run --domain airline --task-set-name airline_twins --task-split-name primary \
  "${C[@]}" --save-to airline_twins_$MODEL
# 4 policy twins (one sentence of the airline policy is changed)
uv run tau2 run --domain airline_pf_delay_no_change --task-set-name airline_twins \
  --task-split-name pf_delay_no_change "${C[@]}" --save-to airline_twins_pf_$MODEL
```

The Prime IDs we used are `openai/gpt-6-luna`, `anthropic/claude-haiku-4.5`,
`openai/gpt-5.4-nano` and `meta-llama/llama-4-maverick`. For more trials, change `--seed` and
add `_seed<N>` to the end of each `--save-to` name (for example `airline_gpt-6-luna_seed301`).
If a run stops, run the same command again with `--auto-resume`.

**3. Score.**

```bash
uv run python ../twins/score_pairs.py $MODEL           # one trial, with twin failure causes
uv run python ../twins/average_trials.py $MODEL:300    # one or more seeds, model:seed,seed,...
```

A full run of one model (65 episodes) cost between $1 and $6 at Prime list prices.

## How the scoring works

| Score | What it means | Where it comes from |
|---|---|---|
| Original | Upstream τ²-bench reward. | `original_reward` in each saved result, or `--original-scoring`. |
| Read gate | A no-action pass becomes 0 when a required read is missing. | `reward` in each saved result. The required reads per task are in `code/tau2-bench/data/tau2/domains/airline/justification.json`. |
| Read gate + twins | Each no-action pass also needs a pass on its twin. | `code/twins/score_pairs.py` and `code/twins/average_trials.py`. |

To re-score saved trajectories with the current rules, without model calls:

```bash
uv run tau2 evaluate-trajs data/simulations/<run>/results.json --fresh-tasks \
  -o data/simulations/<run>_rescored
```

Twins are generated by `code/twins/generate.py` from the per-task specs in
`code/twins/specs/airline.yaml`. Run `uv run python ../twins/generate.py` to rebuild and
validate them. Do not edit `tasks_twins.json` or the policy-flip files by hand.

## Repository layout

```
README.md                 this file
code/
  README.md               every change we made to upstream tau2-bench, file by file
  tau2-bench/             our modified copy of sierra-research/tau2-bench (upstream b7ea907)
    src/tau2/evaluator/   the read gate (justification_core.py, evaluator_justification.py)
    data/tau2/domains/airline/   tasks, required reads, twins, policy flips
    data/simulations/     every run we report, tracked in git
  twins/                  twin generator and pair scorers
  workbench/              our copy of olly-styles/WorkBench (upstream 49c7dfd), 4 files changed
  workbench-m2/           WorkBench gates: runner, twins, read gate, scorer, and every run
  webarena-verified/      script that checks the WebArena-Verified read gate
docs/
  README.md               index of every project document (generated)
  decisions/              charter, milestones, decisions log
  research/               findings log (all numbers) and method notes
  external/               submitted proposals
  drafts/                 presentation draft
  papers/                 the papers we cite
tools/build_index.py      regenerates docs/README.md and audits the docs
CLAUDE.md                 working rules for the authors and their coding agents
```

## Where to read more

- **Method:** `docs/research/justification-check.md` (the read gate) and
  `docs/research/counterfactual-twins.md` (the twins).
- **All numbers and run commands:** `docs/research/findings-log.md`. §1 is the null agent,
  §14 the read gate, §15–§17 the newer models, §20 the 3-trial results.
- **The 23 no-action tasks, one by one:** `docs/research/no-action-tasks.md`.
- **A policy loophole we closed (task 31):** `docs/research/loophole-airline-31.md`.
- **The WorkBench extension:** `docs/research/other-benchmarks/workbench.md`.
- **Scope and goals:** `docs/decisions/charter.md`.
- **Every project document:** `docs/README.md`.

## Scope and limitations

- **Airline is the main result; WorkBench is a small extension.** Retail and telecom are out
  of scope. On WorkBench, the twin rule accepts any write, so it would also accept a wrong action, and 10
  of the 122 no-action tasks have no read gate (`docs/research/other-benchmarks/workbench.md`
  §5). For WebArena-Verified we only read the task data.
- **Our own task change.** We lowered the user's budget in airline task 31 from $100 to $65 to
  close a policy loophole. Task 31 results from this copy are not comparable with upstream.
- **Partial twin coverage.** Twins exist for 15 of the 23 no-action tasks (11 database twins,
  4 policy twins). The other 8 have no twin. `docs/research/counterfactual-twins.md` §4 says why.
- **Small samples.** 3 trials per model, at temperature 0. A difference of 1–2 tasks between
  means is not reliable.
- **Older models.** `data/simulations/` also holds single-trial runs of older models
  (claude-sonnet-4.5, gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, llama-3.3-70b) from the early
  experiments. They support findings-log §7–§17 and are not part of the final results.
