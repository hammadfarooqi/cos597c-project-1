---
title: Decisions Log
type: log
status: current
updated: 2026-10-10
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

## 2026-10-08 — One generated scoreboard; "reads + twins" is the headline score
**By:** Hammad + Claude
**Why:** Scores lived in three places (results files, findings §9, findings §14) and could drift.
`code/scoreboard.py` now computes all methods from the saved runs and writes
`docs/research/scoreboard.md`. Choices:
- Methods: original, reads, twins (strict), twins (lenient), reads + twins. The headline is
  reads + twins: the two checks catch different failures (findings-log §15), so either alone
  leaves wrong-reason passes.
- A task with no check of a kind passes that check. The 27 action tasks keep the upstream score.
- It never calls an LLM or replays an environment. The read check reuses
  `justification_core.py`; the upstream reward comes from the results file.
- Several trials: a task scores its mean over trials; trial k pairs with trial k of the twin. A
  missing twin trial is an error, not a silent pass.
- The file is generated. `--check` reports a stale file.
**Affects:** `code/scoreboard.py` · `docs/research/scoreboard.md` · `code/README.md` ·
`docs/research/findings-log.md` §15
**Replaces:** —

## 2026-10-10 — Two model sets, analysed separately; the newer set is the one we use going forward
**By:** Hammad + Claude
**Why:** The TA asked for (1) qualitative explanations and (2) models released in the last year.
The older five models (findings-log §7) showed the failure patterns in exaggerated form. They are
not what we will report going forward. Mixing the two sets in one table invites comparisons we
do not want to make.
- Two sets in `code/scoreboard.py` (`MODEL_SETS`): `old` (claude-sonnet-4.5, gpt-4.1,
  gpt-4.1-mini, gpt-4.1-nano, llama-3.3-70b) and `new` (claude-haiku-4.5, gpt-6-luna,
  gpt-5.4-nano, llama-4-maverick). The null agent is the baseline in both.
- Each set has its own scoreboard (`docs/research/scoreboard.md`,
  `docs/research/new-models/scoreboard.md`) and its own qualitative note
  (`docs/research/qualitative-patterns.md`, `docs/research/new-models/qualitative-patterns.md`).
  One short note compares them: `docs/research/new-models/old-vs-new.md`.
- Merge bookkeeping: the scoreboard branch's findings-log §15–§16 became §18–§19, because main
  already had §15–§17 (Vatsal's newer-model runs). Milestones M1.6, M1.21, M1.22 now point to
  §18–§19. The 2026-10-08 entry above still says "§15"; it means §18.
- **Conflict settled:** findings-log §17 reads llama-4-maverick's twin failures as "reluctance to
  write". The transcripts show that 3 of its 6 twin removals are correct cancels that were typed
  as text and never ran, and 2 come from the tasks 2/38 twin script (findings-log §20). We follow
  §20. §17 stays as written.
**Affects:** `code/scoreboard.py` · `code/transcript_patterns.py` · `docs/research/scoreboard.md` ·
`docs/research/new-models/` · `docs/research/findings-log.md` §17–§20 ·
`docs/decisions/milestones.md`
**Replaces:** the single all-model scoreboard of 2026-10-08 (now split by set)


## 2026-10-10 — Policy-twin removals are not evidence until the scripts are fixed; lead with the read check
**By:** Vatsal + Claude
**Why:** The 3-trial review (`docs/research/new-models/review-3-trials.md`, findings-log §23)
judged every removal with the two-question rubric of `docs/research/new-models/review-handoff.md`.
The read check removed 14 passes, all correct. The policy twin removed 29, but only 5 by the
intended mechanism and 13 from reasoned originals, mostly because of the task 5, 27 and 2 user
scripts. This contradicts the claim in `docs/research/new-models/qualitative-patterns.md` (A1,
A2, A6) that the policy twin catches these patterns reliably.
- Report the read check and the DB twin as the evidence. Report policy-twin removals only with
  their FP rate, until M1.24 fixes the scripts and the twins are rerun.
- Record "no write attempted" as a candidate gate (M1.27). It is not part of any reported score
  yet.
- Not settled: whether haiku's business-cabin refusals (tasks 47, 28) count as TP or FP. Both
  counts are reported.
**Affects:** `docs/research/new-models/qualitative-patterns.md` · `docs/research/new-models/review-3-trials.md` ·
`docs/decisions/milestones.md` (M1.24, M1.26, M1.27)
**Replaces:** the reliability claims of `docs/research/new-models/qualitative-patterns.md` §5

## 2026-10-21 — M2: WorkBench is the second benchmark; AgentDojo dropped; WebArena only as a write-up point
**By:** Hammad + Claude
**Why:** The phase 1 checkups (`docs/research/other-benchmarks/plan.md` §4) showed:
- AgentDojo's no-op credit sits in the security metric. AgentDojo already reports it next to
  utility, and only 2 of its 97 user tasks are no-ops of the τ² type.
- WebArena-Verified already fixed the main hole, partly with our own mechanism (a required page
  visit on 9 of its 40 failure tasks). A do-nothing agent gets at most 41/812 there.
- WorkBench has 122 of 690 tasks (17.7%) with an empty gold outcome. All are of the τ²
  "possible" type (a false condition or an empty set). It runs on a laptop, and it publishes
  per-task results with every tool call for 24 models.

Hammad treats M2 as a small add-on, not a critical part of the project.
- **AgentDojo: dropped.** Its checkup stays in `plan.md` §4.1 as a record.
- **WebArena: no more runs.** Its checkup findings (original and Verified) are kept for the
  write-up.
- **BFCL:** a contrast case only (impossible-type no-ops; only a twin could apply).
- **WorkBench:** apply the full method (below).

WorkBench is less famous than WebArena (COLM 2024, about 60 citations), but it fits our
problem best.
**Affects:** `docs/research/other-benchmarks/plan.md` · `docs/decisions/milestones.md` (M2.1–M2.3)
**Replaces:** the 2026-10-20 choice of AgentDojo + WebArena (recorded in `plan.md` §2)

## 2026-10-22 — WorkBench method: the tau2 newer-model method, with a twin-defined read gate and request twins
**By:** Hammad + Claude
**Why:** Hammad asked for the exact method we used on τ²-bench (after all fixes), on the 4 newer
models only, with 3 trials, and with the same quantitative and qualitative analysis. WorkBench
differs from τ² in three ways. It has no simulated user, no policy text, and no gold list of
reads.
- **Runs.** The 4 newer models (claude-haiku-4.5, gpt-5.4-nano, gpt-6-luna, llama-4-maverick),
  through Prime Intellect, at temperature 0. 3 trials, labelled seeds 300, 301 and 302. WorkBench
  has no seed, so the label only names the trial, and trials differ only through provider
  non-determinism (as in findings §20). We use WorkBench Revisited's settings: all tools, native
  tool calls, and act without confirmation. The τ² §16 retry for lost tool calls is ported.
- **Upstream behaviour is kept.** A tool call with an unknown argument ends the episode as an
  error (a failure). The published runs show the same errors.
- **Scope of the gates.** The 122 tasks with an empty gold outcome. Two more tasks pass for a
  null agent (CRM 031 and 032: the gold reassigns a customer to the person who already owns
  them). We report them, but they are not gated.
- **DB twin.** One per no-op task: a minimal start-state patch that makes the action correct.
  Each template's gold rule is re-implemented as a function of the generator's exact
  parameters. Before any twin is used, the rule must reproduce the official outcome of every
  task of its template.
- **Read gate.** A no-op pass needs at least one read whose output differs between the start
  state and the DB twin's start state. WorkBench has no gold reads, so the twin defines where
  the deciding evidence lives. This accepts any query wording that would have found it.
- **Request twin (policy-twin analogue).** WorkBench has no policy text. Where one slot of the
  request (a threshold or a number of days) can change so that the action becomes correct on the
  unchanged state, the request twin uses that change. It must be labelled a request flip, not a
  policy flip.
- **Scoring.** As in τ²: pair rule per trial, strict and lenient rules, means with ranges,
  pass^k, stability of removals, behaviour counts, and cost. The qualitative review judges every
  removal with the two-question rubric of `docs/research/new-models/review-handoff.md` §3.
- **Results location.** `code/workbench-m2/runs/<run>/`, tracked in git. This extends CLAUDE.md
  §6, which names only the tau2 folder.
**Affects:** `code/workbench/` · `code/workbench-m2/` · `docs/research/other-benchmarks/workbench.md`
**Replaces:** —

## 2026-10-22 — WorkBench runs are tracked as gzipped CSVs and compact traces
**By:** Hammad + Claude
**Why:** WorkBench saves the whole prompt again at every step. One trial of the 4 models gave
about 130 MB of traces, and the results CSVs embed the same trace again. That makes about
515 MB for all runs.
- Tracked in git: each run's `_meta.json`, its results as `.csv.gz` (as upstream does), and
  `_traces.compact.json.gz`. The compact trace keeps action, input, observation and model
  output for each step. In total this is 16 MB.
- Raw `.csv` and `_traces.json` stay local and are git-ignored
  (`code/workbench-m2/.gitignore`). `code/workbench-m2/compact_traces.py` rebuilds the tracked
  copies.
- The scorer reads the `.csv.gz` copy when the raw `.csv` is missing.
**Affects:** `code/workbench-m2/` · CLAUDE.md §6 (results in git)
**Replaces:** —
