// AgentForge – Session History Page
// Lists all previous research sessions with their query, status, score, and a
// link to re-open the result.

import { useEffect, useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listSessions } from '@/utils/api'
import type { ResearchSession } from '@/types'
import { cn, scoreColor, scoreLabel } from '@/utils/helpers'

const statusBadge: Record<string, { bg: string; text: string; label: string }> = {
  completed: { bg: 'bg-green-100',  text: 'text-green-700',  label: 'Completed' },
  running:   { bg: 'bg-blue-100',   text: 'text-blue-700',   label: 'Running'   },
  pending:   { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Pending'   },
  failed:    { bg: 'bg-red-100',    text: 'text-red-700',    label: 'Failed'    },
}

function SessionRow({ session }: { session: ResearchSession }) {
  const badge = statusBadge[session.status] ?? statusBadge.pending
  const scorePercent = session.critic_score !== null
    ? Math.round((session.critic_score ?? 0) * 100)
    : null

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:shadow-md sm:flex-row sm:items-center sm:gap-4">
      {/* Query text */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-900" title={session.query}>
          {session.query}
        </p>
        <p className="mt-0.5 text-xs text-gray-400">
          {new Date(session.created_at).toLocaleString()}
          {' · '}
          Session <span className="font-mono">{session.id.slice(0, 8)}</span>
        </p>
      </div>

      {/* Status + score */}
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-medium', badge.bg, badge.text)}>
          {badge.label}
        </span>

        {scorePercent !== null && (
          <span className={cn('text-sm font-semibold', scoreColor(session.critic_score ?? 0))}>
            {scorePercent}%
            <span className="ml-1 text-xs font-normal text-gray-500">
              ({scoreLabel(session.critic_score ?? 0)})
            </span>
          </span>
        )}

        {session.iterations > 0 && (
          <span className="text-xs text-gray-400">
            {session.iterations} iter{session.iterations !== 1 ? 's' : ''}
          </span>
        )}

        {session.status === 'completed' && (
          <Link
            to={`/research/${session.id}`}
            className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
          >
            View →
          </Link>
        )}
      </div>
    </div>
  )
}

export default function HistoryPage() {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<ResearchSession[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 20

  const load = useCallback(async (offset: number) => {
    setLoading(true)
    setError(null)
    try {
      const data = await listSessions(PAGE_SIZE, offset)
      setSessions(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(page * PAGE_SIZE)
  }, [page, load])

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      {/* Header */}
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Research History</h1>
          <p className="mt-1 text-sm text-gray-500">Your previous research sessions</p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
        >
          ← New Research
        </button>
      </header>

      {/* Error */}
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          ⚠️ {error}
          {error.includes('401') || error.includes('credentials') ? (
            <span className="ml-2 text-xs">(History requires authentication)</span>
          ) : null}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
        </div>
      )}

      {/* Empty */}
      {!loading && !error && sessions.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 py-16 text-gray-400">
          <span className="text-4xl">🗂️</span>
          <p className="mt-3 text-sm">No research sessions yet.</p>
          <button
            onClick={() => navigate('/')}
            className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            Start your first research
          </button>
        </div>
      )}

      {/* Session list */}
      {!loading && sessions.length > 0 && (
        <>
          <div className="space-y-3">
            {sessions.map((s) => (
              <SessionRow key={s.id} session={s} />
            ))}
          </div>

          {/* Pagination */}
          <div className="mt-6 flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
            >
              ← Prev
            </button>
            <span className="text-sm text-gray-500">Page {page + 1}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={sessions.length < PAGE_SIZE}
              className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        </>
      )}
    </div>
  )
}
