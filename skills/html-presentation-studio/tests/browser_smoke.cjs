#!/usr/bin/env node
/* Optional real-browser smoke test. Requires the Playwright package and browser. */

const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

async function main() {
  const deckPath = process.argv[2];
  const reportDir = process.argv[3];
  if (!deckPath || !reportDir) {
    throw new Error('usage: node browser_smoke.cjs path/to/index.html report-directory');
  }
  fs.mkdirSync(reportDir, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || chromium.executablePath(),
  });
  const report = { ok: true, failures: [], viewports: [] };
  try {
    for (const viewport of [
      { name: 'desktop', width: 1440, height: 900 },
      { name: 'mobile', width: 375, height: 812 },
    ]) {
      const page = await browser.newPage({ viewport });
      const consoleErrors = [];
      page.on('console', message => {
        if (message.type() === 'error') consoleErrors.push(message.text());
      });
      page.on('pageerror', error => consoleErrors.push(String(error)));
      await page.goto(pathToFileURL(path.resolve(deckPath)).href, { waitUntil: 'load' });
      const state = await page.evaluate(() => ({
        slides: document.querySelectorAll('.slide').length,
        dots: document.querySelectorAll('.dot').length,
        horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
        overflowingSlides: [...document.querySelectorAll('.slide')]
          .map((slide, index) => ({ index: index + 1, overflow: slide.scrollHeight > window.innerHeight + 2 }))
          .filter(item => item.overflow),
        invalidImages: [...document.images]
          .map((image, index) => ({ index: index + 1, complete: image.complete, naturalWidth: image.naturalWidth }))
          .filter(item => !item.complete || item.naturalWidth < 1),
      }));
      if (state.slides < 1 || state.slides !== state.dots) {
        report.failures.push(`${viewport.name}: invalid slide or dot count`);
      }
      if (state.horizontalOverflow) report.failures.push(`${viewport.name}: horizontal overflow`);
      if (state.overflowingSlides.length) {
        report.failures.push(`${viewport.name}: overflowing slides ${state.overflowingSlides.map(item => item.index).join(', ')}`);
      }
      if (state.invalidImages.length) {
        report.failures.push(`${viewport.name}: invalid images ${state.invalidImages.map(item => item.index).join(', ')}`);
      }
      if (consoleErrors.length) report.failures.push(`${viewport.name}: console errors: ${consoleErrors.join(' | ')}`);
      await page.screenshot({ path: path.join(reportDir, `${viewport.name}.png`), fullPage: true });
      report.viewports.push({ ...viewport, ...state, consoleErrors });
      await page.close();
    }

    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    await page.goto(pathToFileURL(path.resolve(deckPath)).href, { waitUntil: 'load' });
    const slideCount = await page.locator('.slide').count();
    await page.keyboard.press('PageDown');
    await page.waitForTimeout(50);
    const current = await page.locator('#current').textContent();
    const expected = String(Math.min(2, slideCount)).padStart(2, '0');
    if (current !== expected) report.failures.push(`keyboard navigation expected ${expected}, got ${current}`);
    await page.close();
  } finally {
    await browser.close();
  }
  report.ok = report.failures.length === 0;
  fs.writeFileSync(path.join(reportDir, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = report.ok ? 0 : 1;
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
