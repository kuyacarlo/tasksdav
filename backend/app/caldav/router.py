from __future__ import annotations

import secrets
from typing import Any
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.caldav.mapping import ensure_ical_uid, task_to_vtodo, vtodo_to_google_body
from app.core.config import get_settings
from app.core.security import decrypt_token, verify_password
from app.db.models import ListMap, TaskMap, User
from app.db.session import get_db
from app.google.client import GoogleTasksClient, refresh_access_token

router = APIRouter(prefix="/caldav", tags=["caldav"])
security = HTTPBasic()

DAV = "DAV:"
CAL = "urn:ietf:params:xml:ns:caldav"
CS = "http://calendarserver.org/ns/"
ET.register_namespace("D", DAV)
ET.register_namespace("C", CAL)
ET.register_namespace("CS", CS)


def _q(tag: str, ns: str = DAV) -> str:
    return f"{{{ns}}}{tag}"


async def _user_from_basic(
    credentials: HTTPBasicCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(select(User).where(User.caldav_username == credentials.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(credentials.password, user.caldav_password_hash):
        raise HTTPException(status_code=401, detail="Invalid CalDAV credentials", headers={"WWW-Authenticate": "Basic"})
    return user


async def _tasks_client(user: User) -> GoogleTasksClient:
    refresh = decrypt_token(user.refresh_token_enc)
    tokens = await refresh_access_token(refresh)
    return GoogleTasksClient(tokens["access_token"])


def _multistatus(responses: list[ET.Element]) -> Response:
    root = ET.Element(_q("multistatus"))
    for resp in responses:
        root.append(resp)
    xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return Response(content=xml, media_type="application/xml; charset=utf-8", status_code=207)


def _prop_response(href: str, props: dict[str, str | ET.Element | None], status: str = "HTTP/1.1 200 OK") -> ET.Element:
    resp = ET.Element(_q("response"))
    href_el = ET.SubElement(resp, _q("href"))
    href_el.text = href
    propstat = ET.SubElement(resp, _q("propstat"))
    prop = ET.SubElement(propstat, _q("prop"))
    for name, value in props.items():
        if ":" in name:
            ns, local = name.split(":", 1)
            ns_uri = {"D": DAV, "C": CAL, "CS": CS}[ns]
            el = ET.SubElement(prop, _q(local, ns_uri))
        else:
            el = ET.SubElement(prop, _q(name))
        if isinstance(value, ET.Element):
            el.append(value)
        elif value is not None:
            el.text = value
    st = ET.SubElement(propstat, _q("status"))
    st.text = status
    return resp


@router.api_route("", methods=["PROPFIND", "OPTIONS"])
@router.api_route("/", methods=["PROPFIND", "OPTIONS"])
async def caldav_root(request: Request, user: User = Depends(_user_from_basic)) -> Response:
    if request.method == "OPTIONS":
        return Response(
            status_code=204,
            headers={
                "Allow": "OPTIONS, PROPFIND, REPORT, GET, PUT, DELETE",
                "DAV": "1, 2, calendar-access",
            },
        )
    base = get_settings().base_url.rstrip("/")
    home = f"{base}/caldav/{user.caldav_username}/"
    return _multistatus(
        [
            _prop_response(
                f"{base}/caldav/",
                {
                    "D:resourcetype": ET.Element(_q("collection")),
                    "D:displayname": "TasksDAV",
                    "D:current-user-principal": _href_el(f"{base}/caldav/{user.caldav_username}/principal/"),
                },
            ),
            _prop_response(
                home,
                {
                    "D:resourcetype": ET.Element(_q("collection")),
                    "D:displayname": user.email,
                    "C:calendar-home-set": _href_el(home),
                },
            ),
        ]
    )


def _href_el(href: str) -> ET.Element:
    wrap = ET.Element(_q("href"))
    wrap.text = href
    return wrap


@router.api_route("/{username}/principal/", methods=["PROPFIND", "OPTIONS"])
async def principal(username: str, request: Request, user: User = Depends(_user_from_basic)) -> Response:
    _assert_user(username, user)
    if request.method == "OPTIONS":
        return Response(status_code=204, headers={"DAV": "1, 2, calendar-access"})
    base = get_settings().base_url.rstrip("/")
    home = f"{base}/caldav/{user.caldav_username}/"
    return _multistatus(
        [
            _prop_response(
                f"{home}principal/",
                {
                    "D:resourcetype": _with_children([_q("principal")]),
                    "D:displayname": user.email,
                    "C:calendar-home-set": _href_el(home),
                },
            )
        ]
    )


def _with_children(tags: list[str]) -> ET.Element:
    root = ET.Element(_q("resourcetype"))
    for tag in tags:
        ET.SubElement(root, tag)
    return root


def _assert_user(username: str, user: User) -> None:
    if username != user.caldav_username:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.api_route("/{username}/", methods=["PROPFIND", "OPTIONS"])
async def calendar_home(
    username: str,
    request: Request,
    user: User = Depends(_user_from_basic),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _assert_user(username, user)
    if request.method == "OPTIONS":
        return Response(status_code=204, headers={"DAV": "1, 2, calendar-access"})
    client = await _tasks_client(user)
    lists = await client.list_tasklists()
    base = get_settings().base_url.rstrip("/")
    home = f"{base}/caldav/{user.caldav_username}/"
    responses = [
        _prop_response(
            home,
            {
                "D:resourcetype": ET.Element(_q("collection")),
                "D:displayname": "Calendar Home",
            },
        )
    ]
    for gl in lists:
        cal_id = gl["id"]
        name = gl.get("title") or "Tasks"
        await _upsert_list(db, user, cal_id, name)
        cal_href = f"{home}{cal_id}/"
        rt = ET.Element(_q("resourcetype"))
        ET.SubElement(rt, _q("collection"))
        ET.SubElement(rt, _q("calendar", CAL))
        responses.append(
            _prop_response(
                cal_href,
                {
                    "D:resourcetype": rt,
                    "D:displayname": name,
                    "CS:getctag": secrets.token_hex(4),
                    "C:supported-calendar-component-set": _comp_set(["VTODO"]),
                },
            )
        )
    await db.commit()
    return _multistatus(responses)


def _comp_set(names: list[str]) -> ET.Element:
    wrap = ET.Element(_q("supported-calendar-component-set", CAL))
    for n in names:
        el = ET.SubElement(wrap, _q("comp", CAL))
        el.set("name", n)
    return wrap


async def _upsert_list(db: AsyncSession, user: User, google_list_id: str, name: str) -> ListMap:
    result = await db.execute(
        select(ListMap).where(ListMap.user_id == user.id, ListMap.google_list_id == google_list_id)
    )
    row = result.scalar_one_or_none()
    if row:
        row.display_name = name
        return row
    row = ListMap(
        user_id=user.id,
        google_list_id=google_list_id,
        caldav_calendar_id=google_list_id,
        display_name=name,
        ctag=secrets.token_hex(4),
    )
    db.add(row)
    return row


@router.api_route("/{username}/{list_id}/", methods=["PROPFIND", "REPORT", "OPTIONS"])
async def calendar_collection(
    username: str,
    list_id: str,
    request: Request,
    user: User = Depends(_user_from_basic),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _assert_user(username, user)
    if request.method == "OPTIONS":
        return Response(status_code=204, headers={"DAV": "1, 2, calendar-access", "Allow": "OPTIONS, PROPFIND, REPORT, GET, PUT, DELETE"})

    client = await _tasks_client(user)
    tasks = await client.list_tasks(list_id)
    base = get_settings().base_url.rstrip("/")
    home = f"{base}/caldav/{user.caldav_username}/{list_id}/"

    # Build uid map for parent RELATED-TO
    id_to_uid: dict[str, str] = {}
    for t in tasks:
        result = await db.execute(
            select(TaskMap).where(TaskMap.user_id == user.id, TaskMap.google_task_id == t["id"])
        )
        tm = result.scalar_one_or_none()
        uid = ensure_ical_uid(tm, t["id"])
        id_to_uid[t["id"]] = uid
        if not tm:
            db.add(
                TaskMap(
                    user_id=user.id,
                    google_task_id=t["id"],
                    google_list_id=list_id,
                    ical_uid=uid,
                    etag=t.get("etag"),
                )
            )
        else:
            tm.etag = t.get("etag")
            tm.ical_uid = uid
    await db.commit()

    if request.method == "PROPFIND":
        rt = ET.Element(_q("resourcetype"))
        ET.SubElement(rt, _q("collection"))
        ET.SubElement(rt, _q("calendar", CAL))
        responses = [
            _prop_response(
                home,
                {
                    "D:resourcetype": rt,
                    "D:displayname": list_id,
                    "CS:getctag": secrets.token_hex(4),
                },
            )
        ]
        for t in tasks:
            href = f"{home}{id_to_uid[t['id']]}.ics"
            responses.append(
                _prop_response(
                    href,
                    {
                        "D:getetag": t.get("etag") or secrets.token_hex(4),
                        "D:getcontenttype": "text/calendar; charset=utf-8; component=VTODO",
                    },
                )
            )
        return _multistatus(responses)

    # REPORT calendar-query / multiget → return calendar-data
    responses = []
    for t in tasks:
        uid = id_to_uid[t["id"]]
        parent_uid = id_to_uid.get(t["parent"]) if t.get("parent") else None
        ics = task_to_vtodo(t, ical_uid=uid, list_id=list_id, parent_uid=parent_uid)
        href = f"{home}{uid}.ics"
        resp = ET.Element(_q("response"))
        href_el = ET.SubElement(resp, _q("href"))
        href_el.text = href
        propstat = ET.SubElement(resp, _q("propstat"))
        prop = ET.SubElement(propstat, _q("prop"))
        etag_el = ET.SubElement(prop, _q("getetag"))
        etag_el.text = t.get("etag") or ""
        caldata = ET.SubElement(prop, _q("calendar-data", CAL))
        caldata.text = ics.decode("utf-8")
        st = ET.SubElement(propstat, _q("status"))
        st.text = "HTTP/1.1 200 OK"
        responses.append(resp)
    return _multistatus(responses)


@router.get("/{username}/{list_id}/{object_id}.ics")
async def get_object(
    username: str,
    list_id: str,
    object_id: str,
    user: User = Depends(_user_from_basic),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _assert_user(username, user)
    client = await _tasks_client(user)
    result = await db.execute(
        select(TaskMap).where(TaskMap.user_id == user.id, TaskMap.ical_uid == object_id)
    )
    tm = result.scalar_one_or_none()
    if not tm:
        # object_id may be google id
        task = await client.get_task(list_id, object_id)
        uid = ensure_ical_uid(None, task["id"])
        parent_uid = None
        ics = task_to_vtodo(task, ical_uid=uid, list_id=list_id, parent_uid=parent_uid)
        return Response(content=ics, media_type="text/calendar; charset=utf-8")

    task = await client.get_task(list_id, tm.google_task_id)
    parent_uid = None
    if task.get("parent"):
        pref = await db.execute(
            select(TaskMap).where(TaskMap.user_id == user.id, TaskMap.google_task_id == task["parent"])
        )
        ptm = pref.scalar_one_or_none()
        parent_uid = ptm.ical_uid if ptm else None
    ics = task_to_vtodo(task, ical_uid=tm.ical_uid, list_id=list_id, parent_uid=parent_uid)
    return Response(content=ics, media_type="text/calendar; charset=utf-8", headers={"ETag": task.get("etag") or ""})


@router.put("/{username}/{list_id}/{object_id}.ics")
async def put_object(
    username: str,
    list_id: str,
    object_id: str,
    request: Request,
    user: User = Depends(_user_from_basic),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _assert_user(username, user)
    raw = await request.body()
    body, uid, parent_hint = vtodo_to_google_body(raw)
    client = await _tasks_client(user)

    result = await db.execute(select(TaskMap).where(TaskMap.user_id == user.id, TaskMap.ical_uid == object_id))
    tm = result.scalar_one_or_none()
    if not tm and body.get("id"):
        result = await db.execute(
            select(TaskMap).where(TaskMap.user_id == user.id, TaskMap.google_task_id == body["id"])
        )
        tm = result.scalar_one_or_none()

    google_id = body.pop("id", None)
    if tm or google_id:
        gid = tm.google_task_id if tm else google_id
        task = await client.patch_task(list_id, gid, body)
        if parent_hint is not None:
            await client.move_task(list_id, gid, parent=parent_hint or None)
        if not tm:
            db.add(
                TaskMap(
                    user_id=user.id,
                    google_task_id=task["id"],
                    google_list_id=list_id,
                    ical_uid=uid or object_id,
                    etag=task.get("etag"),
                )
            )
        else:
            tm.etag = task.get("etag")
            tm.ical_uid = uid or tm.ical_uid
        await db.commit()
        return Response(status_code=204, headers={"ETag": task.get("etag") or ""})

    parent = parent_hint
    task = await client.insert_task(list_id, body, parent=parent)
    db.add(
        TaskMap(
            user_id=user.id,
            google_task_id=task["id"],
            google_list_id=list_id,
            ical_uid=uid or object_id,
            etag=task.get("etag"),
        )
    )
    await db.commit()
    return Response(status_code=201, headers={"ETag": task.get("etag") or ""})


@router.delete("/{username}/{list_id}/{object_id}.ics")
async def delete_object(
    username: str,
    list_id: str,
    object_id: str,
    user: User = Depends(_user_from_basic),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _assert_user(username, user)
    client = await _tasks_client(user)
    result = await db.execute(select(TaskMap).where(TaskMap.user_id == user.id, TaskMap.ical_uid == object_id))
    tm = result.scalar_one_or_none()
    if not tm:
        raise HTTPException(status_code=404, detail="Not found")
    await client.delete_task(list_id, tm.google_task_id)
    await db.delete(tm)
    await db.commit()
    return Response(status_code=204)
