import threading
from dataclasses import dataclass, fields

import pandas as pd

_CSV_PATHS = {
    "calendar_events": "data/processed/calendar_events.csv",
    "emails": "data/processed/emails.csv",
    "analytics_data": "data/processed/analytics_data.csv",
    "project_tasks": "data/processed/project_tasks.csv",
    "crm_data": "data/processed/customer_relationship_manager_data.csv",
    "directory_emails": "data/raw/email_addresses.csv",
}


def _load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(_CSV_PATHS[name], dtype=str)


def _load_analytics_data() -> pd.DataFrame:
    df = _load_csv("analytics_data")
    df["user_engaged"] = df["user_engaged"] == "True"
    return df


def _load_directory_emails() -> pd.DataFrame:
    return pd.read_csv(_CSV_PATHS["directory_emails"], header=None, names=["email_address"])


@dataclass
class ToolState:
    calendar_events: pd.DataFrame
    emails: pd.DataFrame
    analytics_data: pd.DataFrame
    plots_data: pd.DataFrame
    project_tasks: pd.DataFrame
    crm_data: pd.DataFrame
    directory_emails: pd.DataFrame

    @classmethod
    def from_csv_files(cls) -> "ToolState":
        return cls(
            calendar_events=_load_csv("calendar_events"),
            emails=_load_csv("emails"),
            analytics_data=_load_analytics_data(),
            plots_data=pd.DataFrame(columns=pd.Index(["file_path"])),
            project_tasks=_load_csv("project_tasks"),
            crm_data=_load_csv("crm_data"),
            directory_emails=_load_directory_emails(),
        )

    def copy(self) -> "ToolState":
        return ToolState(**{f.name: getattr(self, f.name).copy() for f in fields(self)})

    def reset(self) -> None:
        fresh = _patched(_pristine_state().copy())
        for f in fields(self):
            setattr(self, f.name, getattr(fresh, f.name))


_pristine_lock = threading.Lock()
_pristine: ToolState | None = None


def _pristine_state() -> ToolState:
    """The CSV-backed state, loaded from disk once per process.

    Evaluation resets the sandbox several times per task, so reset hands out
    copies of this snapshot instead of re-reading the CSVs every time. The
    data files never change while a process is running (regeneration is a
    separate command), so the snapshot cannot go stale.
    """
    global _pristine
    with _pristine_lock:
        if _pristine is None:
            _pristine = ToolState.from_csv_files()
        return _pristine


_local = threading.local()


# COS597C change: a per-thread start-state patch, for counterfactual twin tasks
# (docs/research/other-benchmarks/workbench.md). A patch is a list of edits:
#   {"table": "emails", "op": "append", "row": {...}}          add one row
#   {"table": "project_tasks", "op": "set", "where": {"task_id": "00000123"},
#    "values": {"status": "in progress"}}                       change one row's cells
#   {"table": "emails", "op": "delete", "where": {"email_id": "00000042"}}
# "where" must match exactly one row. With no patch set, behaviour is upstream's.
def _patched(state: "ToolState") -> "ToolState":
    for edit in getattr(_local, "state_patch", None) or []:
        df = getattr(state, edit["table"])
        for col, val in {**edit.get("row", {}), **edit.get("values", {})}.items():
            if col in df.columns and df[col].dtype == bool and not isinstance(val, bool):
                raise ValueError(f"patch: column {col} of {edit['table']} needs a JSON boolean, got {val!r}")
        if edit["op"] == "append":
            row = {c: edit["row"].get(c) for c in df.columns}
            unknown = set(edit["row"]) - set(df.columns)
            if unknown:
                raise ValueError(f"patch: unknown columns {unknown} for {edit['table']}")
            df = pd.concat([df, pd.DataFrame([row], columns=df.columns).astype(df.dtypes.to_dict())], ignore_index=True)
        else:
            mask = pd.Series(True, index=df.index)
            for col, val in edit["where"].items():
                mask &= df[col] == val
            if int(mask.sum()) != 1:
                raise ValueError(f"patch: 'where' {edit['where']} matches {int(mask.sum())} rows in {edit['table']}")
            if edit["op"] == "set":
                for col, val in edit["values"].items():
                    if col not in df.columns:
                        raise ValueError(f"patch: unknown column {col} for {edit['table']}")
                    df.loc[mask, col] = val
            elif edit["op"] == "delete":
                df = df[~mask].reset_index(drop=True)
            else:
                raise ValueError(f"patch: unknown op {edit['op']}")
        setattr(state, edit["table"], df)
    return state


def set_state_patch(patch: list[dict] | None) -> None:
    """Set (or clear, with None) this thread's start-state patch and reset the state to it."""
    previous = getattr(_local, "state_patch", None)
    _local.state_patch = patch
    try:
        reset_state()
    except Exception:
        _local.state_patch = previous
        reset_state()
        raise


def get_state() -> "ToolState":
    state = getattr(_local, "tool_state", None)
    if state is None:
        _local.tool_state = _patched(_pristine_state().copy())
    return _local.tool_state


def reset_state() -> None:
    get_state().reset()
