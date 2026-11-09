import assert from 'node:assert/strict'
import path from 'node:path'

import { test } from 'vitest'

import { collectSshConfigHosts, parseSshConfigHosts, parseSshConfigIncludes, parseSshGOutput, probeSshG } from './ssh-config'
import { isSshClientFailedBootFailure } from './backend-start-failure'

test('parseSshConfigHosts keeps literal aliases and drops wildcard/negated patterns', () => {
  const cfg = [
    'Host devbox',
    '  HostName 10.0.0.5',
    'Host *.internal prod !staging glob*',
    'Host alpha beta',
    '# Host commented-out',
    'host lower-case'
  ].join('\n')

  assert.deepEqual(parseSshConfigHosts(cfg), ['devbox', 'prod', 'alpha', 'beta', 'lower-case'])
})

test('parseSshConfigHosts de-duplicates', () => {
  assert.deepEqual(parseSshConfigHosts('Host box\nHost box\nHost box other'), ['box', 'other'])
})

test('parseSshConfigIncludes extracts include tokens', () => {
  const cfg = 'Include ~/.ssh/config.d/*\nInclude work_hosts personal_hosts\n# Include ignored'
  assert.deepEqual(parseSshConfigIncludes(cfg), ['~/.ssh/config.d/*', 'work_hosts', 'personal_hosts'])
})

test('collectSshConfigHosts follows Include directives (read-only)', () => {
  const files = {
    '/home/u/.ssh/config': 'Host main\nInclude work\nInclude ~/abs_inc',
    '/home/u/.ssh/work': 'Host work-box\nInclude nested',
    '/home/u/.ssh/nested': 'Host deep',
    '/home/u/abs_inc': 'Host home-abs'
  }

  const hosts = collectSshConfigHosts('/home/u/.ssh/config', {
    homeDir: '/home/u',
    readFile: p => files[p.replaceAll(path.sep, '/')] ?? null
  })

  assert.deepEqual(hosts.sort(), ['deep', 'home-abs', 'main', 'work-box'].sort())
})

test('collectSshConfigHosts tolerates a missing config file', () => {
  assert.deepEqual(collectSshConfigHosts('/nope/config', { homeDir: '/home/u', readFile: () => null }), [])
})

test('collectSshConfigHosts does not loop on a self-include cycle', () => {
  const files = {
    '/home/u/.ssh/config': 'Host a\nInclude loop',
    '/home/u/.ssh/loop': 'Host b\nInclude config' // points back at config
  }

  const hosts = collectSshConfigHosts('/home/u/.ssh/config', {
    homeDir: '/home/u',
    readFile: p => files[p.replaceAll(path.sep, '/')] ?? null
  })

  assert.deepEqual(hosts.sort(), ['a', 'b'])
})

test('collectSshConfigHosts expands globbed includes via injected globSync', () => {
  const files = {
    '/home/u/.ssh/config': 'Host root\nInclude config.d/*',
    '/home/u/.ssh/config.d/10-work': 'Host work',
    '/home/u/.ssh/config.d/20-home': 'Host home'
  }

  const hosts = collectSshConfigHosts('/home/u/.ssh/config', {
    homeDir: '/home/u',
    readFile: p => files[p.replaceAll(path.sep, '/')] ?? null,
    globSync: pattern =>
      pattern.replaceAll(path.sep, '/').endsWith('config.d/*')
        ? ['/home/u/.ssh/config.d/10-work', '/home/u/.ssh/config.d/20-home']
        : [pattern]
  })

  assert.deepEqual(hosts.sort(), ['home', 'root', 'work'].sort())
})

test('parseSshGOutput pulls hostname/user/port/identityfile', () => {
  const out = [
    'host devbox',
    'hostname 10.0.0.5',
    'user alice',
    'port 2222',
    'identityfile ~/.ssh/id_ed25519',
    'forwardagent no'
  ].join('\n')

  assert.deepEqual(parseSshGOutput(out), {
    hostname: '10.0.0.5',
    user: 'alice',
    port: 2222,
    identityFile: '~/.ssh/id_ed25519'
  })
})

test('parseSshGOutput takes the FIRST identityfile and tolerates missing keys', () => {
  const out = 'hostname box\nidentityfile ~/.ssh/a\nidentityfile ~/.ssh/b'
  const parsed = parseSshGOutput(out)
  assert.equal(parsed.identityFile, '~/.ssh/a')
  assert.equal(parsed.user, null)
  assert.equal(parsed.port, null)
})

const killedProbe = Object.assign(new Error('Command failed: ssh -G'), { killed: true, signal: 'SIGTERM' })

test('ssh -G killed on wake retries instead of latching SSH_CLIENT_FAILED (#151462)', async () => {
  let wall = 0
  let calls = 0
  const run = async () => {
    calls++
    if (calls === 1) {
      wall += 1_044_000 // 17 minutes asleep; timeout fires on wake.
      throw killedProbe
    }
    return 'hostname alive'
  }

  assert.equal(await probeSshG('ssh', ['-G', '--', 'alive'], run, () => wall), 'hostname alive')
  assert.equal(calls, 2)
})

test('three short ssh -G timeouts latch rather than retry indefinitely', async () => {
  let wall = 0
  let calls = 0
  const run = async () => {
    calls++
    wall += 10_000
    throw killedProbe
  }

  await assert.rejects(probeSshG('ssh', ['-G', '--', 'hung'], run, () => wall), isSshClientFailedBootFailure)
  assert.equal(calls, 3)
})

test('sleep-affected ssh -G timeouts remain retryable but bounded per attempt', async () => {
  let wall = 0
  let calls = 0
  const run = async () => {
    calls++
    wall += 1_044_000
    throw killedProbe
  }

  await assert.rejects(
    probeSshG('ssh', ['-G', '--', 'suspended'], run, () => wall),
    error => error === killedProbe && !isSshClientFailedBootFailure(error)
  )
  assert.equal(calls, 3)
})

test('ENOENT and ssh -G exit 255 remain terminal without extra probes', async () => {
  const failures = [
    Object.assign(new Error('spawn ssh ENOENT'), { code: 'ENOENT' }),
    Object.assign(new Error('ssh -G exited 255'), { code: 255, killed: false, signal: null })
  ]

  for (const failure of failures) {
    let calls = 0
    await assert.rejects(
      probeSshG('ssh', ['-G', '--', 'bad'], async () => {
        calls++
        throw failure
      }),
      isSshClientFailedBootFailure
    )
    assert.equal(calls, 1)
  }
})

test('ssh -G timeout with a zero-exit SIGTERM handler is still retryable', async () => {
  let calls = 0
  const recovered = await probeSshG('ssh', ['-G', '--', 'alive'], async () => {
    if (++calls === 1) {
      throw Object.assign(new Error('ssh timed out after 10000ms'), { timedOut: true })
    }
    return 'hostname alive'
  })
  assert.equal(recovered, 'hostname alive')
  assert.equal(calls, 2)
})
