import assert from 'node:assert/strict'
import { test as nodeTest, afterEach } from 'node:test'
export { afterEach }
export const test = (name, fn, timeout) => nodeTest(name, { timeout }, fn)
test.each = values => (name, fn, timeout) => {
  for (const value of values) test(name.replace('%s', value), () => fn(value), timeout)
}
export function expect(actual, message) {
  return {
    toBe: expected => assert.strictEqual(actual, expected, message),
    toEqual: expected => assert.deepStrictEqual(actual, expected, message),
    toMatch: expected => assert.match(actual, expected, message),
    toContain: expected => assert.ok(actual.includes(expected), message),
    toBeUndefined: () => assert.strictEqual(actual, undefined, message),
    toBeNull: () => assert.strictEqual(actual, null, message),
    not: {
      toBe: expected => assert.notStrictEqual(actual, expected, message),
      toContain: expected => assert.ok(!actual.includes(expected), message),
    },
  }
}
