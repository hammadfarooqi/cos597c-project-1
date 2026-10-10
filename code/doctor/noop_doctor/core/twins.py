"""Counterfactual twins: build and validate them with the benchmark's own grader.

A twin copies a no-action task and flips one thing so that the write the user asks for
becomes the correct outcome: either one field of the initial state (`patch`) or one
sentence of the policy (`policy_flip`, with an empty patch). The user script stays the same.

Which thing flips is the benchmark-specific part. It comes from a person, an oracle, or a
proposer. This module only checks that a proposed twin does what a twin must do:

    null trajectory  (no calls)           original passes, twin fails
    comply trajectory (gold reads + write) original fails,  twin passes
    the patch changes the state, and only the records it names

The grader here is the adapter's state check, so the test is mechanical. A twin that passes
it can still be implausible for the user script; a person should read a sample.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from noop_doctor.core.calls import ObservedCall
from noop_doctor.core.state import leaf_diff, patch_leaves


@dataclass(frozen=True)
class TwinSpec:
    task_id: str
    name: str
    write: ObservedCall
    patch: dict[str, Any] = field(default_factory=dict)
    why: str = ""
    policy_flip: Optional[str] = None

    @property
    def twin_id(self) -> str:
        return f"{self.task_id}_twin_{self.name}"

    @property
    def kind(self) -> str:
        return "policy" if self.policy_flip or not self.patch else "DB"


@dataclass
class TwinCheck:
    twin_id: str
    fields: int
    effective: bool  # the patch changes the state (always true for a policy flip)
    local: bool
    null_orig: float
    null_twin: float
    comply_orig: float
    comply_twin: float

    @property
    def ok(self) -> bool:
        return (
            self.effective
            and self.local
            and self.null_orig == 1.0
            and self.null_twin == 0.0
            and self.comply_orig == 0.0
            and self.comply_twin == 1.0
        )

    def failures(self) -> list[str]:
        out = []
        if not self.effective:
            out.append("patch changes nothing")
        if not self.local:
            out.append("patch changes records it does not name")
        for name, want in (
            ("null_orig", 1.0),
            ("null_twin", 0.0),
            ("comply_orig", 0.0),
            ("comply_twin", 1.0),
        ):
            if getattr(self, name) != want:
                out.append(f"{name}={getattr(self, name)} (want {want})")
        return out


def validate_twin(adapter, spec: TwinSpec) -> TwinCheck:
    """Check one twin with the adapter's state grader (see the module docstring)."""
    orig = adapter.task(spec.task_id)
    twin = adapter.build_twin(spec)
    comply = adapter.gold_reads(spec.task_id) + [spec.write]
    touched = {p[:-1] for p in patch_leaves(spec.patch)}
    changed = leaf_diff(adapter.state(None), adapter.state(spec.patch or None))
    return TwinCheck(
        twin_id=spec.twin_id,
        fields=len(patch_leaves(spec.patch)),
        effective=bool(changed) or not spec.patch,
        local=all(p[:-1] in touched for p in changed),
        null_orig=adapter.state_reward(orig, []),
        null_twin=adapter.state_reward(twin, []),
        comply_orig=adapter.state_reward(orig, comply),
        comply_twin=adapter.state_reward(twin, comply),
    )
