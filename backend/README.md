# Employee Portal — backend

Django + Django REST Framework. Two apps: `apps.core` (shared base model,
health check, `auth/me/`) and `apps.blog` (`Category`/`Post`, the public
read-only feed, and the authenticated portal API with its approval
workflow).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 8000
```

## Google Sign-In

Login is "Sign in with Google", restricted to a verified
`@<ALLOWED_EMAIL_DOMAIN>` account (default `burntstack.com`) — set in
`.env`:

- `GOOGLE_CLIENT_ID` — from Google Cloud Console (OAuth consent screen +
  a "Web application" credential, with the portal frontend's URL under
  "Authorized JavaScript origins"). **Login is entirely rejected with a
  503 until this is set** — there's no working fallback without it except
  the password endpoint below.
- `ADMIN_EMAILS` — comma-separated. Anyone whose verified Google email is
  in this list gets `is_staff=True`, re-checked on every login.

A first-time sign-in auto-creates the Django `User` — no admin
provisioning step. The domain check uses the ID token's `hd` claim (the
authoritative signal per Google's own docs), not just the email suffix.

Password login (`POST /api/auth/token/`) still works server-side as an
unadvertised admin/recovery fallback and is what the test suite and
`create_test_accounts` below authenticate with — the portal's login page
itself only shows the Google button.

## Local dev / E2E test accounts

`python manage.py create_test_accounts` creates three fixed accounts
(`admin`/`AdminPass123!`, `alice.employee` and `bob.employee`, both
`EmployeePass123!`) idempotently. **Dev/test only** — the passwords are
public in `apps/core/management/commands/create_test_accounts.py`. The
frontend's `e2e/portal.spec.js` depends on these existing.

## Tests

```bash
.venv/bin/python -m pytest --cov=apps --cov-report=term-missing
```

28 tests covering the approval-workflow state machine, ownership boundaries
(an employee can't see or edit another employee's post — 404, not leaked),
staff-only approve/reject, unauthenticated-write rejection, the Google
login endpoint (domain/verification rejection, admin-email sync, no
duplicate users on repeat logins — the real Google verification call is
monkeypatched, not hit for real), and — found and fixed during a security
review of this code — that editing a pending/published post sends it back
to `draft` rather than silently updating already-approved content in
place. 96% statement coverage on `apps/` at last run.

## API surface

- `GET /api/blog/` / `GET /api/blog/<slug>/` — public, published posts only.
- `GET /api/blog/categories/` — public.
- `POST/GET/PATCH/DELETE /api/portal/blog/` — authenticated, scoped to the
  caller's own posts (staff see everyone's).
- `POST /api/portal/blog/<slug>/submit/` — draft → pending.
- `POST /api/portal/blog/<slug>/approve/` / `.../reject/` — staff only.
- `GET /api/portal/blog/pending/` — staff only.
- `POST /api/auth/google/` — the portal's actual login. `{"credential":
  "<google id token>"}` → `{access, refresh}`.
- `POST /api/auth/token/` / `.../refresh/` / `.../verify/` — password JWT
  auth, throttled at `THROTTLE_LOGIN` (default 10/min); unadvertised
  fallback, not shown in `api_root` or the login page.
- `GET /api/auth/me/` — who's logged in.

## Not done yet

Not deployed anywhere. For production: a real `DATABASE_URL` (Postgres —
Supabase is what this config already expects), cloud storage for
`cover_image` uploads (local disk works for dev only), a real `SECRET_KEY`
(the app refuses to start with `DEBUG=False` and the default dev key — see
`config/settings.py`), and `CORS_ALLOWED_ORIGINS`/`CSRF_TRUSTED_ORIGINS` set
to the real frontend + marketing-site domains.
