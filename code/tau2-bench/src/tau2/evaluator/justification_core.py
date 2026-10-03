"""Benchmark-agnostic core of the no-action justification check (COS597C).

A "no-action" task is one where the correct outcome leaves the environment unchanged
(the agent must refuse). A state-only grader cannot tell a justified refusal from an
accidental one. This module implements one rule:

    A no-action pass is justified only if the agent made every *required read*:
    the tool calls that reveal the fact the decision depends on.

This file has NO tau2 imports on purpose. Any benchmark can reuse it by:
  1. writing a spec (task id -> required reads) in the JSON format below, and
  2. turning its own trajectory into a list of `ObservedCall`.

Spec format (JSON):

    {
      "<task_id>": {
        "required_reads": [
          {
            "tool": "<tool name>" | ["<alternative>", ...],
            "match": {"<arg>": <value>, ...},   # only the identifying args
            "why": "<optional: which fact this read reveals>"
          }
        ],
        "note": "<optional free text>"
      }
    }

Matching rule for one requirement: some observed call succeeded, its name is one of
`tool`, and for every key in `match` the call has that argument with an equal value.
Other arguments, call order, repeated calls and extra calls are ignored.

Design and rationale: docs/research/justification-check.md (project repository).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ObservedCall:
    """One tool call made by the agent, in benchmark-neutral form."""

    name: str
    arguments: dict[str, Any]
    succeeded: bool = True


@dataclass(frozen=True)
class ReadRequirement:
    """One read the agent must make. Any tool in `tools` satisfies it."""

    tools: list[str]
    match: dict[str, Any]
    why: str = ""

    def is_met_by(self, call: ObservedCall) -> bool:
        if not call.succeeded or call.name not in self.tools:
            return False
        return all(
            key in call.arguments and call.arguments[key] == value
            for key, value in self.match.items()
        )


@dataclass(frozen=True)
class TaskSpec:
    """The required reads for one task."""

    required_reads: list[ReadRequirement]
    note: str = ""


@dataclass
class Verdict:
    """Result of checking one trajectory against one task spec."""

    justified: bool
    found: list[ReadRequirement] = field(default_factory=list)
    missing: list[ReadRequirement] = field(default_factory=list)


def parse_spec(raw: dict[str, Any]) -> dict[str, TaskSpec]:
    """Validate and parse a spec dict (as loaded from JSON). Raises ValueError."""
    spec: dict[str, TaskSpec] = {}
    for task_id, entry in raw.items():
        if task_id.startswith("_"):  # reserved for file-level metadata
            continue
        reads = entry.get("required_reads")
        if not reads:
            raise ValueError(f"task {task_id}: 'required_reads' must be non-empty")
        parsed = []
        for i, read in enumerate(reads):
            tool = read.get("tool")
            match = read.get("match")
            if not tool or not isinstance(match, dict) or not match:
                raise ValueError(
                    f"task {task_id}, read {i}: needs 'tool' and a non-empty 'match'"
                )
            tools = [tool] if isinstance(tool, str) else list(tool)
            parsed.append(ReadRequirement(tools, dict(match), read.get("why", "")))
        spec[str(task_id)] = TaskSpec(parsed, entry.get("note", ""))
    return spec


def check_task(task_spec: TaskSpec, calls: list[ObservedCall]) -> Verdict:
    """Check whether `calls` contain every required read of `task_spec`."""
    found, missing = [], []
    for requirement in task_spec.required_reads:
        if any(requirement.is_met_by(call) for call in calls):
            found.append(requirement)
        else:
            missing.append(requirement)
    return Verdict(justified=not missing, found=found, missing=missing)
