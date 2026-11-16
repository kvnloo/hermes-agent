// Explicit presentation routes, never inferred from slash output. MCP/SSH
// management is separately unsupported until canonical controls are available.

import type { OperationalView } from '@hermes/shared/gateway-events'

export interface Report {
  title: string
  text: string
  format?: 'plain' | 'markdown'
  status?: 'loading' | 'ready' | 'unavailable' | 'unsupported'
  scope?: string
}

export interface ReportNotice extends Report {
  id: string
  label: string
  failed: boolean
}

interface ReportCommand {
  name: string
  accepts(arg: string): boolean
}

const anyArgument = () => true
const noArgument = (arg: string) => !arg

const REPORT_COMMANDS: readonly ReportCommand[] = [
  { name: 'usage', accepts: anyArgument },
  { name: 'context', accepts: anyArgument },
  { name: 'history', accepts: anyArgument },
  { name: 'tools', accepts: anyArgument },
  { name: 'skills', accepts: anyArgument },
  { name: 'help', accepts: anyArgument },
  { name: 'status', accepts: noArgument },
  { name: 'mcp', accepts: arg => operationalView('mcp', arg) !== undefined },
  { name: 'ssh', accepts: arg => operationalView('ssh', arg) !== undefined }
]

interface OperationalRoute {
  name: string
  arg: string
  view: OperationalView
}

const OPERATIONAL_REPORTS: readonly OperationalRoute[] = [
  { name: 'mcp', arg: '', view: 'mcp-list' },
  { name: 'mcp', arg: 'list', view: 'mcp-list' },
  { name: 'mcp', arg: 'status', view: 'mcp-status' },
  { name: 'mcp', arg: 'tools', view: 'mcp-tools' },
  { name: 'mcp', arg: 'catalog', view: 'mcp-catalog' },
  { name: 'ssh', arg: '', view: 'ssh-list' },
  { name: 'ssh', arg: 'list', view: 'ssh-list' }
]

export function operationalView(name: string, arg: string): OperationalView | undefined {
  return OPERATIONAL_REPORTS.find(route => route.name === name.toLowerCase() && route.arg === arg.trim().toLowerCase())
    ?.view
}

export function isOperationalCommand(name: string): boolean {
  return ['mcp', 'ssh'].includes(name.toLowerCase())
}

export function isReportCommand(name: string, arg: string): boolean {
  return REPORT_COMMANDS.some(command => command.name === name.toLowerCase() && command.accepts(arg))
}
