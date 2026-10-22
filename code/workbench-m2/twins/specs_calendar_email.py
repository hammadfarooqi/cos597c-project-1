"""Template specs: calendar, email, and the multi-domain templates whose condition is
in the calendar, the inbox, the project board or the CRM contact history.

See framework.py for the contract. Each gold rule mirrors the upstream logic
function named in its comment (scripts/data_generation/task_outcome_generation/).
"""

from __future__ import annotations

import pandas as pd
from framework import register

from src.data_generation.data_generation_utils import HARDCODED_CURRENT_TIME

NOW = str(HARDCODED_CURRENT_TIME)


def _next_event_id(s) -> str:
    return f"{int(s.calendar_events['event_id'].astype(int).max()) + 1:08d}"


# --- Cancel future {event_name} meetings -------------------------------------
# upstream: generate_calendar_task_and_outcome.cancel_future_meetings_with_name_logic


def _future_named(p, s) -> pd.DataFrame:
    ev = s.calendar_events
    # The generator lower-cases the name on the action branch only, so match without case.
    return ev[(ev["event_name"].str.lower() == p["event_name"].lower()) & (ev["event_start"] > NOW)]


def cancel_future_named_gold(p, s):
    return [f'calendar.delete_event.func(event_id="{i}")' for i in _future_named(p, s)["event_id"]]


def cancel_future_named_flip(p, s):
    ev = s.calendar_events
    past = ev[ev["event_name"].str.lower() == p["event_name"].lower()].sort_values("event_start")
    if past.empty:
        raise ValueError(f"no {p['event_name']!r} event to copy")
    last = past.iloc[-1]
    # One new future occurrence of the series: same name, participant and length, on
    # Tuesday 2023-12-05 (a work day inside the calendar's range), at the series' time of
    # day if that slot is free, else at the first free generator start time that ends by
    # 18:00 (the twin review found an overlap at the series' time for calendar-091).
    dur = int(last["duration"])
    times = [last["event_start"].split(" ")[1]] + WORK_TIMES
    fits = [t for t in times if _slot_free(s, "2023-12-05", t, dur, last["event_name"])
            and pd.Timestamp(f"2023-12-05 {t}") + pd.Timedelta(minutes=dur) <= pd.Timestamp("2023-12-05 18:00:00")]
    if not fits:
        raise ValueError("no free slot on 2023-12-05")
    start = "2023-12-05 " + fits[0]
    row = {"event_id": _next_event_id(s), "event_name": last["event_name"],
           "participant_email": last["participant_email"], "event_start": start, "duration": last["duration"]}
    why = f"A future '{last['event_name']}' meeting now exists on {start}, so there is one to cancel."
    return [{"table": "calendar_events", "op": "append", "row": row}], why


register("Cancel future {event_name} meetings", cancel_future_named_gold, cancel_future_named_flip)


# =============================================================================
# Shared helpers for the templates below.
# =============================================================================

import re  # noqa: E402

from src.data_generation.data_generation_utils import (  # noqa: E402
    get_first_free_slot,
    get_natural_language_time,
)

TODAY = HARDCODED_CURRENT_TIME.normalize()  # 2023-11-30 00:00:00
CAL_FIRST = pd.Timestamp("2023-08-01")  # the calendar's range (data_generation_utils)
CAL_LAST = pd.Timestamp("2023-12-21")


def _day(offset: int) -> str:
    """The date ``offset`` days from today (2023-11-30), as YYYY-MM-DD."""
    return str((TODAY + pd.Timedelta(days=offset)).date())


def _email_of(s, name: str) -> str:
    """The directory email whose first name is ``name`` (first names are unique)."""
    d = s.directory_emails["email_address"]
    hit = d[d.str.split("@").str[0].str.split(".").str[0] == name.lower()]
    if len(hit) != 1:
        raise ValueError(f"name {name!r} matches {len(hit)} directory emails")
    return hit.iloc[0]


def _first_free_tomorrow_action(s, event_name: str, participant: str, duration_minutes: int = 30) -> str:
    """Mirror of generate_calendar_task_and_outcome.create_event_on_first_free_slot_tomorrow."""
    ev = s.calendar_events
    tomorrow, following = _day(1), _day(2)
    day = ev["event_start"].str.split(" ").str[0]
    events_on_date = ev[(day >= tomorrow) & (day < following)]
    first_free_time = get_first_free_slot(tomorrow, events_on_date, duration_minutes)
    return (
        f'calendar.create_event.func(event_name="{event_name}", participant_email="{participant}", '
        f'event_start="{first_free_time}", duration="{duration_minutes}")'
    )


def _slot_free(s, date: str, hhmmss: str, duration: int, event_name: str, exclude_id: str | None = None) -> bool:
    """True if [date hhmmss, +duration) overlaps no event on ``date`` and no event on that
    date has the same name (the calendar generator's two constraints), ignoring ``exclude_id``."""
    ev = s.calendar_events
    ev = ev[(ev["event_start"].str[:10] == date) & (ev["event_id"] != exclude_id)]
    if (ev["event_name"].str.lower() == event_name.lower()).any():
        return False
    start = pd.Timestamp(f"{date} {hhmmss}")
    end = start + pd.Timedelta(minutes=duration)
    for _, r in ev.iterrows():
        rs = pd.Timestamp(r["event_start"])
        re_ = rs + pd.Timedelta(minutes=int(r["duration"]))
        if start < re_ and rs < end:
            return False
    return True


WORK_TIMES = [f"{h:02d}:{m:02d}:00" for h in range(9, 16) for m in (0, 30)]  # generator start times


def _move_event_patch(s, row, bound: str, step: int) -> dict:
    """A 'set' edit that moves event ``row`` to the nearest work day at or beyond ``bound``
    (step -1 searches earlier, +1 later) with a free slot. It keeps the time of day when
    that slot is free, else takes the nearest free generator start time (09:00-15:30)."""
    d = pd.Timestamp(bound)
    hhmmss = row["event_start"].split(" ")[1]
    t0 = pd.Timestamp(f"2000-01-01 {hhmmss}")
    times = sorted(WORK_TIMES, key=lambda x: (x != hhmmss, abs(pd.Timestamp(f"2000-01-01 {x}") - t0), x))
    while CAL_FIRST <= d <= CAL_LAST:
        if d.dayofweek < 5:
            for t in times:
                if _slot_free(s, str(d.date()), t, int(row["duration"]), row["event_name"], row["event_id"]):
                    return {"table": "calendar_events", "op": "set", "where": {"event_id": row["event_id"]},
                            "values": {"event_start": f"{d.date()} {t}"}}
        d += pd.Timedelta(days=step)
    raise ValueError(f"no free day to move event {row['event_id']}")


def _move_events(s, rows: pd.DataFrame, bound: str, step: int) -> list[dict]:
    """Move several events one by one (each sees the earlier moves), nearest to ``bound``."""
    tmp, patch = s.copy(), []
    order = rows.sort_values("event_start", ascending=(step > 0))
    for _, r in order.iterrows():
        edit = _move_event_patch(tmp, r, bound, step)
        patch.append(edit)
        tmp.calendar_events.loc[tmp.calendar_events["event_id"] == r["event_id"], "event_start"] = edit["values"]["event_start"]
    return patch


def _describe_moves(s, patch: list[dict], table: str = "calendar_events") -> str:
    df = getattr(s, table)
    key, col, label = (("event_id", "event_start", "event_name") if table == "calendar_events"
                       else ("email_id", "sent_datetime", "subject"))
    out = []
    for e in patch:
        r = df[df[key] == e["where"][key]].iloc[0]
        out.append(f"'{r[label]}' ({r[col]} -> {e['values'][col]})")
    return ", ".join(out)


def _move_emails(s, rows: pd.DataFrame, bound: str) -> list[dict]:
    """'set' edits that move emails ``rows`` earlier, one per day: the latest to the nearest
    day at or before ``bound``, the next one to an earlier day, and so on. Each keeps its
    time of day and lands on a day with no other email with the same subject (the email
    generator's constraint). The order of the emails is kept."""
    em = s.emails
    d = pd.Timestamp(bound)
    patch = []
    for _, row in rows.sort_values("sent_datetime", ascending=False).iterrows():
        hhmmss = row["sent_datetime"].split(" ")[1]
        while True:
            if d < pd.Timestamp("2023-10-01"):
                raise ValueError(f"no day to move email {row['email_id']}")
            same_day = em[(em["sent_datetime"].str[:10] == str(d.date())) & (em["email_id"] != row["email_id"])]
            if row["subject"] not in same_day["subject"].values:
                break
            d -= pd.Timedelta(days=1)
        patch.append({"table": "emails", "op": "set", "where": {"email_id": row["email_id"]},
                      "values": {"sent_datetime": f"{d.date()} {hhmmss}"}})
        d -= pd.Timedelta(days=1)
    return patch


def _shift(date: str, days: int) -> str:
    return str((pd.Timestamp(date) + pd.Timedelta(days=days)).date())


def _nearest_first(values, original):
    return sorted((v for v in values if v != original), key=lambda v: (abs(v - original), v))


# --- Cancel my next meeting with {name} ---------------------------------------
# upstream: generate_calendar_task_and_outcome.cancel_next_event_with_name_logic


def cancel_next_with_gold(p, s):
    ev = s.calendar_events
    mine = ev[(ev["participant_email"] == _email_of(s, p["name"])) & (ev["event_start"] > NOW)]
    if mine.empty:
        return []
    return [f'calendar.delete_event.func(event_id="{mine.sort_values("event_start").iloc[0]["event_id"]}")']


def cancel_next_with_flip(p, s):
    email = _email_of(s, p["name"])
    ev = s.calendar_events
    past = ev[ev["participant_email"] == email].sort_values("event_start")
    last = past.iloc[-1]
    # One new future meeting: a repeat of the last meeting with this person (same name
    # and length) on the first work day after tomorrow with a free slot (its old time
    # of day if free, else the nearest free start). It is the only future meeting with
    # them, so "next" has no tie.
    patch_set = _move_event_patch(s, {**last, "event_id": "none"}, _day(2), +1)
    start = patch_set["values"]["event_start"]
    row = {"event_id": _next_event_id(s), "event_name": last["event_name"], "participant_email": email,
           "event_start": start, "duration": last["duration"]}
    why = (f"A meeting '{last['event_name']}' with {p['name']} is now on the calendar for {start}; it is the "
           f"only future meeting with them, so it is the next one and must be cancelled.")
    return [{"table": "calendar_events", "op": "append", "row": row}], why


register("Cancel my next meeting with {name}", cancel_next_with_gold, cancel_next_with_flip)


# --- If I haven't met with {name} in the last {duration} days, schedule ... ------
# upstream: generate_calendar_task_and_outcome.check_last_meeting_with_name_schedule_30_tomorrow


def _met_in_last(s, email: str, days: int) -> pd.DataFrame:
    ev = s.calendar_events
    lo = str(HARDCODED_CURRENT_TIME - pd.Timedelta(days=days))
    return ev[(ev["participant_email"] == email) & (ev["event_start"] > lo) & (ev["event_start"] < NOW)]


def catchup_gold(p, s):
    email = _email_of(s, p["name"])
    if len(_met_in_last(s, email, int(p["duration"]))):
        return []
    return [_first_free_tomorrow_action(s, "catch-up", email, 30)]


def catchup_flip(p, s):
    email, d = _email_of(s, p["name"]), int(p["duration"])
    recent = _met_in_last(s, email, d)
    # Move each meeting inside the window to a work day at least 2 days before the
    # window's first day (free slot, same time of day where possible). Tomorrow is not
    # touched, so the first free slot is unchanged.
    patch = _move_events(s, recent, _day(-d - 2), -1)
    moved = _describe_moves(s, patch)
    why = (f"{len(patch)} meeting(s) with {p['name']} in the last {d} days now took place earlier: {moved}. "
           f"So I have not met {p['name']} in the last {d} days and the catch-up must be booked.")
    return patch, why


def catchup_request(p, s):
    email, d = _email_of(s, p["name"]), int(p["duration"])
    for d2 in _nearest_first(range(1, 11), d):  # generator: random.randint(1, 10)
        if d2 < d and not len(_met_in_last(s, email, d2)):
            past = s.calendar_events[(s.calendar_events["participant_email"] == email) & (s.calendar_events["event_start"] < NOW)]
            last = past["event_start"].max()
            # gold-true implies the last meeting is dated before the window's first day
            new_p = {**p, "duration": d2}
            return new_p, (f"The window shrinks from {d} to {d2} days; my last meeting with {p['name']} was on "
                           f"{last[:10]}, before the window, so the catch-up must be booked.")
    return None


register(
    "If I haven't met with {name} in the last {duration} days, schedule a 30-minute meeting called 'catch-up' for my first free slot from tomorrow",
    catchup_gold, catchup_flip, catchup_request,
)


# --- Cancel my meetings on {next_day} {before_or_after} {natural_language_time} --
# upstream: generate_calendar_task_and_outcome.cancel_events_on_day_logic


def _date_of_next_day(day_name: str) -> str:
    for i in range(1, 8):
        if (TODAY + pd.Timedelta(days=i)).day_name() == day_name:
            return _day(i)
    raise ValueError(day_name)


def _time_of_nl(nl: str) -> str:
    """Inverse of get_natural_language_time for the calendar's times (09:00 to 15:30)."""
    h, _, m = nl.partition(":")
    h = int(h)
    h = h + 12 if h < 9 else h
    return f"{h:02d}:{m or '00'}:00"


def _events_to_cancel(p, s) -> pd.DataFrame:
    ev = s.calendar_events
    on = ev[ev["event_start"].str.split(" ").str[0] == _date_of_next_day(p["next_day"])]
    t = _time_of_nl(p["natural_language_time"])
    hm = on["event_start"].str.split(" ").str[1]
    return on[hm < t] if p["before_or_after"] == "before" else on[hm > t]


def cancel_day_gold(p, s):
    return [f'calendar.delete_event.func(event_id="{i}")' for i in _events_to_cancel(p, s)["event_id"]]


def cancel_day_flip(p, s):
    date = _date_of_next_day(p["next_day"])
    t = _time_of_nl(p["natural_language_time"])
    # One new 30-minute meeting on that day, clearly on the asked side of the time:
    # it ends 30+ minutes before the time ("before"), or starts 30 minutes after the
    # time and after the last meeting of the day has ended ("after").
    if p["before_or_after"] == "before":
        start = (pd.Timestamp(f"{date} {t}") - pd.Timedelta(minutes=60))
    else:
        start = (pd.Timestamp(f"{date} {t}") + pd.Timedelta(minutes=30))
    hhmmss = start.strftime("%H:%M:%S")
    ev = s.calendar_events
    syncs = ev[(ev["event_name"] == "sync up") & (ev["event_start"] < NOW)].sort_values("event_start")
    name, who = "sync up", syncs.iloc[-1]["participant_email"]
    if not _slot_free(s, date, hhmmss, 30, name):
        raise ValueError(f"slot {date} {hhmmss} not free")
    row = {"event_id": _next_event_id(s), "event_name": name, "participant_email": who,
           "event_start": f"{date} {hhmmss}", "duration": "30"}
    why = (f"A 30-minute '{name}' meeting now exists on {p['next_day']} {date} at {hhmmss[:5]}, which is "
           f"{p['before_or_after']} {p['natural_language_time']}, so there is a meeting to cancel.")
    return [{"table": "calendar_events", "op": "append", "row": row}], why


def cancel_day_request(p, s):
    """Move the time threshold (same direction) to the nearest time the generator could pick
    (a start time in the calendar) such that at least one meeting falls on the asked side
    and no meeting on that day starts, runs over, or ends at the new time."""
    date = _date_of_next_day(p["next_day"])
    ev = s.calendar_events
    on = ev[ev["event_start"].str[:10] == date]
    t0 = pd.Timestamp(f"{date} {_time_of_nl(p['natural_language_time'])}")
    times = sorted(set(ev["event_start"].str.split(" ").str[1]))  # generator: random.choice(times)
    cands = sorted((pd.Timestamp(f"{date} {x}") for x in times), key=lambda x: (abs(x - t0), x))
    for t in cands:
        if t == t0:
            continue
        clash = False
        for _, r in on.iterrows():
            rs = pd.Timestamp(r["event_start"])
            if rs <= t <= rs + pd.Timedelta(minutes=int(r["duration"])):
                clash = True
        if clash:
            continue
        nl = get_natural_language_time(t.strftime("%H:%M:%S"))
        new_p = {**p, "natural_language_time": nl, "time": t.strftime("%H:%M:%S")}
        hits = _events_to_cancel(new_p, s)
        if len(hits):
            return new_p, (f"The time moves from {p['natural_language_time']} to {nl}; {len(hits)} meeting(s) on "
                           f"{p['next_day']} are wholly {p['before_or_after']} {nl}, so they must be cancelled.")
    return None


register(
    "Cancel my meetings on {next_day} {before_or_after} {natural_language_time}",
    cancel_day_gold, cancel_day_flip, cancel_day_request,
)


# --- Delete all my emails from {name} from the last {days} days ---------------
# upstream: generate_email_task_and_outcome.delete_last_days_emails_logic


def _emails_since(s, sender: str, days: int, strict: bool) -> pd.DataFrame:
    em = s.emails
    lo = str(HARDCODED_CURRENT_TIME - pd.Timedelta(days=days))
    win = em["sent_datetime"] > lo if strict else em["sent_datetime"] >= lo
    return em[win & (em["sender/recipient"] == sender)]


def delete_days_gold(p, s):
    rows = _emails_since(s, _email_of(s, p["name"]), int(p["days"]), strict=False)
    return [f'email.delete_email.func(email_id="{i}")' for i in rows["email_id"]]


def delete_days_flip(p, s):
    sender = _email_of(s, p["name"])
    em = s.emails
    theirs = em[em["sender/recipient"] == sender].sort_values("sent_datetime")
    latest_subject = theirs.iloc[-1]["subject"]
    # Copy the most recent email from them with a different subject than their latest,
    # so the new email is not mistaken for a duplicate of an older one.
    src = theirs[theirs["subject"] != latest_subject].iloc[-1]
    date = _day(-1)  # yesterday: inside every window of 2-7 days, never on its edge day
    sent = f"{date} {src['sent_datetime'].split(' ')[1]}"
    if ((em["sent_datetime"].str[:10] == date) & (em["subject"] == src["subject"])).any():
        raise ValueError("same subject already sent that day")
    row = {"email_id": f"{int(em['email_id'].astype(int).max()) + 1:08d}", "inbox/outbox": "inbox",
           "sender/recipient": sender, "subject": src["subject"], "sent_datetime": sent, "body": src["body"]}
    why = (f"A new email from {p['name']} ('{src['subject']}') arrived on {sent}, inside the last "
           f"{p['days']} days, so there is an email to delete.")
    return [{"table": "emails", "op": "append", "row": row}], why


def delete_days_request(p, s):
    sender, d = _email_of(s, p["name"]), int(p["days"])
    for d2 in _nearest_first(range(2, 8), d):  # generator: random.randint(2, 7)
        hits = _emails_since(s, sender, d2, strict=False)
        edge = _day(-d2)
        on_edge = hits[hits["sent_datetime"].str[:10] == edge]
        if len(hits) and on_edge.empty:
            return {**p, "days": d2}, (f"The window grows from {d} to {d2} days; {len(hits)} email(s) from "
                                       f"{p['name']} fall inside it (none on its first day, {edge}), so they must be deleted.")
    return None


register("Delete all my emails from {name} from the last {days} days", delete_days_gold, delete_days_flip, delete_days_request)


# --- If we haven't spoke to {customer} in the past fortnight book ... ----------
# upstream: generate_multi_domain_task_and_outcome.book_meeting_if_no_customer_contact_logic


def _customer(s, name: str):
    return s.crm_data[s.crm_data["customer_name"] == name].iloc[0]


def fortnight_gold(p, s):
    c = _customer(s, p["current_customer_name"])
    last = pd.to_datetime(c["last_contact_date"])
    if HARDCODED_CURRENT_TIME - last > pd.Timedelta(14, "D"):
        return [_first_free_tomorrow_action(s, f"Update on {p['current_customer_name']}", c["assigned_to_email"], 30)]
    return []


def fortnight_flip(p, s):
    c = _customer(s, p["current_customer_name"])
    # The new last contact date is the latest contact in the notes that is at least 18
    # days ago (a margin of 4+ days beyond the fortnight), so the record agrees with its
    # own notes; with no such note it is three weeks ago. Notes of later contacts are
    # dropped, or they would contradict the new date.
    cutoff = _day(-18)
    notes = c["notes"] if isinstance(c["notes"], str) else ""
    entries = re.findall(r"(\d{4}-\d{2}-\d{2}): ([^.]*\.)", notes)
    old = sorted(d for d, _ in entries if d <= cutoff)
    new_last = old[-1] if old else _day(-21)
    values = {"last_contact_date": new_last}
    dropped = [f"{d}: {t}" for d, t in entries if d > new_last]
    if dropped:
        values["notes"] = "".join(f"{d}: {t} " for d, t in entries if d <= new_last)
    why = (f"{p['current_customer_name']}'s last contact date is now {new_last}, more than 14 days ago"
           + (f" (the later contact notes {dropped} are removed so the record stays consistent)" if dropped else "")
           + ", so the update meeting must be booked.")
    return [{"table": "crm_data", "op": "set", "where": {"customer_id": c["customer_id"]}, "values": values}], why


register(
    "If we haven't spoke to {current_customer_name} in the past fortnight book a 30-minute meeting with whoever is assigned to them called 'Update on {current_customer_name}' at the first time I'm free tomorrow",
    fortnight_gold, fortnight_flip,
)


# --- If {sender_name} hasn't sent me any emails in the past {days} days ... -----
# upstream: generate_multi_domain_task_and_outcome.schedule_event_if_no_emails_logic


def no_emails_gold(p, s):
    if len(_emails_since(s, p["sender"], int(p["days"]), strict=True)):
        return []
    return [
        f'calendar.create_event.func(event_name="Catch up with {p["sender_name"]}", participant_email="{p["sender"]}", '
        f'event_start="{p["event_date"]} {p["event_time"]}", duration="30")'
    ]


def no_emails_flip(p, s):
    d = int(p["days"])
    recent = _emails_since(s, p["sender"], d, strict=True).sort_values("sent_datetime")
    bound = _day(-d - 2)  # at least 2 days before the window's first day
    patch = _move_emails(s, recent, bound)
    moved = _describe_moves(s, patch, "emails")
    why = (f"The {len(patch)} email(s) from {p['sender_name']} in the past {d} days were sent earlier instead: "
           f"{moved}. So they have not emailed me in the past {d} days and the meeting must be booked.")
    return patch, why


def no_emails_request(p, s):
    d = int(p["days"])
    for d2 in _nearest_first(range(2, 5), d):  # generator: random.randint(2, 4)
        if d2 < d and not len(_emails_since(s, p["sender"], d2, strict=True)):
            last = s.emails[s.emails["sender/recipient"] == p["sender"]]["sent_datetime"].max()
            return {**p, "days": d2}, (f"The window shrinks from {d} to {d2} days; {p['sender_name']}'s last email "
                                       f"was on {last[:10]}, before the window, so the meeting must be booked.")
    return None


register(
    "If {sender_name} hasn't sent me any emails in the past {days} days, schedule a 30 minute meeting with them for {day_of_week} at {natural_language_time} called 'Catch up with {sender_name}'",
    no_emails_gold, no_emails_flip, no_emails_request,
)


# --- If I haven't met with {name} in the past {days} days, send them an email ---
# upstream: generate_multi_domain_task_and_outcome.send_email_if_no_past_meetings_logic

CATCH_UP_PAST_BODY = "We haven't caught up in a while - can you send some availability over next week?"


def _catch_up_email(email: str, body: str) -> str:
    # same quoting as upstream new_email_string (an f-string with "...")
    return f'email.send_email.func(recipient="{email}", subject="Catch up soon?", body="{body}")'


def no_past_meet_gold(p, s):
    email = _email_of(s, p["name"])
    ev = s.calendar_events
    past = ev[(ev["participant_email"] == email) & (ev["event_start"] < NOW)]
    if not len(past):
        return [_catch_up_email(email, CATCH_UP_PAST_BODY)]
    last_date = past.sort_values("event_start", ascending=False).iloc[0]["event_start"].split(" ")[0]
    threshold = str((HARDCODED_CURRENT_TIME - pd.Timedelta(days=int(p["days"]))).date())
    return [_catch_up_email(email, CATCH_UP_PAST_BODY)] if last_date < threshold else []


def no_past_meet_flip(p, s):
    email, d = _email_of(s, p["name"]), int(p["days"])
    threshold = _day(-d)
    ev = s.calendar_events
    recent = ev[(ev["participant_email"] == email) & (ev["event_start"] < NOW)
                & (ev["event_start"].str[:10] >= threshold)].sort_values("event_start")
    patch = _move_events(s, recent, _shift(threshold, -2), -1)
    moved = _describe_moves(s, patch)
    why = (f"{len(patch)} meeting(s) with {p['name']} in the past {d} days now took place earlier: {moved}. "
           f"So I have not met {p['name']} in the past {d} days and the email must be sent.")
    return patch, why


def no_past_meet_request(p, s):
    d = int(p["days"])
    for d2 in (2, 10):  # generator: random.choice([2, 10])
        if d2 != d and no_past_meet_gold({**p, "days": d2}, s):
            email = _email_of(s, p["name"])
            ev = s.calendar_events
            last = ev[(ev["participant_email"] == email) & (ev["event_start"] < NOW)]["event_start"].max()
            return {**p, "days": d2}, (f"The window shrinks from {d} to {d2} days; my last meeting with {p['name']} "
                                       f"was on {last[:10]}, before the window, so the email must be sent.")
    return None


register(
    "If I haven't met with {name} in the past {days} days, send them an email titled 'Catch up soon?' saying 'We haven't caught up in a while - can you send some availability over next week?'",
    no_past_meet_gold, no_past_meet_flip, no_past_meet_request,
)


# --- If I don't have any meetings scheduled with {name} in the next {days} days --
# upstream: generate_multi_domain_task_and_outcome.send_email_if_no_future_meetings_logic

CATCH_UP_FUTURE_BODY = "We have not caught up in a while - can you send some availability over next week?"


def no_future_meet_gold(p, s):
    email = _email_of(s, p["name"])
    ev = s.calendar_events
    fut = ev[(ev["participant_email"] == email) & (ev["event_start"] > NOW)]
    if not len(fut):
        return [_catch_up_email(email, CATCH_UP_FUTURE_BODY)]
    next_date = fut.sort_values("event_start", ascending=True).iloc[0]["event_start"].split(" ")[0]
    threshold = str((HARDCODED_CURRENT_TIME + pd.Timedelta(days=int(p["days"]))).date())
    return [_catch_up_email(email, CATCH_UP_FUTURE_BODY)] if next_date > threshold else []


def no_future_meet_flip(p, s):
    email, d = _email_of(s, p["name"]), int(p["days"])
    threshold = _day(d)
    ev = s.calendar_events
    soon = ev[(ev["participant_email"] == email) & (ev["event_start"] > NOW)
              & (ev["event_start"].str[:10] <= threshold)].sort_values("event_start")
    # Postpone each meeting in the window to a work day at least 2 days after its last day.
    patch = _move_events(s, soon, _shift(threshold, 2), +1)
    moved = _describe_moves(s, patch)
    why = (f"{len(patch)} meeting(s) with {p['name']} in the next {d} days are now later: {moved}. "
           f"So nothing is scheduled with {p['name']} in the next {d} days and the email must be sent.")
    return patch, why


def no_future_meet_request(p, s):
    d = int(p["days"])
    for d2 in _nearest_first(range(2, 5), d):  # generator: random.randint(2, 4)
        if no_future_meet_gold({**p, "days": d2}, s):
            return {**p, "days": d2}, (f"The window shrinks from {d} to {d2} days; my next meeting with {p['name']} "
                                       f"is after it, so the email must be sent.")
    return None


register(
    "If I don't have any meetings scheduled with {name} in the next {days} days, send them an email titled 'Catch up soon?' saying 'We have not caught up in a while - can you send some availability over next week?'",
    no_future_meet_gold, no_future_meet_flip, no_future_meet_request,
)


# --- Book a half-hour meeting with {name} ... tomorrowif they have any overdue tasks
# upstream: generate_multi_domain_task_and_outcome.book_meeting_with_overdue_tasks_logic
#           (overdue rule: overdue_tasks_base_dict)


def _overdue(s, email: str) -> pd.DataFrame:
    pt = s.project_tasks
    return pt[(pt["assigned_to_email"] == email) & (pt["due_date"] < str(HARDCODED_CURRENT_TIME.date()))
              & ~pt["list_name"].isin(["Completed"])]


def overdue_meeting_gold(p, s):
    if len(_overdue(s, p["email"])):
        return [_first_free_tomorrow_action(s, "Catch up on overdue tasks", p["email"], 30)]
    return []


def overdue_meeting_flip(p, s):
    pt = s.project_tasks
    open_ = pt[(pt["assigned_to_email"] == p["email"]) & (pt["list_name"] != "Completed")]
    t = open_.sort_values(["due_date", "task_id"]).iloc[0]  # the open task due soonest
    new_due = _day(-3)  # 2023-11-27, the board's earliest due date: 3 days overdue
    why = (f"{p['name']}'s open task '{t['task_name']}' ({t['list_name']}) was due on {new_due} instead of "
           f"{t['due_date']}, so it is now overdue and the meeting must be booked.")
    return [{"table": "project_tasks", "op": "set", "where": {"task_id": t["task_id"]},
             "values": {"due_date": new_due}}], why


register(
    "Book a half-hour meeting with {name} called 'Catch up on overdue tasks' at the earliest time I'm free tomorrowif they have any overdue tasks",
    overdue_meeting_gold, overdue_meeting_flip,
)
