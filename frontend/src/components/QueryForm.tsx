// AgentForge – Research Query Input Form

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
    <form onSubmit={handleSubmit} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-400">
        Research Query
      </h2>

      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a complex research question…"
        rows={4}
        disabled={isLoading}
        className="w-full resize-none rounded-lg border border-gray-300 px-4 py-3 text-sm
                   text-gray-800 placeholder-gray-400 transition
                   focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200
                   disabled:cursor-not-allowed disabled:bg-gray-50"
      />

      {/* Example queries */}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {EXAMPLE_QUERIES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => setQuery(q)}
            className="rounded-full border border-gray-200 px-2.5 py-0.5 text-xs text-gray-500
                       transition hover:border-blue-300 hover:text-blue-600"
          >
            {q.length > 40 ? q.slice(0, 40) + '…' : q}
          </button>
        ))}
      </div>

      {/* Advanced options */}
      <div className="mt-3">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-xs text-gray-400 hover:text-gray-600"
        >
          {showAdvanced ? '▲ Hide' : '▼ Show'} advanced options
        </button>
        {showAdvanced && (
          <div className="mt-2 flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <span>Top-K results:</span>
              <input
                type="number"
                min={1}
                max={20}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-16 rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
            </label>
          </div>
        )}
      </div>

      {/* Submit */}
      <div className="mt-4 flex items-center justify-between">
        <span className="text-xs text-gray-400">
          Ctrl+Enter to submit
        </span>
        <button
          type="submit"
          disabled={!query.trim() || isLoading}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm
                     font-semibold text-white transition
                     hover:bg-blue-700 active:bg-blue-800
                     disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? (
            <>
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Researching…
            </>
          ) : (
            '🚀 Start Research'
          )}
        </button>
      </div>
    </form>
  )
}
