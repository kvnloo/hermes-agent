// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  createProfile: vi.fn(),
  getActiveProfile: vi.fn(),
  getModelOptions: vi.fn(),
  getProfiles: vi.fn(),
  getSkills: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: apiMocks,
  setManagementProfile: vi.fn(),
  getManagementProfile: vi.fn(() => ""),
}));

let root: Root;
let container: HTMLDivElement;
(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

async function waitFor(condition: () => boolean) {
  const deadline = Date.now() + 5000;
  while (!condition()) {
    if (Date.now() > deadline) throw new Error("Profile creation receipt did not appear");
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 20)); });
  }
}

async function click(button: Element) {
  await act(async () => {
    button.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  });
}

function button(label: string): HTMLButtonElement {
  const found = [...document.querySelectorAll("button")].find(el => el.textContent?.trim() === label);
  if (!found) throw new Error("Missing button: " + label);
  return found;
}

beforeEach(() => {
  Object.values(apiMocks).forEach(mock => mock.mockReset());
  apiMocks.getProfiles.mockResolvedValue({ profiles: [] });
  apiMocks.getActiveProfile.mockResolvedValue({ current: "default", active: "default" });
  apiMocks.getSkills.mockResolvedValue([]);
  apiMocks.getModelOptions.mockResolvedValue({ providers: [] });
  apiMocks.createProfile.mockResolvedValue({
    ok: true,
    name: "warning-bot",
    path: "/profiles/warning-bot",
    warnings: ["Subscription logins stay with default.", "A plugin could not be copied."],
    hub_installs: [],
  });
  vi.stubGlobal("ResizeObserver", class { disconnect() {} observe() {} unobserve() {} });
  vi.stubGlobal("matchMedia", () => ({
    matches: false, media: "", addEventListener() {}, removeEventListener() {},
  }));
  window.__HERMES_DASHBOARD_PROFILE__ = "default";
});

afterEach(async () => {
  await act(async () => root?.unmount());
  container?.remove();
  vi.unstubAllGlobals();
  delete window.__HERMES_DASHBOARD_PROFILE__;
});

it("keeps wizard creation warnings visible after navigation to Profiles until dismissed", async () => {
  const [
    { default: ProfileBuilderPage },
    { default: ProfilesPage },
    { I18nProvider },
    { ProfileProvider },
    { PageHeaderProvider },
  ] = await Promise.all([
    import("./ProfileBuilderPage"),
    import("./ProfilesPage"),
    import("@/i18n"),
    import("@/contexts/ProfileProvider"),
    import("@/contexts/PageHeaderProvider"),
  ]);
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  await act(async () => {
    root.render(
      <I18nProvider>
        <MemoryRouter initialEntries={["/profiles/new"]}>
          <ProfileProvider>
            <PageHeaderProvider pluginTabs={[]}>
              <Routes>
                <Route path="/profiles/new" element={<ProfileBuilderPage />} />
                <Route path="/profiles" element={<ProfilesPage />} />
              </Routes>
            </PageHeaderProvider>
          </ProfileProvider>
        </MemoryRouter>
      </I18nProvider>,
    );
  });
  const input = document.querySelector<HTMLInputElement>("#pb-name")!;
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, "warning-bot");
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await click(button("5. Review"));
  await click(button("Create profile"));

  const warning = "Subscription logins stay with default.";
  const receipt = () => [...document.querySelectorAll<HTMLElement>('[role="status"]')].find(el => el.textContent?.includes(warning));
  await waitFor(() => !!receipt());
  expect(document.querySelector("#pb-name")).toBeNull();
  expect(receipt()!.textContent).toContain("A plugin could not be copied.");
  expect(receipt()!.textContent).toContain("warning-bot");
  expect(apiMocks.createProfile).toHaveBeenCalledTimes(1);

  await click(receipt()!.querySelector<HTMLButtonElement>('[aria-label="Dismiss"]')!);
  expect(receipt()).toBeUndefined();
});
