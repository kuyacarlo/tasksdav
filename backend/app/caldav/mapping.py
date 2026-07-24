from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from icalendar import Calendar, Todo

from app.db.models import TaskMap


def google_due_to_date(due: str | None) -> date | None:
    if not due:
        return None
    # Google returns RFC3339; API stores date only.
    return datetime.fromisoformat(due.replace("Z", "+00:00")).date()


def date_to_google_due(d: date | None) -> str | None:
    if d is None:
        return None
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc).strftime("%Y-%m-%dT00:00:00.000Z")


def task_to_vtodo(
    task: dict[str, Any],
    *,
    ical_uid: str,
    list_id: str,
    parent_uid: str | None = None,
) -> bytes:
    cal = Calendar()
    cal.add("prodid", "-//TasksDAV//EN")
    cal.add("version", "2.0")
    todo = Todo()
    todo.add("uid", ical_uid)
    todo.add("summary", task.get("title") or "")
    if notes := task.get("notes"):
        todo.add("description", notes)
    if due := google_due_to_date(task.get("due")):
        todo.add("due", due)
    status = task.get("status")
    if status == "completed":
        todo.add("status", "COMPLETED")
        if completed := task.get("completed"):
            todo.add("completed", datetime.fromisoformat(completed.replace("Z", "+00:00")))
    else:
        todo.add("status", "NEEDS-ACTION")
    if parent_uid:
        todo.add("related-to", parent_uid, parameters={"RELTYPE": "PARENT"})
    # Opaque ids for roundtrip helpers
    todo.add("x-tasksdav-google-id", task["id"])
    todo.add("x-tasksdav-list-id", list_id)
    if parent := task.get("parent"):
        todo.add("x-tasksdav-parent-id", parent)
    cal.add_component(todo)
    return cal.to_ical()


def vtodo_to_google_body(raw: bytes) -> tuple[dict[str, Any], str | None, str | None]:
    """Return (google_body, ical_uid, parent_google_id_hint)."""
    cal = Calendar.from_ical(raw)
    todo = next(c for c in cal.walk() if c.name == "VTODO")
    uid = str(todo.get("uid") or uuid4())
    body: dict[str, Any] = {
        "title": str(todo.get("summary") or ""),
    }
    if todo.get("description") is not None:
        body["notes"] = str(todo.get("description"))
    due = todo.get("due")
    if due is not None:
        if hasattr(due.dt, "date") and not isinstance(due.dt, date):
            body["due"] = date_to_google_due(due.dt.date())
        elif isinstance(due.dt, date):
            body["due"] = date_to_google_due(due.dt)
        else:
            body["due"] = date_to_google_due(due.dt)
    status = str(todo.get("status") or "NEEDS-ACTION").upper()
    body["status"] = "completed" if status == "COMPLETED" else "needsAction"
    parent_hint = None
    if todo.get("x-tasksdav-parent-id"):
        parent_hint = str(todo.get("x-tasksdav-parent-id"))
    google_id = str(todo.get("x-tasksdav-google-id")) if todo.get("x-tasksdav-google-id") else None
    if google_id:
        body["id"] = google_id
    return body, uid, parent_hint


def ensure_ical_uid(task_map: TaskMap | None, google_task_id: str) -> str:
    if task_map and task_map.ical_uid:
        return task_map.ical_uid
    return f"{google_task_id}@tasksdav.local"
