import { mkdir, mkdtemp, writeFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { collectRepository } from './src/collect.mjs';
import { assertOutputDirectory } from '../openui-preview/src/bundle.mjs';

/** Writes only into a new private directory outside the watched experiment sources. */
export async function saveRepository(options, outputDirectory) {
  const root = await assertOutputDirectory(outputDirectory);
  const result = await collectRepository(options);
  options.signal?.throwIfAborted();
  await mkdir(root, { recursive: true, mode: 0o700 });
  const directory = await mkdtemp(join(root, 'snapshot-'));
  try {
    const path = join(directory, 'repository.json');
    await writeFile(path, JSON.stringify(result.document) + '\n', { flag: 'wx', mode: 0o600 });
    await writeFile(join(directory, 'provenance.json'), JSON.stringify({ id: result.id, ...result.provenance }, null, 2) + '\n',
      { flag: 'wx', mode: 0o600 });
    options.signal?.throwIfAborted();
    return path;
  } catch (error) {
    await rm(directory, { recursive: true, force: true });
    throw error;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [cwd, base, head, out, ...extra] = process.argv.slice(2);
  const controller = new AbortController();
  const cancel = () => controller.abort();
  process.once('SIGINT', cancel); process.once('SIGTERM', cancel);
  try {
    if (!cwd || !base || !head || !out || extra.length) throw new Error('Usage: node cli.mjs REPOSITORY BASE HEAD OUTPUT_DIRECTORY');
    console.log(await saveRepository({ cwd, base, head, signal: controller.signal }, out));
  } catch (error) { console.error(error.message); process.exitCode = 1; }
  finally { process.removeListener('SIGINT', cancel); process.removeListener('SIGTERM', cancel); }
}
