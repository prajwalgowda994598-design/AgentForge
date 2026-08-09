// AgentForge – Research Result Panel  ·  Industrial Foundry Edition

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ResearchResult } from '@/types'
import { cn, formatMs, scoreLabel } from '@/utils/helpers'

interface ResearchResultPanelProps {
  result: ResearchResult
}

function scoreBadgeClass(score: number): string {
  if (score >= 0.8) return 'forge-badge-done'
  if (score >= 0.6) return 'forge-badge-warn'
  return 'forge-badge-alert'
}

function scoreTextClass(score: number): string {
  if (score >= 0.8) return 'text-forge-success'
  if (score >= 0.6) return 'text-forge-warning'
  return 'text-forge-alert'
}

export default function ResearchResultPanel({ result }: ResearchResultPanelProps) {
  const scorePercent = Math.round(result.critic_score * 100)

  return (
    <div className="space-y-4" style={{ animation: 'fade-up 0.3s ease-out' }}>

      {/* ── Meta bar ── */}
      <div className="forge-panel px-5 py-4">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          {/* Score */}
          <div className="flex items-center gap-2.5">
            <div className="flex flex-col items-center">
              <span className={cn('font-display text-2xl font-bold leading-none', scoreTextClass(result.critic_score))}>
                {scorePercent}<span className="font-sans text-sm font-normal">%</span>
              </span>
              <span className="mt-0.5 font-mono text-[10px] uppercase tracking-widest text-forge-steel">
                Quality
              </span>
            </div>
            <span className={cn('forge-badge', scoreBadgeClass(result.critic_score))}>
              {scoreLabel(result.critic_score)}
            </span>
          </div>

          <div className="h-8 w-px bg-forge-border" />

          <div>
            <span className="font-sans text-sm font-semibold text-forge-paper">
              {result.iterations}
            </span>
            <span className="ml-1 font-sans text-sm text-forge-muted">
              iteration{result.iterations !== 1 ? 's' : ''}
            </span>
          </div>

          <div className="h-8 w-px bg-forge-border" />

          <div>
            <span className="font-mono text-xs text-forge-steel">Completed in </span>
            <span className="font-mono text-xs font-medium text-forge-paper">
              {formatMs(result.execution_time_ms)}
            </span>
          </div>

          <div className="ml-auto">
            <span className="forge-badge forge-badge-done">
              <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                <path d="M1 4l2 2 4-4" stroke="currentColor" strokeWidth="1.5"
                      strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Complete
            </span>
          </div>
        </div>
      </div>

      {/* ── Answer ── */}
      <div className="forge-panel p-6">
        <p className="forge-label mb-4">Research Answer</p>
        <div className="forge-prose">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {result.final_answer}
          </ReactMarkdown>
        </div>
      </div>

      {/* ── Sources ── */}
      {result.sources.length > 0 && (
        <div className="forge-panel p-5">
          <p className="forge-label mb-4">
            Sources
            <span className="ml-2 rounded border border-forge-border bg-forge-panel2
                             px-1.5 py-0.5 font-mono text-[10px] normal-case text-forge-steel">
              {result.sources.length}
            </span>
          </p>
          <ul className="space-y-3">
            {result.sources.map((src, idx) => (
              <li key={idx} className="flex items-start gap-3">
                {/* Index plate */}
                <span
                  className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center
                             rounded border border-forge-ember bg-forge-panel2
                             font-mono text-[10px] font-bold text-forge-ember"
                  style={{ boxShadow: '0 0 4px rgba(255,106,61,0.25)' }}
                >
                  {idx + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-sans text-sm font-medium text-forge-paper">
                    {src.title}
                  </p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {src.source && (
                      <span className="forge-tag">{src.source}</span>
                    )}
                    <span className="forge-tag">
                      {Math.round(src.score * 100)}% relevance
                    </span>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
