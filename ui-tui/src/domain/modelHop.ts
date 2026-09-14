import { TUI_SESSION_MODEL_FLAG } from './slash.js'
import type { ModelOptionProvider } from '../gatewayTypes.js'

export interface HopModel {
  current: boolean
  id: string
  label: string
  provider: string
}

export const flattenHopModels = (providers: ModelOptionProvider[], currentModel = ''): HopModel[] => {
  const current = currentModel.trim()
  const rows: HopModel[] = []

  for (const provider of providers) {
    if (provider.authenticated === false) {
      continue
    }

    for (const id of provider.models ?? []) {
      const label = `${provider.slug}/${id}`
      rows.push({
        current: id === current || label === current,
        id,
        label,
        provider: provider.slug
      })
    }
  }

  return rows
}

export const hopSelectValue = (row: HopModel) => `${row.id} --provider ${row.provider} ${TUI_SESSION_MODEL_FLAG}`

export const modelHopOverlay = (arg: string): false | { refresh?: boolean; sessionOnly?: boolean } | true => {
  const parts = arg.trim().split(/\s+/).filter(Boolean)
  const flags = new Set(parts.filter(p => p.startsWith('--')).map(p => p.toLowerCase()))
  const rest = parts.filter(p => !p.startsWith('--'))

  if (rest.length) {
    return false
  }

  const refresh = flags.has('--refresh')
  const sessionOnly = flags.has('--session') && !flags.has('--global')

  if (sessionOnly) {
    return refresh ? { refresh: true, sessionOnly: true } : { sessionOnly: true }
  }

  if (refresh) {
    return { refresh: true }
  }

  return true
}
