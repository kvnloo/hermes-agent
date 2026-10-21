// Assistant answer actions use the text the user can read, not reasoning, tools or usage.
// Clipboard transport remains the caller's responsibility; never let it break a turn.

import type { TurnEntry } from './model.js'

/** Match OMP's answer copy: nonempty text blocks, trimmed, a blank line apart. */
export function answerText(turn: TurnEntry): string {
  return turn.blocks
    .filter(block => block.kind === 'text' && block.text.trim())
    .map(block => block.kind === 'text' ? block.text.trim() : '')
    .join('\n\n')
}

/** A failed clipboard write is a nonfatal, transient UI notice. */
export function copyAnswer(turn: TurnEntry, copy: (text: string) => void, notice: () => void): void {
  if (turn.status === 'live') {
    return
  }

  const text = answerText(turn)

  if (!text) {
    return
  }

  try {
    copy(text)
  } catch {
    notice()
  }
}
