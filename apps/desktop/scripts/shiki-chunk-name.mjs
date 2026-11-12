// Chunk naming for shiki's grammar/theme modules (vite.config.ts advancedChunks).
// Each grammar/theme is a lazy import inside shiki; this keeps them out of the
// one big `shiki` chunk so a highlighted block only evaluates what it uses.

// Languages agents actually emit, plus the default themes (shiki-config.ts).
// Each gets a chunk of its own; everything else shares a per-initial bucket.
const OWN_CHUNK = new Set([
  'bash', 'shellscript', 'python', 'typescript', 'tsx', 'javascript', 'jsx', 'json', 'jsonc',
  'diff', 'markdown', 'yaml', 'toml', 'rust', 'go', 'sql', 'css', 'html', 'github-dark-dimmed',
  'github-light-default'
])

const MODULE = /[\\/]@shikijs[\\/](langs|themes)[\\/]dist[\\/]([^\\/]+)\.mjs$/

/** @param {string} id */
export function shikiGrammarChunkName(id) {
  const match = MODULE.exec(id)

  if (!match) {
    return null
  }

  const [, kind, name] = match

  if (OWN_CHUNK.has(name)) {
    return `shiki-${kind === 'langs' ? 'lang' : 'theme'}-${name}`
  }

  // Themes are few and small; the long tail of grammars buckets by initial.
  return kind === 'themes' ? 'shiki-themes' : `shiki-langs-${/[a-z]/.test(name[0]) ? name[0] : '0'}`
}
