import { readFile } from 'node:fs/promises';
import { prepareArtifact, createBundle } from '../src/bundle.mjs';
import { bindSelection } from '../../openui-generation/src/host.mjs';
export const document = JSON.parse(await readFile(new URL('../fixtures/repository.json', import.meta.url), 'utf8'));
export const build = { rendererHash: 'b'.repeat(64), bridgeHash: 'c'.repeat(64) };
export function bundle(overrides = {}) {
  const { scope = 'session-a:branch-a', mode = 'code', metrics = ['files', 'code', 'churn'], hottestLimit = 8, doc = document, source = 'synthetic validated selection', presentation = {width: 1280, height: 900, appearance: 'dark'} } = overrides;
  const artifact = prepareArtifact(JSON.stringify(doc), build.rendererHash);
  const selection = bindSelection({ snapshotId: 'demo', mode, metrics, hottestLimit }, source, {scope, snapshots: new Map([['demo', artifact]])});
  return createBundle(selection, artifact, presentation, build.bridgeHash);
}
export const evidence = b => ({schema: 'tern-preview-capture/v1', previewId: b.id, status: 'captured-not-inspected',
  checks: ['synthetic transport check'], shots: [{sha256: 'd'.repeat(64), path: '/synthetic.png'}]});
export const review = {method: 'human-inspected', accepted: true, reviewer: 'Test reviewer'};
export function deferred() { let resolve; const promise = new Promise(r => { resolve = r; }); return {promise, resolve}; }
