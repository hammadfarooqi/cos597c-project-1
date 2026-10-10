"""Benchmark-neutral records: tool calls, tool kinds, and scored episodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ToolKind(str, Enum):
    READ = "read"
    WRITE = "write"
    OTHER = "other"


@dataclass(frozen=True)
class ObservedCall:
    """One tool call made by the agent."""

    name: str
    arguments: dict[str, Any]
    succeeded: bool = True


@dataclass(frozen=True)
class Episode:
    """One scored agent run on one task."""

    task_id: str
    reward: float
    calls: list[ObservedCall] = field(default_factory=list)
    # The benchmark's reward before any gate the run already applied (None = same).
    original_reward: Optional[float] = None

    @property
    def passed(self) -> bool:
        return self.reward == 1.0

    @property
    def passed_originally(self) -> bool:
        r = self.reward if self.original_reward is None else self.original_reward
        return r == 1.0
