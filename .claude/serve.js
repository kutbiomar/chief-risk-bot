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

const ROOTS = [
  path.join(__dirname, '..', 'frontend-mvp'),
  path.join(__dirname, '..', 'frontend-design-ideal'),
];
const PORT = Number(process.env.PORT || 8000);
const API_ORIGIN = process.env.CRB_API_ORIGIN || 'http://127.0.0.1:8001';

function readFileFromRoots(requestedPath, callback) {
  let index = 0;

  function tryNextRoot() {
    if (index >= ROOTS.length) {
      callback(new Error('Not found'));
      return;
    }

    const root = ROOTS[index];
    index += 1;
    let file = path.join(root, requestedPath);

    if (file.endsWith(path.sep)) {
      file = path.join(file, 'index.html');
    }

    fs.stat(file, (statErr, stats) => {
      if (statErr) {
        tryNextRoot();
        return;
      }

      if (stats.isDirectory()) {
        file = path.join(file, 'index.html');
      }

      fs.readFile(file, (readErr, data) => {
        if (readErr) {
          tryNextRoot();
          return;
        }
        callback(null, { file, data });
      });
    });
  }

  tryNextRoot();
}

function sendFile(req, res) {
  const cleanUrl = decodeURIComponent(req.url.split('?')[0]);
  const requested = cleanUrl === '/' ? '/index.html' : cleanUrl;

  readFileFromRoots(requested, (err, result) => {
    if (err || !result) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('Not found');
      return;
    }

    const ext = path.extname(result.file).slice(1).toLowerCase();
    const cacheControl = ['html', 'css', 'js'].includes(ext)
      ? 'no-store, no-cache, must-revalidate'
      : 'public, max-age=3600';
    res.writeHead(200, {
      'Content-Type': MIME[ext] || 'text/plain',
      'Cache-Control': cacheControl,
      'Pragma': 'no-cache',
      'Expires': '0',
    });
    res.end(result.data);
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
