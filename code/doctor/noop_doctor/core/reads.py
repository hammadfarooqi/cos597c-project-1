"""Read gate: a no-action pass is justified only if the agent made every required read.

The checking rule is the same as `code/tau2-bench/src/tau2/evaluator/justification_core.py`
and reads the same JSON spec format, so a spec works in both places:

    {
      "<task_id>": {
        "required_reads": [
          {"tool": "<name>" | ["<alternative>", ...],
           "match": {"<arg>": <value>, ...},
           "why": "<optional>"}
        ],
        "note": "<optional>"
      }
    }

A requirement is met when some successful call has one of the tool names and, for every key
in `match`, an equal argument. Order, repeats and extra calls are ignored. Keys that start
with "_" are file-level metadata.

This module adds `draft_spec`: draft the required reads from a gold trajectory, for a
person to audit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from noop_doctor.core.calls import ObservedCall, ToolKind


@dataclass(frozen=True)
class ReadRequirement:
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
    required_reads: list[ReadRequirement]
    note: str = ""


@dataclass
class Verdict:
    justified: bool
    found: list[ReadRequirement] = field(default_factory=list)
    missing: list[ReadRequirement] = field(default_factory=list)


def parse_spec(raw: dict[str, Any]) -> dict[str, TaskSpec]:
    """Validate and parse a spec dict (as loaded from JSON). Raises ValueError."""
    spec: dict[str, TaskSpec] = {}
    for task_id, entry in raw.items():
        if task_id.startswith("_"):
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
    found, missing = [], []
    for requirement in task_spec.required_reads:
        if any(requirement.is_met_by(call) for call in calls):
            found.append(requirement)
        else:
            missing.append(requirement)
    return Verdict(justified=not missing, found=found, missing=missing)


def draft_spec(
    task_ids: Iterable[str],
    gold_calls: Callable[[str], list[ObservedCall]],
    tool_kind: Callable[[str], ToolKind],
    skip_tools: Iterable[str] = (),
) -> dict[str, Any]:
    """Draft a spec: every READ call in each task's gold trajectory becomes a requirement.

    `skip_tools` drops reads that only lead to an ID (for example a user lookup). Tasks with
    no gold read are left out and listed in `_meta.no_gold_reads`. The draft must be audited:
    a gold trajectory is one valid path, not the only one.
    """
    skip = set(skip_tools)
    out: dict[str, Any] = {}
    no_reads = []
    for tid in task_ids:
        reads, seen = [], set()
        for call in gold_calls(tid):
            if call.name in skip or tool_kind(call.name) != ToolKind.READ:
                continue
            if not call.arguments:  # a read with no arguments identifies nothing
                continue
            key = (call.name, tuple(sorted(map(str, call.arguments.items()))))
            if key in seen:
                continue
            seen.add(key)
            reads.append(
                {"tool": call.name, "match": dict(call.arguments), "why": "from gold"}
            )
        if reads:
            out[tid] = {"required_reads": reads}
        else:
            no_reads.append(tid)
    out["_meta"] = {
        "status": "DRAFT from gold trajectories; audit before use",
        "skipped_tools": sorted(skip),
        "no_gold_reads": no_reads,
    }
    return out


def compare_specs(draft: dict[str, TaskSpec], reference: dict[str, TaskSpec]) -> dict:
    """Per task: requirements in both, only in the draft, only in the reference."""

    def keys(ts: TaskSpec) -> set:
        return {
            (tuple(sorted(r.tools)), tuple(sorted(map(str, r.match.items()))))
            for r in ts.required_reads
        }

    out = {}
    for tid in sorted(set(draft) | set(reference), key=_natural):
        d = keys(draft[tid]) if tid in draft else set()
        r = keys(reference[tid]) if tid in reference else set()
        out[tid] = {
            "both": len(d & r),
            "draft_only": len(d - r),
            "ref_only": len(r - d),
        }
    return out


def _natural(tid: str):
    return (0, int(tid), "") if tid.isdigit() else (1, 0, tid)
