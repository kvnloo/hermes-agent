/** Copies through OSC 52, which Tern (and most terminals) honor. */
export function copyToClipboard(text: string) {
  process.stdout.write(`\x1b]52;c;${Buffer.from(text).toString('base64')}\x07`)
}
