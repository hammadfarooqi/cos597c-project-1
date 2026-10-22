"""Template specs: the analytics templates, and the multi-domain templates whose
condition is an analytics metric.

See framework.py for the contract. Each gold rule mirrors the upstream logic
function named in its comment (scripts/data_generation/task_outcome_generation/).
"""

from __future__ import annotations

import json
import random

import numpy as np
import pandas as pd
from framework import register

from src.data_generation.data_generation_utils import HARDCODED_CURRENT_TIME, get_first_free_slot

LAST_DAY = "2023-11-29"  # analytics_data["date_of_visit"].max(): the generator's date_max
NEXT_FRIDAY = str(HARDCODED_CURRENT_TIME.date() + pd.Timedelta(7 + (4 - HARDCODED_CURRENT_TIME.dayofweek), "D"))
PLOT_NAME = {"direct": "visits_direct", "social media": "visits_social_media",
             "referral": "visits_referral", "search engine": "visits_search_engine"}
METRIC_NAME = {"total_visits": "total visits", "session_duration_seconds": "average session duration",
               "user_engaged": "engaged users"}


# --- shared helpers: mirror src/tools/analytics.py and the generator ---------


def _series(s, metric: str, date_min: str, source: str | None = None) -> pd.Series:
    """The generator's pd.Series(json.loads(metric_to_func_dict[metric](date_min)))."""
    d = s.analytics_data[s.analytics_data["date_of_visit"] >= date_min].copy()
    if metric == "total_visits":
        out = d.groupby("date_of_visit").size().to_dict()
    elif metric == "user_engaged":
        d["user_engaged"] = d["user_engaged"].astype(bool).astype(int)
        out = d.groupby("date_of_visit")["user_engaged"].sum().to_dict()
    elif metric == "session_duration_seconds":
        d["session_duration_seconds"] = d["session_duration_seconds"].astype(float)
        out = d.groupby("date_of_visit")["session_duration_seconds"].mean().to_dict()
    elif metric == "traffic_source":
        d["visits_from_source"] = (d["traffic_source"] == source).astype(int)
        out = d.groupby("date_of_visit")["visits_from_source"].sum().to_dict()
    else:
        raise ValueError(metric)
    return pd.Series(json.loads(json.dumps(out)))


def _plot(metric: str, date_min: str, date_max: str, plot_type: str) -> str:
    """generate_analytics_task_and_outcome.get_plot_string."""
    name = PLOT_NAME.get(metric, metric)
    return (f'analytics.create_plot.func(time_min="{date_min}", time_max="{date_max}", '
            f'value_to_plot="{name}", plot_type="{plot_type}")')


def _days_back(k: int) -> str:
    return str(HARDCODED_CURRENT_TIME.date() - pd.Timedelta(k, "D"))


def _date_of_weekday(day: str) -> str:
    """The date in the last 6 days with this weekday name (the generator's day_in_last_week)."""
    for k in range(1, 7):
        if pd.to_datetime(_days_back(k)).day_name().lower() == day.lower():
            return _days_back(k)
    raise ValueError(f"no day {day!r} in the last 6 days")


def _weeks_back(n: int) -> str:
    return str(HARDCODED_CURRENT_TIME.date() - pd.Timedelta(int(n), "W"))


def _more_or_less_any_time(s, metric: str, date_min: str, threshold) -> str:
    """generate_analytics_task_and_outcome.metric_more_or_less_any_time."""
    ser = _series(s, metric, date_min)
    if (ser > threshold).sum() == 0:
        return "less"
    if (ser < threshold).sum() == 0:
        return "more"
    return "both more and less"


def _condition_holds(p, s, date_min: str) -> bool:
    """metric_more_or_less_plot_logic: more_or_less in metric_vs_threshold."""
    return p["more_or_less"] in _more_or_less_any_time(s, p["metric"], date_min, p["threshold"])


def _higher_or_lower(s, metric: str, date_min: str, date_max: str, threshold: float) -> str:
    """generate_analytics_task_and_outcome.metric_higher_or_lower."""
    ser = _series(s, metric, date_min)
    prev, cur = ser[date_min], ser[date_max]
    pct = (cur - prev) / prev
    if pct < 0 and abs(pct) > threshold:
        return "lower"
    if pct > 0 and pct > threshold:
        return "higher"
    return "not changed"


def _pct(s, metric: str, date_min: str, date_max: str) -> float:
    ser = _series(s, metric, date_min)
    return float((ser[date_max] - ser[date_min]) / ser[date_min])


def _relative_growth(s, metric1: str, metric2: str, date_min: str) -> tuple[float, float]:
    """generate_analytics_task_and_outcome.get_relative_growth."""
    s1 = _series(s, metric1, date_min)
    s2 = _series(s, metric2, date_min)
    return (s1.iloc[-1] - s1[date_min]) / s1[date_min], (s2.iloc[-1] - s2[date_min]) / s2[date_min]


def _new_task(name: str, email: str) -> str:
    """generate_project_management_task_and_outcome.get_new_task_string, board Front end."""
    return (f'project_management.create_task.func(task_name="{name}", board="Front end", '
            f'assigned_to_email="{email}", due_date="{NEXT_FRIDAY}", list_name="Backlog")')


def _send_email(to: str, subject: str, body: str) -> str:
    return f'email.send_email.func(recipient="{to}", subject="{subject}", body="{body}")'


def _event_first_free_tomorrow(s, name: str, participant: str, minutes: int) -> str:
    """generate_calendar_task_and_outcome.create_event_on_first_free_slot_tomorrow."""
    tomorrow = str(HARDCODED_CURRENT_TIME + pd.Timedelta(days=1)).split(" ")[0]
    following = str(HARDCODED_CURRENT_TIME + pd.Timedelta(days=2)).split(" ")[0]
    ev = s.calendar_events
    day = ev["event_start"].str.split(" ").str[0]
    first = get_first_free_slot(tomorrow, ev[(day >= tomorrow) & (day < following)], minutes)
    return (f'calendar.create_event.func(event_name="{name}", participant_email="{participant}", '
            f'event_start="{first}", duration="{minutes}")')


# --- gold rules ----------------------------------------------------------------


def _since_date(p) -> str:
    return p["date_min"]


def _past_weeks_date(p) -> str:
    return _weeks_back(p["past_n_weeks"])


def threshold_plot_gold(date_fn):
    # upstream: metric_more_or_less_plot_logic (and ..._past_weeks_plot_logic)
    def gold(p, s):
        d = date_fn(p)
        return [_plot(p["metric"], d, p["date_max"], "line")] if _condition_holds(p, s, d) else []
    return gold


def growth_since_date_gold(p, s):
    # upstream: metric_higher_or_lower_plot_logic (no date arguments)
    d0, d1 = p["date_min"], p["date_max"]
    hit = p["higher_or_lower"] == _higher_or_lower(s, p["metric"], d0, d1, p["growth_threshold"])
    return [_plot(p["metric"], d0, d1, "line")] if hit else []


def growth_since_weekday_gold(p, s):
    # upstream: metric_higher_or_lower_day_of_week_plot_logic
    d0, d1 = _date_of_weekday(p["day_of_week"]), p["date_max"]
    hit = p["higher_or_lower"] == _higher_or_lower(s, p["metric"], d0, d1, p["growth_threshold"])
    return [_plot(p["metric"], d0, d1, "line")] if hit else []


def _week_pair(p) -> tuple[str, str]:
    last = _date_of_weekday(p["day_of_week"])
    return str(pd.to_datetime(last).date() - pd.Timedelta(7, "D")), last


def growth_week_on_week_gold(p, s):
    # upstream: metric_higher_or_lower_past_weeks_plot_logic
    d0, d1 = _week_pair(p)
    hit = p["higher_or_lower"] == _higher_or_lower(s, p["metric"], d0, d1, p["growth_threshold"])
    return [_plot(p["metric"], d0, d1, "line")] if hit else []


def _grew_more(p, s) -> bool:
    g1, g2 = _relative_growth(s, p["metric"], p["metric2"], _date_of_weekday(p["day_of_week"]))
    return bool(g1 > g2)


def relative_growth_plots_gold(p, s):
    # upstream: relative_growth_two_plots_logic
    d0 = _date_of_weekday(p["day_of_week"])
    if not _grew_more(p, s):
        return []
    return [_plot(p["metric"], d0, p["date_max"], "line"), _plot(p["metric2"], d0, p["date_max"], "line")]


def _source_means(p, s) -> tuple[float, float]:
    d0 = _weeks_back(p["n_weeks"])
    m1 = _series(s, "traffic_source", d0, p["traffic_source_1"]).mean()
    m2 = _series(s, "traffic_source", d0, p["traffic_source_2"]).mean()
    return m1, m2


def traffic_sources_gold(p, s):
    # upstream: plot_relative_traffic_source_logic
    d0 = _weeks_back(p["n_weeks"])
    m1, m2 = _source_means(p, s)
    if not m1 > m2:
        return []
    return [_plot(p["traffic_source_1"], d0, p["date_max"], "bar"), _plot(p["traffic_source_2"], d0, p["date_max"], "bar")]


def email_if_threshold_gold(p, s):
    # upstream: generate_multi_domain_task_and_outcome.send_email_if_metric_more_or_less_than_threshold_logic
    if not _condition_holds(p, s, p["date_min"]):
        return []
    m = p["natural_language_metric"]
    return [_send_email(p["sender"], f"Update on {m}",
                        f"I noticed {m} was {p['more_or_less']} than {p['threshold']} - can you update me?")]


def task_if_threshold_gold(p, s):
    # upstream: make_task_if_metric_more_or_less_than_threshold_logic
    if not _condition_holds(p, s, p["date_min"]):
        return []
    return [_new_task(f"Improve {p['natural_language_metric']}", p["email"])]


def _most_completed_front_end(s) -> str:
    pt = s.project_tasks
    return pt[(pt["list_name"] == "Completed") & (pt["board"] == "Front end")]["assigned_to_email"].value_counts().idxmax()


def task_most_completed_if_threshold_gold(p, s):
    # upstream: make_task_person_most_completed_if_metric_vs_threshold_logic
    if not _condition_holds(p, s, p["date_min"]):
        return []
    return [_new_task(f"Improve {p['natural_language_metric']}", _most_completed_front_end(s))]


def task_if_growth_gold(p, s):
    # upstream: make_task_if_relative_growth_logic
    if not _grew_more(p, s):
        return []
    return [_new_task(f"Improve {p['natural_language_metric_2']}", p["email"])]


def delete_leads_if_threshold_gold(p, s):
    # upstream: delete_all_customers_if_metric_more_or_less_than_threshold_logic
    if not _condition_holds(p, s, p["date_min"]):
        return []
    crm = s.crm_data
    leads = crm[(crm["assigned_to_email"] == p["assigned_to_email"]) & (crm["status"] == "Lead")]
    return [f'customer_relationship_manager.delete_customer.func(customer_id="{i}")' for i in leads["customer_id"]]


def task_and_meeting_if_growth_gold(p, s):
    # upstream: make_task_and_book_meeting_if_relative_growth_logic
    if not _grew_more(p, s):
        return []
    return [_new_task(f"Improve {p['natural_language_metric_2']}", p["email"]),
            _event_first_free_tomorrow(s, f"Discuss {p['natural_language_metric']}", p["email"], 30)]


# --- flips: margins --------------------------------------------------------------
# Counts (total visits, engaged users) are exact integers: we ask for 2 past the
# threshold where the data allows it (never below 0). The average session duration is a
# float: we ask for max(1 s, 10% of the threshold). Growth rates: 2 percentage points
# past the growth threshold. Growth of one metric against another: 5 points, and the first
# metric must really grow (by 5% or more). Traffic sources: source 1's period total must lead by 3 visits and 15%.

COUNT_MARGIN = 2
GROWTH_MARGIN = 0.02
REL_MARGIN = 0.05  # metric 1 vs metric 2 growth: two computed rates, so a wider gap
TRAFFIC_MARGIN = 3
TRAFFIC_RATIO = 1.15  # source 1 must also lead by 15%, so the gap shows in rounded means
DURATION_CAP = 150  # the longest session in the data is 154 s; never write a longer one
GROWTH_THRESHOLDS = [0.02, 0.03, 0.05, 0.1]  # get_random_dict's growth_threshold choices
FIRST_DAY = "2023-09-01"  # analytics_data["date_of_visit"].min(): get_threshold's series start


def _margin(metric: str, threshold) -> float:
    return max(1.0, 0.1 * float(threshold)) if metric == "session_duration_seconds" else COUNT_MARGIN


def _passes_threshold(metric: str, value: float, more_or_less: str, threshold) -> bool:
    """The day value is past the threshold with a clear margin."""
    m = _margin(metric, threshold)
    if more_or_less == "more":
        return value >= threshold + m
    target = threshold - m if threshold - m >= 0 else 0  # counts cannot go below 0
    return value <= target and value < threshold


def _generator_thresholds(s, metric: str) -> list[int]:
    """get_threshold: max(1, int(percentile)) for percentiles 0, 50, 100 of the whole series."""
    ser = _series(s, metric, FIRST_DAY)
    return sorted({max(1, int(np.percentile(ser, q))) for q in (0, 50, 100)})


# --- flips: one-day edits of analytics_data ----------------------------------------


def _day_rows(s, day: str) -> pd.DataFrame:
    d = s.analytics_data
    return d[d["date_of_visit"] == day].sort_values("visitor_id").reset_index(drop=True)


def _day_values(rows: pd.DataFrame) -> dict:
    """The three metric values the tools report for one day."""
    return {
        "total_visits": len(rows),
        "user_engaged": int(rows["user_engaged"].astype(bool).sum()),
        "session_duration_seconds": float(rows["session_duration_seconds"].astype(float).mean()),
    }


def _key(row) -> dict:
    # (date_of_visit, visitor_id) is unique in analytics_data.
    return {"date_of_visit": row["date_of_visit"], "visitor_id": row["visitor_id"]}


def _record(row) -> dict:
    return {"date_of_visit": str(row["date_of_visit"]), "visitor_id": str(row["visitor_id"]),
            "page_views": str(row["page_views"]), "session_duration_seconds": str(row["session_duration_seconds"]),
            "traffic_source": str(row["traffic_source"]), "user_engaged": bool(row["user_engaged"])}


def _new_visitor_ids(s, day: str, k: int) -> list[str]:
    """k unused 4-digit visitor ids, chosen reproducibly."""
    used = set(s.analytics_data["visitor_id"])
    pool = [f"{i:04d}" for i in range(10000) if f"{i:04d}" not in used]
    return random.Random(f"twin-{day}").sample(pool, k)


def _append_copies(s, day, rows, base: list[dict], k: int):
    """Append k new visits on ``day``, each a copy of a row in ``base`` with a new visitor id."""
    ids = _new_visitor_ids(s, day, k)
    new = [{**_record(base[i % len(base)]), "visitor_id": ids[i]} for i in range(k)]
    ops = [{"table": "analytics_data", "op": "append", "row": r} for r in new]
    return ops, pd.concat([rows, pd.DataFrame(new)], ignore_index=True)


def _engaged_rule(duration, page_views) -> bool:
    """generate_analytics_data.py: user_engaged = session_duration_seconds > 10 and page_views > 1.
    Every edit keeps this rule true, so no patched row is impossible."""
    return int(float(duration)) > 10 and int(page_views) > 1


def _edit_cells(rows, edits: list[tuple[int, dict]]):
    """Set cells of some of the day's rows; user_engaged follows the data rule."""
    new = rows.copy()
    ops = []
    for i, vals in edits:
        vals = dict(vals)
        dur = vals.get("session_duration_seconds", rows.loc[i, "session_duration_seconds"])
        pv = vals.get("page_views", rows.loc[i, "page_views"])
        eng = _engaged_rule(dur, pv)
        if eng != bool(rows.loc[i, "user_engaged"]):
            vals["user_engaged"] = eng
        for col, val in vals.items():
            new.loc[i, col] = val
        ops.append({"table": "analytics_data", "op": "set", "where": _key(rows.loc[i]), "values": vals})
    return ops, new


def _fam_visits_up(s, day, rows, ok):
    base = [r for _, r in rows.iterrows()]
    for k in range(1, 41):
        ops, new = _append_copies(s, day, rows, base, k)
        if ok(new):
            return ops, new
    return None


def _fam_visits_down(s, day, rows, ok):
    # Keep at least one visit: a day with no visits drops out of the tools' output.
    for k in range(1, len(rows)):
        idx = list(range(k))
        ops = [{"table": "analytics_data", "op": "delete", "where": _key(rows.loc[i])} for i in idx]
        new = rows.drop(index=idx).reset_index(drop=True)
        if ok(new):
            return ops, new
    return None


def _fam_engaged_up(s, day, rows, ok):
    """Make k unengaged visits engaged. First visits that were long enough but saw one page
    (now 2 pages); then short visits with several pages (now 11 s); then both. Past
    that, add copies of the day's engaged visits."""
    dur = rows["session_duration_seconds"].astype(int)
    pv = rows["page_views"].astype(int)
    off = ~rows["user_engaged"].astype(bool)
    edits = ([(i, {"page_views": "2"}) for i in rows.index[off & (dur > 10) & (pv == 1)]]
             + [(i, {"session_duration_seconds": "11"}) for i in rows.index[off & (dur <= 10) & (pv > 1)]]
             + [(i, {"session_duration_seconds": "11", "page_views": "2"}) for i in rows.index[off & (dur <= 10) & (pv == 1)]])
    on = [r for _, r in rows.iterrows() if bool(r["user_engaged"])]
    for k in range(1, 21):
        ops, new = _edit_cells(rows, edits[:k])
        if k > len(edits):
            if not on:
                return None
            more_ops, new = _append_copies(s, day, new, on, k - len(edits))
            ops = ops + more_ops
        if ok(new):
            return ops, new
    return None


def _fam_engaged_down(s, day, rows, ok):
    """Make k engaged visits unengaged: each saw one page instead of several."""
    on = [i for i in rows.index if bool(rows.loc[i, "user_engaged"])]
    for k in range(1, len(on) + 1):
        ops, new = _edit_cells(rows, [(i, {"page_views": "1"}) for i in on[:k]])
        if ok(new):
            return ops, new
    return None


def _duration_edit(rows, idx: list[int], v: int, keep: bool = False):
    """Set these sessions to v seconds. With keep, an engaged session stays at 11 s or more,
    so no visit changes its engagement."""
    def dur(i):
        return max(v, 11) if keep and bool(rows.loc[i, "user_engaged"]) else v
    return _edit_cells(rows, [(i, {"session_duration_seconds": str(dur(i))}) for i in idx])


def _duration_up(s, day, rows, ok, keep: bool):
    """Raise the k shortest sessions to the smallest common length that works (k <= 4).
    With keep, only sessions whose engagement cannot change (one page, or already engaged)."""
    cand = rows
    if keep:
        cand = rows[(rows["page_views"].astype(int) == 1) | rows["user_engaged"].astype(bool)]
    order = cand["session_duration_seconds"].astype(float).sort_values(kind="stable").index.tolist()
    for k in range(1, min(4, len(order)) + 1):
        idx = order[:k]
        lo = int(rows.loc[idx, "session_duration_seconds"].astype(float).max()) + 1
        if lo > DURATION_CAP or not ok(_duration_edit(rows, idx, DURATION_CAP)[1]):
            continue
        hi = DURATION_CAP
        while lo < hi:  # smallest v that works
            mid = (lo + hi) // 2
            if ok(_duration_edit(rows, idx, mid)[1]):
                hi = mid
            else:
                lo = mid + 1
        return _duration_edit(rows, idx, lo)
    return None


def _duration_down(s, day, rows, ok, keep: bool):
    """Cut the k longest sessions to the largest common length that works."""
    order = rows["session_duration_seconds"].astype(float).sort_values(ascending=False, kind="stable").index.tolist()
    for k in range(1, len(rows) + 1):
        idx = order[:k]
        hi = int(rows.loc[idx, "session_duration_seconds"].astype(float).min()) - 1
        if hi < 0 or not ok(_duration_edit(rows, idx, 0, keep)[1]):
            continue
        lo = 0
        while lo < hi:  # largest v that works
            mid = (lo + hi + 1) // 2
            if ok(_duration_edit(rows, idx, mid, keep)[1]):
                lo = mid
            else:
                hi = mid - 1
        ops, new = _duration_edit(rows, idx, lo, keep)
        if any(int(rows.loc[i, "session_duration_seconds"]) <= int(new.loc[i, "session_duration_seconds"]) for i in idx):
            continue  # with keep, a session would not really get shorter
        return ops, new
    return None


def _fam_duration_up_keep(s, day, rows, ok):
    return _duration_up(s, day, rows, ok, keep=True)


def _fam_duration_up(s, day, rows, ok):
    return _duration_up(s, day, rows, ok, keep=False)


def _fam_duration_down_keep(s, day, rows, ok):
    return _duration_down(s, day, rows, ok, keep=True)


def _fam_duration_down(s, day, rows, ok):
    return _duration_down(s, day, rows, ok, keep=False)


FAMILIES = {
    ("total_visits", "up"): [_fam_visits_up], ("total_visits", "down"): [_fam_visits_down],
    ("user_engaged", "up"): [_fam_engaged_up], ("user_engaged", "down"): [_fam_engaged_down],
    ("session_duration_seconds", "up"): [_fam_duration_up_keep, _fam_duration_up],
    ("session_duration_seconds", "down"): [_fam_duration_down_keep, _fam_duration_down],
}
FAMILY_TEXT = {
    _fam_visits_up: "added {n} visit row(s), copies of that day's visits with new visitor ids",
    _fam_visits_down: "removed {n} visit row(s)",
    _fam_engaged_up: "made {n} visit(s) engaged (more pages or a longer session, per the data's engagement rule)",
    _fam_engaged_down: "made {n} engaged visit(s) single-page, so not engaged",
    _fam_duration_up_keep: "lengthened {n} session(s)",
    _fam_duration_up: "lengthened {n} session(s)",
    _fam_duration_down_keep: "shortened {n} session(s)",
    _fam_duration_down: "shortened {n} session(s)",
}


def _best_edit(s, days: list[str], families: list, ok_for_day):
    """The smallest one-day edit that satisfies ok_for_day(day)(new_rows).
    Ties go to the earlier entry of ``days``, then of ``families``."""
    best = None
    for di, day in enumerate(days):
        rows = _day_rows(s, day)
        for fi, fam in enumerate(families):
            got = fam(s, day, rows, ok_for_day(day))
            if got is None:
                continue
            ops, new = got
            cand = (len(ops), di, fi, day, fam, ops, new)
            if best is None or cand[:3] < best[:3]:
                best = cand
    if best is None:
        raise ValueError("no one-day edit within limits makes the condition true")
    _, _, _, day, fam, ops, new = best
    return day, fam, ops, _day_values(_day_rows(s, day)), _day_values(new)


def _fmt(metric: str, v) -> str:
    return f"{v:.2f}" if metric == "session_duration_seconds" else str(int(v))


# --- flips: "was {metric} {more_or_less} than {threshold} at any time since ..." ------


def _threshold_ok(metric, mol, threshold):
    return lambda day: (lambda rows: _passes_threshold(metric, _day_values(rows)[metric], mol, threshold))


def threshold_db_flip(date_fn):
    def flip(p, s):
        d0 = date_fn(p)
        metric, mol, t = p["metric"], p["more_or_less"], p["threshold"]
        days = sorted(_series(s, metric, d0).index, reverse=True)  # ties go to the latest day
        fams = FAMILIES[(metric, "up" if mol == "more" else "down")]
        day, fam, ops, before, after = _best_edit(s, days, fams, _threshold_ok(metric, mol, t))
        why = (f"On {day} {METRIC_NAME[metric]} is now {_fmt(metric, after[metric])} instead of "
               f"{_fmt(metric, before[metric])} ({FAMILY_TEXT[fam].format(n=len(ops))}), so it was {mol} than "
               f"{t} at a time since {d0} and the action is due.")
        return ops, why
    return flip


def _threshold_holds_with_margin(s, metric, d0, mol, t) -> bool:
    return any(_passes_threshold(metric, v, mol, t) for v in _series(s, metric, d0))


def threshold_request_flip(date_fn):
    """Change the threshold to the nearest other value get_threshold can produce for this
    metric; if none flips with margin, change the comparison word."""
    def flip(p, s):
        d0, metric, mol, t = date_fn(p), p["metric"], p["more_or_less"], p["threshold"]
        for nt in sorted((x for x in _generator_thresholds(s, metric) if x != t), key=lambda x: (abs(x - t), x)):
            if _threshold_holds_with_margin(s, metric, d0, mol, nt):
                return {**p, "threshold": nt}, (
                    f"The threshold is now {nt} instead of {t}: {METRIC_NAME[p['metric']]} was {mol} than {nt} "
                    f"on at least one day since {d0}, so the action is due.")
        other = "less" if mol == "more" else "more"
        if _threshold_holds_with_margin(s, metric, d0, other, t):
            return {**p, "more_or_less": other}, (
                f"The comparison is now '{other}' instead of '{mol}': {METRIC_NAME[metric]} was {other} than {t} "
                f"on at least one day since {d0}, so the action is due.")
        return None
    return flip


# --- flips: "is {metric} more than {g} {higher_or_lower} than {day}" ------------------


def _growth_passes(pct: float, hl: str, thr: float) -> bool:
    return pct >= thr + GROWTH_MARGIN if hl == "higher" else pct <= -(thr + GROWTH_MARGIN)


def _growth_ok(s, metric, d0, d1, hl, thr):
    base = {d0: _day_values(_day_rows(s, d0))[metric], d1: _day_values(_day_rows(s, d1))[metric]}

    def for_day(day):
        def ok(rows):
            v = {**base, day: _day_values(rows)[metric]}
            return v[d0] > 0 and _growth_passes((v[d1] - v[d0]) / v[d0], hl, thr)
        return ok
    return for_day


def growth_db_flip(dates_fn):
    def flip(p, s):
        d0, d1 = dates_fn(p)
        if d0 == d1:
            raise ValueError(f"not flippable: the reference day and the current day are both {d0}, "
                             "so the growth is 0 on every state")
        metric, hl, thr = p["metric"], p["higher_or_lower"], p["growth_threshold"]
        fams = FAMILIES[(metric, "up")] + FAMILIES[(metric, "down")]
        # Ties go to the reference day: the task names it, so every agent reads it.
        day, fam, ops, before, after = _best_edit(s, [d0, d1], fams, _growth_ok(s, metric, d0, d1, hl, thr))
        s2 = _with_patch(s, ops)
        pct = _pct(s2, metric, d0, d1)
        why = (f"On {day} {METRIC_NAME[metric]} is now {_fmt(metric, after[metric])} instead of "
               f"{_fmt(metric, before[metric])} ({FAMILY_TEXT[fam].format(n=len(ops))}), so from {d0} to {d1} it "
               f"changed by {100 * pct:+.1f}%, more than {p['natural_language_growth_threshold']} {hl}, and the action is due.")
        return ops, why
    return flip


def growth_request_flip(dates_fn):
    """Change the growth threshold to the nearest other generator value; if none flips
    with margin, change 'higher' <-> 'lower'."""
    def flip(p, s):
        d0, d1 = dates_fn(p)
        if d0 == d1:
            return None
        pct, hl, thr = _pct(s, p["metric"], d0, d1), p["higher_or_lower"], p["growth_threshold"]
        for nt in sorted((x for x in GROWTH_THRESHOLDS if x != thr), key=lambda x: (abs(x - thr), x)):
            if _growth_passes(pct, hl, nt):
                nl = f"{int(100 * nt)}%"
                return {**p, "growth_threshold": nt, "natural_language_growth_threshold": nl}, (
                    f"The growth threshold is now {nl} instead of {p['natural_language_growth_threshold']}: "
                    f"{METRIC_NAME[p['metric']]} changed by {100 * pct:+.1f}% from {d0} to {d1}, so the action is due.")
        other = "lower" if hl == "higher" else "higher"
        if _growth_passes(pct, other, thr):
            return {**p, "higher_or_lower": other}, (
                f"The direction is now '{other}' instead of '{hl}': {METRIC_NAME[p['metric']]} changed by "
                f"{100 * pct:+.1f}% from {d0} to {d1}, more than {p['natural_language_growth_threshold']}, so the action is due.")
        return None
    return flip


def _dates_since_date(p):
    return p["date_min"], p["date_max"]


def _dates_since_weekday(p):
    return _date_of_weekday(p["day_of_week"]), p["date_max"]


# --- flips: "if {metric} grew by more than {metric_2} since {day_of_week}" ------------


def _rel_ok(s, m1, m2, d0, d1):
    base = {d: _day_values(_day_rows(s, d)) for d in (d0, d1)}

    def for_day(day):
        def ok(rows):
            v = {**base, day: _day_values(rows)}
            if v[d0][m1] <= 0 or v[d0][m2] <= 0:
                return False
            g1 = (v[d1][m1] - v[d0][m1]) / v[d0][m1]
            g2 = (v[d1][m2] - v[d0][m2]) / v[d0][m2]
            return g1 >= REL_MARGIN and g1 >= g2 + REL_MARGIN
        return ok
    return for_day


def relative_growth_db_flip(p, s):
    d0, d1 = _date_of_weekday(p["day_of_week"]), LAST_DAY
    if d0 == d1:
        raise ValueError(f"not flippable: '{p['day_of_week']}' is {d0}, the last day of data, so both growths "
                         "are 0 on every state")
    m1, m2 = p["metric"], p["metric2"]
    fams = FAMILIES[(m1, "up")] + FAMILIES[(m1, "down")] + FAMILIES[(m2, "down")] + FAMILIES[(m2, "up")]
    # Ties go to the start day: the task names it, so every agent reads it.
    day, fam, ops, before, after = _best_edit(s, [d0, d1], fams, _rel_ok(s, m1, m2, d0, d1))
    g1, g2 = _relative_growth(_with_patch(s, ops), m1, m2, d0)
    changed = [m for m in (m1, m2) if before[m] != after[m]]
    values = ", ".join(f"{METRIC_NAME[m]} {_fmt(m, before[m])} -> {_fmt(m, after[m])}" for m in changed)
    why = (f"On {day} we {FAMILY_TEXT[fam].format(n=len(ops))} ({values}), so since {d0} {METRIC_NAME[m1]} grew by "
           f"{100 * g1:+.1f}% and {METRIC_NAME[m2]} by {100 * g2:+.1f}%; the first grew more, so the action is due.")
    return ops, why


def relative_growth_request_flip(p, s):
    """Change the day the growth is measured from to the nearest other day the generator
    can produce (1-6 days back) where the first metric grew more, with margin."""
    k0 = next(k for k in range(1, 7) if _days_back(k) == _date_of_weekday(p["day_of_week"]))
    m1, m2 = p["metric"], p["metric2"]
    for k in sorted((k for k in range(2, 7) if k != k0), key=lambda k: (abs(k - k0), k)):
        d0 = _days_back(k)
        g1, g2 = _relative_growth(s, m1, m2, d0)
        if g1 >= REL_MARGIN and g1 >= g2 + REL_MARGIN:
            day = pd.to_datetime(d0).day_name()
            day = day.lower() if p["day_of_week"].islower() else day
            return {**p, "day_of_week": day}, (
                f"The start day is now {day} ({d0}) instead of {p['day_of_week']}: since then {METRIC_NAME[m1]} grew by "
                f"{100 * g1:+.1f}% and {METRIC_NAME[m2]} by {100 * g2:+.1f}%, so the action is due.")
    return None


# --- flips: "if we got more traffic from {s1} than {s2} during the last {n} weeks" -----


def _source_sums(s, p, n_weeks) -> tuple[int, int, int]:
    d0 = _weeks_back(n_weeks)
    a = _series(s, "traffic_source", d0, p["traffic_source_1"])
    b = _series(s, "traffic_source", d0, p["traffic_source_2"])
    return int(a.sum()), int(b.sum()), len(a)


def _traffic_clear(a: int, b: int) -> bool:
    return a >= b + TRAFFIC_MARGIN and a >= TRAFFIC_RATIO * b


def traffic_db_flip(p, s):
    """Re-attribute visits of source 2 to source 1 (one cell per visit), spread over the
    period one visit per day, latest day first, until source 1 leads by the margin."""
    d0 = _weeks_back(p["n_weeks"])
    s1, s2 = p["traffic_source_1"], p["traffic_source_2"]
    a, b, _ = _source_sums(s, p, p["n_weeks"])
    need = next(x for x in range(b + 1) if _traffic_clear(a + x, b - x))
    d = s.analytics_data
    pool = d[(d["date_of_visit"] >= d0) & (d["traffic_source"] == s2)].sort_values(["date_of_visit", "visitor_id"])
    by_day = [list(g.itertuples()) for _, g in sorted(pool.groupby("date_of_visit"), reverse=True)]
    picked, r = [], 0
    while len(picked) < need:
        layer = [rows[r] for rows in by_day if len(rows) > r]
        if not layer:
            raise ValueError("not enough visits to re-attribute")
        picked += layer[: need - len(picked)]
        r += 1
    ops = [{"table": "analytics_data", "op": "set", "where": {"date_of_visit": x.date_of_visit, "visitor_id": x.visitor_id},
            "values": {"traffic_source": s1}} for x in picked]
    why = (f"{len(ops)} visits since {d0} came from {s1}, not {s2}, so over the last {p['n_weeks']} weeks {s1} has "
           f"{a + len(ops)} visits and {s2} {b - len(ops)}; {s1} got more, so the action is due.")
    return ops, why


def traffic_request_flip(p, s):
    for n in sorted((n for n in range(2, 7) if n != p["n_weeks"]), key=lambda n: (abs(n - p["n_weeks"]), n)):
        a, b, _ = _source_sums(s, p, n)
        if _traffic_clear(a, b):
            return {**p, "n_weeks": n}, (f"The period is now the last {n} weeks: {p['traffic_source_1']} had {a} visits "
                                         f"and {p['traffic_source_2']} {b}, so the action is due.")
    return None


# --- patch application (a pure copy of src/tools/state.py::_patched) -------------------


def _with_patch(s, patch):
    out = s.copy()
    for edit in patch:
        df = getattr(out, edit["table"])
        if edit["op"] == "append":
            row = {c: edit["row"].get(c) for c in df.columns}
            df = pd.concat([df, pd.DataFrame([row], columns=df.columns).astype(df.dtypes.to_dict())], ignore_index=True)
        else:
            mask = pd.Series(True, index=df.index)
            for col, val in edit["where"].items():
                mask &= df[col] == val
            assert int(mask.sum()) == 1, edit
            if edit["op"] == "set":
                for col, val in edit["values"].items():
                    df.loc[mask, col] = val
            else:
                df = df[~mask].reset_index(drop=True)
        setattr(out, edit["table"], df)
    return out


# --- registrations ---------------------------------------------------------------------

register(
    "If {natural_language_metric} was {more_or_less} than {threshold} at any time since {natural_language_date}, "
    "make a line plot of it since then",
    threshold_plot_gold(_since_date), threshold_db_flip(_since_date), threshold_request_flip(_since_date))

register(
    "If {natural_language_metric} was {more_or_less} than {threshold} any time in the last {past_n_weeks} weeks, "
    "make a line plot of it since then",
    threshold_plot_gold(_past_weeks_date), threshold_db_flip(_past_weeks_date), threshold_request_flip(_past_weeks_date))

register(
    "If {natural_language_metric} is more than {natural_language_growth_threshold} {higher_or_lower} than "
    "{natural_language_date}, make a line plot of it since then",
    growth_since_date_gold, growth_db_flip(_dates_since_date), growth_request_flip(_dates_since_date))

register(
    "If {natural_language_metric} is more than {natural_language_growth_threshold} {higher_or_lower} than it was on "
    "{day_of_week}, make a line plot of it since then",
    growth_since_weekday_gold, growth_db_flip(_dates_since_weekday), growth_request_flip(_dates_since_weekday))

register(
    "If {natural_language_metric} on {day_of_week} was more than {natural_language_growth_threshold} {higher_or_lower} "
    "than it was the previous {day_of_week}, make a line plot of it over that period.",
    growth_week_on_week_gold, growth_db_flip(_week_pair), growth_request_flip(_week_pair))

register(
    "Can you check the percent growth of {natural_language_metric} since {day_of_week}? If it grew by more than "
    "{natural_language_metric_2}, plot both lines since then",
    relative_growth_plots_gold, relative_growth_db_flip, relative_growth_request_flip)

register(
    "If we got more traffic from {traffic_source_1} than {traffic_source_2} during the last {n_weeks} weeks, "
    "make bar charts of both over that period",
    traffic_sources_gold, traffic_db_flip, traffic_request_flip)

register(
    "If {natural_language_metric} was {more_or_less} than {threshold} at any time since {natural_language_date} "
    "send an email to {sender} titled 'Update on {natural_language_metric}' saying 'I noticed "
    "{natural_language_metric} was {more_or_less} than {threshold} - can you update me?'",
    # {threshold} appears twice (condition and email body); both copies change together,
    # so it is still one slot (build.py counts distinct slots).
    email_if_threshold_gold, threshold_db_flip(_since_date), threshold_request_flip(_since_date))

register(
    "If {natural_language_metric} was {more_or_less} than {threshold} at any time since {natural_language_date} "
    "make a backlog task called 'Improve {natural_language_metric}' for {name} on the front-end board with a "
    "deadline of next Friday",
    task_if_threshold_gold, threshold_db_flip(_since_date), threshold_request_flip(_since_date))

register(
    "If {natural_language_metric} was {more_or_less} than {threshold} at any time since {natural_language_date} "
    "make a backlog task called 'Improve {natural_language_metric}' on the front-end board with a deadline of next "
    "Friday for the person with the most completed front end tasks",
    task_most_completed_if_threshold_gold, threshold_db_flip(_since_date), threshold_request_flip(_since_date))

register(
    "Check the percent growth of {natural_language_metric} since {day_of_week} and if was more than "
    "{natural_language_metric_2} make a backlog task called 'Improve {natural_language_metric_2}' for {name} on the "
    "front-end board with a deadline of next Friday",
    task_if_growth_gold, relative_growth_db_flip, relative_growth_request_flip)

register(
    "If {natural_language_metric} was {more_or_less} than {threshold} at any time since {natural_language_date} "
    "delete all {assigned_to_first_name}'s leads in the CRM",
    delete_leads_if_threshold_gold, threshold_db_flip(_since_date), threshold_request_flip(_since_date))

register(
    "Check the percent growth of {natural_language_metric} since {day_of_week} and if was more than "
    "{natural_language_metric_2} make a backlog task called 'Improve {natural_language_metric_2}' for {name} on the "
    "front-end board with a deadline of next Friday. Also schedule a half-hour meeting called 'Discuss "
    "{natural_language_metric}' with them at the first time I can do tomorrow",
    task_and_meeting_if_growth_gold, relative_growth_db_flip, relative_growth_request_flip)
