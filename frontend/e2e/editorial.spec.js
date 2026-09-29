import { test, expect } from '@playwright/test'
const API = process.env.E2E_API_URL || 'http://localhost:8000/api'
const accounts = {
  admin: ['admin', 'AdminPass123!'],
  author: ['alice.employee', 'EmployeePass123!'],
}
async function login(page, role) {
  const [username, password] = accounts[role]
  const res = await fetch(`${API}/auth/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  expect(res.ok).toBeTruthy()
  const tokens = await res.json()
  await page.goto('/login')
  await page.evaluate((t) => {
    localStorage.setItem('burntstack-access', t.access)
    localStorage.setItem('burntstack-refresh', t.refresh)
  }, tokens)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'My Posts' })).toBeVisible()
  return tokens.access
}
async function api(token, path, data, method = 'POST') {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    ...(data ? { body: JSON.stringify(data) } : {}),
  })
  expect(res.ok).toBeTruthy()
  return res.json()
}

test('admin reviews, requests changes, publishes, compares and restores a live article', async ({
  page,
}) => {
  const title = `Editorial browser test ${Date.now()}`
  const authorToken = await login(page, 'author')
  const post = await api(authorToken, '/portal/blog/', {
    title,
    excerpt: 'A complete browser test of editorial publishing.',
    content:
      '<h2>Engineering notes</h2><p>This article contains enough content to test the complete editorial review workflow.</p>',
    tags: ['testing'],
    reading_time: 2,
  })
  await api(authorToken, `/portal/blog/${post.slug}/submit/`)
  const adminToken = await login(page, 'admin')
  await page.goto(`/posts/${post.slug}/review`)
  await expect(
    page.frameLocator('iframe').getByRole('heading', { name: title }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Mobile preview' }).click()
  await expect(page.locator('iframe')).toHaveAttribute(
    'title',
    'Mobile article preview',
  )
  await page
    .getByLabel('Feedback', { exact: true })
    .fill('Please add a reliable source for the technical claim.')
  await page
    .getByRole('button', { name: 'Request changes', exact: true })
    .click()
  await expect(
    page.getByText('changes requested', { exact: true }),
  ).toBeVisible()
  await expect(
    page.getByText('Please add a reliable source for the technical claim.', {
      exact: true,
    }),
  ).toBeVisible()
  await page
    .getByRole('button', { name: 'Submit for review', exact: true })
    .click()
  await page
    .getByRole('button', { name: 'Approve and publish', exact: true })
    .click()
  await expect(page.getByText('An approved version is live')).toBeVisible()
  const changed = await api(
    authorToken,
    `/portal/blog/${post.slug}/`,
    { title: `${title} updated`, expected_version: post.version },
    'PATCH',
  )
  const live = await fetch(`${API}/blog/${post.slug}/`).then((r) => r.json())
  expect(live.title).toBe(title)
  await page.reload()
  await expect(
    page.getByRole('heading', { name: `${title} updated`, exact: true }),
  ).toBeVisible()
  await page
    .getByRole('button', { name: 'Compare', exact: true })
    .last()
    .click()
  page.once('dialog', (d) => d.accept())
  await page
    .getByRole('button', { name: 'Restore version 1', exact: true })
    .click()
  await expect(
    page.getByRole('heading', { name: title, exact: true }),
  ).toBeVisible()
  const restored = await api(
    adminToken,
    `/portal/blog/${post.slug}/`,
    null,
    'GET',
  )
  expect(restored.version).toBe(changed.version + 1)
  expect(restored.is_live).toBe(true)
  await page.goto('/admin/overview')
  await expect(page.getByText('Live articles', { exact: true })).toBeVisible()
  await page.goto('/admin/activity')
  await page.getByLabel('Search activity').fill(title)
  await expect(
    page.getByText(`admin · restored · ${title}`, { exact: false }),
  ).toBeVisible()
})

test('workspace screens, people, categories, notifications and mobile navigation work', async ({
  page,
}) => {
  await login(page, 'admin')
  for (const section of [
    'overview',
    'posts',
    'calendar',
    'analytics',
    'people',
    'categories',
    'activity',
    'settings',
  ]) {
    await page.goto(`/admin/${section}`)
    await expect(
      page.getByRole('heading', { name: 'Editorial workspace' }),
    ).toBeVisible()
    await expect(page.getByRole('status', { name: 'Loading…' })).toHaveCount(0)
    await expect(page.getByRole('alert')).toHaveCount(0)
  }
  await page.goto('/admin/categories')
  const category = `Browser category ${Date.now()}`
  await page.getByLabel('New category').fill(category)
  await page.getByRole('button', { name: 'Add category', exact: true }).click()
  await expect(
    page.getByLabel(`Category ${category}`, { exact: true }),
  ).toBeVisible()
  await page.goto('/notifications')
  await page
    .getByRole('button', { name: 'Mark all as read', exact: true })
    .click()
  await expect(page.getByRole('alert')).toHaveCount(0)
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(
    page.getByRole('link', { name: 'Admin workspace', exact: true }),
  ).toBeVisible()
  await page.getByRole('link', { name: 'Admin workspace', exact: true }).click()
  await expect(
    page.getByText('Waiting for review', { exact: true }),
  ).toBeVisible()
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true)
  await page.screenshot({
    path: 'frontend/test-results/admin-mobile.png',
    fullPage: true,
  })
})
