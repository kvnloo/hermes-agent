#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const { chromium } = require('playwright');
const here = __dirname;
const live = JSON.parse(fs.readFileSync(path.join(here, 'live.json'), 'utf8'));
const artifacts = path.join(here, 'artifacts');
fs.mkdirSync(artifacts, { recursive: true });
const results = [];
const widths = [320, 360, 390, 430, 1280];

async function instrument(page, reduced = false, vibrate = true) {
  await page.emulateMedia({ reducedMotion: reduced ? 'reduce' : 'no-preference' });
  await page.addInitScript(({ vibrate }) => {
    window.__holdHarness = { clicks: [], drops: [], deletes: [], vibrations: [], requests: [], pointer: [], aria: [] };
    if (vibrate) Object.defineProperty(navigator, 'vibrate', { configurable: true, value: p => { window.__holdHarness.vibrations.push(p); return true; } });
    else Object.defineProperty(navigator, 'vibrate', { configurable: true, value: undefined });
    document.addEventListener('click', e => { const c = e.target.closest && e.target.closest('.hermes-kanban-card'); if (c) window.__holdHarness.clicks.push(c.getAttribute('aria-label')); }, true);
    document.addEventListener('hermes-kanban:drop', e => window.__holdHarness.drops.push(e.detail), true);
    document.addEventListener('hermes-kanban:delete', e => window.__holdHarness.deletes.push(e.detail), true);
    for (const type of ['pointerdown','pointermove','pointerup','pointercancel']) document.addEventListener(type, e => window.__holdHarness.pointer.push({type, pointerType:e.pointerType, id:e.pointerId, x:e.clientX, y:e.clientY, prevented:e.defaultPrevented}), true);
    const nativeFetch = window.fetch;
    window.fetch = async (...args) => { const r = await nativeFetch(...args); window.__holdHarness.requests.push({url:String(args[0]), method:(args[1]&&args[1].method)||'GET', status:r.status}); return r; };
    new MutationObserver(() => { document.querySelectorAll('[aria-live]').forEach(n => { if (n.textContent && !window.__holdHarness.aria.includes(n.textContent)) window.__holdHarness.aria.push(n.textContent); }); }).observe(document.documentElement, {subtree:true, childList:true, characterData:true});
  }, { vibrate });
}

async function box(page, selector) {
  const b = await page.locator(selector).first().boundingBox(); assert(b, `missing ${selector}`); return b;
}
const cdpSessions = new WeakMap();
async function pointer(page, type, x, y, opts = {}) {
  let cdp = cdpSessions.get(page);
  if (!cdp) { cdp = await page.context().newCDPSession(page); cdpSessions.set(page, cdp); }
  const map = { pointerdown: 'touchStart', pointermove: 'touchMove', pointerup: 'touchEnd', pointercancel: 'touchCancel' };
  await cdp.send('Input.dispatchTouchEvent', { type: map[type], touchPoints: type === 'pointerup' || type === 'pointercancel' ? [] : [{x,y,id:opts.id||41,radiusX:1,radiusY:1,force:1}] });
}
async function reset(page) { await page.evaluate(() => { for (const k of Object.keys(window.__holdHarness)) window.__holdHarness[k] = []; }); }
async function state(page) { return page.evaluate(() => structuredClone(window.__holdHarness)); }
async function syntheticPointer(page, type, x, y, pointerType = 'touch') {
  await page.locator('.hermes-kanban-card').first().evaluate((el, event) => el.dispatchEvent(new PointerEvent(event.type, {
    bubbles:true, cancelable:true, isPrimary:true, button:0, buttons:event.type==='pointerup'?0:1, pointerId:73,
    pointerType:event.pointerType, clientX:event.x, clientY:event.y,
  })), {type,x,y,pointerType});
}

(async () => {
  let browser;
  const contexts = new Set();
  try {
  browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium' });
  for (const width of widths) {
    const context = await browser.newContext({ viewport: { width, height: 844 }, recordVideo: { dir: artifacts, size: { width, height: 844 } } });
    contexts.add(context);
    const page = await context.newPage(); await instrument(page); await page.goto(live.url, {waitUntil:'networkidle'});
    await page.locator('.hermes-kanban-card').first().waitFor();
    await page.locator('.hermes-kanban-card').first().scrollIntoViewIfNeeded();
    const card = await box(page, '.hermes-kanban-card');
    const gestureX = card.x + card.width / 2;
    const gestureY = card.y + card.height - 20;
    const dims = await page.evaluate(() => ({scrollWidth:document.documentElement.scrollWidth, clientWidth:document.documentElement.clientWidth, minCard:Math.min(...[...document.querySelectorAll('.hermes-kanban-card')].map(n=>n.getBoundingClientRect().height)), controls:[...document.querySelectorAll('.hermes-kanban-column-tab,.hermes-kanban-card')].map(n=>n.getBoundingClientRect().height)}));
    assert(dims.scrollWidth <= dims.clientWidth, `${width}: viewport overflow`);
    assert(dims.controls.filter(Boolean).every(h => h >= 44), `${width}: control below 44px`);

    // Instant tap: exactly one card open and no move.
    await page.mouse.click(card.x + 20, card.y + 20); await page.waitForTimeout(80);
    let s = await state(page); assert.equal(s.clicks.length, 1); assert.equal(s.drops.length, 0);
    await page.keyboard.press('Escape'); await reset(page);

    // 199ms is below gate.
    await pointer(page,'pointerdown',gestureX,gestureY); await page.waitForTimeout(170); await pointer(page,'pointerup',gestureX,gestureY);
    s=await state(page); assert.equal(s.vibrations.length,0); assert.equal(s.drops.length,0); await reset(page);

    // Exactly 9px remains eligible; arm after threshold, invalid release has arm haptic only.
    await pointer(page,'pointerdown',gestureX,gestureY); await pointer(page,'pointermove',gestureX+9,gestureY); await page.waitForTimeout(220);
    assert.equal(
      await page.locator('.hermes-kanban-card').first().getAttribute('aria-grabbed'),
      'true',
      JSON.stringify({ events: (await state(page)).pointer, gesture: await page.locator('.hermes-kanban-card').first().getAttribute('data-gesture-state') }),
    );
    assert((await page.locator('.hermes-kanban-card [aria-live]').first().textContent()).startsWith('Grabbed '));
    await pointer(page,'pointerup',gestureX+9,gestureY); await page.waitForTimeout(50); s=await state(page); assert.deepEqual(s.vibrations,[18]); await reset(page);

    // >9px pre-arm cancels; no haptic/drop.
    await pointer(page,'pointerdown',gestureX,gestureY); await pointer(page,'pointermove',gestureX+10,gestureY); await page.waitForTimeout(220); await pointer(page,'pointerup',gestureX+10,gestureY);
    s=await state(page); assert.equal(s.vibrations.length,0); assert.equal(s.drops.length,0); await reset(page);

    // Armed cross-lane move/drop reaches real product event and backend request once, no ghost click.
    const dropX = gestureX + 5; const dropY = gestureY + 5;
    await pointer(page,'pointerdown',gestureX,gestureY); await page.waitForTimeout(220); await pointer(page,'pointermove',dropX,dropY); await pointer(page,'pointerup',dropX,dropY); await page.waitForTimeout(150);
    s=await state(page); assert.equal(s.drops.length,1); assert.deepEqual(s.vibrations,[18,12]); assert.equal(s.clicks.length,0); assert(s.requests.some(r=>r.method !== 'GET'));

    await page.screenshot({path:path.join(artifacts,`${width}.png`),fullPage:true});
    results.push({width, dims, state:s}); await context.close(); contexts.delete(context);
  }

  // Fractional Euclidean boundary uses real CDP touch coordinates.
  {
    const context=await browser.newContext({viewport:{width:390,height:844}}); contexts.add(context);
    const page=await context.newPage(); await instrument(page); await page.goto(live.url,{waitUntil:'networkidle'}); await page.locator('.hermes-kanban-card').first().waitFor(); await page.locator('.hermes-kanban-card').first().scrollIntoViewIfNeeded();
    const card=await box(page,'.hermes-kanban-card'); const x=card.x+card.width/2; const y=card.y+card.height-20;
    for (const [distance,expected] of [[8.99,'true'],[9,'true'],[9.01,'false']]) {
      await page.waitForTimeout(30);
      await pointer(page,'pointerdown',x,y); await pointer(page,'pointermove',x+distance,y); await page.waitForTimeout(220);
      assert.equal(await page.locator('.hermes-kanban-card').first().getAttribute('aria-grabbed'),expected,`${distance}px Euclidean boundary`);
      await pointer(page,'pointerup',x+distance,y); await reset(page);
    }
    const cdp=await page.context().newCDPSession(page);
    await cdp.send('Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',buttons:1,clickCount:1,pointerType:'pen'}); await page.waitForTimeout(220);
    assert.equal(await page.locator('.hermes-kanban-card').first().getAttribute('aria-grabbed'),'true','pen hold gate');
    await cdp.send('Input.dispatchMouseEvent',{type:'mouseReleased',x,y,button:'left',buttons:0,clickCount:1,pointerType:'pen'});
    await context.close(); contexts.delete(context);
  }

  // Real Playwright mouse drag exercises native HTML DnD at desktop width.
  {
    const context=await browser.newContext({viewport:{width:1280,height:844}}); contexts.add(context);
    const page=await context.newPage(); await instrument(page); await page.goto(live.url,{waitUntil:'networkidle'}); await page.locator('.hermes-kanban-card').first().waitFor();
    assert.equal(await page.locator('.hermes-kanban-card').first().getAttribute('draggable'),'true');
    await page.locator('.hermes-kanban-card').first().dragTo(page.locator('[data-kanban-column="review"]'));
    await page.waitForTimeout(150); assert((await state(page)).requests.some(r=>r.method!=='GET'));
    await context.close(); contexts.delete(context);
  }

  // Reduced motion suppresses haptics; absent vibrate never throws.
  for (const mode of [{reduced:true,vibrate:true},{reduced:false,vibrate:false}]) {
    const context=await browser.newContext({viewport:{width:390,height:844}}); contexts.add(context); const page=await context.newPage(); await instrument(page,mode.reduced,mode.vibrate); await page.goto(live.url,{waitUntil:'networkidle'}); await page.locator('.hermes-kanban-card').first().waitFor(); const card=await box(page,'.hermes-kanban-card'); await pointer(page,'pointerdown',card.x+20,card.y+20); await page.waitForTimeout(220); await pointer(page,'pointerup',card.x+20,card.y+20); assert.equal((await state(page)).vibrations.length,0); await context.close(); contexts.delete(context);
  }

  fs.writeFileSync(path.join(artifacts,'matrix-results.json'),JSON.stringify({live,results},null,2)); console.log(`PASS ${widths.join('/')} artifacts=${artifacts}`);
  } finally {
    await Promise.allSettled([...contexts].map(context => context.close()));
    if (browser) await browser.close();
  }
})().catch(err => { console.error(err); process.exitCode=1; });
