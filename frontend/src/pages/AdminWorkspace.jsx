import { useEffect, useState } from 'react'
import { Link, NavLink, useParams } from 'react-router-dom'
import PortalShell from '@/components/PortalShell.jsx'
import { useAuth } from '@/context/AuthContext.jsx'
import api from '@/lib/axios.js'
import {
  Badge,
  DateText,
  ErrorMessage,
  Panel,
  Pagination,
  PostRows,
  buttonClass,
  primaryClass,
  inputClass,
  errorText,
} from '@/components/admin/UI.jsx'

const states = [
  'draft',
  'pending',
  'changes_requested',
  'rejected',
  'scheduled',
  'published',
  'archived',
]
export default function AdminWorkspace() {
  const { section = 'overview' } = useParams()
  const { user } = useAuth()
  const admin = user?.role === 'admin' || user?.is_staff
  const tabs = [
    'overview',
    'posts',
    'calendar',
    'analytics',
    ...(admin ? ['people', 'categories', 'activity', 'settings'] : []),
  ]
  return (
    <PortalShell title="Editorial workspace">
      <nav
        aria-label="Editorial workspace"
        className="mb-6 flex flex-wrap gap-2"
      >
        {tabs.map((tab) => (
          <NavLink
            key={tab}
            to={`/admin/${tab}`}
            className={({ isActive }) =>
              `${buttonClass} capitalize ${isActive ? '!bg-ink !text-white' : ''}`
            }
          >
            {tab}
          </NavLink>
        ))}
      </nav>
      {!tabs.includes(section) ? (
        <Panel>This page is unavailable.</Panel>
      ) : section === 'overview' ? (
        <Overview />
      ) : section === 'posts' ? (
        <Posts />
      ) : section === 'calendar' ? (
        <Calendar />
      ) : section === 'analytics' ? (
        <Analytics />
      ) : section === 'people' ? (
        <People />
      ) : section === 'categories' ? (
        <Categories />
      ) : section === 'activity' ? (
        <Activity />
      ) : (
        <Settings />
      )}
    </PortalShell>
  )
}

function useLoad(url, params) {
  const [data, setData] = useState(null),
    [error, setError] = useState(''),
    [loading, setLoading] = useState(true),
    [revision, setRevision] = useState(0)
  const key = JSON.stringify(params || {})
  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    api
      .get(url, { params: JSON.parse(key) })
      .then((r) => {
        if (active) setData(r.data)
      })
      .catch((e) => {
        if (active) setError(errorText(e))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [url, key, revision])
  return { data, error, loading, reload: () => setRevision((n) => n + 1) }
}
function LoadState({ state }) {
  return (
    <>
      <ErrorMessage error={state.error} />
      {state.loading && (
        <p role="status" className="mb-4 text-sm">
          Loading…
        </p>
      )}
    </>
  )
}
function Stat({ label, value }) {
  return (
    <Panel>
      <p className="text-sm text-slate">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-ink">{value ?? '—'}</p>
    </Panel>
  )
}
function Overview() {
  const state = useLoad('/portal/admin/overview/'),
    d = state.data
  return (
    <>
      <LoadState state={state} />
      {d && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Waiting for review" value={d.counts.pending || 0} />
            <Stat label="Overdue reviews" value={d.overdue} />
            <Stat label="Live articles" value={d.live} />
            <Stat label="Scheduled" value={d.counts.scheduled || 0} />
          </div>
          <div className="my-6 flex flex-wrap gap-3">
            <Link to="/review" className={primaryClass}>
              Open review queue
            </Link>
            <span className="self-center text-sm">
              {d.my_reviews} assigned to you · {d.unassigned} unassigned ·
              Review target: {d.settings.review_days} days
            </span>
          </div>
          <Panel>
            <h2 className="text-lg font-semibold">Recent work</h2>
            <PostRows posts={d.recent} />
          </Panel>
          <Panel className="mt-5">
            <h2 className="text-lg font-semibold">Editorial standards</h2>
            <p className="mt-3 whitespace-pre-wrap text-sm">
              {d.settings.guidelines}
            </p>
            <p className="mt-4 text-sm">
              Primary:{' '}
              {d.reviewers.find((u) => u.id === d.settings.primary_admin)
                ?.name || 'Not assigned'}{' '}
              · Backup:{' '}
              {d.reviewers.find((u) => u.id === d.settings.backup_admin)
                ?.name || 'Not assigned'}
            </p>
          </Panel>
        </>
      )}
    </>
  )
}
export function Posts({ pending = false }) {
  const [page, setPage] = useState(1),
    [filters, setFilters] = useState({
      status: pending ? 'pending' : '',
      search: '',
      author: '',
      reviewer: '',
      category__slug: '',
      ordering: '-updated_at',
      created_after: '',
      created_before: '',
    })
  const state = useLoad('/portal/blog/', {
    ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
    page,
  })
  const categories = useLoad('/blog/categories/'),
    overview = useLoad('/portal/admin/overview/')
  const change = (field, value) => {
    setPage(1)
    setFilters((f) => ({ ...f, [field]: value }))
  }
  return (
    <>
      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <input
          aria-label="Search posts"
          className={inputClass}
          placeholder="Search titles, content or tags"
          value={filters.search}
          onChange={(e) => change('search', e.target.value)}
        />
        {!pending && (
          <select
            aria-label="Post status"
            className={inputClass}
            value={filters.status}
            onChange={(e) => change('status', e.target.value)}
          >
            <option value="">All statuses</option>
            {states.map((s) => (
              <option key={s} value={s}>
                {s.replaceAll('_', ' ')}
              </option>
            ))}
          </select>
        )}
        <select
          aria-label="Category filter"
          className={inputClass}
          value={filters.category__slug}
          onChange={(e) => change('category__slug', e.target.value)}
        >
          <option value="">All categories</option>
          {categories.data?.map((c) => (
            <option key={c.id} value={c.slug}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Author filter"
          className={inputClass}
          value={filters.author}
          onChange={(e) => change('author', e.target.value)}
        >
          <option value="">All authors</option>
          {overview.data?.authors.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Reviewer filter"
          className={inputClass}
          value={filters.reviewer}
          onChange={(e) => change('reviewer', e.target.value)}
        >
          <option value="">All reviewers</option>
          {overview.data?.reviewers.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Sort posts"
          className={inputClass}
          value={filters.ordering}
          onChange={(e) => change('ordering', e.target.value)}
        >
          <option value="-updated_at">Recently updated</option>
          <option value="submitted_at">Oldest submission first</option>
          <option value="-created_at">Newest created</option>
          <option value="created_at">Oldest created</option>
        </select>
        <label className="text-xs">
          Created from
          <input
            type="date"
            aria-label="Created from"
            className={inputClass}
            value={filters.created_after}
            onChange={(e) => change('created_after', e.target.value)}
          />
        </label>
        <label className="text-xs">
          Created through
          <input
            type="date"
            aria-label="Created through"
            className={inputClass}
            value={filters.created_before}
            onChange={(e) => change('created_before', e.target.value)}
          />
        </label>
      </div>
      <LoadState state={state} />
      <Panel>
        <PostRows posts={state.data?.results} />
        <Pagination data={state.data} page={page} setPage={setPage} />
      </Panel>
    </>
  )
}
function Calendar() {
  const [page, setPage] = useState(1),
    state = useLoad('/portal/blog/', {
      status: 'scheduled',
      ordering: 'scheduled_at',
      page,
    })
  return (
    <>
      <p className="mb-5 text-sm">
        Upcoming approved publications. Times are shown in your local timezone:{' '}
        {Intl.DateTimeFormat().resolvedOptions().timeZone}.
      </p>
      <LoadState state={state} />
      <Panel>
        {state.data?.results.length === 0 && (
          <p>
            No scheduled publications. Schedule a post from its review page.
          </p>
        )}
        {state.data?.results.map((p) => (
          <div
            key={p.id}
            className="flex flex-wrap items-center gap-5 border-b border-line py-4"
          >
            <div className="min-w-44 rounded-xl bg-orange-50 p-3 text-sm font-semibold text-orange-800">
              <DateText value={p.scheduled_at} />
            </div>
            <div>
              <Link
                to={`/posts/${p.slug}/review`}
                className="font-semibold text-ink"
              >
                {p.title}
              </Link>
              <p className="text-sm">
                {p.author} · {p.category || 'Uncategorised'}
              </p>
            </div>
            <Badge status={p.status} />
          </div>
        ))}
        <Pagination data={state.data} page={page} setPage={setPage} />
      </Panel>
    </>
  )
}
function Analytics() {
  const state = useLoad('/portal/admin/analytics/'),
    d = state.data
  return (
    <>
      <LoadState state={state} />
      {d && (
        <>
          <p className="mb-4 text-sm">Last 30 days · {d.definition}</p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Article views" value={d.views} />
            <Stat label="Engaged reads" value={d.engaged} />
            <Stat label="Engagement rate" value={`${d.engagement_rate}%`} />
            <Stat
              label="Average review time"
              value={
                d.average_review_hours === null
                  ? 'No decisions yet'
                  : `${d.average_review_hours}h`
              }
            />
          </div>
          <Panel className="mt-5">
            <h2 className="mb-4 text-lg font-semibold">Content performance</h2>
            {!d.posts.length ? (
              <p className="text-sm">
                No readership events recorded yet. Metrics appear as readers
                visit articles with tracking enabled.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr>
                      <th className="py-3">Article</th>
                      <th>Views</th>
                      <th>Engaged reads</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.posts.map((p) => (
                      <tr key={p.post__slug} className="border-t border-line">
                        <td className="py-3">
                          <Link to={`/posts/${p.post__slug}/review`}>
                            {p.post__title}
                          </Link>
                        </td>
                        <td>{p.views}</td>
                        <td>{p.engaged}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
          <Panel className="mt-5">
            <h2 className="mb-4 text-lg font-semibold">Daily readership</h2>
            {d.daily.map((row) => (
              <div
                key={row.day}
                className="mb-2 flex items-center gap-3 text-xs"
              >
                <span className="w-24">{row.day}</span>
                <div
                  className="h-4 rounded bg-orange-400"
                  style={{
                    width: `${Math.max(1, (row.views / Math.max(...d.daily.map((r) => r.views))) * 65)}%`,
                  }}
                />
                <span>{row.views} views</span>
              </div>
            ))}
            {!d.daily.length && <p className="text-sm">No data yet.</p>}
          </Panel>
        </>
      )}
    </>
  )
}
function People() {
  const [page, setPage] = useState(1),
    [search, setSearch] = useState(''),
    state = useLoad('/portal/admin/people/', { page, search })
  return (
    <>
      <p className="mb-4 text-sm">
        Contributors manage their own posts. Reviewers manage editorial work.
        Administrators also manage people, categories and settings.
      </p>
      <input
        className={`${inputClass} mb-4`}
        aria-label="Search people"
        placeholder="Search people"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value)
          setPage(1)
        }}
      />
      <LoadState state={state} />
      <Panel>
        {state.data?.results.map((u) => (
          <Person
            key={`${u.id}-${u.role}-${u.is_active}`}
            user={u}
            reload={state.reload}
          />
        ))}
        <Pagination data={state.data} page={page} setPage={setPage} />
      </Panel>
    </>
  )
}
function Person({ user, reload }) {
  const [role, setRole] = useState(user.role),
    [active, setActive] = useState(user.is_active),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false)
  const save = async () => {
    setBusy(true)
    setError('')
    try {
      await api.patch(`/portal/admin/people/${user.id}/`, {
        role,
        is_active: active,
      })
      reload()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="border-b border-line py-4">
      <div className="flex flex-wrap items-center gap-4">
        <div className="min-w-48 flex-1">
          <p className="font-semibold text-ink">{user.name}</p>
          <p className="text-sm">
            {user.email} · ID {user.id}
          </p>
        </div>
        <select
          aria-label={`Role for ${user.name}`}
          className={`${inputClass} !w-auto`}
          value={role}
          onChange={(e) => setRole(e.target.value)}
        >
          {['contributor', 'reviewer', 'admin'].map((r) => (
            <option key={r}>{r}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={active}
            onChange={(e) => setActive(e.target.checked)}
          />
          Active
        </label>
        <button
          className={buttonClass}
          disabled={busy || (role === user.role && active === user.is_active)}
          onClick={save}
        >
          Save access
        </button>
      </div>
      <ErrorMessage error={error} />
    </div>
  )
}
function Categories() {
  const [page, setPage] = useState(1),
    state = useLoad('/portal/admin/categories/', { page }),
    [name, setName] = useState(''),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false)
  const create = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.post('/portal/admin/categories/', { name })
      setName('')
      setPage(1)
      state.reload()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <form onSubmit={create} className="mb-5 flex gap-3">
        <input
          required
          maxLength={80}
          className={inputClass}
          aria-label="New category"
          placeholder="New category name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button disabled={busy} className={`${primaryClass} shrink-0`}>
          Add category
        </button>
      </form>
      <ErrorMessage error={error} />
      <LoadState state={state} />
      <Panel>
        {state.data?.results.map((c) => (
          <CategoryRow key={c.id} category={c} reload={state.reload} />
        ))}
        <Pagination data={state.data} page={page} setPage={setPage} />
      </Panel>
    </>
  )
}
function CategoryRow({ category, reload }) {
  const [name, setName] = useState(category.name),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false)
  const mutate = async (remove) => {
    if (
      remove &&
      !window.confirm(`Delete the unused category “${category.name}”?`)
    )
      return
    setBusy(true)
    setError('')
    try {
      if (remove) await api.delete(`/portal/admin/categories/${category.id}/`)
      else await api.patch(`/portal/admin/categories/${category.id}/`, { name })
      reload()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="border-b border-line py-4">
      <div className="flex gap-2">
        <input
          maxLength={80}
          aria-label={`Category ${category.name}`}
          className={inputClass}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button
          className={buttonClass}
          disabled={busy || name === category.name}
          onClick={() => mutate(false)}
        >
          Save
        </button>
        <button
          className={buttonClass}
          disabled={busy}
          onClick={() => mutate(true)}
        >
          Delete
        </button>
      </div>
      <ErrorMessage error={error} />
    </div>
  )
}
function Activity() {
  const [page, setPage] = useState(1),
    [search, setSearch] = useState(''),
    state = useLoad('/portal/admin/activity/', { page, search })
  return (
    <>
      <input
        aria-label="Search activity"
        className={`${inputClass} mb-4`}
        placeholder="Search people, actions or articles"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value)
          setPage(1)
        }}
      />
      <LoadState state={state} />
      <Panel>
        {state.data?.results.map((a) => (
          <div key={a.id} className="border-b border-line py-4">
            <p className="text-sm">
              <strong>{a.actor_name}</strong> · {a.action.replaceAll('_', ' ')}{' '}
              · {a.target}
            </p>
            <p className="mt-1 text-xs text-mute">
              <DateText value={a.created_at} />
            </p>
            {Object.keys(a.details).length > 0 && (
              <details className="mt-2 text-xs">
                <summary>Details</summary>
                <pre className="mt-2 overflow-auto rounded bg-sand p-3">
                  {JSON.stringify(a.details, null, 2)}
                </pre>
              </details>
            )}
          </div>
        ))}
        {state.data?.count === 0 && <p>No activity yet.</p>}
        <Pagination data={state.data} page={page} setPage={setPage} />
      </Panel>
    </>
  )
}
function Settings() {
  const state = useLoad('/portal/admin/overview/')
  return (
    <>
      <LoadState state={state} />
      {state.data && (
        <SettingsForm
          initial={state.data.settings}
          people={state.data.reviewers.filter((u) => u.role === 'admin')}
        />
      )}
    </>
  )
}
function SettingsForm({ initial, people }) {
  const [form, setForm] = useState(initial),
    [error, setError] = useState(''),
    [saved, setSaved] = useState(false),
    [busy, setBusy] = useState(false)
  const change = (field, value) => {
    setSaved(false)
    setForm((f) => ({ ...f, [field]: value }))
  }
  const save = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.patch('/portal/admin/settings/', form)
      setSaved(true)
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Panel>
      <form onSubmit={save} className="flex max-w-2xl flex-col gap-5">
        {['primary_admin', 'backup_admin'].map((field) => (
          <label key={field} className="text-sm font-semibold">
            {field === 'primary_admin'
              ? 'Primary editorial admin'
              : 'Backup editorial admin'}
            <select
              className={`${inputClass} mt-2`}
              value={form[field] || ''}
              onChange={(e) =>
                change(field, e.target.value ? Number(e.target.value) : null)
              }
            >
              <option value="">Unassigned</option>
              {people.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </select>
          </label>
        ))}
        <label className="text-sm font-semibold">
          Review target (days)
          <input
            type="number"
            min="1"
            max="30"
            className={`${inputClass} mt-2`}
            value={form.review_days}
            onChange={(e) => change('review_days', Number(e.target.value))}
          />
        </label>
        <label className="text-sm font-semibold">
          Editorial guidelines
          <textarea
            rows={8}
            required
            className={`${inputClass} mt-2`}
            value={form.guidelines}
            onChange={(e) => change('guidelines', e.target.value)}
          />
        </label>
        <ErrorMessage error={error} />
        <button disabled={busy} className={`${primaryClass} self-start`}>
          Save settings
        </button>
        {saved && (
          <p role="status" className="text-sm text-green-800">
            Settings saved.
          </p>
        )}
      </form>
    </Panel>
  )
}
