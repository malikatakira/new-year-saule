// End-to-end check of the server API on a temporary database.
'use strict';
const assert = require('node:assert');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'saule-'));
process.env.DB_PATH = path.join(tmp, 't.db'); process.env.ADMIN_TOKEN = 'test-token'; process.env.PORT = '0';
const { server, db } = require('../server/server');
const t = new Date().toISOString();
for (const c of ['SL-AAAA-AAA1', 'SL-AAAA-AAA2', 'SL-AAAA-AAA3', 'SL-AAAA-AAA4', 'SL-AAAA-AAA5', 'SL-AAAA-AAA6', 'SL-BBBB-BBBB'])
  db.prepare('INSERT INTO codes (code, batch, created_at) VALUES (?, ?, ?)').run(c.replace(/1|2|3|4|5|6/g, d => 'CDEFGH'['123456'.indexOf(d)]), 'test', t);
const C = n => 'SL-AAAA-AAA' + 'CDEFGH'[n - 1];
server.listen(0, async () => {
  const base = `http://127.0.0.1:${server.address().port}`;
  const post = (p, b, h = {}) => fetch(base + p, { method: 'POST', headers: { 'content-type': 'application/json', ...h }, body: JSON.stringify(b) }).then(r => r.json());
  const get = (p, h = {}) => fetch(base + p, { headers: h }).then(r => r.json());
  try {
    const a = await post('/api/player', {}), b = await post('/api/player', {});
    assert.ok(a.key && a.pcode && a.points === 0);
    let r = await post('/api/scan', { key: a.key, code: C(1) }); assert.equal(r.status, 'new'); assert.equal(r.points, 1);
    r = await post('/api/scan', { key: a.key, code: C(1) }); assert.equal(r.status, 'mine'); assert.equal(r.points, 1);
    r = await post('/api/scan', { key: b.key, code: C(1) }); assert.equal(r.status, 'taken');
    r = await post('/api/scan', { key: a.key, code: 'sl aaaa aaad' }); assert.equal(r.status, 'new', 'typed code with spaces/lowercase'); assert.equal(r.points, 2);
    r = await post('/api/scan', { key: a.key, code: 'SL-ZZZZ-ZZZZ' }); assert.equal(r.status, 'invalid');
    // race: two players scan the same code at the same moment, only one wins
    const [x, y] = await Promise.all([post('/api/scan', { key: a.key, code: C(3) }), post('/api/scan', { key: b.key, code: C(3) })]);
    assert.deepEqual([x.status, y.status].sort(), ['new', 'taken']);
    // restore on another device by player code
    const rs = await post('/api/restore', { pcode: a.pcode.toLowerCase() }); assert.equal(rs.key, a.key);
    // admin
    assert.equal((await get('/api/admin/stats')).error, 'unauthorized');
    const H = { authorization: 'Bearer test-token' };
    const st = await get('/api/admin/stats', H); assert.equal(st.codes, 7);
    const pl = await get('/api/admin/player?q=' + encodeURIComponent(b.pcode), H); assert.equal(pl.id, b.key);
    assert.equal((await post('/api/admin/grant', { player: b.key, note: '' }, H)).error, 'note_required');
    const g = await post('/api/admin/grant', { player: b.key, note: 'чек 123', by: 'test' }, H); assert.ok(g.ok);
    const before = (await get('/api/me?key=' + a.key)).points;
    const m = await post('/api/admin/merge', { from: b.key, to: a.key, by: 'test' }, H); assert.ok(m.ok);
    const after = await get('/api/me?key=' + b.key); assert.equal(after.key, a.key, 'merged player resolves to target');
    assert.equal(after.points, Math.min(5, before + (y.status === 'new' || x.status === 'taken' ? 1 : 0) + 1));
    // cap at 5 points
    for (const n of [4, 5, 6]) await post('/api/scan', { key: a.key, code: C(n) });
    const fin = await get('/api/me?key=' + a.key); assert.equal(fin.points, 5);
    console.log('SMOKE OK', { points: fin.points, stats: (await get('/api/admin/stats', H)) });
  } catch (e) { console.error('SMOKE FAIL', e); process.exitCode = 1; }
  server.close(); fs.rmSync(tmp, { recursive: true, force: true });
});
