import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${BASE}/api/v1`,
  timeout: 30000,
})

// ── Attach JWT token to every request ──────────────────────────
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Auto-logout on 401 ─────────────────────────────────────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ───────────────────────────────────────────────────────
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login:    (data) => api.post('/auth/login', data),
  me:       ()     => api.get('/auth/me'),
  refresh:  (token) => api.post('/auth/refresh', { refresh_token: token }),
}

// ── Analyze ────────────────────────────────────────────────────
export const analyzeAPI = {
  text:    (text) => api.post('/analyze/text', { text }),
  url:     (url)  => api.post('/analyze/url',  { url }),
  image:   (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/analyze/image', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  history: (limit = 20, offset = 0) => api.get(`/analyze/history?limit=${limit}&offset=${offset}`),
  getById: (id) => api.get(`/analyze/history/${id}`),
}

// ── News ───────────────────────────────────────────────────────
export const newsAPI = {
  trending: (category = 'general', country = 'us') =>
    api.get(`/news/trending?category=${category}&country=${country}&page_size=12`),
  search: (q) => api.get(`/news/search?q=${encodeURIComponent(q)}&page_size=10`),
}

export default api
