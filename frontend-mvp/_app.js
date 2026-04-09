(function () {
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

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function formatCurrency(value, digits = 0) {
    const number = Number(value || 0);
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
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

  function truncateText(value, maxLength) {
    const text = String(value || '').trim();
    if (!text || text.length <= maxLength) return text;
    return `${text.slice(0, maxLength - 1).trimEnd()}...`;
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
    const number = Number(value || 0);
    const abs = Math.abs(number);
    if (abs >= 1_000_000_000) return `${number < 0 ? '-' : ''}$${formatNumber(abs / 1_000_000_000, 2)}B`;
    if (abs >= 1_000_000) return `${number < 0 ? '-' : ''}$${formatNumber(abs / 1_000_000, 1)}M`;
    if (abs >= 1_000) return `${number < 0 ? '-' : ''}$${formatNumber(abs / 1_000, 1)}K`;
    return formatCurrency(number, 0);
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

  function titleCase(value) {
    return String(value || '')
      .replaceAll('_', ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());
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

  async function api(path, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = new Headers(options.headers || {});
    let body = options.body;

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

    const response = await fetch(path.startsWith('/api') ? path : `/api${path}`, {
      method,
      headers,
      body,
      credentials: 'include',
    });

    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json')
      ? await response.json()
      : await response.text();

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
    const response = await fetch(path.startsWith('/api') ? path : `/api${path}`, {
      credentials: 'include',
    });
    if (!response.ok) {
      const contentType = response.headers.get('content-type') || '';
      const payload = contentType.includes('application/json')
        ? await response.json()
        : await response.text();
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
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    return filename;
  }

  async function getSession() {
    const session = await api('/auth/session');
    sessionStorage.setItem('crb.user', JSON.stringify(session.user));
    return session.user;
  }

  function updateShellUser(user) {
    const initials = String(user.display_name || user.email || 'CR')
      .split(/\s+/)
      .map((part) => part[0] || '')
      .join('')
      .slice(0, 2)
      .toUpperCase();
    const avatar = document.getElementById('mvp-user-avatar');
    const name = document.getElementById('mvp-user-name');
    const role = document.getElementById('mvp-user-role');
    const workspace = document.getElementById('mvp-workspace-name');
    if (avatar) avatar.textContent = initials || 'CR';
    if (name) name.textContent = user.display_name || user.email;
    if (role) role.textContent = `${user.role} · ${user.email}`;
    if (workspace) workspace.textContent = user.workspace_name || 'ChiefRiskBot';
  }

  async function requireSession(activePage, crumbs) {
    let user;
    try {
      user = await getSession();
    } catch {
      window.location.href = `login.html?next=${encodeURIComponent(window.location.pathname.split('/').pop() || 'cockpit.html')}`;
      return null;
    }

    if (window.CRBMvpShell) {
      window.CRBMvpShell.mount(activePage, crumbs);
      updateShellUser(user);
      const logout = document.getElementById('mvp-logout');
      if (logout) {
        logout.addEventListener('click', async () => {
          try {
            await api('/auth/logout', { method: 'POST' });
          } catch {
            // ignore logout cleanup errors
          }
          sessionStorage.removeItem('crb.user');
          window.location.href = 'login.html';
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

  async function markOnboardingStep(step) {
    return api('/onboarding/step', { method: 'POST', body: { step } });
  }

  async function resolveAuthenticatedLanding(useNext = false) {
    const next = useNext ? getQueryParam('next') : '';
    if (next) return next;
    const state = await api('/onboarding/state');
    return state.is_complete ? 'cockpit.html' : 'onboarding.html';
  }

  async function initIndex() {
    try {
      await getSession();
      window.location.href = await resolveAuthenticatedLanding();
    } catch {
      window.location.href = 'login.html';
    }
  }

  async function initLogin() {
    try {
      await getSession();
      window.location.href = await resolveAuthenticatedLanding(true);
      return;
    } catch {
      // stay on login
    }

    const form = document.getElementById('login-form');
    const status = document.getElementById('login-status');
    const submit = document.getElementById('login-submit');

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      setStatus(status, '', '');
      submit.disabled = true;
      try {
        const payload = {
          email: document.getElementById('email').value.trim(),
          password: document.getElementById('password').value,
        };
        await api('/auth/login', { method: 'POST', body: payload });
        await getSession();
        window.location.href = await resolveAuthenticatedLanding(true);
      } catch (error) {
        setStatus(status, error.message, 'error');
      } finally {
        submit.disabled = false;
      }
    });
  }

  async function initOnboarding() {
    const user = await requireSession('onboarding.html', ['Workspace', 'Onboarding']);
    if (!user) return;

    const stateNode = document.getElementById('onboarding-steps');
    const status = document.getElementById('onboarding-status');
    const stateMeta = document.getElementById('onboarding-meta');
    const readyBanner = document.getElementById('onboarding-ready');

    async function refreshState() {
      const state = await api('/onboarding/state');
      stateNode.innerHTML = stepMarkup(state);
      stateMeta.textContent = `${state.completed_steps.length} of ${state.total_steps} steps complete`;
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
        const response = await api('/ingest/csv', { method: 'POST', formData });
        await markOnboardingStep('portfolio_uploaded');
        await ensureVarReady();
        await refreshState();
        setStatus(status, 'Portfolio uploaded and VaR computed. Your holdings are ready.', 'success');
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
        const documentRecord = await api('/documents/upload', { method: 'POST', formData });
        await api(`/documents/${documentRecord.id}/parse`, { method: 'POST' });
        await refreshState();
        setStatus(status, `Document uploaded and parsed: ${documentRecord.filename}.`, 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    document.getElementById('run-risk').addEventListener('click', async () => {
      try {
        await ensureRiskReady();
        await refreshState();
        setStatus(status, 'Risk analysis completed for the current portfolio.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    document.getElementById('generate-briefing').addEventListener('click', async () => {
      try {
        await ensureVarReady();
        await ensureRiskReady();
        const briefing = await api('/briefings/generate', { method: 'POST' });
        await markOnboardingStep('briefing_generated');
        await refreshState();
        setStatus(status, `${formatWeekLabel(briefing.week_label)} generated.`, 'success');
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
    const contributions = document.getElementById('cockpit-contribs');
    const varSummary = document.getElementById('cockpit-var-summary');
    const varStats = document.getElementById('cockpit-var-stats');
    const register = document.getElementById('cockpit-register');
    const overlayAlertTop = document.getElementById('cockpit-overlay-alerts-top');
    const overlaySummary = document.getElementById('cockpit-overlay-summary');
    const overlayFactors = document.getElementById('cockpit-overlay-factors');
    const overlayStress = document.getElementById('cockpit-overlay-stress');
    const overlayRegime = document.getElementById('cockpit-overlay-regime');
    const compositionTitle = document.getElementById('cockpit-composition-title');
    const compositionToggles = document.getElementById('cockpit-composition-toggles');
    const varToggles = document.getElementById('cockpit-var-toggles');
    const riskFilters = document.getElementById('cockpit-risk-filters');
    const compositionPalette = ['#1B2B5E', '#72594c', '#C9A449', '#006972', '#d3c3bc', '#8f6f9d'];
    const compositionTitles = {
      asset_class: 'Asset class mix',
      sector: 'Sector mix',
      geo_region: 'Geographic mix',
    };
    const varMetricConfig = {
      var_1d_99: {
        label: '1-Day VaR (99%)',
        formatter: (value) => formatCurrency(value),
        meta: (body) => `${formatPct(body.var_result.model_coverage_pct, 0)} modeled coverage`,
      },
      var_1d_95: {
        label: '1-Day VaR (95%)',
        formatter: (value) => formatCurrency(value),
        meta: (body) => `${formatPct(body.var_result.model_coverage_pct, 0)} modeled coverage`,
      },
      cvar_1d_95: {
        label: '1-Day CVaR (95%)',
        formatter: (value) => formatCurrency(value),
        meta: () => 'Expected loss in the worst tail',
      },
      max_drawdown_1y: {
        label: 'Max Drawdown (1Y)',
        formatter: (value) => formatPct(value, 2),
        meta: () => 'Historical drawdown estimate',
      },
    };
    let compositionDimension = 'asset_class';
    let activeVarMetric = 'var_1d_95';
    let riskSeverity = 'all';
    let cockpitBody = null;
    let overlayTriangulation = null;
    let overlayStressBody = null;
    let overlayRegimeBody = null;
    let dismissedOverlayAlerts = new Set();

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
      const metricConfig = varMetricConfig[activeVarMetric] || varMetricConfig.var_1d_95;
      const metricValue = body.var_result[activeVarMetric];
      const lossLabel = body.var_result.worst_scenario_date
        ? `${body.var_result.worst_scenario_date} worst day`
        : 'Worst day unavailable';
      varSummary.innerHTML = `
        <div>
          <div class="uplabel">${escapeHtml(metricConfig.label)}</div>
          <div class="mvp-var-headline">${metricConfig.formatter(metricValue)}</div>
          <div class="mvp-item-subtle">${escapeHtml(metricConfig.meta(body))}</div>
        </div>
        <div class="mvp-var-meta">
          <div>Computed ${escapeHtml(formatDateTime(body.var_result.computed_at))}</div>
          <div>${formatNumber(body.var_result.effective_lookback_days, 0)} lookback days</div>
        </div>
      `;

      varStats.innerHTML = `
        <div class="mvp-stat-item"><div class="uplabel">Worst day</div><div class="value">${formatCurrency(body.var_result.worst_scenario_loss)}</div><div class="meta">${escapeHtml(lossLabel)}</div></div>
        <div class="mvp-stat-item"><div class="uplabel">Coverage</div><div class="value">${formatPct(body.var_result.model_coverage_pct, 0)}</div><div class="meta">modeled</div></div>
        <div class="mvp-stat-item"><div class="uplabel">CVaR 99%</div><div class="value">${formatCurrency(body.var_result.cvar_1d_99)}</div><div class="meta">tail loss</div></div>
        <div class="mvp-stat-item"><div class="uplabel">Method</div><div class="value">${escapeHtml(titleCase(body.var_result.methodology))}</div><div class="meta">risk engine</div></div>
      `;

      contributions.innerHTML = (body.var_result.position_contributions || [])
        .slice(0, 6)
        .map(
          (item) => `
            <div class="mvp-item">
              <div>
                <div class="mvp-item-title">${escapeHtml(item.ticker)}</div>
                <div class="mvp-item-subtle">${escapeHtml(titleCase(item.method))}</div>
              </div>
              <div style="text-align:right">
                <div class="mvp-item-title">${formatCurrency(item.contribution_usd)}</div>
                <div class="mvp-item-subtle">${formatPct(item.contribution_pct, 1)}</div>
              </div>
            </div>
          `
        )
        .join('');
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

    function renderOverlay() {
      const summary = cockpitBody?.overlay_summary;
      if (!summary || !overlayTriangulation || !overlayStressBody || !overlayRegimeBody) {
        if (overlayAlertTop) overlayAlertTop.innerHTML = '';
        overlaySummary.innerHTML = '<div class="mvp-empty">Overlay data unavailable.</div>';
        overlayFactors.innerHTML = '';
        overlayStress.innerHTML = '';
        if (overlayRegime) overlayRegime.innerHTML = '';
        return;
      }

      const visibleAlerts = (overlayStressBody.alerts || []).filter((item) => !dismissedOverlayAlerts.has(item.rule || item.headline));
      if (overlayAlertTop) {
        overlayAlertTop.innerHTML = visibleAlerts.length
          ? `
              <div class="mvp-overlay-alerts mvp-overlay-alerts-top">
                ${visibleAlerts.map((item) => `
                  <div class="mvp-notice ${item.severity === 'priority' ? 'error' : ''}">
                    <div class="mvp-overlay-banner-head">
                      <strong>${escapeHtml(item.headline)}</strong>
                      <button type="button" class="btn" data-dismiss-alert="${escapeHtml(item.rule || item.headline)}">Dismiss</button>
                    </div>
                    ${escapeHtml(item.description)}
                  </div>
                `).join('')}
              </div>
            `
          : '';
        overlayAlertTop.querySelectorAll('[data-dismiss-alert]').forEach((button) => {
          button.addEventListener('click', () => {
            dismissedOverlayAlerts.add(button.dataset.dismissAlert || '');
            renderOverlay();
          });
        });
      }

      if (overlayRegime) {
        overlayRegime.innerHTML = `
          <span class="mvp-pill ${severityClass(summary.regime)}">${escapeHtml(titleCase(summary.regime))}</span>
          <span class="mvp-item-subtle">Changed ${escapeHtml(formatDateTime(overlayRegimeBody.created_at))}</span>
        `;
      }

      overlaySummary.innerHTML = `
        <div class="mvp-overlay-kpis">
          <div class="mvp-stat-item">
            <div class="uplabel">Composite score</div>
            <div class="value">${formatNumber(summary.composite_score, 2)}</div>
            <div class="meta">${escapeHtml(titleCase(summary.regime))} regime</div>
          </div>
          <div class="mvp-stat-item">
            <div class="uplabel">AUM at risk</div>
            <div class="value">${formatCompactCurrency(overlayTriangulation.aum_at_risk_usd)}</div>
            <div class="meta">Factors above 70</div>
          </div>
          <div class="mvp-stat-item">
            <div class="uplabel">Top factor</div>
            <div class="value">${escapeHtml(summary.top_risk_factors[0]?.label || 'N/A')}</div>
            <div class="meta">${formatCompactCurrency(summary.top_risk_factors[0]?.aum_exposed_usd || 0)}</div>
          </div>
          <div class="mvp-stat-item">
            <div class="uplabel">Trigger</div>
            <div class="value">${escapeHtml(titleCase(overlayRegimeBody.trigger_signal || 'baseline'))}</div>
            <div class="meta">${escapeHtml(overlayRegimeBody.methodology_note || '')}</div>
          </div>
        </div>
      `;

      overlayFactors.innerHTML = `
        <div class="mvp-overlay-panel mvp-overlay-scroll">
          <div class="uplabel">Factor table</div>
          <table class="mvp-table mvp-overlay-factor-table">
            <thead>
              <tr>
                <th>Factor</th>
                <th>Score</th>
                <th>Direction</th>
                <th class="num">% Port.</th>
                <th class="num">AUM</th>
              </tr>
            </thead>
            <tbody>
              ${(overlayTriangulation.factors || []).map((item) => `
                <tr>
                  <td>
                    <div class="mvp-risk-name">${escapeHtml(item.label)}</div>
                    <div class="mvp-risk-desc">${escapeHtml(titleCase(item.factor_type))}</div>
                  </td>
                  <td><span class="mvp-pill ${item.risk_score >= 85 ? 'priority' : item.risk_score >= 75 ? 'elevated' : 'watch'}">${formatNumber(item.risk_score, 0)}</span></td>
                  <td>${escapeHtml(titleCase(item.direction))}</td>
                  <td class="num">${formatPct(item.exposure_pct, 1)}</td>
                  <td class="num">${formatCompactCurrency(item.aum_exposed_usd)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;

      overlayStress.innerHTML = `
        <div class="mvp-overlay-panel mvp-overlay-scroll">
          <div class="uplabel">Stress scenarios</div>
          <div class="mvp-list">
            ${(overlayStressBody.scenarios || []).map((item) => `
              <div class="mvp-item">
                <div>
                  <div class="mvp-item-title">${escapeHtml(item.name)}</div>
                  <div class="mvp-item-subtle">${escapeHtml(item.description)}</div>
                  <div class="mvp-item-subtle">${escapeHtml((item.top_drivers || []).map((driver) => driver.label).join(' · '))}</div>
                </div>
                <div style="text-align:right">
                  <div class="mvp-item-title">${formatCompactCurrency(item.estimated_impact_usd)}</div>
                  <div class="mvp-item-subtle">${formatPct(item.estimated_impact_pct, 1)}</div>
                </div>
              </div>
            `).join('')}
          </div>
          ${visibleAlerts.length ? `
            <div class="mvp-overlay-alerts">
              ${visibleAlerts.map((item) => `
                <div class="mvp-notice ${item.severity === 'priority' ? 'error' : ''}">
                  <strong>${escapeHtml(item.headline)}</strong><br/>${escapeHtml(item.description)}
                </div>
              `).join('')}
            </div>
          ` : ''}
        </div>
      `;
    }

    function renderCockpit(body) {
      const summary = body.portfolio_summary;
      const risks = body.risk_register || [];
      kpis.innerHTML = `
        <div class="mvp-kpi mvp-kpi-featured"><div class="uplabel">Total AUM</div><div class="value">${formatCompactCurrency(summary.total_aum_usd)}</div><div class="meta">Live portfolio snapshot</div></div>
        <div class="mvp-kpi"><div class="uplabel">1-Day VaR (95%)</div><div class="value">${formatCurrency(body.var_result.var_1d_95)}</div><div class="meta">${formatPct(body.var_result.model_coverage_pct, 0)} modeled coverage</div></div>
        <div class="mvp-kpi"><div class="uplabel">Active Risks</div><div class="value">${formatNumber(risks.length)}</div><div class="meta">${formatNumber(risks.filter((item) => item.severity === 'priority').length)} priority · ${formatNumber(risks.filter((item) => item.severity === 'elevated').length)} elevated</div></div>
        <div class="mvp-kpi"><div class="uplabel">Liquidity (T+1)</div><div class="value">${formatPct(summary.liquidity_score_pct, 1)}</div><div class="meta">Current portfolio estimate</div></div>
      `;
      renderComposition(body);
      renderVar(body);
      renderRegister(body);
      renderOverlay();
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
      varStats.innerHTML = '';
      contributions.innerHTML = '<div class="mvp-empty">Loading VaR contributors...</div>';
      register.innerHTML = '<tr><td colspan="4" class="mvp-empty">Loading risk register...</td></tr>';
      overlaySummary.innerHTML = '<div class="mvp-empty">Loading overlay summary...</div>';
      overlayFactors.innerHTML = '';
      overlayStress.innerHTML = '';
      if (overlayAlertTop) overlayAlertTop.innerHTML = '';
      if (overlayRegime) overlayRegime.innerHTML = '';
    }

    async function loadCockpit() {
      renderCockpitLoading();
      try {
        const [cockpitResponse, triangulationResponse, stressResponse, regimeResponse] = await Promise.all([
          api('/cockpit'),
          api('/overlay/aum-triangulation'),
          api('/overlay/stress'),
          api('/overlay/regime'),
        ]);
        cockpitBody = cockpitResponse;
        overlayTriangulation = triangulationResponse;
        overlayStressBody = stressResponse;
        overlayRegimeBody = regimeResponse;
        renderCockpit(cockpitBody);
        setStatus(status, 'Updated just now.', 'success');
      } catch (error) {
        cockpitBody = null;
        overlayTriangulation = null;
        overlayStressBody = null;
        overlayRegimeBody = null;
        kpis.innerHTML = '';
        composition.innerHTML = '';
        varSummary.innerHTML = '';
        varStats.innerHTML = '';
        contributions.innerHTML = '';
        register.innerHTML = '<tr><td colspan="4" class="mvp-empty">No cockpit data available.</td></tr>';
        if (overlayAlertTop) overlayAlertTop.innerHTML = '';
        overlaySummary.innerHTML = '';
        overlayFactors.innerHTML = '';
        overlayStress.innerHTML = '';
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

    if (varToggles) {
      varToggles.addEventListener('click', (event) => {
        const button = event.target.closest('button[data-metric]');
        if (!button || !cockpitBody) return;
        activeVarMetric = button.dataset.metric || 'var_1d_95';
        withTransientUpdate([varSummary, varStats, contributions], () => {
          setActiveToggle(varToggles, 'metric', activeVarMetric);
          renderVar(cockpitBody);
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
    document.getElementById('refresh-overlay').addEventListener('click', async () => {
      try {
        await api('/overlay/run', { method: 'POST' });
        await loadCockpit();
      } catch (error) {
        setStatus(status, error.message, 'error');
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

    await loadCockpit();
  }

  async function initOverlay() {
    const user = await requireSession('overlay.html', ['Workspace', 'Overlay']);
    if (!user) return;

    const status = document.getElementById('overlay-status');
    const kpis = document.getElementById('overlay-kpis');
    const regimePanel = document.getElementById('overlay-regime-panel');
    const triangulationPanel = document.getElementById('overlay-triangulation-panel');
    const factorsPanel = document.getElementById('overlay-factors-panel');
    const stressPanel = document.getElementById('overlay-stress-panel');
    let refreshTimer = null;

    function renderOverlayPage({ factors, regime, triangulation, stress }) {
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
        setStatus(status, 'Overlay data refreshed.', 'success');
      } catch (error) {
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
    const list = document.getElementById('briefings-list');
    const toggleDrafts = document.getElementById('toggle-drafts');
    let showDrafts = false;

    async function loadBriefings() {
      try {
        const response = await api('/briefings');
        const items = (response.items || []).sort((left, right) => {
          if (left.status === right.status) return right.version - left.version;
          return left.status === 'published' ? -1 : 1;
        });
        const visibleItems = showDrafts ? items : items.filter((item) => item.status === 'published');
        if (toggleDrafts) {
          toggleDrafts.textContent = showDrafts ? 'Hide drafts' : 'Show drafts';
        }
        list.innerHTML = visibleItems.length
          ? visibleItems
              .map(
                (item) => `
                  <a class="mvp-card pad" href="briefing.html?id=${encodeURIComponent(item.id)}" style="display:block;color:inherit">
                    <div class="mvp-metadata">
                      <span class="mvp-pill ${item.status === 'published' ? 'good' : 'elevated'}">${escapeHtml(item.status)}</span>
                      <span>${escapeHtml(formatWeekLabel(item.week_label))}</span>
                      <span>v${escapeHtml(item.version)}</span>
                    </div>
                    <h3 style="font-family:'Fraunces',serif;margin:12px 0 6px">${escapeHtml(item.output.headline || 'Weekly briefing')}</h3>
                    <p style="margin:0;color:var(--ink-soft);font-size:12px">${escapeHtml(truncateText(item.output.executive_summary || briefingSummary(item.output), 120))}</p>
                  </a>
                `
              )
              .join('')
          : `<div class="mvp-empty mvp-card">${showDrafts ? 'No briefings yet. Generate the first one from this page.' : 'No published briefings yet. Show drafts or generate a new briefing.'}</div>`;
        setStatus(status, `${visibleItems.length} briefings loaded.`, 'success');
      } catch (error) {
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
        const briefing = await api('/briefings/generate', { method: 'POST' });
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
        body.innerHTML = `
          <section class="mvp-card pad">
            <div class="uplabel">Executive summary</div>
            <p style="margin:10px 0 0;line-height:1.6">${escapeHtml(output.executive_summary || '')}</p>
          </section>
          <section class="mvp-card pad">
            <div class="uplabel">Market context</div>
            <p style="margin:10px 0 0;line-height:1.6">${escapeHtml(output.market_context || '')}</p>
          </section>
          <section class="mvp-card pad">
            <div class="uplabel">Portfolio risks</div>
            <div class="mvp-list" style="margin-top:12px">
              ${(output.portfolio_risks || [])
                .map(
                  (item) => `
                    <div class="mvp-item">
                      <div>
                        <div class="mvp-item-title">${escapeHtml(item.risk_area)}</div>
                        <div class="mvp-item-subtle">${escapeHtml(item.finding)}</div>
                        <div class="mvp-item-subtle" style="margin-top:4px">${escapeHtml(item.implication || '')}</div>
                      </div>
                      <span class="mvp-pill ${severityClass(item.severity)}">${escapeHtml(item.severity)}</span>
                    </div>
                  `
                )
                .join('')}
            </div>
          </section>
          <section class="mvp-card pad">
            <div class="uplabel">Recommendations</div>
            <ul style="margin:12px 0 0;padding-left:18px;line-height:1.8">
              ${(output.recommendations || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}
            </ul>
          </section>
        `;
        setStatus(status, `Loaded ${formatWeekLabel(briefing.week_label)}.`, 'success');
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
    const deleteButton = document.getElementById('delete-position');
    const submitButton = form.querySelector('button[type="submit"]');
    let selected = null;
    let mutationBusy = false;
    const factorSourceOptions = ['manual', 'extracted', 'inferred'];

    function syncMutationButtons() {
      setEnabled(submitButton, !mutationBusy);
      setEnabled(deleteButton, !mutationBusy && Boolean(selected));
    }

    function setForm(position) {
      selected = position;
      formTitle.textContent = position ? `Edit ${position.ticker}` : 'Add position';
      document.getElementById('form-ticker').value = position?.ticker || '';
      document.getElementById('form-ticker').disabled = Boolean(position);
      document.getElementById('form-name').value = position?.name || '';
      document.getElementById('form-quantity').value = position?.quantity ?? '';
      document.getElementById('form-market-value').value = position?.market_value_usd ?? '';
      document.getElementById('form-asset-class').value = position?.asset_class || 'public_equity';
      document.getElementById('form-region').value = position?.geo_region || '';
      document.getElementById('form-sector').value = position?.sector || '';
      document.getElementById('form-segment').value = position?.market_segment || '';
      document.getElementById('form-custodian').value = position?.custodian || '';
      document.getElementById('form-factor-asset-class').value = position?.factor_asset_class || '';
      document.getElementById('form-factor-sector').value = position?.factor_sector || '';
      document.getElementById('form-factor-subsector').value = position?.factor_subsector || '';
      document.getElementById('form-factor-market-segment').value = position?.factor_market_segment || '';
      document.getElementById('form-factor-country').value = position?.factor_country || '';
      document.getElementById('form-factor-region').value = position?.factor_region || '';
      document.getElementById('form-factor-tag-source').value = position?.factor_tag_source || '';
      document.getElementById('form-factor-tag-confidence').value = position?.factor_tag_confidence ?? '';
      document.getElementById('form-notes').value = position?.notes || '';
      syncMutationButtons();
    }

    function factorSourceSelect(item) {
      return `
        <select data-inline-field="factor_tag_source" data-id="${escapeHtml(item.id)}" class="mvp-inline-input">
          <option value="">Unset</option>
          ${factorSourceOptions
            .map((option) => `<option value="${option}" ${item.factor_tag_source === option ? 'selected' : ''}>${option}</option>`)
            .join('')}
        </select>
      `;
    }

    async function patchInlineFactor(itemId, field, value) {
      try {
        const body = {
          [field]: value === '' ? null : field === 'factor_tag_confidence' ? Number(value) : value,
        };
        if (field !== 'factor_tag_source') {
          body.factor_tag_source = 'manual';
          body.factor_tag_confidence = 1.0;
        }
        const response = await api(`/portfolio/positions/${itemId}`, {
          method: 'PATCH',
          body,
        });
        await loadPositions(response.position_id);
        setStatus(status, 'Factor tags updated.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
        await loadPositions(selected?.id || null);
      }
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
                <td><input class="mvp-inline-input" data-inline-field="factor_asset_class" data-id="${escapeHtml(item.id)}" value="${escapeHtml(item.factor_asset_class || '')}"/></td>
                <td><input class="mvp-inline-input" data-inline-field="factor_sector" data-id="${escapeHtml(item.id)}" value="${escapeHtml(item.factor_sector || '')}"/></td>
                <td><input class="mvp-inline-input" data-inline-field="factor_subsector" data-id="${escapeHtml(item.id)}" value="${escapeHtml(item.factor_subsector || '')}"/></td>
                <td><input class="mvp-inline-input" data-inline-field="factor_market_segment" data-id="${escapeHtml(item.id)}" value="${escapeHtml(item.factor_market_segment || '')}"/></td>
                <td><input class="mvp-inline-input" data-inline-field="factor_country" data-id="${escapeHtml(item.id)}" value="${escapeHtml(item.factor_country || '')}"/></td>
                <td><input class="mvp-inline-input" data-inline-field="factor_region" data-id="${escapeHtml(item.id)}" value="${escapeHtml(item.factor_region || '')}"/></td>
                <td>${factorSourceSelect(item)}</td>
                <td><span class="mvp-inline-badge">${item.factor_tag_confidence != null ? formatNumber(item.factor_tag_confidence, 2) : 'n/a'}</span></td>
              </tr>
            `
          )
          .join('');

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

        tableBody.querySelectorAll('[data-inline-field]').forEach((input) => {
          input.addEventListener('click', (event) => event.stopPropagation());
          input.addEventListener('change', async (event) => {
            event.stopPropagation();
            const field = input.dataset.inlineField || '';
            const itemId = input.dataset.id || '';
            if (!field || !itemId) return;
            input.disabled = true;
            await patchInlineFactor(itemId, field, input.value.trim());
          });
        });

        setStatus(status, `Loaded ${response.total} positions.`, 'success');
      } catch (error) {
        tableBody.innerHTML = '<tr><td colspan="10" class="mvp-empty">Unable to load positions.</td></tr>';
        setStatus(status, error.message, 'error');
      }
    }

    document.getElementById('new-position').addEventListener('click', () => {
      tableBody.querySelectorAll('tr').forEach((node) => node.classList.remove('is-selected'));
      setForm(null);
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      mutationBusy = true;
      syncMutationButtons();
      const basePayload = {
        name: document.getElementById('form-name').value.trim() || null,
        quantity: Number(document.getElementById('form-quantity').value || 0),
        market_value_usd: Number(document.getElementById('form-market-value').value || 0),
        asset_class: document.getElementById('form-asset-class').value,
        geo_region: document.getElementById('form-region').value.trim() || null,
        sector: document.getElementById('form-sector').value.trim() || null,
        market_segment: document.getElementById('form-segment').value.trim() || null,
        factor_asset_class: document.getElementById('form-factor-asset-class').value.trim() || null,
        factor_sector: document.getElementById('form-factor-sector').value.trim() || null,
        factor_subsector: document.getElementById('form-factor-subsector').value.trim() || null,
        factor_market_segment: document.getElementById('form-factor-market-segment').value.trim() || null,
        factor_country: document.getElementById('form-factor-country').value.trim() || null,
        factor_region: document.getElementById('form-factor-region').value.trim() || null,
        factor_tag_source: document.getElementById('form-factor-tag-source').value || null,
        factor_tag_confidence: document.getElementById('form-factor-tag-confidence').value === ''
          ? null
          : Number(document.getElementById('form-factor-tag-confidence').value),
        custodian: document.getElementById('form-custodian').value.trim() || null,
        notes: document.getElementById('form-notes').value.trim() || null,
      };

      try {
        let response;
        if (selected) {
          response = await api(`/portfolio/positions/${selected.id}`, { method: 'PATCH', body: basePayload });
        } else {
          response = await api('/portfolio/positions', {
            method: 'POST',
            body: {
              ...basePayload,
              ticker: document.getElementById('form-ticker').value.trim(),
              position_currency: 'USD',
            },
          });
        }
        await loadPositions(response.position_id);
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

    const status = document.getElementById('documents-status');
    const folders = document.getElementById('document-folders');
    const list = document.getElementById('documents-list');
    const preview = document.getElementById('document-preview');
    const tagInput = document.getElementById('document-tag-input');
    const parseButton = document.getElementById('parse-document');
    const saveReviewButton = document.getElementById('save-document-review');
    let selectedId = '';
    let currentReview = null;
    let currentDocuments = [];
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
                            <div class="mvp-field"><label>Quantity</label><input data-position-index="${index}" data-position-field="quantity" value="${escapeHtml(position.quantity ?? '')}"/></div>
                            <div class="mvp-field"><label>Market value USD</label><input data-position-index="${index}" data-position-field="market_value_usd" value="${escapeHtml(position.market_value_usd ?? '')}"/></div>
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
        currentReview = null;
        preview.innerHTML = '<div class="mvp-empty">Select a document to inspect extraction results.</div>';
        return;
      }
      const extraction = documentRecord.extraction_result_id ? await loadExtraction(documentRecord.id) : null;
      const review = documentRecord.extraction_result_id ? await loadReview(documentRecord.id) : null;
      currentReview = review;
      tagInput.value = documentRecord.tag || '';
      preview.innerHTML = `
        <div class="mvp-card pad">
          <div class="mvp-item">
            <div>
              <div class="mvp-item-title">${escapeHtml(documentRecord.filename)}</div>
              <div class="mvp-item-subtle">${escapeHtml(documentRecord.folder)} · ${escapeHtml(documentRecord.file_type)} · ${formatNumber(documentRecord.file_size_bytes, 0)} bytes</div>
            </div>
            <span class="mvp-pill ${documentRecord.extraction_status === 'done' ? 'good' : 'elevated'}">${escapeHtml(documentRecord.extraction_status)}</span>
          </div>
          <div class="mvp-metadata" style="margin-top:12px">
            <span>Malware scan: ${escapeHtml(documentRecord.malware_scan_status)}</span>
            <span>Tag: ${escapeHtml(documentRecord.tag || 'none')}</span>
          </div>
        </div>
        ${renderParseProgress(documentRecord, extraction, review)}
        <div class="mvp-card pad">
          <div class="uplabel">Extraction preview</div>
          ${
            extraction
              ? `
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
              : '<div class="mvp-empty">No extraction yet. Parse the document to inspect candidate holdings.</div>'
          }
        </div>
        ${renderReviewEditor(review)}
      `;
    }

    async function loadDocuments(options = {}) {
      const preserveStatus = Boolean(options.preserveStatus);
      try {
        const response = await api('/documents');
        const items = response.items || [];
        currentDocuments = items;
        const selected =
          items.find((item) => item.id === selectedId) ||
          items[0] ||
          null;
        selectedId = selected?.id || '';

        folders.innerHTML = Object.entries(response.folder_counts || {})
          .map(
            ([name, count]) => `
              <button type="button" class="${selected?.folder === name ? 'is-selected' : ''}">
                <div class="mvp-item-title">${escapeHtml(name)}</div>
                <div class="mvp-item-subtle">${formatNumber(count, 0)} files</div>
              </button>
            `
          )
          .join('');

        list.innerHTML = items.length
          ? items
              .map(
                (item) => `
                  <button type="button" data-id="${escapeHtml(item.id)}" class="${item.id === selectedId ? 'is-selected' : ''}">
                    <div class="mvp-item-title">${escapeHtml(item.filename)}</div>
                    <div class="mvp-item-subtle">${escapeHtml(item.folder)} · ${escapeHtml(item.file_type)} · ${escapeHtml(item.extraction_status)}</div>
                  </button>
                `
              )
              .join('')
          : '<div class="mvp-empty">No documents uploaded yet.</div>';

        list.querySelectorAll('button[data-id]').forEach((button) => {
          button.addEventListener('click', () => {
            selectedId = button.dataset.id || '';
            loadDocuments();
          });
        });

        await renderPreview(selected);
        if (!preserveStatus) {
          setStatus(status, `${items.length} documents loaded.`, 'success');
        }
      } catch (error) {
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
        const documentRecord = await api('/documents/upload', { method: 'POST', formData });
        selectedId = documentRecord.id;
        await loadDocuments();
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    parseButton.addEventListener('click', async () => {
      if (!selectedId) return;
      setEnabled(parseButton, false);
      try {
        startParseProgress(selectedId);
        const selectedDocument = currentDocuments.find((item) => item.id === selectedId);
        if (selectedDocument) await renderPreview(selectedDocument);
        const response = await api(`/documents/${selectedId}/parse`, { method: 'POST' });
        stopParseProgress();
        setStatus(status, response.detail, 'success');
        await loadDocuments({ preserveStatus: true });
      } catch (error) {
        stopParseProgress();
        setStatus(status, error.message, 'error');
      } finally {
        setEnabled(parseButton, true);
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
        positions[index][field] = input.value.trim();
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
        const response = await api(`/documents/${selectedId}/review`, {
          method: 'PATCH',
          body: { positions, treasury, resolved_fields: resolvedFields },
        });
        setStatus(status, `Review saved. ${response.needs_review_count} items still require attention.`, 'success');
        await loadDocuments({ preserveStatus: true });
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    document.getElementById('approve-document').addEventListener('click', async () => {
      if (!selectedId) return;
      try {
        await api(`/documents/${selectedId}/approve`, { method: 'POST' });
        setStatus(status, 'Approved into portfolio — snapshot created.', 'success');
        await loadDocuments({ preserveStatus: true });
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    document.getElementById('save-document-tag').addEventListener('click', async () => {
      if (!selectedId) return;
      try {
        const response = await api(`/documents/${selectedId}/tag`, {
          method: 'POST',
          body: { tag: tagInput.value.trim() || 'reviewed' },
        });
        setStatus(status, `Tag saved: ${response.tag || 'updated'}.`, 'success');
        await loadDocuments({ preserveStatus: true });
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    document.getElementById('delete-document').addEventListener('click', async () => {
      if (!selectedId) return;
      try {
        const response = await api(`/documents/${selectedId}`, { method: 'DELETE' });
        selectedId = '';
        setStatus(status, response.detail, 'success');
        await loadDocuments({ preserveStatus: true });
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    await loadDocuments();
  }

  const initializers = {
    index: initIndex,
    login: initLogin,
    onboarding: initOnboarding,
    cockpit: initCockpit,
    briefings: initBriefings,
    briefing: initBriefingDetail,
    table: initTable,
    documents: initDocuments,
    overlay: initOverlay,
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
      });
    }
  });

  window.CRBMvp = {
    api,
    formatCurrency,
    formatCompactCurrency,
    formatNumber,
    formatPct,
    setStatus,
    escapeHtml,
  };
})();
