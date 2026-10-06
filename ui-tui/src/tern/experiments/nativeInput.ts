export type FixtureInputPacket =
  | { kind: 'apc'; value: string }
  | { kind: 'key'; value: string }
  | { kind: 'barrier' }

const ESC = '\x1b'
const ST = ESC + '\\'
const KEYS: Record<string, string> = { n: 'next', p: 'previous', r: 'reset', b: 'return-chat', q: 'quit', '\x03': 'quit', '\x04': 'quit' }

/** Incremental terminal demultiplexer. Never treat response bodies or pasted text
 * as navigation keys; in particular, an action payload containing "quit" is data. */
export class NativeFixtureInput {
  private buffer = ''
  private paste = false

  feed(chunk: string): FixtureInputPacket[] {
    if (this.buffer.length + chunk.length > 262144) throw new Error('Terminal input exceeds fixture limit')
    this.buffer += chunk
    const out: FixtureInputPacket[] = []
    while (this.buffer) {
      if (this.paste) {
        const end = this.buffer.indexOf(ESC + '[201~')
        if (end < 0) { this.buffer = this.buffer.slice(-5); break }
        this.buffer = this.buffer.slice(end + 6)
        this.paste = false
        continue
      }
      if (this.buffer[0] !== ESC) {
        const key = KEYS[this.buffer[0]]
        if (key) out.push({ kind: 'key', value: key })
        this.buffer = this.buffer.slice(1)
        continue
      }
      if (this.buffer.length < 2) break
      const prefix = this.buffer[1]
      if (prefix === '_' || prefix === ']' || prefix === 'P') {
        const st = this.buffer.indexOf(ST, 2)
        const bell = prefix === ']' ? this.buffer.indexOf('\x07', 2) : -1
        const end = st < 0 ? bell : bell < 0 ? st : Math.min(st, bell)
        if (end < 0) break
        const body = this.buffer.slice(2, end)
        if (prefix === '_' && body.startsWith('tsp;')) out.push({ kind: 'apc', value: body })
        if (prefix === ']' && body.startsWith('877;tsp;')) out.push({ kind: 'apc', value: body.slice(4) })
        this.buffer = this.buffer.slice(end + (end === st ? 2 : 1))
        continue
      }
      if (prefix === '[') {
        const final = this.buffer.slice(2).search(/[@-~]/)
        if (final < 0) break
        const csi = this.buffer.slice(2, final + 3)
        this.buffer = this.buffer.slice(final + 3)
        if (/^\?[\d;]*c$/.test(csi)) out.push({ kind: 'barrier' })
        else if (csi === '200~') this.paste = true
        else if (csi === 'C' || csi === 'D') out.push({ kind: 'key', value: csi === 'C' ? 'next' : 'previous' })
        else {
          const kitty = /^(\d+)(?:;1(?::[12])?)?u$/.exec(csi)
          const key = kitty && KEYS[String.fromCodePoint(Math.min(Number(kitty[1]), 0x10ffff))]
          if (key) out.push({ kind: 'key', value: key })
        }
        continue
      }
      // Ignore unsupported SS3 and two-byte escape sequences as units.
      if (prefix === 'O' && this.buffer.length < 3) break
      this.buffer = this.buffer.slice(prefix === 'O' ? 3 : 2)
    }
    return out
  }
}
