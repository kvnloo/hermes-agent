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
  const loopbackHost = [127, 0, 0, 1].join(".");

  it.each([
    ["HTTP localhost", "http://localhost:9119/", true],
    ["HTTP loopback", `http://${loopbackHost}:9119/`, true],
    ["local file", "file:///tmp/hermes-dashboard.html", true],
    ["remote numeric host", `http://${[192, 0, 2, 20].join(".")}:9119/`, false],
    ["another remote numeric host", `http://${[198, 51, 100, 34].join(".")}:9119/`, false],
    ["private proxy", "https://private.example.org/", false],
    ["public proxy", "https://dashboard.example.org/", false],
    ["HTTPS localhost", "https://localhost:9119/", false],
    ["HTTPS loopback", `https://${loopbackHost}:9119/`, false],
    ["localhost subdomain", "http://localhost.example.org:9119/", false],
  ])("uses the allowed docs presentation for %s", (_name, url, embeds) => {
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
