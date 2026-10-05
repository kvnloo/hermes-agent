import { describe, expect, it } from 'vitest'

import { decodeTspEvent, decodeTspHello, encodeTspHelloQuery, encodeTspMessage, parseTspApc } from './protocol.js'

describe('Tern Surface Protocol', () => {
  it('encodes the Hermes hello query as a TSP APC frame', () => {
    expect(encodeTspHelloQuery('test-build')).toBe(
      '\x1b_tsp;q;{"q":"hello","v":[1],"app":"hermes","features":["edit","send"],"ver":"test-build"}\x1b\\'
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


describe('TSP events', () => {
  it('decodes native editor edits', () => {
    expect(
      decodeTspEvent('tsp;e;{"ev":"edit","sf":"s:1","id":"composer","from":1,"to":2,"text":"x","cursor":2,"len":4}')
    ).toEqual({
      ev: 'edit',
      sf: 's:1',
      id: 'composer',
      from: 1,
      to: 2,
      text: 'x',
      cursor: 2,
      len: 4
    })
  })

  it('decodes explicit composer sends', () => {
    expect(decodeTspEvent('tsp;e;{"ev":"send","sf":"s:1","id":"composer","text":"hello"}')).toEqual({
      ev: 'send',
      sf: 's:1',
      id: 'composer',
      text: 'hello'
    })
  })

  it('rejects malformed and reply-shaped payloads', () => {
    expect(decodeTspEvent('tsp;e;{"ev":"edit","sf":"s:1","id":"composer","from":"1"}')).toBeNull()
    expect(decodeTspEvent('tsp;r;{"r":"hello","v":1,"term":"tern","kinds":[]}')).toBeNull()
  })
})


describe('TSP framing', () => {
  it('chunks large UTF-8 bodies without splitting surrogate pairs', () => {
    const encoded = encodeTspMessage('f', 'a🙂b🙂c', 5)

    expect(encoded).toContain(';c=')
    expect(encoded).toContain(';m=1;')
    expect(encoded).not.toContain('\ufffd')
  })
})
