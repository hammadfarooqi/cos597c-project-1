"""Twin framework for WorkBench no-op tasks (COS597C, M2).

A *template spec* re-implements one WorkBench template's gold rule as a pure function
of (parameters, state), and says how to flip it:

- ``gold(p, s)``         the gold actions for parameters ``p`` on state ``s``. It must
                         reproduce the official outcome of EVERY task of the template on
                         the unchanged state (``validate`` checks this), so the rule is
                         the benchmark's, not ours.
- ``db_flip(p, s)``      a minimal start-state patch (src/tools/state.py format) that makes
                         the action correct, and one sentence saying why. The DB twin is
                         the same task text on the patched state; its gold is
                         ``gold(p, patched state)``.
- ``request_flip(p, s)`` optional: new parameters that change ONE slot of the request
                         (a threshold, a number of days, a status word) so that the
                         action is correct on the UNCHANGED state, and why. ``None`` when
                         no such one-slot change exists. This is our policy-twin analogue:
                         WorkBench has no policy text, so the rule lives in the request.

Parameters come from data/task_params.jsonl (capture_params.py): the exact values the
seeded generator used for each task.

Run from code/workbench/:  uv run python ../workbench-m2/twins/build.py
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
M2 = HERE.parent
sys.path.insert(0, ".")

from src.tools.state import ToolState, get_state, set_state_patch  # noqa: E402

Patch = list[dict]


@dataclass
class TemplateSpec:
    base_template: str
    gold: Callable[[dict, ToolState], list[str]]
    db_flip: Callable[[dict, ToolState], tuple[Patch, str]]
    request_flip: Callable[[dict, ToolState], tuple[dict, str] | None] | None = None


SPECS: dict[str, TemplateSpec] = {}


def register(
    base_template: str,
    gold: Callable[[dict, ToolState], list[str]],
    db_flip: Callable[[dict, ToolState], tuple[Patch, str]],
    request_flip: Callable[[dict, ToolState], tuple[dict, str] | None] | None = None,
) -> None:
    if base_template in SPECS:
        raise ValueError(f"template registered twice: {base_template!r}")
    SPECS[base_template] = TemplateSpec(base_template, gold, db_flip, request_flip)


def state_with(patch: Patch | None) -> ToolState:
    """A private copy of the start state with ``patch`` applied."""
    set_state_patch(patch)
    s = get_state().copy()
    set_state_patch(None)
    return s


def load_tasks() -> list[dict]:
    return [json.loads(line) for line in (M2 / "data" / "task_params.jsonl").read_text().splitlines()]


def norm(actions: list[str]) -> list[str]:
    return sorted(a.lower() for a in actions)
