import classic from './classic-commands.generated.json' with { type: 'json' }

/** Generated from hermes_cli.commands.COMMAND_REGISTRY; never author aliases here. */
export const CLASSIC_COMMANDS = classic
const canonical = new Map(classic.flatMap(command =>
  [command.name, ...command.aliases].map(name => [name, command.name] as const)))

export function canonicalCommand(name: string): string {
  const key = name.toLowerCase().replace(/^\//, '')

  return canonical.get(key) ?? key
}
