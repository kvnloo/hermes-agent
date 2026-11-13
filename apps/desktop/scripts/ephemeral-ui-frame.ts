import { build } from 'esbuild'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

/** `virtual:ephemeral-ui-frame` → the vendored ephemeral-ui kit plus its frame
 *  runtime, bundled into ONE classic script string. The card frame is an
 *  opaque-origin srcdoc, so it cannot load modules or sibling files; the
 *  embed inlines this string (and the kit's CSS/data) into the document. */
export function ephemeralUiFrame() {
  const id = 'virtual:ephemeral-ui-frame'
  const resolved = '\0' + id
  const entry = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src/components/assistant-ui/embeds/ephemeral-ui/frame-runtime.js')

  return {
    name: 'ephemeral-ui-frame',
    resolveId: (source: string) => (source === id ? resolved : null),
    async load(this: { addWatchFile: (file: string) => void }, source: string) {
      if (source !== resolved) {
        return null
      }

      const out = await build({
        bundle: true,
        entryPoints: [entry],
        format: 'iife',
        legalComments: 'none',
        metafile: true,
        minify: true,
        target: 'chrome120',
        write: false
      })

      for (const input of Object.keys(out.metafile.inputs)) {
        this.addWatchFile(path.resolve(process.cwd(), input))
      }

      return `export default ${JSON.stringify(out.outputFiles[0].text)}`
    }
  }
}
