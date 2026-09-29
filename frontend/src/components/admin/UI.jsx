import { Link } from 'react-router-dom'

export const inputClass =
  'w-full rounded-xl border border-line-strong bg-white px-3 py-2 text-sm text-ink'
export const buttonClass =
  'inline-flex items-center justify-center rounded-full border border-line-strong bg-white px-4 py-2 text-sm font-semibold text-ink hover:border-orange-400 disabled:opacity-50 disabled:cursor-wait'
export const primaryClass = `${buttonClass} !border-orange-500 !bg-orange-500 !text-white hover:!bg-orange-600`
export function ErrorMessage({ error }) {
  return error ? (
    <p
      role="alert"
      className="my-4 rounded-xl bg-red-50 p-3 text-sm text-red-700"
    >
      {error}
    </p>
  ) : null
}
export function errorText(error) {
  const data = error.response?.data
  return typeof data === 'string'
    ? 'The request failed. Please try again.'
    : data
      ? Object.values(data).flat().join(' ')
      : 'Could not connect. Please try again.'
}
export function Panel({ children, className = '' }) {
  return (
    <section
      className={`rounded-bento border border-line bg-white p-5 sm:p-6 ${className}`}
    >
      {children}
    </section>
  )
}
export function Badge({ status }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-1 text-xs font-semibold ${status === 'published' ? 'bg-green-50 text-green-800' : status === 'pending' ? 'bg-amber-300/30 text-amber-700' : 'bg-sand text-slate'}`}
    >
      {status?.replaceAll('_', ' ')}
    </span>
  )
}
export function Pagination({ data, page, setPage }) {
  return (
    data && (
      <div className="mt-5 flex items-center justify-between gap-3 text-sm">
        <span>
          {data.count} results · Page {page}
        </span>
        <div className="flex gap-2">
          <button
            className={buttonClass}
            disabled={!data.previous}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </button>
          <button
            className={buttonClass}
            disabled={!data.next}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </div>
      </div>
    )
  )
}
export function PostRows({ posts }) {
  return posts?.length ? (
    <div className="divide-y divide-line">
      {posts.map((p) => (
        <div
          key={p.id}
          className="flex flex-wrap items-center justify-between gap-3 py-4"
        >
          <div className="min-w-0">
            <Link
              className="font-semibold text-ink hover:text-orange-600"
              to={`/posts/${p.slug}/review`}
            >
              {p.title}
            </Link>
            <p className="text-sm text-mute">
              {p.author} · {p.category || 'Uncategorised'}
              {p.reviewer_name ? ` · Reviewer: ${p.reviewer_name}` : ''}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {p.is_live && p.status !== 'published' && (
              <span className="text-xs text-green-700">
                Previous version live
              </span>
            )}
            <Badge status={p.status} />
          </div>
        </div>
      ))}
    </div>
  ) : (
    <p className="py-6 text-sm text-slate">No posts match this view.</p>
  )
}
export function DateText({ value }) {
  return value ? new Date(value).toLocaleString() : '—'
}
