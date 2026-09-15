# Employee Portal — frontend

React + Vite. The whole app is the portal (no `/portal/*` prefix — that only
existed when this lived inside the marketing site). Reuses the marketing
site's design tokens (`src/index.css`) so it still looks like a BurntStack
product, but otherwise has no dependency on that codebase: no
framer-motion/gsap/lenis, no `react-helmet-async` — the whole app is
internal and noindexed via a single static `<meta name="robots">` in
`index.html` rather than per-page SEO plumbing.

## Setup

```bash
npm install
cp .env.example .env   # point VITE_API_URL at the backend
npm run dev
```

## Routes

`/login`, `/` (dashboard — the logged-in employee's own posts), `/posts/new`,
`/posts/:slug/edit`, `/review` (admin only).

## Tests

```bash
npm run test        # vitest — unit test for the reading-time estimator
npm run test:e2e    # playwright — needs the backend running with
                     # `python manage.py create_test_accounts` seeded, and
                     # the frontend dev server up at localhost:5173
```

The E2E spec (`e2e/portal.spec.js`) drives the full loop: unauthenticated
redirect → employee writes + submits a post → admin approves it on the
review screen → the post shows up on the public `GET /api/blog/` feed.
