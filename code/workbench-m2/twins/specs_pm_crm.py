"""Template specs: project management and CRM templates with empty-set no-op tasks.

See framework.py for the contract. Each gold rule mirrors the upstream logic function
named in its comment (scripts/data_generation/task_outcome_generation/).

Flip design, in short:
- Project management: the person has no task that matches the filter. The DB flip
  changes ONE cell of ONE of the person's own tasks so that exactly one task matches:
  a Backlog task moves to "In Progress" (the person started it), or the Backlog task
  with the earliest due date gets a due date three days in the past (2023-11-27, the
  earliest due date in the data).
- CRM (person + status + product): the person's first customer (data order, so it is
  inside the 5-result search cap) with the asked status gets the asked product interest.
- CRM (unanswered proposals): one Proposal customer for the product, with no notes
  that would contradict it, has its last contact moved 10 days before the cutoff; its
  follow-up date moves by the same amount (the data generator sets follow_up_by =
  last_contact_date + 7..30 days). The request flip changes the number of weeks.
"""

from __future__ import annotations

from framework import register

from datetime import timedelta

import pandas as pd

from src.data_generation.data_generation_utils import HARDCODED_CURRENT_TIME, get_first_name

TODAY = str(HARDCODED_CURRENT_TIME.date())  # "2023-11-30"
OVERDUE_DATE = "2023-11-27"  # 3 days overdue; the earliest due date in project_tasks.csv


# --- helpers -------------------------------------------------------------------


def _pm_email(s, name: str) -> str:
    """The team member's email for a first name, as the generator derives names."""
    emails = [e for e in s.project_tasks["assigned_to_email"].unique() if get_first_name(e) == name]
    if len(emails) != 1:
        raise ValueError(f"name {name!r} maps to {emails}")
    return emails[0]


def _tasks_of(s, email: str) -> pd.DataFrame:
    return s.project_tasks[s.project_tasks["assigned_to_email"] == email]


def _in_progress(s, email: str) -> pd.DataFrame:
    pt = s.project_tasks
    return pt[(pt["assigned_to_email"] == email) & (pt["list_name"] == "In Progress")]


def _overdue_backlog(s, email: str) -> pd.DataFrame:
    pt = s.project_tasks
    return pt[(pt["assigned_to_email"] == email) & (pt["list_name"] == "Backlog") & (pt["due_date"] < TODAY)]


def _update_task(task_id: str, field: str, value: str) -> str:
    return f'project_management.update_task.func(task_id="{task_id}", field="{field}", new_value="{value}")'


def _flip_to_in_progress(s, email: str, name: str) -> tuple[list[dict], str]:
    """One of the person's Backlog tasks (earliest due date that is not overdue) is In Progress."""
    if not _in_progress(s, email).empty:
        raise ValueError(f"{email} already has in-progress tasks")
    t = _tasks_of(s, email)
    cand = t[(t["list_name"] == "Backlog") & (t["due_date"] >= TODAY)].sort_values(["due_date", "task_id"])
    if cand.empty:
        raise ValueError(f"{email} has no backlog task to start")
    row = cand.iloc[0]
    patch = [{"table": "project_tasks", "op": "set", "where": {"task_id": row["task_id"]},
              "values": {"list_name": "In Progress"}}]
    why = (f"{name}'s task '{row['task_name']}' ({row['task_id']}) is now In Progress instead of Backlog, "
           f"so {name} has exactly one in-progress task.")
    return patch, why


def _flip_to_overdue(s, email: str, name: str) -> tuple[list[dict], str]:
    """The person's Backlog task with the earliest due date is due 2023-11-27 (overdue)."""
    if not _overdue_backlog(s, email).empty:
        raise ValueError(f"{email} already has overdue backlog tasks")
    t = _tasks_of(s, email)
    cand = t[t["list_name"] == "Backlog"].sort_values(["due_date", "task_id"])
    if cand.empty:
        raise ValueError(f"{email} has no backlog task")
    row = cand.iloc[0]
    patch = [{"table": "project_tasks", "op": "set", "where": {"task_id": row["task_id"]},
              "values": {"due_date": OVERDUE_DATE}}]
    why = (f"{name}'s Backlog task '{row['task_name']}' ({row['task_id']}) is now due {OVERDUE_DATE} instead of "
           f"{row['due_date']}, so it is overdue (before {TODAY}) and not started: exactly one such task.")
    return patch, why


# --- Move all of {name}'s tasks that are in progress to in review ----------------
# upstream: generate_project_management_task_and_outcome.move_tasks_to_in_review_logic


def to_review_gold(p, s):
    return [_update_task(i, "list_name", "In Review") for i in _in_progress(s, _pm_email(s, p["name"]))["task_id"]]


def to_review_flip(p, s):
    return _flip_to_in_progress(s, _pm_email(s, p["name"]), p["name"])


register("Move all of {name}'s tasks that are in progress to in review", to_review_gold, to_review_flip)


# --- Move all of {name}'s overdue tasks in the backlog to in progress ------------
# upstream: generate_project_management_task_and_outcome.move_overdue_tasks_logic


def overdue_to_progress_gold(p, s):
    return [_update_task(i, "list_name", "In Progress") for i in _overdue_backlog(s, _pm_email(s, p["name"]))["task_id"]]


def overdue_to_progress_flip(p, s):
    return _flip_to_overdue(s, _pm_email(s, p["name"]), p["name"])


register("Move all of {name}'s overdue tasks in the backlog to in progress", overdue_to_progress_gold,
         overdue_to_progress_flip)


# --- {name_1} is sick so reassign their in progress tasks to {name_2}. -----------
# upstream: generate_project_management_task_and_outcome.reassign_unfinished_tasks_logic


def sick_gold(p, s):
    e1, e2 = _pm_email(s, p["name_1"]), _pm_email(s, p["name_2"])
    return [_update_task(i, "assigned_to_email", e2) for i in _in_progress(s, e1)["task_id"]]


def sick_flip(p, s):
    return _flip_to_in_progress(s, _pm_email(s, p["name_1"]), p["name_1"])


register("{name_1} is sick so reassign their in progress tasks to {name_2}.", sick_gold, sick_flip)


# --- {name_1} is on vacation now so move all the tasks they are currently working on to the backlog.
# upstream: generate_project_management_task_and_outcome.move_unfinished_tasks_to_backlog_logic


def vacation_gold(p, s):
    e1 = p.get("email_1") or _pm_email(s, p["name_1"])
    return [_update_task(i, "list_name", "Backlog") for i in _in_progress(s, e1)["task_id"]]


def vacation_flip(p, s):
    e1 = p.get("email_1") or _pm_email(s, p["name_1"])
    return _flip_to_in_progress(s, e1, p["name_1"])


register("{name_1} is on vacation now so move all the tasks they are currently working on to the backlog.",
         vacation_gold, vacation_flip)


# --- Give all the overdue tasks that {name_1} hasn't started to {name_2}. --------
# upstream: generate_project_management_task_and_outcome.reassign_overdue_tasks_logic


def overdue_give_gold(p, s):
    e1 = p.get("email_1") or _pm_email(s, p["name_1"])
    e2 = p.get("email_2") or _pm_email(s, p["name_2"])
    return [_update_task(i, "assigned_to_email", e2) for i in _overdue_backlog(s, e1)["task_id"]]


def overdue_give_flip(p, s):
    e1 = p.get("email_1") or _pm_email(s, p["name_1"])
    return _flip_to_overdue(s, e1, p["name_1"])


register("Give all the overdue tasks that {name_1} hasn't started to {name_2}.", overdue_give_gold, overdue_give_flip)


# --- CRM: person + status + product -------------------------------------------------


def _crm_match(s, email: str, status: str, product: str) -> pd.DataFrame:
    c = s.crm_data
    return c[(c["assigned_to_email"] == email) & (c["status"] == status) & (c["product_interest"] == product)]


def _flip_product(s, email: str, status: str, product: str, first_name: str) -> tuple[list[dict], str]:
    """The person's first customer (data order) in ``status`` now has ``product`` as its interest."""
    if not _crm_match(s, email, status, product).empty:
        raise ValueError("already matches")
    c = s.crm_data
    cand = c[(c["assigned_to_email"] == email) & (c["status"] == status)]
    if cand.empty:
        raise ValueError(f"{email} has no {status} customer")
    row = cand.iloc[0]
    patch = [{"table": "crm_data", "op": "set", "where": {"customer_id": row["customer_id"]},
              "values": {"product_interest": product}}]
    why = (f"{first_name}'s {status} customer {row['customer_name']} ({row['customer_id']}) is now interested in "
           f"{product} instead of {row['product_interest']}, so exactly one of {first_name}'s customers is "
           f"{status} and interested in {product}.")
    return patch, why


# --- Reassign all of {assigned_to_first_name}'s leads that are interested in ... ---
# upstream: generate_customer_relationship_manager_task_and_outcome.reassign_all_leads_for_product_logic


def leads_gold(p, s):
    return [
        f'customer_relationship_manager.update_customer.func(customer_id="{i}", field="assigned_to_email", '
        f'new_value="{p["new_assigned_to_email"]}")'
        for i in _crm_match(s, p["assigned_to_email"], "Lead", p["product_interest"])["customer_id"]
    ]


def leads_flip(p, s):
    return _flip_product(s, p["assigned_to_email"], "Lead", p["product_interest"], p["assigned_to_first_name"])


register(
    "Reassign all of {assigned_to_first_name}'s leads that are interested in {natural_language_product_interest} "
    "to {new_assigned_to_first_name} in the crm.",
    leads_gold,
    leads_flip,
)


# --- Delete all of {assigned_to_first_name}'s customers that are in the {new_status_natural_language} stage ...
# upstream: generate_customer_relationship_manager_task_and_outcome.delete_all_customers_in_stage_logic


def delete_stage_gold(p, s):
    return [
        f'customer_relationship_manager.delete_customer.func(customer_id="{i}")'
        for i in _crm_match(s, p["assigned_to_email"], p["new_status"], p["product_interest"])["customer_id"]
    ]


def delete_stage_flip(p, s):
    return _flip_product(s, p["assigned_to_email"], p["new_status"], p["product_interest"],
                         p["assigned_to_first_name"])


register(
    "Delete all of {assigned_to_first_name}'s customers that are in the {new_status_natural_language} stage and "
    "interested in {natural_language_product_interest} in the crm",
    delete_stage_gold,
    delete_stage_flip,
)


# --- Move all customers that haven't responded to a proposal for the ... in {weeks} weeks to lost
# upstream: generate_customer_relationship_manager_task_and_outcome.move_unresponsive_customers_to_lost_logic

MARGIN_DAYS = 3  # request flip: every Proposal customer of the product is >= 3 days from the cutoff date
SHIFT_DAYS = 10  # DB flip: the new last contact is 10 days before the cutoff date


def _cutoff(weeks) -> str:
    # Mirrors the generator: a string compare against "YYYY-MM-DD 00:00:00".
    return str(HARDCODED_CURRENT_TIME - timedelta(weeks=int(weeks)))


def _proposals(s, product: str) -> pd.DataFrame:
    c = s.crm_data
    return c[(c["status"] == "Proposal") & (c["product_interest"] == product)]


def unresponsive_gold(p, s):
    pr = _proposals(s, p["product_interest"])
    hit = pr[pr["last_contact_date"] < _cutoff(p["weeks"])]
    return [
        f'customer_relationship_manager.update_customer.func(customer_id="{i}", field="status", new_value="Lost")'
        for i in hit["customer_id"]
    ]


def _note_dates(notes) -> list[str]:
    if not isinstance(notes, str):
        return []
    return [part.strip()[:10] for part in notes.split(". ") if part.strip()[:4].isdigit()]


def unresponsive_flip(p, s):
    cutoff = pd.Timestamp(_cutoff(p["weeks"]))
    new_last = cutoff - timedelta(days=SHIFT_DAYS)
    floor = HARDCODED_CURRENT_TIME - timedelta(days=60)  # the data's last-contact window starts here
    if new_last < floor:
        raise ValueError("new last contact date falls outside the data's window")
    new_last_s = str(new_last.date())
    pr = _proposals(s, p["product_interest"])
    # A customer whose notes record no contact after the new date (so the record stays consistent).
    ok = pr[pr["notes"].apply(lambda n: all(d <= new_last_s for d in _note_dates(n)))]
    if ok.empty:
        raise ValueError("no Proposal customer whose notes allow an older last contact")
    row = ok.iloc[0]
    offset = pd.Timestamp(row["follow_up_by"]) - pd.Timestamp(row["last_contact_date"])
    new_follow = str((new_last + offset).date())
    patch = [{"table": "crm_data", "op": "set", "where": {"customer_id": row["customer_id"]},
              "values": {"last_contact_date": new_last_s, "follow_up_by": new_follow}}]
    why = (f"Proposal customer {row['customer_name']} ({row['customer_id']}, {p['product_interest']}) was last "
           f"contacted on {new_last_s} instead of {row['last_contact_date']} (follow-up date moved by the same "
           f"amount, to {new_follow}), which is {SHIFT_DAYS} days before the {p['weeks']}-week cutoff "
           f"{cutoff.date()}, so it is now unanswered for more than {p['weeks']} weeks.")
    return patch, why


def unresponsive_request_flip(p, s):
    orig = int(p["weeks"])
    pr = _proposals(s, p["product_interest"])
    for w in sorted((w for w in range(3, 7) if w != orig), key=lambda w: (abs(w - orig), w)):
        new_p = {**p, "weeks": w}
        if not unresponsive_gold(new_p, s):
            continue
        cut = pd.Timestamp(_cutoff(w))
        gaps = [abs((pd.Timestamp(d) - cut).days) for d in pr["last_contact_date"]]
        if min(gaps) < MARGIN_DAYS:
            continue
        n = len(unresponsive_gold(new_p, s))
        why = (f"With {w} weeks instead of {orig}, the cutoff is {cut.date()}; {n} {p['product_interest']} "
               f"Proposal customer(s) were last contacted before it, and every Proposal customer for the product "
               f"is at least {min(gaps)} days from the cutoff.")
        return new_p, why
    return None


register(
    "Move all customers that haven't responded to a proposal for the {natural_language_product_interest} product "
    "in {weeks} weeks to lost in the crm",
    unresponsive_gold,
    unresponsive_flip,
    unresponsive_request_flip,
)
