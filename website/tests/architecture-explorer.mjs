import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { access, mkdir } from "node:fs/promises";
import { createServer } from "node:net";
import path from "node:path";
import { chromium } from "playwright";

const probe = createServer();
await new Promise((resolve, reject) => probe.listen(0, "127.0.0.1", resolve).once("error", reject));
const address = probe.address();
const port = typeof address === "object" && address ? address.port : 4317;
await new Promise((resolve) => probe.close(resolve));
const base = `http://127.0.0.1:${port}`;
const route = "/docs/developer-guide/architecture";
const evidence = process.env.ARCHITECTURE_EVIDENCE_DIR || "/tmp/hermes-architecture-evidence";
const server = spawn(process.execPath, ["node_modules/@docusaurus/core/bin/docusaurus.mjs", "serve", "--port", String(port), "--host", "127.0.0.1", "--no-open"], { stdio: "pipe" });

async function waitForServer() {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      const response = await fetch(base + route);
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Docusaurus preview did not become ready");
}

try {
  await mkdir(evidence, { recursive: true });
  await waitForServer();
  let browser;
  try {
    browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH });
  } catch (error) {
    const systemChromium = "/usr/bin/chromium";
    await access(systemChromium).catch(() => { throw error; });
    browser = await chromium.launch({ headless: true, executablePath: systemChromium });
  }

  for (const scheme of ["light", "dark"]) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, colorScheme: scheme });
    await page.addInitScript((theme) => localStorage.setItem("theme", theme), scheme);
    await page.goto(`${base}${route}?architecture=tools-approvals`, { waitUntil: "networkidle" });
    assert.equal(await page.locator("html").getAttribute("data-theme"), scheme, `${scheme} theme is effective`);
    await page.locator("[data-testid=architecture-canvas] .react-flow__node").first().waitFor();
    assert.equal(await page.locator(".react-flow__node").count(), 8, "desktop graph has exactly eight stages");
    assert.match(await page.locator("aside[aria-live=polite] h3").textContent(), /Tools \/ Approvals/);
    await page.getByRole("button", { name: /Provider Runtime/ }).focus();
    await page.keyboard.press("Enter");
    assert.equal(new URL(page.url()).searchParams.get("architecture"), "provider-runtime", "selection is reflected in URL state");
    assert.match(await page.locator("aside[aria-live=polite] h3").textContent(), /Provider Runtime/);
    assert.equal(await page.locator(".react-flow__edge-text").count(), 0, "there are no edge labels to collide");
    const geometry = await page.evaluate(() => {
      const nodes = [...document.querySelectorAll(".react-flow__node")].map((node) => ({ id: node.getAttribute("data-id"), rect: node.getBoundingClientRect() }));
      const collisions = [];
      for (let i = 0; i < nodes.length; i += 1) for (let j = i + 1; j < nodes.length; j += 1) {
        const a = nodes[i].rect; const b = nodes[j].rect; const margin = 12;
        if (a.left < b.right + margin && a.right > b.left - margin && a.top < b.bottom + margin && a.bottom > b.top - margin) collisions.push(`${nodes[i].id}/${nodes[j].id}`);
      }
      const edgeNode = [];
      for (const path of document.querySelectorAll(".react-flow__edge-path")) {
        const edge = path.closest(".react-flow__edge");
        const id = edge?.getAttribute("data-testid")?.replace("rf__edge-", "") || "edge:unknown->unknown";
        const [source, target] = id.replace("edge:", "").split("->");
        const length = path.getTotalLength();
        const steps = Math.ceil(length);
        for (let step = 1; step < steps; step += 1) {
          const point = path.getPointAtLength(step);
          const screen = new DOMPoint(point.x, point.y).matrixTransform(path.getScreenCTM());
          for (const node of nodes) {
            if (node.id === source || node.id === target) continue;
            const r = node.rect; const margin = 4;
            if (screen.x > r.left - margin && screen.x < r.right + margin && screen.y > r.top - margin && screen.y < r.bottom + margin) edgeNode.push(`${id}/${node.id}`);
          }
        }
      }
      return { collisions, edgeNode, overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth };
    });
    assert.deepEqual(geometry.collisions, [], "nodes preserve a 12px safe margin");
    assert.deepEqual(geometry.edgeNode, [], "edges preserve a 4px safe margin from nodes between endpoints");
    assert.ok(geometry.overflow <= 1, `page has no horizontal overflow (${geometry.overflow}px)`);
    const references = await page.locator("section[aria-label='Hermes request lifecycle'] a").evaluateAll((links) => [...new Set(links.map((link) => link.href))]);
    assert.ok(references.length >= 20, "all stages expose canonical references");
    for (const href of references) {
      const url = new URL(href);
      if (url.origin === base) {
        const response = await fetch(href);
        assert.ok(response.ok, `internal reference resolves: ${href}`);
      } else {
        assert.equal(url.hostname, "github.com", `external reference is canonical GitHub: ${href}`);
        assert.match(url.pathname, /^\/NousResearch\/hermes-agent\/(blob|tree)\/main\//);
        const relative = url.pathname.replace(/^\/NousResearch\/hermes-agent\/(?:blob|tree)\/main\//, "");
        await access(path.resolve("..", relative));
      }
    }
    await page.screenshot({ path: `${evidence}/desktop-${scheme}.png`, fullPage: true });
    await page.close();
  }

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto(base + route, { waitUntil: "networkidle" });
  assert.equal(await mobile.locator("[data-testid=architecture-canvas]").isVisible(), false, "mobile does not squeeze the graph");
  assert.equal(await mobile.locator("ol[aria-label='Hermes request lifecycle stages'] button").count(), 8);
  await mobile.getByRole("button", { name: /Events \/ Delivery/ }).click();
  assert.match(await mobile.locator("aside[aria-live=polite] h3").textContent(), /Events \/ Delivery/);
  assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth), 0);
  await mobile.screenshot({ path: `${evidence}/mobile.png`, fullPage: true });
  await mobile.close();

  const reduced = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
  await reduced.goto(base + route, { waitUntil: "networkidle" });
  assert.equal(await reduced.locator(".react-flow__edge.animated").count(), 0, "reduced motion disables animated edges");
  await reduced.screenshot({ path: `${evidence}/reduced-motion.png`, fullPage: true });
  await reduced.close();

  const noJs = await browser.newPage({ javaScriptEnabled: false, viewport: { width: 1200, height: 900 } });
  await noJs.goto(base + route, { waitUntil: "load" });
  const fallback = noJs.locator("section[aria-label='Hermes request lifecycle']").first();
  assert.equal(await fallback.locator(":scope > ol > li").count(), 8, "no-JS fallback contains all stages");
  assert.match(await fallback.textContent(), /Surfaces[\s\S]*Sessions \/ Memory \/ Usage \/ State/);
  await noJs.screenshot({ path: `${evidence}/no-js.png`, fullPage: true });
  await noJs.close();

  await browser.close();
  console.log(`Architecture explorer contract passed; evidence: ${evidence}`);
} finally {
  server.kill("SIGTERM");
}
