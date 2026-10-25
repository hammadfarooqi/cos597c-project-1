---
title: Decisions Log
type: log
status: current
updated: 2026-10-24
summary: >-
  Append-only record of every settled decision, with the date, the reason, and the documents it
  affects. Newest at the bottom. This file outranks every other document.
---

# Decisions Log

**Append only. Never edit or delete an entry.** When a decision changes, add a new entry that
says what it replaces. The old entry stays, so the reasoning stays readable.

**Format:**

```
## YYYY-MM-DD — Short statement of the decision
**By:** who
**Why:** the reason, in one or two sentences.
**Affects:** the documents that carry the detail.
**Replaces:** an earlier entry, if any.
```

Entries dated before 2026-10-03 were reconstructed from the proposals when this log was created.

---

## 2026-10-02 — Narrow the project to justified vs unjustified no-action verdicts
**By:** Hammad, Vatsal (reconstructed)
**Why:** The initial proposal aimed at a general detector of reward/criteria mismatches on
τ³-bench, to make trivial agents fail. The hand-graded pilot showed the sharper problem: models
pass no-action tasks for the wrong reasons, at very different rates, which can reorder
rankings. The formalization makes that the Minimal goal and moves generality to Target/Stretch.
**Affects:** `docs/decisions/charter.md` §0, §3 · `docs/external/2026-10-02-proposal-formalization.pdf`
**Replaces:** the scope in `docs/external/2026-10-02-initial-proposal.pdf`

## 2026-10-03 — Vendor tau2-bench as plain files, not a submodule
**By:** Hammad + Claude
**Why:** We will edit the benchmark itself, and both of us need those edits in one history. The
upstream git history is not needed. Upstream commit: `b7ea907`.
**Affects:** `code/README.md`

## 2026-10-03 — Track experiment results in git
**By:** Hammad + Claude
**Why:** Both of us must work from the same runs. Upstream ignores `data/simulations/`; we do
not. Results files are small (under 5 MB each so far).
**Affects:** `CLAUDE.md` §6 · `code/README.md`

## 2026-10-03 — Redact credentials from saved `llm_args`
**By:** Hammad + Claude
**Why:** tau2 writes `llm_args` into every results file. Passing the Prime Intellect key through
`--agent-llm-args` put the key in plain text in `airline_gpt41_check/results.json`. It was
caught before any commit. `AgentInfo` and `UserInfo` now write `<redacted>` for credential-like
keys; the in-memory value is unchanged, so API calls and checkpoint resume still work.
**Affects:** `code/tau2-bench/src/tau2/data_model/simulation.py` · `CLAUDE.md` §6

## 2026-10-03 — Use Prime Intellect for model inference
**By:** Hammad
**Why:** One OpenAI-compatible endpoint serves the OpenAI, Anthropic, and open models we
compare, through LiteLLM with model names like `openai/openai/gpt-4.1`.
**Affects:** `code/README.md` · `code/tau2-bench/.env.example`

## 2026-10-03 — Make `websockets` a core dependency
**By:** Hammad + Claude
**Why:** Upstream imports `websockets` from core code (`tau2.data_model.simulation`), but lists
it only under the `voice` extra. A fresh `uv sync` could not run `tau2`.
**Affects:** `code/tau2-bench/pyproject.toml` · `code/tau2-bench/uv.lock`

## 2026-10-03 — Grade "justified" with two mechanisms: mandatory necessary reads and counterfactual twins
**By:** Hammad + Claude
**Why:** These are the only two strategies we like so far. Mandatory reads are cheap and
deterministic. They fail the null agent (`docs/research/findings-log.md` §5), but they cannot
catch an agent that reads and then refuses everything. Twins catch that agent with outcome-only
scoring and no LLM judge. Natural twins already show the effect (findings-log §6). tau2 can
patch the database per task, so a twin needs no change to the shared `db.json`.
The formalization's other two checks are set aside for now: "no forbidden writes" (the DB check
already catches executed writes, findings-log §4; catching *agreement* needs an LLM judge) and
"no premature transfer" (a transfer is required or expected in some no-action tasks). We do not
plan an LLM judge.
**Affects:** `docs/decisions/charter.md` §2, §4, §6 · `docs/decisions/milestones.md` M1 ·
`docs/research/no-action-tasks.md`
**Replaces:** the three-check rubric in `docs/external/2026-10-02-proposal-formalization.pdf`,
as restated in the charter §2 of 2026-10-03.

## 2026-10-03 — Generate twins from specs with a policy oracle; keep them in their own task set
**By:** Vatsal + Claude
**Why:** The airline tools do not enforce policy, so only an executable policy can show that a
flip makes a write allowed. A short per-task spec, a one-field DB search, and validation with
the real evaluator make each twin checkable. A separate task set (`airline_twins`) leaves the
upstream `tasks.json` and `db.json` unchanged.
A twin is built only when (1) the edit touches one fact, or only facts the user's script
claims, (2) the correct write is unique, and (3) the user's goal is reachable. Tasks 31 and 36
fail (2); task 4 fails (3).
**Affects:** `code/twins/` · `docs/research/counterfactual-twins.md` · `code/README.md`

## 2026-10-03 — Pair scoring: a no-action pass counts only if its twin also passes
**By:** Vatsal + Claude
**Why:** A pass on the original alone cannot tell a reasoned refusal from a refusal that
happens no matter what. A twin pass with a failed original means the agent writes no matter
what, so it is also a failure. The headline uses the strict rule (any twin failure removes the
credit); the lenient rule (the twin counts if the right write happened) is reported next to it.
Twin failures are reported by cause (transfer, no write, wrong write, right write + other error).
**Affects:** `docs/decisions/charter.md` §6 Q2–Q3 · `code/twins/score_pairs.py` ·
`docs/research/findings-log.md` §8

## 2026-10-03 — Policy-flip twins: one-sentence policy edits, each run as its own domain
**By:** Vatsal + Claude
**Why:** For policy-based no-action tasks no DB edit makes the request allowed; the decisive
variable is the rule. A policy flip changes one sentence of `policy.md` and keeps the user,
the script, and the DB the same, so it tests whether a refusal depends on the written rule.
tau2 gives one policy per domain, so each flip is a registered domain (`airline_pf_<id>`) with
the same tools and DB. The sentence and the matching oracle rule flip together, and the
generator checks that the sentence occurs once in `policy.md`. A flip must be plausible for a
real airline and must leave the user's goal reachable (checked live with one strong model).
First flip: `delay_no_change` (tasks 2, 5, 27, 38).
**Affects:** `code/twins/policy_flips.yaml` · `code/twins/airline_policy.py` ·
`code/tau2-bench/src/tau2/domains/airline/environment.py` · `code/tau2-bench/src/tau2/registry.py` ·
`docs/research/counterfactual-twins.md` §6

## 2026-10-03 — Lower task 31's budget from $100 to $65 to close a policy loophole
**By:** Hammad + Claude
**Why:** In airline task 31 a policy-legal route (upgrade the cabin to economy, then change to a
nonstop) costs $81 net and fit the user's $100 budget, which contradicts the expected "no
change". The policy is ambiguous on whether the two steps compose, and the benchmark answers
that ambiguity both ways (task 32 yes, task 45 no). Every legal route costs at least $81, so a
$65 budget makes "no change" correct under both readings. We chose $65 over $80 (a $1 margin is
too thin for a simulated user) and over a "no upgrade" user line (it takes one side of the
ambiguity).
**Affects:** `code/tau2-bench/data/tau2/domains/airline/tasks.json` (task 31) ·
`docs/research/loophole-airline-31.md` · `docs/research/findings-log.md` §14 · `code/README.md`
**Replaces:** —

## 2026-10-03 — Implement the justification check as a reward gate after upstream scoring
**By:** Hammad + Claude
**Why:** We want a check that is automatic, rule-based, generalizable to other benchmarks, and
leaves upstream scoring intact and reproducible. Choices:
- `reward_basis` is untouched; ACTION is not turned on.
- A wrapper around the unchanged upstream scorer gates the reward.
- One JSON spec per domain. Tasks not in it are unchanged.
- Matching uses the tool name (alternatives allowed) and only the identifying arguments.
  Failed calls do not count; order is ignored.
- Justified scoring is the default. `--original-scoring` (an environment variable, inherited by
  workers) restores upstream.
- Both scores are always saved.
- The core logic has no tau2 imports, so other benchmarks can reuse it.
- The airline spec covers 16 tasks. It excludes the 6 tasks whose refusal needs no data (2, 5, 6,
  13, 27, 46) and task 38 (depends on the conversation).
**Affects:** `docs/research/justification-check.md` · `docs/research/findings-log.md` §14 ·
`code/README.md` · `code/tau2-bench/src/tau2/evaluator/` · `code/tau2-bench/src/tau2/cli.py` ·
`code/tau2-bench/src/tau2/data_model/simulation.py` ·
`code/tau2-bench/data/tau2/domains/airline/justification.json`
**Replaces:** —

## 2026-10-08 — Merge all branches into `main`; renumber the parallel findings and milestones
**By:** Hammad + Claude
**Why:** Two lines of work ran in parallel on 2026-10-03 and used the same numbers.
- Findings log: Vatsal's §7–§9 stay. Hammad's §8–§12 become §10–§14. All references to them
  were updated, including two entries above in this log (`findings-log.md` §12 → §14). We
  changed only the reference, not the decision.
- Milestones: Vatsal's M1.15–M1.18 stay. Hammad's M1.15 (task 31 fix) and M1.16 (verify the
  fix) become M1.19 and M1.20.
- M1.3 was `done` on one branch and `in progress` on the other. It is now `in progress`. The
  read gate is in the evaluator. Pair scoring is still a script (`code/twins/score_pairs.py`).
- Task 31's budget is now $65. The five-model runs (findings-log §7) used the old $100 budget.
  Re-run task 31 before you use those results for it (M1.20).
**Affects:** `docs/research/findings-log.md` · `docs/decisions/milestones.md` ·
`docs/decisions/charter.md` §6 · `code/README.md`
**Replaces:** —

## 2026-10-24 — Make the repository submission-ready; the root README becomes hand-written
**By:** Vatsal + Claude
**Why:** The repository is the submission. A reader who opens it must see what the project
found and how to run it, not a generated table of documents. Choices:
- **Scope of the submission:** the airline domain and the four newer models (gpt-6-luna,
  claude-haiku-4.5, gpt-5.4-nano, llama-4-maverick), 3 trials each (findings-log §20). Vatsal
  set this scope on 2026-10-10. Retail and telecom are out of scope. The older-model runs stay
  in `code/tau2-bench/data/simulations/`, because findings-log §7–§17 cite them, but the root
  README does not report them as results.
- **The no-op doctor tool is not submitted.** It was never merged to `main`, so nothing is
  removed. The root README does not mention it.
- **The root `README.md` is hand-written.** It has the results table, a quick start, the run
  and scoring commands, the layout, and the limitations. Its table reports the twin pairs with
  the lenient rule. This replaces the CLAUDE.md rule "README.md is generated, never edit it by
  hand".
- **The generated document index moves to `docs/README.md`.** `tools/build_index.py` now
  writes that file. All other doc rules are unchanged.
- **Removed:** the results folder `20260925_150033_mock_llm_agent_gpt-3.5-turbo_user_simulator_gpt-3.5-turbo`
  in `code/tau2-bench/data/simulations/`,
  a mock-LLM smoke-test run that no document cites.
**Affects:** `README.md` · `docs/README.md` · `tools/build_index.py` · `CLAUDE.md` §1, §3,
§5.7 · `code/README.md` · `docs/decisions/milestones.md` M0.11
**Replaces:** the "README.md is generated" rule in `CLAUDE.md` (set when the repository was
created, 2026-10-03).
