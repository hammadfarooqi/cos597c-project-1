"""Checkup: which tasks does an agent that does nothing pass?

Free with most benchmarks: the null trajectory is scored by the benchmark's own grader,
without running an agent. A pass on a task whose gold has a write is a grader bug, not a
no-op task, and is reported apart.
"""

from __future__ import annotations

from dataclasses import dataclass

from noop_doctor.core.calls import ToolKind


@dataclass(frozen=True)
class TaskCheckup:
    task_id: str
    null_reward: float
    gold_writes: int
    gold_reads: int
    error: str = ""

    @property
    def passed(self) -> bool:
        return self.null_reward == 1.0


def run_checkup(adapter, task_ids=None) -> list[TaskCheckup]:
    out = []
    for tid in task_ids or adapter.task_ids():
        gold = adapter.gold_calls(tid)
        writes = sum(adapter.tool_kind(c.name) == ToolKind.WRITE for c in gold)
        reads = sum(adapter.tool_kind(c.name) == ToolKind.READ for c in gold)
        try:
            reward, error = adapter.null_reward(tid), ""
        except Exception as e:  # e.g. an LLM judge without a key
            reward, error = float("nan"), f"{type(e).__name__}: {e}"[:200]
        out.append(TaskCheckup(tid, reward, writes, reads, error))
    return out


def summarize(results: list[TaskCheckup]) -> dict:
    passed = [r.task_id for r in results if r.passed]
    return {
        "tasks": len(results),
        "null_passes": len(passed),
        "pass_rate": len(passed) / len(results) if results else 0.0,
        "passed": passed,
        "passed_with_gold_reads": [
            r.task_id for r in results if r.passed and r.gold_reads
        ],
        "passed_without_gold_reads": [
            r.task_id for r in results if r.passed and not r.gold_reads
        ],
        "passed_but_gold_writes": [
            r.task_id for r in results if r.passed and r.gold_writes
        ],
        "no_gold_write": sum(1 for r in results if not r.gold_writes),
        "errors": {r.task_id: r.error for r in results if r.error},
        "verdict": "healthy: no no-op passes"
        if not passed
        else "treat: no-op passes found",
    }
