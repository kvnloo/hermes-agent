import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const widths = [320, 360, 390, 430, 1280];
const out = path.resolve('.preview/captures');
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ executablePath: '/usr/bin/chromium', headless: true });
const results = [];
for (const width of widths) {
  const page = await browser.newPage({ viewport: { width, height: width === 1280 ? 900 : 844 } });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(String(err)));
  await page.goto(`http://127.0.0.1:9135/kanban?rev=0ba3d009d&w=${width}`, { waitUntil: 'networkidle' });
  await page.waitForSelector('.hermes-kanban-card', { timeout: 15000 });
  const metrics = await page.evaluate(() => {
    const doc = document.documentElement;
    const controls = [...document.querySelectorAll('button, input, select')]
      .map(el => ({ label: el.getAttribute('aria-label') || el.textContent?.trim() || el.tagName, rect: el.getBoundingClientRect() }))
      .filter(x => x.rect.width > 0 && x.rect.height > 0);
    return {
      scrollWidth: doc.scrollWidth,
      clientWidth: doc.clientWidth,
      overflow: doc.scrollWidth > doc.clientWidth,
      minControlHeight: Math.min(...controls.map(x => x.rect.height)),
      densityTargetHeights: [...document.querySelectorAll('.hermes-kanban-column-add, .hermes-kanban-attention-toggle, .hermes-kanban-attention-dismiss, .hermes-kanban-attention-row-btn, .hermes-kanban-drawer-close')]
        .map(el => ({ className: el.className, height: el.getBoundingClientRect().height }))
        .filter(x => x.height > 0),
      cardCount: document.querySelectorAll('.hermes-kanban-card').length,
    };
  });
  await page.locator('.hermes-kanban-card').first().click();
  await page.waitForSelector('.hermes-kanban-drawer');
  const drawerVisible = await page.locator('.hermes-kanban-drawer').isVisible();
  const drawerCloseHeight = await page.locator('.hermes-kanban-drawer-close').evaluate(el => el.getBoundingClientRect().height);
  await page.keyboard.press('Escape');
  const drawerClosed = await page.locator('.hermes-kanban-drawer').count() === 0;
  const filter = page.locator('input[placeholder*="Filter"], input[placeholder*="filter"]').first();
  let filterWorks = false;
  if (await filter.count()) {
    await filter.fill('Running density');
    filterWorks = (await page.locator('.hermes-kanban-card').count()) === 1;
    await filter.fill('');
  }
  await page.screenshot({ path: path.join(out, `density-${width}.png`), fullPage: true });
  results.push({ width, ...metrics, drawerVisible, drawerCloseHeight, drawerClosed, filterWorks, errors });
  await page.close();
}
await browser.close();
fs.writeFileSync(path.join(out, 'browser-results.json'), JSON.stringify(results, null, 2) + '\n');
console.log(JSON.stringify(results, null, 2));
