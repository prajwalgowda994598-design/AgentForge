// AgentForge – Research Result Display Component
// Renders the final markdown answer, critic score, sources, and stats.

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ResearchResult } from '@/types'
import { cn, formatMs, scoreColor, scoreLabel } from '@/utils/helpers'

interface ResearchResultPanelProps {
  result: ResearchResult
}

export default function ResearchResultPanel({ result }: ResearchResultPanelProps) {
  const scorePercent = Math.round(result.critic_score * 100)

  return (
    <div className="space-y-4">
      {/* Meta bar */}
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Quality Score</span>
          <span className={cn('text-lg font-bold', scoreColor(result.critic_score))}>
            {scorePercent}%
          </span>
          <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', 
            result.critic_score >= 0.7 ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
          )}>
            {scoreLabel(result.critic_score)}
          </span>
        </div>

        <div className="h-5 w-px bg-gray-200" />

        <div className="text-sm text-gray-500">
          <span className="font-medium text-gray-700">{result.iterations}</span> iteration{result.iterations !== 1 ? 's' : ''}
        </div>

        <div className="h-5 w-px bg-gray-200" />

        <div className="text-sm text-gray-500">
          Completed in <span className="font-medium text-gray-700">{formatMs(result.execution_time_ms)}</span>
        </div>

        <div className="ml-auto">
          <span className={cn(
            'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium',
            'bg-green-100 text-green-700'
          )}>
            ✓ Research Complete
          </span>
        </div>
      </div>

      {/* Answer */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">
          Research Answer
        </h2>
        <div className="prose prose-sm max-w-none text-gray-800">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {result.final_answer}
          </ReactMarkdown>
        </div>
      </div>

      {/* Sources */}
      {result.sources.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-400">
            Sources ({result.sources.length})
          </h2>
          <ul className="space-y-2">
            {result.sources.map((src, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                  {idx + 1}
                </span>
                <div>
                  <span className="font-medium text-gray-800">{src.title}</span>
                  {src.source && (
                    <span className="ml-2 text-xs text-gray-400">({src.source})</span>
                  )}
                  <span className="ml-2 text-xs text-gray-400">
                    relevance: {Math.round(src.score * 100)}%
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
