# Security model

## Is it multi-tenant?

**Yes — shared app, shared database, app-layer isolation.**

Many users share one TasksDAV deploy and one Postgres (Compose or Neon).  
**Google Tasks is still the source of truth for task bodies.** Our DB stores:

| Column | Sensitivity |
|--------|-------------|
| `email`, `google_sub` | identifying |
| `caldav_password_hash` | bcrypt hash (not reversible) |
| `refresh_token_enc` | **Google refresh token**, Fernet-encrypted with `SECRET_KEY` |
| `list_maps` / `task_maps` | IDs + etags only (not titles/notes) |

## How a normal request stays on one tenant

1. **CalDAV**: HTTP Basic → lookup by `caldav_username` → verify password hash → all queries filter `user_id` / `_assert_user(path_username)`.
2. **Connect UI**: signed session cookie → `/api/me` only for that session user.
3. **Google API calls** use that user’s decrypted refresh token only.

Guessing another user’s CalDAV URL path without their app password → **401**.  
Using user A’s password on user B’s path → **403** (`_assert_user`).

## What “open the DB” actually gets an attacker

If someone steals **`DATABASE_URL` only**:

- Sees every tenant’s email + mapping IDs + ciphertext tokens.
- Does **not** get plaintext CalDAV passwords (bcrypt).
- Does **not** get Google tokens **unless** they also have **`SECRET_KEY`** (Fernet).

If they steal **`DATABASE_URL` + `SECRET_KEY`**:

- They can decrypt every user’s Google refresh token → read/write that user’s Google Tasks.

So: **DB credentials and `SECRET_KEY` are crown jewels.** Treat them like production secrets.

## What we do / must do

| Control | Status |
|---------|--------|
| Per-user CalDAV Basic auth | yes |
| Path username must match auth user | yes |
| Queries scoped by `user_id` | yes |
| Google tokens encrypted at rest | yes (app-level Fernet) |
| CalDAV passwords hashed | yes (bcrypt) |
| Task content not stored locally | yes (Google SoT) |
| Never commit `.env` / connection strings | required |
| Neon: strong password, SSL, prefer IP allow / no public broad access | required in prod |
| Postgres RLS / per-tenant schemas | **not yet** (defense-in-depth backlog) |
| Per-user encryption keys (KMS) | **not yet** |

## Practical rules

1. Don’t put Neon/Postgres on the open internet without SSL + strong password (and IP allow when possible).
2. Never ship `SECRET_KEY` in the image or the public repo.
3. Rotate CalDAV app passwords and Google OAuth client secret if either leaks.
4. For hostile multi-tenant SaaS later: add RLS or one-DB-per-tenant, and wrap token encryption with KMS — app checks alone aren’t enough against a stolen DB URL + app secret.
