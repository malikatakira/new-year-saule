// Build one self-contained demo file (no server needed): all images inlined, demo mode on.
// Usage: node tools/build-demo.js out/saule-demo.html
'use strict';
const fs = require('node:fs'), path = require('node:path');
const pub = path.join(__dirname, '..', 'public');
let s = fs.readFileSync(path.join(pub, 'index.html'), 'utf8');
s = s.replace("const DEMO=new URLSearchParams(location.search).has('demo');", 'const DEMO=true;');
s = s.replace(/assets\/([a-z_]+)\.webp/g, (m, n) => 'data:image/webp;base64,' + fs.readFileSync(path.join(pub, 'assets', n + '.webp')).toString('base64'));
const out = process.argv[2] || path.join(__dirname, '..', 'out', 'saule-demo.html');
fs.mkdirSync(path.dirname(out), { recursive: true }); fs.writeFileSync(out, s);
console.log('demo ->', out, Math.round(s.length / 1024) + ' KB');
