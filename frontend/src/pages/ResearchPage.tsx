// AgentForge – Research Page  ·  Industrial Foundry Edition

import { useState, useCallback } from 'react'
import { submitResearch } from '@/utils/api'
import { useResearchWebSocket } from '@/hooks/useResearchWebSocket'
import QueryForm from '@/components/QueryForm'
import AgentPipeline from '@/components/AgentPipeline'
import ResearchResultPanel from '@/components/ResearchResultPanel'

type PageState = 'idle' | 'running' | 'done' | 'error'

export default function ResearchPage() {
  const [pageState, setPageState] = useState<PageState>('idle')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const { agents, result, error: wsError, isConnected, connect } = useResearchWebSocket()

  const handleSubmit = useCallback(async (query: string, topK: number) => {
    setSubmitError(null)
    setPageState('running')
    try {
      const res = await submitResearch({ query, top_k: topK })
      setSessionId(res.session_id)
      connect(res.session_id)
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to start research')
      setPageState('error')
    }
  }, [connect])

  const currentResult = result
  const effectiveState: PageState =
    wsError ? 'error' : currentResult ? 'done' : pageState

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">

      {/* Live session indicator */}
      {sessionId && isConnected && (
        <div className="mb-5 flex justify-center" style={{ animation: 'fade-up 0.25s ease-out' }}>
          <div
            className="inline-flex items-center gap-2 rounded border border-forge-success/40
                       bg-forge-panel px-3.5 py-1 font-mono text-[10px] uppercase
                       tracking-widest text-forge-success"
            style={{ boxShadow: '0 0 8px rgba(95,191,143,0.15)' }}
          >
            <span
              className="h-1.5 w-1.5 rounded-full bg-forge-success anim-ember-pulse"
              style={{ boxShadow: '0 0 4px rgba(95,191,143,0.8)' }}
            />
            Live · {sessionId.slice(0, 8)}
          </div>
        </div>
      )}

      {/* Error banner */}
      {(submitError || wsError) && (
        <div
          className="mb-5 flex items-start gap-3 rounded border border-forge-alert/40
                     bg-forge-panel px-4 py-3 font-sans text-sm text-forge-alert"
        >
          <svg className="mt-0.5 shrink-0" width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1L13 12.5H1L7 1z" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinejoin="round" />
            <path d="M7 5v3.5M7 10v.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
          </svg>
          {submitError ?? wsError}
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Left sidebar */}
        <div className="space-y-4 lg:col-span-1">
          <QueryForm onSubmit={handleSubmit} isLoading={effectiveState === 'running'} />
          <AgentPipeline agents={agents} />
        </div>

        {/* Main content */}
        <div className="lg:col-span-2">

          {/* Idle */}
          {effectiveState === 'idle' && (
            <div
              className="flex h-72 flex-col items-center justify-center rounded
                         border border-dashed border-forge-border text-center px-6"
              style={{ background: 'rgba(27,31,36,0.5)' }}
            >
              {/* Blueprint crosshair target */}
              <svg width="56" height="56" viewBox="0 0 56 56" fill="none" className="mb-4 opacity-50">
                <circle cx="28" cy="28" r="24" stroke="#333a42" strokeWidth="1" />
                <circle cx="28" cy="28" r="12" stroke="#333a42" strokeWidth="1" />
                <circle cx="28" cy="28" r="4"  fill="#ff6a3d" opacity="0.6" />
                <line x1="28" y1="4"  x2="28" y2="16" stroke="#ff6a3d" strokeWidth="1" strokeDasharray="2 2" opacity="0.5" />
                <line x1="28" y1="40" x2="28" y2="52" stroke="#ff6a3d" strokeWidth="1" strokeDasharray="2 2" opacity="0.5" />
                <line x1="4"  y1="28" x2="16" y2="28" stroke="#ff6a3d" strokeWidth="1" strokeDasharray="2 2" opacity="0.5" />
                <line x1="40" y1="28" x2="52" y2="28" stroke="#ff6a3d" strokeWidth="1" strokeDasharray="2 2" opacity="0.5" />
              </svg>
              <p className="font-display text-sm font-bold uppercase tracking-widest text-forge-steel">
                Awaiting Query
              </p>
              <p className="mt-1 font-sans text-xs text-forge-steel/60">
                Enter a research question to initialise the pipeline
              </p>
            </div>
          )}

          {/* Running */}
          {effectiveState === 'running' && !currentResult && (
            <div className="forge-panel flex h-72 flex-col items-center justify-center gap-5">
              {/* Triple-ring spinner */}
              <div className="relative h-14 w-14">
                <div
                  className="absolute inset-0 rounded-full border-2 border-transparent border-t-forge-ember"
                  style={{ animation: 'spin 1s linear infinite', boxShadow: '0 0 10px rgba(255,106,61,0.3)' }}
                />
                <div
                  className="absolute inset-2 rounded-full border-2 border-transparent border-t-forge-blue"
                  style={{ animation: 'spin 1.6s linear infinite reverse' }}
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div
                    className="h-2 w-2 rounded-full bg-forge-ember anim-ember-pulse"
                  />
                </div>
              </div>
              <div className="text-center">
                <p className="font-display text-sm font-bold uppercase tracking-widest text-forge-paper">
                  Pipeline Active
                </p>
                <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-forge-steel">
                  30 – 90 seconds
                </p>
              </div>
            </div>
          )}

          {/* Done */}
          {effectiveState === 'done' && currentResult && (
            <ResearchResultPanel result={currentResult} />
          )}

          {/* Error */}
          {effectiveState === 'error' && !currentResult && (
            <div className="forge-panel p-8 text-center">
              <div
                className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded
                           border border-forge-alert/40 bg-forge-panel2 text-forge-alert"
                style={{ boxShadow: '0 0 12px rgba(224,98,90,0.15)' }}
              >
                <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                  <path d="M11 2L21 20H1L11 2z" stroke="currentColor" strokeWidth="1.5"
                        fill="none" strokeLinejoin="round" />
                  <path d="M11 8v5M11 15v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </div>
              <p className="font-display text-sm font-bold uppercase tracking-widest text-forge-alert">
                Pipeline Failed
              </p>
              <p className="mt-2 font-sans text-sm text-forge-muted">{submitError ?? wsError}</p>
              <button
                onClick={() => setPageState('idle')}
                className="forge-btn-ghost mt-5"
              >
                ↩ Retry
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
