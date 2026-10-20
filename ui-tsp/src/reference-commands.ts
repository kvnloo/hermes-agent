/** Native-only snapshot views: discoverable in /help and slash completion. */
export const REFERENCE_COMMANDS = [
  ['/map', 'Inspect Graphify symbols and code links from the project snapshot (read only)'],
  ['/machine', 'Inspect the explicit machine-health snapshot (read only, not live)'],
  ['/host-health', 'Alias for /machine']
] as const
