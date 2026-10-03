# Copyright Sierra
from functools import partial
from pathlib import Path
from typing import Callable, Optional

from tau2.data_model.tasks import Task
from tau2.domains.airline.data_model import FlightDB
from tau2.domains.airline.tools import AirlineTools
from tau2.domains.airline.utils import (
    AIRLINE_DB_PATH,
    AIRLINE_POLICY_FLIPS_DIR,
    AIRLINE_POLICY_PATH,
    AIRLINE_TASK_SET_PATH,
    AIRLINE_TWIN_TASK_SET_PATH,
)
from tau2.environment.environment import Environment
from tau2.utils import load_file


def get_environment(
    db: Optional[FlightDB] = None,
    solo_mode: bool = False,
    policy_path: Path = AIRLINE_POLICY_PATH,
) -> Environment:
    """policy_path selects a policy variant (see get_policy_flip_environments)."""
    if solo_mode:
        raise ValueError("Airline domain does not support solo mode")
    if db is None:
        db = FlightDB.load(AIRLINE_DB_PATH)
    tools = AirlineTools(db)
    with open(policy_path, "r") as fp:
        policy = fp.read()
    return Environment(
        domain_name="airline",
        policy=policy,
        tools=tools,
    )


def get_tasks(task_split_name: Optional[str] = "base") -> list[Task]:
    tasks = load_file(AIRLINE_TASK_SET_PATH)
    tasks = [Task.model_validate(task) for task in tasks]
    if task_split_name is None:
        return tasks
    task_splits = get_tasks_split()
    if task_split_name not in task_splits:
        raise ValueError(
            f"Invalid task split name: {task_split_name}. Valid splits are: {task_splits.keys()}"
        )
    return [task for task in tasks if task.id in task_splits[task_split_name]]


def get_tasks_split() -> dict[str, list[str]]:
    split_file = (
        Path(AIRLINE_TASK_SET_PATH).parent
        / f"split_{Path(AIRLINE_TASK_SET_PATH).stem}.json"
    )
    return load_file(split_file)


def get_twin_tasks(task_split_name: Optional[str] = "base") -> list[Task]:
    """Counterfactual twins of the no-action tasks (built by code/twins/generate.py)."""
    tasks = [Task.model_validate(t) for t in load_file(AIRLINE_TWIN_TASK_SET_PATH)]
    if task_split_name is None:
        return tasks
    split = get_twin_tasks_split()
    if task_split_name not in split:
        raise ValueError(
            f"Invalid task split name: {task_split_name}. Valid splits are: {split.keys()}"
        )
    return [task for task in tasks if task.id in split[task_split_name]]


def get_twin_tasks_split() -> dict[str, list[str]]:
    return load_file(AIRLINE_TWIN_TASK_SET_PATH.parent / "split_tasks_twins.json")


def get_policy_flip_environments() -> dict[str, Callable[..., Environment]]:
    """One environment per flipped policy (built by code/twins/generate.py).

    Each has the airline tools and DB and a policy with one sentence changed.
    Registered as the domain airline_pf_<flip id>.
    """
    if not AIRLINE_POLICY_FLIPS_DIR.exists():
        return {}
    return {
        f"airline_pf_{p.stem}": partial(get_environment, policy_path=p)
        for p in sorted(AIRLINE_POLICY_FLIPS_DIR.glob("*.md"))
    }
