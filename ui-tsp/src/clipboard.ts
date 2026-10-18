import type { App } from './app.js'

/** Copy the draft literally, without submitting it or disturbing the caret. */
export function copyPrompt(app: App, currentLine = false) {
  const { text, cursor } = app.composer
  const start = text.lastIndexOf('\n', cursor - 1) + 1
  const end = text.indexOf('\n', cursor)

  try {
    copyToClipboard(currentLine ? text.slice(start, end < 0 ? undefined : end) : text)
    // OSC52 has no acknowledgement; don't claim the terminal accepted it.
    app.transcript.notice('Composer text sent to the terminal clipboard (OSC 52).')
  } catch {
    app.transcript.notice('Could not copy the composer text to the clipboard.', 'warning')
  }

  app.changed()
}

/** Copies through OSC 52, which Tern (and most terminals) honor. */
export function copyToClipboard(text: string) {
  process.stdout.write(`\x1b]52;c;${Buffer.from(text).toString('base64')}\x07`)
}
