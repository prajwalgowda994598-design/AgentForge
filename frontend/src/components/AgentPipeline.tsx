// AgentForge – Agent Pipeline  ·  Industrial Foundry Edition
// Conveyor-line: stations connected by a thin rail; ember dot travels
// down the rail while a station is actively processing.

import type { AgentInfo, AgentStatus } from '@/types'
import { cn } from '@/utils/helpers'

interface AgentPipelineProps {
  agents: AgentInfo[]
}

const statusCfg: Record<AgentStatus, {
  label:      string
  roundel:    string
  labelClass: string
  badgeClass: string
  railClass:  string
}> = {
  idle:      { label: 'Waiting',  roundel: 'roundel-idle',   labelClass: 'text-forge-steel',   badgeClass: 'forge-badge-idle',   railClass: 'bg-forge-border' },
  starting:  { label: 'Starting', roundel: 'roundel-active', labelClass: 'text-forge-ember',   badgeClass: 'forge-badge-active', railClass: 'bg-forge-ember/50' },
  running:   { label: 'Running',  roundel: 'roundel-active', labelClass: 'text-forge-ember',   badgeClass: 'forge-badge-active', railClass: 'bg-forge-ember/50' },
  completed: { label: 'Done',     roundel: 'roundel-done',   labelClass: 'text-forge-success', badgeClass: 'forge-badge-done',   railClass: 'bg-forge-success/50' },
  failed:    { label: 'Failed',   roundel: 'roundel-failed', labelClass: 'text-forge-alert',   badgeClass: 'forge-badge-alert',  railClass: 'bg-forge-alert/50' },
}

const isActive = (s: AgentStatus) => s === 'running' || s === 'starting'

function AgentStation({ agent, isLast, index }: {
  agent: AgentInfo; isLast: boolean; index: number
}) {
  const cfg = statusCfg[agent.status]
  const active = isActive(agent.status)

  return (
    <div className="flex items-start gap-3">
      {/* Rail column */}
      <div className="flex flex-col items-center" style={{ minWidth: '2rem' }}>
        {/* Roundel */}
        <div className={cn('roundel', cfg.roundel, active && 'anim-ember-pulse')}>
          {agent.status === 'completed' ? (
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M1.5 5l2.5 2.5 4.5-5" stroke="currentColor" strokeWidth="1.8"
                    strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          ) : agent.status === 'failed' ? (
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M2 2l6 6M8 2l-6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          ) : (
            <span>{index + 1}</span>
          )}
        </div>

        {/* Vertical rail */}
        {!isLast && (
          <div
            className="relative mt-0.5 flex-1"
            style={{ width: '2px', minHeight: '2.75rem', background: '#333a42' }}
          >
            {/* Completed fill */}
            {agent.status === 'completed' && (
              <div className={cn('absolute inset-0', cfg.railClass)} />
            )}
            {/* Travelling ember dot */}
            {active && (
              <span
                className="anim-rail-travel absolute left-1/2 h-2.5 w-2.5 -translate-x-1/2
                           rounded-full bg-forge-ember"
                style={{ boxShadow: '0 0 8px 2px rgba(255,106,61,0.7)' }}
              />
            )}
          </div>
        )}
      </div>

      {/* Content */}
      <div className={cn('min-w-0 flex-1', isLast ? 'pb-0' : 'pb-5')}>
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-sans text-sm font-medium text-forge-paper">
            {agent.displayName}
          </span>
          <span className={cn('forge-badge', cfg.badgeClass)}>
            <span className={cn(
              'inline-block h-1.5 w-1.5 rounded-full bg-current',
              active && 'anim-ember-pulse'
            )} />
            {cfg.label}
          </span>
        </div>
        <p className="mt-0.5 font-sans text-xs text-forge-steel">{agent.description}</p>
        {agent.executionTimeMs !== undefined && agent.status === 'completed' && (
          <p className="mt-0.5 font-mono text-[10px] text-forge-steel/70">
            {(agent.executionTimeMs / 1000).toFixed(2)}s
          </p>
        )}
      </div>
    </div>
  )
}

export default function AgentPipeline({ agents }: AgentPipelineProps) {
  return (
    <div className="forge-panel p-5">
      <p className="forge-label mb-4">Agent Pipeline</p>
      <div>
        {agents.map((agent, idx) => (
          <AgentStation
            key={agent.name}
            agent={agent}
            isLast={idx === agents.length - 1}
            index={idx}
          />
        ))}
      </div>
    </div>
  )
}
