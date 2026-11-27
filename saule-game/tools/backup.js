// Consistent copy of the live database: node tools/backup.js [dir] ; keeps the last 14 copies.
'use strict';
const fs = require('node:fs'), path = require('node:path');
const { openDb } = require('../server/db');
const DB = process.env.DB_PATH || path.join(__dirname, '..', 'data', 'saule.db');
const dir = process.argv[2] || path.join(__dirname, '..', 'backups');
fs.mkdirSync(dir, { recursive: true });
const file = path.join(dir, 'saule-' + new Date().toISOString().replace(/[:.]/g, '-') + '.db');
openDb(DB).exec(`VACUUM INTO '${file.replace(/'/g, "''")}'`);
const all = fs.readdirSync(dir).filter(f => f.startsWith('saule-') && f.endsWith('.db')).sort();
all.slice(0, Math.max(0, all.length - 14)).forEach(f => fs.unlinkSync(path.join(dir, f)));
console.log('backup:', file);
