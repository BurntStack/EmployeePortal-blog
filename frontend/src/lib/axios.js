import axios from 'axios'

/**
 * Central Axios instance. The base URL comes from an environment variable so
 * the same build works across local, staging and production.
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
})

// Attach the JWT access token if present. Drop the forced JSON content-type
// for FormData bodies (cover-image uploads) so the browser can set the
// correct multipart boundary itself.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('burntstack-access')
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  return config
})

// Access tokens live 30 minutes. On a 401, try the refresh token once before
// giving up and sending the portal back to the login screen.
let refreshPromise = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const refreshToken = localStorage.getItem('burntstack-refresh')

    if (error.response?.status !== 401 || original?._retried || !refreshToken || original?.url?.includes('/auth/token/')) {
      return Promise.reject(error)
    }
    original._retried = true

    try {
      if (!refreshPromise) {
        refreshPromise = axios
          .post(`${api.defaults.baseURL}/auth/token/refresh/`, { refresh: refreshToken })
          .finally(() => {
            refreshPromise = null
          })
      }
      const { data } = await refreshPromise
      localStorage.setItem('burntstack-access', data.access)
      original.headers.Authorization = `Bearer ${data.access}`
      return api(original)
    } catch {
      localStorage.removeItem('burntstack-access')
      localStorage.removeItem('burntstack-refresh')
      window.location.href = '/portal/login'
      return Promise.reject(error)
    }
  },
)

export default api
