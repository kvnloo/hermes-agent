import assert from 'node:assert/strict'

import { test } from 'vitest'

import { createStreamThrottle, type ThrottleWindowLike } from './stream-throttle'

function makeTimers() {
  const pending = new Map<number, () => void>()
  let nextId = 1

  return {
    clearTimeout: (handle: unknown) => {
      pending.delete(handle as number)
    },
    fire() {
      const jobs = [...pending.values()]
      pending.clear()

      for (const job of jobs) {
        job()
      }
    },
    get pendingCount() {
      return pending.size
    },
    setTimeout: (fn: () => void, _ms: number) => {
      const id = nextId++
      pending.set(id, fn)

      return id
    }
  }
}

function makeWindow(options: { visible?: boolean; minimized?: boolean; throwingProbes?: boolean } = {}) {
  const calls: boolean[] = []
  const listeners = new Map<string, () => void>()
  let destroyed = false
  let visible = options.visible
  let minimized = options.minimized

  const win = {
    calls,
    close() {
      destroyed = true
      listeners.get('closed')?.()
    },
    emit(event: string) {
      listeners.get(event)?.()
    },
    isDestroyed: () => destroyed,
    isMinimized: options.throwingProbes ? () => { throw new Error('probe failed') } : () => minimized === true,
    isVisible: options.throwingProbes ? () => { throw new Error('probe failed') } : () => visible === true,
    on(event: string, fn: () => void) {
      listeners.set(event, fn)
    },
    setMinimized(value: boolean) { minimized = value },
    setVisible(value: boolean) { visible = value },
    webContents: {
      isDestroyed: () => destroyed,
      setBackgroundThrottling(allowed: boolean) {
        calls.push(allowed)
      }
    }
  }

  return win
}

test('registering a window applies the current throttle state immediately', () => {
  const timers = makeTimers()
  const throttle = createStreamThrottle(timers)
  const idle = makeWindow()
  throttle.register(idle)

  // Idle default: throttling allowed.
  assert.deepEqual(idle.calls, [true])

  throttle.update(idle, true)
  const late = makeWindow()
  throttle.register(late)

  // Another renderer's stream does not wake a newly created sibling window.
  assert.deepEqual(late.calls, [true])
  assert.equal(throttle.isUnthrottled(idle), true)
  assert.equal(throttle.isUnthrottled(late), false)
})

test('a turn in flight unthrottles its own window; settling re-throttles after the trailing delay', () => {
  const timers = makeTimers()
  const throttle = createStreamThrottle(timers)
  const win = makeWindow()
  throttle.register(win)

  throttle.update(win, true)
  assert.deepEqual(win.calls, [true, false])
  assert.equal(throttle.isUnthrottled(), true)

  // Turn ends: not re-throttled synchronously — the tail flush needs full
  // cadence — only after the trailing timer fires.
  throttle.update(win, false)
  assert.deepEqual(win.calls, [true, false])
  assert.equal(throttle.isUnthrottled(), true)

  timers.fire()
  assert.deepEqual(win.calls, [true, false, true])
  assert.equal(throttle.isUnthrottled(), false)
})

test('a new turn during the trailing window cancels the pending re-throttle', () => {
  const timers = makeTimers()
  const throttle = createStreamThrottle(timers)
  const win = makeWindow()
  throttle.register(win)

  throttle.update(win, true)
  throttle.update(win, false)
  assert.equal(timers.pendingCount, 1)

  // Busy again before the delay elapses: stay unthrottled, timer cancelled.
  throttle.update(win, true)
  assert.equal(timers.pendingCount, 0)
  assert.equal(throttle.isUnthrottled(), true)

  // The cancelled timer firing late must be a no-op.
  timers.fire()
  assert.equal(throttle.isUnthrottled(), true)
})

test('repeated busy reports do not re-apply or stack timers', () => {
  const timers = makeTimers()
  const throttle = createStreamThrottle(timers)
  const win = makeWindow()
  throttle.register(win)

  throttle.update(win, true)
  throttle.update(win, true)
  throttle.update(win, true)
  assert.deepEqual(win.calls, [true, false])

  throttle.update(win, false)
  throttle.update(win, false)
  assert.equal(timers.pendingCount, 1)
})

test('concurrent windows throttle independently', () => {
  const timers = makeTimers()
  const throttle = createStreamThrottle(timers)
  const first = makeWindow()
  const second = makeWindow()
  throttle.register(first)
  throttle.register(second)

  throttle.update(first, true)
  assert.deepEqual(first.calls, [true, false])
  assert.deepEqual(second.calls, [true])

  throttle.update(second, true)
  throttle.update(first, false)
  assert.equal(timers.pendingCount, 1)
  assert.equal(throttle.isUnthrottled(first), true)
  assert.equal(throttle.isUnthrottled(second), true)

  timers.fire()
  assert.deepEqual(first.calls, [true, false, true])
  assert.deepEqual(second.calls, [true, false])
  assert.equal(throttle.isUnthrottled(first), false)
  assert.equal(throttle.isUnthrottled(second), true)
})

test('visible windows stay unthrottled while idle and busy', () => {
  const throttle = createStreamThrottle(makeTimers())
  const win = makeWindow({ visible: true, minimized: false })
  throttle.register(win)
  throttle.update(win, true)
  assert.deepEqual(win.calls, [false, false])
})

test('hidden and minimized idle windows allow throttling', () => {
  const throttle = createStreamThrottle(makeTimers())
  const hidden = makeWindow({ visible: false })
  const minimized = makeWindow({ visible: true, minimized: true })
  throttle.register(hidden)
  throttle.register(minimized)
  assert.deepEqual(hidden.calls, [true])
  assert.deepEqual(minimized.calls, [true])
})

test('visibility transitions reapply without a busy edge', () => {
  const throttle = createStreamThrottle(makeTimers())
  const win = makeWindow({ visible: true })
  throttle.register(win)
  win.setMinimized(true)
  win.emit('minimize')
  win.setMinimized(false)
  win.emit('restore')
  win.setVisible(false)
  win.emit('hide')
  win.setVisible(true)
  win.emit('show')
  assert.deepEqual(win.calls, [false, true, false, true, false])
})

test('throwing visibility probes fail closed to throttling', () => {
  const throttle = createStreamThrottle(makeTimers())
  const win = makeWindow({ throwingProbes: true })
  throttle.register(win)
  assert.deepEqual(win.calls, [true])
})

test('a visible idle window does not alter a hidden sibling', () => {
  const throttle = createStreamThrottle(makeTimers())
  const visible = makeWindow({ visible: true })
  const hidden = makeWindow({ visible: false })
  throttle.register(visible)
  throttle.register(hidden)
  assert.deepEqual(visible.calls, [false])
  assert.deepEqual(hidden.calls, [true])
})

test('closed and destroyed windows drop out without throwing', () => {
  const timers = makeTimers()
  const throttle = createStreamThrottle(timers)
  const closedWin = makeWindow()
  throttle.register(closedWin)
  closedWin.close()

  const gone: ThrottleWindowLike & { on?: never } = {
    isDestroyed: () => true,
    webContents: null
  }

  throttle.register(gone)

  throttle.update(closedWin, true)
  // Only the registration-time call landed; nothing after close.
  assert.deepEqual(closedWin.calls, [true])
})
