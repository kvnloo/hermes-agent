import { EXPERIMENT_VIEWPORTS, TERN_UX_FIXTURE, TERN_UX_FIXTURE_VERSION } from '../../src/tern/experiments/fixture.js'
import { NativeFixtureInput } from '../../src/tern/experiments/nativeInput.js'
import { NativeFixtureSession } from '../../src/tern/experiments/nativeSession.js'
import { INITIAL_NATIVE_FIXTURE, NATIVE_FIXTURE_REVISION, renderNativeFixture } from '../../src/tern/experiments/nativeView.js'
import type { TspHello } from '../../src/tern/protocol.js'

const args = process.argv.slice(2)
if ((args.length > 0 && !['--dump', '--help'].includes(args[0])) || args.length > 1) {
  process.stderr.write('Usage: npm run tern:ux:preview --workspace ui-tui -- [--dump|--help]\n')
  process.exitCode = 2
} else if (args[0] === '--help') {
  process.stdout.write('Native Tern fixture, not a live Hermes session. Next n / Previous p / Back b / Reset r / Quit q.\n--dump writes all 14 semantic views without a terminal or model calls.\n')
} else if (args[0] === '--dump') {
  process.stdout.write(JSON.stringify({
    fixtureVersion: TERN_UX_FIXTURE_VERSION,
    presentationRevision: NATIVE_FIXTURE_REVISION,
    variant: 'omp-baseline',
    evidence: 'synthetic semantic documents, not screenshots or measured attention results',
    viewportsToCapture: EXPERIMENT_VIEWPORTS,
    limitations: ['read-only composer', 'local simulated controls', 'file preview is not a host split'],
    views: TERN_UX_FIXTURE.map((step, index) => ({ stepId: step.id, view: renderNativeFixture({ ...INITIAL_NATIVE_FIXTURE, step: index }) }))
  }, null, 2) + '\n')
} else if (!process.stdin.isTTY || !process.stdout.isTTY) {
  process.stderr.write('Native preview requires a real Tern TTY. Use --dump for offline semantic documents.\n')
  process.exitCode = 1
} else if (process.env.TMUX || process.env.STY || process.env.ZELLIJ) {
  process.stderr.write('Run the native preview directly in Tern, outside tmux/screen/zellij.\n')
  process.exitCode = 1
} else {
  await runNativePreview()
}

async function runNativePreview(): Promise<void> {
  // Reuse the existing Hermes wire kernel, not the incomplete live composer hook.
  const { decodeTspEvent, decodeTspHello, encodeTspJson, parseTspApc } = await import('../../src/tern/protocol.js')
  const input = new NativeFixtureInput()
  const wasRaw = process.stdin.isRaw
  const encoding = process.stdin.readableEncoding
  let phase: 'probe' | 'active' | 'drain' | 'done' = 'probe'
  let hello: TspHello | null = null
  let session: NativeFixtureSession | null = null
  let barriers = 0
  let timer: ReturnType<typeof setTimeout> | undefined
  let message = ''

  const barrier = () => { barriers++; process.stdout.write('\x1b[c') }
  const restore = () => {
    if (phase === 'done') return
    phase = 'done'
    clearTimeout(timer)
    process.stdin.off('data', data)
    process.stdin.off('end', ended)
    process.off('SIGINT', signalled)
    process.off('SIGTERM', signalled)
    process.stdout.write('\x1b[?2004l')
    process.stdin.setRawMode(wasRaw)
    process.stdin.setEncoding(encoding ?? undefined)
    process.stdin.pause()
    if (message) process.stderr.write(message.replace(/[\x00-\x1f\x7f-\x9f]/g, ' ') + '\n')
  }
  const close = (reason = '') => {
    if (phase === 'done' || phase === 'drain') return
    phase = 'drain'
    clearTimeout(timer)
    message = reason
    if (reason) process.exitCode = 1
    session?.close()
    // Keep raw input and the decoder alive through a post-close DA1 barrier.
    barrier()
    timer = setTimeout(() => {
      message ||= 'Preview closed, but the terminal did not confirm the close-drain barrier.'
      process.exitCode = 1
      restore()
    }, 800)
  }
  const signalled = () => close()
  const ended = () => { session?.close(); restore() }
  const data = (chunk: string) => {
    try {
      for (const packet of input.feed(chunk)) {
        if (packet.kind === 'barrier') {
          barriers = Math.max(0, barriers - 1)
          if (phase === 'drain' && barriers === 0) { restore(); return }
          if (phase === 'probe') {
            clearTimeout(timer)
            if (!hello) { close('TSP is unavailable or disabled; no native fixture was opened.'); continue }
            const limit = Math.min(hello.apc ?? 65536, 65536)
            session = new NativeFixtureSession(hello, (verb, value) => process.stdout.write(encodeTspJson(verb, value, limit)))
            phase = 'active'
            session.start()
          }
        } else if (packet.kind === 'apc' && phase !== 'drain') {
          const envelope = parseTspApc(packet.value)
          if (envelope?.params.c) { close('Chunked terminal replies are not supported by this fixture viewer.'); continue }
          if (phase === 'probe') hello = decodeTspHello(packet.value) ?? hello
          else if (phase === 'active') {
            const event = decodeTspEvent(packet.value)
            const result = event && session?.event(event)
            if (result === 'quit') close()
            else if (result === 'invalidated') close('Tern invalidated the fixture document. Restart the preview; no live Hermes state was affected.')
          }
        } else if (packet.kind === 'key') {
          if (packet.value === 'quit') close()
          else if (phase === 'active') session?.dispatch(packet.value)
        }
      }
    } catch (error) {
      close(error instanceof Error ? error.message : 'Native fixture failed')
    }
  }
  process.stdin.setEncoding('utf8')
  process.stdin.setRawMode(true)
  process.stdin.on('data', data)
  process.stdin.on('end', ended)
  process.on('SIGINT', signalled)
  process.on('SIGTERM', signalled)
  process.stdin.resume()
  process.stdout.write('\x1b[?2004h')
  // Read-only fixture: never advertise edit, undo, send or runtime capabilities.
  process.stdout.write(encodeTspJson('q', { q: 'hello', v: [1], app: 'hermes-ux-fixture', features: [] }))
  barrier()
  timer = setTimeout(() => close('Tern did not complete TSP negotiation. Use --dump for offline inspection.'), 1500)
}
