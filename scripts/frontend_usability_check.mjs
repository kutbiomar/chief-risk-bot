#!/usr/bin/env node

import fs from 'node:fs/promises';
import http from 'node:http';
import https from 'node:https';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');
const frontendDir = path.join(rootDir, 'frontend-mvp');
const defaultEvidenceDir = path.join(rootDir, 'admin/status/rollout_2026-05-12/usability');

const evidenceDir = process.env.CRB_USABILITY_EVIDENCE_DIR || defaultEvidenceDir;
const screenshotDir = path.join(evidenceDir, 'screenshots');
const apiOrigin = (process.env.CRB_API_ORIGIN || 'https://api.chiefriskbot.com').replace(/\/$/, '');
const smokeEmail = process.env.CRB_SMOKE_EMAIL || 'cio@demo.chiefriskbot.com';
const smokePassword = process.env.CRB_SMOKE_PASSWORD || 'DemoPass2026!';
const chromePath = process.env.CRB_CHROME_PATH || '/usr/local/bin/google-chrome';

const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.json': 'application/json; charset=utf-8',
};

const pages = [
  { slug: 'home', path: '/', selector: '#home-metrics', label: 'Home metrics' },
  { slug: 'assets', path: '/assets', selector: '#assets-kpis', label: 'Assets KPIs' },
  { slug: 'cockpit', path: '/cockpit', selector: '#cockpit-kpis', label: 'Cockpit KPIs' },
  { slug: 'liquidity', path: '/liquidity', selector: '#liquidity-kpis', label: 'Liquidity KPIs' },
  { slug: 'briefings', path: '/briefings', selector: '#briefings-list', label: 'Briefings list' },
  { slug: 'documents', path: '/documents', selector: '#documents-summary', label: 'Documents summary' },
  { slug: 'positions', path: '/table', selector: '#positions-body', label: 'Positions table' },
  { slug: 'settings', path: '/settings', selector: '#settings-form', label: 'Settings form' },
  { slug: 'access', path: '/access', selector: '#access-members', label: 'Access members' },
  { slug: 'scenarios', path: '/scenarios', selector: '#overlay-kpis', label: 'Scenario KPIs' },
];

const viewports = [
  { name: 'desktop-1440', width: 1440, height: 1000, screenshot: true },
  { name: 'tablet-768', width: 768, height: 1024, screenshot: true },
  { name: 'mobile-390', width: 390, height: 844, screenshot: true },
  { name: 'mobile-375', width: 375, height: 812, screenshot: false },
  { name: 'mobile-430', width: 430, height: 932, screenshot: false },
];

function sendStaticFile(requestUrl, response) {
  const parsed = new URL(requestUrl, 'http://127.0.0.1');
  const cleanPath = decodeURIComponent(parsed.pathname);
  const requestedPath = cleanPath === '/'
    ? '/index.html'
    : path.extname(cleanPath)
      ? cleanPath
      : `${cleanPath}.html`;
  const safePath = path.normalize(requestedPath).replace(/^(\.\.(\/|\\|$))+/, '');
  const filePath = path.join(frontendDir, safePath);
  if (!filePath.startsWith(frontendDir)) {
    response.writeHead(403, { 'Content-Type': 'text/plain' });
    response.end('Forbidden');
    return;
  }
  fs.readFile(filePath)
    .then((data) => {
      const ext = path.extname(filePath).toLowerCase();
      response.writeHead(200, {
        'Content-Type': mimeTypes[ext] || 'application/octet-stream',
        'Cache-Control': ['.html', '.css', '.js'].includes(ext) ? 'no-store' : 'public, max-age=3600',
      });
      response.end(data);
    })
    .catch(() => {
      response.writeHead(404, { 'Content-Type': 'text/plain' });
      response.end('Not found');
    });
}

function proxyApi(request, response) {
  const upstream = new URL(request.url || '/', apiOrigin);
  const client = upstream.protocol === 'https:' ? https : http;
  const headers = {
    ...request.headers,
    host: upstream.host,
    origin: 'https://app.chiefriskbot.com',
    referer: 'https://app.chiefriskbot.com/',
  };

  const proxyRequest = client.request(
    {
      protocol: upstream.protocol,
      hostname: upstream.hostname,
      port: upstream.port || (upstream.protocol === 'https:' ? 443 : 80),
      method: request.method,
      path: `${upstream.pathname}${upstream.search}`,
      headers,
    },
    (proxyResponse) => {
      const responseHeaders = { ...proxyResponse.headers };
      delete responseHeaders['content-security-policy'];
      response.writeHead(proxyResponse.statusCode || 502, responseHeaders);
      proxyResponse.pipe(response, { end: true });
    },
  );

  proxyRequest.on('error', (error) => {
    response.writeHead(502, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify({ detail: `Failed to reach ${apiOrigin}`, error: error.message }));
  });
  request.pipe(proxyRequest, { end: true });
}

function createServer() {
  const server = http.createServer((request, response) => {
    if ((request.url || '').startsWith('/api/')) {
      proxyApi(request, response);
      return;
    }
    sendStaticFile(request.url || '/', response);
  });
  return new Promise((resolve, reject) => {
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      resolve({ server, baseUrl: `http://127.0.0.1:${address.port}` });
    });
  });
}

async function waitForReady(page, selector) {
  await page.waitForSelector('body.mvp-ready', { timeout: 25000 });
  await page.waitForSelector(selector, { timeout: 20000 });
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
}

async function login(page, baseUrl) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded' });
  await page.fill('#email', smokeEmail);
  await page.fill('#password', smokePassword);
  await Promise.all([
    page.waitForURL((url) => !url.pathname.includes('login'), { timeout: 25000 }),
    page.click('#login-submit'),
  ]);
  await page.waitForSelector('body.mvp-ready', { timeout: 25000 });
}

async function collectChecks(page) {
  return page.evaluate(() => {
    const bodyOverflowPx = Math.max(0, document.documentElement.scrollWidth - window.innerWidth);
    const visibleErrorNotices = [...document.querySelectorAll('[data-global-status], .mvp-notice')]
      .filter((item) => !item.hidden && item.textContent.trim())
      .map((item) => item.textContent.trim().replace(/\s+/g, ' '));
    const lingeringSkeletons = [...document.querySelectorAll('.mvp-skeleton')]
      .filter((item) => {
        const rect = item.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      }).length;
    const visibleButtons = [...document.querySelectorAll('button, a.btn, .iconbtn')]
      .filter((item) => {
        const rect = item.getBoundingClientRect();
        const style = window.getComputedStyle(item);
        return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
      });
    const smallTargets = visibleButtons
      .map((item) => {
        const rect = item.getBoundingClientRect();
        return {
          label: (item.getAttribute('aria-label') || item.textContent || item.getAttribute('title') || '').trim().replace(/\s+/g, ' '),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        };
      })
      .filter((item) => item.width < 32 || item.height < 32)
      .slice(0, 8);
    return { bodyOverflowPx, visibleErrorNotices, lingeringSkeletons, smallTargets };
  });
}

async function collectA11yViolations(page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  return results.violations
    .filter((violation) => ['serious', 'critical'].includes(violation.impact || ''))
    .map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      help: violation.help,
      nodes: violation.nodes.length,
    }));
}

function requestAuthState(request) {
  const headers = request.headers();
  return headers.authorization ? 'auth=present' : 'auth=missing';
}

function requestContext(viewportName, routeLabel, request) {
  return `${viewportName}/${routeLabel}: ${request.method()} ${request.url()} (${request.resourceType()}, ${requestAuthState(request)})`;
}

function markdownTable(rows) {
  const header = '| Viewport | Page | Status | Findings |\n|---|---|---|---|';
  const body = rows.map((row) => {
    const status = row.blockers.length ? 'BLOCKED' : row.warnings.length ? 'WARN' : 'PASS';
    const findings = [...row.blockers, ...row.warnings].join('<br>') || 'No issues observed';
    return `| ${row.viewport} | ${row.page} | ${status} | ${findings.replace(/\|/g, '\\|')} |`;
  }).join('\n');
  return `${header}\n${body}`;
}

async function main() {
  await fs.mkdir(screenshotDir, { recursive: true });
  const { server, baseUrl } = await createServer();
  const results = [];
  const consoleEvents = [];
  const failedResponses = [];
  const failedRequests = [];
  const a11yViolations = [];
  const browser = await chromium.launch({
    executablePath: chromePath,
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });

  try {
    for (const viewport of viewports) {
      const context = await browser.newContext({
        viewport: { width: viewport.width, height: viewport.height },
        deviceScaleFactor: 1,
        isMobile: viewport.width < 640,
      });
      const page = await context.newPage();
      let currentRouteLabel = 'login';
      page.on('console', (message) => {
        if (['error', 'warning'].includes(message.type())) {
          consoleEvents.push(`${viewport.name}/${currentRouteLabel}: console ${message.type()} ${message.text()}`);
        }
      });
      page.on('pageerror', (error) => {
        consoleEvents.push(`${viewport.name}/${currentRouteLabel}: pageerror ${error.message}`);
      });
      page.on('requestfailed', (request) => {
        const failure = request.failure();
        failedRequests.push(`${requestContext(viewport.name, currentRouteLabel, request)} -> ${failure?.errorText || 'request failed'}`);
      });
      page.on('response', (response) => {
        if (response.status() >= 400) {
          failedResponses.push(`${requestContext(viewport.name, currentRouteLabel, response.request())} -> ${response.status()}`);
        }
      });

      await login(page, baseUrl);

      for (const route of pages) {
        const row = { viewport: viewport.name, page: route.slug, blockers: [], warnings: [] };
        currentRouteLabel = route.slug;
        try {
          await page.goto(`${baseUrl}${route.path}`, { waitUntil: 'domcontentloaded' });
          await waitForReady(page, route.selector);
          const checks = await collectChecks(page);
          const routeA11yViolations = await collectA11yViolations(page);
          if (checks.visibleErrorNotices.length) {
            row.blockers.push(`Visible error notice: ${checks.visibleErrorNotices.join('; ')}`);
          }
          if (routeA11yViolations.length) {
            const summary = routeA11yViolations
              .map((violation) => `${violation.impact} ${violation.id} (${violation.nodes} nodes)`)
              .join(', ');
            row.blockers.push(`serious/critical accessibility violations: ${summary}`);
            a11yViolations.push(...routeA11yViolations.map((violation) => ({
              viewport: viewport.name,
              page: route.slug,
              ...violation,
            })));
          }
          if (checks.lingeringSkeletons > 0) {
            row.warnings.push(`${checks.lingeringSkeletons} visible skeleton placeholders remain after idle`);
          }
          if (checks.bodyOverflowPx > 4) {
            row.warnings.push(`body horizontal overflow ${checks.bodyOverflowPx}px`);
          }
          if (checks.smallTargets.length) {
            row.warnings.push(`small tap/click targets: ${checks.smallTargets.map((target) => `${target.label || '(unlabelled)'} ${target.width}x${target.height}`).join(', ')}`);
          }
          if (viewport.name === 'mobile-390') {
            const hamburgerVisible = await page.locator('#crb-hamburger').isVisible().catch(() => false);
            if (!hamburgerVisible) row.blockers.push('mobile hamburger is not visible');
          }
          if (viewport.screenshot) {
            await page.screenshot({
              path: path.join(screenshotDir, `${viewport.name}-${route.slug}.png`),
              fullPage: false,
            });
          }
        } catch (error) {
          row.blockers.push(error.message);
        }
        results.push(row);
      }
      await context.close();
    }
  } finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }

  const blockers = results.flatMap((row) => row.blockers);
  const warnings = results.flatMap((row) => row.warnings);
  const report = [
    '# Frontend Usability Sweep - 2026-05-12',
    '',
    `Target frontend: local \`frontend-mvp\` served at runtime`,
    `API proxy target: \`${apiOrigin}\``,
    `Viewports: ${viewports.map((viewport) => `${viewport.name} (${viewport.width}x${viewport.height})`).join(', ')}`,
    '',
    '## Summary',
    '',
    `- Pages checked: ${pages.length}`,
    `- Viewport/page combinations: ${results.length}`,
    `- Blocking usability failures: ${blockers.length}`,
    `- Warnings: ${warnings.length}`,
    `- Console warnings/errors: ${consoleEvents.length}`,
    `- 4xx/5xx network responses: ${failedResponses.length}`,
    `- Request failures: ${failedRequests.length}`,
    `- Serious/critical accessibility violations: ${a11yViolations.length}`,
    '',
    '## Results',
    '',
    markdownTable(results),
    '',
    '## Console observations',
    '',
    consoleEvents.length ? consoleEvents.map((item) => `- ${item}`).join('\n') : '- None',
    '',
    '## 4xx/5xx network responses',
    '',
    failedResponses.length ? failedResponses.map((item) => `- ${item}`).join('\n') : '- None',
    '',
    '## Request failures',
    '',
    failedRequests.length ? failedRequests.map((item) => `- ${item}`).join('\n') : '- None',
    '',
    '## Serious/critical accessibility violations',
    '',
    a11yViolations.length
      ? a11yViolations.map((item) => `- ${item.viewport}/${item.page}: ${item.impact} ${item.id} — ${item.help} (${item.nodes} nodes)`).join('\n')
      : '- None',
    '',
    '## Screenshot evidence',
    '',
    `Screenshots saved under \`${path.relative(rootDir, screenshotDir)}\`.`,
    '',
  ].join('\n');

  await fs.writeFile(path.join(evidenceDir, 'frontend_usability_report.md'), report, 'utf8');
  await fs.writeFile(path.join(evidenceDir, 'frontend_usability_results.json'), JSON.stringify({ results, consoleEvents, failedResponses, failedRequests, a11yViolations }, null, 2), 'utf8');

  console.log(report);
  if (blockers.length || consoleEvents.some((item) => item.includes('pageerror'))) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
