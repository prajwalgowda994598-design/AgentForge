// AgentForge – cn() utility (Tailwind class merger)
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export function scoreColor(score: number): string {
  if (score >= 0.8) return 'text-green-600'
  if (score >= 0.6) return 'text-yellow-600'
  return 'text-red-600'
}

export function scoreLabel(score: number): string {
  if (score >= 0.9) return 'Excellent'
  if (score >= 0.7) return 'Good'
  if (score >= 0.5) return 'Fair'
  return 'Poor'
}
