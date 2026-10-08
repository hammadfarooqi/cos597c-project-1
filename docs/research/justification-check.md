---
title: The No-Action Justification Check — Method and Implementation
type: research
status: current
updated: 2026-10-08
review_by: 2026-11-15
summary: >-
  The authoritative description of how we grade a no-action pass as justified: the rule, the
  spec format, the matching semantics, the scoring modes, the code layout, how the airline spec
  was derived, validation results, limitations, and a step-by-step guide for adding the check to
  a new domain or benchmark.
note: >-
  Read this before changing evaluator_justification.py, justification_core.py, or any
  justification.json. Twins are not part of this check yet.
---

# The No-Action Justification Check — Method and Implementation

**Last updated:** 2026-10-08 (findings-log references renumbered; first implementation 2026-10-03)

Decisions: `docs/decisions/decisions-log.md`, 2026-10-03 entries "Grade 'justified' with two
mechanisms" and "Implement the justification check as a reward gate".
Evidence: `docs/research/findings-log.md` §14.

---

## 1. The problem in one paragraph

Many agent benchmarks grade the final state only. On a **no-action task** the correct final
state is "nothing changed" (the agent must refuse), so a refusal for the right reason and a
refusal by accident get the same score. On τ²-bench airline, a null agent that does nothing
passes 23 of 50 tasks. This check adds one condition to a no-action pass: **the agent must have
looked at the facts its decision depends on.**

## 2. The rule

> **A no-action pass is justified only if the agent made every *required read*.**
> A read is *required* when the correct outcome depends on a fact that only that read reveals.

### 2.1 How to decide whether a read is required

Ask, for each task:

1. **Does any database fact decide the outcome?** Assume that every user claim is true. If the
   policy still forbids the request, no read is required: the refusal needs no data. Examples:
   "add insurance after booking" (never allowed), or "compensation for a delay, but I will not
   change my flight" (never allowed).
2. **If yes, which reads reveal those facts?** Require only those reads: the **minimum decisive
   set**. A user claim that, if true, would change the outcome *must* be checked. Example: "I
   booked 10 hours ago" → read the reservation.
3. **Do not require route-finding reads.** Example: `get_user_details` only gives the reservation
   IDs. Leave it out.
4. **For price-dependent outcomes** (the user declines because of cost), require the reads that
   give the prices: the reservation (what was paid) and the fare searches.
5. **If the outcome depends on the conversation,** not on data, do not list the task. Example:
   task 38 depends on whether the user says "I won't change".

### 2.2 What the rule does NOT check (by design)

- **Order.** A read anywhere in the run counts, even after the refusal.
- **Reasoning.** The check does not confirm that the agent used the fact correctly. The planned
  counterfactual twins test that.
- **Exact arguments.** Only the identifying arguments must match.

## 3. The spec format (benchmark-neutral)

One JSON file per domain. Keys are task IDs. Keys that start with `_` are metadata and are
ignored.

```json
{
  "_meta": {"purpose": "...", "rule": "...", "version": "2026-10-03"},
  "48": {
    "required_reads": [
      {"tool": "get_reservation_details",
       "match": {"reservation_id": "3RK2T9"},
       "why": "booked 13 days ago, not 10 hours as the user claims"}
    ]
  },
  "10": {
    "required_reads": [
      {"tool": "get_reservation_details", "match": {"reservation_id": "4NQLHD"}},
      {"tool": ["search_direct_flight", "search_onestop_flight"],
       "match": {"origin": "IAH", "destination": "SEA", "date": "2024-05-24"}}
    ]
  }
}
```

| Field | Meaning |
|---|---|
| `tool` | A tool name, or a list of alternatives. Any one satisfies the read. |
| `match` | The identifying arguments. Each must be present and equal. Must not be empty. |
| `why` | Optional. The fact the read reveals. Saved in every result. Write it: it documents the spec. |
| `note` | Optional, per task. |

**Matching semantics** (implemented in `ReadRequirement.is_met_by`). A requirement is met when
some agent tool call:
1. **succeeded** (its tool result is not an error),
2. has a name in `tool`, and
3. has every `match` argument with an equal value.

Other arguments, order, repeats, and extra calls are ignored. Only the agent's calls count, not
the user's.

## 4. Scoring

| Mode | Main `reward` | When |
|---|---|---|
| **justified** (default) | `original_reward`, set to 0 if the task is in the spec and a required read is missing | always, unless the flag is set |
| **original** | upstream reward, unchanged | `--original-scoring`, or `TAU2_ORIGINAL_SCORING=1` |

Every `RewardInfo` saves both scores and the evidence:

| Field | Content |
|---|---|
| `reward` | The main score in the active mode |
| `original_reward` | The upstream score |
| `scoring_mode` | `"justified"` or `"original"` |
| `justification` | `null` if the task is not in the spec. Otherwise: `justified`, and each read with `tools`, `match`, `why`, `met`, plus `spec_source` |

Tasks that are not in the spec, and domains with no spec file, score exactly as upstream in both
modes.

The check runs for every task in the spec, also when the original reward is 0, so that failures
can be analyzed too. It changes the reward only when the original reward is 1.

## 5. Code layout

| File | Role | Depends on tau2? |
|---|---|---|
| `code/tau2-bench/src/tau2/evaluator/justification_core.py` | The rule: spec parsing, matching, verdict. | **No.** Reuse it as is. |
| `code/tau2-bench/src/tau2/evaluator/evaluator_justification.py` | The tau2 adapter: loads `data/tau2/domains/<domain>/justification.json`, extracts the agent's calls (half-duplex messages or full-duplex ticks), gates the reward, reads the scoring mode. | Yes |
| `code/tau2-bench/src/tau2/evaluator/evaluator.py` | `evaluate_simulation()` now calls the unchanged upstream scorer (`_evaluate_simulation_upstream`), then `apply_justification()`. Every path goes through it: live runs, `tau2 evaluate-trajs`, and the gym. | Yes |
| `code/tau2-bench/src/tau2/data_model/simulation.py` | New optional fields on `RewardInfo`; new models `JustificationCheck` and `RequiredReadCheck`. Old results files still load. | Yes |
| `code/tau2-bench/src/tau2/cli.py` | `--original-scoring` on `tau2 run` and `tau2 evaluate-trajs`. It sets `TAU2_ORIGINAL_SCORING=1`, which worker processes inherit. | Yes |
| `code/tau2-bench/data/tau2/domains/airline/justification.json` | The airline spec: 16 tasks. | — |
| `code/tau2-bench/tests/test_justification.py` | 9 unit tests on the core, plus spec-file validation, plus an end-to-end null-agent test in both modes. | — |

**Why an environment variable for the mode?** The run path passes settings through several
layers (batch runner, controller, worker processes). An environment variable reaches all of them
with a change to `cli.py` only. Each result records its `scoring_mode`, so the mode is never
ambiguous afterwards.

## 6. Commands

From `code/tau2-bench/`:

```bash
# New runs: justified scoring is the default
uv run tau2 run --domain airline ... --save-to <name>
uv run tau2 run --domain airline ... --save-to <name> --original-scoring

# Re-score existing runs (no LLM calls, free)
uv run tau2 evaluate-trajs <results.json> --fresh-tasks -o <out_dir>
uv run tau2 evaluate-trajs <results.json> --fresh-tasks -o <out_dir> --original-scoring

# Tests
uv run pytest tests/test_justification.py -q
```

`--fresh-tasks` is needed for runs made before our task 31 change
(`docs/research/loophole-airline-31.md`).

## 7. The airline spec (16 tasks)

Derived with the rule in §2.1, from `docs/research/no-action-tasks.md` and two independent
audits (one blind, one adversarial).

| Task | Required reads | Fact |
|---|---|---|
| 0 | EHGLP3 | cabin, insurance, booking time |
| 1 | Q69X3R | booked 29 h ago |
| 4 | NM1VX1, KC18K6, S61CZX, H8Q05L, WUNA5K | no cancelled business flight exists |
| 9 | IFOYYZ, NQNU5R, M20IZO + search JFK→MCO 05-22 | three requests, three facts |
| 10 | 4NQLHD + search IAH→SEA 05-24 | full upgrade costs $1,815 > $1,000 |
| 26 | 3FRNFB | cabin, insurance, booking time |
| 28 | SI5UKW | cabin, insurance, booking time |
| 31 | DF89BM | basic economy; upgrade route is $81 > $65 |
| 34 | HXDUBJ + search IAH→SFO 05-19 + search SFO→IAH 05-23 | package costs $222 > $200 |
| 36 | EUJUY6 | basic economy |
| 41 | all 7 reservations | passenger counts |
| 43 | D1EW9B, 9HBUV8 | both are asked for; neither is cancellable |
| 45 | PEP4E0 | basic economy, no insurance |
| 47 | H8Q05L | insured, but the reason is not covered |
| 48 | 3RK2T9 | booked 13 days ago, not 10 h |
| 49 | 3RK2T9 | no insurance |

**Not in the spec:**
- **2, 5, 6, 13, 27, 46:** the refusal needs no data.
- **38:** depends on the conversation.

All searches accept either search tool.

## 8. Validation (2026-10-03)

Full numbers: `docs/research/findings-log.md` §14.

- **Null agent:** 23 → **7** passes. All 16 spec tasks are gated. The 7 that remain are exactly
  the non-spec tasks.
- **`--original-scoring`** reproduces upstream exactly on the 4 released runs (95, 111, 87, 123
  of 200).
- **Capable models:** the gate removes few passes: claude-3-7-sonnet 0, gpt-4.1 0, gpt-4.1-mini 2,
  o4-mini 6.
- **All gated passes were checked by hand.** None is a false rejection on the evidence:
  - gpt-4.1-mini, task 34: it searched IAH→JFK instead of the nonstop IAH→SFO, so it priced the
    wrong itinerary.
  - o4-mini, task 4: it never read a reservation.
  - o4-mini, tasks 9, 41, 43: it skipped a decisive read.
- **Upstream test suite:** the same 121 tests fail with and without our change. All of them need
  network access, API keys, or optional extras. No new failures.

## 9. Known limitations

1. **Reads are not reasoning.** An agent can read the fact and still refuse for another reason.
   The twins will cover this.
2. **Order is ignored.** Refusing first and reading later passes.
3. **All-or-nothing per task.** In multi-request tasks (9, 43), an agent that refuses one request
   correctly but transfers before the next request fails. Task 43's second request comes only
   after the first refusal, so an early transfer misses it. We accept this: the agent did not
   handle the user's full request.
4. **The spec is hand-written.** It encodes our judgment of "necessary". The rule in §2.1 makes
   that judgment repeatable, and the `why` fields make it auditable.
5. **Full-duplex mode** is implemented but not yet tested on a real full-duplex run.
6. **Tasks without data dependence** (2, 5, 6, 13, 27, 46) and task 38 are not gated. Their
   wrong-reason passes (findings-log §10: tasks 2, 5, 27, 38) remain.

## 10. Adding the check to a new domain or benchmark

**A new τ² domain (for example retail):**
1. Find the no-action tasks: run the null agent and list the tasks it passes.
2. For each task, apply the rule in §2.1. Record the decisive facts and the minimum reads, with
   one line of evidence each (`why`).
3. Write `data/tau2/domains/<domain>/justification.json`. No code change is needed.
4. Validate:
   - re-score the null-agent run: every listed task must become unjustified;
   - re-score one capable run, and hand-check every gated pass for false rejections;
   - re-score with `--original-scoring`: it must reproduce the upstream numbers.
5. Add a findings-log entry with the numbers.

**A different benchmark:**
1. Copy `justification_core.py` unchanged. It has no tau2 imports.
2. Write an adapter that does what `evaluator_justification.py` does:
   - turn the benchmark's trajectory into a list of `ObservedCall(name, arguments, succeeded)`;
   - load the spec;
   - call `check_task`;
   - keep the original score;
   - gate the main score;
   - record the mode.
3. Hook the adapter at the benchmark's single scoring entry point, after its own scoring.
4. Follow steps 1–5 above. If the benchmark's "reads" are not tool calls (for example, page
   visits), map each observation to an `ObservedCall` with a stable `name` and identifying
   `arguments`.

**What must stay the same across benchmarks** (so that results are comparable):
- the rule in §2.1,
- the matching semantics in §3,
- both scores always saved, and original scoring always reproducible.
