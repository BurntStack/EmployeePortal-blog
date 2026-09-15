# BurntStack Employee Portal

A standalone app where employees write and manage blog posts, with an
admin-approval workflow before anything reaches the public
`burntstack.com/blog` feed.

Extracted from the main `BurntStack-frontend`/`BurntStack-backend` repos,
where this started as a `/portal/*` section. It only ever depended on a
handful of files from those repos (see `frontend/README.md` and
`backend/README.md`) — not preserved with `git subtree`/`filter-repo`, so
history here starts fresh.

- `backend/` — Django + DRF. Owns `Post`/`Category` and JWT auth.
- `frontend/` — React + Vite. Login, dashboard, post editor, admin review.

## Workflow

1. Anyone with a verified `@burntstack.com` Google account can sign in —
   no admin provisioning needed for *access*. `ADMIN_EMAILS` (backend env
   var) controls who gets admin rights, re-synced on every login.
2. An employee logs in, writes a post (title, excerpt, markdown content,
   category, topic tags, cover image, reading time), saves it as a draft,
   and submits it for review.
3. The admin reviews pending posts and approves or rejects them.
4. Approved posts appear on the public blog feed (`GET /api/blog/`) —
   whatever consumes that endpoint (the marketing site) shows them.
5. If an employee edits a post that's already pending or published, it's
   sent back to draft automatically — edited content always needs a fresh
   approval, it never updates what's already live in place.

## Quick start

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
# set GOOGLE_CLIENT_ID and ADMIN_EMAILS in .env — see backend/README.md
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 8000

cd ../frontend && npm install
cp .env.example .env
# set VITE_GOOGLE_CLIENT_ID (same Client ID as the backend's)
npm run dev
```

Not deployed anywhere yet — see the individual READMEs for what's needed to
actually ship this (hosting, a real Postgres database, media storage for
cover images, `CORS_ALLOWED_ORIGINS`/`VITE_API_URL` pointed at real domains).
