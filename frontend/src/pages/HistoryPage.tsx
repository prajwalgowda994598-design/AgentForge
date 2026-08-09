// AgentForge – History Page  ·  Industrial Foundry Edition

import { useEffect, useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listSessions } from '@/utils/api'
import type { ResearchSession } from '@/types'
import { cn, scoreLabel } from '@/utils/helpers'

const statusCfg: Record<string, { badge: string; dot: string; label: string }> = {
  completed: { badge: 'forge-badge-done',   dot: 'bg-forge-success', label: 'Completed' },
  running:   { badge: 'forge-badge-active', dot: 'bg-forge-ember',   label: 'Running'   },
  pending:   { badge: 'forge-badge-warn',   dot: 'bg-forge-warning', label: 'Pending'   },
  failed:    { badge: 'forge-badge-alert',  dot: 'bg-forge-alert',   label: 'Failed'    },
}

function scoreTextClass(score: number): string {
  if (score >= 0.8) return 'text-forge-success'
  if (score >= 0.6) return 'text-forge-warning'
  return 'text-forge-alert'
}

function SessionRow({ session }: { session: ResearchSession }) {
  const cfg = statusCfg[session.status] ?? statusCfg.pending
  const scorePercent = session.critic_score !== null
    ? Math.round((session.critic_score ?? 0) * 100)
    : null

  return (
    <div
      className="forge-panel flex flex-col gap-2 p-4 transition-colors
                 hover:border-forge-ember/40 sm:flex-row sm:items-center sm:gap-4"
    >
      {/* Query */}
      <div className="min-w-0 flex-1">
        <p className="truncate font-sans text-sm font-medium text-forge-paper"
           title={session.query}>
          {session.query}
        </p>
        <p className="mt-0.5 font-mono text-[10px] text-forge-steel">
          {new Date(session.created_at).toLocaleString()}
          {' · '}
          <span>{session.id.slice(0, 8)}</span>
        </p>
      </div>

      {/* Meta */}
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <span className={cn('forge-badge', cfg.badge)}>
          <span className={cn('h-1.5 w-1.5 rounded-full', cfg.dot)} />
          {cfg.label}
        </span>

        {scorePercent !== null && (
          <span className={cn('font-display text-sm font-bold', scoreTextClass(session.critic_score ?? 0))}>
            {scorePercent}%
            <span className="ml-1 font-mono text-[10px] font-normal text-forge-steel">
              ({scoreLabel(session.critic_score ?? 0)})
            </span>
          </span>
        )}

        {session.iterations > 0 && (
          <span className="font-mono text-[10px] text-forge-steel">
            {session.iterations} iter{session.iterations !== 1 ? 's' : ''}
          </span>
        )}

        {session.status === 'completed' && (
          <Link to={`/research/${session.id}`} className="forge-btn px-3 py-1.5 text-[10px]">
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

  useEffect(() => { load(page * PAGE_SIZE) }, [page, load])

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">

      {/* Header */}
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-bold uppercase tracking-widest text-forge-paper">
            Research History
          </h1>
          <p className="mt-0.5 font-sans text-sm text-forge-muted">
            Previous research sessions
          </p>
        </div>
        <button onClick={() => navigate('/')} className="forge-btn-ghost">
          ← New Research
        </button>
      </header>

      {/* Error */}
      {error && (
        <div
          className="mb-5 flex items-start gap-3 rounded border border-forge-alert/40
                     bg-forge-panel px-4 py-3 font-sans text-sm text-forge-alert"
        >
          <svg className="mt-0.5 shrink-0" width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1L13 12.5H1L7 1z" stroke="currentColor" strokeWidth="1.2"
                  fill="none" strokeLinejoin="round" />
            <path d="M7 5v3.5M7 10v.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
          </svg>
          {error}
          {(error.includes('401') || error.includes('credentials')) && (
            <span className="text-forge-steel"> — authentication required</span>
          )}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-20">
          <div
            className="h-8 w-8 rounded-full border-2 border-forge-border border-t-forge-ember"
            style={{ animation: 'spin 0.85s linear infinite', boxShadow: '0 0 8px rgba(255,106,61,0.2)' }}
          />
        </div>
      )}

      {/* Empty */}
      {!loading && !error && sessions.length === 0 && (
        <div
          className="flex flex-col items-center justify-center rounded border
                     border-dashed border-forge-border py-20 text-center"
          style={{ background: 'rgba(27,31,36,0.5)' }}
        >
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" className="mb-4 opacity-40">
            <rect x="4" y="4" width="32" height="32" rx="2" stroke="#333a42" strokeWidth="1.5" />
            <path d="M10 14h20M10 20h20M10 26h12" stroke="#ff6a3d" strokeWidth="1.2"
                  strokeLinecap="round" opacity="0.6" />
          </svg>
          <p className="font-display text-xs font-bold uppercase tracking-widest text-forge-steel">
            No Sessions Yet
          </p>
          <p className="mt-1 font-sans text-xs text-forge-steel/60">
            Completed research will appear here
          </p>
          <button onClick={() => navigate('/')} className="forge-btn mt-5">
            Start First Research
          </button>
        </div>
      )}

      {/* List */}
      {!loading && sessions.length > 0 && (
        <>
          <div className="space-y-3">
            {sessions.map(s => <SessionRow key={s.id} session={s} />)}
          </div>

          {/* Pagination */}
          <div className="mt-6 flex items-center justify-between">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="forge-btn-ghost"
            >
              ← Prev
            </button>
            <span className="font-mono text-xs text-forge-steel">Page {page + 1}</span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={sessions.length < PAGE_SIZE}
              className="forge-btn-ghost"
            >
              Next →
            </button>
          </div>
        </>
      )}
    </div>
  )
}
