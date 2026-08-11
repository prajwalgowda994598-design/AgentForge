// AgentForge – Document Ingestion Panel  ·  Industrial Foundry Edition
// Allows pasting text content directly into the knowledge base (FAISS).

import { useState, type FormEvent } from 'react'
import { ingestDocument, loadSampleData, getVectorStoreStats } from '@/utils/api'

type PanelState = 'idle' | 'loading' | 'success' | 'error'

export default function IngestPanel() {
  const [open, setOpen]         = useState(false)
  const [title, setTitle]       = useState('')
  const [source, setSource]     = useState('')
  const [content, setContent]   = useState('')
  const [state, setState]       = useState<PanelState>('idle')
  const [message, setMessage]   = useState('')
  const [stats, setStats]       = useState<{ total_vectors: number } | null>(null)

  const reset = () => { setTitle(''); setSource(''); setContent(''); setState('idle'); setMessage('') }

  const loadStats = async () => {
    try {
      const s = await getVectorStoreStats()
      setStats(s)
    } catch { /* non-fatal */ }
  }

  const handleOpen = () => { setOpen(true); loadStats() }

  const handleIngest = async (e: FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !source.trim() || content.trim().length < 50) return
    setState('loading')
    try {
      const res = await ingestDocument({ title: title.trim(), source: source.trim(), content: content.trim() })
      setState('success')
      setMessage(`${res.chunks_created} chunk${res.chunks_created !== 1 ? 's' : ''} indexed into FAISS`)
      loadStats()
    } catch (err) {
      setState('error')
      setMessage(err instanceof Error ? err.message : 'Ingestion failed')
    }
  }

  const handleLoadSample = async () => {
    setState('loading')
    setMessage('')
    try {
      const res = await loadSampleData()
      setState('success')
      setMessage(res.message ?? 'Sample data loaded')
      loadStats()
    } catch (err) {
      setState('error')
      setMessage(err instanceof Error ? err.message : 'Failed to load sample data')
    }
  }

  if (!open) {
    return (
      <button onClick={handleOpen} className="forge-btn-ghost w-full text-center text-[10px]">
        ⊕ Add Documents to Knowledge Base
      </button>
    )
  }

  return (
    <div className="forge-panel p-5">
      <div className="mb-4 flex items-center justify-between">
        <p className="forge-label">Knowledge Base</p>
        <div className="flex items-center gap-3">
          {stats && (
            <span className="font-mono text-[10px] text-forge-steel">
              {stats.total_vectors ?? 0} vectors
            </span>
          )}
          <button
            onClick={() => { setOpen(false); reset() }}
            className="font-mono text-[10px] uppercase tracking-widest text-forge-steel
                       transition-colors hover:text-forge-ember"
          >
            ✕ Close
          </button>
        </div>
      </div>

      {/* Status message */}
      {state === 'success' && (
        <div className="mb-3 flex items-center gap-2 rounded border border-forge-success/40
                        bg-forge-success/5 px-3 py-2 font-mono text-xs text-forge-success">
          <span>✓</span> {message}
        </div>
      )}
      {state === 'error' && (
        <div className="mb-3 flex items-center gap-2 rounded border border-forge-alert/40
                        bg-forge-alert/5 px-3 py-2 font-mono text-xs text-forge-alert">
          <span>✗</span> {message}
        </div>
      )}

      {/* Ingest form */}
      <form onSubmit={handleIngest} className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="mb-1 block font-mono text-[9px] uppercase tracking-widest text-forge-steel">
              Title
            </label>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Document title"
              disabled={state === 'loading'}
              className="forge-input py-1.5 text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block font-mono text-[9px] uppercase tracking-widest text-forge-steel">
              Source / URL
            </label>
            <input
              value={source}
              onChange={e => setSource(e.target.value)}
              placeholder="https://... or filename"
              disabled={state === 'loading'}
              className="forge-input py-1.5 text-xs"
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block font-mono text-[9px] uppercase tracking-widest text-forge-steel">
            Content <span className="text-forge-steel/50">(min 50 chars)</span>
          </label>
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            placeholder="Paste document text here…"
            rows={5}
            disabled={state === 'loading'}
            className="forge-input text-xs"
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            type="submit"
            disabled={state === 'loading' || !title.trim() || !source.trim() || content.trim().length < 50}
            className="forge-btn py-1.5 text-[10px]"
          >
            {state === 'loading' ? (
              <>
                <span className="h-3 w-3 rounded-full border-2 border-forge-bg/30 border-t-forge-bg"
                      style={{ animation: 'spin 0.75s linear infinite' }} />
                Indexing…
              </>
            ) : '▶ Index Document'}
          </button>

          <span className="text-forge-border">|</span>

          <button
            type="button"
            onClick={handleLoadSample}
            disabled={state === 'loading'}
            className="forge-btn-ghost py-1.5 text-[10px]"
          >
            Load Sample Data
          </button>

          {(state === 'success' || state === 'error') && (
            <button type="button" onClick={reset}
                    className="font-mono text-[10px] text-forge-steel hover:text-forge-ember ml-auto">
              Clear
            </button>
          )}
        </div>
      </form>
    </div>
  )
}
