// Saule New Year game: tiny server with no dependencies (Node 22+, built-in SQLite).
// - Static files from ../public
// - Player API: create player, scan a code, read progress, restore on another device
// - Admin API (token): stats, look up code/player, grant a point, merge players
'use strict';
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { openDb } = require('./db');

const PORT = +process.env.PORT || 8787;
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || '';
const POINTS = +process.env.POINTS || 5;
const PUBLIC = path.join(__dirname, '..', 'public');
const db = openDb(process.env.DB_PATH || path.join(__dirname, '..', 'data', 'saule.db'));

const now = () => new Date().toISOString();
const json = (res, code, obj) => { res.writeHead(code, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }); res.end(JSON.stringify(obj)); };
const ALPH = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
// Codes look like SL-XXXX-XXXX; accept any spacing or case when typed by hand
const fixCode = c => { const s = String(c || '').toUpperCase().replace(/[^A-Z0-9]/g, ''); return s.length === 10 ? s.slice(0, 2) + '-' + s.slice(2, 6) + '-' + s.slice(6) : String(c || '').toUpperCase().trim(); };
const WORDS = ['ЁЛКА', 'СНЕГ', 'ЗВЕЗДА', 'ШАР', 'ИСКРА', 'КОНФЕТА', 'ПОДАРОК', 'САНИ'];
const newPlayerCode = () => WORDS[crypto.randomInt(WORDS.length)] + '-' + crypto.randomInt(1000, 10000) + '-' + Array.from({ length: 3 }, () => ALPH[crypto.randomInt(ALPH.length)]).join('');

// ---------- rate limiting (in memory) ----------
const hits = new Map();
function limited(key, max, windowMs) {
  const t = Date.now(), h = (hits.get(key) || []).filter(x => t - x < windowMs);
  h.push(t); hits.set(key, h); return h.length > max;
}
setInterval(() => { const t = Date.now(); for (const [k, v] of hits) if (!v.some(x => t - x < 3600e3)) hits.delete(k); }, 600e3).unref();

// ---------- helpers ----------
const q = {
  player: db.prepare('SELECT id, pcode, merged_into FROM players WHERE id = ?'),
  playerByCode: db.prepare('SELECT id, pcode, merged_into FROM players WHERE pcode = ?'),
  addPlayer: db.prepare('INSERT INTO players (id, pcode, created_at) VALUES (?, ?, ?)'),
  code: db.prepare('SELECT code, player_id, used_at FROM codes WHERE code = ?'),
  claim: db.prepare('UPDATE codes SET player_id = ?, used_at = ? WHERE code = ? AND player_id IS NULL'),
  owned: db.prepare('SELECT code, used_at FROM codes WHERE player_id = ? ORDER BY used_at'),
  grants: db.prepare('SELECT at, note FROM grants WHERE player_id = ? ORDER BY at'),
  addGrant: db.prepare('INSERT INTO grants (player_id, at, note, by) VALUES (?, ?, ?, ?)'),
  log: db.prepare('INSERT INTO admin_log (at, action, detail) VALUES (?, ?, ?)'),
};
function resolve(id) { // follow merges
  let p = q.player.get(id), guard = 0;
  while (p && p.merged_into && guard++ < 10) p = q.player.get(p.merged_into);
  return p;
}
function progress(id) {
  const owned = q.owned.all(id), grants = q.grants.all(id);
  return { points: Math.min(POINTS, owned.length + grants.length), total: POINTS, codes: owned.length, grants: grants.length };
}
async function body(req) {
  let s = ''; for await (const c of req) { s += c; if (s.length > 1e4) throw new Error('too big'); }
  try { return JSON.parse(s || '{}'); } catch { return {}; }
}
const ip = req => (req.headers['x-real-ip'] || req.headers['x-forwarded-for'] || req.socket.remoteAddress || '').toString().split(',')[0].trim();

// ---------- player API ----------
async function api(req, res, url) {
  const p = url.pathname;
  if (p === '/api/health') return json(res, 200, { ok: true, time: now() });

  if (p === '/api/player' && req.method === 'POST') {
    if (limited('new:' + ip(req), 300, 3600e3)) return json(res, 429, { error: 'slow_down' });
    const id = crypto.randomBytes(16).toString('hex');
    let pcode; for (let i = 0; i < 5; i++) { pcode = newPlayerCode(); if (!q.playerByCode.get(pcode)) break; }
    q.addPlayer.run(id, pcode, now());
    return json(res, 200, { key: id, pcode, ...progress(id) });
  }

  if (p === '/api/me' && req.method === 'GET') {
    const pl = resolve(url.searchParams.get('key') || '');
    if (!pl) return json(res, 404, { error: 'no_player' });
    return json(res, 200, { key: pl.id, pcode: pl.pcode, ...progress(pl.id) });
  }

  if (p === '/api/restore' && req.method === 'POST') {
    const b = await body(req);
    if (limited('restore:' + ip(req), 30, 3600e3)) return json(res, 429, { error: 'slow_down' });
    const pl = q.playerByCode.get(String(b.pcode || '').toUpperCase().trim());
    const r = pl && resolve(pl.id);
    if (!r) return json(res, 404, { error: 'not_found' });
    return json(res, 200, { key: r.id, pcode: r.pcode, ...progress(r.id) });
  }

  if (p === '/api/scan' && req.method === 'POST') {
    const b = await body(req);
    const pl = resolve(String(b.key || ''));
    if (!pl) return json(res, 404, { error: 'no_player' });
    // limit wrong guesses per player and (generously) per network so a school Wi-Fi is not blocked
    if (limited('scan:' + pl.id, 40, 3600e3) || limited('scanip:' + ip(req), 600, 3600e3)) return json(res, 429, { error: 'slow_down' });
    const code = fixCode(b.code);
    const row = q.code.get(code);
    if (!row) return json(res, 200, { status: 'invalid', code, ...progress(pl.id) });
    if (row.player_id === null) {
      const before = progress(pl.id).points;
      if (before >= POINTS) return json(res, 200, { status: 'full', code, ...progress(pl.id) });
      const r = q.claim.run(pl.id, now(), code); // atomic: only one player can win the race
      if (r.changes === 1) return json(res, 200, { status: 'new', code, point: before + 1, ...progress(pl.id) });
    }
    const again = q.code.get(code);
    const owner = again.player_id && resolve(again.player_id);
    return json(res, 200, { status: owner && owner.id === pl.id ? 'mine' : 'taken', code, ...progress(pl.id) });
  }
  return json(res, 404, { error: 'not_found' });
}

// ---------- admin API ----------
function isAdmin(req) {
  if (!ADMIN_TOKEN) return false;
  const h = (req.headers.authorization || '').replace(/^Bearer\s+/i, '');
  const a = Buffer.from(h), b = Buffer.from(ADMIN_TOKEN);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
async function admin(req, res, url) {
  if (!isAdmin(req)) { if (limited('adminfail:' + ip(req), 30, 3600e3)) return json(res, 429, { error: 'slow_down' }); return json(res, 401, { error: 'unauthorized' }); }
  const p = url.pathname;
  if (p === '/api/admin/stats') {
    const one = sql => db.prepare(sql).get();
    const finished = db.prepare(`SELECT COUNT(*) n FROM (SELECT p.id, (SELECT COUNT(*) FROM codes c WHERE c.player_id=p.id)+(SELECT COUNT(*) FROM grants g WHERE g.player_id=p.id) pts FROM players p WHERE p.merged_into IS NULL) WHERE pts >= ?`).get(POINTS).n;
    const byDay = db.prepare("SELECT substr(used_at,1,10) day, COUNT(*) n FROM codes WHERE used_at IS NOT NULL GROUP BY day ORDER BY day").all();
    return json(res, 200, { codes: one('SELECT COUNT(*) n FROM codes').n, used: one('SELECT COUNT(*) n FROM codes WHERE player_id IS NOT NULL').n,
      players: one("SELECT COUNT(*) n FROM players WHERE merged_into IS NULL AND id IN (SELECT player_id FROM codes WHERE player_id IS NOT NULL)").n,
      finished, byDay, points: POINTS });
  }
  if (p === '/api/admin/code') {
    const row = q.code.get(fixCode(url.searchParams.get('c')));
    if (!row) return json(res, 404, { error: 'no_code' });
    const owner = row.player_id && resolve(row.player_id);
    return json(res, 200, { ...row, owner: owner ? { id: owner.id, pcode: owner.pcode, ...progress(owner.id) } : null });
  }
  if (p === '/api/admin/player') {
    const s = String(url.searchParams.get('q') || '').toUpperCase().trim();
    const pl = resolve(s.toLowerCase()) || (q.playerByCode.get(s) && resolve(q.playerByCode.get(s).id));
    if (!pl) return json(res, 404, { error: 'no_player' });
    return json(res, 200, { id: pl.id, pcode: pl.pcode, ...progress(pl.id), owned: q.owned.all(pl.id), grants: q.grants.all(pl.id) });
  }
  if (p === '/api/admin/grant' && req.method === 'POST') {
    const b = await body(req); const pl = resolve(String(b.player || ''));
    if (!pl) return json(res, 404, { error: 'no_player' });
    if (!String(b.note || '').trim()) return json(res, 400, { error: 'note_required' });
    if (progress(pl.id).points >= POINTS) return json(res, 400, { error: 'already_full' });
    q.addGrant.run(pl.id, now(), String(b.note).slice(0, 300), String(b.by || 'admin').slice(0, 60));
    q.log.run(now(), 'grant', JSON.stringify({ player: pl.id, note: b.note, by: b.by }));
    return json(res, 200, { ok: true, ...progress(pl.id) });
  }
  if (p === '/api/admin/merge' && req.method === 'POST') {
    const b = await body(req); const from = resolve(String(b.from || '')), to = resolve(String(b.to || ''));
    if (!from || !to || from.id === to.id) return json(res, 400, { error: 'bad_players' });
    db.exec('BEGIN');
    try {
      db.prepare('UPDATE codes SET player_id = ? WHERE player_id = ?').run(to.id, from.id);
      db.prepare('UPDATE grants SET player_id = ? WHERE player_id = ?').run(to.id, from.id);
      db.prepare('UPDATE players SET merged_into = ? WHERE id = ?').run(to.id, from.id);
      q.log.run(now(), 'merge', JSON.stringify({ from: from.id, to: to.id, by: b.by }));
      db.exec('COMMIT');
    } catch (e) { db.exec('ROLLBACK'); throw e; }
    return json(res, 200, { ok: true, ...progress(to.id) });
  }
  if (p === '/api/admin/log') return json(res, 200, db.prepare('SELECT * FROM admin_log ORDER BY id DESC LIMIT 100').all());
  return json(res, 404, { error: 'not_found' });
}

// ---------- static ----------
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.webp': 'image/webp', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json', '.ico': 'image/x-icon' };
function serveStatic(req, res, url) {
  let f = path.normalize(path.join(PUBLIC, decodeURIComponent(url.pathname)));
  if (!f.startsWith(PUBLIC)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end('not found'); }
  res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream', 'cache-control': f.endsWith('.html') ? 'no-cache' : 'public, max-age=86400' });
  fs.createReadStream(f).pipe(res);
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  try {
    if (url.pathname.startsWith('/api/admin/')) return await admin(req, res, url);
    if (url.pathname.startsWith('/api/')) return await api(req, res, url);
    return serveStatic(req, res, url);
  } catch (e) { console.error(now(), e); json(res, 500, { error: 'server_error' }); }
});
if (require.main === module) server.listen(PORT, () => console.log(`Saule game on :${PORT}${ADMIN_TOKEN ? '' : ' (admin disabled: set ADMIN_TOKEN)'}`));
module.exports = { server, db };
