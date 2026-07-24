# OAuth setup (public)

1. Create a Google Cloud project (personal account).
2. Enable **Google Tasks API**.
3. Configure OAuth consent (External) and add yourself as a test user.
4. Create an OAuth client: **Web application**.
5. Authorized redirect URI:

   `{BASE_URL}/auth/google/callback`

   Local example: `http://127.0.0.1:8010/auth/google/callback`

6. Copy client id + secret into env (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`). Never commit them.

See `.env.example` and `README.md`.
