# Authentication and access control

## Local setup

Install locked dependencies with `uv sync`. Configure `DATABASE_URL` and
`JWT_SECRET_KEY` in the ignored `.env` file (see `.env.example`). Generate a key:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Keep it private, stable across restarts and shared only by instances of the same
deployment. Missing/short keys cause authentication to return 503; no fallback key
exists. Rotating the key invalidates previously issued tokens.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## Swagger login

1. Open `http://127.0.0.1:8000/docs` and click **Authorize**.
2. Enter an existing user's email in `username` and their original password in
   `password`. Leave `client_id` and `client_secret` empty.
3. Authorize, then call `GET /auth/me` to inspect the current account.

`POST /auth/login` accepts an OAuth2 form (`application/x-www-form-urlencoded`),
not JSON. Fields: `username=admin@example.com` and `password=...`.
It uses the OAuth2 token response so Swagger can consume it:

```json
{
  "access_token": "<signed JWT>",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Send `Authorization: Bearer <access_token>` to other endpoints. `/auth/me` and
business responses use `success`, `message`, `data`. Missing/invalid/expired
authentication returns 401 with `WWW-Authenticate: Bearer`; insufficient
permissions return 403. Generic 422 responses do not echo sensitive inputs.

Use an existing ADMIN to create users in their organization. There is no public
registration or platform-wide administrator. On an empty database, initial
organization/admin provisioning requires a trusted administrative process;
there is no unauthenticated bootstrap bypass.

## Implemented boundary

Resource authorization follows organization, role, then assignment checks.
See the [Sprint 1 endpoint policy and test scope](sprint1_permissions.md).

- Existing scrypt hashes are verified using constant-time digest comparison and
  fixed cost parameters. Plaintext/unsupported hashes are rejected.
- JWT uses HS256 and a 30-minute lifetime. Claims `sub`, `iat`, `exp`, `iss`, `aud`
  and `type` are required. Algorithm, issuer and audience are pinned by the API.
- Requests reload the user from the database. Deleted users/unsupported roles
  are rejected; role changes take effect without re-login.
- `/health`, `/auth/login` and documentation remain public. Business routes
  require authentication; `/db-health` additionally requires ADMIN.
- User management is ADMIN-only within their organization. Customer management
  is limited to ADMIN/SUPERVISOR in the same organization.
- ADMIN sees all conversations in their organization. SUPERVISOR accesses permitted
  operational conversations in their organization; there are currently no additional
  conversation-level restrictions. AGENT lists/reads/updates assigned conversations only.
- Message reads follow conversation access. Staff messages require
  `sender_type=AGENT` and the authenticated user's own `sender_id`. AI/customer
  ingestion needs a separate authenticated integration.
- Organization reads are scoped to the caller's organization and updates to
  ADMIN. Creation/deletion are denied pending trusted onboarding/platform
  permissions. No OWNER role is introduced.
- SQL echo is disabled; bound SQL parameters are hidden to avoid logging hashes.

## Limitations and QA

No refresh tokens, logout revocation, MFA, password reset, teams or reassignment
endpoints are included. Password changes do not revoke existing JWTs; tokens
expire within 30 minutes. Add rate limiting and HTTPS before public exposure:
scrypt uses substantial CPU/memory per verification. Tokens must not be logged.

Email lookup distinguishes unknown accounts (404) from inaccessible accounts
(403); a future privacy pass should normalize this and duplicate-email behavior.

Tests cover real JWTs, real scrypt hashes, SQLite persistence, role changes,
tenant boundaries, assignment boundaries and impersonation attempts. MySQL and
deployment-level concurrency/throttling require environment-specific QA.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

References: [FastAPI OAuth2 JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/),
[PyJWT validation](https://pyjwt.readthedocs.io/en/stable/usage.html).
