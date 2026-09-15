import api from '@/lib/axios.js'

/** Uploads an image for the rich text editor, returns its public URL. */
export async function uploadContentImage(file) {
  const fd = new FormData()
  fd.append('image', file)
  const { data } = await api.post('/portal/blog/uploads/image/', fd)
  return data.url
}
