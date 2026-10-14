'use strict'

// Fail closed if these targeted component tests unexpectedly attempt networking.
const forbid = name => function () {
  const error = new Error(`OFFLINE_GUARD: unexpected ${name} call`)
  process.stderr.write(`${error.message}\n`)
  throw error
}

globalThis.fetch = forbid('fetch')
for (const [moduleName, methods] of [
  ['node:http', ['request', 'get']],
  ['node:https', ['request', 'get']],
  ['node:net', ['connect', 'createConnection']],
  ['node:tls', ['connect']],
  ['node:dns', ['lookup', 'resolve']]
]) {
  const module = require(moduleName)
  for (const method of methods) module[method] = forbid(`${moduleName}.${method}`)
}
require('node:net').Socket.prototype.connect = forbid('net.Socket.connect')
require('node:module').syncBuiltinESMExports()
