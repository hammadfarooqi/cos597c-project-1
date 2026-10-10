"""Helpers for JSON-like state: leaf differences and patch leaves."""

from __future__ import annotations


def leaf_diff(a, b, path=()) -> list[tuple]:
    """Every leaf path where two JSON-like values differ."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in set(a) | set(b):
            out += leaf_diff(a.get(k), b.get(k), path + (k,))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += leaf_diff(x, y, path + (i,))
        return out
    return [] if a == b else [path]


def patch_leaves(patch, path=()) -> list[tuple]:
    if isinstance(patch, dict) and patch:
        return [p for k, v in patch.items() for p in patch_leaves(v, path + (k,))]
    return [path] if path else []
