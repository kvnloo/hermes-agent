// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";

vi.mock("@/lib/api", () => ({
  api: {
    getProfiles: () => new Promise(() => {}),
    getActiveProfile: () => new Promise(() => {}),
  },
  setManagementProfile: vi.fn(),
}));

import { ProfileProvider } from "@/contexts/ProfileProvider";
import { ScopedSessionsRedirect } from "./ScopedSessionsRedirect";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root | undefined;
let container: HTMLDivElement | undefined;

function Destination() {
  const { pathname, search } = useLocation();
  return <output>{pathname + search}</output>;
}

afterEach(async () => {
  if (root) await act(async () => root!.unmount());
  container?.remove();
  root = undefined;
  container = undefined;
  delete window.__HERMES_DASHBOARD_PROFILE__;
});

describe("fallback redirect after profile bootstrap", () => {
  it.each([
    ["/missing", "/sessions?profile=served"],
    ["/missing?sort=recent", "/sessions?sort=recent&profile=served"],
    ["/missing?profile=review&sort=recent", "/sessions?profile=review&sort=recent"],
  ])("lands from %s at %s", async (entry, expected) => {
    window.__HERMES_DASHBOARD_PROFILE__ = "served";
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);

    await act(async () => root!.render(
      <MemoryRouter initialEntries={[entry]}>
        <ProfileProvider>
          <Routes>
            <Route path="/sessions" element={<Destination />} />
            <Route path="*" element={<ScopedSessionsRedirect />} />
          </Routes>
        </ProfileProvider>
      </MemoryRouter>,
    ));

    expect(container.querySelector("output")?.textContent).toBe(expected);
  });
});
