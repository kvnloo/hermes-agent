#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert/strict');
const { chromium } = require('playwright');

const here = __dirname;
const live = JSON.parse(fs.readFileSync(path.join(here, 'live.json'), 'utf8'));
const artifacts = path.join(here, 'artifacts');
fs.mkdirSync(artifacts, { recursive: true });
const widths = [320, 360, 390, 430, 1280];
const results = [];

async function instrument(page, { reduced = false, vibrate = true } = {}) {
  await page.emulateMedia({ reducedMotion: reduced ? 'reduce' : 'no-preference' });
  await page.addInitScript(({ vibrate }) => {
    window.__holdHarness = { clicks: [], drops: [], deletes: [], vibrations: [], requests: [], pointer: [], touch: [], aria: [] };
    if (vibrate) Object.defineProperty(navigator, 'vibrate', { configurable: true, value: p => { window.__holdHarness.vibrations.push(p); return true; } });
    else Object.defineProperty(navigator, 'vibrate', { configurable: true, value: undefined });
    document.addEventListener('click', e => { const c = e.target.closest && e.target.closest('.hermes-kanban-card'); if (c) window.__holdHarness.clicks.push({ task: c.dataset.taskId, at: performance.now() }); }, true);
    document.addEventListener('hermes-kanban:drop', e => window.__holdHarness.drops.push(e.detail), true);
    document.addEventListener('hermes-kanban:delete', e => window.__holdHarness.deletes.push(e.detail), true);
    for (const type of ['pointerdown', 'pointermove', 'pointerup', 'pointercancel']) document.addEventListener(type, e => window.__holdHarness.pointer.push({ type, pointerType: e.pointerType, id: e.pointerId, x: e.clientX, y: e.clientY, button: e.button, isPrimary: e.isPrimary, target: e.target && e.target.className, prevented: e.defaultPrevented, at: performance.now(), stamp: e.timeStamp }), true);
    for (const type of ['touchstart', 'touchmove', 'touchend', 'touchcancel']) document.addEventListener(type, e => window.__holdHarness.touch.push({ type, prevented: e.defaultPrevented, cancelable: e.cancelable, at: performance.now() }), true);
    const nativeFetch = window.fetch;
    window.fetch = async (...args) => { const r = await nativeFetch(...args); window.__holdHarness.requests.push({ url: String(args[0]), method: (args[1] && args[1].method) || 'GET', status: r.status }); return r; };
    new MutationObserver(() => { document.querySelectorAll('[aria-live]').forEach(n => { if (n.textContent && !window.__holdHarness.aria.includes(n.textContent)) window.__holdHarness.aria.push(n.textContent); }); }).observe(document.documentElement, { subtree: true, childList: true, characterData: true });
  }, { vibrate });
}

async function openPage(browser, width = 390, options = {}) {
  const context = await browser.newContext({ viewport: { width, height: 844 } });
  const page = await context.newPage();
  await instrument(page, options);
  await page.goto(live.url, { waitUntil: 'networkidle' });
  await page.locator('[data-task-id="t_hold_alpha"]').waitFor();
  await page.locator('[data-task-id="t_hold_alpha"]').scrollIntoViewIfNeeded();
  return { context, page };
}

async function box(page, selector) { const b = await page.locator(selector).first().boundingBox(); assert(b, `missing ${selector}`); return b; }
async function center(page, selector) { const b = await box(page, selector); return { x: b.x + b.width / 2, y: b.y + b.height / 2 }; }
const sessions = new WeakMap();
async function touch(page, type, x, y, id = 41, timestamp) {
  let cdp = sessions.get(page);
  if (!cdp) { cdp = await page.context().newCDPSession(page); sessions.set(page, cdp); }
  const event = { type, touchPoints: type === 'touchEnd' || type === 'touchCancel' ? [] : [{ x, y, id, radiusX: 1, radiusY: 1, force: 1 }] };
  if (timestamp !== undefined) event.timestamp = timestamp;
  await cdp.send('Input.dispatchTouchEvent', event);
}
async function tap(page, x, y) { await touch(page, 'touchStart', x, y); await touch(page, 'touchEnd', x, y); }
async function measuredTap(page, x, y, measuredMs, wallMs) {
  const start = Date.now() / 1000;
  await touch(page, 'touchStart', x, y, 41, start);
  await page.waitForTimeout(wallMs);
  await touch(page, 'touchEnd', x, y, 41, start + measuredMs / 1000);
}
async function syntheticPen(page, type, x, y) {
  let cdp = sessions.get(page);
  if (!cdp) { cdp = await page.context().newCDPSession(page); sessions.set(page, cdp); }
  await cdp.send('Input.dispatchMouseEvent', {
    type: type === 'pointerdown' ? 'mousePressed' : 'mouseReleased',
    x, y, button: 'left', buttons: type === 'pointerup' ? 0 : 1,
    clickCount: 1, pointerType: 'pen',
  });
}
async function state(page) { return page.evaluate(() => structuredClone(window.__holdHarness)); }
async function reset(page) { await page.evaluate(() => { for (const key of Object.keys(window.__holdHarness)) window.__holdHarness[key] = []; }); }
function elapsed(events) { const down = events.find(e => e.type === 'pointerdown'); const up = events.find(e => e.type === 'pointerup'); assert(down && up, 'missing measured pointer trace'); return up.stamp - down.stamp; }
function hash(bytes) { return crypto.createHash('sha256').update(bytes).digest('hex'); }

async function assertServedAssets(page) {
  const served = await page.evaluate(async expected => {
    const out = {};
    for (const [rel] of Object.entries(expected)) {
      const pluginPath = rel.replace('plugins/kanban/dashboard/', '');
      const url = new URL(`/dashboard-plugins/kanban/${pluginPath}`, location.href).href;
      const response = await fetch(url); if (!response.ok) throw new Error(`${url}: ${response.status}`);
      out[rel] = Array.from(new Uint8Array(await response.arrayBuffer()));
    }
    return out;
  }, live.assets);
  for (const [rel, bytes] of Object.entries(served)) assert.equal(hash(Buffer.from(bytes)), live.assets[rel], `served hash ${rel}`);
}

(async () => {
  let browser;
  const contexts = new Set();
  try {
    browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium' });
    // Exercise native desktop DnD before touch cases intentionally mutate the
    // shared disposable board.
    {
      const opened = await openPage(browser, 1280); contexts.add(opened.context); const { page } = opened;
      await page.locator('[data-task-id="t_hold_gamma"]').dragTo(page.locator('[data-kanban-column="ready"]')); await page.waitForTimeout(500);
      assert.match(await page.locator('[data-task-id="t_hold_gamma"]').getAttribute('aria-label'), /— ready$/);
      await opened.context.close(); contexts.delete(opened.context);
    }
    for (const width of widths) {
      const opened = await openPage(browser, width); contexts.add(opened.context);
      const { page } = opened; const card = await center(page, '[data-task-id="t_hold_alpha"]');
      const dims = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth, controls: [...document.querySelectorAll('.hermes-kanban-column-tab,.hermes-kanban-card')].map(n => n.getBoundingClientRect().height) }));
      assert(dims.scrollWidth <= dims.clientWidth, `${width}: viewport overflow`);
      assert(dims.controls.filter(Boolean).every(h => h >= 44), `${width}: control below 44px`);
      await tap(page, card.x, card.y); await page.waitForTimeout(80);
      let s = await state(page); assert.equal(s.clicks.length, 1, `${width}: real touch tap click count ${JSON.stringify(s)}`); assert.equal(s.drops.length, 0);
      assert.equal(s.touch.find(e => e.type === 'touchstart').prevented, false, `${width}: touchstart prevented`);
      await page.reload({ waitUntil: 'networkidle' }); await page.locator('[data-task-id="t_hold_alpha"]').waitFor(); await page.locator('[data-task-id="t_hold_alpha"]').scrollIntoViewIfNeeded(); await reset(page);

      await measuredTap(page, card.x, card.y, 199.2, 120);
      s = await state(page); const ms199 = elapsed(s.pointer); assert(ms199 >= 199 && ms199 < 200, `${width}: 199ms trace was ${ms199}`); assert(!s.vibrations.includes(18), `${width}: 199ms armed`); assert.equal(s.drops.length, 0); await page.reload({ waitUntil: 'networkidle' }); await page.locator('[data-task-id="t_hold_alpha"]').waitFor(); await page.locator('[data-task-id="t_hold_alpha"]').scrollIntoViewIfNeeded(); await reset(page);

      await measuredTap(page, card.x, card.y, 200.2, 250);
      s = await state(page); const ms200 = elapsed(s.pointer); assert(ms200 >= 200, `${width}: 200ms trace was ${ms200}`); assert.deepEqual(s.vibrations, [18]); assert.equal(s.clicks.length, 0); await reset(page);

      results.push({ width, dims, measured199: ms199, measured200: ms200 });
      await page.screenshot({ path: path.join(artifacts, `${width}.png`), fullPage: true });
      await opened.context.close(); contexts.delete(opened.context);
    }

    // Strict fractional slop boundaries from real CDP touch coordinates.
    {
      const opened = await openPage(browser); contexts.add(opened.context); const { page } = opened; const p = await center(page, '[data-task-id="t_hold_alpha"]');
      for (const [distance, expected] of [[8.99, 'true'], [9, 'true'], [9.01, 'false']]) {
        await touch(page, 'touchStart', p.x, p.y); await touch(page, 'touchMove', p.x + distance, p.y); await page.waitForTimeout(220);
        assert.equal(await page.locator('[data-task-id="t_hold_alpha"]:not(.hermes-kanban-touch-proxy)').getAttribute('aria-grabbed'), expected, `${distance}px boundary`);
        await touch(page, 'touchEnd', p.x + distance, p.y); await reset(page);
      }
      await opened.context.close(); contexts.delete(opened.context);
    }

    // Real target coordinates, backend + DOM mutation, ghost-click suppression, and invalid drop.
    {
      const opened = await openPage(browser, 1280); contexts.add(opened.context); const { page } = opened;
      const source = await center(page, '[data-task-id="t_hold_alpha"]'); const targetBox = await box(page, '[data-kanban-column="ready"]');
      const target = { x: Math.min(1250, targetBox.x + 40), y: targetBox.y + Math.min(80, targetBox.height / 2) };
      await touch(page, 'touchStart', source.x, source.y); await page.waitForTimeout(220); await touch(page, 'touchMove', target.x, target.y); await touch(page, 'touchEnd', target.x, target.y); await page.waitForTimeout(400);
      let s = await state(page); assert.deepEqual(s.drops, [{ taskId: 't_hold_alpha', status: 'ready' }], JSON.stringify({ source, target, state: s })); assert.deepEqual(s.vibrations, [18, 12]); assert.equal(s.clicks.length, 0); assert(s.requests.some(r => r.method !== 'GET' && r.status < 400));
      await page.waitForFunction(() => document.querySelector('[data-kanban-column="ready"] [data-task-id="t_hold_alpha"]'));
      assert.match(await page.locator('[data-task-id="t_hold_alpha"]').getAttribute('aria-label'), /— ready$/);
      await page.waitForTimeout(400); assert.equal((await state(page)).clicks.length, 0, 'ghost click after valid drop');

      const beta = await center(page, '[data-task-id="t_hold_beta"]'); const betaBefore = await page.locator('[data-task-id="t_hold_beta"]').getAttribute('aria-label'); await reset(page);
      await touch(page, 'touchStart', beta.x, beta.y); await page.waitForTimeout(220); await touch(page, 'touchMove', 2, 2); await touch(page, 'touchEnd', 2, 2); await page.waitForTimeout(250);
      s = await state(page); assert.equal(s.drops.length, 0); assert.equal(s.clicks.length, 0); assert.equal(await page.locator('[data-task-id="t_hold_beta"]').getAttribute('aria-label'), betaBefore);
      await opened.context.close(); contexts.delete(opened.context);
    }

    // Nested control and keyboard remain independent card-open paths.
    {
      const opened = await openPage(browser, 1280); contexts.add(opened.context); const { page } = opened;
      const checkbox = await center(page, '[data-task-id="t_hold_beta"] [role="checkbox"]'); await tap(page, checkbox.x, checkbox.y); await page.waitForTimeout(100);
      let s = await state(page); assert.equal(s.clicks.length, 1); assert.equal(s.vibrations.length, 0); assert.equal(await page.locator('[data-task-id="t_hold_beta"]').getAttribute('aria-grabbed'), 'false');
      await reset(page); await page.locator('[data-task-id="t_hold_beta"]').focus(); await page.keyboard.press('Enter'); await page.waitForTimeout(100); assert.equal(await page.locator('.hermes-kanban-drawer').count(), 1, 'keyboard opens task');
      await opened.context.close(); contexts.delete(opened.context);
    }

    // Pen hold and immediate native mouse DnD run in independent contexts so
    // the pen's deliberate compatibility-click suppression cannot taint the
    // desktop drag oracle.
    {
      const opened = await openPage(browser, 1280); contexts.add(opened.context); const { page } = opened; const p = await center(page, '[data-task-id="t_hold_alpha"]');
      await page.waitForTimeout(100);
      await syntheticPen(page, 'pointerdown', p.x, p.y); await page.waitForTimeout(300);
      assert.equal(await page.locator('[data-task-id="t_hold_alpha"]:not(.hermes-kanban-touch-proxy)').getAttribute('aria-grabbed'), 'true', JSON.stringify(await state(page)));
      await syntheticPen(page, 'pointerup', p.x, p.y);
      await opened.context.close(); contexts.delete(opened.context);
    }

    for (const options of [{ reduced: true, vibrate: true }, { reduced: false, vibrate: false }]) {
      const opened = await openPage(browser, 390, options); contexts.add(opened.context); const p = await center(opened.page, '[data-task-id="t_hold_alpha"]'); await touch(opened.page, 'touchStart', p.x, p.y); await opened.page.waitForTimeout(220); await touch(opened.page, 'touchEnd', p.x, p.y); assert.equal((await state(opened.page)).vibrations.length, 0); await opened.context.close(); contexts.delete(opened.context);
    }

    // Both mutation oracles: exact served assets still match and canonical DB sentinel is unchanged.
    {
      const opened = await openPage(browser); contexts.add(opened.context); await assertServedAssets(opened.page);
      const sentinel = await (await fetch(`${live.url.replace(/\/kanban$/, '')}/api/kanban/boards`)).status; assert(sentinel < 500, 'disposable API unavailable');
      await opened.context.close(); contexts.delete(opened.context);
    }
    fs.writeFileSync(path.join(artifacts, 'matrix-results.json'), JSON.stringify({ live, results }, null, 2));
    fs.writeFileSync(path.join(live.home, 'matrix-success.json'), JSON.stringify({ pid: live.pid, commit: live.commit }) + '\n');
    console.log(`PASS ${widths.join('/')} artifacts=${artifacts}`);
  } finally {
    await Promise.allSettled([...contexts].map(context => context.close()));
    if (browser) await browser.close();
  }
})().catch(err => { console.error(err); process.exitCode = 1; });