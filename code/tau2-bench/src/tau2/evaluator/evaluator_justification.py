"""tau2 adapter for the no-action justification check (COS597C).

The benchmark-agnostic logic lives in `justification_core.py`. This adapter does the
three tau2-specific jobs:

1. Load the domain spec: `data/tau2/domains/<domain>/justification.json`.
   No file -> the domain is scored exactly as upstream.
2. Turn a tau2 trajectory (half-duplex messages or full-duplex ticks) into a list of
   `ObservedCall`: the agent's tool calls, each marked failed if its tool result had
   `error=True`.
3. Gate the reward. Upstream scoring runs first and is kept in `original_reward`. For a
   task in the spec, `justification` records each required read. In "justified" mode
   (the default) an unjustified task gets reward 0. In "original" mode the reward is the
   upstream reward.

Scoring mode: the `original_scoring` argument wins if given. Otherwise the environment
variable `TAU2_ORIGINAL_SCORING=1` selects "original". The CLI flag `--original-scoring`
(on `tau2 run` and `tau2 evaluate-trajs`) sets that variable, so worker processes inherit
it.

Design and rationale: docs/research/justification-check.md (project repository).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from tau2.data_model.message import AssistantMessage, Message, Tick, ToolMessage
from tau2.data_model.simulation import (
    JustificationCheck,
    RequiredReadCheck,
    RewardInfo,
)
from tau2.evaluator.justification_core import (
    ObservedCall,
    TaskSpec,
    check_task,
    parse_spec,
)
from tau2.utils.utils import DATA_DIR

SPEC_FILENAME = "justification.json"
ORIGINAL_SCORING_ENV = "TAU2_ORIGINAL_SCORING"
MODE_JUSTIFIED = "justified"
MODE_ORIGINAL = "original"


def spec_path(domain: str) -> Path:
    return DATA_DIR / "tau2" / "domains" / domain / SPEC_FILENAME


@lru_cache(maxsize=None)
def load_domain_spec(domain: str) -> Optional[dict[str, TaskSpec]]:
    """Return the parsed spec for `domain`, or None if the domain has no spec file."""
    path = spec_path(domain)
    if not path.exists():
        return None
    with open(path) as f:
        return parse_spec(json.load(f))


def is_original_scoring(original_scoring: Optional[bool] = None) -> bool:
    if original_scoring is not None:
        return original_scoring
    return os.environ.get(ORIGINAL_SCORING_ENV, "").strip().lower() in {"1", "true"}


def _calls_from_messages(messages: list[Message]) -> list[ObservedCall]:
    failed_ids = {
        m.id for m in messages if isinstance(m, ToolMessage) and m.error and m.id
    }
    calls = []
    for message in messages:
        if isinstance(message, AssistantMessage) and message.tool_calls:
            for call in message.tool_calls:
                calls.append(
                    ObservedCall(
                        call.name, dict(call.arguments), call.id not in failed_ids
                    )
                )
    return calls


def _calls_from_ticks(ticks: list[Tick]) -> list[ObservedCall]:
    failed_ids = {r.id for t in ticks for r in t.agent_tool_results if r.error and r.id}
    return [
        ObservedCall(call.name, dict(call.arguments), call.id not in failed_ids)
        for t in ticks
        for call in t.agent_tool_calls
    ]


def observed_agent_calls(simulation, full_duplex: bool) -> list[ObservedCall]:
    """The agent's tool calls in a tau2 simulation, in neutral form."""
    if full_duplex:
        return _calls_from_ticks(simulation.ticks or [])
    return _calls_from_messages(simulation.messages or [])


def apply_justification(
    reward_info: RewardInfo,
    task_id: str,
    simulation,
    domain: str,
    full_duplex: bool = False,
    original_scoring: Optional[bool] = None,
) -> RewardInfo:
    """Record the justification check on `reward_info` and gate its reward."""
    original = is_original_scoring(original_scoring)
    reward_info.original_reward = reward_info.reward
    reward_info.scoring_mode = MODE_ORIGINAL if original else MODE_JUSTIFIED

    spec = load_domain_spec(domain)
    if spec is None or task_id not in spec:
        return reward_info

    verdict = check_task(spec[task_id], observed_agent_calls(simulation, full_duplex))
    found = {id(r) for r in verdict.found}
    reward_info.justification = JustificationCheck(
        justified=verdict.justified,
        reads=[
            RequiredReadCheck(
                tools=r.tools, match=r.match, why=r.why, met=id(r) in found
            )
            for r in spec[task_id].required_reads
        ],
        spec_source=str(spec_path(domain).relative_to(DATA_DIR)),
    )
    if not original and not verdict.justified:
        reward_info.reward = 0.0
    return reward_info
