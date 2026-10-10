---
title: No-op Doctor — Design Proposal
type: research
status: needs-review
updated: 2026-10-10
review_by: 2026-10-31
summary: >-
  Proposal for a benchmark-agnostic "no-op doctor": the null-agent checkup, the read gate, DB
  twins and policy flips as one tool with a small adapter per benchmark. Lists what a benchmark
  must expose, what is airline-specific today, and first results on tau2 retail and telecom.
note: >-
  Section 9 records the first build (2026-10-10, code/doctor/). Sections 5 and 7 are the
  original proposal; section 9 says where the build differs. The LLM proposer and a non-tau2
  adapter are still open.
---

# No-op Doctor — Design Proposal

**By:** Vatsal + Claude

## 1. Goal

We have three defenses against agents that pass by doing nothing. They work on tau2 airline.
The goal is one tool, the **no-op doctor**, that applies them to another benchmark with a small
adapter and data files, not new code per benchmark. This is milestone group M3 in
`docs/decisions/milestones.md`.

The doctor does four things, in order of cost:

| Step | Question it answers | Cost | Human work per benchmark |
|---|---|---|---|
| 1. **Checkup** | Which tasks does an agent that does nothing pass? | Free: no LLM, except an LLM judge if the benchmark has one | None |
| 2. **Read gate** | Did the agent look at the fact the refusal depends on? | Free to apply | Audit a drafted spec |
| 3. **DB twins** | Does the agent act when one fact flips and the action becomes allowed? | One extra episode per twin | Say which fact flips and what the write becomes |
| 4. **Policy flips** | Does the agent act when one policy sentence flips? | One extra episode per twin | Write the sentence and its replacement |

Step 1 is fully automatic and tells you whether steps 2–4 are needed at all.

## 2. What a benchmark must expose

The doctor needs an **adapter**: a small class that maps the benchmark onto these operations.
Each step needs only some of them.

| Operation | What it is | Checkup | Read gate | DB twins | Policy flips |
|---|---|---|---|---|---|
| `tasks()` | The task IDs and their gold outcome | ✓ | ✓ | ✓ | ✓ |
| `run_null(task)` | Run an agent that stops at once (and a scripted user, if interactive) and return the reward | ✓ | | ✓ (validate) | ✓ (validate) |
| `tool_kind(name)` | Is a tool a READ or a WRITE? | ✓ (report) | ✓ | ✓ | |
| `calls(trajectory)` | The agent's tool calls as `ObservedCall` (name, arguments, succeeded) | | ✓ | ✓ | |
| `gold_calls(task)` | The tool calls in the gold trajectory, if the benchmark has one | | ✓ (draft) | | |
| `patch_state(task, patch)` | Start the task from a changed initial state | | | ✓ | |
| `add_gold_write(task, call)` | Make a write part of the expected outcome | | | ✓ | ✓ |
| `evaluate(task, trajectory)` | Score a synthetic trajectory with the benchmark's own grader | | | ✓ | ✓ |
| `with_policy(text)` | Run the same tasks under a different policy text | | | | ✓ |

So the minimum is: a way to run an empty agent, and a state-based grader. The read gate adds a
tool-call log and read/write tool labels. Twins add a settable initial state and the ability
to score a hand-made trajectory. Policy flips add a policy that is plain text in the agent's
prompt.

## 3. What is airline-specific today

| File | Today | Change needed |
|---|---|---|
| `code/tau2-bench/src/tau2/evaluator/justification_core.py` | Benchmark-agnostic. No tau2 imports. | None. It becomes the doctor's read-gate core. |
| `code/tau2-bench/src/tau2/evaluator/evaluator_justification.py` | Generic for **every tau2 domain**: it loads `data/tau2/domains/<domain>/justification.json` if the file exists. | None for tau2. A retail spec file turns it on for retail. |
| `code/twins/generate.py` | Airline only. Imports `airline_policy`, `AIRLINE_*` paths, and a hand-written `READ_TOOLS` set. Twin "families" (cancel, compensation, delay certificate) are airline rules. | Split into a generic engine (patch → build twin → validate) and an airline plug-in (the oracle search). The "compensation" family, an explicit `patch` + `write`, is already generic. |
| `code/twins/airline_policy.py` | The airline policy as code. | Stays airline-specific by nature. Optional for other domains: a hand patch replaces the oracle search. |
| `code/twins/score_pairs.py` | Hard-coded airline `WRITES` set and `airline_*` run folders. | Read write tools from the tool labels (below); take the domain as an argument. |
| `code/twins/policy_flips.yaml` + `domains/airline/environment.py`, `utils.py`, `registry.py` | Policy-flip domains `airline_pf_<id>` are registered for airline only. | Register `<domain>_pf_<id>` for any tau2 domain that has a `policy_flips/` folder. |

**A useful fact:** every tau2 tool already carries a label, `@is_tool(ToolType.READ)` or
`ToolType.WRITE` (`code/tau2-bench/src/tau2/environment/toolkit.py`). Airline has 6 read and 6
write tools, retail 7 and 7, telecom 6 and 6. The doctor can use these labels and drop the
hand-written sets in `generate.py` and `score_pairs.py`.

## 4. First checkup: tau2 retail and telecom (measured)

Null agent, scripted user, 1 trial. Details and commands: `docs/research/findings-log.md` §18.

| Domain | Tasks | Gold has no agent write | Null agent passes | Why |
|---|---|---|---|---|
| airline | 50 | 24 | **23** (46%) | §1. Grader: DB + required text, and most no-action tasks have no required text. |
| retail | 114 | 10 | **6** (5.3%) | 4 of the 10 no-write tasks also have NL assertions (the agent must say a fact), and the null agent fails them. |
| telecom | 114 | 43 | **0** | The grader checks the *user's device* state. The user changes it only when the agent tells them how. Doing nothing cannot pass. |

Zhu et al. (`docs/papers/index.md` [1], App. E) report 38% (airline) and 6.0% (retail) for
τ-bench v1. Our retail number agrees.

**What this means for the doctor.** Retail needs the read gate on 6 tasks. Telecom needs
nothing: the checkup says it is healthy. That is a useful output too. The doctor should say
"no treatment needed" when the checkup finds no no-op passes.

**Retail read gate, drafted from the gold (inferred, not yet run).** Retail gold actions list
the agent's reads, as airline's do (`docs/research/findings-log.md` §5). 4 of the 6 null-agent
passes (10, 12, 25, 65) have gold reads such as `get_order_details`. A spec drafted from these
reads would gate those 4 automatically. Tasks 50 and 57 have no gold reads and need a human
look. The drafted spec also needs the airline pruning rule: drop reads that are only a route
to an ID (for example `get_user_details`, `find_user_id_by_*`), and keep the read that reveals
the deciding fact.

## 5. Proposed design

A new folder `doctor` under `code/` (built 2026-10-10, see section 9), outside `code/tau2-bench/`, so that the tool does not depend on
our copy of tau2. It holds:

```
code/doctor/
  core/              # no benchmark imports
    reads.py         # = justification_core.py (moved or re-exported)
    twins.py         # build a twin from (task, patch, write); validation rules
    flips.py         # one-sentence policy edit; checks the sentence occurs once
    pairs.py         # pair scoring: a no-action pass counts only if its twin passes
  adapters/
    base.py          # the Adapter protocol from section 2
    tau2.py          # tau2 adapter: any domain (airline, retail, telecom, ...)
  plugins/
    airline_oracle.py   # = code/twins/airline_policy.py, used only to search DB flips
  cli.py
```

Commands (from `code/tau2-bench/`, so the tau2 adapter finds its data):

```bash
uv run python ../doctor/cli.py checkup     --bench tau2:retail          # step 1, free
uv run python ../doctor/cli.py draft-reads --bench tau2:retail          # writes a draft justification.json
uv run python ../doctor/cli.py twins       --bench tau2:retail --spec ../doctor/specs/retail.yaml
uv run python ../doctor/cli.py score       --bench tau2:retail <model> ...
```

Rules the design keeps from the airline work:

- **The benchmark's own grader is the judge.** The doctor never re-implements scoring. Every
  twin is validated with synthetic trajectories through `evaluate()`: the null trajectory must
  score original 1 / twin 0, the comply trajectory original 0 / twin 1, and the patch must
  change exactly one leaf of the state (`docs/research/counterfactual-twins.md`).
- **Specs are data.** A read spec and a twin spec are files per benchmark. A spec is drafted by
  the doctor where it can be, and audited by a person.
- **Both scores are kept.** The original reward is always reported next to the doctor's score.

## 6. Other benchmarks (not checked; from Zhu et al. and inferred)

| Benchmark | No-op problem (Zhu et al. [1]) | Fit with the adapter |
|---|---|---|
| τ-bench v1 | Same as tau2 airline, retail | Same shape as tau2. Easy. |
| WebArena | "N/A" tasks: an empty reply passes | Checkup and read gate fit (page visits as reads). DB twins need a site whose state can be patched; harder. Not checked. |
| Others with "infeasible" tasks (for example OSWorld) | Not checked | Checkup always fits. The rest depends on whether the state is patchable. |

These rows are inferences. Each one needs a checkup before we claim it.

## 7. Open choices for Vatsal and Hammad

1. **Scope of the first build.** Proposed default: make the doctor generic **inside tau2 first**
   (airline, retail, telecom with no per-domain code except data files). Retail does not
   count as the "other benchmark" in M3.2, so a second, non-tau2 adapter comes after.
2. **Where the code lives.** Proposed default: a new `doctor` folder under `code/`, with the airline code moved in
   and `code/twins/` kept as a thin wrapper so the existing commands still work.
3. **Retail twins.** The checkup shows only 6 retail no-op passes. Proposed default: read gate
   only for retail; twins only if a model's retail no-action passes look suspicious after the
   gate.

## 8. Weak points

- The checkup measures one kind of trivial agent. An agent that reads everything and then
  refuses everything passes the read gate; only twins catch it (M1.13).
- Twins need a person or an oracle to say which fact flips. The doctor automates building and
  validating a twin, not choosing it.
- Gold reads are "one reference trajectory" (upstream PR #314, `docs/papers/index.md`). A
  drafted read spec can require a read that another valid path does not make. The audit step
  must remove those.
- The retail and telecom checkups are 1 trial with a scripted user. The null agent is
  deterministic, so more trials should not change them, except where an LLM judge scores NL
  assertions.

## 9. First build (2026-10-10)

**By:** Vatsal + Claude

Vatsal asked for the doctor as its own folder, kept apart from the tau2 code. It is in
`code/doctor/` (`code/doctor/README.md`). Validation: `docs/research/findings-log.md` §19.

**Where it differs from section 5:**

- `code/tau2-bench/` and `code/twins/` are **not changed**. Another line of work edits them at
  the same time. So the read-gate core is a copy of `justification_core.py` (same rule, same
  spec format), not a move, and the airline oracle stays in `code/twins/`.
- The checkup does not run an agent. It scores the do-nothing trajectory (greeting, one user
  turn, stop) with tau2's own `evaluate_simulation`. This gives the same numbers as the real
  null-agent runs and needs no simulator.
- Twin validation adds one check: the patch must change the state. A patch that sets a field
  to its current value would otherwise pass when the write is a no-op on the original state.
- No `plugins/` folder yet: there is no oracle search in the doctor. A twin comes from a YAML
  spec with an explicit patch and write.

**For completely different benchmarks** (Vatsal, 2026-10-10): the core imports no benchmark
(a test checks it). A second adapter, `code/doctor/noop_doctor/adapters/mini_web.py`, runs
every step on a toy benchmark that is not tau2: no user, no policy, no database writes, and a
final answer as the outcome (the WebArena "N/A" flaw). To make that work, the command line
now takes twins from a YAML spec for any benchmark, loads an adapter by module path
(`--bench py:<module>:<Class>:<arg>`), and reports a step as unavailable when the adapter
lacks its methods. A changed record is also allowed when the patch creates it (a new
product), not only when the patch edits it. What an adapter must provide is listed in
`code/doctor/README.md`, "Add a different benchmark".

**Not built:** running agents on twins or flipped policies outside airline (needs tau2
registry entries); the LLM proposer for read specs and twins; an adapter for a real benchmark
outside tau2.
