const puppeteer = require('puppeteer');
const fs = require('fs');
(async () => {
  const outDir = '/screenshots';
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
  const browser = await puppeteer.launch({ args: ['--no-sandbox','--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  const base = 'http://host.docker.internal:8001/user-guides';

  // Overview
  await page.goto(base, { waitUntil: 'networkidle2', timeout: 30000 });
  await page.setViewport({ width: 1400, height: 1000 });
  await page.screenshot({ path: `${outDir}/overview.png`, fullPage: true });

  const tabs = [
    'getting-started','onboarding-guide','kyc-review-guide','intelligence-guide','decisioning-guide','reports-guide','production-guide','api-reference'
  ];

  for (const id of tabs) {
    try {
      // use switchTab if available
      await page.evaluate((tab)=>{ if(window.switchTab) { window.switchTab(tab); } else { const el = document.querySelector('[data-tab="'+tab+'"]'); if(el) el.click(); } }, id);
      await page.waitForTimeout(700);
      await page.screenshot({ path: `${outDir}/${id}.png`, fullPage: true });
    } catch (e) {
      console.error('failed', id, e.message);
    }
  }

  await browser.close();
  console.log('done');
})();
