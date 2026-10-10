"""Review state: one JSON file per benchmark in `<workspace>/reviews/`.

An item is one proposal a person reviews:

    reads   the required reads for one no-op task (a read-gate spec entry)
    twin    one counterfactual twin (a DB patch, or a policy flip, plus the expected write)
    flip    one policy sentence and its replacement

Each item keeps the `proposal` as it came from its source and the `current` version after a
person's edits, a status (pending, approved, rejected), a note, and a history of who did what.
Refreshing the proposals never overwrites an item a person has reviewed or edited.
"""

from __future__ import annotations

import copy
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUSES = ("pending", "approved", "rejected")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ReviewStore:
    def __init__(self, workspace: Path, bench_id: str):
        self.file = workspace / "reviews" / f"{bench_id}.json"
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.data: dict[str, Any] = (
            json.loads(self.file.read_text())
            if self.file.exists()
            else {"checkup": None, "items": {}, "tools": []}
        )

    def save(self) -> None:
        with self.lock:
            tmp = self.file.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=2) + "\n")
            tmp.replace(self.file)

    # --- proposals -----------------------------------------------------------------------

    def upsert_proposal(
        self,
        item_id: str,
        kind: str,
        proposal: dict,
        *,
        task_id: str | None,
        source: str,
        extra: dict | None = None,
    ) -> dict:
        """Add a proposal, or refresh it if no person has touched the item yet."""
        with self.lock:
            items = self.data["items"]
            old = items.get(item_id)
            touched = old and (old["status"] != "pending" or old["edited"])
            if old and touched:
                old["proposal"] = proposal
                old.update(extra or {})
                return old
            item = {
                "id": item_id,
                "kind": kind,
                "task_id": task_id,
                "source": source,
                "proposal": proposal,
                "current": copy.deepcopy(proposal),
                "status": "pending",
                "edited": False,
                "note": "",
                "history": (old or {}).get("history", [])
                + [{"at": now(), "who": "doctor", "action": "proposed", "note": source}],
                "validation": (old or {}).get("validation"),
            } | (extra or {})
            items[item_id] = item
            return item

    def add_manual(self, item_id: str, kind: str, current: dict, task_id, who: str) -> dict:
        with self.lock:
            if item_id in self.data["items"]:
                raise ValueError(f"item {item_id} exists")
            item = {
                "id": item_id,
                "kind": kind,
                "task_id": task_id,
                "source": f"added by {who or 'reviewer'}",
                "proposal": None,
                "current": current,
                "status": "pending",
                "edited": True,
                "note": "",
                "history": [{"at": now(), "who": who, "action": "added", "note": ""}],
                "validation": None,
            }
            self.data["items"][item_id] = item
            self.save()
            return item

    # --- review --------------------------------------------------------------------------

    def get(self, item_id: str) -> dict:
        return self.data["items"][item_id]

    def review(
        self,
        item_id: str,
        who: str,
        *,
        status: str | None = None,
        note: str | None = None,
        current: dict | None = None,
        revert: bool = False,
    ) -> dict:
        with self.lock:
            item = self.get(item_id)
            if revert and item["proposal"] is not None:
                item["current"] = copy.deepcopy(item["proposal"])
                item["edited"] = False
                item["validation"] = None
                item["history"].append({"at": now(), "who": who, "action": "reverted"})
            if current is not None and current != item["current"]:
                item["current"] = current
                item["edited"] = item["proposal"] is None or current != item["proposal"]
                item["validation"] = None
                item["history"].append({"at": now(), "who": who, "action": "edited"})
            if note is not None and note != item["note"]:
                item["note"] = note
            if status is not None and status != item["status"]:
                if status not in STATUSES:
                    raise ValueError(f"status must be one of {STATUSES}")
                item["status"] = status
                item["history"].append(
                    {"at": now(), "who": who, "action": status, "note": note or ""}
                )
            self.save()
            return item

    def set_validation(self, item_id: str, validation: dict) -> None:
        with self.lock:
            self.data["items"][item_id]["validation"] = validation | {"at": now()}
            self.save()

    def remove(self, item_id: str) -> None:
        with self.lock:
            item = self.get(item_id)
            if item["proposal"] is not None:
                raise ValueError("only items a person added can be deleted; reject it instead")
            del self.data["items"][item_id]
            self.save()

    def counts(self) -> dict:
        out = {s: 0 for s in STATUSES}
        for it in self.data["items"].values():
            out[it["status"]] += 1
        return out
