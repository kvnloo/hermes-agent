/**
 * Decide whether the paginated sessions list should be silently
 * re-fetched after an overview poll.
 *
 * The dashboard's FastAPI server and a terminal CLI are separate
 * processes that share the same SQLite session DB. There is no
 * inter-process push channel, so the Sessions page polls the 50 most
 * recently active sessions every few seconds (the "overview" poll). When
 * the first visible page's ordered IDs change, its paginated list is
 * stale — refresh it even if the head ID itself stays the same.
 *
 * Returns false on the first poll (no baseline yet) and when
 * either order signature is null (empty DB / transient empty response), so we never
 * trigger a spurious reload on mount or while the DB is empty.
 */
export function shouldRefreshSessions(
  previousVisibleOrder: string | null,
  currentVisibleOrder: string | null,
): boolean {
  return (
    previousVisibleOrder !== null &&
    currentVisibleOrder !== null &&
    previousVisibleOrder !== currentVisibleOrder
  );
}
