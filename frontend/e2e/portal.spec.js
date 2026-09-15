// Full write -> submit -> approve -> public flow, against a running backend
// seeded with `python manage.py create_test_accounts` (see backend/README.md).
//
// The login page only shows "Sign in with Google" now, and nobody drives a
// real Google OAuth popup in CI. So these tests authenticate directly
// against the (still-alive, unadvertised) password endpoint and inject the
// tokens into localStorage — that's a login-page-UI-independent way to get
// into an authenticated state, which is all this spec actually needs; the
// Google flow itself is covered by the backend's mocked-verifier tests.
import { test, expect } from '@playwright/test'

const EMPLOYEE = { username: 'alice.employee', password: 'EmployeePass123!' }
const ADMIN = { username: 'admin', password: 'AdminPass123!' }
const API_BASE = process.env.E2E_API_URL || 'http://localhost:8000/api'
const BLOG_API = process.env.E2E_BLOG_API_URL || `${API_BASE}/blog/`

async function login(page, { username, password }) {
  const res = await fetch(`${API_BASE}/auth/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  const { access, refresh } = await res.json()
  await page.goto('/login') // any same-origin page, just to get a document to write localStorage on
  await page.evaluate(
    ([a, r]) => {
      localStorage.setItem('burntstack-access', a)
      localStorage.setItem('burntstack-refresh', r)
    },
    [access, refresh],
  )
  await page.goto('/')
  await page.waitForURL('**/')
}

async function logout(page) {
  await page.click('button[aria-label="Log out"]')
  await page.waitForURL('**/login')
}

test.describe('employee blog portal', () => {
  test('redirects unauthenticated visitors to login, which offers Google sign-in', async ({ page }) => {
    await page.goto('/')
    await page.waitForURL('**/login')
    await expect(page.locator('h1')).toContainText('Employee Portal')
    await expect(page.getByText('@burntstack.com')).toBeVisible()
  })

  test('employee writes and submits a post, admin approves it, it goes public', async ({ page }) => {
    const title = `E2E Post ${Date.now()}`

    await login(page, EMPLOYEE)
    await page.getByRole('link', { name: 'New Post' }).last().click()
    await page.waitForURL('**/posts/new')

    await page.fill('#title', title)
    await page.fill('#excerpt', 'An excerpt written by the Playwright E2E spec.')
    await page.fill('#content', 'Full body content for the automated end-to-end test. '.repeat(10))
    await page.fill('#tags', 'e2e, playwright')
    await page.click('button:has-text("Save Draft")')
    await page.waitForURL('**/')

    await expect(page.getByText(title)).toBeVisible()
    await page.locator('button:has-text("Submit")').first().click()
    await expect(page.getByText('pending').first()).toBeVisible()

    // Not public yet.
    const beforeApproval = await fetch(BLOG_API).then((r) => r.json())
    expect(beforeApproval.results.some((p) => p.title === title)).toBe(false)

    await logout(page)
    await login(page, ADMIN)
    await page.getByRole('link', { name: 'Review' }).click()
    await page.waitForURL('**/review')
    await expect(page.getByText(title)).toBeVisible()
    await page.locator('button:has-text("Approve")').first().click()
    await expect(page.getByText('Nothing waiting for review').or(page.getByText(title))).toBeVisible()

    // Now public.
    await expect
      .poll(async () => {
        const res = await fetch(BLOG_API).then((r) => r.json())
        return res.results.some((p) => p.title === title)
      })
      .toBe(true)
  })
})
