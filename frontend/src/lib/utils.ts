import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function priorityColor(p: string) {
  if (p === 'Critical') return 'bg-red-500'
  if (p === 'High') return 'bg-orange-500'
  if (p === 'Medium') return 'bg-yellow-500'
  return 'bg-gray-500'
}

export function riskColor(score: number) {
  if (score >= 70) return { bar: 'bg-red-500', text: 'text-red-400', label: 'HIGH RISK' }
  if (score >= 40) return { bar: 'bg-orange-500', text: 'text-orange-400', label: 'MEDIUM RISK' }
  return { bar: 'bg-green-500', text: 'text-green-400', label: 'LOW RISK' }
}
