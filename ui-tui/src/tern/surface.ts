import { useStdin } from '@hermes/ink'
import { atom } from 'nanostores'
import { useEffect } from 'react'

import { decodeTspHello, encodeTspHelloQuery, isTspHelloApcResponse, type TspHello } from './protocol.js'

export type TernSurfaceState =
  | { status: 'idle' }
  | { status: 'probing' }
  | { status: 'unsupported' }
  | { status: 'active'; hello: TspHello }

/**
 * Renderer-independent capability state. Nothing consumes this for layout yet:
 * phase one only proves that Hermes can negotiate TSP without changing the
 * ordinary Ink experience.
 */
export const $ternSurface = atom<TernSurfaceState>({ status: 'idle' })

export function useTernSurfaceProbe(): void {
  const { querier } = useStdin()

  useEffect(() => {
    let cancelled = false

    if (!querier) {
      $ternSurface.set({ status: 'unsupported' })

      return
    }

    $ternSurface.set({ status: 'probing' })

    const helloResponse = querier.send({
      request: encodeTspHelloQuery(),
      match: isTspHelloApcResponse
    })

    // Reuse Hermes Ink's existing timeout-free terminal-query barrier: the TSP
    // query is written first, then DA1. A TSP-aware terminal replies before DA1;
    // an ordinary terminal ignores the APC and DA1 resolves the probe unsupported.
    void Promise.all([helloResponse, querier.flush()])
      .then(([response]) => {
        if (cancelled) {
          return
        }

        const hello = response?.type === 'apc' ? decodeTspHello(response.data) : null
        $ternSurface.set(hello ? { status: 'active', hello } : { status: 'unsupported' })
      })
      .catch(() => {
        if (!cancelled) {
          $ternSurface.set({ status: 'unsupported' })
        }
      })

    return () => {
      cancelled = true
    }
  }, [querier])
}
