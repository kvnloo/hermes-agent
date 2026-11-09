import { Navigate, useLocation } from "react-router";
import { useProfileScope } from "@/contexts/useProfileScope";

// A one-shot Navigate races ProfileProvider's missing-?profile repair on
// unknown routes. Wait until the URL reflects that scope before redirecting.
export function ScopedSessionsRedirect() {
  const { profile } = useProfileScope();
  const { search } = useLocation();
  const urlProfile = new URLSearchParams(search).get("profile") ?? "";
  if (urlProfile !== profile) return null;
  return <Navigate to={`/sessions${search}`} replace />;
}
