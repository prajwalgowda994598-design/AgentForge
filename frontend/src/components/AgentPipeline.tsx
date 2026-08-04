// AgentForge – Agent Pipeline Status Component
// Shows the 5 agents as a vertical pipeline with live status badges.

import type { AgentInfo, AgentStatus } from '@/types'
import { cn } from '@/utils/helpers'

interface AgentPipelineProps {
  agents: AgentInfo[]
}

const statusConfig: Record<AgentStatus, { label: string; dot: string; text: string }> = {
  idle:      { label: 'Waiting',   dot: 'bg-gray-300',    text: 'text-gray-500' },
  starting:  { label: 'Starting',  dot: 'bg-blue-400 animate-pulse', text: 'text-blue-600' },
  running:   { label: 'Running',   dot: 'bg-blue-500 animate-pulse', text: 'text-blue-700' },
  completed: { label: 'Done',      dot: 'bg-green-500',   text: 'text-green-700' },
  failed:    { label: 'Failed',    dot: 'bg-red-500',     text: 'text-red-700' },
}

function AgentCard({ agent, isLast }: { agent: AgentInfo; isLast: boolean }) {
  const cfg = statusConfig[agent.status]
  return (
    <div className="flex items-start gap-3">
      {/* Timeline column */}
      <div className="flex flex-col items-center">
        <div
          className={cn(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 text-lg',
            agent.status === 'running' || agent.status === 'starting'
              ? 'border-blue-500 bg-blue-50'
              : agent.status === 'completed'
              ? 'border-green-500 bg-green-50'
              : agent.status === 'failed'
              ? 'border-red-400 bg-red-50'
              : 'border-gray-200 bg-white'
          )}
        >
          {agent.icon}
        </div>
        {!isLast && (
          <div
            className={cn(
              'mt-1 w-0.5 flex-1',
              agent.status === 'completed' ? 'bg-green-400' : 'bg-gray-200'
            )}
            style={{ minHeight: '2rem' }}
          />
        )}
      </div>

      {/* Content */}
      <div className="pb-6">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-gray-800">{agent.displayName}</span>
          <span className={cn('flex items-center gap-1 text-xs font-medium', cfg.text)}>
            <span className={cn('inline-block h-2 w-2 rounded-full', cfg.dot)} />
            {cfg.label}
          </span>
        </div>
        <p className="mt-0.5 text-sm text-gray-500">{agent.description}</p>
        {agent.executionTimeMs !== undefined && agent.status === 'completed' && (
          <p className="mt-0.5 text-xs text-gray-400">{(agent.executionTimeMs / 1000).toFixed(1)}s</p>
        )}
      </div>
    </div>
  )
}

export default function AgentPipeline({ agents }: AgentPipelineProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">
        Agent Pipeline
      </h2>
      <div>
        {agents.map((agent, idx) => (
          <AgentCard key={agent.name} agent={agent} isLast={idx === agents.length - 1} />
        ))}
      </div>
    </div>
  )
}
