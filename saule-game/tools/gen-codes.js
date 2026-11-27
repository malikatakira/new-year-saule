// Generate unique codes, store them in the database and write print files.
// Usage: node tools/gen-codes.js --count 1000 --reserve 50 --base https://saule.shustudio.kz --batch print-1
//   out/<batch>/codes.csv   code;url  (for the print shop: variable data printing)
//   out/<batch>/qr/*.svg    one vector QR per code
//   out/<batch>/sheet.html  A4 preview sheets (QR + code under it) for a test print
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const QRCode = require('qrcode');
const { openDb } = require('../server/db');

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const COUNT = +arg('count', 1000), RESERVE = +arg('reserve', 50);
const BASE = String(arg('base', 'https://saule.shustudio.kz')).replace(/\/$/, '');
const BATCH = arg('batch', 'print-' + new Date().toISOString().slice(0, 10));
const DB = arg('db', process.env.DB_PATH || path.join(__dirname, '..', 'data', 'saule.db'));
const ALPH = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'; // no 0/O, 1/I/L: easy to type by hand
const rnd = n => Array.from({ length: n }, () => ALPH[crypto.randomInt(ALPH.length)]).join('');

(async () => {
  const db = openDb(DB);
  if (db.prepare('SELECT COUNT(*) n FROM codes WHERE batch = ?').get(BATCH).n) { console.error(`Batch "${BATCH}" already exists. Use another --batch.`); process.exit(1); }
  const out = path.join(__dirname, '..', 'out', BATCH), qrDir = path.join(out, 'qr');
  fs.mkdirSync(qrDir, { recursive: true });
  const total = COUNT + RESERVE, codes = new Set(), ins = db.prepare('INSERT OR IGNORE INTO codes (code, batch, created_at) VALUES (?, ?, ?)');
  const t = new Date().toISOString();
  db.exec('BEGIN');
  while (codes.size < total) { const c = 'SL-' + rnd(4) + '-' + rnd(4); if (ins.run(c, BATCH, t).changes) codes.add(c); }
  db.exec('COMMIT');
  const list = [...codes];
  const rows = ['n;code;url;reserve'];
  let sheet = `<!doctype html><meta charset="utf-8"><title>${BATCH}</title><style>@page{size:A4;margin:10mm}body{font:10px sans-serif;margin:0}.g{display:grid;grid-template-columns:repeat(5,1fr);gap:4mm}.c{text-align:center;page-break-inside:avoid;border:1px dashed #ccc;padding:2mm}.c svg{width:28mm;height:28mm}.c b{display:block;font:700 11px monospace;margin-top:1mm}</style><div class="g">`;
  for (let i = 0; i < list.length; i++) {
    const c = list[i], url = `${BASE}/?c=${c}`, svg = await QRCode.toString(url, { type: 'svg', errorCorrectionLevel: 'M', margin: 2 });
    fs.writeFileSync(path.join(qrDir, `${String(i + 1).padStart(4, '0')}_${c}.svg`), svg);
    rows.push(`${i + 1};${c};${url};${i >= COUNT ? 'yes' : 'no'}`);
    sheet += `<div class="c">${svg}<b>${c}</b></div>`;
  }
  fs.writeFileSync(path.join(out, 'codes.csv'), '﻿' + rows.join('\n'));
  fs.writeFileSync(path.join(out, 'sheet.html'), sheet + '</div>');
  console.log(`OK: ${COUNT} codes + ${RESERVE} reserve in batch "${BATCH}" -> ${out}`);
})();
