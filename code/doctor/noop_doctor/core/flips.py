"""Policy flips: replace exactly one sentence of a policy text."""

from __future__ import annotations

from typing import Any


def apply_flip(policy: str, original: str, replacement: str) -> str:
    n = policy.count(original)
    if n != 1:
        raise ValueError(f"original sentence found {n} times in the policy (need 1)")
    return policy.replace(original, replacement)


def apply_flips(policy: str, flips: dict[str, Any]) -> dict[str, str]:
    """`flips` maps an id to {original, replacement, ...}. Returns id -> flipped policy."""
    out = {}
    for fid, flip in flips.items():
        try:
            out[fid] = apply_flip(policy, flip["original"], flip["replacement"])
        except ValueError as e:
            raise ValueError(f"flip {fid}: {e}") from None
    return out
