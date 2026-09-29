import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import PortalShell from '@/components/PortalShell.jsx'
import { useAuth } from '@/context/AuthContext.jsx'
import api from '@/lib/axios.js'
import {
  Badge,
  DateText,
  ErrorMessage,
  Panel,
  Pagination,
  buttonClass,
  primaryClass,
  inputClass,
  errorText,
} from '@/components/admin/UI.jsx'

export default function PostReview() {
  const { slug } = useParams(),
    { user } = useAuth(),
    canReview = user?.can_review || user?.is_staff
  const [post, setPost] = useState(null),
    [comments, setComments] = useState([]),
    [history, setHistory] = useState(null),
    [page, setPage] = useState(1),
    [quality, setQuality] = useState(null),
    [links, setLinks] = useState(null),
    [reviewers, setReviewers] = useState([])
  const [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [body, setBody] = useState(''),
    [when, setWhen] = useState(''),
    [reviewer, setReviewer] = useState(''),
    [mobile, setMobile] = useState(false),
    [selected, setSelected] = useState(null),
    [message, setMessage] = useState('')
  const load = useCallback(async () => {
    const [p, c, r, q] = await Promise.all([
      api.get(`/portal/blog/${slug}/`),
      api.get(`/portal/blog/${slug}/comments/`),
      api.get(`/portal/blog/${slug}/revisions/`, { params: { page } }),
      api.get(`/portal/blog/${slug}/quality/`),
    ])
    setPost(p.data)
    setReviewer(p.data.reviewer || '')
    setComments(c.data)
    setHistory(r.data)
    setQuality(q.data)
  }, [slug, page])
  useEffect(() => {
    load().catch((e) => setError(errorText(e)))
  }, [load])
  useEffect(() => {
    if (canReview)
      api
        .get('/portal/admin/overview/')
        .then((r) => setReviewers(r.data.reviewers))
        .catch((e) => setError(errorText(e)))
  }, [canReview])
  const act = async (action, payload = {}) => {
    setError('')
    setMessage('')
    setBusy(true)
    try {
      await api.post(`/portal/blog/${slug}/${action}/`, {
        expected_version: post.version,
        ...payload,
      })
      setBody('')
      setWhen('')
      setSelected(null)
      setLinks(null)
      await load()
      setMessage('Changes saved.')
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  const checkLinks = async () => {
    setBusy(true)
    setError('')
    try {
      const r = await api.post(
        `/portal/blog/${slug}/check-links/`,
        {},
        { timeout: 60000 },
      )
      setLinks(r.data)
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  const approve = () => {
    if (when && Number.isNaN(new Date(when).getTime())) return
    act('approve', {
      body,
      scheduled_at: when ? new Date(when).toISOString() : null,
    })
  }
  return (
    <PortalShell title={post?.title || 'Review article'}>
      <ErrorMessage error={error} />
      {message && (
        <p role="status" className="mb-4 text-sm text-green-800">
          {message}
        </p>
      )}
      {!post ? (
        <p>Loading article…</p>
      ) : (
        <>
          <div className="mb-6 flex flex-wrap items-center gap-3">
            <Badge status={post.status} />
            <span className="text-sm">
              {post.author} · Version {post.version}
            </span>
            {post.is_live && (
              <span className="text-sm text-green-800">
                An approved version is live
              </span>
            )}
            <Link className={buttonClass} to={`/posts/${slug}/edit`}>
              Edit draft
            </Link>
            {['draft', 'changes_requested', 'rejected'].includes(
              post.status,
            ) && (
              <button
                className={primaryClass}
                disabled={busy}
                onClick={() => act('submit')}
              >
                Submit for review
              </button>
            )}
          </div>
          <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
            <div className="min-w-0">
              <Panel>
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h2 className="text-lg font-semibold">Publishing preview</h2>
                  <button
                    className={buttonClass}
                    onClick={() => setMobile((v) => !v)}
                  >
                    {mobile ? 'Desktop preview' : 'Mobile preview'}
                  </button>
                </div>
                <p className="mb-4 text-xs text-mute">
                  Previewing the current draft. Publication requires approval.
                </p>
                <ArticlePreview post={post} mobile={mobile} />
              </Panel>
              <Panel className="mt-6">
                <h2 className="mb-4 text-lg font-semibold">
                  Feedback and decisions
                </h2>
                {comments.length === 0 && (
                  <p className="text-sm">No feedback yet.</p>
                )}
                {comments.map((c) => (
                  <div key={c.id} className="mb-4 rounded-xl bg-ivory p-4">
                    <p className="text-sm font-semibold text-ink">
                      {c.author} · {c.decision.replaceAll('_', ' ')} · v
                      {c.version}
                    </p>
                    {c.body && (
                      <p className="mt-2 whitespace-pre-wrap text-sm">
                        {c.body}
                      </p>
                    )}
                    <p className="mt-2 text-xs text-mute">
                      <DateText value={c.created_at} />
                    </p>
                  </div>
                ))}
                <label
                  htmlFor="review-feedback"
                  className="text-sm font-semibold"
                >
                  Feedback
                </label>
                <textarea
                  id="review-feedback"
                  rows={4}
                  maxLength={4000}
                  className={`${inputClass} mt-2`}
                  placeholder="Explain what works and what needs to change…"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                />
                <button
                  className={`${buttonClass} mt-3`}
                  disabled={busy || !body.trim()}
                  onClick={() => act('comments', { body })}
                >
                  Add comment
                </button>
              </Panel>
              <Panel className="mt-6">
                <h2 className="mb-4 text-lg font-semibold">Revision history</h2>
                <p className="mb-4 text-sm">
                  Compare a saved version with the current draft, or restore it
                  for a fresh review.
                </p>
                {history?.results.map((r) => (
                  <div
                    className="flex flex-wrap items-center justify-between gap-3 border-b border-line py-3"
                    key={r.id}
                  >
                    <div className="text-sm">
                      <strong>Version {r.number}</strong>
                      {r.is_live && (
                        <span className="ml-2 text-green-700">Live</span>
                      )}
                      <p className="text-xs text-mute">
                        {r.author} · <DateText value={r.created_at} />
                      </p>
                    </div>
                    <button
                      className={buttonClass}
                      onClick={() => setSelected(r)}
                    >
                      Compare
                    </button>
                  </div>
                ))}
                <Pagination data={history} page={page} setPage={setPage} />
                {selected && (
                  <div className="mt-5">
                    <h3 className="mb-3 font-semibold">
                      Version {selected.number} compared with current version{' '}
                      {post.version}
                    </h3>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <Comparison
                        label={`Version ${selected.number}`}
                        data={selected.snapshot}
                        other={post}
                      />
                      <Comparison
                        label="Current draft"
                        data={post}
                        other={selected.snapshot}
                      />
                    </div>
                    <button
                      className={`${buttonClass} mt-3`}
                      disabled={busy || selected.number === post.version}
                      onClick={() => {
                        if (
                          window.confirm(
                            'Restore this version as a new draft? The live article stays unchanged.',
                          )
                        )
                          act('restore', { revision_id: selected.id })
                      }}
                    >
                      Restore version {selected.number}
                    </button>
                  </div>
                )}
              </Panel>
            </div>
            <aside className="flex flex-col gap-5">
              {canReview && (
                <Panel>
                  <h2 className="mb-4 text-lg font-semibold">
                    Review decision
                  </h2>
                  {post.status === 'pending' ? (
                    <>
                      <label className="text-sm">
                        Schedule publication (optional)
                        <input
                          aria-label="Publication time"
                          className={`${inputClass} mt-2`}
                          type="datetime-local"
                          value={when}
                          onChange={(e) => setWhen(e.target.value)}
                        />
                      </label>
                      <p className="mt-2 text-xs text-mute">
                        Your timezone:{' '}
                        {Intl.DateTimeFormat().resolvedOptions().timeZone}
                      </p>
                      <button
                        className={`${primaryClass} mt-4 w-full`}
                        disabled={busy}
                        onClick={approve}
                      >
                        {when ? 'Approve and schedule' : 'Approve and publish'}
                      </button>
                      <button
                        className={`${buttonClass} mt-2 w-full`}
                        disabled={busy || !body.trim()}
                        onClick={() => act('request-changes', { body })}
                      >
                        Request changes
                      </button>
                      <button
                        className={`${buttonClass} mt-2 w-full`}
                        disabled={busy || !body.trim()}
                        onClick={() => act('reject', { body })}
                      >
                        Reject with feedback
                      </button>
                      <p className="mt-3 text-xs text-mute">
                        Requesting changes or rejecting requires feedback.
                      </p>
                    </>
                  ) : (
                    <p className="text-sm">
                      {post.status === 'scheduled' ? (
                        <>
                          Scheduled for <DateText value={post.scheduled_at} />.
                        </>
                      ) : (
                        'Submit this draft before approving it.'
                      )}
                    </p>
                  )}
                  {post.status === 'scheduled' && (
                    <button
                      className={`${buttonClass} mt-3`}
                      disabled={busy}
                      onClick={() => act('cancel-schedule')}
                    >
                      Cancel schedule
                    </button>
                  )}
                </Panel>
              )}
              {canReview && (
                <Panel>
                  <h2 className="mb-4 text-lg font-semibold">
                    Ownership and visibility
                  </h2>
                  <label className="text-sm">
                    Assigned reviewer
                    <select
                      aria-label="Assigned reviewer"
                      className={`${inputClass} mt-2`}
                      value={reviewer}
                      onChange={(e) => setReviewer(e.target.value)}
                    >
                      <option value="">Unassigned</option>
                      {reviewers.map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    className={`${buttonClass} mt-3`}
                    disabled={
                      busy || String(reviewer) === String(post.reviewer || '')
                    }
                    onClick={() =>
                      act('assign', {
                        reviewer_id: reviewer ? Number(reviewer) : null,
                      })
                    }
                  >
                    Save assignment
                  </button>
                  <label className="mt-5 flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={post.is_featured}
                      disabled={busy}
                      onChange={(e) =>
                        act('feature', { is_featured: e.target.checked })
                      }
                    />
                    Featured article
                  </label>
                  {post.is_live && (
                    <button
                      className={`${buttonClass} mt-4`}
                      disabled={busy}
                      onClick={() => {
                        if (
                          window.confirm(
                            'Remove this article from the public blog? Its history will be retained.',
                          )
                        )
                          act('unpublish')
                      }}
                    >
                      Unpublish article
                    </button>
                  )}
                </Panel>
              )}
              <Panel>
                <h2 className="mb-4 text-lg font-semibold">Quality checks</h2>
                {quality?.issues.length ? (
                  <ul className="list-disc space-y-2 pl-5 text-sm">
                    {quality.issues.map((issue, i) => (
                      <li key={i}>{issue}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-green-800">
                    Basic content checks passed.
                  </p>
                )}
                {canReview && (
                  <button
                    className={`${buttonClass} mt-4`}
                    disabled={busy}
                    onClick={checkLinks}
                  >
                    Check external links
                  </button>
                )}
                {links && (
                  <div className="mt-4 space-y-3 text-xs">
                    {links.results.length === 0 && <p>No external links.</p>}
                    {links.results.map((l, i) => (
                      <p key={i} className="break-all">
                        <strong
                          className={l.state === 'broken' ? 'text-red-700' : ''}
                        >
                          {l.state}: {l.detail}
                        </strong>
                        <br />
                        {l.url}
                      </p>
                    ))}
                    {links.skipped > 0 && (
                      <p>
                        {links.skipped} links exceed the 20-link check limit;
                        review them manually.
                      </p>
                    )}
                  </div>
                )}
                <p className="mt-4 text-xs text-mute">
                  Review factual accuracy, sources, permissions and confidential
                  details before publishing.
                </p>
              </Panel>
            </aside>
          </div>
        </>
      )}
    </PortalShell>
  )
}
function Comparison({ label, data, other }) {
  return (
    <div className="min-w-0 rounded-xl border border-line p-3">
      <h4 className="mb-2 text-sm font-semibold">{label}</h4>
      {[
        'title',
        'excerpt',
        'content',
        'tags',
        'reading_time',
        'category',
        'cover_image',
      ].map((field) => (
        <div
          key={field}
          className={`mb-3 rounded p-2 text-xs ${JSON.stringify(data[field]) !== JSON.stringify(other[field]) ? 'bg-amber-300/20' : 'bg-ivory'}`}
        >
          <strong className="capitalize">{field.replaceAll('_', ' ')}</strong>
          <pre className="mt-1 max-h-72 overflow-auto whitespace-pre-wrap break-words font-sans">
            {typeof data[field] === 'object'
              ? JSON.stringify(data[field])
              : data[field]}
          </pre>
        </div>
      ))}
    </div>
  )
}
function escape(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}
function ArticlePreview({ post, mobile }) {
  // API sanitation plus a script-free sandbox isolate imported HTML from the portal.
  const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src https: http:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><style>body{margin:0;padding:28px;color:#1b1712;background:#fff;font:16px/1.75 system-ui,sans-serif;overflow-wrap:anywhere}h1{font-size:34px;line-height:1.15}h2{font-size:24px}h3{font-size:20px}img{max-width:100%;height:auto;border-radius:10px}.cover{width:100%;aspect-ratio:16/9;object-fit:cover}.tags{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0}.tag{background:#f4f1ea;padding:3px 10px;border-radius:999px;font-size:12px}.meta{color:#8b847a;font-size:13px}.excerpt{font-size:19px;color:#57514a}a{color:#c6520f}pre{overflow:auto;background:#1b1712;color:white;padding:16px;border-radius:8px}blockquote{border-left:3px solid #ea8038;padding-left:16px}table{border-collapse:collapse;display:block;overflow:auto}td,th{border:1px solid #ddd6c9;padding:8px}@media(max-width:400px){body{padding:18px}h1{font-size:28px}}</style></head><body><p class="meta">${escape(post.category)} · ${escape(post.reading_time)} min read</p><h1>${escape(post.title)}</h1><p class="excerpt">${escape(post.excerpt)}</p><p class="meta">By ${escape(post.author)}</p>${post.cover_image ? `<img class="cover" src="${escape(post.cover_image)}" alt="">` : ''}<div class="tags">${(post.tags || []).map((t) => `<span class="tag">#${escape(t)}</span>`).join('')}</div><article>${post.content}</article></body></html>`
  return (
    <iframe
      title={mobile ? 'Mobile article preview' : 'Desktop article preview'}
      sandbox=""
      referrerPolicy="no-referrer"
      srcDoc={html}
      className="mx-auto block h-[720px] max-w-full rounded-xl border border-line"
      style={{ width: mobile ? 375 : '100%' }}
    />
  )
}
