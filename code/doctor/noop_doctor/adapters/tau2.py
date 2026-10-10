"""Adapter for τ²-bench (any domain: airline, retail, telecom, ...).

It uses tau2 as a library and changes nothing in it. Run the doctor with tau2's Python
environment (from `code/tau2-bench/`, `uv run python ../doctor/doctor.py ...`).

What tau2 gives the doctor for free:
  - tool kinds: every tool is labelled `ToolType.READ` / `WRITE` / ... in its `tools.py`;
  - gold calls: `evaluation_criteria.actions` with requestor "assistant";
  - a settable initial state: `initial_state.initialization_data.agent_data`;
  - a state grader: `EnvironmentEvaluator` (DB / environment assertions only);
  - the full grader: `evaluate_simulation` (DB, required text, NL assertions, ...).

The full grader calls an LLM judge for tasks with NL assertions (retail). `nl_judge`
sets the judge model in this process only. The judge reads its key from the environment.
"""

from __future__ import annotations

import json
import uuid
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Optional

from noop_doctor.core.calls import Episode, ObservedCall, ToolKind
from noop_doctor.core.twins import TwinSpec

NULL_GREETING = "Hi! How can I help you today?"
NULL_USER = "Hi, I need help with my reservation."  # = tau2 ScriptedUser.MESSAGE
NULL_STOP = "###STOP###"


class Tau2Adapter:
    def __init__(
        self,
        domain: str,
        task_set: Optional[str] = None,
        nl_judge: Optional[str] = None,
    ):
        from tau2.registry import registry

        self.name = f"tau2:{domain}"
        self.domain = domain
        self._constructor = registry.get_env_constructor(domain)
        tasks = registry.get_tasks_loader(task_set or domain)()
        self._tasks = {str(t.id): t for t in tasks}
        self._env = self._constructor()
        if nl_judge:
            import tau2.evaluator.evaluator_nl_assertions as nl

            nl.DEFAULT_LLM_NL_ASSERTIONS = nl_judge

    # --- tasks and tools -------------------------------------------------------------

    def task_ids(self) -> list[str]:
        return list(self._tasks)

    def task(self, task_id: str):
        return self._tasks[task_id]

    def add_tasks(self, path: Path) -> list[str]:
        """Load extra tasks (for example a twin file) so they can be looked up by id."""
        from tau2.data_model.tasks import Task

        added = []
        for raw in json.loads(Path(path).read_text()):
            t = Task.model_validate(raw)
            self._tasks[str(t.id)] = t
            added.append(str(t.id))
        return added

    @lru_cache(maxsize=None)
    def tool_kind(self, tool_name: str) -> ToolKind:
        from tau2.environment.toolkit import ToolType

        tools = self._env.tools
        if tools is None or not tools.has_tool(tool_name):
            return ToolKind.OTHER
        kind = tools.tool_type(tool_name)
        if kind == ToolType.READ:
            return ToolKind.READ
        if kind == ToolType.WRITE:
            return ToolKind.WRITE
        return ToolKind.OTHER

    def agent_tools(self) -> list[str]:
        return list(self._env.tools.get_tools()) if self._env.tools else []

    def write_tools(self) -> set[str]:
        return {n for n in self.agent_tools() if self.tool_kind(n) == ToolKind.WRITE}

    def transfer_tools(self) -> set[str]:
        return {n for n in self.agent_tools() if "transfer" in n}

    def gold_calls(self, task_id: str) -> list[ObservedCall]:
        ec = self._tasks[task_id].evaluation_criteria
        if ec is None or not ec.actions:
            return []
        return [
            ObservedCall(a.name, dict(a.arguments))
            for a in ec.actions
            if str(getattr(a.requestor, "value", a.requestor)) == "assistant"
        ]

    def gold_reads(self, task_id: str) -> list[ObservedCall]:
        return [
            c
            for c in self.gold_calls(task_id)
            if self.tool_kind(c.name) == ToolKind.READ
        ]

    def policy_text(self) -> str:
        return self._env.policy

    # --- checkup ---------------------------------------------------------------------

    def null_reward(self, task_id: str) -> float:
        """Upstream reward of the do-nothing trajectory: greeting, one user turn, stop.

        This is the trajectory that tau2's `do_nothing_agent` + `scripted_user` produce.
        """
        from tau2.data_model.message import AssistantMessage, UserMessage
        from tau2.data_model.simulation import SimulationRun, TerminationReason
        from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation

        task = self._tasks[task_id]
        history = list(
            (task.initial_state.message_history or []) if task.initial_state else []
        )
        messages = history + [
            AssistantMessage(role="assistant", content=NULL_GREETING),
            UserMessage(role="user", content=NULL_USER),
            AssistantMessage(role="assistant", content=NULL_STOP),
        ]
        sim = SimulationRun(
            id=uuid.uuid4().hex,
            task_id=task_id,
            start_time="",
            end_time="",
            duration=0.0,
            termination_reason=TerminationReason.AGENT_STOP,
            messages=messages,
        )
        info = evaluate_simulation(
            simulation=sim,
            task=task,
            evaluation_type=EvaluationType.ALL,
            solo_mode=False,
            domain=self.domain,
            original_scoring=True,
        )
        return info.reward

    # --- state and twins -------------------------------------------------------------

    def _env_for(self, patch: Optional[dict]):
        from tau2.data_model.tasks import InitializationData

        env = self._constructor()
        if patch:
            env.set_state(InitializationData(agent_data=patch), None, [])
        return env

    def state(self, patch: Optional[dict]) -> dict:
        return self._env_for(patch).tools.db.model_dump(mode="json")

    def build_twin(self, spec: TwinSpec):
        """The original task with the patch in its initial state and the write in its gold.

        An existing initial state is kept; the patch is merged into its agent data.
        """
        from tau2.data_model.tasks import Task

        raw = self._tasks[spec.task_id].model_dump(mode="json")
        twin = deepcopy(raw)
        twin["id"] = spec.twin_id
        call = f"{spec.write.name}({spec.write.arguments})"
        where = f"--domain {self.domain}" + (
            f"_pf_{spec.policy_flip}" if spec.policy_flip else ""
        )
        twin["description"] = {
            "purpose": (
                f"Counterfactual twin of {self.domain} task {spec.task_id}. "
                f"{spec.why} Correct outcome: {call}."
            ),
            "relevant_policies": None,
            "notes": f"Run with {where}. Original purpose: "
            f"{(raw.get('description') or {}).get('purpose')}",
        }
        if spec.patch:
            init = twin.get("initial_state") or {
                "initialization_data": None,
                "initialization_actions": None,
                "message_history": None,
            }
            data = init.get("initialization_data") or {
                "agent_data": None,
                "user_data": None,
            }
            data["agent_data"] = _deep_merge(data.get("agent_data") or {}, spec.patch)
            init["initialization_data"] = data
            twin["initial_state"] = init
        ec = twin["evaluation_criteria"]
        n = len(ec["actions"] or [])
        ec["actions"] = (ec["actions"] or []) + [
            {
                "action_id": f"{spec.twin_id}_{n}",
                "requestor": "assistant",
                "name": spec.write.name,
                "arguments": dict(spec.write.arguments),
                "info": None,
            }
        ]
        ec["nl_assertions"] = [f"Agent calls {call}."]
        return Task.model_validate(twin)

    def state_reward(self, task, calls: list[ObservedCall]) -> float:
        from tau2.data_model.message import AssistantMessage, ToolCall
        from tau2.evaluator.evaluator_env import EnvironmentEvaluator

        env = self._constructor()
        init = task.initial_state
        if init and (init.initialization_data or init.initialization_actions):
            env.set_state(init.initialization_data, init.initialization_actions, [])
        msgs = []
        for c in calls:
            tc = ToolCall(id=uuid.uuid4().hex[:12], name=c.name, arguments=c.arguments)
            msgs.append(
                AssistantMessage(role="assistant", content=None, tool_calls=[tc])
            )
            msgs.append(env.get_response(tc))
        return EnvironmentEvaluator.calculate_reward(
            environment_constructor=self._constructor, task=task, full_trajectory=msgs
        ).reward

    def twin_specs_from_tasks(self, path: Path) -> list[TwinSpec]:
        """Recover TwinSpecs from a twin task file (ids like `<task>_twin_<name>`)."""
        specs = []
        for raw in json.loads(Path(path).read_text()):
            task_id, name = raw["id"].split("_twin_", 1)
            data = (raw.get("initial_state") or {}).get("initialization_data") or {}
            patch = data.get("agent_data") or {}
            write = raw["evaluation_criteria"]["actions"][-1]
            flip = name[3:] if name.startswith("pf_") else None
            specs.append(
                TwinSpec(
                    task_id=task_id,
                    name=name,
                    write=ObservedCall(write["name"], dict(write["arguments"])),
                    patch=patch,
                    policy_flip=flip,
                )
            )
        return specs

    # --- runs ------------------------------------------------------------------------

    def load_episodes(self, path: Path) -> dict[str, Episode]:
        """Episodes from a tau2 `results.json`. A missing reward (infra error) counts as 0.

        `reward` is the saved reward (after our read gate, for runs made with it);
        `original_reward` is the upstream reward when the run saved it.

        With several trials of a task, the last one wins.
        """
        out = {}
        for sim in json.loads(Path(path).read_text())["simulations"]:
            msgs = sim.get("messages") or []
            failed = {
                m.get("id") for m in msgs if m.get("role") == "tool" and m.get("error")
            }
            calls = [
                ObservedCall(
                    c["name"], dict(c.get("arguments") or {}), c.get("id") not in failed
                )
                for m in msgs
                if m.get("role") == "assistant" and m.get("tool_calls")
                for c in m["tool_calls"]
            ]
            info = sim.get("reward_info") or {}
            out[str(sim["task_id"])] = Episode(
                str(sim["task_id"]),
                info.get("reward") or 0.0,
                calls,
                info.get("original_reward"),
            )
        return out


def _deep_merge(base: dict, patch: dict) -> dict:
    out = deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out
