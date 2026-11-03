import { describe, expect, it } from 'vitest'

import { diffProcessCpu, labelForProcess, sampleProcessCpu } from './perf/lib/processes.mjs'

describe('labelForProcess', () => {
  it('maps Chromium process types to stable scenario labels', () => {
    expect(labelForProcess({ type: 'browser', name: 'electron' })).toBe('main')
    expect(labelForProcess({ type: 'GPU', name: 'electron' })).toBe('gpu')
    expect(labelForProcess({ type: 'renderer', name: '' })).toBe('renderer')
    expect(labelForProcess({ type: 'zygote', name: 'electron' })).toBe('zygote')
    expect(labelForProcess({ type: 'utility', name: 'network.mojom.NetworkService' })).toBe(
      'network.mojom.NetworkService'
    )
    expect(labelForProcess({ type: 'other', name: 'crashpad' })).toBe('crashpad')
  })
})

// Rows carry no pid in current Chromium, so pairing two samples must go by
// label sums — mispairing by pid once put gpu's total on utility's delta and
// reported a 55-core idle burn that /proc showed was ~1%. The delta is also
// clamped at 0: a GPU child respawn between samples must read as "grew by its
// own usage", never as a negative regression.
describe('diffProcessCpu', () => {
  it('pairs samples by label sum, not by pid', () => {
    const before = [
      { pid: null, label: 'gpu', cpu: 10 },
      { pid: null, label: 'main', cpu: 2 }
    ]
    const after = [
      { pid: null, label: 'gpu', cpu: 11.2 },
      { pid: null, label: 'main', cpu: 2.1 }
    ]

    expect(diffProcessCpu(before, after)).toEqual({ gpu: 1.2, main: 0.1 })
  })

  it('sums same-label rows and clamps a respawned, smaller process at 0', () => {
    const before = [
      { pid: null, label: 'renderer', cpu: 30 },
      { pid: null, label: 'renderer', cpu: 40 }
    ]
    const after = [{ pid: null, label: 'renderer', cpu: 65 }]

    expect(diffProcessCpu(before, after)).toEqual({ renderer: 0 })
  })

  it('a sample snapshot never invents pids when Chromium omits them', async () => {
    // sampleProcessCpu maps rows; without a transport it must return []
    // rather than throw, so the scenario can report "unavailable" instead of guessing.
    await expect(sampleProcessCpu({}, {})).resolves.toEqual([])
  })

  it('preserves GPU CPU-time from a nonempty CDP snapshot and excludes other rows', async () => {
    const sent = []
    const cdp = {
      send: async method => {
        sent.push(method)
        return {
          processInfo: [
            { type: 'browser', processId: 101, cpuTime: 8 },
            { type: 'GPU', cpuTime: 1.5 },
            { type: 'renderer', cpuTime: 2.25 },
            { type: 'other', cpuTime: 99 }
          ]
        }
      }
    }

    await expect(sampleProcessCpu(cdp)).resolves.toEqual([
      { pid: 101, label: 'main', cpu: 8 },
      { pid: null, label: 'gpu', cpu: 1.5 },
      { pid: null, label: 'renderer', cpu: 2.25 }
    ])
    expect(sent).toEqual(['SystemInfo.getProcessInfo'])
  })
})
