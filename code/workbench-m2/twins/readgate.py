"""The read gate for WorkBench no-op tasks (COS597C, M2).

Rule: a no-op pass is justified by its reads if the agent made at least one read
call whose output differs between the task's start state and its DB twin's start
state. The twin flips the deciding fact, so such a read looked where the
counter-evidence would be. The rule is fixed by the twin patch; it needs no
hand-written list of acceptable queries.

Read tools are WorkBench's tools without side effects (src/tools/toolkits.py).
Calls are parsed exactly as the upstream scorer parses them (src/evals/actions.py).
"""

from __future__ import annotations

import ast
import sys

sys.path.insert(0, ".")

from src.evals.actions import _TOOL_DISPATCH  # noqa: E402
from src.tools.state import set_state_patch  # noqa: E402
from src.tools.toolkits import tools_with_side_effects  # noqa: E402

WRITE_TOOLS = {t.name for t in tools_with_side_effects}
READ_TOOLS = set(_TOOL_DISPATCH) - WRITE_TOOLS


def parse_call(action: str) -> tuple[str, dict[str, str]] | None:
    """Same parsing as src/evals/actions.py::_parse_and_dispatch; None if unparsable."""
    try:
        call = ast.parse(action, mode="eval").body
    except SyntaxError:
        return None
    if not isinstance(call, ast.Call):
        return None
    parts: list[str] = []
    node = call.func
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    parts.reverse()
    parts = parts[:-1] if len(parts) >= 3 and parts[-1] == "func" else parts
    kwargs: dict[str, str] = {}
    try:
        for kw in call.keywords:
            if kw.arg is not None:
                kwargs[kw.arg] = str(ast.literal_eval(kw.value))
    except (ValueError, SyntaxError):
        return None
    return ".".join(parts), kwargs


def tool_name(action: str) -> str:
    parsed = parse_call(action)
    return parsed[0] if parsed else ""


def is_read(action: str) -> bool:
    return tool_name(action) in READ_TOOLS


def is_write(action: str) -> bool:
    return tool_name(action) in WRITE_TOOLS


def read_output(action: str, patch: list[dict] | None) -> str:
    """Run one read call on the start state (with ``patch``) and return its output."""
    parsed = parse_call(action)
    if parsed is None or parsed[0] not in READ_TOOLS:
        return "<not a read>"
    name, kwargs = parsed
    set_state_patch(patch)
    try:
        return str(_TOOL_DISPATCH[name](**kwargs))
    except Exception as e:  # a bad call reveals nothing
        return f"<error {type(e).__name__}>"
    finally:
        set_state_patch(None)


def revealing_reads(actions: list[str], twin_patch: list[dict]) -> list[str]:
    """The read calls whose output differs between the start state and the twin's."""
    return [a for a in actions if is_read(a) and read_output(a, None) != read_output(a, twin_patch)]


def passes_read_gate(actions: list[str], twin_patch: list[dict]) -> bool:
    return bool(revealing_reads(actions, twin_patch))
