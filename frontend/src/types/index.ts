// AgentForge – TypeScript Type Definitions

export type AgentStatus = 'idle' | 'starting' | 'running' | 'completed' | 'failed'

export interface AgentInfo {
  name: string
  displayName: string
  description: string
  icon: string
  status: AgentStatus
  executionTimeMs?: number
}

export interface ResearchQueryRequest {
  query: string
  context?: string
  top_k?: number
  session_id?: string
}

export interface ResearchSession {
  id: string
  user_id: string | null
  query: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  final_answer: string | null
  critic_score: number | null
  iterations: number
  created_at: string
  updated_at: string
}

export interface AgentRun {
  id: string
  session_id: string
  agent_name: string
  status: string
  execution_time_ms: number | null
  tokens_used: number | null
  error_message: string | null
  created_at: string
}

export interface Source {
  title: string
  source: string
  score: number
}

export interface ResearchResult {
  session_id: string
  final_answer: string
  critic_score: number
  iterations: number
  sources: Source[]
  execution_time_ms: number
  status: string
}

// WebSocket event types
export type WsEventType = 'agent_status' | 'stream_chunk' | 'final_result' | 'error' | 'pong'

export interface WsAgentStatusEvent {
  type: 'agent_status'
  session_id: string
  agent_name: string
  status: AgentStatus
  message: string
  timestamp: string
}

export interface WsFinalResultEvent {
  type: 'final_result'
  data: ResearchResult
}

export interface WsErrorEvent {
  type: 'error'
  message: string
}

export interface WsStreamChunkEvent {
  type: 'stream_chunk'
  content: string
}

export type WsEvent =
  | WsAgentStatusEvent
  | WsFinalResultEvent
  | WsErrorEvent
  | WsStreamChunkEvent
  | { type: 'pong' }

export interface HealthStatus {
  status: string
  version: string
  environment: string
  services: Record<string, string>
}
