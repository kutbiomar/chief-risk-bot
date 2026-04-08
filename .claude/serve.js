const http = require('http');
const fs = require('fs');
const path = require('path');
const MIME = { html:'text/html', css:'text/css', js:'application/javascript', png:'image/png', jpg:'image/jpeg', svg:'image/svg+xml', ico:'image/x-icon' };
const ROOT = path.join(__dirname, '..', 'app', 'static');
http.createServer((req, res) => {
  const url = req.url.split('?')[0];
  const file = path.join(ROOT, url === '/' ? 'index.html' : url);
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); res.end('Not found'); return; }
    const ext = path.extname(file).slice(1);
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'text/plain' });
    res.end(data);
  });
}).listen(8000, () => console.log('ChiefRiskBot serving on :8000'));
