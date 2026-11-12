import { describe, expect, it } from 'vitest'

import { shikiGrammarChunkName } from './shiki-chunk-name.mjs'

const lang = name => `/x/node_modules/.pnpm/@shikijs+langs@4.5.0/node_modules/@shikijs/langs/dist/${name}.mjs`
const theme = name => `/x/node_modules/@shikijs/themes/dist/${name}.mjs`

describe('shikiGrammarChunkName', () => {
  it('gives common grammars and the default themes their own chunk', () => {
    expect(shikiGrammarChunkName(lang('bash'))).toBe('shiki-lang-bash')
    expect(shikiGrammarChunkName(lang('typescript'))).toBe('shiki-lang-typescript')
    expect(shikiGrammarChunkName(theme('github-dark-dimmed'))).toBe('shiki-theme-github-dark-dimmed')
  })

  it('buckets the long tail so the file count stays in the tens', () => {
    expect(shikiGrammarChunkName(lang('haskell'))).toBe('shiki-langs-h')
    expect(shikiGrammarChunkName(lang('1c-query'))).toBe('shiki-langs-0')
    expect(shikiGrammarChunkName(theme('dracula'))).toBe('shiki-themes')
  })

  it('leaves everything else to the next group', () => {
    expect(shikiGrammarChunkName('/x/node_modules/@shikijs/core/dist/index.mjs')).toBeNull()
    expect(shikiGrammarChunkName(lang('bash').replace('.mjs', '.d.mts'))).toBeNull()
  })
})
