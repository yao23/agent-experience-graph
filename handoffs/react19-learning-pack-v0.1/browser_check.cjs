// Uses an existing Playwright installation and installed Chrome; installs nothing.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PACK_PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.PACK_PREVIEW_ORIGIN || 'http://127.0.0.1:8765';
const output = path.join(__dirname, 'evidence');
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const context = await browser.newContext({ permissions: ['clipboard-read', 'clipboard-write'], reducedMotion: 'reduce' });
    const page = await context.newPage();
    const errors = [], externalRequests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { if (!request.url().startsWith(base)) externalRequests.push(request.url()); });
    const response = await page.goto(base + '/docs/react19-migration-pack/');
    assert.equal(response.status(), 200);
    assert.equal(await page.title(), 'React 19 Migration Acceptance Pack');
    assert.equal(await page.locator('h1').count(), 1);
    assert.equal(await page.locator('section[id^="r19-"]').count(), 6);
    const rules = await page.locator('#copy-block-1').textContent();
    await page.getByRole('button', { name: 'Copy shared agent rules', exact: true }).click();
    assert.equal(await page.evaluate(() => navigator.clipboard.readText()), rules);
    for (let i = 1; i <= 6; i++) {
      const id = `R19-${String(i).padStart(2, '0')}`;
      const brief = await page.locator(`#copy-block-${i + 1}`).textContent();
      await page.getByRole('button', { name: `Copy ${id} agent brief`, exact: true }).click();
      assert.equal(await page.evaluate(() => navigator.clipboard.readText()), rules + '\n\n' + brief);
    }
    const receipt = await page.locator('#copy-block-8').textContent();
    await page.getByRole('button', { name: 'Copy receipt template', exact: true }).click();
    assert.equal(await page.evaluate(() => navigator.clipboard.readText()), receipt);
    const downloadEvent = page.waitForEvent('download');
    await page.getByRole('link', { name: 'Download Markdown', exact: true }).click();
    const download = await downloadEvent;
    assert.equal(download.suggestedFilename(), 'react19-migration-acceptance-pack-v0.1.md');
    assert.equal(fs.readFileSync(await download.path(), 'utf8'), fs.readFileSync(path.join(__dirname, '../../docs/react19-migration-pack/pack.md'), 'utf8'));
    const feedback = page.locator('a[href*="/issues/new"]');
    assert.equal(await feedback.count(), 1);
    assert.equal(await feedback.getAttribute('href'), 'https://github.com/yao23/agent-experience-graph/issues/new?template=learning-pack-feedback.yml');
    const layouts = [];
    await page.evaluate(() => { document.querySelector('[data-copy-status]').textContent = ''; });
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.reload();
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      await page.evaluate(() => window.scrollTo(0, 0));
      const layout = await page.evaluate(() => ({ width: innerWidth, documentWidth: document.documentElement.scrollWidth, bodyFont: getComputedStyle(document.body).fontSize }));
      assert.ok(layout.documentWidth <= width, JSON.stringify(layout));
      layouts.push(layout);
      await page.screenshot({ path: path.join(output, `top-${width}.png`) });
      await page.locator('#r19-04').evaluate(element => element.scrollIntoView({ block: 'start' }));
      await page.screenshot({ path: path.join(output, `check04-${width}.png`) });
      const colors = await page.locator('#copy-block-5').evaluate(element => ({ text: getComputedStyle(element).color, background: getComputedStyle(element).backgroundColor, code: getComputedStyle(element.querySelector('code')).color }));
      assert.deepEqual(colors, { text: 'rgb(18, 27, 24)', background: 'rgb(251, 250, 245)', code: 'rgb(18, 27, 24)' });
      if (width === 390) {
        await page.locator('#copy-block-5').evaluate(element => element.scrollIntoView({ block: 'center' }));
        await page.screenshot({ path: path.join(output, 'agent-brief-390.png') });
      }
    }
    // Explicitly deny clipboard access and verify the visible manual-copy route.
    await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async () => { throw new Error('denied for fallback check'); } } }));
    await page.getByRole('button', { name: 'Copy R19-04 agent brief', exact: true }).click();
    assert.match(await page.locator('[data-copy-status]').textContent(), /Clipboard access is unavailable/);
    assert.equal(await page.evaluate(() => document.activeElement.id), 'copy-block-5');
    await page.getByRole('button', { name: 'Copy shared agent rules', exact: true }).click();
    assert.equal(await page.evaluate(() => document.activeElement.id), 'copy-block-1');
    assert.deepEqual(errors, []);
    assert.deepEqual(externalRequests, []);
    const noJS = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 900 } });
    const plain = await noJS.newPage();
    await plain.goto(base + '/docs/react19-migration-pack/');
    assert.equal(await plain.locator('section[id^="r19-"]').count(), 6);
    assert.equal(await plain.locator('a[download]').count(), 1);
    await noJS.close();
    const report = {
      status: 'PASS', browser: await browser.version(), layouts,
      checks: ['HTTP 200', 'six check sections', 'shared-rule copy', 'six self-contained brief copies', 'receipt copy', 'Markdown download filename and exact bytes', 'single feedback URL (not submitted)', '1440/390/320px no horizontal overflow', 'dark code text on light code background', 'clipboard-denial fallback and focus', 'no JS errors', 'no external requests', 'content/download present with JavaScript disabled'],
      limits: ['No target React app or native IME was tested', 'GitHub hosted issue-form rendering/submission UNKNOWN before publication', 'Other browser engines and real devices UNKNOWN', 'Screenshots require human visual inspection']
    };
    fs.writeFileSync(path.join(output, 'browser-report.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
