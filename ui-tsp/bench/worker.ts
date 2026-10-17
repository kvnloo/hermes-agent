import assert from 'node:assert/strict'
import { cpus, hostname, release } from 'node:os'
import { replay } from './replay.js'

const retention = process.argv.includes('--retention')
// Warm App/SDK/JIT equally before measuring either history size, not by always timing 200 first.
if (retention) await replay({ retention: true, history: 200, deltas: 5000 })
const runs = Number(process.argv.find(a => a.startsWith('--runs='))?.split('=')[1] ?? 1)
for (let run = 0; run < runs; run++) {
  const scenarios: Parameters<typeof replay>[0][] = retention
    ? [200, 2000].map(history => ({ credits: 1, history, retention: true }))
    : [{ credits: 1 }, { credits: 8 }, { credits: 1, hidden: true }, { credits: 8, hidden: true }]
  if (process.argv.includes('--reverse-history') || (retention && run % 2)) scenarios.reverse()
  for (const scenario of scenarios) {
    const result = await replay(scenario)
    if (process.argv.includes('--assert-win')) {
      if (scenario?.hidden) assert.equal(result.hiddenRenders, 0)
      else if (scenario?.credits === 1) assert.equal(result.renders, 127)
    }
    console.log(
      JSON.stringify({
        run,
        node: process.version,
        machine: hostname(),
        cpu: cpus()[0]?.model,
        kernel: release(),
        ...result
      })
    )
  }
}
