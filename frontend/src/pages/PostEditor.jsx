import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Button from '@/components/Button.jsx'
import PortalShell from '@/components/PortalShell.jsx'
import api from '@/lib/axios.js'
import { estimateReadingTime } from '@/lib/readingTime.js'

export default function PostEditor() {
  const { slug } = useParams()
  const isEdit = Boolean(slug)
  const navigate = useNavigate()

  const [categories, setCategories] = useState([])
  const [form, setForm] = useState({
    title: '', excerpt: '', content: '', category_id: '', tags: '', reading_time: '',
  })
  const [coverFile, setCoverFile] = useState(null)
  const [existingCover, setExistingCover] = useState('')
  const [readingTimeTouched, setReadingTimeTouched] = useState(false)
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const suggestedReadingTime = useMemo(() => estimateReadingTime(form.content), [form.content])

  useEffect(() => {
    api.get('/blog/categories/').then(({ data }) => setCategories(data)).catch(() => {})
  }, [])

  useEffect(() => {
    if (!isEdit) return
    api
      .get(`/portal/blog/${slug}/`)
      .then(({ data }) => {
        setForm({
          title: data.title,
          excerpt: data.excerpt,
          content: data.content,
          category_id: '',
          tags: (data.tags || []).join(', '),
          reading_time: data.reading_time,
        })
        setExistingCover(data.cover_image || '')
        setReadingTimeTouched(true)
      })
      .catch(() => setError('Could not load this post.'))
      .finally(() => setLoading(false))
  }, [isEdit, slug])

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  const buildFormData = () => {
    const fd = new FormData()
    fd.append('title', form.title)
    fd.append('excerpt', form.excerpt)
    fd.append('content', form.content)
    if (form.category_id) fd.append('category_id', form.category_id)
    fd.append('tags', JSON.stringify(form.tags.split(',').map((t) => t.trim()).filter(Boolean)))
    fd.append('reading_time', String(form.reading_time || suggestedReadingTime))
    if (coverFile) fd.append('cover_image', coverFile)
    return fd
  }

  const save = async (e) => {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      const fd = buildFormData()
      if (isEdit) {
        await api.patch(`/portal/blog/${slug}/`, fd)
      } else {
        await api.post('/portal/blog/', fd)
      }
      navigate('/')
    } catch (err) {
      const data = err.response?.data
      setError(typeof data === 'object' ? Object.values(data).flat().join(' ') : 'Could not save this post.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <PortalShell title="Loading…">
        <p className="text-sm text-slate">Loading post…</p>
      </PortalShell>
    )
  }

  return (
    <PortalShell title={isEdit ? 'Edit Post' : 'New Post'}>
      <form onSubmit={save} className="flex max-w-3xl flex-col gap-5 rounded-bento border border-line bg-white p-6 sm:p-8">
        <Field id="title" label="Title" value={form.title} onChange={update('title')} required />

        <div className="flex flex-col gap-2">
          <label htmlFor="excerpt" className="text-sm font-medium text-ink">Excerpt</label>
          <textarea
            id="excerpt"
            value={form.excerpt}
            onChange={update('excerpt')}
            rows={2}
            required
            maxLength={400}
            className="rounded-xl border border-line-strong bg-canvas px-4 py-3 text-sm text-ink outline-none transition-colors focus:border-orange-400"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="content" className="text-sm font-medium text-ink">Content (Markdown supported)</label>
          <textarea
            id="content"
            value={form.content}
            onChange={update('content')}
            rows={14}
            required
            className="rounded-xl border border-line-strong bg-canvas px-4 py-3 text-sm text-ink outline-none transition-colors focus:border-orange-400"
          />
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div className="flex flex-col gap-2">
            <label htmlFor="category" className="text-sm font-medium text-ink">Category</label>
            <select
              id="category"
              value={form.category_id}
              onChange={update('category_id')}
              className="rounded-xl border border-line-strong bg-canvas px-4 py-3 text-sm text-ink outline-none transition-colors focus:border-orange-400"
            >
              <option value="">Uncategorised</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="reading_time" className="text-sm font-medium text-ink">
              Reading time (minutes) <span className="font-normal text-mute">— suggested {suggestedReadingTime}</span>
            </label>
            <input
              id="reading_time"
              type="number"
              min={1}
              value={readingTimeTouched ? form.reading_time : suggestedReadingTime}
              onChange={(e) => {
                setReadingTimeTouched(true)
                update('reading_time')(e)
              }}
              className="rounded-xl border border-line-strong bg-canvas px-4 py-3 text-sm text-ink outline-none transition-colors focus:border-orange-400"
            />
          </div>
        </div>

        <Field id="tags" label="Topic tags (comma-separated)" value={form.tags} onChange={update('tags')} placeholder="Django, Performance, Scaling" />

        <div className="flex flex-col gap-2">
          <label htmlFor="cover_image" className="text-sm font-medium text-ink">Cover image</label>
          {existingCover && !coverFile && (
            <img src={existingCover} alt="" className="h-32 w-full rounded-xl object-cover" />
          )}
          <input
            id="cover_image"
            type="file"
            accept="image/*"
            onChange={(e) => setCoverFile(e.target.files?.[0] ?? null)}
            className="rounded-xl border border-line-strong bg-canvas px-4 py-3 text-sm text-slate file:mr-4 file:rounded-full file:border-0 file:bg-orange-500 file:px-4 file:py-1.5 file:text-white"
          />
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}

        <div className="flex gap-3">
          <Button type="submit" size="lg" disabled={saving}>
            {saving ? 'Saving…' : 'Save Draft'}
          </Button>
          <Button type="button" variant="secondary" size="lg" onClick={() => navigate('/')}>
            Cancel
          </Button>
        </div>
      </form>
    </PortalShell>
  )
}

function Field({ label, id, ...props }) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium text-ink">{label}</label>
      <input
        id={id}
        {...props}
        className="rounded-xl border border-line-strong bg-canvas px-4 py-3 text-sm text-ink outline-none transition-colors focus:border-orange-400"
      />
    </div>
  )
}
