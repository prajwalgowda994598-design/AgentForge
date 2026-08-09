// AgentForge – Research Query Input Form  ·  Industrial Foundry Edition

import { useState, type FormEvent, type KeyboardEvent } from 'react'

interface QueryFormProps {
  onSubmit: (query: string, topK: number) => void
  isLoading: boolean
}

const EXAMPLE_QUERIES = [
  'What are the latest breakthroughs in quantum computing?',
  'Explain the key differences between transformer and mamba architectures.',
  'What is the current state of CRISPR gene editing in medicine?',
]

export default function QueryForm({ onSubmit, isLoading }: QueryFormProps) {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim() || isLoading) return
    onSubmit(query.trim(), topK)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      if (!query.trim() || isLoading) return
      onSubmit(query.trim(), topK)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="forge-panel p-5">
      <p className="forge-label mb-3">Research Query</p>

      {/* Textarea */}
      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a complex research question…"
        rows={4}
        disabled={isLoading}
        className="forge-input"
      />

      {/* Example chips */}
      <div className="mt-2.5 flex flex-wrap gap-1.5">
        {EXAMPLE_QUERIES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => setQuery(q)}
            className="forge-chip"
          >
            {q.length > 46 ? q.slice(0, 46) + '…' : q}
          </button>
        ))}
      </div>

      {/* Advanced */}
      <div className="mt-3.5">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="font-mono text-[10px] uppercase tracking-widest text-forge-steel
                     transition-colors hover:text-forge-ember"
        >
          {showAdvanced ? '▲ Hide' : '▼ Show'} Advanced
        </button>

        {showAdvanced && (
          <div className="mt-2 flex items-center gap-3 rounded border border-forge-border
                          bg-forge-panel2 px-3 py-2">
            <label className="flex items-center gap-2 font-mono text-xs text-forge-steel">
              <span className="uppercase tracking-widest">Top-K</span>
              <input
                type="number"
                min={1}
                max={20}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-14 rounded border border-forge-border bg-forge-bg px-2 py-1
                           font-mono text-xs text-forge-paper focus:border-forge-ember
                           focus:outline-none focus:ring-1 focus:ring-forge-ember/30"
              />
            </label>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-widest text-forge-steel">
          Ctrl+Enter
        </span>
        <button
          type="submit"
          disabled={!query.trim() || isLoading}
          className="forge-btn"
        >
          {isLoading ? (
            <>
              <span
                className="h-3.5 w-3.5 rounded-full border-2 border-forge-bg/30 border-t-forge-bg"
                style={{ animation: 'spin 0.75s linear infinite' }}
              />
              Processing…
            </>
          ) : (
            '▶ Launch Research'
          )}
        </button>
      </div>
    </form>
  )
}
