// AgentForge – WebSocket hook for real-time agent updates

import { useCallback, useEffect, useRef, useState } from 'react'
import type { AgentInfo, AgentStatus, ResearchResult, WsEvent } from '@/types'

const AGENT_DEFINITIONS: Omit<AgentInfo, 'status'>[] = [
  { name: 'researcher',   displayName: 'Researcher',   description: 'Searches documents and web', icon: '🔍' },
  { name: 'summarizer',   displayName: 'Summarizer',   description: 'Condenses research notes',   icon: '📝' },
  { name: 'critic',       displayName: 'Critic',       description: 'Evaluates answer quality',   icon: '⚖️' },
  { name: 'fact_checker', displayName: 'Fact Checker', description: 'Verifies factual claims',    icon: '✅' },
  { name: 'synthesizer',  displayName: 'Synthesizer',  description: 'Generates final answer',     icon: '🧩' },
]

interface UseResearchWebSocketReturn {
  agents: AgentInfo[]
  result: ResearchResult | null
  error: string | null
  isConnected: boolean
  connect: (sessionId: string) => void
  disconnect: () => void
}

export function useResearchWebSocket(): UseResearchWebSocketReturn {
  const ws = useRef<WebSocket | null>(null)
  const [agents, setAgents] = useState<AgentInfo[]>(
    AGENT_DEFINITIONS.map((a) => ({ ...a, status: 'idle' as AgentStatus }))
  )
  const [result, setResult] = useState<ResearchResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const pingInterval = useRef<ReturnType<typeof setInterval> | null>(null)

  const disconnect = useCallback(() => {
    if (pingInterval.current) clearInterval(pingInterval.current)
    ws.current?.close()
    ws.current = null
    setIsConnected(false)
  }, [])

  const connect = useCallback((sessionId: string) => {
    disconnect()

    // Reset state for new session
    setAgents(AGENT_DEFINITIONS.map((a) => ({ ...a, status: 'idle' as AgentStatus })))
    setResult(null)
    setError(null)

    const wsUrl =
      (import.meta.env.VITE_WS_URL ?? `ws://${window.location.host}`) +
      `/ws/${sessionId}`

    const socket = new WebSocket(wsUrl)
    ws.current = socket

    socket.onopen = () => {
      setIsConnected(true)
      // Keep-alive ping every 25 seconds
      pingInterval.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send('ping')
        }
      }, 25_000)
    }

    socket.onmessage = (event) => {
      try {
        const msg: WsEvent = JSON.parse(event.data)

        if (msg.type === 'agent_status') {
          const { agent_name, status } = msg
          setAgents((prev) =>
            prev.map((a) =>
              a.name === agent_name ? { ...a, status: status as AgentStatus } : a
            )
          )
        } else if (msg.type === 'final_result') {
          setResult(msg.data)
          // Mark all agents completed on final result
          setAgents((prev) => prev.map((a) => ({ ...a, status: a.status === 'idle' ? 'idle' : 'completed' })))
        } else if (msg.type === 'error') {
          setError(msg.message)
        }
      } catch {
        // Ignore malformed messages
      }
    }

    socket.onerror = () => {
      setError('WebSocket connection error')
      setIsConnected(false)
    }

    socket.onclose = () => {
      setIsConnected(false)
      if (pingInterval.current) clearInterval(pingInterval.current)
    }
  }, [disconnect])

  // Cleanup on unmount
  useEffect(() => () => disconnect(), [disconnect])

  return { agents, result, error, isConnected, connect, disconnect }
}
