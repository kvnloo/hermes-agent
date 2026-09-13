// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock the api module — SystemPage calls many endpoints on mount and on the
// debug-share click. Stub them all to resolve-empty so the page renders.
vi.mock("@/lib/api", () => ({
  api: {
    getStatus: vi.fn(async () => ({})),
    getSystemStats: vi.fn(async () => ({})),
    getMemory: vi.fn(async () => ({ builtin_files: { memory: 0, user: 0 } })),
    getCredentialPool: vi.fn(async () => ({ providers: [] })),
    getCheckpoints: vi.fn(async () => ({ sessions: [] })),
    getHooks: vi.fn(async () => ({ hooks: [] })),
    getCurator: vi.fn(async () => ({})),
    getPortal: vi.fn(async () => ({})),
    checkHermesUpdate: vi.fn(async () => ({})),
    runDebugShare: vi.fn(async () => ({
      ok: true,
      urls: { Report: "https://dpaste.com/abc", "agent.log": "https://dpaste.com/def" },
      failures: [],
      redacted: true,
      auto_delete_seconds: 86400,
      dpaste_fallback: true,
    })),
  },
}));

// Mock the heavy hooks/dialogs so rendering doesn't need providers.
vi.mock("@nous-research/ui/hooks/use-toast", () => ({
  useToast: () => ({ showToast: vi.fn() }),
}));
vi.mock("@nous-research/ui/hooks/use-confirm-delete", () => ({
  useConfirmDelete: () => ({ confirmDelete: vi.fn(async () => true), isOpen: false }),
}));
vi.mock("@/hooks/useModalBehavior", () => ({ useModalBehavior: vi.fn(() => ({})) }));
vi.mock("@/components/DeleteConfirmDialog", () => ({
  DeleteConfirmDialog: () => null,
}));
vi.mock("@/components/HermesConsoleModal", () => ({
  HermesConsoleModal: () => null,
}));
vi.mock("@/lib/clipboard", () => ({ copyTextToClipboard: vi.fn(async () => true) }));

import { api } from "@/lib/api";
import SystemPage from "@/pages/SystemPage";

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.clearAllMocks();
});

describe("SystemPage debug-share dpaste fallback rendering", () => {
  it("shows the hedged pre-upload label mentioning the dpaste.com fallback", async () => {
    await act(async () => {
      root.render(
        <MemoryRouter>
          <SystemPage />
        </MemoryRouter>,
      );
    });
    // Flush the mount loadAll promise.
    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });

    expect(container.textContent).toContain("dpaste.com");
  });

  it("renders the real auto_delete_seconds (24h) and the dpaste.com fallback badge after a fall-back share", async () => {
    await act(async () => {
      root.render(
        <MemoryRouter>
          <SystemPage />
        </MemoryRouter>,
      );
    });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });

    // Click "Generate share link".
    const buttons = Array.from(container.querySelectorAll("button"));
    const shareBtn = buttons.find((b) => b.textContent?.includes("Generate share link"));
    expect(shareBtn).toBeTruthy();
    await act(async () => {
      shareBtn!.click();
    });
    // Let the mocked runDebugShare promise settle.
    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });

    expect(api.runDebugShare).toHaveBeenCalledTimes(1);
    // Real 1-day retention rendered (not the old hardcoded 6h).
    expect(container.textContent).toContain("auto-deletes in 24h");
    expect(container.textContent).not.toContain("auto-deletes in 6h");
    expect(container.textContent).toContain("dpaste.com fallback");
  });
});
