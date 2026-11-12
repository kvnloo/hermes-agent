#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const { chromium } = require('playwright');
const here = __dirname;
const live = JSON.parse(fs.readFileSync(path.join(here, 'live.json'), 'utf8'));
const widths = [320, 360, 390, 430, 1280];
const results = [];
assert.equal(live.commit, 'e78904f1ffb2af707d896c0de9fcb298c4d747fb');
assert.deepEqual(live.source_identity.assets, live.assets);

async function point(page, selector) {
  const box = await page.locator(selector).first().boundingBox();
  assert(box, `missing ${selector}`);
  return { x: box.x + box.width / 2, y: box.y + Math.min(70, box.height / 2) };
}
async function touch(cdp, type, p, timestamp, points) {
  await cdp.send('Input.dispatchTouchEvent', {
    type,
    timestamp,
    touchPoints: type === 'touchEnd' || type === 'touchCancel' ? [] : (points || [{ x: p.x, y: p.y, id: 71, radiusX: 1, radiusY: 1, force: 1 }]),
  });
}
async function drag(page, cdp, from, moves, duration = 0.18) {
  const start = Date.now() / 1000;
  await touch(cdp, 'touchStart', from, start);
  for (let i = 0; i < moves.length; i++) await touch(cdp, 'touchMove', moves[i], start + duration * (i + 1) / moves.length);
  await touch(cdp, 'touchEnd', moves.at(-1), start + duration);
  await page.waitForTimeout(220);
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium' });
  try {
    for (const width of widths) {
      const context = await browser.newContext({ viewport: { width, height: 844 } });
      const page = await context.newPage();
      await page.addInitScript(() => {
        window.__laneProof = { changes: [], vibrations: [], cancels: 0 };
        Object.defineProperty(navigator, 'vibrate', { configurable: true, value: p => { window.__laneProof.vibrations.push(p); return true; } });
        document.addEventListener('hermes-kanban:lane-change', e => window.__laneProof.changes.push(e.detail));
        document.addEventListener('pointercancel', () => window.__laneProof.cancels++);
      });
      await page.goto(live.url, { waitUntil: 'networkidle' });
      await page.locator('.hermes-kanban-columns').waitFor();
      const cdp = await context.newCDPSession(page);
      const css = await page.locator('.hermes-kanban-columns').evaluate(el => ({ touchAction: getComputedStyle(el).touchAction, direction: getComputedStyle(el).direction }));
      assert.equal(css.touchAction, 'pan-y', `${width}: touch ownership`);
      if (width < 768) {
        const edge = await point(page, '.hermes-kanban-lane-edge--end');
        const before = await page.locator('.hermes-kanban-columns').getAttribute('data-active-lane');
        await drag(page, cdp, edge, [{ x: edge.x - 3, y: edge.y }, { x: edge.x - 6, y: edge.y }]);
        let proof = await page.evaluate(() => structuredClone(window.__laneProof));
        assert.equal(proof.changes.length, 0, `${width}: tap/no-axis navigated`);
        await drag(page, cdp, edge, [{ x: edge.x + 2, y: edge.y + 30 }, { x: edge.x + 4, y: edge.y + 75 }]);
        proof = await page.evaluate(() => structuredClone(window.__laneProof));
        assert.equal(proof.changes.length, 0, `${width}: vertical navigated`);
        const cancelsBeforeHorizontal = proof.cancels;
        await drag(page, cdp, edge, [{ x: edge.x - 30, y: edge.y }, { x: edge.x - 95, y: edge.y }], 0.12);
        proof = await page.evaluate(() => structuredClone(window.__laneProof));
        assert.equal(proof.cancels, cancelsBeforeHorizontal, `${width}: browser cancelled horizontal pointer stream`);
        assert.equal(proof.changes.length, 1, `${width}: committed callback count`);
        assert.deepEqual(proof.vibrations, [8], `${width}: committed haptic count`);
        const after = await page.locator('.hermes-kanban-columns').getAttribute('data-active-lane');
        assert.notEqual(after, before, `${width}: lane unchanged`);
        const card = await point(page, '.hermes-kanban-card');
        await drag(page, cdp, card, [{ x: card.x - 100, y: card.y }], 0.12);
        proof = await page.evaluate(() => structuredClone(window.__laneProof));
        assert.equal(proof.changes.length, 1, `${width}: card-origin navigated`);
        results.push({ width, css, before, after, proof });
      } else {
        assert.equal(await page.locator('.hermes-kanban-lane-tabs').evaluate(el => getComputedStyle(el).display), 'none');
        results.push({ width, css, desktop: true });
      }
      await context.close();
    }
    const out = path.join(here, 'artifacts', 'gesture-results.json');
    fs.writeFileSync(out, JSON.stringify({ commit: live.commit, assets: live.assets, results }, null, 2));
    console.log(`PASS lane gestures ${widths.join('/')} evidence=${out}`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
