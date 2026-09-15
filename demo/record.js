// Prisma showcase recorder — by drgmb
// usage: node record.js preview|record demo2.html [t1,t2,...]
// build demo2.html first: python3 -c "import json;t=open('demo2_template.html').read();open('demo2.html','w').write(t.replace('__CARD_JSON__',json.dumps(json.load(open('card.json')),ensure_ascii=False)))"
const puppeteer = require('puppeteer-core');
const fs = require('fs'); const path = require('path');
const mode = process.argv[2] || 'preview'; const file = process.argv[3] || 'demo.html'; const times = (process.argv[4] || '').split(',').filter(Boolean).map(Number);
(async () => {
  const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: 'new',
    args: ['--no-sandbox', '--hide-scrollbars', '--force-device-scale-factor=1'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });
  await page.goto('file://' + path.resolve(file), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  const total = await page.evaluate(() => window.TOTAL);
  if (mode === 'preview') {
    fs.mkdirSync('preview', { recursive: true });
    for (const t of (times.length ? times : [1500, 5200, 7300, 11500, 17000, 22000, 26000, 30000, 33500, 40500, 44500])) {
      await page.evaluate(t => window.render(t), t);
      await page.screenshot({ path: `preview/t${String(t).padStart(5,'0')}.png` });
    }
  } else {
    fs.rmSync('frames', { recursive: true, force: true }); fs.mkdirSync('frames');
    const fps = 30, n = Math.ceil(total / 1000 * fps);
    for (let i = 0; i < n; i++) {
      await page.evaluate(t => window.render(t), i * 1000 / fps);
      await page.screenshot({ path: `frames/f${String(i).padStart(5,'0')}.jpg`, type: 'jpeg', quality: 93 });
      if (i % 150 === 0) console.log('frame', i, '/', n);
    }
    console.log('frames', n);
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
