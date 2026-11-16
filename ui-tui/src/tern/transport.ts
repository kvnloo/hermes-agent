import { PassThrough } from 'node:stream'

import { connect, type ConnectOptions, type InputItem, InputParser } from '@stencil-hq/tern'

import { TernComposer } from './composer.js'

/** Keep protocol bytes away from Ink's keyboard parser; never discard ordinary key bytes. */
export function filterTernInput(input: NodeJS.ReadStream) {
  const stdin = Object.assign(new PassThrough(), {
    isTTY: input.isTTY,
    setRawMode: (raw: boolean) => input.setRawMode(raw),
    ref: () => input.ref(),
    unref: () => input.unref()
  })

  const parser = new InputParser()
  let timer: ReturnType<typeof setTimeout> | undefined

  const forward = (items: InputItem[]) => {
    for (const item of items) {
      if (item.type === 'keys') {
        stdin.write(item.bytes)
      }
    }
  }

  const onData = (chunk: Buffer | string) => {
    clearTimeout(timer)
    forward(parser.feed(typeof chunk === 'string' ? Buffer.from(chunk) : chunk))

    if (parser.pending) {
      timer = setTimeout(() => forward(parser.flush()), 30)
    }
  }

  input.on('data', onData)

  return {
    stdin: stdin as unknown as NodeJS.ReadStream,
    close() {
      clearTimeout(timer)
      input.off('data', onData)
      stdin.destroy()
    }
  }
}

/** Runs before gateway startup. Only no TSP (or an incompatible hello) returns null. */
export async function probeTern(options: ConnectOptions = {}) {
  const session = await connect({
    app: 'hermes-composer',
    bracketedPaste: false,
    features: ['edit', 'send'], // Undo remains Ink-owned; do not advertise native undo.
    kittyKeyboard: false,
    record: '', // Drafts/credentials must not be recorded through an ambient SDK setting.
    timeout: 700,
    ...options
  })

  if (!session) {
    return null
  }

  if (!session.caps.kinds.includes('editor') || !session.caps.features.includes('dock') || !Number.isSafeInteger(session.caps.credits) ||
      session.caps.credits < 1 || session.caps.credits > 8) {
    await session.close()

    return null
  }

  const composer = new TernComposer(session.open({ id: 'hermes-composer', mode: 'inline' }))

  // Session owns ACKs, negotiation, framing and the bounded replaceable-view slot.
  // Drain unhandled input, including keys also forwarded byte-for-byte to Ink.
  const drain = (async () => {
    for await (const input of session) {
      if (input.type === 'event' && input.event.ev === 'visible') {
        composer.setVisible(input.event.visible)
      }
    }
  })()

  return {
    composer,
    async close() {
      composer.close()
      await session.close()
      await drain
    }
  }
}
