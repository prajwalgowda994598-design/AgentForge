// AgentForge – Axios API Client

import axios from 'axios'
import type { ResearchQueryRequest, ResearchSession, AgentRun, HealthStatus } from '@/types'

const BASE_URL = import.meta.env.VITE_API_URL ?? ''

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// Inject auth token if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Global error handler
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err.response?.data?.error?.message ?? err.message ?? 'Network error'
    return Promise.reject(new Error(message))
  }
)

// ── Research API ───────────────────────────────────────────────────────────────

export const submitResearch = async (
  request: ResearchQueryRequest
): Promise<{ session_id: string; status: string; message: string }> => {
  const { data } = await api.post('/research', request)
  return data
}

export const getSession = async (sessionId: string): Promise<ResearchSession> => {
  const { data } = await api.get(`/research/${sessionId}`)
  return data
}

export const getAgentRuns = async (sessionId: string): Promise<AgentRun[]> => {
  const { data } = await api.get(`/research/${sessionId}/runs`)
  return data
}

export const listSessions = async (limit = 20, offset = 0): Promise<ResearchSession[]> => {
  const { data } = await api.get('/research', { params: { limit, offset } })
  return data
}

// ── Documents API ──────────────────────────────────────────────────────────────

export const ingestDocument = async (body: {
  title: string
  source: string
  content: string
  metadata?: Record<string, unknown>
}) => {
  const { data } = await api.post('/documents', body)
  return data
}

export const getVectorStoreStats = async () => {
  const { data } = await api.get('/documents/stats')
  return data
}

export const loadSampleData = async () => {
  const { data } = await api.post('/documents/load-sample')
  return data
}

// ── Health API ─────────────────────────────────────────────────────────────────

export const checkHealth = async (): Promise<HealthStatus> => {
  const { data } = await axios.get(`${BASE_URL}/health/ready`)
  return data
}

export default api
