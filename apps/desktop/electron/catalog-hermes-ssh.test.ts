import { mkdtempSync, readFileSync, readdirSync, rmSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { expect, it } from 'vitest'
import { parse as parseYaml } from 'yaml'

import { installDesktopPluginFromGit } from './desktop-plugin-install'
import { PACKAGE_MARKER } from './desktop-plugins-root'

it('installs the reviewed hermes-ssh catalog pin under the package name, not catalog', async () => {
  const here = path.dirname(fileURLToPath(import.meta.url))
  const entry = parseYaml(
    readFileSync(path.resolve(here, '../../../plugin-catalog/hermes-ssh.yaml'), 'utf8')
  ) as { name: string; repo: string; sha: string; subdir: string }

  const desktopPluginsRoot = mkdtempSync(path.join(os.tmpdir(), 'hermes-ssh-catalog-'))
  try {
    const result = await installDesktopPluginFromGit(
      'git',
      `${entry.repo}#${entry.subdir}`,
      desktopPluginsRoot,
      { sha: entry.sha, catalogName: entry.name }
    )

    expect(result).toMatchObject({ ok: true, pluginName: entry.name })
    expect(readdirSync(desktopPluginsRoot)).toEqual([entry.name])
    const marker = JSON.parse(
      readFileSync(path.join(desktopPluginsRoot, entry.name, PACKAGE_MARKER), 'utf8')
    ) as { package: string }
    expect(marker.package).toBe(entry.name)
  } finally {
    rmSync(desktopPluginsRoot, { recursive: true, force: true })
  }
}, 120_000)
