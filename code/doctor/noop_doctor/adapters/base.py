"""The interface a benchmark adapter implements.

Each doctor step needs only part of it:

    checkup      task_ids, gold_calls, tool_kind, null_reward
    read gate    tool_kind, gold_calls (to draft), load_episodes (to check runs)
    twins        task, gold_reads, build_twin, state, state_reward
    pair score   load_episodes, twin_info, tool_kind
    policy flip  policy_text (the edit itself is benchmark-free)
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

    def policy_text(self) -> str: ...
