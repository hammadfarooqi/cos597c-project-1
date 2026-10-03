"""Executable form of parts of the airline policy.

The airline tools do not enforce the policy ("The API does not check that
cancellation rules are met", policy.md, Cancel flight). The twin generator
needs an oracle that says whether a write is allowed in a given database
state. This module is that oracle. It reads a plain dict dump of FlightDB.

Encoded: cancellation, the cancelled-flight certificate, and the delayed-flight
certificate. Not encoded: flight changes, cabin changes, baggage.

RULES holds the switchable rules. A policy flip (policy_flips.yaml) changes one
sentence of policy.md and the matching entry here, so the text and the oracle
flip together.
"""

from datetime import datetime, timedelta

# policy.md: "The current time is 2024-05-15 15:00:00 EST."
NOW = datetime(2024, 5, 15, 15, 0, 0)

# policy.md, Book flight: insurance "enables full refund if the user needs to
# cancel the flight given health or weather reasons".
COVERED_REASONS = {"health", "weather"}

FLOWN_STATUSES = {"landed", "flying"}

# Switchable rules, at their policy.md values.
RULES = {
    # "...and wants to change or cancel the reservation, the agent can offer a
    # certificate ... after confirming the facts and changing or cancelling".
    "delay_certificate_requires_change": True,
}


def _flight_status(db: dict, flight_number: str, date: str) -> str | None:
    return db["flights"][flight_number]["dates"].get(date, {}).get("status")


def any_portion_flown(db: dict, reservation_id: str) -> bool:
    """True if any flight in the reservation has departed."""
    res = db["reservations"][reservation_id]
    for f in res["flights"]:
        if _flight_status(db, f["flight_number"], f["date"]) in FLOWN_STATUSES:
            return True
        if datetime.fromisoformat(f["date"]).date() < NOW.date():
            return True
    return False


def cancel_conditions(db: dict, reservation_id: str, reason: str) -> dict[str, bool]:
    """The four policy conditions, any one of which permits a cancellation."""
    res = db["reservations"][reservation_id]
    created = datetime.fromisoformat(res["created_at"])
    return {
        "within_24h": NOW - timedelta(hours=24) < created <= NOW,
        "airline_cancelled": any(
            _flight_status(db, f["flight_number"], f["date"]) == "cancelled"
            for f in res["flights"]
        ),
        "business": res["cabin"] == "business",
        "insured_and_covered": res["insurance"] == "yes" and reason in COVERED_REASONS,
    }


def can_cancel(db: dict, reservation_id: str, reason: str) -> bool:
    """Policy verdict for cancel_reservation(reservation_id) with this reason."""
    res = db["reservations"][reservation_id]
    if res.get("status") == "cancelled":
        return False
    if any_portion_flown(db, reservation_id):
        return False  # policy: the agent cannot help; transfer
    return any(cancel_conditions(db, reservation_id, reason).values())


def cancelled_flight_certificate(
    db: dict, user_id: str, reservation_id: str
) -> int | None:
    """Certificate amount the policy allows for a cancelled flight, or None.

    policy.md, Refunds and Compensation: compensate only a silver/gold member,
    or a reservation with insurance, or a business reservation. For cancelled
    flights the amount is $100 times the number of passengers.
    """
    res = db["reservations"][reservation_id]
    if res["user_id"] != user_id:
        return None
    eligible = compensation_eligible(db, user_id, reservation_id)
    has_cancelled = any(
        _flight_status(db, f["flight_number"], f["date"]) == "cancelled"
        for f in res["flights"]
    )
    if eligible and has_cancelled:
        return 100 * len(res["passengers"])
    return None


def compensation_eligible(db: dict, user_id: str, reservation_id: str) -> bool:
    """policy.md: only a silver/gold member, insurance, or business cabin."""
    user = db["users"][user_id]
    res = db["reservations"][reservation_id]
    return (
        user["membership"] in {"silver", "gold"}
        or res["insurance"] == "yes"
        or res["cabin"] == "business"
    )


def delayed_flight_certificate(
    db: dict,
    user_id: str,
    reservation_id: str,
    wants_change_or_cancel: bool,
    rules: dict = RULES,
) -> int | None:
    """Certificate amount the policy allows for a delayed flight, or None.

    $50 times the number of passengers, for an eligible user, if a flight in
    the reservation is delayed and (unless the rule is flipped) the user wants
    to change or cancel the reservation.
    """
    res = db["reservations"][reservation_id]
    if res["user_id"] != user_id or not compensation_eligible(
        db, user_id, reservation_id
    ):
        return None
    if not any(
        _flight_status(db, f["flight_number"], f["date"]) == "delayed"
        for f in res["flights"]
    ):
        return None
    if rules["delay_certificate_requires_change"] and not wants_change_or_cancel:
        return None
    return 50 * len(res["passengers"])


# One-field edits that make one cancellation condition true.
# Each maps a condition to (field, value). "airline_cancelled" is left out:
# a cancelled flight date has a different record shape, so the edit is not a
# one-field deep merge.
CANCEL_ENABLING_EDITS = {
    "within_24h": ("created_at", (NOW - timedelta(hours=5)).isoformat()),
    "business": ("cabin", "business"),
    "insured_and_covered": ("insurance", "yes"),
}
