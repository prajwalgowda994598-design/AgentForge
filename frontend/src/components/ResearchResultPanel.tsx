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

function scoreColor(score: number): string {
  if (score >= 0.8) return '#5fbf8f'
  if (score >= 0.6) return '#e0b04a'
  return '#e0625a'
}

/** Circular pressure-gauge dial — SVG arc filled to `score` (0–1) */
function ScoreGauge({ score }: { score: number }) {
  const pct     = Math.round(score * 100)
  const color   = scoreColor(score)
  // Arc parameters: r=18, cx/cy=22, sweep from 135° to 405° (270° total arc)
  const R       = 18
  const CX      = 22
  const CY      = 22
  const ARC     = 270  // total degrees
  const START   = 135  // degrees, measured from 3-o'clock (SVG convention)
  const filled  = ARC * score

  function polarToXY(deg: number) {
    const rad = ((deg - 90) * Math.PI) / 180
    return { x: CX + R * Math.cos(rad), y: CY + R * Math.sin(rad) }
  }

  function arcPath(startDeg: number, sweepDeg: number) {
    const s = polarToXY(startDeg)
    const e = polarToXY(startDeg + sweepDeg)
    const large = sweepDeg > 180 ? 1 : 0
    return `M ${s.x} ${s.y} A ${R} ${R} 0 ${large} 1 ${e.x} ${e.y}`
  }

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="44" height="44" viewBox="0 0 44 44">
        {/* Track */}
        <path d={arcPath(START, ARC)} fill="none" stroke="#333a42" strokeWidth="3"
              strokeLinecap="round" />
        {/* Fill */}
        {filled > 0 && (
          <path d={arcPath(START, filled)} fill="none" stroke={color} strokeWidth="3"
                strokeLinecap="round"
                style={{ filter: `drop-shadow(0 0 3px ${color}88)` }} />
        )}
        {/* Centre value */}
        <text x={CX} y={CY + 1} textAnchor="middle" dominantBaseline="middle"
              fontFamily="'IBM Plex Mono', monospace" fontSize="8" fontWeight="700"
              fill={color}>
          {pct}
        </text>
        {/* Tick marks at 0 / 50 / 100 */}
        {[0, 0.5, 1].map((t) => {
          const { x: x1, y: y1 } = polarToXY(START + ARC * t)
          const { x: x2, y: y2 } = polarToXY(START + ARC * t)
          const offset = 4
          const rad = ((START + ARC * t - 90) * Math.PI) / 180
          return (
            <line key={t}
              x1={CX + (R - offset) * Math.cos(rad)} y1={CY + (R - offset) * Math.sin(rad)}
              x2={CX + (R + 1)      * Math.cos(rad)} y2={CY + (R + 1)      * Math.sin(rad)}
              stroke="#8b95a1" strokeWidth="1.5" strokeLinecap="round" />
          )
        })}
      </svg>
      <span className="font-mono text-[9px] uppercase tracking-widest text-forge-steel">
        Quality
      </span>
    </div>
  )
}

export default function ResearchResultPanel({ result }: ResearchResultPanelProps) {
  const scorePercent = Math.round(result.critic_score * 100)

  return (
    <div className="space-y-4" style={{ animation: 'fade-up 0.3s ease-out' }}>

      {/* ── Meta bar ── */}
      <div className="forge-panel px-5 py-4">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          {/* Score gauge */}
          <div className="flex items-center gap-3">
            <ScoreGauge score={result.critic_score} />
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
                  <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                    {src.source && (
                      <span className="forge-tag">{src.source}</span>
                    )}
                    {/* Relevance bar */}
                    <div className="flex items-center gap-1.5">
                      <div className="h-1 w-20 overflow-hidden rounded-full bg-forge-border">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${Math.round(src.score * 100)}%`,
                            background: src.score >= 0.6
                              ? '#5fbf8f'
                              : src.score >= 0.35
                              ? '#e0b04a'
                              : '#e0625a',
                            boxShadow: src.score >= 0.6
                              ? '0 0 4px rgba(95,191,143,0.5)'
                              : src.score >= 0.35
                              ? '0 0 4px rgba(224,176,74,0.5)'
                              : '0 0 4px rgba(224,98,90,0.5)',
                          }}
                        />
                      </div>
                      <span className="forge-tag">{Math.round(src.score * 100)}%</span>
                    </div>
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
