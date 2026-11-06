import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import DocsPage, { HERMES_DOCS_URL } from "./DocsPage";

vi.mock("@/i18n", () => ({
  useI18n: () => ({
    t: {
      app: {
        nav: { documentation: "Documentation" },
        openDocumentation: "Open documentation in a new tab",
      },
    },
  }),
}));
vi.mock("@/contexts/usePageHeader", () => ({
  usePageHeader: () => ({ setEnd: vi.fn() }),
}));
vi.mock("@/plugins", () => ({ PluginSlot: () => null }));

afterEach(() => vi.unstubAllGlobals());

describe("DocsPage framing fallback", () => {
  it.each([
    ["http://localhost:9119/", true],
    ["http://127.0.0.1:9119/", true],
    ["file:///tmp/hermes-dashboard.html", true],
    ["http://192.168.1.20:9119/", false],
    ["http://100.64.12.34:9119/", false],
    ["https://host.tailnet.ts.net/", false],
    ["https://dashboard.example.org/", false],
  ])("renders docs on %s only when the docs site allows framing", (url, embeds) => {
    vi.stubGlobal("window", { location: new URL(url) });
    const html = renderToStaticMarkup(<DocsPage />);

    if (embeds) {
      expect(html).toContain("<iframe");
      expect(html).toContain(`src="${HERMES_DOCS_URL}"`);
    } else {
      expect(html).not.toContain("<iframe");
      expect(html).toContain(`href="${HERMES_DOCS_URL}"`);
      expect(html).toContain('target="_blank"');
      expect(html).toContain('rel="noopener noreferrer"');
      expect(html).toContain("Open documentation in a new tab");
    }
  });
});
