// Presentation-only report routing. Unknown commands and mutating forms keep
// their existing transcript behavior; never infer a report from output text.

export interface Report {
  title: string
  text: string
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
  { name: 'btw', accepts: anyArgument },
  { name: 'history', accepts: anyArgument },
  { name: 'tools', accepts: anyArgument },
  { name: 'help', accepts: anyArgument },
  { name: 'status', accepts: noArgument },
  { name: 'mcp', accepts: noArgument }
]

export function isReportCommand(name: string, arg: string): boolean {
  return REPORT_COMMANDS.some(command => command.name === name.toLowerCase() && command.accepts(arg))
}
