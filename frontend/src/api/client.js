import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Crawls
export const crawlsAPI = {
  list: () => api.get('/api/crawls/'),
  get: (id) => api.get(`/api/crawls/${id}`),
  create: (data) => api.post('/api/crawls/', data),
  start: (id) => api.post(`/api/crawls/${id}/start`),
  delete: (id) => api.delete(`/api/crawls/${id}`),
}

// URLs
export const urlsAPI = {
  list: (crawlId, params = {}) => api.get(`/api/crawls/${crawlId}/urls/`, { params }),
  summary: (crawlId) => api.get(`/api/crawls/${crawlId}/urls/summary`),
  exportCSV: (crawlId) => `${API_BASE_URL}/api/crawls/${crawlId}/urls/export/csv`,
}

// Issues
export const issuesAPI = {
  list: (crawlId, params = {}) => api.get(`/api/crawls/${crawlId}/issues/`, { params }),
  summary: (crawlId) => api.get(`/api/crawls/${crawlId}/issues/summary`),
  analyze: (crawlId) => api.post(`/api/crawls/${crawlId}/issues/analyze`),
  exportCSV: (crawlId) => `${API_BASE_URL}/api/crawls/${crawlId}/issues/export/csv`,
}

export default api
