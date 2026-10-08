---
title: Papers Index
type: index
status: current
updated: 2026-10-08
summary: >-
  The papers and sources the proposals cite, what each one contributed, and why this project
  cares. PDFs stored here: Zhu et al. [1], τ²-bench [2], SABER [3], τ-bench [6], Cao [7], Cao et al. [8].
---

# Papers Index

| Ref | Source | Link | Why it matters |
|---|---|---|---|
| [1] | Y. Zhu et al., *Establishing Best Practices for Building Rigorous Agentic Benchmarks* (2025) | [arXiv 2507.02825](https://arxiv.org/abs/2507.02825) · `docs/papers/2025-zhu-agentic-benchmark-checklist.pdf` | Showed that τ-bench gives credit to agents that do nothing. The origin of this project. |
| [2] | V. Barres et al., *τ²-Bench: Evaluating Conversational Agents in a Dual-Control Environment* (2025) | [arXiv 2506.07982](https://arxiv.org/abs/2506.07982) · `docs/papers/2025-barres-tau2-bench.pdf` | The benchmark we modify. Source of the airline policy that makes refusal the correct outcome. |
| [3] | A. Cuadron et al., *SABER* (2025) | [arXiv 2512.07850](https://arxiv.org/abs/2512.07850) · `docs/papers/2025-cuadron-saber.pdf` | Cited for the τ³ task fixes. Check what it fixed before we claim the no-action problem is open. |
| [4] | τ²-bench GitHub issue #384, *No-op and missing reward checks in Airline and Retail tasks allow false positive rewards* (2026) | [issue 384](https://github.com/sierra-research/tau2-bench/issues/384) | Independently found the same null-agent tasks. Proposes hand fixes. Read its proposed fixes before M1.2. |
| [5] | AGI Eval, *tau2 bench revised* (2026) | — (link not recorded) | A revised τ²-bench. Check whether it already fixes no-action grading. |
| [6] | S. Yao et al., *τ-Bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains* (2024) | [arXiv 2406.12045](https://arxiv.org/abs/2406.12045) · `docs/papers/2024-yao-tau-bench.pdf` | The original τ-bench. |
| [7] | H. Cao, *Policy Loopholes in Agent Evaluation: When Policy Ambiguity Masquerades as Agent Error* (2026) | [arXiv 2609.14400](https://arxiv.org/abs/2609.14400) · `docs/papers/2026-cao-policy-loopholes.pdf` | Audits τ²-bench airline/retail policies for clauses with more than one defensible reading. Names the "upgrade cabin, then modify" pattern (L6). Relevant to task 31 (`docs/research/findings-log.md` §12). |
| [8] | H. Cao, I. Driouich, E. Thomas, *Beyond Task Completion: Revealing Corrupt Success in LLM Agents through Procedure-Aware Evaluation* (2026) | [arXiv 2603.03116](https://arxiv.org/abs/2603.03116) · `docs/papers/2026-cao-procedure-aware-evaluation.pdf` | **Close prior work. Read before the write-up.** On τ-bench, 27–78% of reported successes are "corrupt successes" (right outcome, broken procedure), and gating them changes model rankings. |
| [9] | Amazon AGI, *τ²-Bench-Verified* (2025) | [github.com/amazon-agi/tau2-bench-verified](https://github.com/amazon-agi/tau2-bench-verified) | A corrected τ²-bench. Same task 31 as ours. |

Reference numbers follow `docs/external/2026-10-02-initial-proposal.pdf`.

## What the papers say about scoring

Both PDFs were downloaded from arXiv on 2026-10-03.

- **τ-bench [6], §3 "Reward".** The reward is `r = r_action × r_output`. `r_action` checks only
  that the final database equals the gold database. The gold `actions` are the **write**
  actions used to build that database. The authors allow any reads on purpose: "the agent can
  call various (read) actions, but the agent is successful if the only database write action
  is …". They also state that `r = 1` "might be a necessary but not sufficient condition for a
  successful episode."
- **τ²-bench [2], §3.3 "Task evaluation".** Adds three new criteria: status (environment)
  assertions, natural-language assertions, and **action matching** ("every solution function
  … exists in the actual agent-user interaction trajectory"). "The DB check and communication
  info check are the same as the original τ-bench." "Each task can specify a subset of these
  criteria." Appendix B.2 says the evaluation criteria were "augmented and split" into these
  categories, including "action assertions (confirming required agent actions)".
- **So:** airline and retail came from τ-bench, and kept τ-bench's scoring (`DB + COMMUNICATE`
  in airline). Action matching is a τ²-bench addition. In our copy, only 32 telecom tasks use it
  (`ENV_ASSERTION + ACTION`). The read actions now listed in airline tasks are counted by no
  task. The papers do not say why they were added; most likely as annotation or for debugging.
- **Upstream PR #314** (merged) says the same in the docs: `actions` is "**one** reference
  trajectory", required only when ACTION is in `reward_basis`; on airline task 1 "a no-op agent
  gets full reward by design".
- **Zhu et al. [1], §E.2.** τ-bench "contains intentionally unsolvable tasks—38% of the airline
  subset": the correct outcome is "no change", so a do-nothing agent passes. The paper discusses
  this class of tasks in general; it does not discuss individual tasks.
- **SABER [3], §5 and Appendix C ("τ-Bench Verified").** Audits the τ-bench airline gold answers
  and finds a performance cap of about 70%. Its "Task 13" is our airline task 31 (daiki_lee_6144):
  it calls the empty gold `actions=[]` incorrect. Its "Task 14" is our task 32 and states the rule
  "For BE tickets, upgrade to economy before changing". Details: `docs/research/findings-log.md` §11.
