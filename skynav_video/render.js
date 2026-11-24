// Tüm kareleri JPEG olarak çeker: node render.js <video> <klasör>
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [vid, out] = process.argv.slice(2);
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await p.goto('file://' + __dirname + '/anim.html#' + vid);
  await p.waitForFunction(() => window.ready && window.ready(), null, { timeout: 20000 });
  const info = await p.evaluate(() => ({ dur: window.VIDEO.dur, sfx: window.VIDEO.sfx }));
  fs.writeFileSync(`${out}/info.json`, JSON.stringify(info));
  const n = Math.round(info.dur * 30);
  for (let f = 0; f < n; f++) {
    await p.evaluate(tt => window.render(tt), f / 30);
    await p.screenshot({ path: `${out}/${String(f).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 93 });
  }
  await b.close();
  console.log('frames', n);
})();
