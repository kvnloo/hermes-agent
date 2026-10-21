import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { digest, freeze, requireInput } from '../../openui-generation/src/catalog.mjs';
import { normalizeDocument } from '../../openui-preview/src/bundle.mjs';
import { runGit } from './git.mjs';

export const LIMITS = freeze({ files: 50_000, blobBytes: 1_048_576, totalBytes: 134_217_728,
  historyBytes: 33_554_432, timeoutMs: 60_000 });
const OBJECT = '(?:[a-f0-9]{40}|[a-f0-9]{64})';
const TREE = new RegExp(`^(\\d{6}) (blob|commit) (${OBJECT}) +([0-9]+|-)$`);
const RAW = new RegExp(`^:\\d{6} \\d{6} ${OBJECT} ${OBJECT} [ACDMRTUXB]$`);
const utf8 = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true });
const safeLabel = text => text.length > 0 && text.length <= 159 &&
  !/[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/.test(text);
const stableId = (kind, path) => `n${digest(`${kind}:${path}`).slice(0, 63)}`;

function bounds(overrides = {}) {
  requireInput(overrides && typeof overrides === 'object' && !Array.isArray(overrides), 'limits', 'Invalid limits.');
  for (const [key, value] of Object.entries(overrides)) requireInput(Object.hasOwn(LIMITS, key) &&
    Number.isSafeInteger(value) && value > 0 && value <= LIMITS[key], 'limits', 'Limits may only lower the host budgets.');
  return { ...LIMITS, ...overrides };
}
function* records(buffer) {
  let offset = 0;
  while (offset < buffer.length) {
    const end = buffer.indexOf(0, offset);
    requireInput(end !== -1, 'git-format', 'Incomplete NUL-delimited Git output.');
    yield buffer.subarray(offset, end); offset = end + 1;
  }
}
function decodePath(bytes) {
  try { return utf8.decode(bytes); } catch { return undefined; }
}
function treeEntries(buffer, limits, excluded) {
  const entries = []; let count = 0;
  for (const record of records(buffer)) {
    requireInput(++count <= limits.files, 'budget', 'Tracked file count exceeds the budget.');
    const tab = record.indexOf(9);
    const match = TREE.exec(record.subarray(0, tab).toString('ascii'));
    requireInput(tab > 0 && match, 'git-format', 'Unexpected ls-tree record.');
    const [, mode, type, oid, sizeText] = match;
    if (type !== 'blob' || !['100644', '100755'].includes(mode)) { excluded.special++; continue; }
    const path = decodePath(record.subarray(tab + 1));
    const parts = path?.split('/');
    if (!parts || parts.length > 16 || !parts.every(safeLabel) || parts.some(p => p === '.' || p === '..')) {
      excluded.unsafePath++; continue;
    }
    const size = Number(sizeText);
    requireInput(Number.isSafeInteger(size) && size >= 0, 'git-format', 'Invalid Git blob size.');
    if (size > limits.blobBytes) { excluded.oversized++; continue; }
    entries.push({ path, parts, oid, size });
  }
  return { entries, count };
}
function countLines(bytes) {
  if (bytes.includes(0)) return undefined;
  try { utf8.decode(bytes); } catch { return undefined; }
  let lines = 0;
  for (const value of bytes) if (value === 10) lines++;
  return lines + (bytes.length > 0 && bytes.at(-1) !== 10 ? 1 : 0);
}
function blobCounts(buffer, objects) {
  const counts = new Map(); let at = 0;
  for (const [oid, size] of objects) {
    const end = buffer.indexOf(10, at);
    requireInput(end >= at && buffer.toString('ascii', at, end) === `${oid} blob ${size}`,
      'git-format', 'Blob response does not match the pinned object.');
    const start = end + 1, next = start + size;
    requireInput(next < buffer.length && buffer[next] === 10, 'git-format', 'Incomplete blob response.');
    counts.set(oid, countLines(buffer.subarray(start, next))); at = next + 1;
  }
  requireInput(at === buffer.length, 'git-format', 'Unexpected trailing blob data.');
  return counts;
}
function churnCounts(buffer, included) {
  const parts = records(buffer), counts = new Map(); let outside = 0, total = 0;
  for (const header of parts) {
    requireInput(RAW.test(header.toString('ascii').replace(/^\n+/, '')), 'git-format', 'Unexpected raw history record.');
    const path = parts.next();
    requireInput(!path.done, 'git-format', 'Missing history path.');
    const name = decodePath(path.value); total++;
    if (included.has(name)) counts.set(name, (counts.get(name) ?? 0) + 1);
    else outside++;
  }
  return { counts, outside, total };
}
function documentTree(entries, lines, touches) {
  const root = { id: 'repo', label: 'tracked UTF-8 files', code: 0, churn: 0, children: [] };
  const directories = new Map([['', root]]);
  for (const entry of [...entries].sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0)) {
    let parent = root, prefix = ''; const ancestors = [root];
    for (const part of entry.parts.slice(0, -1)) {
      prefix += `${part}/`;
      if (!directories.has(prefix)) {
        const dir = { id: stableId('dir', prefix), label: `${part}/`, code: 0, churn: 0, children: [] };
        directories.set(prefix, dir); parent.children.push(dir);
      }
      parent = directories.get(prefix); ancestors.push(parent);
    }
    const node = { id: stableId('file', entry.path), label: entry.parts.at(-1), code: lines.get(entry.oid),
      churn: touches.get(entry.path) ?? 0, children: [] };
    parent.children.push(node);
    for (const dir of ancestors) { dir.code += node.code; dir.churn += node.churn; }
  }
  return root;
}

/** Committed text only. Metrics are host data, never a visual approval or executable UI. */
export async function collectRepository({ cwd, base, head, limits: overrides, signal, execute = runGit }) {
  signal?.throwIfAborted();
  const limits = bounds(overrides);
  requireInput(typeof cwd === 'string' && cwd.length > 0, 'repository', 'Select a local repository explicitly.');
  for (const ref of [base, head]) requireInput(typeof ref === 'string' && ref.length > 0 && ref.length <= 256 &&
    !ref.startsWith('-') && !/[\x00-\x1f\x7f]/.test(ref), 'revision', 'Supply explicit base and head revisions.');
  const stop = signal ? AbortSignal.any([signal, AbortSignal.timeout(limits.timeoutMs)]) : AbortSignal.timeout(limits.timeoutMs);
  const directory = resolve(cwd);
  const git = (args, options = {}) => { stop.throwIfAborted(); return execute(directory, args, { ...options, signal: stop }); };
  const gitVersion = (await git(['--version'])).toString('utf8').trim();
  requireInput((await git(['rev-parse', '--is-shallow-repository'])).toString().trim() === 'false',
    'history', 'Shallow history is not supported; no partial churn is reported.');
  async function commit(ref) {
    const oid = (await git(['rev-parse', '--verify', '--end-of-options', `${ref}^{commit}`])).toString().trim();
    requireInput(new RegExp(`^${OBJECT}$`).test(oid), 'revision', 'Expected a full commit object ID.');
    return oid;
  }
  // Refs are resolved once. All further reads use those immutable object IDs.
  const baseOid = await commit(base), headOid = await commit(head);
  try { await git(['merge-base', '--is-ancestor', baseOid, headOid]); }
  catch (error) { stop.throwIfAborted(); throw new Error('Base must be an available ancestor of head.', { cause: error }); }
  const excluded = { special: 0, unsafePath: 0, oversized: 0, nonText: 0 };
  const tree = await git(['ls-tree', '-r', '-l', '-z', '--full-tree', headOid]);
  const { entries, count: trackedFiles } = treeEntries(tree, limits, excluded);
  const objects = new Map(entries.map(entry => [entry.oid, entry.size]));
  const blobBytesRead = [...objects.values()].reduce((a, b) => a + b, 0);
  requireInput(blobBytesRead <= limits.totalBytes, 'budget', 'Unique blob bytes exceed the budget.');
  const blobs = objects.size ? await git(['cat-file', '--batch'], {
    input: [...objects.keys()].join('\n') + '\n', maxBytes: limits.totalBytes + objects.size * 100 + 1024,
  }) : Buffer.alloc(0);
  const lines = blobCounts(blobs, objects);
  const included = entries.filter(entry => {
    if (lines.get(entry.oid) !== undefined) return true;
    excluded.nonText++; return false;
  });
  const history = await git(['log', '--format=', '--raw', '-z', '--no-abbrev', '--no-renames', '--no-merges',
    '--no-ext-diff', '--no-textconv', '--no-show-signature', '--no-color', headOid, `^${baseOid}`, '--'], { maxBytes: limits.historyBytes });
  const churn = churnCounts(history, new Set(included.map(entry => entry.path)));
  const omitted = Object.values(excluded).reduce((a, b) => a + b, 0);
  const document = normalizeDocument(JSON.stringify({ version: 1,
    title: `Committed UTF-8 lines; churn=file touches ${baseOid.slice(0, 12)}..${headOid.slice(0, 12)}; ${omitted} omitted`,
    root: documentTree(included, lines, churn.counts) }));
  stop.throwIfAborted();
  const source = await Promise.all(['collect.mjs', 'git.mjs'].map(async name => [name, digest(await readFile(new URL(name, import.meta.url)))]));
  const provenance = { schema: 'hermes-git-metrics/v1', status: 'collected-not-verified',
    collectorHash: digest(JSON.stringify(source)), gitVersion, base: baseOid, head: headOid,
    documentHash: digest(JSON.stringify(document)), trackedFiles, includedFiles: included.length, excluded,
    uniqueBlobsRead: objects.size, blobBytesRead, historyRecords: churn.total, historyPathsOutsideView: churn.outside,
    semantics: { code: 'LF-delimited UTF-8 text lines, including comments/blanks and an unterminated final line',
      churn: 'Non-merge commit file touches in base..head for paths present in the included head tree; no rename following',
      scope: 'Committed regular UTF-8 files only; not working-tree data, syntax-aware SLOC, net line churn or visual evidence' }, limits };
  stop.throwIfAborted();
  return freeze({ id: digest(JSON.stringify(provenance)), document, provenance });
}
