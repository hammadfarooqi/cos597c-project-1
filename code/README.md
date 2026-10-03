---
title: Code
type: index
status: current
updated: 2026-10-03
summary: >-
  What is in code/, what we changed in tau2-bench, how to set up, and how to run the baselines.
  The reasoning behind each change is in docs/.
---

# Code

## `tau2-bench/` — our copy of τ²-bench

- **Upstream:** <https://github.com/sierra-research/tau2-bench>, commit `b7ea907`
  (2026-09, "feat(voice): pass default en-US language hint…").
- **A copy, not a submodule.** We edit it directly. Decision: `docs/decisions/decisions-log.md`,
  2026-10-03.

### Our changes to upstream

| File | Change | Why |
|---|---|---|
| `src/tau2/agent/do_nothing_agent.py` | New. An agent that stops on its first turn. | Null-agent baseline. |
| `src/tau2/user/user_simulator.py` | New `ScriptedUser`: sends one fixed message, never calls an LLM. | Free, deterministic baseline runs. |
| `src/tau2/registry.py` | Registers `do_nothing_agent` and `scripted_user`. | So the CLI can use them. |
| `src/tau2/data_model/simulation.py` | Redacts credential-like `llm_args` when results are saved. | Keys leaked into `results.json`. |
| `pyproject.toml`, `uv.lock` | `websockets` is a core dependency. | Upstream imports it from core code. |
| `.gitignore` | `data/simulations/` is tracked. | Shared results. |
| `.env.example` | Adds `PI_KEY`, `PI_API_BASE`. | Prime Intellect inference. |

When you change upstream code, add a row here.

## Setup

```bash
cd code/tau2-bench
uv sync --extra dev          # Python >=3.12,<3.14
cp .env.example .env         # then fill in PI_KEY (and any other keys you need)
uv run tau2 check-data       # verify installation
```

## Run the baselines

All commands run from `code/tau2-bench/`. Results go to `data/simulations/<save-to>/` and are
tracked in git.

**Null agent** (free, no LLM):

```bash
uv run tau2 run --domain airline --agent do_nothing_agent --user scripted_user \
  --num-trials 1 --save-to airline_do_nothing
```

**A model through Prime Intellect.** LiteLLM needs the `openai/` prefix in front of the Prime
Intellect model ID, so `openai/gpt-4.1` becomes `openai/openai/gpt-4.1`.

```bash
set -a; source .env; set +a
ARGS="{\"api_base\": \"$PI_API_BASE\", \"api_key\": \"$PI_KEY\", \"temperature\": 0}"
uv run tau2 run --domain airline \
  --agent-llm openai/openai/gpt-4.1 --agent-llm-args "$ARGS" \
  --user-llm  openai/openai/gpt-4.1 --user-llm-args  "$ARGS" \
  --num-trials 1 --save-to airline_gpt41_check
```

**Alternative: keep the key out of `llm_args`.** Put the key in the process environment.
LiteLLM reads it there, and tau2 never sees it. The five-model runs (`docs/research/findings-log.md` §7)
used this method:

```bash
set -a; source .env; set +a
export OPENAI_API_KEY="$PI_KEY" OPENAI_API_BASE="$PI_API_BASE"
uv run tau2 run --domain airline \
  --agent-llm openai/anthropic/claude-sonnet-4.5 --agent-llm-args '{"temperature": 0.0}' \
  --user-llm  openai/openai/gpt-4.1 --user-llm-args '{"temperature": 0.0}' \
  --num-trials 1 --seed 300 --max-concurrency 5 --save-to airline_claude-sonnet-4.5
```

To add tasks to an existing run, run again with the same `--save-to` and `--auto-resume`.
Completed tasks are skipped.

The key is redacted in the saved results. Check anyway before you commit:
`git diff --cached | grep -E 'pit_|sk-'` must print nothing.

Then add an entry to `docs/research/findings-log.md`.

## Upstream documentation

`tau2-bench/README.md` and `tau2-bench/AGENTS.md` describe the framework itself (domains, agents,
orchestrators, evaluator). Read `tau2-bench/AGENTS.md` before you change the evaluator.
