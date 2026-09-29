import { useCallback, useEffect, useState } from 'react'
import { FiCheck, FiX } from 'react-icons/fi'
import PortalShell from '@/components/PortalShell.jsx'
import api from '@/lib/axios.js'

export default function Review() {
  const [posts, setPosts] = useState(null)
  const [error, setError] = useState('')
  const [busySlug, setBusySlug] = useState('')

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/portal/blog/pending/')
      setPosts(data.results ?? data)
    } catch {
      setError('Could not load the review queue.')
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const act = async (slug, action) => {
    setBusySlug(slug)
    try {
      await api.post(`/portal/blog/${slug}/${action}/`)
      await load()
    } finally {
      setBusySlug('')
    }
  }

  return (
    <PortalShell title="Pending Review">
      {error && <p className="text-sm text-red-500">{error}</p>}
      {posts === null && !error && <p className="text-sm text-slate">Loading…</p>}

      {posts?.length === 0 && (
        <div className="rounded-bento border border-dashed border-line-strong bg-white p-10 text-center text-sm text-slate">
          Nothing waiting for review right now.
        </div>
      )}

      {posts?.length > 0 && (
        <div className="flex flex-col gap-4">
          {posts.map((post) => (
            <article key={post.id} className="rounded-bento border border-line bg-white p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-orange-600">
                    {post.author} {post.category ? `· ${post.category}` : ''}
                  </p>
                  <h3 className="mt-1 font-display text-lg font-bold text-ink">{post.title}</h3>
                  <p className="mt-2 text-sm text-slate">{post.excerpt}</p>
                  {post.tags?.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {post.tags.map((t) => (
                        <span key={t} className="rounded-full bg-sand px-2 py-0.5 text-xs text-slate">#{t}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    onClick={() => act(post.slug, 'approve')}
                    disabled={busySlug === post.slug}
                    className="inline-flex items-center gap-1.5 rounded-full bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-orange-600 disabled:opacity-50"
                  >
                    <FiCheck className="h-4 w-4" /> Approve
                  </button>
                  <button
                    onClick={() => act(post.slug, 'reject')}
                    disabled={busySlug === post.slug}
                    className="inline-flex items-center gap-1.5 rounded-full border border-line-strong px-4 py-2 text-sm font-semibold text-slate transition-colors hover:border-red-400/60 hover:text-red-500 disabled:opacity-50"
                  >
                    <FiX className="h-4 w-4" /> Reject
                  </button>
                </div>
              </div>
              <details className="mt-4">
                <summary className="cursor-pointer text-sm font-semibold text-orange-600">Read full post</summary>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate">{post.content}</p>
              </details>
            </article>
          ))}
        </div>
      )}
    </PortalShell>
  )
}
