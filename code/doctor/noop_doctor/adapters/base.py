"""The interface a benchmark adapter implements.

Each doctor step needs only part of it:

    checkup      task_ids, gold_calls, tool_kind, null_reward
    read gate    tool_kind, gold_calls (to draft), load_episodes (to check runs)
    twins        task, gold_reads, build_twin, state, state_reward
    pair score   load_episodes, write_tools, transfer_tools (+ twin specs)
    policy flip  nothing: the edit works on the policy file itself

Everything is in the adapter's own terms except the neutral records in `core/calls.py`:
`ObservedCall` (a tool call, or any agent action: a final answer is a call too), `Episode`
(one scored run; reward 1.0 means pass) and `ToolKind` (READ reveals a fact, WRITE decides
the outcome). Two adapters exist: `tau2.py` and `mini_web.py` (a template that is not tau2).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Protocol

from noop_doctor.core.calls import Episode, ObservedCall, ToolKind
from noop_doctor.core.twins import TwinSpec


class Adapter(Protocol):
    name: str

    def task_ids(self) -> list[str]: ...

    def task(self, task_id: str) -> Any:
        """The benchmark's own task object."""

    def tool_kind(self, tool_name: str) -> ToolKind: ...

    def gold_calls(self, task_id: str) -> list[ObservedCall]:
        """The agent's calls in the gold trajectory (empty if the benchmark has none)."""

    def gold_reads(self, task_id: str) -> list[ObservedCall]: ...

    def null_reward(self, task_id: str) -> float:
        """The full reward of a trajectory in which the agent does nothing."""

    def state(self, patch: Optional[dict]) -> dict:
        """The initial state as JSON, with `patch` deep-merged in."""

    def build_twin(self, spec: TwinSpec) -> Any:
        """A task object for the twin: the patch in its initial state, the write in its gold."""

    def state_reward(self, task: Any, calls: list[ObservedCall]) -> float:
        """Run `calls` from the task's initial state; return the state-only reward."""

    def load_episodes(self, path: Path) -> dict[str, Episode]: ...

    def write_tools(self) -> set[str]: ...

    def transfer_tools(self) -> set[str]:
        """Tools that hand the task to a human (a twin failure cause). May be empty."""

    def policy_text(self) -> str: ...


# The methods each step needs. An adapter may leave out the methods of steps its benchmark
# cannot support (for example `policy_text` when there is no policy); the CLI then says
# which step is not available instead of failing inside it.
STEP_NEEDS = {
    "checkup": ("task_ids", "gold_calls", "tool_kind", "null_reward"),
    "draft-reads": ("task_ids", "gold_calls", "tool_kind", "null_reward"),
    "check-reads": ("load_episodes",),
    "twins": ("task", "gold_reads", "build_twin", "state", "state_reward"),
    "pairs": ("load_episodes", "write_tools", "transfer_tools"),
}


def missing_methods(adapter, step: str) -> list[str]:
    return [
        m for m in STEP_NEEDS.get(step, ()) if not callable(getattr(adapter, m, None))
    ]
