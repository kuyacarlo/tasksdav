from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://www.googleapis.com/oauth2/v3/userinfo"
TASKS_BASE = "https://tasks.googleapis.com/tasks/v1"
SCOPE = "https://www.googleapis.com/auth/tasks openid email profile"


def authorization_url(state: str) -> str:
    s = get_settings()
    params = httpx.QueryParams(
        {
            "client_id": s.google_client_id,
            "redirect_uri": s.google_redirect_uri,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return f"{GOOGLE_AUTH}?{params}"


async def exchange_code(code: str) -> dict[str, Any]:
    s = get_settings()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            GOOGLE_TOKEN,
            data={
                "code": code,
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "redirect_uri": s.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        r.raise_for_status()
        return r.json()


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    s = get_settings()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            GOOGLE_TOKEN,
            data={
                "refresh_token": refresh_token,
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "grant_type": "refresh_token",
            },
        )
        r.raise_for_status()
        return r.json()


async def fetch_userinfo(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            GOOGLE_USERINFO,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        r.raise_for_status()
        return r.json()


class GoogleTasksClient:
    def __init__(self, access_token: str) -> None:
        self._headers = {"Authorization": f"Bearer {access_token}"}

    async def list_tasklists(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{TASKS_BASE}/users/@me/lists", headers=self._headers)
            r.raise_for_status()
            return r.json().get("items", [])

    async def list_tasks(self, list_id: str, show_completed: bool = True) -> list[dict[str, Any]]:
        params = {"showCompleted": str(show_completed).lower(), "showHidden": "false", "maxResults": "100"}
        items: list[dict[str, Any]] = []
        page_token: str | None = None
        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                q = dict(params)
                if page_token:
                    q["pageToken"] = page_token
                r = await client.get(
                    f"{TASKS_BASE}/lists/{list_id}/tasks",
                    headers=self._headers,
                    params=q,
                )
                r.raise_for_status()
                body = r.json()
                items.extend(body.get("items", []))
                page_token = body.get("nextPageToken")
                if not page_token:
                    break
        return items

    async def get_task(self, list_id: str, task_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{TASKS_BASE}/lists/{list_id}/tasks/{task_id}",
                headers=self._headers,
            )
            r.raise_for_status()
            return r.json()

    async def insert_task(self, list_id: str, body: dict[str, Any], parent: str | None = None) -> dict[str, Any]:
        params = {"parent": parent} if parent else None
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{TASKS_BASE}/lists/{list_id}/tasks",
                headers=self._headers,
                params=params,
                json=body,
            )
            r.raise_for_status()
            return r.json()

    async def patch_task(self, list_id: str, task_id: str, body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.patch(
                f"{TASKS_BASE}/lists/{list_id}/tasks/{task_id}",
                headers=self._headers,
                json=body,
            )
            r.raise_for_status()
            return r.json()

    async def move_task(
        self, list_id: str, task_id: str, parent: str | None = None, previous: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, str] = {}
        if parent:
            params["parent"] = parent
        if previous:
            params["previous"] = previous
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{TASKS_BASE}/lists/{list_id}/tasks/{task_id}/move",
                headers=self._headers,
                params=params or None,
            )
            r.raise_for_status()
            return r.json()

    async def delete_task(self, list_id: str, task_id: str) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.delete(
                f"{TASKS_BASE}/lists/{list_id}/tasks/{task_id}",
                headers=self._headers,
            )
            r.raise_for_status()
