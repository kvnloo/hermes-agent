import { spawn } from 'node:child_process';
import { devNull } from 'node:os';

/** Read-only Git plumbing, with no shell, external diff/textconv or lazy fetch. */
export function runGit(cwd, args, { input, maxBytes = 16 * 1024 * 1024, signal } = {}) {
  signal?.throwIfAborted();
  // Ambient GIT_DIR/INDEX_FILE/CONFIG_COUNT must not redirect the selected repository.
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.toUpperCase().startsWith('GIT_')));
  Object.assign(env, { GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: devNull,
    GIT_NO_LAZY_FETCH: '1', GIT_TERMINAL_PROMPT: '0', GIT_ATTR_NOSYSTEM: '1' });
  return new Promise((resolve, reject) => {
    const child = spawn('git', ['--no-pager', '--no-optional-locks', '--no-replace-objects',
      '-c', 'protocol.allow=never', '-c', 'core.fsmonitor=false',
      '-c', `core.attributesFile=${devNull}`, ...args], { cwd, env, signal, killSignal: 'SIGKILL', stdio: 'pipe' });
    const output = [], errors = [];
    let bytes = 0, errorBytes = 0, failure;
    const fail = error => { failure ??= error; child.kill('SIGKILL'); };
    child.on('error', fail);
    child.stdin.on('error', fail);
    child.stdout.on('data', chunk => {
      bytes += chunk.length;
      if (bytes > maxBytes) fail(new Error('Git output exceeded the byte budget; no partial snapshot is returned.'));
      else if (!failure) output.push(chunk);
    });
    child.stderr.on('data', chunk => {
      errorBytes += chunk.length;
      if (errorBytes > 65_536) fail(new Error('Git diagnostics exceeded the byte budget.'));
      else errors.push(chunk);
    });
    child.on('close', code => {
      if (signal?.aborted) return reject(signal.reason);
      if (failure) return reject(failure);
      const diagnostic = Buffer.concat(errors).toString('utf8').trim();
      if (code !== 0 || diagnostic) return reject(new Error(`Git ${args[0]} failed (${code}): ${diagnostic.slice(0, 512)}`));
      resolve(Buffer.concat(output, bytes));
    });
    child.stdin.end(input);
  });
}
