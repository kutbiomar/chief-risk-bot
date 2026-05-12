(function () {
  // MVP app index: auth/API helpers, shared render helpers, page initializers, then data-page routing.
  // This tree has richer UI than frontend/; confirm the canonical deploy target before adding features.
  const DEFAULT_CURRENCY = 'CHF';
  const SETTINGS_STORAGE_KEY = 'crb_workspace_settings';
  const AUTH_TOKEN_STORAGE_KEY = 'crb.auth_token';
  const AUTH_TOKEN_SESSION_STORAGE_KEY = 'crb.auth_token.session';
  const AUTH_STORAGE_PREFERENCE_KEY = 'crb.auth_storage';
  const API_BASE_OVERRIDE_STORAGE_KEY = 'crb.api_base_override';
  const PROD_API_BASE = 'https://api.chiefriskbot.com/api';
  const REPORTING_FX_RATES = {
    USD: 1,
    CHF: 0.91,
    EUR: 0.93,
    GBP: 0.79,
  };
  let preferredCurrency = DEFAULT_CURRENCY;

  const STEP_LABELS = {
    workspace_created: 'Workspace created',
    portfolio_uploaded: 'Portfolio uploaded',
    enrichment_run: 'Portfolio valued & market data refreshed',
    risk_run: 'Risk analysis completed',
    briefing_generated: 'First briefing generated',
  };

  function getCookie(name) {
    const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`));
    return match ? decodeURIComponent(match[1]) : '';
  }

  function getAuthToken() {
    try {
      return window.sessionStorage.getItem(AUTH_TOKEN_SESSION_STORAGE_KEY)
        || window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)
        || '';
    } catch {
      return '';
    }
  }

  function saveAuthToken(token, persist = false) {
    try {
      if (token) {
        if (persist) {
          window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
          window.sessionStorage.removeItem(AUTH_TOKEN_SESSION_STORAGE_KEY);
          window.localStorage.setItem(AUTH_STORAGE_PREFERENCE_KEY, 'local');
        } else {
          window.sessionStorage.setItem(AUTH_TOKEN_SESSION_STORAGE_KEY, token);
          window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
          window.localStorage.setItem(AUTH_STORAGE_PREFERENCE_KEY, 'session');
        }
      } else {
        window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
        window.sessionStorage.removeItem(AUTH_TOKEN_SESSION_STORAGE_KEY);
        window.localStorage.removeItem(AUTH_STORAGE_PREFERENCE_KEY);
      }
    } catch {
      // ignore storage failures
    }
  }

  function clearAuthState() {
    saveAuthToken('');
    try {
      sessionStorage.removeItem('crb.user');
      window.localStorage.removeItem(SETTINGS_STORAGE_KEY);
      for (let i = window.localStorage.length - 1; i >= 0; i--) {
        const key = window.localStorage.key(i);
        if (key && (key.startsWith('crb_') || key.startsWith('crb.'))
            && key !== API_BASE_OVERRIDE_STORAGE_KEY) {
          window.localStorage.removeItem(key);
        }
      }
    } catch {
      // ignore storage failures
    }
  }

  function preferredAuthPersistence() {
    try {
      return window.localStorage.getItem(AUTH_STORAGE_PREFERENCE_KEY) === 'local';
    } catch {
      return false;
    }
  }

  function browserTimezone() {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  }

  function isLocalHostname(hostname) {
    const normalized = String(hostname || '').toLowerCase();
    return normalized === 'localhost'
      || normalized === '127.0.0.1'
      || normalized === '0.0.0.0'
      || normalized === '[::1]';
  }

  function normalizeApiBase(value) {
    return String(value || '').trim().replace(/\/$/, '');
  }

  function getStoredApiBaseOverride() {
    try {
      return normalizeApiBase(window.localStorage.getItem(API_BASE_OVERRIDE_STORAGE_KEY) || '');
    } catch {
      return '';
    }
  }

  function getExplicitApiBaseOverride() {
    const queryOverride = normalizeApiBase(new URL(window.location.href).searchParams.get('api_base') || '');
    if (queryOverride) {
      try {
        window.localStorage.setItem(API_BASE_OVERRIDE_STORAGE_KEY, queryOverride);
      } catch {
        // ignore storage failures; redirects still carry the query param
      }
      return queryOverride;
    }
    const runtimeOverride = normalizeApiBase(window.CRB_API_BASE || '');
    if (runtimeOverride) return runtimeOverride;
    return getStoredApiBaseOverride();
  }

  function withApiBaseOverride(target) {
    const override = getExplicitApiBaseOverride();
    if (!override) return target;
    const url = new URL(target, window.location.href);
    url.searchParams.set('api_base', override);
    if (url.origin === window.location.origin) {
      return `${url.pathname.split('/').pop()}${url.search}${url.hash}`;
    }
    return url.toString();
  }

  function getApiBase() {
    const { location } = window;
    const hostname = String(location?.hostname || '').toLowerCase();
    const explicitOverride = getExplicitApiBaseOverride();
    if (explicitOverride) return explicitOverride;
    if (!hostname || location?.protocol === 'file:' || isLocalHostname(hostname)) {
      return '/api';
    }
    if (hostname === 'app.chiefriskbot.com' || hostname.endsWith('.pages.dev')) {
      return PROD_API_BASE;
    }
    return `${location.origin}/api`;
  }

  function resolveApiUrl(path) {
    if (/^https?:\/\//i.test(path)) return path;
    const normalizedPath = path.startsWith('/api')
      ? path.slice('/api'.length)
      : (path.startsWith('/') ? path : `/${path}`);
    return `${getApiBase()}${normalizedPath}`;
  }

  function apiCredentialsMode(url) {
    try {
      const target = new URL(url, window.location.href);
      return target.origin === window.location.origin ? 'include' : 'omit';
    } catch {
      return 'include';
    }
  }

  function markPageReady() {
    document.body.classList.remove('mvp-app-loading');
    document.body.classList.add('mvp-ready');
  }

  function setButtonBusy(button, busy, busyLabel) {
    if (!button) return;
    if (!button.dataset.defaultHtml) {
      button.dataset.defaultHtml = button.innerHTML;
    }
    button.disabled = busy;
    button.classList.toggle('is-loading', busy);
    if (busy) {
      button.innerHTML = `<span class="mvp-inline-spinner" aria-hidden="true"></span>${escapeHtml(busyLabel || 'Working...')}`;
    } else {
      button.innerHTML = button.dataset.defaultHtml;
    }
  }

  async function withButtonBusy(button, busyLabel, task) {
    setButtonBusy(button, true, busyLabel);
    try {
      return await task();
    } finally {
      setButtonBusy(button, false);
    }
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function formatCurrency(value, digits = 0) {
    const rate = REPORTING_FX_RATES[preferredCurrency] || 1;
    const number = Number(value || 0) * rate;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: preferredCurrency,
      maximumFractionDigits: digits,
      minimumFractionDigits: digits,
    }).format(number);
  }

  function formatNumber(value, digits = 0) {
    const number = Number(value || 0);
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: digits,
      minimumFractionDigits: digits,
    }).format(number);
  }

  function formatPct(value, digits = 1) {
    return `${formatNumber(value, digits)}%`;
  }

  function formatAssetClass(value) {
    const key = String(value || '').toLowerCase();
    const labels = {
      public_equity: 'Public Equity',
      fixed_income: 'Fixed Income',
      private_equity: 'Private Equity',
      real_assets: 'Real Assets',
      real_estate: 'Real Estate',
      cash: 'Cash & Equivalents',
      alternative: 'Alternative',
    };
    return labels[key] || key.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function isoWeekStart(year, week) {
    const januaryFourth = new Date(Date.UTC(year, 0, 4));
    const day = januaryFourth.getUTCDay() || 7;
    const monday = new Date(januaryFourth);
    monday.setUTCDate(januaryFourth.getUTCDate() - day + 1 + (week - 1) * 7);
    return monday;
  }

  function formatWeekLabel(value) {
    const match = String(value || '').match(/^week-(\d{1,2})-(\d{4})$/);
    if (!match) return String(value || '');
    const monday = isoWeekStart(Number(match[2]), Number(match[1]));
    const formatter = new Intl.DateTimeFormat('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      timeZone: 'UTC',
    });
    return `Week of ${formatter.format(monday)}`;
  }

  function formatMonthKey(value) {
    const match = String(value || '').match(/^(\d{4})-(\d{2})$/);
    if (!match) return String(value || '');
    const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, 1));
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      year: '2-digit',
      timeZone: 'UTC',
    }).format(date);
  }

  function clampNumber(value, fallback, minimum = Number.NEGATIVE_INFINITY) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.max(minimum, parsed);
  }

  function truncateText(value, maxLength) {
    const text = String(value || '').trim();
    if (!text || text.length <= maxLength) return text;
    return `${text.slice(0, maxLength - 1).trimEnd()}...`;
  }

  function portfolioAum(summary) {
    return Number(summary?.total_aum_usd ?? summary?.total_value ?? 0) || 0;
  }

  function bucketValue(bucket) {
    return Number(bucket?.market_value_usd ?? bucket?.total_value ?? bucket?.value ?? 0) || 0;
  }

  function portfolioPositionCount(summary) {
    const explicit = Number(summary?.position_count);
    if (Number.isFinite(explicit) && explicit > 0) return explicit;
    return (summary?.asset_class || []).reduce((total, bucket) => total + (Number(bucket.position_count) || 0), 0);
  }

  function assetClassBucket(summary, labels) {
    const normalizedLabels = new Set(labels.map((label) => String(label).toLowerCase()));
    return (summary?.asset_class || []).find((bucket) => {
      const label = String(bucket.label || bucket.asset_class || '').toLowerCase();
      return normalizedLabels.has(label);
    }) || null;
  }

  function sumAssetClassBuckets(summary, labels) {
    const normalizedLabels = new Set(labels.map((label) => String(label).toLowerCase()));
    return (summary?.asset_class || []).reduce((total, bucket) => {
      const label = String(bucket.label || bucket.asset_class || '').toLowerCase();
      return normalizedLabels.has(label) ? total + bucketValue(bucket) : total;
    }, 0);
  }

  function pctOfAum(value, summary) {
    const aum = portfolioAum(summary);
    return aum > 0 ? (Number(value || 0) / aum) * 100 : 0;
  }

  function withTransientUpdate(nodes, render) {
    const items = (Array.isArray(nodes) ? nodes : [nodes]).filter(Boolean);
    items.forEach((node) => node.classList.add('is-updating'));
    render();
    window.requestAnimationFrame(() => {
      items.forEach((node) => node.classList.remove('is-updating'));
    });
  }

  function formatCompactCurrency(value) {
    const rate = REPORTING_FX_RATES[preferredCurrency] || 1;
    const number = Number(value || 0) * rate;
    const abs = Math.abs(number);
    const parts = new Intl.NumberFormat('en-US', { style: 'currency', currency: preferredCurrency, maximumFractionDigits: 0 }).formatToParts(0);
    const symbol = parts.find((part) => part.type === 'currency')?.value || preferredCurrency;
    if (abs >= 1_000_000_000) return `${number < 0 ? '-' : ''}${symbol}${formatNumber(abs / 1_000_000_000, 2)}B`;
    if (abs >= 1_000_000) return `${number < 0 ? '-' : ''}${symbol}${formatNumber(abs / 1_000_000, 1)}M`;
    if (abs >= 1_000) return `${number < 0 ? '-' : ''}${symbol}${formatNumber(abs / 1_000, 1)}K`;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: preferredCurrency,
      maximumFractionDigits: 0,
      minimumFractionDigits: 0,
    }).format(number);
  }

  function normalizeCurrencyCode(value) {
    const normalized = String(value || '').trim().toUpperCase();
    return /^[A-Z]{3}$/.test(normalized) ? normalized : DEFAULT_CURRENCY;
  }

  function loadStoredSettings() {
    try {
      return JSON.parse(window.localStorage.getItem(SETTINGS_STORAGE_KEY) || 'null');
    } catch {
      return null;
    }
  }

  function applyWorkspaceSettings(settings) {
    const nextCurrency = normalizeCurrencyCode(settings?.reporting_currency);
    preferredCurrency = nextCurrency;
    try {
      const merged = { ...(loadStoredSettings() || {}), ...(settings || {}), reporting_currency: nextCurrency };
      window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(merged));
    } catch {
      // ignore storage failures
    }
  }

  function parseFormattedNumber(value) {
    const normalized = String(value ?? '')
      .replace(/[^0-9,.-]/g, '')
      .replace(/,(?=\d{3}\b)/g, '')
      .replace(/,/g, '.');
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : NaN;
  }

  function formatNumberInputValue(value, mode = 'decimal') {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return '';
    const digits = mode === 'integer' ? 0 : (Number.isInteger(parsed) ? 0 : 2);
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: digits,
      minimumFractionDigits: 0,
    }).format(parsed);
  }

  function sanitizeNumberInputValue(value, mode = 'decimal') {
    const source = String(value ?? '');
    const hasLeadingMinus = source.trimStart().startsWith('-');
    let normalized = source
      .replace(/,/g, '.')
      .replace(/[^0-9.-]/g, '')
      .replace(/-/g, '');
    if (mode === 'integer') {
      normalized = normalized.replace(/\./g, '');
    } else {
      const dotIndex = normalized.indexOf('.');
      if (dotIndex !== -1) {
        normalized = `${normalized.slice(0, dotIndex + 1)}${normalized.slice(dotIndex + 1).replace(/\./g, '')}`;
      }
    }
    if (hasLeadingMinus) normalized = `-${normalized}`;
    return normalized;
  }

  function attachFormattedNumberInput(input, mode = 'decimal') {
    if (!input || input.dataset.formatBound === 'true') return;
    input.dataset.formatBound = 'true';
    input.setAttribute('inputmode', mode === 'integer' ? 'numeric' : 'decimal');
    input.setAttribute('pattern', mode === 'integer' ? '^-?[0-9]*$' : '^-?[0-9]*[.,]?[0-9]*$');

    const sync = () => {
      const parsed = parseFormattedNumber(input.value);
      if (Number.isFinite(parsed)) {
        input.value = formatNumberInputValue(parsed, mode);
      }
    };

    input.addEventListener('focus', () => {
      const parsed = parseFormattedNumber(input.value);
      if (Number.isFinite(parsed)) input.value = String(parsed);
    });
    input.addEventListener('input', () => {
      const sanitized = sanitizeNumberInputValue(input.value, mode);
      if (sanitized !== input.value) input.value = sanitized;
    });
    input.addEventListener('blur', sync);
    sync();
  }

  function bindFormattedNumberInputs(root = document) {
    root.querySelectorAll('input[data-format="integer"], input[data-format="decimal"]').forEach((input) => {
      attachFormattedNumberInput(input, input.dataset.format || 'decimal');
    });
  }

  function bindFileDropzones(root = document) {
    root.querySelectorAll('[data-file-dropzone]').forEach((zone) => {
      if (zone.dataset.dropzoneBound === 'true') return;
      zone.dataset.dropzoneBound = 'true';
      const inputId = zone.dataset.inputId || '';
      const input = inputId ? document.getElementById(inputId) : zone.querySelector('input[type="file"]');
      const selected = zone.querySelector('[data-file-selected]');
      if (!input) return;

      const syncSelected = () => {
        const file = input.files?.[0];
        if (selected) {
          selected.textContent = file ? `${file.name} · ${formatNumber(file.size || 0, 0)} bytes` : 'No file selected';
        }
      };

      const stop = (event) => {
        event.preventDefault();
        event.stopPropagation();
      };

      ['dragenter', 'dragover'].forEach((name) => {
        zone.addEventListener(name, (event) => {
          stop(event);
          zone.classList.add('is-dragover');
        });
      });
      ['dragleave', 'dragend', 'drop'].forEach((name) => {
        zone.addEventListener(name, (event) => {
          stop(event);
          zone.classList.remove('is-dragover');
        });
      });
      zone.addEventListener('drop', (event) => {
        const files = event.dataTransfer?.files;
        if (!files?.length) return;
        input.files = files;
        input.dispatchEvent(new Event('change', { bubbles: true }));
      });
      input.addEventListener('change', syncSelected);
      syncSelected();
    });
  }

  function formatDateTime(value) {
    if (!value) return 'Live';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Live';
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(date);
  }

  function buildPositionIdentifier(tickerValue, nameValue) {
    const explicit = String(tickerValue || '').trim().toUpperCase();
    if (explicit) return explicit;
    const normalized = String(nameValue || '')
      .toUpperCase()
      .replace(/[^A-Z0-9]+/g, '')
      .slice(0, 12);
    return normalized || `POS${Date.now().toString().slice(-6)}`;
  }

  function isRecentTimestamp(value, windowMs = 15 * 60 * 1000) {
    if (!value) return false;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return false;
    return Math.abs(Date.now() - date.getTime()) <= windowMs;
  }

  function titleCase(value) {
    return String(value || '')
      .replaceAll('_', ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function normalizeWeekday(value, fallback = 'Monday') {
    const normalized = String(value || '').trim().toLowerCase();
    const weekdays = {
      monday: 'Monday',
      tuesday: 'Tuesday',
      wednesday: 'Wednesday',
      thursday: 'Thursday',
      friday: 'Friday',
      saturday: 'Saturday',
      sunday: 'Sunday',
    };
    return weekdays[normalized] || fallback;
  }

  function severityClass(value) {
    const normalized = String(value || '').toLowerCase();
    if (normalized === 'priority') return 'priority';
    if (normalized === 'elevated') return 'elevated';
    if (normalized === 'stress') return 'elevated';
    if (normalized === 'crisis') return 'priority';
    if (normalized === 'watch') return 'watch';
    return 'good';
  }

  function confidenceTone(value) {
    const score = Number(value || 0);
    if (score >= 0.9) return 'good';
    if (score >= 0.75) return 'watch';
    if (score >= 0.5) return 'elevated';
    return 'priority';
  }

  function qualityTone(gate) {
    if (!gate) return 'watch';
    if (gate.publish_ready) return 'good';
    return (gate.blocking_reasons || []).length ? 'elevated' : 'watch';
  }

  function qualitySummary(gate) {
    if (!gate) return 'Manual review recommended';
    return gate.summary || (gate.publish_ready ? 'Publish ready' : 'Manual review required');
  }

  function briefingPortfolioSummary(output) {
    const snapshot = output?.portfolio_snapshot || {};
    const liquidity = output?.liquidity_snapshot || {};
    const parts = [];
    if (snapshot.total_aum_usd != null) {
      parts.push(`Portfolio AUM is ${formatCurrency(snapshot.total_aum_usd)}.`);
    }
    if (output?.var_commentary) {
      const varText = String(output.var_commentary)
        .replace(/\$[\d,]+(?:\.\d+)?/g, (match) => {
          const value = Number(match.replace(/[$,]/g, ''));
          return Number.isFinite(value) ? formatCurrency(value) : match;
        });
      parts.push(varText);
    }
    if (liquidity.buffer_breach != null) {
      parts.push(
        liquidity.buffer_breach
          ? `Liquidity buffer is short by ${formatCurrency(liquidity.buffer_gap_usd || 0)}.`
          : `Liquidity buffer remains intact with ${formatCurrency(liquidity.projected_cash_usd || 0)} projected cash.`
      );
    }
    return parts.join(' ');
  }

  function briefingDisplaySummary(output) {
    return briefingPortfolioSummary(output) || output?.executive_summary || briefingSummary(output);
  }

  function briefingDisplayLiquidity(output) {
    const liq = output?.liquidity_snapshot;
    if (!liq) return output?.liquidity_commentary || '';
    const nextCall = liq.next_call_due_date
      ? `Next capital call: ${formatCurrency(liq.next_call_amount_usd || 0)} on ${liq.next_call_due_date}.`
      : 'No capital call is currently scheduled.';
    return [
      nextCall,
      `Expected 90-day distributions: ${formatCurrency(liq.expected_distributions_usd || 0)}.`,
      `Net 90-day liquidity: ${formatCurrency(liq.net_liquidity_usd || 0)}.`,
      liq.buffer_breach
        ? `Buffer breach projected: ${formatCurrency(liq.buffer_gap_usd || 0)} shortfall.`
        : 'Buffer remains intact.',
    ].join(' ');
  }

  function renderQualityNote(gate) {
    if (!gate) return '';
    const blocking = gate.blocking_messages || [];
    const warnings = gate.warning_messages || [];
    return `
      <div class="mvp-quality-note">
        <div class="mvp-feature-meta">
          <span class="mvp-pill ${qualityTone(gate)}">${escapeHtml(qualitySummary(gate))}</span>
          <span>${escapeHtml(`Score ${formatNumber(gate.score || 0, 0)}/100`)}</span>
          <span>${escapeHtml(`${formatNumber(gate.agent_success_count || 0, 0)} of ${formatNumber(gate.expected_agent_count || 0, 0)} agents completed`)}</span>
        </div>
        ${(blocking.length || warnings.length) ? `
          <div class="mvp-quality-list">
            ${blocking.map((item) => `<span>${escapeHtml(item)}</span>`).join('')}
            ${warnings.map((item) => `<span>${escapeHtml(item)}</span>`).join('')}
          </div>
        ` : ''}
      </div>
    `;
  }

  function setStatus(node, message, tone) {
    if (!node) return;
    if (node._successTimer) {
      window.clearTimeout(node._successTimer);
      node._successTimer = null;
    }
    node.className = `mvp-notice${tone ? ` ${tone}` : ''}`;
    node.textContent = message;
    node.hidden = !message;
    if (message && tone === 'success') {
      node._successTimer = window.setTimeout(() => {
        setStatus(node, '', '');
      }, 3000);
    }
  }

  function setEnabled(node, enabled) {
    if (!node) return;
    node.disabled = !enabled;
  }

  function parseDownloadFilename(headerValue, fallback) {
    if (!headerValue) return fallback;
    const utf8Match = headerValue.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match) return decodeURIComponent(utf8Match[1]);
    const simpleMatch = headerValue.match(/filename="?([^";]+)"?/i);
    return simpleMatch ? simpleMatch[1] : fallback;
  }

  async function readApiPayload(response, { expectJson = true } = {}) {
    const contentType = response.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');

    if (expectJson) {
      if (!isJson) {
        const sample = (await response.text()).trim().slice(0, 120);
        const suffix = sample ? ` Received: ${sample}` : '';
        throw new Error(`API routing error: expected JSON from ${response.url}.${suffix}`);
      }
      return response.json();
    }

    if (isJson) return response.json();
    return response.text();
  }

  async function api(path, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = new Headers(options.headers || {});
    let body = options.body;
    const url = resolveApiUrl(path);

    if (options.formData) {
      body = options.formData;
    } else if (options.body !== undefined && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    if (options.body !== undefined && headers.get('Content-Type') === 'application/json') {
      body = JSON.stringify(options.body);
    }

    if (method !== 'GET') {
      const csrf = getCookie('__crb_csrf');
      if (csrf && !headers.has('X-CSRF-Token')) {
        headers.set('X-CSRF-Token', csrf);
      }
    }

    const token = getAuthToken();
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const response = await fetch(url, {
      method,
      headers,
      body,
      credentials: apiCredentialsMode(url),
    });
    const payload = await readApiPayload(response);

    if (!response.ok) {
      const detail =
        typeof payload === 'object' && payload && 'detail' in payload
          ? payload.detail
          : typeof payload === 'string'
            ? payload
            : `Request failed (${response.status})`;
      throw new Error(detail);
    }

    return payload;
  }

  async function download(path, fallbackName) {
    const headers = new Headers();
    const token = getAuthToken();
    const url = resolveApiUrl(path);
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    const response = await fetch(url, {
      headers,
      credentials: apiCredentialsMode(url),
    });
    if (!response.ok) {
      const payload = await readApiPayload(response, { expectJson: false });
      const detail =
        typeof payload === 'object' && payload && 'detail' in payload
          ? payload.detail
          : typeof payload === 'string'
            ? payload
            : `Request failed (${response.status})`;
      throw new Error(detail);
    }

    const blob = await response.blob();
    const filename = parseDownloadFilename(
      response.headers.get('content-disposition'),
      fallbackName
    );
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    return filename;
  }

  async function fetchBlob(path) {
    const headers = new Headers();
    const token = getAuthToken();
    const url = resolveApiUrl(path);
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    const response = await fetch(url, {
      headers,
      credentials: apiCredentialsMode(url),
    });
    if (!response.ok) {
      const payload = await readApiPayload(response, { expectJson: false });
      const detail =
        typeof payload === 'object' && payload && 'detail' in payload
          ? payload.detail
          : typeof payload === 'string'
            ? payload
            : `Request failed (${response.status})`;
      throw new Error(detail);
    }
    return {
      blob: await response.blob(),
      contentType: response.headers.get('content-type') || '',
      filename: parseDownloadFilename(response.headers.get('content-disposition'), 'document'),
    };
  }

  async function getSession(retries = 0) {
    try {
      const session = await api('/auth/session');
      if (!session || typeof session !== 'object' || !session.user) {
        throw new Error('Invalid session payload');
      }
      sessionStorage.setItem('crb.user', JSON.stringify(session.user));
      return session.user;
    } catch (error) {
      const shouldRetry = retries > 0
        && Boolean(getAuthToken())
        && /invalid session/i.test(String(error.message || ''));
      if (!shouldRetry) throw error;
      await new Promise((resolve) => window.setTimeout(resolve, 250));
      return getSession(retries - 1);
    }
  }

  async function requireSession(activePage, crumbs) {
    let user;
    try {
      user = await getSession(3);
    } catch {
      window.location.href = withApiBaseOverride(`login.html?next=${encodeURIComponent(window.location.pathname.split('/').pop() || 'cockpit.html')}`);
      return null;
    }

    try {
      applyWorkspaceSettings(await api('/settings'));
    } catch {
      applyWorkspaceSettings(loadStoredSettings() || { reporting_currency: DEFAULT_CURRENCY });
    }

    if (window.CRBMvpShell) {
      window.CRBMvpShell.mount(activePage, crumbs);
      window.CRBMvpShell.updateUser(user);

      const logout = document.getElementById('mvp-logout');
      if (logout) {
        logout.addEventListener('click', async () => {
          try {
            if (!getAuthToken()) {
              await api('/auth/logout', { method: 'POST' });
            }
          } catch {
            // ignore
          }
          clearAuthState();
          window.location.href = withApiBaseOverride('login.html');
        });
      }

      // Expose api for drawer history loader
      window.CRBApi = api;

      // Wire generate briefing button in drawer
      const genBtn = document.getElementById('crb-drawer-generate-btn');
      if (genBtn) {
        genBtn.addEventListener('click', async () => {
          const scope = genBtn.dataset.scope || 'full';
          genBtn.disabled = true;
          const progress = document.getElementById('crb-drawer-progress');
          const result = document.getElementById('crb-drawer-result');
          if (progress) { progress.hidden = false; progress.textContent = 'Generating briefing…'; }
          if (result) result.hidden = true;
          try {
            const data = await api(`/briefings/generate?scope=${encodeURIComponent(scope)}`, { method: 'POST' });
            if (progress) progress.hidden = true;
            if (result) {
              result.hidden = false;
              result.innerHTML = `
                <div style="margin-top:20px;padding:16px;background:rgba(232,241,234,.4);border-radius:4px;font-family:'Inter Tight',sans-serif;font-size:13px;color:#3F7A4F;">
                  <strong>Briefing ready.</strong><br>
                  <a href="briefing.html?id=${encodeURIComponent(data.id || '')}" style="color:#1B2B5E;text-decoration:underline;margin-top:8px;display:inline-block;">Open full briefing →</a>
                </div>`;
            }
          } catch (err) {
            if (progress) { progress.hidden = false; progress.textContent = `Error: ${err.message || 'Could not generate briefing.'}`; }
          } finally {
            genBtn.disabled = false;
          }
        });
      }
    }

    return user;
  }

  function getQueryParam(name) {
    return new URL(window.location.href).searchParams.get(name);
  }

  function stepMarkup(state) {
    const completed = new Set(state.completed_steps || []);
    const steps = Object.keys(STEP_LABELS).map((step) => {
      const done = completed.has(step);
      const active = state.next_step === step;
      return `
        <div class="mvp-item">
          <div>
            <div class="mvp-item-title">${escapeHtml(STEP_LABELS[step])}</div>
            <div class="mvp-item-subtle">${escapeHtml(step)}</div>
          </div>
          <span class="mvp-pill ${done ? 'good' : active ? 'elevated' : ''}">${done ? 'done' : active ? 'next' : 'pending'}</span>
        </div>
      `;
    });
    return steps.join('');
  }

  function onboardingStepperMarkup(state) {
    const completed = new Set(state.completed_steps || []);
    return Object.keys(STEP_LABELS)
      .map((step, index, steps) => {
        const done = completed.has(step);
        const active = !done && state.next_step === step;
        return `
          <div class="mvp-onboarding-step ${done ? 'is-done' : active ? 'is-active' : ''}">
            <div class="mvp-onboarding-step-badge">${done ? '<span class="ms">check</span>' : index + 1}</div>
            <div>
              <div class="mvp-onboarding-step-label">${escapeHtml(STEP_LABELS[step])}</div>
              <div class="mvp-item-subtle">${done ? 'Complete' : active ? 'Current focus' : 'Queued'}</div>
            </div>
          </div>
          ${index < steps.length - 1 ? '<div class="mvp-onboarding-step-rail"></div>' : ''}
        `;
      })
      .join('');
  }

  function documentStatusTone(value) {
    const normalized = String(value || '').toLowerCase();
    if (normalized === 'done' || normalized === 'approved') return 'good';
    if (normalized === 'failed') return 'priority';
    if (normalized === 'needs_review') return 'elevated';
    return 'watch';
  }

  function documentStatusLabel(value) {
    const normalized = String(value || '').toLowerCase();
    const labels = {
      pending: 'Queued',
      processing: 'Parsing',
      done: 'Ready for review',
      needs_review: 'Needs review',
      approved: 'Approved',
      failed: 'Parse failed',
    };
    return labels[normalized] || titleCase(normalized || 'pending');
  }

  function documentStatusDescription(documentRecord, extraction) {
    const normalized = String(documentRecord?.extraction_status || '').toLowerCase();
    if (normalized === 'done') {
      return extraction
        ? `${formatNumber(extraction.positions?.length || 0, 0)} candidate rows extracted. Review and approve when ready.`
        : 'Extraction completed. Review and approve the output.';
    }
    if (normalized === 'needs_review') {
      return 'One or more fields need human confirmation before approval.';
    }
    if (normalized === 'failed') {
      return 'The parser could not finish this document. Re-run parse after checking the file.';
    }
    return 'The file is stored and ready to be parsed into reviewable holdings.';
  }

  async function markOnboardingStep(step) {
    return api('/onboarding/step', { method: 'POST', body: { step } });
  }

  async function resolveAuthenticatedLanding(useNext = false) {
    const next = useNext ? getQueryParam('next') : '';
    if (next) return withApiBaseOverride(next);
    let attempts = 3;
    while (attempts > 0) {
      try {
        const state = await api('/onboarding/state');
        return withApiBaseOverride(state.is_complete ? 'cockpit.html' : 'onboarding.html');
      } catch (error) {
        attempts -= 1;
        const transient = attempts > 0
          && Boolean(getAuthToken())
          && /invalid session/i.test(String(error.message || ''));
        if (!transient) throw error;
        await new Promise((resolve) => window.setTimeout(resolve, 250));
      }
    }
    return withApiBaseOverride('onboarding.html');
  }

  // ── Shared rendering helpers ─────────────────────────────────────────────

  function initScrollReveal(bodyEl) {
    if (!bodyEl) return;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('is-visible'); observer.unobserve(e.target); } });
    }, { threshold: 0.10 });
    bodyEl.querySelectorAll('.essay-section:not(.is-visible)').forEach((el) => observer.observe(el));
  }

  function renderBriefingBody(bodyEl, output, tocEl) {
    if (!bodyEl) return;
    const summaryText = briefingDisplaySummary(output);
    const liquidityText = briefingDisplayLiquidity(output);
    const sections = [
      summaryText && {
        id: 'summary', eyebrow: 'Executive Summary', heading: 'The week in one breath',
        html: `<div class="essay-prose"><p class="essay-deck">${escapeHtml(summaryText)}</p></div>`,
      },
      output.market_context && {
        id: 'context', eyebrow: 'Market Context', heading: 'What the tape is saying',
        html: `<div class="essay-prose"><p>${escapeHtml(output.market_context).replace(/\n\n+/g, '</p><p>')}</p></div>`,
      },
      (output.portfolio_risks || []).length && {
        id: 'risks', eyebrow: 'Portfolio Risks', heading: 'Where the exposure sits',
        html: (output.portfolio_risks || []).map((item) => `
          <div class="essay-risk">
            <div class="essay-risk-head">
              <div class="essay-risk-title">${escapeHtml(item.risk_area)}</div>
              <div class="essay-risk-sev">${escapeHtml(item.severity)}</div>
            </div>
            <div class="essay-risk-finding">${escapeHtml(item.finding)}</div>
            ${item.implication ? `<div class="essay-risk-implication">${escapeHtml(item.implication)}</div>` : ''}
          </div>`).join(''),
      },
      (output.recommendations || []).length && {
        id: 'recs', eyebrow: 'Recommendations', heading: 'What to do next',
        html: `<ol class="essay-recs">${(output.recommendations || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ol>`,
      },
      liquidityText && {
        id: 'liquidity', eyebrow: 'Liquidity', heading: 'Cash and commitments',
        html: `<div class="essay-prose"><p>${escapeHtml(liquidityText)}</p></div>`,
      },
    ].filter(Boolean);

    bodyEl.innerHTML = sections.map((s) => `
      <section class="essay-section" id="home-sec-${s.id}">
        <div class="essay-eyebrow">${s.eyebrow}</div>
        <h2 class="essay-heading">${s.heading}</h2>
        ${s.html}
      </section>`).join('');

    if (tocEl) {
      tocEl.innerHTML = '<div class="essay-toc-label">Today\'s briefing</div>'
        + sections.map((s) => `<a href="#home-sec-${s.id}">${s.eyebrow}</a>`).join('');
    }

    initScrollReveal(bodyEl);
  }

  function renderCompositionDonut(containerEl, buckets, palette) {
    if (!containerEl || !buckets || !buckets.length) return;
    const size = 200;
    const r = 70;
    const cx = size / 2;
    const cy = size / 2;
    const tau = 2 * Math.PI;
    let cursor = -Math.PI / 2;

    function arc(startAngle, endAngle, radius) {
      const x1 = cx + radius * Math.cos(startAngle);
      const y1 = cy + radius * Math.sin(startAngle);
      const x2 = cx + radius * Math.cos(endAngle);
      const y2 = cy + radius * Math.sin(endAngle);
      const large = (endAngle - startAngle) > Math.PI ? 1 : 0;
      return `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2}`;
    }

    const total = buckets.reduce((s, b) => s + (bucketValue(b) || b.pct_of_portfolio || 0), 0);
    const paths = buckets.map((b, i) => {
      const share = total > 0 ? (bucketValue(b) || b.pct_of_portfolio || 0) / total : 0;
      const sweep = share * tau;
      const startAngle = cursor;
      cursor += sweep;
      const color = palette[i % palette.length];
      return `<path d="${arc(startAngle, cursor, r)}" fill="none" stroke="${color}" stroke-width="28" opacity="0.9"/>`;
    }).join('');

    const legend = buckets.slice(0, 6).map((b, i) => {
      const label = titleCase(b.label || b.asset_class || '');
      const pct = formatNumber(b.pct_of_portfolio || 0, 1);
      return `<div class="mvp-cockpit-legend-item"><span class="mvp-cockpit-legend-dot" style="background:${palette[i % palette.length]}"></span><span>${escapeHtml(label)}</span><span class="mvp-cockpit-legend-pct">${pct}%</span></div>`;
    }).join('');

    containerEl.innerHTML = `
      <div class="mvp-cockpit-donut-wrap">
        <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" aria-hidden="true">${paths}</svg>
        <div class="mvp-cockpit-legend">${legend}</div>
      </div>`;
  }

  async function initIndex() {
    const user = await requireSession('index', ['Home']);
    if (!user) return;

    // Check onboarding completion — redirect if not done
    try {
      const state = await api('/onboarding/state');
      if (!state.is_complete) { window.location.href = 'onboarding.html'; return; }
    } catch { /* proceed */ }

    // Personalise headline
    const name = user.display_name ? user.display_name.split(' ')[0] : null;
    const headline = document.getElementById('home-headline');
    if (headline && name) headline.textContent = `Good morning, ${name}.`;

    const eyebrow = document.getElementById('home-eyebrow');
    if (eyebrow) {
      const d = new Date();
      eyebrow.textContent = `Today · ${d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}`;
    }

    // Load cockpit + liquidity data in parallel for the metric strip
    const [cockpitData, liquidityData] = await Promise.allSettled([
      api('/cockpit'),
      api('/liquidity/summary'),
    ]);
    let homePortfolioSummary = {};

    if (cockpitData.status === 'fulfilled') {
      const body = cockpitData.value;
      const ps = body?.portfolio_summary || {};
      homePortfolioSummary = ps;

      const aum = document.getElementById('home-aum');
      if (aum) aum.textContent = formatCurrency(portfolioAum(ps));

      const conc = document.getElementById('home-concentration');
      const concSub = document.getElementById('home-concentration-sub');
      const buckets = (ps.asset_class || []).sort((a, b) => b.pct_of_portfolio - a.pct_of_portfolio);
      if (buckets.length && conc) {
        conc.textContent = `${formatNumber(buckets[0].pct_of_portfolio || 0, 1)}%`;
        if (concSub) concSub.textContent = titleCase(buckets[0].label || buckets[0].asset_class || '');
      }

      const varEl = document.getElementById('home-var');
      const varSub = document.getElementById('home-var-sub');
      if (body?.var_result && varEl) {
        varEl.textContent = formatCurrency(body.var_result.var_1d_95 ?? body.var_result.var_95 ?? 0);
        if (varSub) varSub.textContent = '95% confidence, 1-day';
      }

      const alertsEl = document.getElementById('home-alerts');
      const alertsSub = document.getElementById('home-alerts-sub');
      const flags = body?.risk_flags || body?.risk_register || [];
      const priorityCount = flags.filter((f) => f.severity === 'priority').length;
      if (alertsEl) {
        alertsEl.textContent = flags.length;
        alertsEl.classList.toggle('essay-metric-badge', priorityCount > 0);
      }
      if (alertsSub) alertsSub.textContent = priorityCount > 0 ? `${priorityCount} priority` : 'No priority alerts';
    }

    if (liquidityData.status === 'fulfilled') {
      const liq = liquidityData.value;
      const cashEl = document.getElementById('home-cash');
      const cashSub = document.getElementById('home-cash-sub');
      const cashOnHand = Number(liq?.cash_on_hand_usd ?? liq?.cash_balance ?? 0) || 0;
      if (cashEl) {
        cashEl.textContent = formatCurrency(cashOnHand);
        if (cashSub) {
          const pct = liq?.cash_pct_of_portfolio ?? pctOfAum(cashOnHand, homePortfolioSummary);
          cashSub.textContent = pct != null ? `${formatNumber(pct, 1)}% of AUM` : '';
        }
      }
    }

    // Load latest briefing after the shell is visible.
    const briefingBody = document.getElementById('home-briefing-body');
    const deck = document.getElementById('home-deck');
    try {
      const result = await api('/briefings?limit=1');
      const items = result.items || result.briefings || result || [];
      const latest = items[0];
      if (latest) {
        const output = latest.output || {};
        if (deck) deck.textContent = briefingDisplaySummary(output);
        if (briefingBody) renderBriefingBody(briefingBody, output, document.getElementById('home-toc'));
      } else if (briefingBody) {
        briefingBody.innerHTML = `
          <div class="essay-section is-visible">
            <div class="essay-eyebrow">Today's briefing</div>
            <div class="essay-heading">No briefing yet.</div>
            <p class="essay-prose">Generate your first briefing using the button in the nav bar.</p>
          </div>`;
      }
    } catch {
      if (briefingBody) {
        briefingBody.innerHTML = `<div class="essay-section is-visible"><div class="essay-eyebrow">Today's briefing</div><p class="essay-prose">Could not load briefing data.</p></div>`;
      }
    }
    markPageReady();
  }

  async function initAssets() {
    const user = await requireSession('assets', ['Assets Overview']);
    if (!user) return;

    const statusEl = document.getElementById('assets-status');
    const asOf = document.getElementById('assets-as-of');

    let cockpitBody = null;
    try {
      cockpitBody = await api('/cockpit');
      if (asOf) asOf.textContent = `as of ${new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
    } catch (err) {
      setStatus(statusEl, err.message, 'error');
      markPageReady();
      return;
    }

    const ps = cockpitBody?.portfolio_summary || {};
    const kpis = document.getElementById('assets-kpis');
    if (kpis) {
      const publicEquity = assetClassBucket(ps, ['public_equity', 'Public Equity']);
      const privateAlternativesValue = sumAssetClassBuckets(ps, ['private_equity', 'alternative', 'real_assets', 'real_estate']);
      const cashFixedIncomeValue = sumAssetClassBuckets(ps, ['cash', 'fixed_income']);
      kpis.innerHTML = [
        { label: 'Total AUM', value: formatCurrency(portfolioAum(ps)), meta: `${formatNumber(portfolioPositionCount(ps), 0)} positions` },
        { label: 'Public Equity', value: formatCurrency(bucketValue(publicEquity)), meta: formatPct(publicEquity?.pct_of_portfolio || pctOfAum(bucketValue(publicEquity), ps)) },
        { label: 'Private / Alternatives', value: formatCurrency(privateAlternativesValue), meta: formatPct(pctOfAum(privateAlternativesValue, ps)) },
        { label: 'Cash & Fixed Income', value: formatCurrency(cashFixedIncomeValue), meta: formatPct(pctOfAum(cashFixedIncomeValue, ps)) },
      ].map((k) => `
        <div class="mvp-kpi">
          <div class="uplabel">${escapeHtml(k.label)}</div>
          <div class="value">${escapeHtml(k.value)}</div>
          <div class="meta">${escapeHtml(k.meta)}</div>
        </div>`).join('');
    }

    // Composition donut (reuse cockpit renderer helper)
    const compositionChart = document.getElementById('assets-composition-chart');
    const compositionPalette = ['#1B2B5E', '#72594c', '#C9A449', '#006972', '#d3c3bc', '#8f6f9d'];
    if (compositionChart && ps.asset_class) renderCompositionDonut(compositionChart, ps.asset_class, compositionPalette);

    // Slicing tables
    const sliceToggles = document.getElementById('assets-slice-toggles');
    const sliceTitle = document.getElementById('assets-slice-title');
    const sliceTable = document.getElementById('assets-slice-table');
    const dimTitles = { asset_class: 'By Asset Class', sector: 'By Sector', geo_region: 'By Region', custodian: 'By Custodian' };
    let activeDimension = 'asset_class';

    function renderSliceTable(dimension) {
      const buckets = ps[dimension] || [];
      if (!sliceTable) return;
      if (!buckets.length) { sliceTable.innerHTML = '<p style="color:var(--ink-mute);font-size:13px">No data for this dimension.</p>'; return; }
      sliceTable.innerHTML = `
        <table class="essay-table">
          <thead><tr><th>Category</th><th class="num">Market Value</th><th class="num">% of AUM</th><th class="num">Positions</th></tr></thead>
          <tbody>${buckets.map((b) => `
            <tr>
              <td>${escapeHtml(titleCase(b.label || b.asset_class || b.sector || b.geo_region || b.custodian || ''))}</td>
              <td class="num">${escapeHtml(formatCurrency(bucketValue(b)))}</td>
              <td class="num">${escapeHtml(formatNumber(b.pct_of_portfolio || 0, 1))}%</td>
              <td class="num">${escapeHtml(formatNumber(b.position_count || 0, 0))}</td>
            </tr>`).join('')}
          </tbody>
        </table>`;
    }

    if (sliceToggles) {
      sliceToggles.querySelectorAll('.essay-pill').forEach((btn) => {
        btn.addEventListener('click', () => {
          activeDimension = btn.dataset.dimension;
          sliceToggles.querySelectorAll('.essay-pill').forEach((b) => b.classList.toggle('active', b === btn));
          if (sliceTitle) sliceTitle.textContent = dimTitles[activeDimension] || 'Composition';
          renderSliceTable(activeDimension);
        });
      });
    }
    renderSliceTable(activeDimension);

    // Projections — use liquidity data
    const projSummary = document.getElementById('assets-proj-summary');
    try {
      const liq = await api('/liquidity/summary');
      if (projSummary) {
        const cashBal = formatCurrency(liq?.cash_on_hand_usd || 0);
        const next90 = formatCurrency(liq?.net_liquidity_usd || 0);
        const bufferText = liq?.buffer_breach
          ? `Projected cash is ${formatCurrency(liq.projected_cash_usd || 0)}, leaving a ${formatCurrency(liq.buffer_gap_usd || 0)} shortfall to the buffer.`
          : `Projected cash is ${formatCurrency(liq?.projected_cash_usd || 0)}, above the target buffer.`;
        projSummary.textContent = `Current cash position is ${cashBal}. Net cash flow over the next 90 days is projected at ${next90}. ${bufferText} Detailed cash flow ladder available on the Liquidity page.`;
      }
    } catch {
      if (projSummary) projSummary.textContent = 'Liquidity projection data unavailable. Visit the Liquidity page for cash flow detail.';
    }

    // Scroll reveal
    initScrollReveal(document.getElementById('assets-section-agg')?.closest('.essay-body'));
    markPageReady();
  }

  async function initLogin() {
    applyWorkspaceSettings(loadStoredSettings() || { reporting_currency: DEFAULT_CURRENCY });
    if (getAuthToken() || getCookie('__crb_session')) {
      try {
        await getSession(3);
        window.location.href = await resolveAuthenticatedLanding(true);
        return;
      } catch {
        clearAuthState();
      }
    }

    const status = document.getElementById('login-status');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const forgotForm = document.getElementById('forgot-password-form');
    const loginSubmit = document.getElementById('login-submit');
    const registerSubmit = document.getElementById('register-submit');
    const forgotSubmit = document.getElementById('forgot-submit');
    const authTabs = Array.from(document.querySelectorAll('[data-auth-mode]'));
    const authPanels = Array.from(document.querySelectorAll('[data-auth-panel]'));
    const showReset = document.getElementById('show-reset');
    const loginRemember = document.getElementById('login-remember');
    const registerRemember = document.getElementById('register-remember');
    const timezoneLabel = document.getElementById('register-timezone');
    const loginEmail = document.getElementById('email');
    const loginPassword = document.getElementById('password');
    const registerWorkspaceName = document.getElementById('register-workspace-name');
    const registerName = document.getElementById('register-name');
    const registerEmail = document.getElementById('register-email');
    const registerPassword = document.getElementById('register-password');
    const registerCurrency = document.getElementById('register-reporting-currency');
    const forgotEmail = document.getElementById('forgot-email');
    let authMode = 'sign-in';

    function setAuthMode(nextMode) {
      authMode = nextMode;
      authTabs.forEach((tab) => {
        const active = tab.dataset.authMode === nextMode;
        tab.classList.toggle('is-active', active);
        tab.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      authPanels.forEach((panel) => {
        panel.hidden = panel.dataset.authPanel !== nextMode;
      });
      setStatus(status, '', '');
    }

    const persistDefault = preferredAuthPersistence();
    if (loginRemember) loginRemember.checked = persistDefault;
    if (registerRemember) registerRemember.checked = persistDefault;
    if (timezoneLabel) timezoneLabel.textContent = browserTimezone();
    setStatus(status, 'Sign in with a live workspace or create a new Supabase-backed workspace.', '');
    setAuthMode(getQueryParam('mode') === 'reset' ? 'reset' : 'sign-in');

    authTabs.forEach((tab) => {
      tab.addEventListener('click', () => setAuthMode(tab.dataset.authMode || 'sign-in'));
    });
    showReset?.addEventListener('click', () => setAuthMode('reset'));

    async function handleLoginSubmit() {
      setStatus(status, '', '');
      await withButtonBusy(loginSubmit, 'Signing in...', async () => {
        const login = await api('/auth/login', {
          method: 'POST',
          body: {
            email: loginEmail.value.trim(),
            password: loginPassword.value,
          },
        });
        saveAuthToken(login.access_token || '', loginRemember?.checked);
        if (login.user) {
          sessionStorage.setItem('crb.user', JSON.stringify(login.user));
        }
        window.location.href = await resolveAuthenticatedLanding(true);
      });
    }

    loginForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      try {
        await handleLoginSubmit();
      } catch (error) {
        clearAuthState();
        setStatus(status, error.message, 'error');
      }
    });

    loginSubmit?.addEventListener('click', async (event) => {
      if (event.detail === 0) return;
      event.preventDefault();
      if (loginForm?.reportValidity && !loginForm.reportValidity()) return;
      try {
        await handleLoginSubmit();
      } catch (error) {
        clearAuthState();
        setStatus(status, error.message, 'error');
      }
    });

    async function handleRegisterSubmit() {
      setStatus(status, '', '');
      await withButtonBusy(registerSubmit, 'Creating workspace...', async () => {
        const response = await api('/auth/register', {
          method: 'POST',
          body: {
            workspace_name: registerWorkspaceName.value.trim(),
            display_name: registerName.value.trim(),
            email: registerEmail.value.trim(),
            password: registerPassword.value,
            timezone: browserTimezone(),
            reporting_currency: registerCurrency.value,
          },
        });
        saveAuthToken(response.access_token || '', registerRemember?.checked);
        if (response.user) {
          sessionStorage.setItem('crb.user', JSON.stringify(response.user));
        }
        window.location.href = await resolveAuthenticatedLanding(true);
      });
    }

    registerForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      try {
        await handleRegisterSubmit();
      } catch (error) {
        clearAuthState();
        setStatus(status, error.message, 'error');
      }
    });

    registerSubmit?.addEventListener('click', async (event) => {
      if (event.detail === 0) return;
      event.preventDefault();
      if (registerForm?.reportValidity && !registerForm.reportValidity()) return;
      try {
        await handleRegisterSubmit();
      } catch (error) {
        clearAuthState();
        setStatus(status, error.message, 'error');
      }
    });

    async function handleForgotSubmit() {
      setStatus(status, '', '');
      await withButtonBusy(forgotSubmit, 'Sending reset...', async () => {
        await api('/auth/forgot-password', {
          method: 'POST',
          body: { email: forgotEmail.value.trim() },
        });
      });
      setStatus(status, 'If that email exists, a reset flow has been accepted for the workspace.', 'success');
    }

    forgotForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      try {
        await handleForgotSubmit();
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    forgotSubmit?.addEventListener('click', async (event) => {
      if (event.detail === 0) return;
      event.preventDefault();
      if (forgotForm?.reportValidity && !forgotForm.reportValidity()) return;
      try {
        await handleForgotSubmit();
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });
  }

  async function initOnboarding() {
    const user = await requireSession('onboarding.html', ['Workspace', 'Onboarding']);
    if (!user) return;
    bindFileDropzones(document);

    const stateNode = document.getElementById('onboarding-steps');
    const status = document.getElementById('onboarding-status');
    const stateMeta = document.getElementById('onboarding-meta');
    const readyBanner = document.getElementById('onboarding-ready');
    const stepperNode = document.getElementById('onboarding-stepper');
    const summaryNode = document.getElementById('onboarding-summary');
    const nextActionNode = document.getElementById('onboarding-next-action');
    const titleNode = document.getElementById('onboarding-title');
    const workspaceNode = document.getElementById('onboarding-workspace-name');
    const onboardingUrl = new URL(window.location.href);
    if (workspaceNode) workspaceNode.textContent = user.workspace_name || 'Your workspace';

    async function refreshState() {
      const state = await api('/onboarding/state');
      stateNode.innerHTML = stepMarkup(state);
      stateMeta.textContent = `${state.completed_steps.length} of ${state.total_steps} steps complete`;
      if (stepperNode) {
        stepperNode.innerHTML = onboardingStepperMarkup(state);
      }
      if (summaryNode) {
        summaryNode.innerHTML = `
          <div class="mvp-feature-stat">
            <div class="uplabel">Progress</div>
            <div class="value">${formatNumber(state.completed_steps.length, 0)} / ${formatNumber(state.total_steps, 0)}</div>
            <div class="meta">A tighter first-run flow: import the book, add optional documents, run analysis, and publish the first memo.</div>
          </div>
          <div class="mvp-feature-stat">
            <div class="uplabel">Next step</div>
            <div class="value">${escapeHtml(STEP_LABELS[state.next_step] || 'Ready')}</div>
            <div class="meta">${state.is_complete ? 'Onboarding is finished. Continue in the cockpit.' : 'This is the next action required to reach a live briefing.'}</div>
          </div>
          <div class="mvp-feature-stat">
            <div class="uplabel">Workspace</div>
            <div class="value">${escapeHtml(user.workspace_name || 'Workspace')}</div>
            <div class="meta">Timezone ${escapeHtml(browserTimezone())} · Auth path live</div>
          </div>
        `;
      }
      if (nextActionNode) {
        nextActionNode.textContent = STEP_LABELS[state.next_step] || 'Open cockpit';
      }
      if (titleNode) {
        const workspaceName = user.workspace_name || 'Your workspace';
        titleNode.textContent = state.is_complete
          ? `${workspaceName} is ready.`
          : `Take ${workspaceName} to first briefing.`;
      }
      if (readyBanner) {
        readyBanner.hidden = !state.is_complete;
      }
      if (!state.completed_steps.includes('workspace_created')) {
        await markOnboardingStep('workspace_created');
        return refreshState();
      }
      return state;
    }

    async function ensureVarReady() {
      await api('/var/compute', { method: 'POST' });
      await markOnboardingStep('enrichment_run');
    }

    async function ensureRiskReady() {
      await api('/risk/run', { method: 'POST' });
      await markOnboardingStep('risk_run');
    }

    await refreshState();

    document.getElementById('csv-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      const file = document.getElementById('csv-file').files[0];
      if (!file) {
        setStatus(status, 'Choose a CSV file first.', 'error');
        return;
      }
      const formData = new FormData();
      formData.append('file', file);
      try {
        await withButtonBusy(event.submitter, 'Uploading portfolio...', async () => {
          await api('/ingest/csv', { method: 'POST', formData });
          await markOnboardingStep('portfolio_uploaded');
          await ensureVarReady();
          await refreshState();
        });
        setStatus(status, 'Portfolio uploaded and valued. The holdings are now live in the workspace.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    document.getElementById('document-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      const file = document.getElementById('document-file').files[0];
      if (!file) {
        setStatus(status, 'Choose a document file first.', 'error');
        return;
      }
      const formData = new FormData();
      formData.append('folder', document.getElementById('document-folder').value);
      formData.append('file', file);
      try {
        await withButtonBusy(event.submitter, 'Uploading document...', async () => {
          const documentRecord = await api('/documents/upload', { method: 'POST', formData });
          await api(`/documents/${documentRecord.id}/parse`, { method: 'POST' });
          await refreshState();
          const documentsUrl = new URL('documents.html', onboardingUrl);
          documentsUrl.searchParams.set('documentId', documentRecord.id);
          documentsUrl.searchParams.set('uploaded', '1');
          window.location.href = documentsUrl.toString();
        });
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    document.getElementById('run-risk').addEventListener('click', async () => {
      try {
        await withButtonBusy(document.getElementById('run-risk'), 'Running analysis...', async () => {
          await ensureRiskReady();
          await refreshState();
        });
        setStatus(status, 'Risk analysis completed for the current portfolio.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    document.getElementById('generate-briefing').addEventListener('click', async () => {
      try {
        await withButtonBusy(document.getElementById('generate-briefing'), 'Generating briefing...', async () => {
          await ensureVarReady();
          await ensureRiskReady();
          const briefing = await api('/briefings/generate', { method: 'POST' });
          await markOnboardingStep('briefing_generated');
          await refreshState();
          setStatus(status, `${formatWeekLabel(briefing.week_label)} generated.`, 'success');
        });
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });
  }

  async function initSettings() {
    const user = await requireSession('settings.html', ['Workspace', 'Settings']);
    if (!user) return;

    const status = document.getElementById('settings-status');
    const form = document.getElementById('settings-form');
    const overview = document.getElementById('settings-overview');
    const fields = {
      reporting_currency: document.getElementById('settings-reporting-currency'),
      briefing_day: document.getElementById('settings-briefing-day'),
      briefing_time: document.getElementById('settings-briefing-time'),
      briefing_recipients: document.getElementById('settings-briefing-recipients'),
      briefing_auto_publish: document.getElementById('settings-auto-publish'),
      briefing_send_pdf: document.getElementById('settings-send-pdf'),
      briefing_include_audit_footer: document.getElementById('settings-audit-footer'),
      ai_model: document.getElementById('settings-ai-model'),
      ai_risk_tone: document.getElementById('settings-ai-risk-tone'),
      ai_custom_instructions: document.getElementById('settings-ai-custom-instructions'),
      ai_allow_trade_actions: document.getElementById('settings-ai-allow-trade-actions'),
    };

    function fill(settings) {
      fields.reporting_currency.value = normalizeCurrencyCode(settings.reporting_currency);
      fields.briefing_day.value = normalizeWeekday(settings.briefing_day, 'Monday');
      fields.briefing_time.value = settings.briefing_time || '06:00';
      fields.briefing_recipients.value = settings.briefing_recipients || '';
      fields.briefing_auto_publish.checked = Boolean(settings.briefing_auto_publish);
      fields.briefing_send_pdf.checked = Boolean(settings.briefing_send_pdf);
      fields.briefing_include_audit_footer.checked = Boolean(settings.briefing_include_audit_footer);
      fields.ai_model.value = settings.ai_model || 'claude-opus-4-6';
      fields.ai_risk_tone.value = settings.ai_risk_tone || 'conservative';
      fields.ai_custom_instructions.value = settings.ai_custom_instructions || '';
      fields.ai_allow_trade_actions.checked = Boolean(settings.ai_allow_trade_actions);
      if (overview) {
        overview.innerHTML = `
          <div class="mvp-feature-stat">
            <div class="uplabel">Reporting</div>
            <div class="value">${escapeHtml(normalizeCurrencyCode(settings.reporting_currency))}</div>
            <div class="meta">Default currency for cockpit, liquidity, and briefing reads.</div>
          </div>
          <div class="mvp-feature-stat">
            <div class="uplabel">Cadence</div>
            <div class="value">${escapeHtml(`${normalizeWeekday(settings.briefing_day, 'Monday')} ${settings.briefing_time || '06:00'}`)}</div>
            <div class="meta">${settings.briefing_recipients ? `${escapeHtml(settings.briefing_recipients)} receive the memo.` : 'Recipients are configured directly in this workspace.'}</div>
          </div>
          <div class="mvp-feature-stat">
            <div class="uplabel">AI profile</div>
            <div class="value">${escapeHtml(settings.ai_model || 'claude-opus-4-6')}</div>
            <div class="meta">${escapeHtml(titleCase(settings.ai_risk_tone || 'conservative'))} tone${settings.ai_allow_trade_actions ? ' · trade ideas enabled' : ' · no trade actions'}</div>
          </div>
        `;
      }
    }

    try {
      const settings = await api('/settings');
      applyWorkspaceSettings(settings);
      fill(settings);
    } catch (error) {
      setStatus(status, error.message, 'error');
      return;
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const payload = {
        reporting_currency: normalizeCurrencyCode(fields.reporting_currency.value),
        briefing_day: fields.briefing_day.value,
        briefing_time: fields.briefing_time.value,
        briefing_recipients: fields.briefing_recipients.value.trim(),
        briefing_auto_publish: fields.briefing_auto_publish.checked,
        briefing_send_pdf: fields.briefing_send_pdf.checked,
        briefing_include_audit_footer: fields.briefing_include_audit_footer.checked,
        ai_model: fields.ai_model.value,
        ai_risk_tone: fields.ai_risk_tone.value,
        ai_custom_instructions: fields.ai_custom_instructions.value.trim(),
        ai_allow_trade_actions: fields.ai_allow_trade_actions.checked,
      };
      try {
        const submitButton = form.querySelector('button[type="submit"]');
        const response = await withButtonBusy(submitButton, 'Saving...', async () => api('/settings', { method: 'PATCH', body: payload }));
        applyWorkspaceSettings(response);
        fill(response);
        setStatus(status, 'Settings saved.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });
  }

  async function initCockpit() {
    const user = await requireSession('cockpit.html', ['Workspace', 'Risk Cockpit']);
    if (!user) return;

    const status = document.getElementById('cockpit-status');
    const kpis = document.getElementById('cockpit-kpis');
    const composition = document.getElementById('cockpit-composition');
    const varSummary = document.getElementById('cockpit-var-summary');
    const varVisual = document.getElementById('cockpit-var-visual');
    const varDrivers = document.getElementById('cockpit-var-drivers');
    const register = document.getElementById('cockpit-register');
    const compositionTitle = document.getElementById('cockpit-composition-title');
    const compositionToggles = document.getElementById('cockpit-composition-toggles');
    const riskFilters = document.getElementById('cockpit-risk-filters');
    const compositionPalette = ['#1B2B5E', '#72594c', '#C9A449', '#006972', '#d3c3bc', '#8f6f9d'];
    const compositionTitles = {
      asset_class: 'Asset class mix',
      sector: 'Sector mix',
      geo_region: 'Geographic mix',
    };
    let compositionDimension = 'asset_class';
    let riskSeverity = 'all';
    let cockpitBody = null;
    let liquiditySummary = null;

    function setActiveToggle(container, valueKey, activeValue) {
      if (!container) return;
      container.querySelectorAll('button').forEach((button) => {
        button.classList.toggle('is-active', button.dataset[valueKey] === activeValue);
      });
    }

    function compositionBuckets(body) {
      return body?.portfolio_summary?.[compositionDimension] || [];
    }

    function renderComposition(body) {
      const summary = body.portfolio_summary;
      const buckets = compositionBuckets(body).slice(0, 6);
      const totalPositions = buckets.reduce((sum, bucket) => sum + Number(bucket.position_count || 0), 0);
      const circumference = 2 * Math.PI * 48;
      let offset = 0;
      if (compositionTitle) {
        compositionTitle.textContent = compositionTitles[compositionDimension] || 'Portfolio mix';
      }

      const donut = buckets.length
        ? buckets.map((bucket, index) => {
            const pct = Math.max(0, Number(bucket.pct_of_portfolio || 0));
            const arc = circumference * (pct / 100);
            const color = compositionPalette[index % compositionPalette.length];
            const circle = `
              <circle
                cx="60"
                cy="60"
                r="48"
                fill="none"
                stroke="${color}"
                stroke-width="14"
                stroke-dasharray="${arc} ${circumference}"
                stroke-dashoffset="${-offset}"
              />`;
            offset += arc;
            return circle;
          }).join('')
        : '';

      composition.innerHTML = buckets.length
        ? `
            <div class="mvp-chart-container">
              <div class="mvp-donut-wrapper">
                <svg viewBox="0 0 120 120" class="mvp-donut-svg" aria-hidden="true">
                  <circle cx="60" cy="60" r="48" fill="none" stroke="#f4ecea" stroke-width="14"/>
                  ${donut}
                </svg>
                <div class="mvp-donut-center">
                  <div class="uplabel">${escapeHtml(compositionTitles[compositionDimension] || 'Portfolio mix')}</div>
                  <div class="value">${formatCompactCurrency(summary.total_aum_usd)}</div>
                  <div class="label">${formatNumber(totalPositions, 0)} positions</div>
                </div>
              </div>
              <div class="mvp-legend">
                ${buckets.map((bucket, index) => `
                  <div class="mvp-legend-item">
                    <div class="mvp-legend-item-head">
                      <div class="mvp-legend-item-label">
                        <span class="mvp-legend-item-dot" style="background:${compositionPalette[index % compositionPalette.length]}"></span>
                        <span>${escapeHtml(compositionDimension === 'asset_class' ? formatAssetClass(bucket.label) : titleCase(bucket.label))}</span>
                      </div>
                      <span class="mvp-legend-item-pct">${formatPct(bucket.pct_of_portfolio, 1)}</span>
                    </div>
                    <div class="mvp-legend-item-bar"><div style="width:${Math.min(bucket.pct_of_portfolio, 100)}%;background:${compositionPalette[index % compositionPalette.length]}"></div></div>
                    <div class="mvp-legend-item-footer">
                      <span>${formatCurrency(bucket.market_value_usd)}</span>
                      <span>${formatNumber(bucket.position_count, 0)} positions</span>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          `
        : '<div class="mvp-empty">No composition data available.</div>';
    }

    function renderVar(body) {
      const varResult = body.var_result;
      const bars = [
        { label: 'Bad normal day', value: Number(varResult.var_1d_95 || 0), tone: 'watch', meta: 'VaR 95%' },
        { label: 'Severe day', value: Number(varResult.var_1d_99 || 0), tone: 'elevated', meta: 'VaR 99%' },
        { label: 'Worst modeled day', value: Number(varResult.worst_scenario_loss || 0), tone: 'priority', meta: String(varResult.worst_scenario_date || 'History') },
      ];
      const maxBarValue = Math.max(...bars.map((item) => item.value), 1);
      const topDrivers = (varResult.position_contributions || []).slice(0, 3);
      const driverSummary = topDrivers.length
        ? topDrivers.map((item) => item.ticker).join(', ')
        : 'current concentration and position mix';

      varSummary.innerHTML = `
        <div>
          <div class="uplabel">Downside read</div>
          <div class="mvp-var-headline">${formatCurrency(varResult.var_1d_95)}</div>
          <div class="mvp-var-plain-english">On a bad normal day, the portfolio could lose about ${formatCurrency(varResult.var_1d_95)}.</div>
          <div class="mvp-item-subtle">Modeled coverage ${formatPct(varResult.model_coverage_pct, 0)}. Severe-day estimate is ${formatCurrency(varResult.var_1d_99)}.</div>
        </div>
        <div class="mvp-var-meta">
          <div>Computed ${escapeHtml(formatDateTime(varResult.computed_at))}</div>
          <div>${formatNumber(varResult.effective_lookback_days, 0)} lookback days</div>
        </div>
      `;

      varVisual.innerHTML = `
        <div class="mvp-var-chart">
          ${bars.map((item) => `
            <div class="mvp-var-bar-row">
              <div class="mvp-var-bar-label">
                <span>${escapeHtml(item.label)}</span>
                <span class="mvp-item-subtle">${escapeHtml(item.meta)}</span>
              </div>
              <div class="mvp-var-bar-track">
                <div class="mvp-var-bar-fill ${item.tone}" style="width:${Math.max((item.value / maxBarValue) * 100, 8)}%"></div>
              </div>
              <div class="mvp-var-bar-value">${formatCurrency(item.value)}</div>
            </div>
          `).join('')}
        </div>
        <div class="mvp-var-note">
          <div class="mvp-item-title">What is pushing downside now</div>
          <div class="mvp-item-subtle">${escapeHtml(driverSummary)} are the largest current drivers of modeled downside.</div>
        </div>
      `;

      varDrivers.innerHTML = topDrivers
        .map(
          (item) => `
            <div class="mvp-item">
              <div>
                <div class="mvp-item-title">${escapeHtml(item.ticker)} is pushing current downside</div>
                <div class="mvp-item-subtle">${escapeHtml(titleCase(item.method))} estimate</div>
              </div>
              <div style="text-align:right">
                <div class="mvp-item-title">${formatCurrency(item.contribution_usd)}</div>
                <div class="mvp-item-subtle">${formatPct(item.contribution_pct, 1)}</div>
              </div>
            </div>
          `
        )
        .join('');
      if (!topDrivers.length) {
        varDrivers.innerHTML = '<div class="mvp-empty">No downside drivers available.</div>';
      }
    }

    function renderRegister(body) {
      const risks = body.risk_register || [];
      const counts = {
        all: risks.length,
        priority: risks.filter((item) => item.severity === 'priority').length,
        elevated: risks.filter((item) => item.severity === 'elevated').length,
        watch: risks.filter((item) => item.severity === 'watch').length,
      };
      if (riskFilters) {
        riskFilters.querySelectorAll('button').forEach((button) => {
          const severity = button.dataset.severity || 'all';
          const label = severity === 'all' ? 'All' : titleCase(severity);
          button.textContent = `${label} · ${formatNumber(counts[severity] || 0, 0)}`;
          button.classList.toggle('is-active', severity === riskSeverity);
        });
      }
      const filtered = riskSeverity === 'all'
        ? risks
        : risks.filter((item) => item.severity === riskSeverity);
      register.innerHTML = filtered.length
        ? filtered.map((item) => `
            <tr>
              <td><span class="mvp-risk-dot ${severityClass(item.severity)}"></span></td>
              <td>
                <div class="mvp-risk-name">${escapeHtml(item.headline || item.rule || 'Risk flag')}</div>
                <div class="mvp-risk-desc">${escapeHtml(item.kind === 'agent' ? 'Agent signal' : 'Rule trigger')}</div>
              </td>
              <td><span class="mvp-pill ${severityClass(item.severity)}">${escapeHtml(item.severity)}</span></td>
              <td>${escapeHtml(item.description || titleCase(item.agent || item.rule || 'Portfolio'))}</td>
            </tr>
          `).join('')
        : '<tr><td colspan="4" class="mvp-empty">No risks in this severity bucket.</td></tr>';
    }

    function renderCockpit(body) {
      const summary = body.portfolio_summary;
      const risks = body.risk_register || [];
      const liquidity = summary.liquidity_summary || liquiditySummary;
      const nextCallAmount = Math.abs(Number(liquidity?.next_call_amount_usd || 0));
      const bufferGap = Math.abs(Number(liquidity?.buffer_gap_usd || 0));
      const projectedCash = Number(liquidity?.projected_cash_usd || 0);
      kpis.innerHTML = `
        <div class="mvp-kpi mvp-kpi-featured"><div class="uplabel">Portfolio value</div><div class="value">${formatCompactCurrency(summary.total_aum_usd)}</div><div class="meta">Live portfolio snapshot</div></div>
        <div class="mvp-kpi"><div class="uplabel">Bad normal day</div><div class="value">${formatCurrency(body.var_result.var_1d_95)}</div><div class="meta">Estimated 1-day downside at 95%</div></div>
        <div class="mvp-kpi"><div class="uplabel">Active risks</div><div class="value">${formatNumber(risks.length)}</div><div class="meta">${formatNumber(risks.filter((item) => item.severity === 'priority').length)} priority · ${formatNumber(risks.filter((item) => item.severity === 'elevated').length)} elevated</div></div>
        <button type="button" class="mvp-kpi mvp-kpi-liquidity" data-open-liquidity>
          <div class="uplabel">Liquidity outlook</div>
          <div class="mvp-kpi-liquidity-list">
            <div class="mvp-kpi-liquidity-item mvp-kpi-liquidity-status">
              <span class="mvp-pill ${liquidity?.buffer_breach ? 'priority' : 'good'}">${liquidity?.buffer_breach ? 'Buffer breach' : 'Buffer intact'}</span>
              <div class="meta">${liquidity?.buffer_breach ? `${formatCompactCurrency(bufferGap)} shortfall to buffer` : `${formatCompactCurrency(projectedCash)} projected cash`}</div>
            </div>
            <div class="mvp-kpi-liquidity-item">
              <div>
                <div class="value">${liquidity?.next_call_due_date ? formatCompactCurrency(nextCallAmount) : 'No scheduled call'}</div>
                <div class="meta">${escapeHtml(liquidity?.next_call_due_date ? `Next call · ${liquidity.next_call_due_date}` : 'Capital calls only; buffer status shown above')}</div>
              </div>
            </div>
            <div class="mvp-kpi-liquidity-item">
              <div>
                <div class="value">${formatCompactCurrency(liquidity?.net_liquidity_usd || 0)}</div>
                <div class="meta">Net 90-day liquidity</div>
              </div>
            </div>
          </div>
        </button>
      `;
      renderComposition(body);
      renderVar(body);
      renderRegister(body);
    }

    function renderCockpitLoading() {
      kpis.innerHTML = Array.from({ length: 4 }, () => `
        <div class="mvp-kpi">
          <div class="uplabel">Loading</div>
          <div class="value">...</div>
          <div class="meta">Fetching cockpit data</div>
        </div>
      `).join('');
      composition.innerHTML = '<div class="mvp-empty">Loading composition...</div>';
      varSummary.innerHTML = '';
      varVisual.innerHTML = '';
      varDrivers.innerHTML = '<div class="mvp-empty">Loading downside read...</div>';
      register.innerHTML = '<tr><td colspan="4" class="mvp-empty">Loading risk register...</td></tr>';
    }

    async function loadCockpit() {
      renderCockpitLoading();
      try {
        const [cockpitResponse, liquidityResponse] = await Promise.all([
          api('/cockpit'),
          api('/liquidity/summary'),
        ]);
        cockpitBody = cockpitResponse;
        liquiditySummary = liquidityResponse;
        renderCockpit(cockpitBody);
        setStatus(status, '', '');
      } catch (error) {
        cockpitBody = null;
        liquiditySummary = null;
        kpis.innerHTML = '';
        composition.innerHTML = '';
        varSummary.innerHTML = '';
        varVisual.innerHTML = '';
        varDrivers.innerHTML = '';
        register.innerHTML = '<tr><td colspan="4" class="mvp-empty">No cockpit data available.</td></tr>';
        setStatus(status, error.message, 'error');
      }
    }

    if (compositionToggles) {
      compositionToggles.addEventListener('click', (event) => {
        const button = event.target.closest('button[data-dimension]');
        if (!button || !cockpitBody) return;
        compositionDimension = button.dataset.dimension || 'asset_class';
        withTransientUpdate(composition, () => {
          setActiveToggle(compositionToggles, 'dimension', compositionDimension);
          renderComposition(cockpitBody);
        });
      });
    }

    if (riskFilters) {
      riskFilters.addEventListener('click', (event) => {
        const button = event.target.closest('button[data-severity]');
        if (!button || !cockpitBody) return;
        riskSeverity = button.dataset.severity || 'all';
        withTransientUpdate(register, () => {
          renderRegister(cockpitBody);
        });
      });
    }

    document.getElementById('refresh-cockpit').addEventListener('click', loadCockpit);
    kpis.addEventListener('click', (event) => {
      if (event.target.closest('[data-open-liquidity]')) {
        window.location.href = 'liquidity.html';
      }
    });
    document.getElementById('rerun-risk').addEventListener('click', async () => {
      try {
        await api('/risk/run', { method: 'POST' });
        await loadCockpit();
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    markPageReady();
    await loadCockpit();
  }

  async function initLiquidity() {
    const user = await requireSession('liquidity.html', ['Workspace', 'Liquidity']);
    if (!user) return;

    const status = document.getElementById('liquidity-status');
    const kpis = document.getElementById('liquidity-kpis');
    const chart = document.getElementById('liquidity-chart');
    const chartSummary = document.getElementById('liquidity-chart-summary');
    const gaps = document.getElementById('liquidity-gaps');
    const detail = document.getElementById('liquidity-detail');
    const notes = document.getElementById('liquidity-notes');
    const scenarioButton = document.getElementById('liquidity-scenario');
    const bufferInput = document.getElementById('liquidity-buffer');
    const refreshButton = document.getElementById('liquidity-refresh');
    bindFormattedNumberInputs(document);
    let scenario = 'base';

    function renderChart(cashflow, summary) {
      const rows = cashflow.monthly_buckets || [];
      if (!rows.length) {
        chart.innerHTML = '<div class="mvp-empty">No liquidity data available.</div>';
        return;
      }
      const width = Math.max(1100, rows.length * 52);
      const height = 360;
      const padding = { top: 20, right: 24, bottom: 44, left: 76 };
      const innerWidth = width - padding.left - padding.right;
      const innerHeight = height - padding.top - padding.bottom;
      const barGroupWidth = innerWidth / rows.length;
      const barWidth = Math.max(10, Math.min(18, barGroupWidth * 0.24));
      const bufferValue = Number(cashflow.liquidity_buffer || 0);
      const domainValues = rows.flatMap((row) => [
        Number(row.inflows || 0),
        -Number(row.outflows || 0),
        Number(row.net || 0),
        Number(row.cumulative || 0),
      ]);
      const rawMin = Math.min(...domainValues, 0);
      const rawMax = Math.max(...domainValues, bufferValue, 0);
      const range = Math.max(rawMax - rawMin, 1);
      const domainPadding = range * 0.12;
      const domainMin = rawMin - domainPadding;
      const domainMax = rawMax + domainPadding;
      const scaleY = (value) => {
        const ratio = (domainMax - Number(value || 0)) / Math.max(domainMax - domainMin, 1);
        return padding.top + ratio * innerHeight;
      };
      const zeroY = scaleY(0);
      const linePoints = rows.map((row, index) => {
        const x = padding.left + barGroupWidth * index + barGroupWidth / 2;
        const y = scaleY(row.cumulative);
        return `${x},${y}`;
      }).join(' ');
      const tickCount = 5;
      const ticks = Array.from({ length: tickCount }, (_, index) => {
        const ratio = index / (tickCount - 1);
        const value = domainMax - (domainMax - domainMin) * ratio;
        return {
          value,
          y: scaleY(value),
          label: formatCompactCurrency(value),
        };
      });

      chart.innerHTML = `
        <div class="mvp-liquidity-chart-scroll">
          <svg viewBox="0 0 ${width} ${height}" class="mvp-liquidity-svg" role="img" aria-label="Liquidity cash flow chart">
            ${ticks.map((tick) => `
              <g class="mvp-liquidity-tick">
                <line x1="${padding.left}" y1="${tick.y}" x2="${width - padding.right}" y2="${tick.y}" class="mvp-liquidity-gridline"/>
                <text x="${padding.left - 12}" y="${tick.y + 4}" text-anchor="end" class="mvp-liquidity-y-axis">${escapeHtml(tick.label)}</text>
              </g>
            `).join('')}
            <line x1="${padding.left}" y1="${zeroY}" x2="${width - padding.right}" y2="${zeroY}" class="mvp-liquidity-baseline"/>
            ${rows.map((row, index) => {
              const x = padding.left + barGroupWidth * index;
              const centerX = x + barGroupWidth / 2;
              const inflowValue = Number(row.inflows || 0);
              const outflowValue = -Number(row.outflows || 0);
              const netValue = Number(row.net || 0);
              const cumulativeValue = Number(row.cumulative || 0);
              const inflowY = scaleY(inflowValue);
              const outflowY = scaleY(outflowValue);
              const cumulativeY = scaleY(cumulativeValue);
              const slotWidth = Math.max(barGroupWidth - 8, 24);
              const hitX = centerX - slotWidth / 2;
              const label = `${formatMonthKey(row.month)}. Inflows ${formatCurrency(inflowValue)}. Outflows ${formatCurrency(Math.abs(outflowValue))}. Net ${formatCurrency(netValue)}. Cumulative ${formatCurrency(cumulativeValue)}.`;
              return `
                <g class="mvp-liquidity-slot" data-index="${index}">
                  <rect x="${hitX}" y="${padding.top}" width="${slotWidth}" height="${innerHeight}" class="mvp-liquidity-highlight"/>
                  <rect x="${x + barGroupWidth * 0.14}" y="${Math.min(inflowY, zeroY)}" width="${barWidth}" height="${Math.max(Math.abs(zeroY - inflowY), 1)}" class="mvp-liquidity-bar inflow"/>
                  <rect x="${x + barGroupWidth * 0.14 + barWidth + 8}" y="${Math.min(outflowY, zeroY)}" width="${barWidth}" height="${Math.max(Math.abs(outflowY - zeroY), 1)}" class="mvp-liquidity-bar outflow"/>
                  <line x1="${centerX}" y1="${zeroY}" x2="${centerX}" y2="${cumulativeY}" class="mvp-liquidity-stem"/>
                  <circle cx="${centerX}" cy="${cumulativeY}" r="4.5" class="mvp-liquidity-point"/>
                  <rect x="${hitX}" y="${padding.top}" width="${slotWidth}" height="${innerHeight}" class="mvp-liquidity-hitbox" tabindex="0" role="button" aria-label="${escapeHtml(label)}"/>
                  <text x="${centerX}" y="${height - 14}" text-anchor="middle" class="mvp-liquidity-axis">${escapeHtml(formatMonthKey(row.month))}</text>
                </g>
              `;
            }).join('')}
            <polyline points="${linePoints}" class="mvp-liquidity-line"/>
          </svg>
          <div class="mvp-liquidity-tooltip" id="liquidity-tooltip" hidden></div>
        </div>
      `;

      chartSummary.innerHTML = `
        <div class="mvp-overlay-kpis">
          <div class="mvp-stat-item"><div class="uplabel">Scenario</div><div class="value">${escapeHtml(titleCase(cashflow.scenario))}</div><div class="meta">${rows.length} monthly buckets</div></div>
          <div class="mvp-stat-item"><div class="uplabel">Buffer target</div><div class="value">${formatCompactCurrency(cashflow.liquidity_buffer)}</div><div class="meta">${summary.buffer_breach ? `${formatCompactCurrency(summary.buffer_gap_usd)} below target` : 'Target maintained in the 90-day view'}</div></div>
          <div class="mvp-stat-item"><div class="uplabel">Projected cash after 90 days</div><div class="value">${formatCompactCurrency(summary.projected_cash_usd)}</div><div class="meta">Cash on hand plus next 90-day net flows</div></div>
          <div class="mvp-stat-item"><div class="uplabel">Gap months</div><div class="value">${formatNumber(cashflow.liquidity_gaps?.length || 0, 0)}</div><div class="meta">${cashflow.liquidity_gaps?.length ? 'Months where projected cash falls short of the target buffer.' : 'No projected months fall below the target buffer.'}</div></div>
        </div>
      `;

      const tooltip = document.getElementById('liquidity-tooltip');
      const scroll = chart.querySelector('.mvp-liquidity-chart-scroll');
      const slots = [...chart.querySelectorAll('.mvp-liquidity-slot')];
      
      function showTooltip(index) {
        const row = rows[index];
        const slot = slots[index];
        if (!row || !slot || !tooltip || !scroll) return;
        slots.forEach((slot, slotIndex) => {
          slot.classList.toggle('is-active', slotIndex === index);
        });
        const point = slot.querySelector('.mvp-liquidity-point');
        const pointBox = point?.getBoundingClientRect();
        const scrollBox = scroll.getBoundingClientRect();
        tooltip.innerHTML = `
          <div class="mvp-liquidity-tooltip-title">${escapeHtml(formatMonthKey(row.month))}</div>
          <div>Inflows <strong>${escapeHtml(formatCompactCurrency(row.inflows || 0))}</strong></div>
          <div>Outflows <strong>${escapeHtml(formatCompactCurrency(row.outflows || 0))}</strong></div>
          <div>Net <strong>${escapeHtml(formatCompactCurrency(row.net || 0))}</strong></div>
          <div>Cumulative <strong>${escapeHtml(formatCompactCurrency(row.cumulative || 0))}</strong></div>
        `;
        tooltip.hidden = false;
        const tooltipWidth = tooltip.offsetWidth || 180;
        const pointLeft = pointBox ? (pointBox.left - scrollBox.left + scroll.scrollLeft) : (barGroupWidth * index);
        const pointTop = pointBox ? (pointBox.top - scrollBox.top) : 0;
        const left = Math.max(12, Math.min(pointLeft - tooltipWidth / 2, scroll.scrollWidth - tooltipWidth - 12));
        const top = Math.max(12, pointTop - 112);
        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${top}px`;
      }

      function hideTooltip() {
        if (tooltip) tooltip.hidden = true;
        slots.forEach((slot) => slot.classList.remove('is-active'));
      }

      slots.forEach((slot, index) => {
        const hitbox = slot.querySelector('.mvp-liquidity-hitbox');
        if (!hitbox) return;
        hitbox.addEventListener('mouseenter', () => showTooltip(index));
        hitbox.addEventListener('focus', () => showTooltip(index));
        hitbox.addEventListener('click', () => showTooltip(index));
        hitbox.addEventListener('keydown', (event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            showTooltip(index);
          }
        });
      });

      scroll?.addEventListener('mouseleave', hideTooltip);
      scroll?.addEventListener('focusout', (event) => {
        if (!chart.contains(event.relatedTarget)) hideTooltip();
      });
    }

    function renderLiquidity(summary, cashflow) {
      kpis.innerHTML = `
        <div class="mvp-kpi mvp-kpi-featured"><div class="uplabel">Next call due</div><div class="value">${summary.next_call_amount_usd ? formatCompactCurrency(summary.next_call_amount_usd) : 'None'}</div><div class="meta">${escapeHtml(summary.next_call_due_date || 'No scheduled call')}</div></div>
        <div class="mvp-kpi"><div class="uplabel">Total unfunded</div><div class="value">${formatCompactCurrency(summary.total_unfunded_usd)}</div><div class="meta">Commitments still drawable</div></div>
        <div class="mvp-kpi"><div class="uplabel">Expected distributions</div><div class="value">${formatCompactCurrency(summary.expected_distributions_usd)}</div><div class="meta">Next 90 days</div></div>
        <div class="mvp-kpi"><div class="uplabel">Net position</div><div class="value">${formatCompactCurrency(summary.net_liquidity_usd)}</div><div class="meta">${summary.buffer_breach ? 'Below target buffer' : 'Above target buffer'}</div></div>
      `;

      detail.innerHTML = `
        <div class="mvp-list">
          <div class="mvp-item"><div><div class="mvp-item-title">Cash on hand</div><div class="mvp-item-subtle">Current cash positions in portfolio</div></div><div class="mvp-item-title">${formatCompactCurrency(summary.cash_on_hand_usd)}</div></div>
          <div class="mvp-item"><div><div class="mvp-item-title">Scheduled outflows</div><div class="mvp-item-subtle">Calls and fees inside 90 days</div></div><div class="mvp-item-title">${formatCompactCurrency(summary.scheduled_outflows_usd)}</div></div>
          <div class="mvp-item"><div><div class="mvp-item-title">Projected cash</div><div class="mvp-item-subtle">Cash plus net flows</div></div><div class="mvp-item-title">${formatCompactCurrency(summary.projected_cash_usd)}</div></div>
          <div class="mvp-item"><div><div class="mvp-item-title">Recallable pending</div><div class="mvp-item-subtle">Distributions not yet clear of recall window</div></div><div class="mvp-item-title">${formatCompactCurrency(summary.recallable_pending_usd)}</div></div>
        </div>
      `;
      if (notes) {
        notes.innerHTML = `
          <div class="mvp-list">
            <div class="mvp-item">
              <div>
                <div class="mvp-item-title">Scenario mode</div>
                <div class="mvp-item-subtle">${scenario === 'stress' ? 'Stress case is active. Inflows are delayed and outflows stay conservative.' : 'Base case is active. This is the clean operational planning view.'}</div>
              </div>
              <span class="mvp-pill ${scenario === 'stress' ? 'elevated' : 'good'}">${escapeHtml(titleCase(scenario))}</span>
            </div>
            <div class="mvp-item">
              <div>
                <div class="mvp-item-title">Next call</div>
                <div class="mvp-item-subtle">${escapeHtml(summary.next_call_due_date || 'No scheduled capital call in the current view.')}</div>
              </div>
              <span class="mvp-pill ${summary.next_call_amount_usd ? 'watch' : 'good'}">${summary.next_call_amount_usd ? formatCompactCurrency(summary.next_call_amount_usd) : 'None'}</span>
            </div>
            <div class="mvp-item">
              <div>
                <div class="mvp-item-title">Buffer read</div>
                <div class="mvp-item-subtle">${summary.buffer_breach ? 'Projected cash falls below the selected buffer inside the 90-day window.' : 'Projected cash remains above the selected buffer inside the 90-day window.'}</div>
              </div>
              <span class="mvp-pill ${summary.buffer_breach ? 'priority' : 'good'}">${summary.buffer_breach ? 'At risk' : 'Covered'}</span>
            </div>
          </div>
        `;
      }

      gaps.innerHTML = cashflow.liquidity_gaps?.length ? `
        <div class="mvp-list">
          ${cashflow.liquidity_gaps.map((item) => `
            <div class="mvp-item">
              <div>
                <div class="mvp-item-title">${escapeHtml(formatMonthKey(item.month))}</div>
                <div class="mvp-item-subtle">${escapeHtml(item.description)}</div>
              </div>
              <div style="text-align:right">
                <span class="mvp-pill priority">${formatCompactCurrency(item.gap_amount)}</span>
              </div>
            </div>
          `).join('')}
        </div>
      ` : '<div class="mvp-empty">No projected liquidity gaps at the current buffer target.</div>';

      renderChart(cashflow, summary);
      scenarioButton.classList.toggle('primary', scenario === 'stress');
      scenarioButton.innerHTML = scenario === 'stress'
        ? '<span class="ms">check_circle</span>Stress case'
        : '<span class="ms">tornado</span>Stress case';
    }

    async function loadLiquidity() {
      setStatus(status, '', '');
      try {
        const bufferTarget = clampNumber(parseFormattedNumber(bufferInput.value), 2000000, 0);
        bufferInput.value = formatNumberInputValue(bufferTarget, 'integer');
        const [summary, cashflow] = await Promise.all([
          api(`/liquidity/summary?buffer_target_usd=${encodeURIComponent(bufferTarget)}`),
          api(`/liquidity/cashflow?months=24&scenario=${encodeURIComponent(scenario)}&buffer_target_usd=${encodeURIComponent(bufferTarget)}`),
        ]);
        renderLiquidity(summary, cashflow);
      } catch (error) {
        kpis.innerHTML = '';
        chart.innerHTML = '';
        chartSummary.innerHTML = '';
        gaps.innerHTML = '';
        detail.innerHTML = '';
        if (notes) notes.innerHTML = '';
        setStatus(status, error.message, 'error');
      }
    }

    refreshButton.addEventListener('click', async () => {
      await withButtonBusy(refreshButton, 'Refreshing...', loadLiquidity);
    });
    scenarioButton.addEventListener('click', async () => {
      await withButtonBusy(scenarioButton, scenario === 'base' ? 'Loading stress...' : 'Loading base...', async () => {
        scenario = scenario === 'base' ? 'stress' : 'base';
        await loadLiquidity();
      });
    });
    bufferInput.addEventListener('change', async () => {
      await loadLiquidity();
    });

    await loadLiquidity();
  }

  async function initOverlay() {
    const user = await requireSession('scenarios.html', ['Workspace', 'Overlay']);
    if (!user) return;

    const status = document.getElementById('overlay-status');
    const feature = document.getElementById('overlay-feature');
    const kpis = document.getElementById('overlay-kpis');
    const regimePanel = document.getElementById('overlay-regime-panel');
    const triangulationPanel = document.getElementById('overlay-triangulation-panel');
    const factorsPanel = document.getElementById('overlay-factors-panel');
    const stressPanel = document.getElementById('overlay-stress-panel');
    let refreshTimer = null;

    function renderOverlayPage({ factors, regime, triangulation, stress }) {
      const topFactor = (triangulation.factors || [])[0];
      const topScenario = (stress.scenarios || [])[0];
      feature.innerHTML = `
        <div class="mvp-overlay-feature">
          <div class="mvp-overlay-feature-main">
            <div class="mvp-overlay-feature-copy">
              <div class="mvp-feature-meta">
                <span class="mvp-pill ${severityClass(regime.regime)}">${escapeHtml(titleCase(regime.regime))} regime</span>
                <span>${escapeHtml(`Updated ${formatDateTime(regime.created_at)}`)}</span>
              </div>
              <h3>${escapeHtml(titleCase(regime.trigger_signal || 'baseline'))} is driving today's overlay posture.</h3>
              <p>${escapeHtml(regime.methodology_note || 'Daily factor scoring and scenario monitoring are aligned to the latest portfolio snapshot.')}</p>
            </div>
            <div class="mvp-overlay-feature-side">
              <div class="mvp-overlay-insight">
                <div class="uplabel">Top factor at risk</div>
                <div class="value">${escapeHtml(topFactor?.label || 'N/A')}</div>
                <div class="meta">${escapeHtml(topFactor ? `${formatPct(topFactor.exposure_pct, 1)} of portfolio · ${formatCompactCurrency(topFactor.aum_exposed_usd)}` : 'No factor exposure available')}</div>
              </div>
              <div class="mvp-overlay-insight">
                <div class="uplabel">Largest scenario</div>
                <div class="value">${topScenario ? formatCompactCurrency(topScenario.estimated_impact_usd) : 'N/A'}</div>
                <div class="meta">${escapeHtml(topScenario ? `${topScenario.name} · ${formatPct(topScenario.estimated_impact_pct, 1)}` : 'No scenario impact available')}</div>
              </div>
            </div>
          </div>
        </div>
      `;

      kpis.innerHTML = `
        <div class="mvp-kpi mvp-kpi-featured"><div class="uplabel">Composite score</div><div class="value">${formatNumber(triangulation.composite_score, 2)}</div><div class="meta">${escapeHtml(titleCase(regime.regime))} regime</div></div>
        <div class="mvp-kpi"><div class="uplabel">AUM at risk</div><div class="value">${formatCompactCurrency(triangulation.aum_at_risk_usd)}</div><div class="meta">Scores above 70</div></div>
        <div class="mvp-kpi"><div class="uplabel">Tracked factors</div><div class="value">${formatNumber(factors.length, 0)}</div><div class="meta">Daily scored</div></div>
        <div class="mvp-kpi"><div class="uplabel">Active alerts</div><div class="value">${formatNumber((stress.alerts || []).length, 0)}</div><div class="meta">Latest overlay run</div></div>
      `;

      regimePanel.innerHTML = `
        <div class="mvp-overlay-regime-card">
          <div class="mvp-overlay-regime">
            <span class="mvp-pill ${severityClass(regime.regime)}">${escapeHtml(titleCase(regime.regime))}</span>
            <span class="mvp-item-subtle">Updated ${escapeHtml(formatDateTime(regime.created_at))}</span>
          </div>
          <div class="mvp-overlay-regime-grid">
            <div class="mvp-stat-item"><div class="uplabel">Trigger</div><div class="value">${escapeHtml(titleCase(regime.trigger_signal))}</div><div class="meta">${escapeHtml(regime.methodology_note)}</div></div>
            <div class="mvp-stat-item"><div class="uplabel">VIX</div><div class="value">${formatNumber(regime.vix_level, 1)}</div><div class="meta">Market volatility</div></div>
            <div class="mvp-stat-item"><div class="uplabel">IG spread</div><div class="value">${formatNumber(regime.credit_spread_bps, 0)} bps</div><div class="meta">Credit stress</div></div>
          </div>
        </div>
      `;

      triangulationPanel.innerHTML = `
        <div class="mvp-table-wrap">
          <table class="mvp-table mvp-overlay-factor-table">
            <thead>
              <tr>
                <th>Factor</th>
                <th>Direction</th>
                <th class="num">% Port.</th>
                <th class="num">AUM</th>
                <th class="num">Risk score</th>
              </tr>
            </thead>
            <tbody>
              ${(triangulation.factors || []).map((item) => `
                <tr>
                  <td><div class="mvp-risk-name">${escapeHtml(item.label)}</div><div class="mvp-risk-desc">${escapeHtml(titleCase(item.factor_type))}</div></td>
                  <td>${escapeHtml(titleCase(item.direction))}</td>
                  <td class="num">${formatPct(item.exposure_pct, 1)}</td>
                  <td class="num">${formatCompactCurrency(item.aum_exposed_usd)}</td>
                  <td class="num">${formatNumber(item.risk_score, 0)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;

      factorsPanel.innerHTML = `
        <div class="mvp-table-wrap">
          <table class="mvp-table mvp-overlay-factor-table">
            <thead>
              <tr>
                <th>Factor</th>
                <th>Type</th>
                <th class="num">Z-score</th>
                <th class="num">Today's score</th>
                <th>Direction</th>
                <th>Primary driver</th>
              </tr>
            </thead>
            <tbody>
              ${(factors || []).map((item) => `
                <tr>
                  <td>${escapeHtml(item.label)}</td>
                  <td>${escapeHtml(titleCase(item.factor_type))}</td>
                  <td class="num">${formatNumber(item.z_score, 2)}</td>
                  <td class="num"><span class="mvp-pill ${item.score >= 85 ? 'priority' : item.score >= 75 ? 'elevated' : 'watch'}">${formatNumber(item.score, 0)}</span></td>
                  <td>${escapeHtml(titleCase(item.direction))}</td>
                  <td>${escapeHtml(titleCase(item.primary_driver || 'baseline'))}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;

      stressPanel.innerHTML = `
        <div class="mvp-table-wrap">
          <table class="mvp-table">
            <thead>
              <tr>
                <th>Scenario</th>
                <th>Severity</th>
                <th class="num">Impact</th>
                <th class="num">% Port.</th>
                <th>Top drivers</th>
              </tr>
            </thead>
            <tbody>
              ${(stress.scenarios || []).map((item) => `
                <tr>
                  <td><div class="mvp-risk-name">${escapeHtml(item.name)}</div><div class="mvp-risk-desc">${escapeHtml(item.description)}</div></td>
                  <td><span class="mvp-pill ${severityClass(item.severity)}">${escapeHtml(item.severity)}</span></td>
                  <td class="num">${formatCompactCurrency(item.estimated_impact_usd)}</td>
                  <td class="num">${formatPct(item.estimated_impact_pct, 1)}</td>
                  <td>${escapeHtml((item.top_drivers || []).map((driver) => driver.label).join(' · '))}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
        ${(stress.alerts || []).length ? `
          <div class="mvp-overlay-alerts" style="margin-top:14px">
            ${(stress.alerts || []).map((item) => `
              <div class="mvp-notice ${item.severity === 'priority' ? 'error' : ''}">
                <strong>${escapeHtml(item.headline)}</strong><br/>${escapeHtml(item.description)}
              </div>
            `).join('')}
          </div>
        ` : ''}
      `;
    }

    async function loadOverlayPage() {
      try {
        const [factors, regime, triangulation, stress] = await Promise.all([
          api('/overlay/factors'),
          api('/overlay/regime'),
          api('/overlay/aum-triangulation'),
          api('/overlay/stress'),
        ]);
        renderOverlayPage({ factors, regime, triangulation, stress });
        setStatus(status, '', '');
      } catch (error) {
        feature.innerHTML = '';
        kpis.innerHTML = '';
        regimePanel.innerHTML = '<div class="mvp-empty">Overlay regime unavailable.</div>';
        triangulationPanel.innerHTML = '<div class="mvp-empty">Triangulation unavailable.</div>';
        factorsPanel.innerHTML = '<div class="mvp-empty">Factor scores unavailable.</div>';
        stressPanel.innerHTML = '<div class="mvp-empty">Stress scenarios unavailable.</div>';
        setStatus(status, error.message, 'error');
      }
    }

    document.getElementById('overlay-refresh').addEventListener('click', loadOverlayPage);
    document.getElementById('overlay-run').addEventListener('click', async () => {
      try {
        await api('/overlay/run', { method: 'POST' });
        await loadOverlayPage();
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    refreshTimer = window.setInterval(loadOverlayPage, 60000);
    window.addEventListener('beforeunload', () => {
      if (refreshTimer) window.clearInterval(refreshTimer);
    }, { once: true });

    await loadOverlayPage();
  }

  function briefingSummary(output) {
    const risks = output.portfolio_risks || [];
    const first = risks[0];
    return first ? `${first.risk_area}: ${first.finding}` : output.executive_summary || 'Briefing ready.';
  }

  async function initBriefings() {
    const user = await requireSession('briefings.html', ['Workspace', 'Briefings']);
    if (!user) return;

    const status = document.getElementById('briefings-status');
    const overview = document.getElementById('briefings-overview');
    const list = document.getElementById('briefings-list');
    const toggleDrafts = document.getElementById('toggle-drafts');
    const rail = document.getElementById('briefings-rail');
    let showDrafts = false;

    async function loadBriefings() {
      try {
        const response = await api('/briefings');
        const items = (response.items || []).sort((left, right) => {
          if (left.status === right.status) return right.version - left.version;
          return left.status === 'published' ? -1 : 1;
        });
        const published = items.filter((item) => item.status === 'published');
        const drafts = items.filter((item) => item.status !== 'published');
        const featured = published[0] || items[0] || null;
        const visibleItems = showDrafts ? items : items.filter((item) => item.status === 'published');
        if (toggleDrafts) {
          toggleDrafts.textContent = showDrafts ? 'Hide drafts' : 'Show drafts';
        }
        if (rail) {
          rail.innerHTML = `
            <div class="mvp-card pad mvp-briefings-rail-card">
              <div class="uplabel">Workflow</div>
              <h3>Weekly committee cycle</h3>
              <div class="mvp-list" style="margin-top:12px">
                <div class="mvp-item"><div><div class="mvp-item-title">Published</div><div class="mvp-item-subtle">Memos already cleared for distribution.</div></div><span class="mvp-pill good">${formatNumber(published.length, 0)}</span></div>
                <div class="mvp-item"><div><div class="mvp-item-title">Draft queue</div><div class="mvp-item-subtle">Generated output waiting for review or publish.</div></div><span class="mvp-pill elevated">${formatNumber(drafts.length, 0)}</span></div>
                <div class="mvp-item"><div><div class="mvp-item-title">View mode</div><div class="mvp-item-subtle">${showDrafts ? 'Published and draft items are visible below.' : 'Drafts are hidden until needed.'}</div></div><span class="mvp-pill watch">${showDrafts ? 'all' : 'published'}</span></div>
              </div>
            </div>
          `;
        }
        overview.innerHTML = featured
          ? `
              <div class="mvp-feature-grid">
                <div class="mvp-feature-card">
                  <div class="uplabel">Latest committee pack</div>
                  <h3>${escapeHtml(featured.output.headline || 'Weekly briefing')}</h3>
                  <p>${escapeHtml(briefingDisplaySummary(featured.output))}</p>
                  <div class="mvp-feature-meta" style="margin-top:14px">
                    <span class="mvp-pill ${featured.status === 'published' ? 'good' : 'elevated'}">${escapeHtml(featured.status)}</span>
                    <span>${escapeHtml(formatWeekLabel(featured.week_label))}</span>
                    <span>v${escapeHtml(featured.version)}</span>
                  </div>
                  ${renderQualityNote(featured.output.quality_gate)}
                </div>
                <div class="mvp-feature-stat">
                  <div class="uplabel">Published</div>
                  <div class="value">${formatNumber(published.length, 0)}</div>
                  <div class="meta">Investor-ready weekly memos.</div>
                </div>
                <div class="mvp-feature-stat">
                  <div class="uplabel">Drafts</div>
                  <div class="value">${formatNumber(drafts.length, 0)}</div>
                  <div class="meta">${showDrafts ? 'Visible in the grid below.' : 'Hidden by default to keep the list focused.'}</div>
                </div>
                <div class="mvp-feature-stat">
                  <div class="uplabel">Current status</div>
                  <div class="value">${escapeHtml(qualitySummary(featured.output.quality_gate))}</div>
                  <div class="meta">${escapeHtml((featured.output.quality_gate?.blocking_messages || [])[0] || 'Latest briefing is committee-ready.')}</div>
                </div>
              </div>
            `
          : '';
        list.innerHTML = visibleItems.length
          ? visibleItems
              .map(
                (item) => `
                  <a class="mvp-card pad" href="briefing.html?id=${encodeURIComponent(item.id)}" style="display:block;color:inherit">
                    <div class="mvp-metadata">
                      <span class="mvp-pill ${item.status === 'published' ? 'good' : 'elevated'}">${escapeHtml(item.status)}</span>
                      ${item.output.quality_gate ? `<span class="mvp-pill ${qualityTone(item.output.quality_gate)}">${escapeHtml(qualitySummary(item.output.quality_gate))}</span>` : ''}
                      <span>${escapeHtml(formatWeekLabel(item.week_label))}</span>
                      <span>v${escapeHtml(item.version)}</span>
                    </div>
                    <h3 style="font-family:'Fraunces',serif;margin:12px 0 6px">${escapeHtml(item.output.headline || 'Weekly briefing')}</h3>
                    <p style="margin:0;color:var(--ink-soft);font-size:12px">${escapeHtml(truncateText(briefingDisplaySummary(item.output), 120))}</p>
                  </a>
                `
              )
              .join('')
          : `<div class="mvp-empty mvp-card">${showDrafts ? 'No briefings yet. Generate the first one from this page.' : 'No published briefings yet. Show drafts or generate a new briefing.'}</div>`;
        setStatus(status, '', '');
      } catch (error) {
        overview.innerHTML = '';
        list.innerHTML = '<div class="mvp-empty mvp-card">Unable to load briefings.</div>';
        setStatus(status, error.message, 'error');
      }
    }

    if (toggleDrafts) {
      toggleDrafts.addEventListener('click', async () => {
        showDrafts = !showDrafts;
        await loadBriefings();
      });
    }

    document.getElementById('generate-briefing-action').addEventListener('click', async () => {
      try {
        const briefing = await withButtonBusy(
          document.getElementById('generate-briefing-action'),
          'Generating...',
          async () => api('/briefings/generate', { method: 'POST' })
        );
        window.location.href = `briefing.html?id=${encodeURIComponent(briefing.id)}`;
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    await loadBriefings();
  }

  async function initBriefingDetail() {
    const user = await requireSession('briefing.html', ['Workspace', 'Briefings', 'Briefing']);
    if (!user) return;

    const status = document.getElementById('briefing-status');
    const meta = document.getElementById('briefing-meta');
    const title = document.getElementById('briefing-title');
    const body = document.getElementById('briefing-body');
    const publishButton = document.getElementById('publish-briefing');
    const exportButton = document.getElementById('export-briefing');
    let briefingId = getQueryParam('id');

    if (!briefingId) {
      try {
        const response = await api('/briefings');
        briefingId = response.items?.[0]?.id || '';
      } catch {
        briefingId = '';
      }
    }

    if (!briefingId) {
      setStatus(status, 'No briefing selected.', 'error');
      return;
    }

    async function loadBriefing() {
      try {
        const briefing = await api(`/briefings/${briefingId}`);
        const output = briefing.output || {};
        title.textContent = output.headline || 'Weekly briefing';
        meta.innerHTML = `
          <span class="mvp-pill ${briefing.status === 'published' ? 'good' : 'elevated'}">${escapeHtml(briefing.status)}</span>
          ${output.quality_gate ? `<span class="mvp-pill ${qualityTone(output.quality_gate)}">${escapeHtml(qualitySummary(output.quality_gate))}</span>` : ''}
          <span>${escapeHtml(formatWeekLabel(briefing.week_label))}</span>
          <span>Version ${escapeHtml(briefing.version)}</span>
        `;
        if (window.CRBMvpShell?.updateCrumbs) {
          window.CRBMvpShell.updateCrumbs(['Workspace', 'Briefings', formatWeekLabel(briefing.week_label)]);
        }
        publishButton.disabled = briefing.status === 'published';
        publishButton.innerHTML = briefing.status === 'published'
          ? '<span class="ms">task_alt</span>Published'
          : '<span class="ms">publish</span>Publish';
        const legacyTxtExport = typeof briefing.pdf_path === 'string' && briefing.pdf_path.toLowerCase().endsWith('.txt');
        exportButton.disabled = legacyTxtExport;
        exportButton.innerHTML = legacyTxtExport
          ? '<span class="ms">block</span>PDF unavailable'
          : '<span class="ms">file_download</span>Export PDF';
        const summaryText = briefingDisplaySummary(output);
        const liquidityText = briefingDisplayLiquidity(output);
        const sections = [
          summaryText && {
            id: 'summary', eyebrow: 'I. Executive Summary', heading: 'The week in one breath',
            html: `<div class="essay-prose"><p class="essay-deck">${escapeHtml(summaryText)}</p></div>`,
          },
          output.market_context && {
            id: 'context', eyebrow: 'II. Market Context', heading: 'What the tape is saying',
            html: `<div class="essay-prose"><p>${escapeHtml(output.market_context).replace(/\n\n+/g, '</p><p>')}</p></div>`,
          },
          (output.portfolio_risks || []).length && {
            id: 'risks', eyebrow: 'III. Portfolio Risks', heading: 'Where the exposure sits',
            html: (output.portfolio_risks || []).map((item) => `
              <div class="essay-risk">
                <div class="essay-risk-head">
                  <div class="essay-risk-title">${escapeHtml(item.risk_area)}</div>
                  <div class="essay-risk-sev">${escapeHtml(item.severity)}</div>
                </div>
                <div class="essay-risk-finding">${escapeHtml(item.finding)}</div>
                ${item.implication ? `<div class="essay-risk-implication">${escapeHtml(item.implication)}</div>` : ''}
              </div>`).join(''),
          },
          (output.recommendations || []).length && {
            id: 'recs', eyebrow: 'IV. Recommendations', heading: 'What to do next',
            html: `<ol class="essay-recs">${(output.recommendations || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ol>`,
          },
          liquidityText && {
            id: 'liquidity', eyebrow: 'V. Liquidity', heading: 'Cash and commitments',
            html: `<div class="essay-prose"><p>${escapeHtml(liquidityText)}</p></div>`,
          },
        ].filter(Boolean);

        body.innerHTML = (output.quality_gate ? `<section class="essay-section"><div class="essay-eyebrow">Quality Gate</div>${renderQualityNote(output.quality_gate)}</section>` : '')
          + sections.map((s) => `
            <section class="essay-section" id="sec-${s.id}">
              <div class="essay-eyebrow">${s.eyebrow}</div>
              <h2 class="essay-heading">${s.heading}</h2>
              ${s.html}
            </section>`).join('');

        const toc = document.getElementById('briefing-toc');
        if (toc) {
          toc.innerHTML = `<div class="essay-toc-label">Contents</div>`
            + sections.map((s) => `<a href="#sec-${s.id}" data-toc="${s.id}">${s.eyebrow.replace(/^[IVX]+\.\s*/, '')}</a>`).join('');
        }

        const reveal = new IntersectionObserver((entries) => {
          entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('is-visible'); reveal.unobserve(e.target); } });
        }, { threshold: 0.12 });
        body.querySelectorAll('.essay-section').forEach((el) => reveal.observe(el));

        const tocLinks = toc ? toc.querySelectorAll('a[data-toc]') : [];
        if (tocLinks.length) {
          const spy = new IntersectionObserver((entries) => {
            entries.forEach((e) => {
              if (e.isIntersecting) {
                const id = e.target.id.replace(/^sec-/, '');
                tocLinks.forEach((a) => a.classList.toggle('active', a.dataset.toc === id));
              }
            });
          }, { rootMargin: '-40% 0px -55% 0px' });
          body.querySelectorAll('.essay-section[id]').forEach((el) => spy.observe(el));
        }
        setStatus(status, '', '');
      } catch (error) {
        body.innerHTML = '<div class="mvp-empty">Unable to load briefing.</div>';
        setStatus(status, error.message, 'error');
      }
    }

    document.getElementById('publish-briefing').addEventListener('click', async () => {
      try {
        const response = await api(`/briefings/${briefingId}/publish`, { method: 'POST' });
        setStatus(status, response.detail, 'success');
        await loadBriefing();
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    exportButton.addEventListener('click', async () => {
      try {
        const filename = await download(
          `/briefings/${briefingId}/export/pdf`,
          `briefing-${briefingId}.pdf`
        );
        setStatus(status, `Download started for ${filename}.`, 'success');
      } catch (error) {
        if (error.message.includes('PDF export unavailable')) {
          exportButton.disabled = true;
          exportButton.innerHTML = '<span class="ms">block</span>PDF unavailable';
        }
        setStatus(status, error.message, 'error');
      }
    });

    await loadBriefing();
  }

  async function initTable() {
    const user = await requireSession('table.html', ['Workspace', 'Data', 'Positions']);
    if (!user) return;

    const status = document.getElementById('table-status');
    const tableBody = document.getElementById('positions-body');
    const snapshotMeta = document.getElementById('positions-meta');
    const form = document.getElementById('position-form');
    const formTitle = document.getElementById('position-form-title');
    const versionMeta = document.getElementById('position-version-meta');
    const deleteButton = document.getElementById('delete-position');
    const submitButton = form.querySelector('button[type="submit"]');
    const formNodes = {
      ticker: document.getElementById('form-ticker'),
      name: document.getElementById('form-name'),
      quantity: document.getElementById('form-quantity'),
      marketValue: document.getElementById('form-market-value'),
      assetClass: document.getElementById('form-asset-class'),
      region: document.getElementById('form-region'),
      sector: document.getElementById('form-sector'),
      subsector: document.getElementById('form-subsector'),
      segment: document.getElementById('form-segment'),
      custodian: document.getElementById('form-custodian'),
      notes: document.getElementById('form-notes'),
    };
    let selected = null;
    let mutationBusy = false;
    const SUBSECTORS_BY_SECTOR = {
      private_equity: ['buyout', 'growth_equity', 'venture_capital', 'co_investment', 'secondaries'],
      technology: ['application_software', 'semiconductors', 'ai_infrastructure', 'it_services'],
      financials: ['banks', 'insurance', 'asset_management', 'private_credit'],
      healthcare: ['biotech', 'pharma', 'medical_devices', 'health_services'],
      consumer_discretionary: ['retail', 'consumer_internet', 'travel_leisure', 'autos'],
      consumer_staples: ['food_beverage', 'household_products', 'consumer_brands'],
      industrials: ['aerospace_defense', 'transportation', 'capital_goods'],
      energy: ['upstream', 'midstream', 'downstream', 'energy_transition'],
      fixed_income: ['investment_grade_credit', 'high_yield', 'distressed_debt', 'government_bonds', 'structured_credit'],
      real_estate: ['reit', 'residential', 'commercial', 'logistics'],
      real_assets: ['infrastructure', 'timber', 'agriculture', 'commodities'],
      cash: ['operating_cash', 'money_market'],
    };
    const DEFAULT_SUBSECTORS = ['other', 'multi_strategy'];

    function normalizeTaxonomyValue(value) {
      return String(value || '')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '');
    }

    function taxonomyLabel(value) {
      const normalized = normalizeTaxonomyValue(value);
      if (!normalized) return '';
      if (normalized === 'reit') return 'REIT';
      if (normalized === 'ig_credit') return 'IG Credit';
      return normalized.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase());
    }

    function ensureSelectValue(selectNode, value, fallback = '') {
      if (!selectNode) return;
      const normalized = normalizeTaxonomyValue(value);
      if (!normalized) {
        selectNode.value = fallback;
        return;
      }
      const hasOption = Array.from(selectNode.options).some((option) => option.value === normalized);
      selectNode.value = hasOption ? normalized : fallback;
    }

    function applySubsectorOptions(sectorValue, preferredSubsector = '') {
      const sectorKey = normalizeTaxonomyValue(sectorValue);
      const options = SUBSECTORS_BY_SECTOR[sectorKey] || DEFAULT_SUBSECTORS;
      formNodes.subsector.innerHTML = `
        <option value="">Unset</option>
        ${options.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(taxonomyLabel(value))}</option>`).join('')}
      `;
      ensureSelectValue(formNodes.subsector, preferredSubsector, '');
    }

    function syncMutationButtons() {
      setEnabled(submitButton, !mutationBusy);
      setEnabled(deleteButton, !mutationBusy && Boolean(selected));
    }

    function setForm(position) {
      selected = position;
      formTitle.textContent = position ? `Edit ${position.ticker || position.name || 'position'}` : 'Add position';
      formNodes.ticker.value = position?.ticker || '';
      formNodes.ticker.disabled = Boolean(position);
      formNodes.name.value = position?.name || '';
      formNodes.quantity.value = position?.quantity ?? '';
      formNodes.marketValue.value = position?.market_value_usd ?? '';
      ensureSelectValue(formNodes.assetClass, position?.asset_class || position?.factor_asset_class, 'public_equity');
      ensureSelectValue(formNodes.region, position?.geo_region || position?.factor_region);
      ensureSelectValue(formNodes.sector, position?.sector || position?.factor_sector);
      applySubsectorOptions(formNodes.sector.value, position?.factor_subsector || '');
      ensureSelectValue(formNodes.segment, position?.market_segment || position?.factor_market_segment);
      formNodes.custodian.value = position?.custodian || '';
      formNodes.notes.value = position?.notes || '';
      if (versionMeta) {
        if (position) {
          const added = position.first_seen_at || position.created_at;
          const modified = position.last_modified_at || position.created_at;
          versionMeta.textContent = `Date added ${formatDateTime(added)} · Date modified ${formatDateTime(modified)}`;
        } else {
          versionMeta.textContent = 'Date added and modified tags appear after this position is saved.';
        }
      }
      bindFormattedNumberInputs(form);
      syncMutationButtons();
    }

    function showOrDash(value) {
      const text = String(value ?? '').trim();
      return text || '—';
    }

    function formatPositionPrice(item) {
      const price = Number(item?.price_usd);
      if (Number.isFinite(price) && price > 0) return formatCurrency(price, 2);
      const quantity = Number(item?.quantity);
      const marketValue = Number(item?.market_value_usd);
      if (Number.isFinite(quantity) && quantity > 0 && Number.isFinite(marketValue) && marketValue > 0) {
        return formatCurrency(marketValue / quantity, 2);
      }
      return '—';
    }

    async function loadPositions(selectId) {
      try {
        const response = await api('/portfolio/positions');
        snapshotMeta.textContent = `${response.total} positions`;
        tableBody.innerHTML = response.items
          .map(
            (item) => `
              <tr data-id="${escapeHtml(item.id)}" class="${selectId === item.id || (!selectId && selected?.id === item.id) ? 'is-selected' : ''}">
                <td>${escapeHtml(item.ticker)}</td>
                <td>${escapeHtml(item.name || '')}</td>
                <td class="num">${escapeHtml(formatNumber(item.quantity || 0, 2))}</td>
                <td class="num">${escapeHtml(formatPositionPrice(item))}</td>
                <td class="num">${escapeHtml(formatCurrency(item.market_value_usd || 0))}</td>
                <td>${escapeHtml(showOrDash(taxonomyLabel(item.asset_class || item.factor_asset_class)))}</td>
                <td>${escapeHtml(showOrDash(taxonomyLabel(item.market_segment || item.factor_market_segment)))}</td>
                <td>${escapeHtml(showOrDash(item.custodian))}</td>
                <td>${escapeHtml(showOrDash(titleCase(item.price_source || 'manual')))}</td>
                <td>${escapeHtml(formatDateTime(item.first_seen_at || item.created_at))}</td>
                <td>${escapeHtml(formatDateTime(item.last_modified_at || item.created_at))}</td>
              </tr>
            `
          )
          .join('');
        if (!response.items.length) {
          tableBody.innerHTML = '<tr><td colspan="11" class="mvp-empty">No positions yet. Add the first holding from the editor.</td></tr>';
        }

        const selectedPosition = response.items.find((item) => item.id === selectId) || response.items.find((item) => item.id === selected?.id) || null;
        setForm(selectedPosition);

        tableBody.querySelectorAll('tr').forEach((row) => {
          row.addEventListener('click', () => {
            const position = response.items.find((item) => item.id === row.dataset.id);
            tableBody.querySelectorAll('tr').forEach((node) => node.classList.remove('is-selected'));
            row.classList.add('is-selected');
            setForm(position || null);
          });
        });

        setStatus(status, '', '');
      } catch (error) {
        tableBody.innerHTML = '<tr><td colspan="11" class="mvp-empty">Unable to load positions.</td></tr>';
        setStatus(status, error.message, 'error');
      }
    }

    document.getElementById('new-position').addEventListener('click', () => {
      tableBody.querySelectorAll('tr').forEach((node) => node.classList.remove('is-selected'));
      setForm(null);
    });

    formNodes.sector.addEventListener('change', () => {
      applySubsectorOptions(formNodes.sector.value, '');
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const isEdit = Boolean(selected);
      mutationBusy = true;
      syncMutationButtons();
      const nameValue = formNodes.name.value.trim();
      const normalizedAssetClass = normalizeTaxonomyValue(formNodes.assetClass.value) || 'public_equity';
      const normalizedSector = normalizeTaxonomyValue(formNodes.sector.value) || null;
      const normalizedSubsector = normalizeTaxonomyValue(formNodes.subsector.value) || null;
      const marketSegment = normalizeTaxonomyValue(formNodes.segment.value) || null;
      const geoRegion = normalizeTaxonomyValue(formNodes.region.value) || null;
      const basePayload = {
        name: nameValue || null,
        quantity: parseFormattedNumber(formNodes.quantity.value) || 0,
        market_value_usd: parseFormattedNumber(formNodes.marketValue.value) || 0,
        asset_class: normalizedAssetClass,
        geo_region: geoRegion,
        sector: normalizedSector,
        market_segment: marketSegment,
        factor_asset_class: normalizedAssetClass,
        factor_sector: normalizedSector,
        factor_subsector: normalizedSubsector,
        factor_market_segment: marketSegment,
        factor_country: null,
        factor_region: geoRegion,
        factor_tag_source: 'manual',
        factor_tag_confidence: 1,
        custodian: formNodes.custodian.value.trim() || null,
        notes: formNodes.notes.value.trim() || null,
      };

      try {
        let response;
        if (isEdit) {
          response = await api(`/portfolio/positions/${selected.id}`, { method: 'PATCH', body: basePayload });
        } else {
          const identifier = buildPositionIdentifier(formNodes.ticker.value, nameValue);
          response = await api('/portfolio/positions', {
            method: 'POST',
            body: {
              ...basePayload,
              ticker: identifier,
              position_currency: preferredCurrency,
            },
          });
        }
        await loadPositions(response.position_id);
        setStatus(status, isEdit ? 'Position updated.' : 'Position created.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      } finally {
        mutationBusy = false;
        syncMutationButtons();
      }
    });

    deleteButton.addEventListener('click', async () => {
      if (!selected) return;
      mutationBusy = true;
      syncMutationButtons();
      try {
        await api(`/portfolio/positions/${selected.id}`, { method: 'DELETE' });
        setForm(null);
        await loadPositions(null);
        setStatus(status, 'Position removed from the current portfolio.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      } finally {
        mutationBusy = false;
        syncMutationButtons();
      }
    });

    await loadPositions(null);
  }

  async function initDocuments() {
    const user = await requireSession('documents.html', ['Workspace', 'Data', 'Documents']);
    if (!user) return;
    bindFileDropzones(document);

    const status = document.getElementById('documents-status');
    const summary = document.getElementById('documents-summary');
    const folders = document.getElementById('document-folders');
    const list = document.getElementById('documents-list');
    const preview = document.getElementById('document-preview');
    const tagInput = document.getElementById('document-tag-input');
    const parseButton = document.getElementById('parse-document');
    const saveReviewButton = document.getElementById('save-document-review');
    const approveButton = document.getElementById('approve-document');
    const saveTagButton = document.getElementById('save-document-tag');
    const deleteButton = document.getElementById('delete-document');
    const pageUrl = new URL(window.location.href);
    let selectedId = pageUrl.searchParams.get('documentId') || '';
    let currentReview = null;
    let currentDocuments = [];
    let activeFolder = '';
    let activeObjectUrl = '';
    const parseStages = ['librarian', 'accountant', 'risk_officer', 'treasury', 'reconciliation'];
    const parseProgress = {
      documentId: '',
      active: false,
      stageIndex: -1,
      stageTimer: null,
      pollTimer: null,
    };

    async function loadExtraction(documentId) {
      try {
        return await api(`/documents/${documentId}/extraction`);
      } catch {
        return null;
      }
    }

    async function loadReview(documentId) {
      try {
        return await api(`/documents/${documentId}/review`);
      } catch {
        return null;
      }
    }

    async function loadDocumentDetail(documentId) {
      try {
        return await api(`/documents/${documentId}`);
      } catch {
        return null;
      }
    }

    function stopParseProgress() {
      parseProgress.active = false;
      parseProgress.documentId = '';
      parseProgress.stageIndex = -1;
      if (parseProgress.stageTimer) window.clearInterval(parseProgress.stageTimer);
      if (parseProgress.pollTimer) window.clearInterval(parseProgress.pollTimer);
      parseProgress.stageTimer = null;
      parseProgress.pollTimer = null;
    }

    function startParseProgress(documentId) {
      stopParseProgress();
      parseProgress.active = true;
      parseProgress.documentId = documentId;
      parseProgress.stageIndex = 0;
      parseProgress.stageTimer = window.setInterval(async () => {
        parseProgress.stageIndex = Math.min(parseProgress.stageIndex + 1, parseStages.length - 1);
        const selectedDocument = currentDocuments.find((item) => item.id === documentId);
        if (selectedDocument) await renderPreview(selectedDocument);
      }, 900);
      parseProgress.pollTimer = window.setInterval(async () => {
        const detail = await loadDocumentDetail(documentId);
        if (!detail) return;
        currentDocuments = currentDocuments.map((item) => (item.id === detail.id ? detail : item));
        if (detail.extraction_result_id) {
          stopParseProgress();
        }
        const selectedDocument = currentDocuments.find((item) => item.id === documentId);
        if (selectedDocument) await renderPreview(selectedDocument);
      }, 1200);
    }

    function renderParseProgress(documentRecord, extraction, review) {
      const isActive = parseProgress.active && parseProgress.documentId === documentRecord.id;
      const overallConfidence = review?.reconciliation?.overall_confidence;
      if (!isActive && !extraction) return '';
      return `
        <div class="mvp-card pad">
          <div class="uplabel">Parse pipeline</div>
          <div class="mvp-review-fields" style="margin-top:12px">
            ${parseStages.map((stage, index) => {
              let tone = '';
              let label = 'Pending';
              if (isActive && index < parseProgress.stageIndex) {
                tone = 'good';
                label = 'Done';
              } else if (isActive && index === parseProgress.stageIndex) {
                tone = 'elevated';
                label = 'Running';
              } else if (!isActive && extraction) {
                tone = 'good';
                label = 'Done';
              }
              return `
                <div class="mvp-review-field">
                  <div class="mvp-review-field-head">
                    <div class="mvp-item-title">${escapeHtml(titleCase(stage))}</div>
                    <span class="mvp-pill ${tone || 'watch'}">${escapeHtml(label)}</span>
                  </div>
                  <div class="mvp-review-field-meta"><span>Document parse pipeline</span></div>
                </div>
              `;
            }).join('')}
          </div>
          ${!isActive && extraction ? `
            <div class="mvp-metadata" style="margin-top:12px">
              <span>Rows extracted: ${formatNumber(extraction.positions?.length || 0, 0)}</span>
              <span>Needs review: ${formatNumber(extraction.needs_review_count || 0, 0)}</span>
              <span>Overall confidence: ${overallConfidence != null ? formatNumber(overallConfidence, 2) : 'n/a'}</span>
            </div>
          ` : '<div class="mvp-item-subtle" style="margin-top:12px">Parsing in progress. Status updates will refresh automatically.</div>'}
        </div>
      `;
    }

    function releaseActiveObjectUrl() {
      if (!activeObjectUrl) return;
      try {
        URL.revokeObjectURL(activeObjectUrl);
      } catch {
        // no-op
      }
      activeObjectUrl = '';
    }

    function syncDocumentActions(documentRecord = null) {
      const hasSelection = Boolean(documentRecord && documentRecord.id);
      setEnabled(parseButton, hasSelection);
      setEnabled(saveReviewButton, hasSelection);
      setEnabled(approveButton, hasSelection);
      setEnabled(saveTagButton, hasSelection);
      setEnabled(deleteButton, hasSelection);
      setEnabled(tagInput, hasSelection);
    }

    function formatReviewValue(value, options = {}) {
      if (value == null || value === '') return options.empty || 'Not extracted';
      if (typeof value === 'number') {
        if (options.kind === 'currency') return formatCurrency(value, 0);
        if (options.kind === 'pct') return formatPct(value, 1);
        return formatNumber(value, 2);
      }
      if (Array.isArray(value)) {
        if (!value.length) return options.empty || 'None';
        return value.map((item) => {
          if (typeof item === 'object' && item) {
            if (item.name && item.weight != null) {
              return `${item.name} (${formatCompactCurrency(item.weight)})`;
            }
            return JSON.stringify(item);
          }
          return String(item);
        }).join(' · ');
      }
      if (typeof value === 'object') {
        const entries = Object.entries(value);
        if (!entries.length) return options.empty || 'None';
        return entries.map(([key, entryValue]) => {
          if (typeof entryValue === 'number') return `${titleCase(key)} ${formatPct(entryValue, 1)}`;
          return `${titleCase(key)} ${entryValue}`;
        }).join(' · ');
      }
      return String(value);
    }

    function renderArtifactField(label, value, source, confidence, options = {}) {
      return `
        <div class="mvp-review-field">
          <div class="mvp-review-field-head">
            <div class="mvp-item-title">${escapeHtml(label)}</div>
            ${confidence != null ? `<span class="mvp-pill ${confidenceTone(confidence)}">${formatNumber(confidence, 2)} conf</span>` : ''}
          </div>
          <div class="mvp-review-field-value">${escapeHtml(formatReviewValue(value, options))}</div>
          <div class="mvp-review-field-meta">
            <span>${escapeHtml(source)}</span>
            ${options.badge ? `<span>${escapeHtml(options.badge)}</span>` : ''}
          </div>
        </div>
      `;
    }

    function renderWireField(label, field, value, confidence) {
      return `
        <div class="mvp-field">
          <label for="treasury-${field}">
            ${escapeHtml(label)}
            <span class="mvp-pill elevated">HITL</span>
          </label>
          <input id="treasury-${field}" data-treasury-field="${field}" value="${escapeHtml(value || '')}"/>
          <div class="mvp-item-subtle">Treasury agent · ${formatNumber(confidence || 0, 2)} confidence · always confirm manually</div>
        </div>
      `;
    }

    function renderReviewEditor(review) {
      if (!review) return '';
      const fieldReviews = Array.isArray(review.field_reviews) ? review.field_reviews : [];
      const positions = Array.isArray(review.positions) ? review.positions : [];
      const confidenceRows = Array.isArray(review.confidence) ? review.confidence : [];
      const rowConfidenceByIndex = new Map(confidenceRows.map((item) => [Number(item.row || 0) - 1, item]));
      const unresolvedFieldReviews = fieldReviews.filter((item) => !item.resolved);
      return `
        <div class="mvp-card pad" style="margin-top:16px">
          <div class="mvp-review-header">
            <div>
              <div class="uplabel">Review workspace</div>
              <h3>Extraction artifact review</h3>
            </div>
            <div class="mvp-metadata">
              <span>Doc type: ${escapeHtml(review.classification?.doc_type || 'unknown')}</span>
              <span>Classifier: ${escapeHtml(review.classification?.model || 'n/a')}</span>
              <span>Reconciliation: ${escapeHtml(review.reconciliation?.model || 'n/a')}</span>
              <span>${formatNumber(review.needs_review_count || 0, 0)} items need review</span>
            </div>
          </div>
          <div class="mvp-review-grid" style="margin-top:14px">
            <div class="mvp-review-section">
              <div class="mvp-review-section-head">
                <div>
                  <div class="uplabel">Artifacts</div>
                  <h4>Field ledger</h4>
                </div>
                <span class="mvp-pill ${confidenceTone(review.reconciliation?.overall_confidence || 0)}">${formatNumber(review.reconciliation?.overall_confidence || 0, 2)} overall</span>
              </div>
              <div class="mvp-review-fields" style="margin-top:12px">
                ${renderArtifactField('Document type', review.classification?.doc_type, 'Librarian agent', review.classification?.confidence)}
                ${renderArtifactField('General partner', review.classification?.gp_name, 'Librarian agent', review.classification?.confidence)}
                ${renderArtifactField('Fund name', review.classification?.fund_name, 'Librarian agent', review.classification?.confidence)}
                ${renderArtifactField('Statement period', review.classification?.period, 'Librarian agent', review.classification?.confidence)}
                ${renderArtifactField('Call amount', review.treasury?.call_amount, 'Treasury agent', review.treasury?.confidence, { kind: 'currency' })}
                ${renderArtifactField('Call due date', review.treasury?.call_due_date, 'Treasury agent', review.treasury?.confidence)}
                ${renderArtifactField('Distribution amount', review.treasury?.distribution_amount, 'Treasury agent', review.treasury?.confidence, { kind: 'currency' })}
                ${renderArtifactField('Distribution date', review.treasury?.distribution_date, 'Treasury agent', review.treasury?.confidence)}
                ${renderArtifactField('Sector exposures', review.risk?.sector_exposures, 'Risk officer agent', review.risk?.confidence)}
                ${renderArtifactField('Geography', review.risk?.geography, 'Risk officer agent', review.risk?.confidence)}
                ${renderArtifactField('Red flags', review.risk?.red_flags, 'Risk officer agent', review.risk?.confidence, { empty: 'No red flags detected' })}
                ${renderArtifactField('Layout parser', review.layout?.parser, 'Layout parser', null)}
              </div>
            </div>
            <div class="mvp-review-section">
              <div class="mvp-review-section-head">
                <div>
                  <div class="uplabel">Human review</div>
                  <h4>Wire instructions</h4>
                </div>
                <span class="mvp-pill elevated">Always HITL</span>
              </div>
              <div class="mvp-form-grid" style="margin-top:12px">
                ${renderWireField('Wire bank', 'wire_bank', review.treasury?.wire_bank, review.treasury?.confidence)}
                ${renderWireField('Wire account', 'wire_account', review.treasury?.wire_account, review.treasury?.confidence)}
                ${renderWireField('Wire routing / ABA', 'wire_routing', review.treasury?.wire_routing, review.treasury?.confidence)}
                ${renderWireField('Wire reference', 'wire_reference', review.treasury?.wire_reference, review.treasury?.confidence)}
              </div>
              <div class="mvp-form-grid" style="margin-top:12px">
                <div class="mvp-field">
                  <label for="treasury-contact_name">Contact name</label>
                  <input id="treasury-contact_name" data-treasury-field="contact_name" value="${escapeHtml(review.treasury?.contact_name || '')}"/>
                  <div class="mvp-item-subtle">Treasury agent</div>
                </div>
                <div class="mvp-field">
                  <label for="treasury-contact_email">Contact email</label>
                  <input id="treasury-contact_email" data-treasury-field="contact_email" value="${escapeHtml(review.treasury?.contact_email || '')}"/>
                  <div class="mvp-item-subtle">Treasury agent</div>
                </div>
              </div>
              <div class="mvp-list" style="margin-top:14px">
                ${
                  fieldReviews.length
                    ? fieldReviews.map((item) => `
                        <label class="mvp-item mvp-review-check ${item.resolved ? 'is-resolved' : ''}">
                          <div>
                            <div class="mvp-item-title">
                              ${escapeHtml(item.field)}
                              ${item.field === 'wire_instructions' ? '<span class="mvp-pill elevated">HITL</span>' : ''}
                            </div>
                            <div class="mvp-item-subtle">${escapeHtml(item.reason)} · confidence ${formatNumber(item.confidence || 0, 2)}</div>
                          </div>
                          <input type="checkbox" data-review-field="${escapeHtml(item.field)}" ${item.resolved ? 'checked' : ''}/>
                        </label>
                      `).join('')
                    : '<div class="mvp-empty">No field-level review flags.</div>'
                }
              </div>
              <div class="mvp-item-subtle" style="margin-top:10px">
                ${unresolvedFieldReviews.length ? `${formatNumber(unresolvedFieldReviews.length, 0)} unresolved review flags remain.` : 'All review flags resolved.'}
              </div>
            </div>
          </div>
          <div class="mvp-review-section" style="margin-top:14px">
            <div class="mvp-review-section-head">
              <div>
                <div class="uplabel">Rows</div>
                <h4>Position candidates</h4>
              </div>
            </div>
            <div class="mvp-list" style="margin-top:12px">
              ${
                positions.length
                  ? positions.map((position, index) => {
                      const rowReview = rowConfidenceByIndex.get(index) || {};
                      const sourceSheet = position.source_ref?.sheet_name || 'source unavailable';
                      const sourceRow = position.source_ref?.sheet_row_index || position.source_ref?.row_number || 'n/a';
                      return `
                        <div class="mvp-card pad mvp-review-position">
                          <div class="mvp-item" style="margin-bottom:12px">
                            <div>
                              <div class="mvp-item-title">Position ${index + 1}</div>
                              <div class="mvp-item-subtle">${escapeHtml(position.notes || 'review candidate')}</div>
                            </div>
                            <div class="mvp-review-position-meta">
                              <span class="mvp-pill ${confidenceTone(rowReview.confidence || 0)}">${formatNumber(rowReview.confidence || 0, 2)} conf</span>
                              <span class="mvp-item-subtle">Accountant agent · ${escapeHtml(sourceSheet)} row ${escapeHtml(String(sourceRow))}</span>
                            </div>
                          </div>
                          <div class="mvp-form-grid">
                            <div class="mvp-field"><label>Ticker</label><input data-position-index="${index}" data-position-field="ticker" value="${escapeHtml(position.ticker || '')}"/></div>
                            <div class="mvp-field"><label>Name</label><input data-position-index="${index}" data-position-field="name" value="${escapeHtml(position.name || '')}"/></div>
                            <div class="mvp-field"><label>Quantity</label><input data-format="decimal" data-position-index="${index}" data-position-field="quantity" value="${escapeHtml(position.quantity ?? '')}"/></div>
                            <div class="mvp-field"><label>Market value USD</label><input data-format="decimal" data-position-index="${index}" data-position-field="market_value_usd" value="${escapeHtml(position.market_value_usd ?? '')}"/></div>
                            <div class="mvp-field"><label>Asset class</label><input data-position-index="${index}" data-position-field="asset_class" value="${escapeHtml(position.asset_class || '')}"/></div>
                            <div class="mvp-field"><label>Region</label><input data-position-index="${index}" data-position-field="geo_region" value="${escapeHtml(position.geo_region || '')}"/></div>
                            <div class="mvp-field"><label>Sector</label><input data-position-index="${index}" data-position-field="sector" value="${escapeHtml(position.sector || '')}"/></div>
                            <div class="mvp-field"><label>Market segment</label><input data-position-index="${index}" data-position-field="market_segment" value="${escapeHtml(position.market_segment || '')}"/></div>
                          </div>
                          ${
                            Array.isArray(rowReview.issues) && rowReview.issues.length
                              ? `<div class="mvp-review-issues">${rowReview.issues.map((issue) => `<span>${escapeHtml(issue)}</span>`).join('')}</div>`
                              : ''
                          }
                        </div>
                      `;
                    }).join('')
                  : '<div class="mvp-empty">No extracted positions to edit yet.</div>'
              }
            </div>
          </div>
        </div>
      `;
    }

    async function renderPreview(documentRecord) {
      if (!documentRecord) {
        syncDocumentActions(null);
        releaseActiveObjectUrl();
        currentReview = null;
        preview.innerHTML = '<div class="mvp-empty">No document selected. Upload and parse a file, then select it from the list to open source preview, review fields, and approve.</div>';
        return;
      }
      syncDocumentActions(documentRecord);
      const extraction = documentRecord.extraction_result_id ? await loadExtraction(documentRecord.id) : null;
      const review = documentRecord.extraction_result_id ? await loadReview(documentRecord.id) : null;
      currentReview = review;
      tagInput.value = documentRecord.tag || '';
      const filePath = `/documents/${documentRecord.id}/file`;
      let fileViewMarkup = '<div class="mvp-item-subtle">Original file preview unavailable.</div>';
      try {
        releaseActiveObjectUrl();
        const { blob, contentType } = await fetchBlob(filePath);
        activeObjectUrl = URL.createObjectURL(blob);
        const isPdf = String(contentType || '').toLowerCase().includes('application/pdf');
        if (isPdf) {
          fileViewMarkup = `
            <iframe src="${activeObjectUrl}" title="${escapeHtml(documentRecord.filename)}" style="width:100%;height:320px;border:1px solid var(--rule);border-radius:12px;background:#fff"></iframe>
            <div style="margin-top:10px">
              <button type="button" class="btn" data-open-source-document-tab="${escapeHtml(documentRecord.id)}"><span class="ms">open_in_new</span>Open in new tab</button>
              <button type="button" class="btn" data-open-source-document="${escapeHtml(documentRecord.id)}"><span class="ms">download</span>Download source file</button>
            </div>
          `;
        } else {
          fileViewMarkup = `
            <div class="mvp-item-subtle">Inline preview is supported for PDF files. This ${escapeHtml(documentRecord.file_type.toUpperCase())} file is available via open/download.</div>
            <div style="margin-top:10px">
              <button type="button" class="btn" data-open-source-document-tab="${escapeHtml(documentRecord.id)}"><span class="ms">open_in_new</span>Open source file</button>
              <button type="button" class="btn" data-open-source-document="${escapeHtml(documentRecord.id)}"><span class="ms">download</span>Download source file</button>
            </div>
          `;
        }
      } catch (error) {
        releaseActiveObjectUrl();
        fileViewMarkup = `<div class="mvp-item-subtle">${escapeHtml(error.message || 'Unable to load source file preview.')}</div>`;
      }
      preview.innerHTML = `
        <div class="mvp-card pad">
          <div class="mvp-item">
            <div>
              <div class="mvp-item-title">${escapeHtml(documentRecord.filename)}</div>
              <div class="mvp-item-subtle">${escapeHtml(documentRecord.folder)} · ${escapeHtml(documentRecord.file_type)} · ${formatNumber(documentRecord.file_size_bytes, 0)} bytes</div>
            </div>
            <span class="mvp-pill ${documentStatusTone(documentRecord.extraction_status)}">${escapeHtml(documentStatusLabel(documentRecord.extraction_status))}</span>
          </div>
          <div class="mvp-metadata" style="margin-top:12px">
            <span>Malware scan: ${escapeHtml(documentRecord.malware_scan_status)}</span>
            <span>Tag: ${escapeHtml(documentRecord.tag || 'none')}</span>
          </div>
          <div class="mvp-item-subtle" style="margin-top:12px">${escapeHtml(documentStatusDescription(documentRecord, extraction))}</div>
        </div>
        ${renderParseProgress(documentRecord, extraction, review)}
        <div class="mvp-card pad">
          <div class="uplabel">Source file</div>
          <div style="margin-top:10px">${fileViewMarkup}</div>
        </div>
        <div class="mvp-card pad">
          <div class="uplabel">Preview</div>
          ${
            extraction
              ? `
                <div class="mvp-item-subtle" style="margin-top:10px">First extracted rows for a quick QA pass before approval.</div>
                <div class="mvp-list" style="margin-top:12px">
                  ${extraction.positions
                    .slice(0, 6)
                    .map(
                      (position, index) => `
                        <div class="mvp-item">
                          <div>
                            <div class="mvp-item-title">${escapeHtml(position.ticker || position.name || `Row ${index + 1}`)}</div>
                            <div class="mvp-item-subtle">${escapeHtml(position.asset_class || 'unmapped')} · ${formatNumber(position.quantity || 0, 2)} units</div>
                          </div>
                          <div style="text-align:right">
                            <div class="mvp-item-title">${position.market_value_usd != null ? formatCurrency(position.market_value_usd) : 'n/a'}</div>
                            <div class="mvp-item-subtle">review rows: ${extraction.needs_review_count}</div>
                          </div>
                        </div>
                      `
                    )
                    .join('')}
                </div>
              `
              : '<div class="mvp-empty">No extraction yet. Parse the file to create reviewable holdings and treasury fields.</div>'
          }
        </div>
        ${renderReviewEditor(review)}
      `;
      bindFormattedNumberInputs(preview);
      preview.querySelectorAll('[data-open-source-document]').forEach((button) => {
        button.addEventListener('click', async () => {
          try {
            const filename = await download(filePath, documentRecord.filename);
            setStatus(status, `Downloaded source file: ${filename}.`, 'success');
          } catch (error) {
            setStatus(status, error.message, 'error');
          }
        });
      });
      preview.querySelectorAll('[data-open-source-document-tab]').forEach((button) => {
        button.addEventListener('click', () => {
          if (!activeObjectUrl) {
            setStatus(status, 'Source file preview is not available yet.', 'error');
            return;
          }
          window.open(activeObjectUrl, '_blank', 'noopener,noreferrer');
        });
      });
    }

    async function loadDocuments(options = {}) {
      const preserveStatus = Boolean(options.preserveStatus);
      const focusSelectedDocument = Boolean(options.focusSelectedDocument);
      try {
        const response = await api('/documents');
        const items = response.items || [];
        currentDocuments = items;
        const targetedDocument = selectedId ? items.find((item) => item.id === selectedId) : null;
        const folderEntries = Object.entries(response.folder_counts || {});
        if (activeFolder && !folderEntries.some(([name]) => name === activeFolder)) {
          activeFolder = '';
        }
        if (targetedDocument && (focusSelectedDocument || !activeFolder)) {
          activeFolder = targetedDocument.folder || '';
        }
        const visibleItems = activeFolder ? items.filter((item) => item.folder === activeFolder) : items;
        const selected =
          visibleItems.find((item) => item.id === selectedId) ||
          visibleItems[0] ||
          null;
        selectedId = selected?.id || '';
        summary.innerHTML = `
          <div class="mvp-feature-stat mvp-doc-summary-card">
            <div class="uplabel">Documents</div>
            <div class="value">${formatNumber(items.length, 0)}</div>
            <div class="meta">Files available in the current workspace library.</div>
          </div>
          <div class="mvp-feature-stat mvp-doc-summary-card">
            <div class="uplabel">Parsed</div>
            <div class="value">${formatNumber(items.filter((item) => item.extraction_status !== 'pending').length, 0)}</div>
            <div class="meta">Extraction completed and available in the review queue.</div>
          </div>
          <div class="mvp-feature-stat mvp-doc-summary-card">
            <div class="uplabel">Pending</div>
            <div class="value">${formatNumber(items.filter((item) => item.extraction_status === 'pending').length, 0)}</div>
            <div class="meta">Files that still need parse or approval work.</div>
          </div>
          <div class="mvp-feature-stat mvp-doc-summary-card">
            <div class="uplabel">Active folder</div>
            <div class="value">${escapeHtml(activeFolder || 'All files')}</div>
            <div class="meta">${escapeHtml(`${formatNumber(visibleItems.length, 0)} document${visibleItems.length === 1 ? '' : 's'} in scope`)}</div>
          </div>
          <div class="mvp-feature-stat mvp-doc-summary-card">
            <div class="uplabel">Latest upload</div>
            <div class="value">${escapeHtml(items[0]?.filename || 'No files yet')}</div>
            <div class="meta">${items[0]?.created_at ? `Uploaded ${escapeHtml(formatDateTime(items[0].created_at))}` : 'Upload a file to populate the review queue.'}</div>
          </div>
        `;

        folders.innerHTML = `
          <button type="button" class="${activeFolder ? '' : 'is-selected'}" data-folder="">
            <div class="mvp-item-title">All files</div>
            <div class="mvp-item-subtle">${formatNumber(items.length, 0)} files</div>
          </button>
          ${folderEntries
          .map(
            ([name, count]) => `
              <button type="button" class="${activeFolder === name ? 'is-selected' : ''}" data-folder="${escapeHtml(name)}">
                <div class="mvp-item-title">${escapeHtml(name)}</div>
                <div class="mvp-item-subtle">${formatNumber(count, 0)} files</div>
              </button>
            `
          )
          .join('')}
        `;

        folders.querySelectorAll('button[data-folder]').forEach((button) => {
          button.addEventListener('click', () => {
            activeFolder = button.dataset.folder || '';
            selectedId = '';
            loadDocuments({ preserveStatus: true });
          });
        });

        list.innerHTML = visibleItems.length
          ? visibleItems
              .map(
                (item) => `
                  <button type="button" data-id="${escapeHtml(item.id)}" class="${item.id === selectedId ? 'is-selected' : ''}">
                    <div class="mvp-item-title">
                      ${escapeHtml(item.filename)}
                      ${item.id === selectedId ? '<span class="mvp-pill elevated">Open</span>' : ''}
                      ${isRecentTimestamp(item.created_at) ? '<span class="mvp-pill good">Recent</span>' : ''}
                    </div>
                    <div class="mvp-item-subtle">${escapeHtml(item.folder)} · ${escapeHtml(item.file_type)} · ${escapeHtml(documentStatusLabel(item.extraction_status))}</div>
                    <div class="mvp-item-subtle">Uploaded ${escapeHtml(formatDateTime(item.created_at))}</div>
                  </button>
                `
              )
              .join('')
          : `<div class="mvp-empty">${activeFolder ? `No documents in ${escapeHtml(activeFolder)}.` : 'No documents uploaded yet.'}</div>`;

        list.querySelectorAll('button[data-id]').forEach((button) => {
          button.addEventListener('click', () => {
            selectedId = button.dataset.id || '';
            loadDocuments({ preserveStatus: true });
          });
        });

        await renderPreview(selected);
        if (!preserveStatus) {
          if (pageUrl.searchParams.get('uploaded') === '1' && selected) {
            setStatus(status, `Document uploaded and opened in the review queue: ${selected.filename}.`, 'success');
            pageUrl.searchParams.delete('uploaded');
            pageUrl.searchParams.set('documentId', selected.id);
            window.history.replaceState({}, '', `${pageUrl.pathname}${pageUrl.search ? `?${pageUrl.searchParams.toString()}` : ''}`);
          } else {
            setStatus(status, '', '');
          }
        }
      } catch (error) {
        summary.innerHTML = '';
        list.innerHTML = '<div class="mvp-empty">Unable to load documents.</div>';
        preview.innerHTML = '<div class="mvp-empty">No preview available.</div>';
        setStatus(status, error.message, 'error');
      }
    }

    document.getElementById('upload-document-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      const file = document.getElementById('upload-document-file').files[0];
      if (!file) {
        setStatus(status, 'Choose a document file first.', 'error');
        return;
      }
      const formData = new FormData();
      formData.append('folder', document.getElementById('upload-document-folder').value);
      formData.append('file', file);
      try {
        const documentRecord = await withButtonBusy(event.submitter, 'Uploading...', async () => api('/documents/upload', { method: 'POST', formData }));
        selectedId = documentRecord.id;
        activeFolder = documentRecord.folder || activeFolder;
        currentDocuments = [documentRecord, ...currentDocuments.filter((item) => item.id !== documentRecord.id)];
        await loadDocuments({ preserveStatus: true, focusSelectedDocument: true });
        setStatus(
          status,
          `Uploaded to ${user.workspace_name || 'workspace'}: ${documentRecord.filename}. Parsing in background...`,
          'success',
        );
        startParseProgress(selectedId);
        // Parse asynchronously so the uploaded file appears immediately even if parsing is slow.
        (async () => {
          try {
            await api(`/documents/${selectedId}/parse`, { method: 'POST' });
            stopParseProgress();
            await loadDocuments({ preserveStatus: true, focusSelectedDocument: true });
            setStatus(status, `Parse complete: ${documentRecord.filename}.`, 'success');
          } catch (error) {
            stopParseProgress();
            setStatus(status, error.message, 'error');
          }
        })();
      } catch (error) {
        stopParseProgress();
        setStatus(status, error.message, 'error');
      }
    });

    parseButton.addEventListener('click', async () => {
      if (!selectedId) return;
      try {
        const response = await withButtonBusy(parseButton, 'Parsing...', async () => {
          startParseProgress(selectedId);
          const selectedDocument = currentDocuments.find((item) => item.id === selectedId);
          if (selectedDocument) await renderPreview(selectedDocument);
          const parseResponse = await api(`/documents/${selectedId}/parse`, { method: 'POST' });
          stopParseProgress();
          return parseResponse;
        });
        setStatus(status, response.detail, 'success');
        await loadDocuments({ preserveStatus: true });
      } catch (error) {
        stopParseProgress();
        setStatus(status, error.message, 'error');
      }
    });

    saveReviewButton.addEventListener('click', async () => {
      if (!selectedId) return;
      const positionInputs = Array.from(preview.querySelectorAll('[data-position-index][data-position-field]'));
      const positions = Array.isArray(currentReview?.positions)
        ? currentReview.positions.map((item) => ({ ...item }))
        : [];
      positionInputs.forEach((input) => {
        const index = Number(input.dataset.positionIndex || 0);
        const field = input.dataset.positionField || '';
        positions[index] ||= {};
        if (field === 'quantity' || field === 'market_value_usd') {
          const parsed = parseFormattedNumber(input.value);
          positions[index][field] = Number.isFinite(parsed) ? parsed : null;
        } else {
          positions[index][field] = input.value.trim();
        }
      });
      const treasuryInputs = Array.from(preview.querySelectorAll('[data-treasury-field]'));
      const treasury = { ...(currentReview?.treasury || {}) };
      treasuryInputs.forEach((input) => {
        const field = input.dataset.treasuryField || '';
        if (!field) return;
        treasury[field] = input.value.trim() || null;
      });
      const resolvedFields = Array.from(preview.querySelectorAll('[data-review-field]:checked'))
        .map((input) => input.dataset.reviewField)
        .filter(Boolean);
      try {
        const response = await withButtonBusy(saveReviewButton, 'Saving review...', async () => api(`/documents/${selectedId}/review`, {
          method: 'PATCH',
          body: { positions, treasury, resolved_fields: resolvedFields },
        }));
        setStatus(status, `Review saved. ${response.needs_review_count} items still require attention.`, 'success');
        await loadDocuments({ preserveStatus: true });
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    approveButton.addEventListener('click', async () => {
      if (!selectedId) return;
      try {
        await withButtonBusy(approveButton, 'Approving...', async () => api(`/documents/${selectedId}/approve`, { method: 'POST' }));
        setStatus(status, 'Approved into portfolio — snapshot created.', 'success');
        await loadDocuments({ preserveStatus: true });
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    saveTagButton.addEventListener('click', async () => {
      if (!selectedId) return;
      try {
        const response = await withButtonBusy(saveTagButton, 'Saving tag...', async () => api(`/documents/${selectedId}/tag`, {
          method: 'POST',
          body: { tag: tagInput.value.trim() || 'reviewed' },
        }));
        setStatus(status, `Tag saved: ${response.tag || 'updated'}.`, 'success');
        await loadDocuments({ preserveStatus: true });
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    deleteButton.addEventListener('click', async () => {
      if (!selectedId) return;
      try {
        const response = await withButtonBusy(deleteButton, 'Deleting...', async () => api(`/documents/${selectedId}`, { method: 'DELETE' }));
        selectedId = '';
        setStatus(status, response.detail, 'success');
        await loadDocuments({ preserveStatus: true });
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    syncDocumentActions(null);
    await loadDocuments({ focusSelectedDocument: Boolean(selectedId) });
  }

  async function initAccess() {
    let user = await requireSession('access.html', ['Access']);
    if (!user) return;

    const userName = document.getElementById('access-user-name');
    const userEmail = document.getElementById('access-user-email');
    const userRole = document.getElementById('access-user-role');
    const sessionMode = document.getElementById('access-session-mode');
    const apiBase = document.getElementById('access-api-base');
    const workspace = document.getElementById('access-workspace');
    const members = document.getElementById('access-members');
    const refresh = document.getElementById('access-refresh');

    function renderAccess(nextUser) {
      const storageMode = window.localStorage.getItem(AUTH_STORAGE_PREFERENCE_KEY) === 'session'
        ? 'This browser session'
        : 'Remembered device';
      const apiRoute = getApiBase();
      if (userName) userName.textContent = nextUser.display_name || 'Workspace owner';
      if (userEmail) userEmail.textContent = nextUser.email || 'No email on session';
      if (userRole) userRole.textContent = titleCase(nextUser.role || 'owner');
      if (sessionMode) sessionMode.textContent = getAuthToken() ? storageMode : 'Cookie session';
      if (apiBase) apiBase.textContent = apiRoute.replace(/^https?:\/\//, '');
      if (workspace) workspace.textContent = nextUser.workspace_name || 'Current workspace';
      if (members) {
        members.innerHTML = `
          <tr>
            <td><div class="mvp-risk-name">${escapeHtml(nextUser.display_name || 'Workspace owner')}</div></td>
            <td>${escapeHtml(nextUser.email || 'Unknown')}</td>
            <td>${escapeHtml(titleCase(nextUser.role || 'owner'))}</td>
            <td><span class="mvp-pill good">Active</span></td>
          </tr>
        `;
      }
    }

    renderAccess(user);

    refresh?.addEventListener('click', async () => {
      await withButtonBusy(refresh, 'Refreshing...', async () => {
        const session = await api('/auth/session');
        user = session.user || user;
        sessionStorage.setItem('crb.user', JSON.stringify(user));
        renderAccess(user);
      });
    });

    markPageReady();
  }

  const initializers = {
    index: initIndex,
    login: initLogin,
    onboarding: initOnboarding,
    settings: initSettings,
    cockpit: initCockpit,
    assets: initAssets,
    briefings: initBriefings,
    briefing: initBriefingDetail,
    table: initTable,
    documents: initDocuments,
    liquidity: initLiquidity,
    overlay: initOverlay,
    access: initAccess,
  };

  document.addEventListener('DOMContentLoaded', () => {
    const page = document.body.dataset.page;
    const init = initializers[page];
    if (init) {
      init().catch((error) => {
        const status = document.querySelector('[data-global-status]');
        if (status) {
          setStatus(status, error.message, 'error');
        } else {
          console.error(error);
        }
      }).finally(() => {
        markPageReady();
      });
      return;
    }
    markPageReady();
  });

  window.CRBMvp = {
    api,
    getApiBase,
    resolveApiUrl,
    formatCurrency,
    formatCompactCurrency,
    formatNumber,
    formatPct,
    setStatus,
    escapeHtml,
  };
})();
