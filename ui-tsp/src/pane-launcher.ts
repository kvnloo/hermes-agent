import { execFile } from 'node:child_process'
import { promisify } from 'node:util'

type PaneProcess = (command: string, args: string[], options: { shell: false }) => Promise<unknown>

/** Launch literal argv, never shell-interpolated conversation/profile text. */
export async function launchPane(argv: readonly string[], execute: PaneProcess = promisify(execFile)): Promise<void> {
  await execute('tern', ['split', '@focused', 'right', '--', ...argv], { shell: false })
}
