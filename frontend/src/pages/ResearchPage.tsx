// AgentForge – Main Research Page

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

  // When result arrives, transition to done
  const currentResult = result
  const effectiveState: PageState =
    wsError ? 'error'
    : currentResult ? 'done'
    : pageState

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      {/* Live session indicator */}
      {sessionId && isConnected && (
        <div className="mb-4 flex justify-center">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-xs text-green-700">
            <span className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
            Live session: {sessionId.slice(0, 8)}…
          </div>
        </div>
      )}

      {/* Error Banner */}
      {(submitError || wsError) && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          ⚠️ {submitError ?? wsError}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left column */}
        <div className="space-y-6 lg:col-span-1">
          <QueryForm
            onSubmit={handleSubmit}
            isLoading={effectiveState === 'running'}
          />
          <AgentPipeline agents={agents} />
        </div>

        {/* Right column */}
        <div className="lg:col-span-2">
          {effectiveState === 'idle' && (
            <div className="flex h-64 flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 text-gray-400">
              <span className="text-4xl">🔬</span>
              <p className="mt-3 text-sm">Enter a research question to get started</p>
            </div>
          )}

          {effectiveState === 'running' && !currentResult && (
            <div className="flex h-64 flex-col items-center justify-center rounded-xl border border-gray-200 bg-white shadow-sm">
              <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
              <p className="mt-4 text-sm font-medium text-gray-600">Running agent pipeline…</p>
              <p className="mt-1 text-xs text-gray-400">This may take 30–90 seconds</p>
            </div>
          )}

          {effectiveState === 'done' && currentResult && (
            <ResearchResultPanel result={currentResult} />
          )}

          {effectiveState === 'error' && !currentResult && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-700">
              <p className="font-semibold">Research pipeline failed</p>
              <p className="mt-1 text-sm">{submitError ?? wsError}</p>
              <button
                onClick={() => setPageState('idle')}
                className="mt-4 rounded bg-red-100 px-3 py-1.5 text-xs font-medium hover:bg-red-200"
              >
                Try again
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
