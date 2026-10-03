"""Executable form of the airline cancellation policy.

The airline tools do not enforce the policy ("The API does not check that
cancellation rules are met", policy.md, Cancel flight). The twin generator
needs an oracle that says whether a write is allowed in a given database
state. This module is that oracle. It reads a plain dict dump of FlightDB.

Only the cancellation rules are encoded so far. Change, cabin, baggage and
compensation rules are not.
"""

from datetime import datetime, timedelta

# policy.md: "The current time is 2024-05-15 15:00:00 EST."
NOW = datetime(2024, 5, 15, 15, 0, 0)

# policy.md, Book flight: insurance "enables full refund if the user needs to
# cancel the flight given health or weather reasons".
COVERED_REASONS = {"health", "weather"}

FLOWN_STATUSES = {"landed", "flying"}


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
    user = db["users"][user_id]
    res = db["reservations"][reservation_id]
    if res["user_id"] != user_id:
        return None
    eligible = (
        user["membership"] in {"silver", "gold"}
        or res["insurance"] == "yes"
        or res["cabin"] == "business"
    )
    has_cancelled = any(
        _flight_status(db, f["flight_number"], f["date"]) == "cancelled"
        for f in res["flights"]
    )
    if eligible and has_cancelled:
        return 100 * len(res["passengers"])
    return None


# One-field edits that make one cancellation condition true.
# Each maps a condition to (field, value). "airline_cancelled" is left out:
# a cancelled flight date has a different record shape, so the edit is not a
# one-field deep merge.
CANCEL_ENABLING_EDITS = {
    "within_24h": ("created_at", (NOW - timedelta(hours=5)).isoformat()),
    "business": ("cabin", "business"),
    "insured_and_covered": ("insurance", "yes"),
}
