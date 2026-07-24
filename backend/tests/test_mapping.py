from datetime import date

from app.caldav.mapping import date_to_google_due, google_due_to_date, task_to_vtodo, vtodo_to_google_body


def test_due_roundtrip_date_only():
    d = date(2026, 7, 24)
    g = date_to_google_due(d)
    assert g is not None
    assert google_due_to_date(g) == d


def test_task_to_vtodo_and_back():
    task = {
        "id": "abc123",
        "title": "Ship TasksDAV",
        "notes": "Connect + copy URL",
        "status": "needsAction",
        "due": "2026-07-24T00:00:00.000Z",
    }
    ics = task_to_vtodo(task, ical_uid="abc123@tasksdav.local", list_id="list1")
    body, uid, parent = vtodo_to_google_body(ics)
    assert uid == "abc123@tasksdav.local"
    assert body["title"] == "Ship TasksDAV"
    assert body["notes"] == "Connect + copy URL"
    assert body["status"] == "needsAction"
    assert body["due"].startswith("2026-07-24")
    assert parent is None
