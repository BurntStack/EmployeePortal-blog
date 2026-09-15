// Full write -> submit -> approve -> public flow, against a running backend
// seeded with `python manage.py create_test_accounts` (see backend/README.md).
import { test, expect } from '@playwright/test'

const EMPLOYEE = { username: 'alice.employee', password: 'EmployeePass123!' }
const ADMIN = { username: 'admin', password: 'AdminPass123!' }
const BLOG_API = process.env.E2E_BLOG_API_URL || 'http://localhost:8000/api/blog/'

async function login(page, { username, password }) {
  await page.goto('/login')
  await page.fill('#username', username)
  await page.fill('#password', password)
  await page.click('button[type="submit"]')
  await page.waitForURL('**/')
}

async function logout(page) {
  await page.click('button[aria-label="Log out"]')
  await page.waitForURL('**/login')
}

test.describe('employee blog portal', () => {
  test('redirects unauthenticated visitors to login', async ({ page }) => {
    await page.goto('/')
    await page.waitForURL('**/login')
    await expect(page.locator('h1')).toContainText('Employee Portal')
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
