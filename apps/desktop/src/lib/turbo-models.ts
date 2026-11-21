/**
 * Canonical vLLM Semantic Router virtual routes. The gateway catalog remains
 * the source of availability; no route is invented for an unconfigured host.
 */
export const TURBO_ROUTE_IDS = ['turbo', 'free-quality', 'free-reasoning', 'free-verify', 'free-longctx'] as const

export type TurboRouteId = (typeof TURBO_ROUTE_IDS)[number]

/** Support both the registered provider and its custom-provider namespace. */
export function turboRouteId(provider: string, model: string): TurboRouteId | null {
  const slug = provider.trim().toLowerCase().replace(/^custom:/, '')

  if (slug !== 'vllm-sr') {
    return null
  }

  const id = model.trim().toLowerCase().replace(/^vllm-sr\//, '')

  return (TURBO_ROUTE_IDS as readonly string[]).includes(id) ? (id as TurboRouteId) : null
}
