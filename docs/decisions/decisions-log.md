---
title: Decisions Log
type: log
status: current
updated: 2026-10-03
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
