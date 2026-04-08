const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const MIME = {
  html: 'text/html',
  css: 'text/css',
  js: 'application/javascript',
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  svg: 'image/svg+xml',
  ico: 'image/x-icon',
  json: 'application/json',
};

const ROOT = path.join(__dirname, '..', 'app', 'static');
const PORT = Number(process.env.PORT || 8000);
const API_ORIGIN = process.env.CRB_API_ORIGIN || 'http://127.0.0.1:8001';

function sendFile(req, res) {
  const cleanUrl = decodeURIComponent(req.url.split('?')[0]);
  const requested = cleanUrl === '/' ? '/index.html' : cleanUrl;
  let file = path.join(ROOT, requested);

  if (file.endsWith(path.sep)) {
    file = path.join(file, 'index.html');
  }

  fs.stat(file, (err, stats) => {
    if (!err && stats.isDirectory()) {
      file = path.join(file, 'index.html');
    }
    fs.readFile(file, (readErr, data) => {
      if (readErr) {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('Not found');
        return;
      }
      const ext = path.extname(file).slice(1).toLowerCase();
      res.writeHead(200, { 'Content-Type': MIME[ext] || 'text/plain' });
      res.end(data);
    });
  });
}

function proxyApi(req, res) {
  const upstream = new URL(req.url, API_ORIGIN);
  const client = upstream.protocol === 'https:' ? https : http;
  const headers = { ...req.headers, host: upstream.host };
  const proxyReq = client.request(
    {
      protocol: upstream.protocol,
      hostname: upstream.hostname,
      port: upstream.port || (upstream.protocol === 'https:' ? 443 : 80),
      method: req.method,
      path: `${upstream.pathname}${upstream.search}`,
      headers,
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res, { end: true });
    }
  );

  proxyReq.on('error', (error) => {
    res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end(
      JSON.stringify({
        detail: `Failed to reach backend at ${API_ORIGIN}`,
        error: error.message,
      })
    );
  });

  req.pipe(proxyReq, { end: true });
}

http
  .createServer((req, res) => {
    if ((req.url || '').startsWith('/api/')) {
      proxyApi(req, res);
      return;
    }
    sendFile(req, res);
  })
  .listen(PORT, () => {
    console.log(`ChiefRiskBot static frontend on :${PORT} (proxying /api to ${API_ORIGIN})`);
  });
