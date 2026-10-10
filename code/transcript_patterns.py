"""Count the behaviour patterns behind the scoreboard numbers.

The scoreboard says how many no-action passes each check removes. This script
says what the agents did: how often they transfer, whether they looked anything
up first, whether they guessed a user ID, whether their outcome changes when the
decisive fact changes (base task vs. its twin), and how they make writes: as text
that never runs, or before reading the reservation they change.

Reads the same saved runs as scoreboard.py. No LLM calls. Prints Markdown.
Analysis: docs/research/new-models/qualitative-patterns.md (newer models) and
docs/research/qualitative-patterns.md (older models).

Counts cover every trial (seed) of each model; the task in trial N is paired with
its twin in trial N. Use --seed 300 to count one trial only.

Usage (from code/tau2-bench/):
  uv run python ../transcript_patterns.py               # newer models, all trials
  uv run python ../transcript_patterns.py --seed 300    # newer models, trial 1 only
  uv run python ../transcript_patterns.py --set old     # older models
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scoreboard import (  # noqa: E402
    NO_ACTION,
    agent_calls,
    load_all,
    models,
    trial_runs,
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

# A tool call written into the agent's text, e.g. "[cancel_reservation(reservation_id=...)]".
TEXT_CALL = re.compile(r"\b(" + "|".join(sorted(WRITES | {TRANSFER})) + r")\s*\(")


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


def silent_transfer(sim: dict) -> bool:
    """A transfer in the same agent turn as a successful read, with no reply between:
    the agent looks at the record and hands off without telling the customer."""
    failed = {
        m["id"]
        for m in sim.get("messages") or []
        if m["role"] == "tool" and m.get("error")
    }
    read = False
    for m in sim.get("messages") or []:
        if m["role"] == "user" or (m["role"] == "assistant" and m.get("content")):
            read = False
        for c in (m.get("tool_calls") or []) if m["role"] == "assistant" else []:
            if c["name"] == TRANSFER:
                return read
            if c["name"] in READS and c["id"] not in failed:
                read = True
    return False


def phantom_writes(sim: dict) -> set[str]:
    """Writes (or transfers) the agent wrote as text and never made as a tool call
    later in the episode. The customer is often told the action is done."""
    msgs = sim.get("messages") or []
    out = set()
    for i, m in enumerate(msgs):
        if m["role"] != "assistant":
            continue
        later = {
            c["name"]
            for x in msgs[i:]
            if x["role"] == "assistant"
            for c in x.get("tool_calls") or []
        }
        out |= set(TEXT_CALL.findall(m.get("content") or "")) - later
    return out


def write_before_read(sim: dict) -> bool:
    """A successful write on a reservation that the agent had not read successfully."""
    seen = set()
    for c in agent_calls(sim):
        rid = c.arguments.get("reservation_id")
        if c.name == "get_reservation_details" and c.succeeded:
            seen.add(rid)
        if c.name in WRITES and c.succeeded and rid and rid not in seen:
            return True
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
    rows, rows2 = [], []
    set_name = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else "new"
    only = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else None
    for m in models(set_name):
        base, twins = {}, {}
        for seed, (b, *tws) in trial_runs(m).items():
            if only is not None and seed != only:
                continue
            for tid, trials in load_all(b / "results.json").items():
                base.setdefault(tid, {}).update(
                    {(seed, k): s for k, s in trials.items()}
                )
            for d in tws:
                for tid, trials in load_all(d / "results.json").items():
                    twins.setdefault(tid, {}).update(
                        {(seed, k): s for k, s in trials.items()}
                    )
        sims = [s for t in base.values() for s in t.values()]
        tw_sims = [s for t in twins.values() for s in t.values()]
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
                same += (a == "write") == (b == "write")
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
        na_sims = [s for t, ts in base.items() if t in na for s in ts.values()]
        allw = sims + tw_sims
        rows2.append(
            [
                m,
                f"{sum(silent_transfer(s) for s in na_sims)} / {len(na_sims)}",
                f"{sum(bool(phantom_writes(s) - {TRANSFER}) for s in allw)} / {len(allw)}",
                f"{sum(bool(phantom_writes(s) - {TRANSFER}) for s in na_pass)} / {len(na_pass)}",
                f"{sum(write_before_read(s) for s in allw)} / {len(allw)}",
            ]
        )
    head = [
        "Model",
        "Episodes with a transfer (50 tasks × trials)",
        "Transfer before any successful read",
        "Guessed user ID",
        "No-action passes that are blind transfers",
        "Same decision on task and twin (write or not)",
        "Transfer on both task and twin",
    ]
    head2 = [
        "Model",
        "Silent transfers (no-action tasks)",
        "Episodes with a write typed as text, never run (tasks + twins)",
        "No-action passes with such a write",
        "Write on a reservation before reading it (tasks + twins)",
    ]
    for h, rs in [(head, rows), (head2, rows2)]:
        print("| " + " | ".join(h) + " |")
        print("|" + "---|" * len(h))
        for r in rs:
            print("| " + " | ".join(r) + " |")
        print()


if __name__ == "__main__":
    main()
