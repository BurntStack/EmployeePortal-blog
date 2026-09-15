import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FiEdit2, FiTrash2, FiSend, FiPlus } from 'react-icons/fi'
import Button from '@/components/Button.jsx'
import PortalShell from '@/components/PortalShell.jsx'
import { useAuth } from '@/context/AuthContext.jsx'
import { cn } from '@/utils/cn.js'
import api from '@/lib/axios.js'

const STATUS_STYLE = {
  draft: 'bg-sand text-slate',
  pending: 'bg-amber-300/30 text-amber-700',
  published: 'bg-orange-500/10 text-orange-600',
}

export default function Dashboard() {
  const { user } = useAuth()
  const [posts, setPosts] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    if (!user) return
    try {
      const { data } = await api.get('/portal/blog/', { params: { author: user.id, ordering: '-updated_at' } })
      setPosts(data.results ?? data)
    } catch {
      setError('Could not load your posts.')
    }
  }, [user])

  useEffect(() => {
    load()
  }, [load])

  const submitForReview = async (slug) => {
    await api.post(`/portal/blog/${slug}/submit/`)
    load()
  }

  const remove = async (slug) => {
    if (!window.confirm('Delete this post? This can’t be undone.')) return
    await api.delete(`/portal/blog/${slug}/`)
    load()
  }

  return (
    <PortalShell title="My Posts">
      <div className="mb-6 flex justify-end">
        <Button to="/posts/new" size="md">
          <FiPlus className="h-4 w-4" /> New Post
        </Button>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      {posts === null && !error && <p className="text-sm text-slate">Loading…</p>}

      {posts?.length === 0 && (
        <div className="rounded-bento border border-dashed border-line-strong bg-white p-10 text-center text-sm text-slate">
          You haven&apos;t written anything yet. Start your first post.
        </div>
      )}

      {posts?.length > 0 && (
        <div className="flex flex-col gap-3">
          {posts.map((post) => (
            <div
              key={post.id}
              className="flex flex-col gap-3 rounded-bento-sm border border-line bg-white p-5 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-display text-base font-semibold text-ink">{post.title}</h3>
                  <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize', STATUS_STYLE[post.status])}>
                    {post.status}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate">{post.excerpt}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {post.status === 'draft' && (
                  <button
                    onClick={() => submitForReview(post.slug)}
                    className="inline-flex items-center gap-1.5 rounded-full border border-orange-500/30 px-3 py-1.5 text-xs font-semibold text-orange-600 hover:bg-orange-50"
                  >
                    <FiSend className="h-3.5 w-3.5" /> Submit
                  </button>
                )}
                <Link
                  to={`/posts/${post.slug}/edit`}
                  aria-label="Edit"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-line-strong text-slate hover:border-orange-400/60 hover:text-orange-600"
                >
                  <FiEdit2 className="h-3.5 w-3.5" />
                </Link>
                <button
                  onClick={() => remove(post.slug)}
                  aria-label="Delete"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-line-strong text-slate hover:border-red-400/60 hover:text-red-500"
                >
                  <FiTrash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </PortalShell>
  )
}
