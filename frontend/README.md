# Employee Portal — frontend

React + Vite. The whole app is the portal (no `/portal/*` prefix — that only
existed when this lived inside the marketing site). Reuses the marketing
site's design tokens (`src/index.css`) so it still looks like a BurntStack
product, but otherwise has no dependency on that codebase: no gsap/lenis,
no `react-helmet-async` — the whole app is internal and noindexed via a
single static `<meta name="robots">` in `index.html` rather than per-page
SEO plumbing.

The post editor (`src/components/editor/`) is a real rich text editor
(TipTap), not a plain textarea — bold/italic/underline/strike, headings,
lists, blockquote, code blocks, links, and inline images via the toolbar
button, drag-drop, or paste (each uploads to the backend and embeds a URL,
never inlines base64). `content` is stored as sanitized HTML. `framer-motion`
is used deliberately but sparingly: button press/hover feedback and the
editor's own entrance/upload-indicator animations, all skipped under
`prefers-reduced-motion`.

## Setup

```bash
npm install
cp .env.example .env   # point VITE_API_URL at the backend, set VITE_GOOGLE_CLIENT_ID
npm run dev
```

Login is "Sign in with Google" only — `VITE_GOOGLE_CLIENT_ID` must be the
same Client ID configured on the backend (see `backend/README.md`), with
this app's dev/prod URL added under the credential's "Authorized
JavaScript origins" in Google Cloud Console. With no Client ID set, the
login page shows a clear "not configured" message instead of a broken
button.

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
Since nobody drives a real Google OAuth popup in CI, it authenticates via
the backend's password endpoint directly and injects the tokens into
localStorage rather than clicking through the login page — the Google
flow itself is covered by the backend's own mocked-verifier tests.
