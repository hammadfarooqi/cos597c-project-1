"""Count the behaviour patterns behind the scoreboard numbers.

The scoreboard says how many no-action passes each check removes. This script
says what the agents did: how often they transfer, whether they looked anything
up first, whether they guessed a user ID, and whether their outcome changes
when the decisive fact changes (base task vs. its twin).

Reads the same saved runs as scoreboard.py. No LLM calls. Prints Markdown.
Analysis: docs/research/qualitative-patterns.md.

Usage (from code/tau2-bench/):
  uv run python ../transcript_patterns.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scoreboard import (  # noqa: E402
    NO_ACTION,
    SIM,
    agent_calls,
    load_all,
    models,
    twin_map,
    upstream_pass,
)

TRANSFER = "transfer_to_human_agents"
READS = {
    "get_user_details",
    "get_reservation_details",
    "get_flight_status",
    "search_direct_flight",
    "search_onestop_flight",
}
WRITES = {
    "book_reservation",
    "cancel_reservation",
    "send_certificate",
    "update_reservation_baggages",
    "update_reservation_flights",
    "update_reservation_passengers",
}


def guessed_user_id(sim: dict) -> bool:
    """A get_user_details call on an ID the user had not said yet."""
    said = ""
    for m in sim.get("messages") or []:
        if m["role"] == "user":
            said += m.get("content") or ""
        for c in (m.get("tool_calls") or []) if m["role"] == "assistant" else []:
            uid = str(c["arguments"].get("user_id", ""))
            if c["name"] == "get_user_details" and uid and uid not in said:
                return True
    return False


def blind_transfer(sim: dict) -> bool:
    """A transfer before any successful read."""
    for c in agent_calls(sim):
        if c.name == TRANSFER:
            return True
        if c.name in READS and c.succeeded:
            return False
    return False


def outcome(sim: dict) -> str:
    calls = agent_calls(sim)
    if any(c.name in WRITES and c.succeeded for c in calls):
        return "write"
    if any(c.name == TRANSFER for c in calls):
        return "transfer"
    return "none"


def main():
    twin_of, kinds, _ = twin_map()
    na = {str(t) for t in NO_ACTION}
    rows = []
    for m in models():
        base = load_all(SIM / f"airline_{m}" / "results.json")
        twins = load_all(SIM / f"airline_twins_{m}" / "results.json")
        pf = SIM / f"airline_twins_pf_{m}" / "results.json"
        if pf.exists():
            twins |= load_all(pf)
        sims = [s for t in base.values() for s in t.values()]
        na_pass = [
            s
            for t, ts in base.items()
            if t in na
            for s in ts.values()
            if upstream_pass(s)
        ]
        pairs = same = both_transfer = 0
        for t, tw in twin_of.items():
            if t not in base or tw not in twins:
                continue
            for k, s in base[t].items():
                if k not in twins[tw]:
                    continue
                a, b = outcome(s), outcome(twins[tw][k])
                pairs += 1
                same += a == b
                both_transfer += a == b == "transfer"
        rows.append(
            [
                m,
                f"{sum(any(c.name == TRANSFER for c in agent_calls(s)) for s in sims)} / {len(sims)}",
                f"{sum(blind_transfer(s) for s in sims)} / {len(sims)}",
                f"{sum(guessed_user_id(s) for s in sims)} / {len(sims)}",
                f"{sum(blind_transfer(s) for s in na_pass)} / {len(na_pass)}",
                f"{same} / {pairs}",
                f"{both_transfer} / {pairs}",
            ]
        )
    head = [
        "Model",
        "Episodes with a transfer (50 tasks)",
        "Transfer before any successful read",
        "Guessed user ID",
        "No-action passes that are blind transfers",
        "Same outcome on task and twin",
        "Transfer on both task and twin",
    ]
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for r in rows:
        print("| " + " | ".join(r) + " |")


if __name__ == "__main__":
    main()
