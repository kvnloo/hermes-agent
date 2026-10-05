import { describe, expect, it } from 'vitest'

import { decodeTspHello, encodeTspHelloQuery, parseTspApc } from './protocol.js'

describe('Tern Surface Protocol', () => {
  it('encodes the Hermes hello query as a TSP APC frame', () => {
    expect(encodeTspHelloQuery('test-build')).toBe(
      '\x1b_tsp;q;{"q":"hello","v":[1],"app":"hermes","features":[],"ver":"test-build"}\x1b\\'
    )
  })

  it('parses params without consuming the JSON body', () => {
    expect(parseTspApc('tsp;r;c=abc;m=1;{"r":"hello"}')).toEqual({
      verb: 'r',
      params: { c: 'abc', m: '1' },
      body: '{"r":"hello"}'
    })
  })

  it('decodes a valid TSP hello reply', () => {
    expect(
      decodeTspHello('tsp;r;{"r":"hello","v":1,"term":"tern","kinds":["screen","dock"],"credits":2}')
    ).toEqual({
      r: 'hello',
      v: 1,
      term: 'tern',
      kinds: ['screen', 'dock'],
      credits: 2
    })
  })

  it('rejects unrelated APC payloads and malformed hello replies', () => {
    expect(parseTspApc('kitty;G,a=q')).toBeNull()
    expect(decodeTspHello('tsp;r;{"r":"hello","v":"1","term":"tern","kinds":[]}')).toBeNull()
  })
})
