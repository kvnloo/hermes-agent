#!/usr/bin/env node
// Real isolated frontend install regression; never mutates a donor node_modules.
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const target = mkdtempSync(join(tmpdir(), 'openui-install-'));
try {
  const archive = execFileSync('git', ['archive', 'HEAD'], { cwd: root, maxBuffer: 256 * 1024 * 1024 });
  execFileSync('tar', ['xf', '-', '-C', target], { input: archive });
  const result = spawnSync(process.argv[2] ?? 'npm', [
    'install', '--ignore-scripts', '--no-audit', '--no-fund', '--package-lock=false', '--workspaces=false',
  ], { cwd: join(target, 'ui-tsp'), encoding: 'utf8', timeout: 120_000 });
  process.stdout.write(result.stdout ?? '');
  process.stderr.write(result.stderr ?? '');
  assert.equal(result.status, 0, 'the real focused frontend install must succeed without Arborist edgesOut');
  console.log('ok - real isolated frontend install (lifecycle scripts disabled)');
} finally {
  rmSync(target, { recursive: true, force: true });
}
