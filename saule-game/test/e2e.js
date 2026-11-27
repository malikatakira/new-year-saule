// Browser check: scan a code from a QR link, play, continue on another "device" by player code.
'use strict';
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'saule-e2e-'));
process.env.DB_PATH = path.join(tmp, 'e.db'); process.env.ADMIN_TOKEN = 'e2e';
const { server, db } = require('../server/server');
const { chromium, devices } = require('playwright');
const t = new Date().toISOString();
['SL-AAAA-AAAA', 'SL-BBBB-BBBB', 'SL-CCCC-CCCC'].forEach(c => db.prepare('INSERT INTO codes (code,batch,created_at) VALUES (?,?,?)').run(c, 'e2e', t));
const shots = process.argv[2];
server.listen(0, async () => {
  const base = `http://127.0.0.1:${server.address().port}`;
  const b = await chromium.launch(); let ok = true;
  try {
    const ctx = await b.newContext({ ...devices['iPhone 13'], deviceScaleFactor: 1 }); const p = await ctx.newPage();
    const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.goto(base + '/?c=SL-AAAA-AAAA'); await p.waitForSelector('#ov:not([hidden])', { timeout: 8000 });
    console.log('overlay:', await p.textContent('#ov-card h2'));
    if (shots) await p.screenshot({ path: shots + '/e2e_mini.png' });
    await p.evaluate(() => { document.getElementById('ov').hidden = true; });
    console.log('points after QR:', await p.textContent('#pts'), '| url cleaned:', p.url() === base + '/');
    await p.fill('#code', 'sl-bbbb-bbbb'); await p.click('#enter'); await p.waitForTimeout(800);
    await p.evaluate(() => { document.getElementById('ov').hidden = true; });
    console.log('points after typed code:', await p.textContent('#pts'));
    await p.fill('#code', 'SL-BBBB-BBBB'); await p.click('#enter'); await p.waitForTimeout(500);
    console.log('repeat:', await p.textContent('#status'));
    const pcode = await p.textContent('#pcode');
    if (shots) await p.screenshot({ path: shots + '/e2e_map.png', fullPage: true });
    // another device
    const p2 = await (await b.newContext({ ...devices['Pixel 5'] })).newPage();
    await p2.goto(base + '/?p=' + encodeURIComponent(pcode)); await p2.waitForTimeout(1200);
    console.log('other device points:', await p2.textContent('#pts'), 'pcode same:', (await p2.textContent('#pcode')) === pcode);
    await p2.goto(base + '/?c=SL-AAAA-AAAA'); await p2.waitForTimeout(800); console.log('other device rescans own code:', await p2.textContent('#status'));
    // third device without restore: code is taken
    const p3 = await (await b.newContext()).newPage(); await p3.goto(base + '/?c=SL-AAAA-AAAA'); await p3.waitForTimeout(1000);
    console.log('stranger:', await p3.textContent('#status'));
    // admin page
    const pa = await ctx.newPage(); await pa.goto(base + '/admin.html'); await pa.fill('#tok', 'e2e'); await pa.click('#go'); await pa.waitForTimeout(700);
    console.log('admin kpis:', (await pa.textContent('#kpis')).replace(/\s+/g, ' '));
    if (shots) await pa.screenshot({ path: shots + '/e2e_admin.png', fullPage: true });
    console.log('page errors:', errs);
  } catch (e) { ok = false; console.error('E2E FAIL', e); }
  await b.close(); server.close(); fs.rmSync(tmp, { recursive: true, force: true }); process.exitCode = ok ? 0 : 1;
});
