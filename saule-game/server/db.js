'use strict';
// SQLite schema. One file, easy to back up (see tools/backup.js).
const fs = require('node:fs');
const path = require('node:path');
process.removeAllListeners('warning'); // hide the "SQLite is experimental" notice
const { DatabaseSync } = require('node:sqlite');

function openDb(file) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const db = new DatabaseSync(file);
  db.exec(`
    PRAGMA journal_mode = WAL;
    PRAGMA busy_timeout = 5000;
    CREATE TABLE IF NOT EXISTS codes (
      code TEXT PRIMARY KEY,            -- SL-XXXX-XXXX, printed in one box
      batch TEXT,                       -- print batch label
      created_at TEXT NOT NULL,
      player_id TEXT,                   -- who activated it (NULL = not used yet)
      used_at TEXT
    );
    CREATE INDEX IF NOT EXISTS codes_player ON codes(player_id);
    CREATE TABLE IF NOT EXISTS players (
      id TEXT PRIMARY KEY,              -- secret key kept in the browser
      pcode TEXT UNIQUE NOT NULL,       -- player code shown in the game, used to continue on another device
      created_at TEXT NOT NULL,
      merged_into TEXT                  -- set when support merges two players
    );
    CREATE TABLE IF NOT EXISTS grants (  -- points opened by support by hand
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      player_id TEXT NOT NULL, at TEXT NOT NULL, note TEXT NOT NULL, by TEXT
    );
    CREATE TABLE IF NOT EXISTS admin_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, action TEXT NOT NULL, detail TEXT
    );
  `);
  return db;
}
module.exports = { openDb };
