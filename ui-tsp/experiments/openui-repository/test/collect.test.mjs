import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtemp, mkdir, writeFile, readFile, symlink, rm } from 'node:fs/promises';
import { tmpdir, devNull } from 'node:os';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { collectRepository } from '../src/collect.mjs';
import { runGit } from '../src/git.mjs';
import { normalizeDocument, prepareArtifact, createBundle } from '../../openui-preview/src/bundle.mjs';
import { bindSelection } from '../../openui-generation/src/host.mjs';

const git = (cwd, ...args) => execFileSync('git', ['-C', cwd, ...args], {
  encoding: 'utf8', env: { ...process.env, GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: devNull,
    GIT_AUTHOR_NAME: 'Fixture', GIT_AUTHOR_EMAIL: 'fixture@example.invalid',
    GIT_COMMITTER_NAME: 'Fixture', GIT_COMMITTER_EMAIL: 'fixture@example.invalid' },
}).trim();
async function repository(t) {
  const cwd = await mkdtemp(join(tmpdir(), 'openui-repo-test-'));
  t.after(() => rm(cwd, { recursive: true, force: true }));
  git(cwd, 'init', '-q');
  git(cwd, 'commit', '-q', '--allow-empty', '-m', 'base');
  const base = git(cwd, 'rev-parse', 'HEAD');
  const put = async (path, data) => {
    const parts = path.split('/'); parts.pop();
    await mkdir(join(cwd, ...parts), { recursive: true });
    await writeFile(join(cwd, path), data);
  };
  const commit = () => { git(cwd, 'add', '.'); git(cwd, 'commit', '-qm', 'fixture'); return git(cwd, 'rev-parse', 'HEAD'); };
  return { cwd, base, put, commit };
}
function leaves(document) {
  const rows = new Map();
  function visit(node, parent) {
    for (const child of node.children) {
      const path = parent + child.label;
      if (child.children.length) visit(child, path);
      else rows.set(path, child);
    }
  }
  visit(document.root, ''); return rows;
}

test('reads pinned committed blobs, not dirty, staged, untracked or symlink targets', async t => {
  const r = await repository(t);
  await r.put('src/a.ts', 'one\ntwo\n');
  await r.put('empty.txt', '');
  await r.put('binary.bin', Buffer.from([0, 1, 10, 2]));
  await r.put('legacy.txt', Buffer.from([0xff, 0xfe]));
  await symlink('/definitely-not-readable-openui-target', join(r.cwd, 'link'));
  const head = r.commit();
  await r.put('src/a.ts', 'dirty\n'.repeat(50)); git(r.cwd, 'add', 'src/a.ts');
  await r.put('untracked-secret.txt', 'DO_NOT_INCLUDE\n');
  const status = git(r.cwd, 'status', '--porcelain');
  const result = await collectRepository({ cwd: r.cwd, base: r.base, head });
  const files = leaves(result.document);
  assert.equal(files.get('src/a.ts').code, 2);
  assert.equal(files.get('empty.txt').code, 0);
  assert.equal(files.size, 2);
  assert.equal(result.provenance.excluded.special, 1);
  assert.equal(result.provenance.excluded.nonText, 2);
  assert.equal(result.document.root.churn, 2);
  assert.equal(JSON.stringify(result).includes('DO_NOT_INCLUDE'), false);
  assert.equal(git(r.cwd, 'status', '--porcelain'), status);
  assert.deepEqual(normalizeDocument(JSON.stringify(result.document)), result.document);
});

test('counts file touches over the exact range, including changes later reverted', async t => {
  const r = await repository(t);
  await r.put('a.txt', 'first\n'); r.commit();
  await r.put('a.txt', 'second\n'); r.commit();
  await r.put('a.txt', 'first\n'); const head = r.commit();
  const result = await collectRepository({ cwd: r.cwd, base: r.base, head });
  assert.equal(leaves(result.document).get('a.txt').churn, 3);
  assert.equal(leaves(result.document).get('a.txt').code, 1);
  assert.equal(result.provenance.base, r.base);
  assert.equal(result.provenance.head, head);
});

test('stable IDs, exact aggregates, valid unusual labels and unterminated lines', async t => {
  const r = await repository(t);
  for (const path of ['src/space name.ts', 'src/日本語.ts', 'src/__proto__', '-option.txt']) await r.put(path, 'a\r\nb');
  const head = r.commit();
  const first = await collectRepository({ cwd: r.cwd, base: r.base, head });
  const again = await collectRepository({ cwd: join(r.cwd, 'src'), base: r.base, head });
  assert.deepEqual(first, again);
  assert.equal(first.document.root.code, 8);
  assert.equal(first.document.root.churn, 4);
  assert.equal(new Set([...leaves(first.document).values()].map(row => row.id)).size, 4);
  await r.put('another.txt', 'x\n'); const newer = r.commit();
  const next = await collectRepository({ cwd: r.cwd, base: r.base, head: newer });
  assert.equal(leaves(first.document).get('src/日本語.ts').id, leaves(next.document).get('src/日本語.ts').id);
  assert.notEqual(first.id, next.id);
  assert.equal(Object.isFrozen(first.document.root), true);
});

test('batch-reads each unique object once, with process count independent of file count', async t => {
  const r = await repository(t);
  for (let i = 0; i < 80; i++) await r.put(`src/f${i}.txt`, 'shared\n');
  const head = r.commit(); const calls = [];
  const execute = (cwd, args, options) => { calls.push(args); return runGit(cwd, args, options); };
  const result = await collectRepository({ cwd: r.cwd, base: r.base, head, execute });
  assert.equal(result.provenance.includedFiles, 80);
  assert.equal(result.provenance.uniqueBlobsRead, 1);
  assert.equal(result.provenance.blobBytesRead, 7);
  assert.equal(calls.filter(args => args[0] === 'cat-file').length, 1);
  assert.equal(calls.filter(args => args[0] === 'log').length, 1);
  assert.equal(calls.length, 8);
});

test('exclusions are explicit; control-character filenames never become protocol input', async t => {
  const r = await repository(t);
  await r.put('good.txt', 'x'); await r.put('bad\nname.txt', 'x');
  await r.put('huge.txt', '123456789'); const head = r.commit();
  const result = await collectRepository({ cwd: r.cwd, base: r.base, head, limits: { blobBytes: 8 } });
  assert.equal(result.provenance.excluded.unsafePath, 1);
  assert.equal(result.provenance.excluded.oversized, 1);
  assert.equal(result.provenance.includedFiles, 1);
  assert.match(result.document.title, /2 omitted/);
});

test('rejects incomplete history, non-ancestor base, invalid refs and resource overruns', async t => {
  const r = await repository(t);
  await r.put('a.txt', '12345'); const head = r.commit();
  await assert.rejects(collectRepository({ cwd: r.cwd, base: 'missing-ref', head }));
  await assert.rejects(collectRepository({ cwd: r.cwd, base: '--help', head }));
  await assert.rejects(collectRepository({ cwd: r.cwd, base: r.base, head, limits: { totalBytes: 4 } }), /budget/i);
  await assert.rejects(collectRepository({ cwd: r.cwd, base: r.base, head, limits: { historyBytes: 8 } }), /budget/i);
  await assert.rejects(collectRepository({ cwd: r.cwd, base: head, head: r.base }), /ancestor/i);
  await writeFile(join(r.cwd, '.git', 'shallow'), `${head}\n`);
  await assert.rejects(collectRepository({ cwd: r.cwd, base: r.base, head }), /shallow/i);
});

test('same base/head is valid zero churn; deleted/renamed paths do not inflate current totals', async t => {
  const r = await repository(t);
  await r.put('old.txt', 'one\n'); const before = r.commit();
  git(r.cwd, 'mv', 'old.txt', 'new.txt'); const head = r.commit();
  const result = await collectRepository({ cwd: r.cwd, base: before, head });
  assert.equal(leaves(result.document).get('new.txt').churn, 1);
  assert.equal(result.provenance.historyPathsOutsideView, 1);
  const unchanged = await collectRepository({ cwd: r.cwd, base: head, head });
  assert.equal(unchanged.document.root.churn, 0);
});

test('feeds the existing generation binding and preview bundle without a new schema', async t => {
  const r = await repository(t);
  await r.put('src/a.ts', 'a\n'); const head = r.commit();
  const snapshot = await collectRepository({ cwd: r.cwd, base: r.base, head });
  const artifact = prepareArtifact(JSON.stringify(snapshot.document), 'a'.repeat(64));
  const selection = bindSelection({ snapshotId: 'demo', mode: 'code', metrics: ['files', 'code', 'churn'], hottestLimit: 6 },
    'host integration fixture', { scope: 'test:branch', snapshots: new Map([['demo', artifact]]) });
  const bundle = createBundle(selection, artifact, { width: 1000, height: 650, appearance: 'dark' }, 'b'.repeat(64));
  assert.equal(bundle.artifact.document.root.code, 1);
  assert.equal(bundle.selection.status, 'validated-not-verified');
  assert.equal(bundle.artifact.document.title, snapshot.document.title);
});

test('cancellation stops before subprocess creation', async t => {
  const r = await repository(t); let invoked = false;
  await assert.rejects(collectRepository({ cwd: r.cwd, base: r.base, head: r.base,
    signal: AbortSignal.abort(), execute: () => { invoked = true; throw new Error('must not run'); } }), { name: 'AbortError' });
  assert.equal(invoked, false);
});

test('ref movement after resolution cannot change the collected snapshot', async t => {
  const r = await repository(t); await r.put('a.txt', 'first\n'); const pinned = r.commit();
  let moved = false;
  const execute = async (cwd, args, options) => {
    if (args[0] === 'ls-tree' && !moved) { moved = true; await r.put('a.txt', 'next\nextra\n'); r.commit(); }
    return runGit(cwd, args, options);
  };
  const result = await collectRepository({ cwd: r.cwd, base: r.base, head: 'HEAD', execute });
  assert.equal(result.provenance.head, pinned);
  assert.equal(result.document.root.code, 1);
  assert.equal(result.document.root.churn, 1);
  assert.notEqual(git(r.cwd, 'rev-parse', 'HEAD'), pinned);
});

test('ambient Git overrides and configured diff helpers do not redirect or execute', async t => {
  const r = await repository(t); await r.put('a.txt', 'first\n'); const head = r.commit();
  git(r.cwd, 'config', 'diff.external', 'this-executable-must-never-run');
  const old = process.env.GIT_DIR; process.env.GIT_DIR = '/missing-other-repository';
  try {
    const result = await collectRepository({ cwd: r.cwd, base: r.base, head });
    assert.equal(result.document.root.code, 1);
  } finally { if (old === undefined) delete process.env.GIT_DIR; else process.env.GIT_DIR = old; }
});

test('CLI writes a private compatible document and bound provenance, without overwriting runs', async t => {
  const r = await repository(t); await r.put('src/a.txt', 'first\n'); const head = r.commit();
  const out = join(r.cwd, 'output');
  const cli = fileURLToPath(new URL('../cli.mjs', import.meta.url));
  const path = execFileSync(process.execPath, [cli, r.cwd, r.base, head, out], { encoding: 'utf8' }).trim();
  const document = normalizeDocument(await readFile(path, 'utf8'));
  const { digest } = await import('../../openui-generation/src/catalog.mjs');
  const { stat } = await import('node:fs/promises');
  const { dirname } = await import('node:path');
  const meta = JSON.parse(await readFile(join(dirname(path), 'provenance.json'), 'utf8'));
  assert.equal(meta.documentHash, digest(JSON.stringify(document)));
  assert.equal(meta.head, head);
  assert.equal((await stat(path)).mode & 0o777, 0o600);
  const other = execFileSync(process.execPath, [cli, r.cwd, r.base, head, out], { encoding: 'utf8' }).trim();
  assert.notEqual(path, other);
  assert.deepEqual(await readFile(path), await readFile(other));
});

test('reuses the existing output-directory guard for watched sources', async t => {
  const r = await repository(t);
  const { saveRepository } = await import('../cli.mjs');
  await assert.rejects(saveRepository({ cwd: r.cwd, base: r.base, head: r.base },
    fileURLToPath(new URL('../unsafe-output', import.meta.url))), /outside experiment/i);
});

test('process-level cancellation terminates an active Git batch', async t => {
  const r = await repository(t); const controller = new AbortController();
  const pending = runGit(r.cwd, ['hash-object', '--stdin'], { input: Buffer.alloc(16 * 1024 * 1024, 120), signal: controller.signal });
  controller.abort();
  await assert.rejects(pending, { name: 'AbortError' });
});
