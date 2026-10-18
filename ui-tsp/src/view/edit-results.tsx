import type { JSX } from '@stencil-hq/tern'

import { displayText } from '../display-text.js'
import { fileHref } from '../links.js'

interface FileDiff {
  path: string
  text: string
}

/** Hermes V4A emits concatenated difflib sections, not one anonymous hunk. */
export function fileDiffs(raw: string | undefined): FileDiff[] {
  if (!raw) { return [] }
  const lines = raw.split('\n')
  const files: FileDiff[] = []
  let current: FileDiff | undefined
  let oldLines = 0
  let newLines = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? ''
    const next = lines[i + 1] ?? ''

    if (oldLines <= 0 && newLines <= 0 && line.startsWith('--- ') && next.startsWith('+++ ')) {
      const target = next.slice(4)
      const path = target === '/dev/null' ? line.slice(4).replace(/^a\//, '') : target.replace(/^b\//, '')
      current = { path, text: '' }
      files.push(current)
      i++
    } else if (current) {
      const hunk = /^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@/.exec(line)

      if (hunk) {
        oldLines = hunk[1] === undefined ? 1 : Number(hunk[1])
        newLines = hunk[2] === undefined ? 1 : Number(hunk[2])
      } else {
        if (line.startsWith('-') || line.startsWith(' ')) { oldLines-- }

        if (line.startsWith('+') || line.startsWith(' ')) { newLines-- }
      }

      current.text += (current.text ? '\n' : '') + line
    }
  }

  return files
}

export function changedFiles(result: Record<string, unknown> | undefined): string[] {
  return [...new Set(['files_modified', 'files_created', 'files_deleted'].flatMap(key => {
    const paths = result?.[key]

    return Array.isArray(paths) ? paths.filter((path): path is string => typeof path === 'string') : []
  }))]
}

export function editFiles(files: FileDiff[], paths: string[], cwd: string): JSX.Element[] {
  return [...new Set([...paths, ...files.map(file => file.path)])].map((path, i) => {
    const file = files.find(file => file.path === path)
    const first = /@@ -\d+(?:,\d+)? \+(\d+)/.exec(file?.text ?? '')
    const href = fileHref(path, cwd, first ? { line: Number(first[1]) } : undefined)

    return <col key={`edit-file-${i}`} role="omp.tool.edit.file">
      <text href={href} key="path" role="omp.tool.file" text={displayText(path)} />
      {file?.text ? <diff key="diff" text={displayText(file.text)} /> : null}
    </col>
  })
}
