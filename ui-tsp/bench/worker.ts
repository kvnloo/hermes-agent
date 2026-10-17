import assert from 'node:assert/strict'
import { cpus, hostname, release } from 'node:os'
import { replay } from './replay.js'

const runs = Number(process.argv.find(a => a.startsWith('--runs='))?.split('=')[1] ?? 1)
for (let run = 0; run < runs; run++) {
  for (const scenario of [{ credits: 1 }, { credits: 8 }, { credits: 1, hidden: true }, { credits: 8, hidden: true }]) {
    const result = await replay(scenario)
    if (process.argv.includes('--assert-win')) {
      if (scenario.hidden) assert.equal(result.hiddenRenders, 0)
      else if (scenario.credits === 1) assert.equal(result.renders, 127)
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
