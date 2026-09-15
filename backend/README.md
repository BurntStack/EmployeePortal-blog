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
.venv/bin/python manage.py createsuperuser   # the one real admin account
.venv/bin/python manage.py runserver 8000
```

Add employees via `/admin/` → Users → set `first_name`/`last_name` (used as
the blog byline) and a password. No self-registration endpoint exists.

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

18 tests covering the approval-workflow state machine, ownership boundaries
(an employee can't see or edit another employee's post — 404, not leaked),
staff-only approve/reject, unauthenticated-write rejection, and — found and
fixed during a security review of this code — that editing a
pending/published post sends it back to `draft` rather than silently
updating already-approved content in place. 95% statement coverage on
`apps/` at last run.

## API surface

- `GET /api/blog/` / `GET /api/blog/<slug>/` — public, published posts only.
- `GET /api/blog/categories/` — public.
- `POST/GET/PATCH/DELETE /api/portal/blog/` — authenticated, scoped to the
  caller's own posts (staff see everyone's).
- `POST /api/portal/blog/<slug>/submit/` — draft → pending.
- `POST /api/portal/blog/<slug>/approve/` / `.../reject/` — staff only.
- `GET /api/portal/blog/pending/` — staff only.
- `POST /api/auth/token/` / `.../refresh/` / `.../verify/` — JWT, throttled
  at `THROTTLE_LOGIN` (default 10/min) on the obtain endpoint.
- `GET /api/auth/me/` — who's logged in.

## Not done yet

Not deployed anywhere. For production: a real `DATABASE_URL` (Postgres —
Supabase is what this config already expects), cloud storage for
`cover_image` uploads (local disk works for dev only), a real `SECRET_KEY`
(the app refuses to start with `DEBUG=False` and the default dev key — see
`config/settings.py`), and `CORS_ALLOWED_ORIGINS`/`CSRF_TRUSTED_ORIGINS` set
to the real frontend + marketing-site domains.
