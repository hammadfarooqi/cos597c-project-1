"""Pair scoring: a no-action pass counts only if the same agent also passes its twin.

Twin failures get a cause, so a blanket refusal ("no write") can be told apart from a bad
write. Decision: project decisions log, 2026-10-03.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass

from noop_doctor.core.calls import Episode, ObservedCall


@dataclass(frozen=True)
class PairResult:
    twin_id: str
    task_id: str
    kind: str
    orig_passed: bool
    twin_passed: bool
    cause: str  # "" when the twin passed


def failure_cause(
    calls: list[ObservedCall],
    gold_write: ObservedCall,
    write_tools: set[str],
    transfer_tools: set[str],
) -> str:
    if any(
        c.name == gold_write.name
        and all(
            str(c.arguments.get(k)) == str(v) for k, v in gold_write.arguments.items()
        )
        for c in calls
    ):
        return "right write + other error"
    if any(c.name in write_tools for c in calls):
        return "wrong write"
    if any(c.name in transfer_tools for c in calls):
        return "transfer"
    return "no write"


def score_pairs(
    originals: dict[str, Episode],
    twins: dict[str, Episode],
    twin_info: dict[str, tuple[str, str, ObservedCall]],
    write_tools: set[str],
    transfer_tools: set[str] = frozenset(),
) -> list[PairResult]:
    """`twin_info` maps twin id -> (original task id, kind, gold write).

    Only twins that have an episode are scored; a missing original episode is an error.
    """
    out = []
    for twin_id, (task_id, kind, gold) in twin_info.items():
        if twin_id not in twins:
            continue
        o, t = originals[task_id].passed, twins[twin_id].passed
        cause = (
            ""
            if t
            else failure_cause(twins[twin_id].calls, gold, write_tools, transfer_tools)
        )
        out.append(PairResult(twin_id, task_id, kind, o, t, cause))
    return out


def summarize(results: list[PairResult]) -> dict:
    cells = collections.Counter((r.orig_passed, r.twin_passed) for r in results)
    return {
        "n": len(results),
        "noop_passes": cells[(True, True)] + cells[(True, False)],
        "twin_passes": cells[(True, True)] + cells[(False, True)],
        "paired": cells[(True, True)],
        "noop_only": cells[(True, False)],
        "twin_only": cells[(False, True)],
        "neither": cells[(False, False)],
        "causes": dict(collections.Counter(r.cause for r in results if r.cause)),
        "credit_removed": cells[(True, False)],
    }
