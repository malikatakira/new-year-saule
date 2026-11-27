// Browser check of the game app: QR link opens a mini-game, all 5 points, codes typed by hand,
// continue on another device by player code, taken code for a stranger, admin page.
'use strict';
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'saule-e2e-'));
process.env.DB_PATH = path.join(tmp, 'e.db'); process.env.ADMIN_TOKEN = 'e2e';
const { server, db } = require('../server/server');
const { chromium, devices } = require('playwright');
const t = new Date().toISOString();
const CODES = ['SL-AAAA-AAAA', 'SL-BBBB-BBBB', 'SL-CCCC-CCCC', 'SL-DDDD-DDDD', 'SL-EEEE-EEEE', 'SL-FFFF-FFFF'];
CODES.forEach(c => db.prepare('INSERT INTO codes (code,batch,created_at) VALUES (?,?,?)').run(c, 'e2e', t));
const shots = process.argv[2];
const snap = async (p, n) => { if (shots) await p.screenshot({ path: `${shots}/${n}.png` }); };
const stars = p => p.$$eval('#stars i.on', a => a.length);
const assert = (c, m) => { if (!c) throw new Error('assert: ' + m); console.log('ok', m); };

async function playOpenGame(p, n) {
  await p.waitForSelector('#game:not([hidden]) #g-go', { timeout: 8000 });
  await snap(p, `g${n}_rules`);
  await p.click('#g-go'); await p.waitForTimeout(2400);
  if (n === 3) for (let k = 0; k < 6; k++) { await p.mouse.click(150, 500); await p.waitForTimeout(450); }
  if (n === 4) { await p.click('#m3 button[data-i="0"]'); await p.waitForTimeout(150); }
  await p.waitForTimeout(800); await snap(p, `g${n}_play`);
  await p.evaluate(() => window.__finish(true));
  await p.waitForSelector('#res:not([hidden]) #r-ok'); await snap(p, `g${n}_win`);
  await p.click('#r-ok');
}

server.listen(0, async () => {
  const base = `http://127.0.0.1:${server.address().port}`;
  const b = await chromium.launch(); let ok = true;
  try {
    const ctx = await b.newContext({ ...devices['iPhone 13'], deviceScaleFactor: 1 });
    await ctx.addInitScript(() => localStorage.setItem('saule_debug', '1'));
    const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
    // fresh player: start screen
    await p.goto(base + '/'); await p.waitForSelector('#start:not([hidden])'); await p.waitForTimeout(600); await snap(p, 'start');
    await p.click('.chip[data-i="1"]'); assert(await p.$eval('.chip.on', e => e.dataset.i) === '1', 'hero picked');
    // QR link opens point 1 directly
    await p.goto(base + '/?c=SL-AAAA-AAAA'); await playOpenGame(p, 1);
    await p.waitForSelector('#map:not([hidden])'); await p.waitForTimeout(1600); await snap(p, 'map1');
    assert(await p.$$eval('.mate.on', a => a.length) === 2, 'hero joined team after point 1');
    assert(await stars(p) === 1, 'one star after QR'); assert(p.url() === base + '/', 'url cleaned');
    // typed codes for points 2..5
    for (let i = 2; i <= 5; i++) {
      await p.click('#b-code'); await p.fill('#f-code', CODES[i - 1].toLowerCase()); if (i === 2) await snap(p, 'sheet_code');
      await p.click('#f-go'); await playOpenGame(p, i);
      if (i < 5) { await p.waitForSelector('#map:not([hidden])'); assert(await stars(p) === i, `${i} stars`); }
    }
    await p.waitForSelector('#final:not([hidden])'); await p.waitForTimeout(1500); await snap(p, 'final');
    // repeat own code
    await p.click('#back'); await p.click('#b-code'); await p.fill('#f-code', 'SL-BBBB-BBBB'); await p.click('#f-go'); await p.waitForTimeout(500);
    console.log('repeat:', await p.textContent('#f-msg'));
    await p.click('#sheet', { position: { x: 20, y: 20 } });
    await p.click('#b-me'); const pcode = (await p.textContent('.pcode')).trim(); await snap(p, 'sheet_me');
    await p.click('#sheet', { position: { x: 20, y: 20 } });
    await p.click('#b-help'); await snap(p, 'sheet_help');
    // another device restores by link
    const p2 = await (await b.newContext({ ...devices['Pixel 5'] })).newPage();
    await p2.goto(base + '/?p=' + encodeURIComponent(pcode)); await p2.waitForSelector('#map:not([hidden])');
    assert(await stars(p2) === 5, 'other device has 5 stars');
    // stranger scans a taken code
    const p3 = await (await b.newContext({ ...devices['iPhone SE'] })).newPage();
    await p3.goto(base + '/?c=SL-AAAA-AAAA'); await p3.waitForSelector('#bubble:not([hidden])');
    console.log('stranger:', await p3.textContent('#bubble')); await snap(p3, 'stranger_320');
    // stranger plays a fresh code on small screen
    await p3.evaluate(() => localStorage.setItem('saule_debug', '1'));
    await p3.goto(base + '/?c=SL-FFFF-FFFF'); await p3.waitForSelector('#g-go'); await p3.click('#g-go'); await p3.waitForTimeout(2600); await snap(p3, 'g1_play_se');
    // admin
    const pa = await ctx.newPage(); await pa.goto(base + '/admin.html'); await pa.fill('#tok', 'e2e'); await pa.click('#go'); await pa.waitForTimeout(700);
    console.log('admin kpis:', (await pa.textContent('#kpis')).replace(/\s+/g, ' '));
    assert(errs.length === 0, 'no page errors ' + JSON.stringify(errs));
  } catch (e) { ok = false; console.error('E2E FAIL', e); }
  await b.close(); server.close(); fs.rmSync(tmp, { recursive: true, force: true }); process.exitCode = ok ? 0 : 1;
});
