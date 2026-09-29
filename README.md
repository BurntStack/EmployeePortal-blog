# BurntStack Employee Portal

An editorial workspace for employee-authored articles, backed by Django/DRF and React/Vite. The public website consumes approved articles from `/api/blog/`.

## Editorial workspace

- **Overview:** pending, overdue, live and scheduled counts, review ownership, recent work and editorial guidelines.
- **All posts:** search titles/content/tags; filter by author, category, reviewer, status and creation dates; paginated results and sorting.
- **Review:** sandboxed desktop/mobile publishing preview, comments, approve, request changes or reject with mandatory feedback. Decisions verify the revision opened by the reviewer.
- **History:** immutable saved versions, comparison and restore to a new draft. Working edits never change or remove the current approved public version.
- **Calendar:** upcoming approved publications with local timezone display, cancellation and automatic publication when due.
- **People:** contributor, reviewer and administrator roles; disable/re-enable users; revoke suspended users' refresh tokens and reject their Google sign-ins.
- **Activity:** searchable read-only audit trail for editorial decisions, edits, access and settings changes.
- **Notifications:** private in-app feedback, publication, assignment and overdue reminders with read/unread controls.
- **Organization:** category management, tags in the editor, featured articles, basic quality checks and bounded external-link checking.
- **Analytics:** 30-day article views, engaged reads, daily trends, content performance and review turnaround. Companion public-site change: `feat/blog-readership` in `BurntStack-frontend`.
- **Ownership:** assign primary and backup administrators, review target and shared editorial standards. Actual people must be selected by an authorized administrator.

## Roles

| Capability | Contributor | Reviewer | Administrator |
| --- | --- | --- | --- |
| Write, submit, comment, compare, restore | Own posts | All posts | All posts |
| Approve, return, schedule, assign, unpublish, feature | — | Yes | Yes |
| Overview and analytics | — | Yes | Yes |
| People, categories, audit and settings | — | — | Yes |

Google sign-in requires a verified account in `ALLOWED_EMAIL_DOMAIN`. `ADMIN_EMAILS` bootstraps administrator access for accounts without a managed portal role. Explicit assignments in People take precedence on subsequent logins. Existing recovery superusers remain administrators.

## Local setup

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 8000
```

In another terminal:

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Configure Google credentials, allowed origins and object storage as described in `backend/README.md`.

## Release and scheduling

1. Back up the database and run `python manage.py migrate` **before** serving the new API code. Migration 0005 creates an initial snapshot for each existing post and preserves published articles.
2. Deploy the portal backend and frontend together. Deploy the companion public-site tracker to populate readership metrics. The public article response shape remains compatible with the existing site.
3. Run `python manage.py run_editorial_jobs` every minute using the host's scheduler, **or** schedule authenticated requests to `GET /api/portal/jobs/` with `Authorization: Bearer <CRON_SECRET>`. Set a strong `CRON_SECRET` in the backend environment; an unset secret disables that endpoint. No scheduler or hosting-plan frequency is assumed by this repository.
4. Public blog requests also publish due approved revisions, and the overview refresh generates deduplicated overdue reminders. The minute job provides publication and reminders even without traffic.
5. Select primary and backup owners under **Admin workspace → Settings**. Existing posts start with no assigned reviewer.

The public feed intentionally avoids the previous five-minute application cache so approvals, corrections and unpublishing are immediately reflected by the API. Separately cached or prerendered website pages need their usual refresh/rebuild policy.

Notifications are in-app; no email service is required. The default review target is three calendar days. Reminder notifications are deduplicated per post version, recipient and day.

Readership metrics are approximate browser-session counts, not unique people. The tracker uses a random session-storage identifier, no cookies or stored IPs, and honors Global Privacy Control / Do Not Track. Engagement requires 30 visible seconds and reaching 50% of the article. Historical visits cannot be reconstructed. Public event ingestion is throttled, but is not an anti-fraud analytics system.

External-link checks inspect up to 20 URLs with HEAD requests, pin validated public IPs and revalidate redirects. Only confirmed 404/410 responses are marked broken; timeouts, blocked HEAD requests and private addresses are marked unchecked. Review unverified links manually. Category labels are preserved in approved snapshots; category renames appear on those articles when next republished.

## Validation

```bash
cd backend
.venv/bin/python manage.py test
.venv/bin/python manage.py makemigrations --check --dry-run
cd ../frontend
npm run lint
npm test
npm run build
```

Browser tests use local development accounts only:

```bash
cd backend
.venv/bin/python manage.py create_test_accounts
# Start the API and frontend first, then:
cd ../frontend
npm run test:e2e
```

Never create the documented test accounts in production. Configure `E2E_API_URL` and `E2E_BASE_URL` when testing on alternate local ports.
