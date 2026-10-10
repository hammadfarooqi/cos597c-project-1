"""Adapter for `examples/mini_web.json`: a small benchmark that is not tau2.

It is a template for a new adapter and a test that the core needs nothing from tau2. The
benchmark differs from tau2 in the ways most benchmarks do:

  - there is no user simulator and no policy; the agent browses and then answers;
  - the outcome is a final answer string, not a database write. The doctor models the answer
    as a WRITE call, `answer(text=...)`: it is the action that decides the outcome;
  - the grader compares the answer with the gold answer. An empty reply counts as "N/A",
    which is how a do-nothing agent passes the infeasible tasks (as in WebArena).

A twin makes an infeasible task feasible: the patch adds the product, and the expected
"write" is the answer with its price.

Results file format (`load_episodes`): a JSON list of
`{"task_id": ..., "reward": ..., "calls": [{"name": ..., "arguments": {...}, "succeeded": true}]}`.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Optional

from noop_doctor.core.calls import Episode, ObservedCall, ToolKind
from noop_doctor.core.twins import TwinSpec

KINDS = {"search": ToolKind.READ, "open": ToolKind.READ, "answer": ToolKind.WRITE}


def _norm(text: str) -> str:
    text = (text or "").strip().lower()
    return "n/a" if text in {"", "n/a", "none"} else text


class MiniWebAdapter:
    def __init__(self, path: str | Path):
        data = json.loads(Path(path).read_text())
        self.name = f"mini_web:{path}"
        self._state = data["state"]
        self._tasks = {t["id"]: t for t in data["tasks"]}

    def task_ids(self) -> list[str]:
        return list(self._tasks)

    def task(self, task_id: str) -> dict:
        return self._tasks[task_id]

    def tool_kind(self, tool_name: str) -> ToolKind:
        return KINDS.get(tool_name, ToolKind.OTHER)

    def write_tools(self) -> set[str]:
        return {n for n, k in KINDS.items() if k == ToolKind.WRITE}

    def transfer_tools(self) -> set[str]:
        return set()

    def gold_calls(self, task_id: str) -> list[ObservedCall]:
        return [
            ObservedCall(c["name"], c["arguments"])
            for c in self._tasks[task_id]["gold"]
        ]

    def gold_reads(self, task_id: str) -> list[ObservedCall]:
        return [
            c
            for c in self.gold_calls(task_id)
            if self.tool_kind(c.name) == ToolKind.READ
        ]

    def _grade(self, task: dict, calls: list[ObservedCall]) -> float:
        answers = [c.arguments.get("text", "") for c in calls if c.name == "answer"]
        return float(_norm(answers[-1] if answers else "") == _norm(task["answer"]))

    def null_reward(self, task_id: str) -> float:
        return self._grade(self._tasks[task_id], [])

    def state(self, patch: Optional[dict]) -> dict:
        s = copy.deepcopy(self._state)
        for pid, fields in (patch or {}).get("products", {}).items():
            s["products"].setdefault(pid, {}).update(fields)
        return s

    def build_twin(self, spec: TwinSpec) -> dict:
        twin = copy.deepcopy(self._tasks[spec.task_id])
        twin["id"] = spec.twin_id
        twin["patch"] = spec.patch
        twin["answer"] = spec.write.arguments["text"]
        twin["gold"] = twin["gold"][:-1] + [
            {"name": spec.write.name, "arguments": dict(spec.write.arguments)}
        ]
        return twin

    def state_reward(self, task: dict, calls: list[ObservedCall]) -> float:
        # The grader only reads the final answer; the state matters to the agent, not to it.
        return self._grade(task, calls)

    def load_episodes(self, path: Path) -> dict[str, Episode]:
        out = {}
        for e in json.loads(Path(path).read_text()):
            calls = [
                ObservedCall(
                    c["name"], c.get("arguments", {}), c.get("succeeded", True)
                )
                for c in e.get("calls", [])
            ]
            out[str(e["task_id"])] = Episode(
                str(e["task_id"]), float(e["reward"]), calls
            )
        return out

    def policy_text(self) -> str:
        raise NotImplementedError("mini_web has no policy")
