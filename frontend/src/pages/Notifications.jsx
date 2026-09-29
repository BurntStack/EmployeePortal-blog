import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PortalShell from '@/components/PortalShell.jsx'
import api from '@/lib/axios.js'
import {
  DateText,
  Panel,
  Pagination,
  ErrorMessage,
  buttonClass,
  errorText,
} from '@/components/admin/UI.jsx'

export default function Notifications() {
  const [data, setData] = useState(null),
    [page, setPage] = useState(1),
    [version, setVersion] = useState(0),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false)
  useEffect(() => {
    let active = true
    api
      .get('/portal/admin/notifications/', { params: { page } })
      .then((r) => {
        if (active) setData(r.data)
      })
      .catch((e) => {
        if (active) setError(errorText(e))
      })
    return () => {
      active = false
    }
  }, [page, version])
  const markRead = async (id) => {
    setBusy(true)
    setError('')
    try {
      await api.post(
        `/portal/admin/notifications/${id ? `${id}/read` : 'read-all'}/`,
      )
      setVersion((v) => v + 1)
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <PortalShell title="Notifications">
      <ErrorMessage error={error} />
      <button
        className={`${buttonClass} mb-5`}
        disabled={busy}
        onClick={() => markRead(null)}
      >
        Mark all as read
      </button>
      <Panel>
        {!data && !error && <p>Loading notifications…</p>}
        {data?.count === 0 && <p>You are all caught up.</p>}
        {data?.results.map((n) => (
          <div
            key={n.id}
            className={`flex flex-wrap items-center justify-between gap-3 border-b border-line p-4 ${n.read_at ? '' : 'bg-orange-50'}`}
          >
            <div>
              {n.slug ? (
                <Link
                  className="font-semibold text-ink"
                  to={`/posts/${n.slug}/review`}
                >
                  {n.message}
                </Link>
              ) : (
                <p>{n.message}</p>
              )}
              <p className="text-xs text-mute">
                <DateText value={n.created_at} />
              </p>
            </div>
            {!n.read_at && (
              <button
                className={buttonClass}
                disabled={busy}
                onClick={() => markRead(n.id)}
              >
                Mark read
              </button>
            )}
          </div>
        ))}
        <Pagination data={data} page={page} setPage={setPage} />
      </Panel>
    </PortalShell>
  )
}
