(function() {
  'use strict';

  const fmt = {
    money(value, digits = 1) {
      const n = Number(value || 0);
      const sign = n < 0 ? '-' : '';
      const abs = Math.abs(n);
      if (abs >= 1_000_000_000) return sign + '$' + (abs / 1_000_000_000).toFixed(digits) + 'B';
      if (abs >= 1_000_000) return sign + '$' + (abs / 1_000_000).toFixed(digits) + 'M';
      return sign + '$' + abs.toLocaleString(undefined, { maximumFractionDigits: 0 });
    },
    num(value, digits = 0) {
      return Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: digits });
    },
    pct(value, digits = 1) {
      return Number(value || 0).toFixed(digits) + '%';
    },
    date(value) {
      if (!value) return '';
      return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    },
    signedMoney(value) {
      const n = Number(value || 0);
      return (n >= 0 ? '+' : '-') + fmt.money(Math.abs(n), 1);
    },
  };

  const colors = ['#1B2B5E', '#72594c', '#C9A449', '#006972', '#d3c3bc', '#4a6fa1', '#8d7c76'];

  function toast(message, type) {
    if (window.Shell && Shell.toast) Shell.toast(message, type);
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  }

  function normalizeList(payload) {
    if (Array.isArray(payload)) return payload;
    return payload && Array.isArray(payload.items) ? payload.items : [];
  }

  function severityClass(value) {
    const v = String(value || '').toLowerCase();
    if (v.startsWith('pri')) return 'pri';
    if (v.startsWith('ele')) return 'ele';
    if (v.startsWith('wat')) return 'wat';
    return 'mute';
  }

  function outputText(output, key) {
    if (!output || typeof output !== 'object') return '';
    const value = output[key];
    if (Array.isArray(value)) return value.map(item => typeof item === 'string' ? item : item.headline || item.description || '').filter(Boolean).join(' ');
    if (value && typeof value === 'object') return value.summary || value.headline || value.description || '';
    return value || '';
  }

  function briefingSummary(briefing) {
    return outputText(briefing.output, 'executive_summary') ||
      outputText(briefing.output, 'summary') ||
      outputText(briefing.output, 'recommended_actions') ||
      'Generated briefing is ready for review.';
  }

  function briefingHtml(briefing) {
    if (briefing.html_body) return briefing.html_body;
    const output = briefing.output || {};
    const summary = briefingSummary(briefing);
    const risks = Array.isArray(output.priority_risks) ? output.priority_risks : [];
    const actions = Array.isArray(output.recommended_actions) ? output.recommended_actions : [];
    return `
      <div class="briefing-section">
        <div class="section-label">Executive Summary</div>
        <p>${escapeHtml(summary)}</p>
      </div>
      ${risks.length ? `<div class="briefing-section"><div class="section-label">Priority Risks</div>${risks.map(r => `
        <div class="risk-item">
          <div class="ri-sev"><span class="sev-dot ${severityClass(r.severity)}"></span></div>
          <div>
            <div class="ri-headline">${escapeHtml(r.headline || r.title || 'Risk item')}<span class="pill ${severityClass(r.severity)}">${escapeHtml(r.severity || 'Risk')}</span></div>
            <div class="ri-body">${escapeHtml(r.description || r.reasoning || '')}</div>
          </div>
        </div>`).join('')}</div>` : ''}
      ${actions.length ? `<div class="briefing-section"><div class="section-label">Recommended Actions</div><ul class="action-list">${actions.map(a => `
        <li><span class="ms sm">arrow_forward</span><span>${escapeHtml(typeof a === 'string' ? a : a.text || a.action || a.description || '')}</span></li>`).join('')}</ul></div>` : ''}
    `;
  }

  function renderDonut(svg, legend, buckets) {
    if (!svg || !buckets.length) return;
    const total = buckets.reduce((sum, item) => sum + Number(item.market_value_usd || item.value || 0), 0) || 1;
    const r = 46;
    const c = 2 * Math.PI * r;
    let offset = 0;
    svg.innerHTML = buckets.map((item, i) => {
      const value = Number(item.market_value_usd || item.value || 0);
      const len = c * value / total;
      const html = `<circle cx="60" cy="60" r="${r}" fill="none" stroke="${colors[i % colors.length]}" stroke-width="18" stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-offset}" transform="rotate(-90 60 60)"></circle>`;
      offset += len;
      return html;
    }).join('') + '<circle cx="60" cy="60" r="28" fill="#fffdfb"></circle>';
    if (legend) {
      legend.innerHTML = buckets.map((item, i) => {
        const value = Number(item.market_value_usd || item.value || 0);
        return `<div class="legend-row"><span class="legend-dot" style="background:${colors[i % colors.length]}"></span><span class="legend-label">${escapeHtml(item.label || item.name || 'Other')}</span><span class="legend-pct">${fmt.pct((value / total) * 100, 0)}</span><span class="legend-val">${fmt.money(value)}</span></div>`;
      }).join('');
    }
  }

  function renderCashflow(svg, buckets, width = 760) {
    if (!svg || !buckets.length) return;
    const h = 160;
    const max = Math.max(1, ...buckets.flatMap(b => [
      Math.abs(b.inflows || b.inflow_usd || 0),
      Math.abs(b.outflows || b.outflow_usd || 0),
      Math.abs(b.cumulative || b.cumulative_net_usd || b.net || 0),
    ]));
    const step = (width - 70) / buckets.length;
    const base = 130;
    const bars = buckets.map((b, i) => {
      const x = 44 + i * step;
      const inflow = Number(b.inflows || b.inflow_usd || 0);
      const outflow = Number(b.outflows || b.outflow_usd || 0);
      const inH = Math.max(2, Math.abs(inflow) / max * 110);
      const outH = Math.max(2, Math.abs(outflow) / max * 110);
      const label = String(b.month || '').slice(5) || String(b.month || '').slice(0, 3);
      return `<rect x="${x}" y="${base - inH}" width="12" height="${inH}" rx="2" fill="#3F7A4F"></rect>
        <rect x="${x + 14}" y="${base - outH}" width="12" height="${outH}" rx="2" fill="#B91C1C" opacity=".72"></rect>
        <text x="${x + 13}" y="148" text-anchor="middle" font-size="7" fill="#81756f" font-family="JetBrains Mono">${escapeHtml(label)}</text>`;
    }).join('');
    const points = buckets.map((b, i) => {
      const x = 57 + i * step;
      const y = base - ((Number(b.cumulative || b.cumulative_net_usd || b.net || 0) / max) * 55);
      return `${x},${Math.max(12, Math.min(134, y))}`;
    }).join(' ');
    svg.innerHTML = '<line x1="40" y1="130" x2="' + (width - 5) + '" y2="130" stroke="var(--rule)" stroke-width=".5"/>' +
      bars + `<polyline points="${points}" fill="none" stroke="#1B2B5E" stroke-width="1.5" stroke-linejoin="round"></polyline>`;
  }

  function slugify(value) {
    return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'section';
  }

  function ensureFieldError(input) {
    const field = input.closest('.field');
    if (!field) return null;
    let node = field.querySelector('.field-error');
    if (!node) {
      node = document.createElement('div');
      node.className = 'field-error';
      node.style.cssText = 'font-size:11px;color:var(--pri-fg);margin-top:6px;';
      field.appendChild(node);
    }
    return node;
  }

  function clearFieldErrors(scope) {
    scope.querySelectorAll('.field-error').forEach(node => { node.textContent = ''; });
  }

  function applyValidationErrors(scope, detail) {
    clearFieldErrors(scope);
    if (!Array.isArray(detail)) return false;
    let applied = false;
    detail.forEach(item => {
      const fieldName = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : '';
      const input = scope.querySelector(`[name="${fieldName}"]`) || scope.querySelector(`[data-name="${fieldName}"]`);
      if (!input) return;
      const node = ensureFieldError(input);
      if (node) {
        node.textContent = item.msg || 'Invalid value';
        applied = true;
      }
    });
    return applied;
  }

  function setButtonBusy(button, busyText, busy) {
    if (!button) return;
    if (!button.dataset.label) button.dataset.label = button.innerHTML;
    button.disabled = !!busy;
    button.innerHTML = busy
      ? `<span class="ms sm">progress_activity</span> ${busyText}`
      : button.dataset.label;
  }

  function showPanelGroup(tabs, panels, id) {
    tabs.forEach(tab => tab.classList.toggle('on', tab.dataset.tab === id));
    panels.forEach(panel => panel.classList.toggle('visible', panel.dataset.panel === id));
  }

  function byPath(pathname) {
    if (pathname === '/') return '/index.html';
    return pathname.includes('.') ? pathname : `${pathname}.html`;
  }

  async function initLogin() {
    const authTabs = document.querySelectorAll('.auth-tabs button');
    const authPanels = document.querySelectorAll('[data-panel]');
    const signInPanel = document.querySelector('[data-panel="sign-in"]');
    const registerPanel = document.querySelector('[data-panel="register"]');
    const forgotPanel = document.querySelector('[data-panel="forgot"]');
    const signInEmail = signInPanel?.querySelector('input[type="email"]');
    const signInPassword = signInPanel?.querySelector('input[type="password"]');
    const signInRemember = signInPanel?.querySelector('input[type="checkbox"]');
    const signInButton = signInPanel?.querySelector('.btn.primary');
    const registerInputs = registerPanel?.querySelectorAll('input') || [];
    const registerEmail = registerInputs[2];
    const registerPassword = registerInputs[3];
    const registerButton = registerPanel?.querySelector('.btn.primary');
    const forgotEmail = forgotPanel?.querySelector('input[type="email"]');
    const forgotButton = forgotPanel?.querySelector('.btn.primary');

    [signInEmail, registerEmail, forgotEmail].forEach(input => {
      if (input) input.name = 'email';
    });
    if (signInPassword) signInPassword.name = 'password';
    if (registerInputs[0]) registerInputs[0].name = 'display_name';
    if (registerInputs[1]) registerInputs[1].name = 'workspace_name';
    if (registerPassword) registerPassword.name = 'password';

    function syncEmail(source, target) {
      if (source && target && source.value.trim() && !target.value.trim()) target.value = source.value.trim();
    }

    authTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        if (tab.dataset.tab === 'sign-in') syncEmail(registerEmail, signInEmail);
        if (tab.dataset.tab === 'register') syncEmail(signInEmail, registerEmail);
        showPanelGroup(authTabs, authPanels, tab.dataset.tab);
      });
    });
    document.getElementById('forgot-link')?.addEventListener('click', e => {
      e.preventDefault();
      syncEmail(signInEmail, forgotEmail);
      authTabs.forEach(t => t.classList.remove('on'));
      authPanels.forEach(p => p.classList.toggle('visible', p.dataset.panel === 'forgot'));
    });
    document.getElementById('back-to-signin')?.addEventListener('click', () => {
      syncEmail(forgotEmail, signInEmail);
      showPanelGroup(authTabs, authPanels, 'sign-in');
    });

    try {
      await API.get('/auth/me', { redirectOnUnauthorized: false });
      API.markLoggedIn();
      window.location.href = '/index.html';
      return;
    } catch (_error) {
      API.clearToken();
    }

    function notice(container, message, type) {
      let node = container.querySelector('.auth-notice');
      if (!node) {
        node = document.createElement('div');
        node.className = 'auth-notice';
        node.style.cssText = 'font-size:12px;font-weight:600;line-height:1.4;';
        container.appendChild(node);
      }
      node.textContent = message;
      node.style.color = type === 'ok' ? 'var(--good-fg)' : 'var(--pri-fg)';
    }

    const strength = document.createElement('div');
    strength.className = 'pw-strength';
    strength.innerHTML = '<div class="fill"></div>';
    strength.style.cssText = 'height:6px;border-radius:999px;background:var(--paper-3);overflow:hidden;margin-top:8px;';
    strength.querySelector('.fill').style.cssText = 'height:100%;width:0%;background:var(--pri-fg);transition:width 160ms ease, background 160ms ease;';
    registerPassword?.closest('.field')?.appendChild(strength);

    function evaluatePassword(value) {
      const lengthGood = value.length >= 12;
      const variety = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter(rx => rx.test(value)).length;
      const score = (!value ? 0 : value.length >= 8 ? 1 : 0) + (value.length >= 12 ? 1 : 0) + (variety >= 3 ? 1 : 0) + (variety >= 4 ? 1 : 0);
      if (score <= 1) return { level: 'weak', width: 25, ok: false };
      if (score === 2) return { level: 'fair', width: 50, ok: false };
      if (score === 3) return { level: 'good', width: 75, ok: false };
      return { level: 'strong', width: 100, ok: lengthGood && variety >= 3 };
    }

    function updateStrength() {
      const result = evaluatePassword(registerPassword?.value || '');
      const fill = strength.querySelector('.fill');
      fill.style.width = `${result.width}%`;
      fill.style.background = ({
        weak: 'var(--pri-fg)',
        fair: 'var(--ele-fg)',
        good: 'var(--wat-fg)',
        strong: 'var(--good-fg)',
      })[result.level];
      if (registerButton) registerButton.disabled = !result.ok;
    }

    registerPassword?.addEventListener('input', updateStrength);
    updateStrength();

    [signInPanel, registerPanel, forgotPanel].forEach(panel => {
      panel?.querySelectorAll('input').forEach(input => {
        input.addEventListener('keydown', event => {
          if (event.key !== 'Enter') return;
          event.preventDefault();
          panel.querySelector('.btn.primary')?.click();
        });
      });
    });

    signInButton?.addEventListener('click', async () => {
      clearFieldErrors(signInPanel);
      setButtonBusy(signInButton, 'Signing in...', true);
      try {
        const data = await API.post('/auth/login', { email: signInEmail?.value.trim(), password: signInPassword?.value || '' });
        if (data && data.access_token) API.setToken(data.access_token, !!signInRemember?.checked);
        else API.markLoggedIn();
        window.location.href = '/index.html';
      } catch (error) {
        if (!applyValidationErrors(signInPanel, error?.data?.detail)) {
          notice(signInPanel, API.detail(error) || 'Invalid credentials');
        }
      } finally {
        setButtonBusy(signInButton, 'Signing in...', false);
      }
    });

    registerButton?.addEventListener('click', async () => {
      clearFieldErrors(registerPanel);
      setButtonBusy(registerButton, 'Creating workspace...', true);
      try {
        const data = await API.post('/auth/register', {
          display_name: registerInputs[0]?.value.trim(),
          workspace_name: registerInputs[1]?.value.trim(),
          email: registerEmail?.value.trim(),
          password: registerPassword?.value || '',
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
          reporting_currency: 'USD',
        });
        if (data && data.access_token) API.setToken(data.access_token);
        else API.markLoggedIn();
        window.location.href = '/onboarding.html';
      } catch (error) {
        if (!applyValidationErrors(registerPanel, error?.data?.detail)) {
          notice(registerPanel, API.detail(error));
        }
      } finally {
        setButtonBusy(registerButton, 'Creating workspace...', false);
      }
    });

    forgotButton?.addEventListener('click', async () => {
      clearFieldErrors(forgotPanel);
      setButtonBusy(forgotButton, 'Sending reset link...', true);
      try {
        const email = forgotEmail?.value.trim();
        await API.post('/auth/forgot-password', { email });
        forgotPanel.innerHTML = `<div style="padding:12px;border:1px solid var(--rule);border-radius:8px;background:var(--paper-2);display:flex;flex-direction:column;gap:12px">
          <div style="display:flex;align-items:center;gap:8px;color:var(--good-fg);font-weight:700"><span class="ms">check_circle</span> Check your inbox</div>
          <div style="font-size:13px;color:var(--ink-soft);line-height:1.5">We've sent a reset link to ${escapeHtml(email)}.</div>
          <a href="#" id="forgot-back-inline" style="color:var(--accent);font-weight:600;text-decoration:none">Back to sign in</a>
        </div>`;
        forgotPanel.querySelector('#forgot-back-inline')?.addEventListener('click', event => {
          event.preventDefault();
          syncEmail(forgotEmail, signInEmail);
          showPanelGroup(authTabs, authPanels, 'sign-in');
        });
      } catch (error) {
        if (!applyValidationErrors(forgotPanel, error?.data?.detail)) {
          notice(forgotPanel, API.detail(error));
        }
      } finally {
        setButtonBusy(forgotButton, 'Sending reset link...', false);
      }
    });
  }

  async function initDashboard() {
    const hour = new Date().getHours();
    const headline = document.querySelector('.page-head h1');
    if (headline) {
      headline.textContent = hour < 12 ? 'Good morning.' : hour < 17 ? 'Good afternoon.' : 'Good evening.';
    }
    if (!(await API.redirectIfUnauth())) return;
    document.querySelectorAll('.kpi-tile,.briefing-card,.events-card').forEach(el => el.classList.add('loading'));
    try {
      const [session, snapshot, varResult, liquidity, risk, briefings] = await Promise.all([
        API.get('/auth/me', { redirectOnUnauthorized: false }),
        API.get('/portfolio/snapshot'),
        API.get('/var'),
        API.get('/liquidity'),
        API.get('/risk/register'),
        API.get('/briefings?limit=1'),
      ]);
      const kpis = document.querySelectorAll('.kpi-tile');
      kpis[0].querySelector('.kpi-value').textContent = fmt.money(snapshot.total_aum_usd);
      kpis[0].querySelector('.kpi-sub').textContent = `${snapshot.position_count} positions`;
      if (typeof snapshot.weekly_pnl === 'number' || typeof snapshot.weekly_pnl_pct === 'number') {
        const weeklyPnl = Number(snapshot.weekly_pnl || 0);
        const weeklyPnlPct = Number(snapshot.weekly_pnl_pct || 0);
        kpis[1].querySelector('.kpi-value').textContent = fmt.signedMoney(weeklyPnl);
        kpis[1].querySelector('.kpi-delta').className = `kpi-delta ${weeklyPnl >= 0 ? 'pos' : 'neg'}`;
        kpis[1].querySelector('.kpi-delta').innerHTML = `<span class="ms sm">${weeklyPnl >= 0 ? 'trending_up' : 'trending_down'}</span> ${fmt.pct(Math.abs(weeklyPnlPct), 2)} this week`;
      } else {
        kpis[1].querySelector('.kpi-value').textContent = '$0.0M';
        kpis[1].querySelector('.kpi-delta').className = 'kpi-delta';
        kpis[1].querySelector('.kpi-delta').innerHTML = '<span class="ms sm">trending_flat</span> Live P&L pending';
      }
      kpis[2].querySelector('.kpi-value').textContent = fmt.money(varResult.var_1d_95);
      kpis[3].querySelector('.kpi-value').textContent = fmt.num(((liquidity.cash_on_hand_usd || 0) / Math.max(liquidity.scheduled_outflows_usd || 1, 1)) * 3, 1);
      const dateLine = document.querySelector('.page-head .sub');
      const workspaceName = session?.user?.workspace_name || session?.workspace_name || 'Workspace';
      if (dateLine) dateLine.textContent = `${fmt.date(new Date())} · ${workspaceName}`;

      const counts = { priority: 0, elevated: 0, watch: 0 };
      normalizeList(risk).forEach(item => { if (counts[item.severity] !== undefined) counts[item.severity] += 1; });
      const riskRow = document.querySelector('.risk-row');
      [['pri', 'priority'], ['ele', 'elevated'], ['wat', 'watch']].forEach(([cls, key]) => {
        const pill = riskRow.querySelector(`.pill.${cls}`);
        if (!pill) return;
        pill.innerHTML = `<span class="dot"></span>${counts[key]} ${key}`;
        pill.style.cursor = 'pointer';
        pill.addEventListener('click', () => { location.href = `cockpit.html?severity=${encodeURIComponent(key)}`; });
      });

      const latest = normalizeList(briefings)[0];
      if (latest) {
        document.querySelector('.briefing-card .pill').textContent = `${latest.scope || 'Full'} briefing`;
        document.querySelector('.briefing-card .bdate').textContent = `Generated ${fmt.date(latest.created_at)}`;
        document.querySelector('.briefing-card .summary-text').textContent = briefingSummary(latest);
        document.querySelector('.briefing-card a.btn.primary').href = `briefing.html?id=${latest.id}`;
        const ageDays = (Date.now() - new Date(latest.created_at).getTime()) / 86400000;
        document.querySelector('.stale-notice').style.display = ageDays > 6 ? '' : 'none';
      }

      const events = [
        { date: liquidity.next_call_due_date, description: 'Next capital call', amount: -Number(liquidity.next_call_amount_usd || 0) },
        { date: 'Next 90 days', description: 'Expected distributions', amount: Number(liquidity.expected_distributions_usd || 0) },
        { date: 'Next 90 days', description: 'Scheduled outflows', amount: -Number(liquidity.scheduled_outflows_usd || 0) },
      ].filter(e => e.amount);
      document.querySelector('.events-card tbody').innerHTML = events.length
        ? events.map(e => `<tr><td class="muted">${escapeHtml(e.date || '')}</td><td>${escapeHtml(e.description)}</td><td class="amount ${e.amount >= 0 ? 'pos' : 'neg'}">${fmt.signedMoney(e.amount)}</td></tr>`).join('')
        : '<tr><td colspan="3" class="muted" style="text-align:center;padding:20px">No upcoming events in the next 30 days.</td></tr>';
    } catch (error) {
      toast(API.detail(error), 'error');
    } finally {
      document.querySelectorAll('.loading').forEach(el => el.classList.remove('loading'));
    }
  }

  async function loadPortfolioSummary() {
    const [snapshot, summary, positions] = await Promise.all([
      API.get('/portfolio/snapshot'),
      API.get('/portfolio/summary'),
      API.get('/portfolio/positions'),
    ]);
    return { snapshot, summary, positions: normalizeList(positions) };
  }

  async function initCockpit() {
    if (!(await API.redirectIfUnauth())) return;
    const tbody = document.querySelector('.risk-table tbody');
    const riskCardHead = document.querySelector('.risk-card .card-head');
    const donutSvg = document.querySelector('.donut-svg');
    const legend = document.querySelector('.legend');
    const seg = document.getElementById('comp-seg');
    const filterSeverity = new URLSearchParams(location.search).get('severity');
    const filterRiskId = new URLSearchParams(location.search).get('risk_id');
    let dataCache = null;

    function ensureDrawer() {
      let backdrop = document.getElementById('risk-inline-backdrop');
      let drawer = document.getElementById('risk-inline-drawer');
      if (drawer && backdrop) return { drawer, backdrop };
      backdrop = document.createElement('div');
      backdrop.id = 'risk-inline-backdrop';
      backdrop.className = 'drawer-backdrop';
      drawer = document.createElement('div');
      drawer.id = 'risk-inline-drawer';
      drawer.className = 'drawer';
      drawer.innerHTML = `<header><h3>Risk detail</h3><button class="iconbtn"><span class="ms sm">close</span></button></header><div class="drawer-body"></div>`;
      document.body.appendChild(backdrop);
      document.body.appendChild(drawer);
      const close = () => { backdrop.classList.remove('open'); drawer.classList.remove('open'); };
      backdrop.addEventListener('click', close);
      drawer.querySelector('.iconbtn').addEventListener('click', close);
      return { drawer, backdrop };
    }

    function openRiskDrawer(item) {
      const { drawer, backdrop } = ensureDrawer();
      const body = drawer.querySelector('.drawer-body');
      const linked = Array.isArray(item.linked_positions) ? item.linked_positions : (item.ticker ? [item.ticker] : []);
      body.innerHTML = `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px"><span class="pill ${severityClass(item.severity)}">${escapeHtml(item.severity || 'risk')}</span></div>
        <div style="font-family:var(--font-serif);font-size:18px;font-weight:700;color:var(--ink);margin-bottom:8px">${escapeHtml(item.headline || item.description || 'Risk item')}</div>
        <div style="font-size:13px;color:var(--ink-soft);line-height:1.6;margin-bottom:14px">${escapeHtml(item.reasoning || item.rule || item.description || 'No additional reasoning provided.')}</div>
        <div class="uplabel" style="margin-bottom:8px">Linked positions</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px">${linked.length ? linked.map(ticker => `<button class="btn ghost risk-ticker" data-ticker="${escapeHtml(ticker)}" style="padding:4px 10px;font-size:11px">${escapeHtml(ticker)}</button>`).join('') : '<span class="muted">No linked positions</span>'}</div>
      `;
      body.querySelectorAll('.risk-ticker').forEach(button => button.addEventListener('click', () => {
        location.href = `table.html?ticker=${encodeURIComponent(button.dataset.ticker)}`;
      }));
      backdrop.classList.add('open');
      drawer.classList.add('open');
    }

    function renderVarChart(history) {
      const svg = document.querySelector('.chart-container svg');
      if (!svg || !Array.isArray(history) || !history.length) return;
      const width = 580;
      const height = 130;
      const left = 40;
      const right = 10;
      const top = 18;
      const bottom = 20;
      const values = history.map(item => Number(item.value || 0));
      const min = Math.min(...values);
      const max = Math.max(...values);
      const range = max - min || 1;
      const step = (width - left - right) / Math.max(history.length - 1, 1);
      const points = history.map((item, index) => {
        const x = left + index * step;
        const y = top + ((max - Number(item.value || 0)) / range) * (height - top - bottom);
        return { x, y, item };
      });
      const polyline = points.map(point => `${point.x},${point.y}`).join(' ');
      const fill = `${polyline} ${left + (history.length - 1) * step},${height - bottom} ${left},${height - bottom}`;
      svg.innerHTML = `
        <defs><linearGradient id="varFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1B2B5E" stop-opacity=".15"/><stop offset="100%" stop-color="#1B2B5E" stop-opacity="0"/></linearGradient></defs>
        <line x1="${left}" y1="${height - bottom}" x2="${width - right}" y2="${height - bottom}" stroke="var(--rule)" stroke-width=".5"/>
        <polygon points="${fill}" fill="url(#varFill)"></polygon>
        <polyline points="${polyline}" fill="none" stroke="#1B2B5E" stroke-width="1.5" stroke-linejoin="round"></polyline>
      `;
    }

    function renderStressTests(items) {
      const card = document.querySelector('.cockpit-bottom .card:last-child');
      if (!card) return;
      const list = Array.isArray(items) && items.length ? items : [];
      const summary = card.querySelector('div[style*="margin-top:14px"]');
      card.querySelectorAll('.stress-row').forEach(node => node.remove());
      if (!list.length) {
        summary.insertAdjacentHTML('beforebegin', '<div class="stress-row"><div class="muted">No stress scenarios configured.</div></div>');
        return;
      }
      summary.insertAdjacentHTML('beforebegin', list.map(item => {
        const lossPct = Math.abs(Number(item.loss_pct || 0));
        const color = lossPct > 5 ? 'var(--pri-fg)' : lossPct > 2 ? 'var(--ele-fg)' : 'var(--ink)';
        return `<div class="stress-row"><div><div class="stress-name">${escapeHtml(item.scenario)}</div></div><div class="stress-impact"><div class="stress-abs">${fmt.signedMoney(-(Math.abs(Number(item.loss_usd || 0))))}</div><div class="stress-pct" style="color:${color}">${fmt.pct(lossPct, 1)} of AUM</div></div></div>`;
      }).join(''));
    }

    function renderRisks(rows) {
      const filtered = rows.filter(item => {
        if (filterSeverity && item.severity !== filterSeverity) return false;
        if (filterRiskId && item.id && item.id !== filterRiskId) return false;
        return true;
      });
      const label = riskCardHead?.querySelector('.pill');
      if (label) label.textContent = `${filtered.length} risks`;
      tbody.innerHTML = filtered.length
        ? filtered.map(item => `<tr data-key="${escapeHtml(item.id || item.headline || item.rule || item.agent || '')}"><td><span class="sev-dot ${severityClass(item.severity)}"></span></td><td class="dim">${escapeHtml(item.kind || item.agent || 'Risk')}</td><td class="headline">${escapeHtml(item.headline || item.description || '')}</td><td class="reasoning">${escapeHtml(item.reasoning || item.rule || item.description || '')}</td></tr>`).join('')
        : '<tr><td colspan="4" class="muted" style="text-align:center;padding:24px">No active risks. Portfolio looks clean.</td></tr>';
      tbody.querySelectorAll('tr[data-key]').forEach((row, index) => {
        row.addEventListener('click', () => openRiskDrawer(filtered[index]));
      });
      if (filterSeverity && riskCardHead && !riskCardHead.querySelector('.risk-clear-filter')) {
        const chip = document.createElement('button');
        chip.className = 'btn ghost risk-clear-filter';
        chip.style.cssText = 'padding:4px 10px;font-size:11px';
        chip.textContent = `Clear ${filterSeverity} filter`;
        chip.addEventListener('click', () => {
          const url = new URL(location.href);
          url.searchParams.delete('severity');
          location.href = url.toString();
        });
        riskCardHead.appendChild(chip);
      }
    }

    async function loadComposition(view) {
      if (!view || view === 'asset') return dataCache?.portfolio_summary?.asset_class || [];
      const summary = await API.get('/portfolio/summary');
      return summary[view === 'geo' ? 'geo_region' : view] || [];
    }

    async function load() {
      dataCache = await API.get('/cockpit');
      const ps = dataCache.portfolio_summary || {};
      const kpis = document.querySelectorAll('.kpi-tile');
      kpis[0].querySelector('.kpi-value').textContent = fmt.money(ps.total_aum_usd);
      if (typeof ps.weekly_pnl === 'number') kpis[1].querySelector('.kpi-value').textContent = fmt.signedMoney(ps.weekly_pnl);
      else kpis[1].querySelector('.kpi-value').textContent = '$0.0M';
      kpis[2].querySelector('.kpi-value').textContent = fmt.money(dataCache.var_result?.var_1d_95);
      kpis[3].querySelector('.kpi-value').textContent = fmt.num(((ps.liquidity_summary?.cash_on_hand_usd || 0) / Math.max(ps.liquidity_summary?.scheduled_outflows_usd || 1, 1)) * 3, 1);
      renderDonut(donutSvg, legend, ps.asset_class || []);
      renderRisks(normalizeList(dataCache.risk_register));
      renderStressTests(dataCache.stress_tests);
      renderVarChart(dataCache.var_result?.history || []);
      const stats = document.querySelectorAll('.var-stat .vs-value');
      if (stats[0]) stats[0].textContent = fmt.money(dataCache.var_result?.var_1d_95);
      if (stats[1]) stats[1].textContent = fmt.money(dataCache.var_result?.var_1d_99);
      if (stats[2]) stats[2].textContent = fmt.pct(Math.abs(dataCache.var_result?.max_drawdown_1y || 0) * 100);
      if (stats[3]) stats[3].textContent = fmt.date(dataCache.var_result?.worst_scenario_date);
    }

    seg?.addEventListener('seg-change', async event => {
      donutSvg.innerHTML = '<text x="60" y="60" text-anchor="middle" font-size="10" fill="#81756f">Loading…</text>';
      try {
        renderDonut(donutSvg, legend, await loadComposition(event.detail.value));
      } catch (error) {
        toast(API.detail(error), 'error');
      }
    });

    document.querySelector('.page-head .btn')?.addEventListener('click', async () => {
      try {
        await load();
        toast('Cockpit refreshed', 'success');
      } catch (error) {
        toast(API.detail(error), 'error');
      }
    });

    try {
      await load();
      setTimeout(() => { load().catch(() => {}); }, 5 * 60 * 1000);
    } catch (error) {
      toast(API.detail(error), 'error');
    }
  }

  async function initAssets() {
    if (!(await API.redirectIfUnauth())) return;
    const tableCard = document.querySelector('.table-card');
    const tableHead = tableCard?.querySelector('.table-head');
    const tbody = tableCard?.querySelector('tbody');
    const seg = document.getElementById('alloc-seg');
    let allPositions = [];
    let groupedSummary = [];

    if (tableHead && !tableHead.querySelector('.search-input')) {
      const controls = document.createElement('div');
      controls.style.cssText = 'display:flex;gap:8px;align-items:center;margin-left:auto';
      controls.innerHTML = '<input class="search-input" placeholder="Search by name or ticker..." style="padding:7px 10px;border:1px solid var(--rule);border-radius:4px;font:12px var(--font-sans);min-width:220px"><button class="btn add-position-btn" style="padding:6px 12px;font-size:11px"><span class="ms sm">add</span> Add position</button>';
      tableHead.appendChild(controls);
    }

    function animateAum(target) {
      const node = document.querySelector('.aum-value');
      if (!node) return;
      const start = performance.now();
      const duration = 600;
      function tick(now) {
        const pct = Math.min(1, (now - start) / duration);
        node.textContent = fmt.money(target * pct);
        if (pct < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    }

    function renderHoldings(items, summaryBuckets) {
      const total = items.reduce((sum, item) => sum + Number(item.market_value_usd || 0), 0) || 1;
      groupedSummary = summaryBuckets;
      tbody.innerHTML = summaryBuckets.map(group => {
        const children = items.filter(p => p.asset_class === group.label);
        return `<tr class="group-header" data-group="${escapeHtml(group.label)}"><td colspan="4"><span class="ms sm" style="vertical-align:middle;margin-right:6px">expand_more</span>${escapeHtml(group.label)} — ${fmt.money(group.market_value_usd)} · ${fmt.pct(group.pct_of_portfolio)}</td></tr>` +
          children.map(p => `<tr data-ticker="${escapeHtml(p.ticker)}" data-group-child="${escapeHtml(group.label)}"><td>${escapeHtml(p.name || p.ticker)}</td><td class="muted">${escapeHtml(p.ticker)}</td><td class="num">${fmt.money(p.market_value_usd)}</td><td class="num">${fmt.pct((Number(p.market_value_usd || 0) / total) * 100)}</td></tr>`).join('');
      }).join('') || '<tr><td colspan="4" class="muted" style="text-align:center;padding:24px">No positions loaded.</td></tr>';
      tbody.querySelectorAll('tr[data-ticker]').forEach(row => row.addEventListener('click', () => {
        location.href = `table.html?ticker=${encodeURIComponent(row.dataset.ticker)}`;
      }));
      tbody.querySelectorAll('.group-header').forEach(header => header.addEventListener('click', () => {
        const group = header.dataset.group;
        const children = [...tbody.querySelectorAll(`[data-group-child="${CSS.escape(group)}"]`)];
        const hide = !children[0]?.hasAttribute('hidden');
        children.forEach(child => child.toggleAttribute('hidden', hide));
        const icon = header.querySelector('.ms');
        if (icon) icon.textContent = hide ? 'expand_less' : 'expand_more';
      }));
    }

    async function load(view = 'asset') {
      const [{ snapshot, summary, positions }, cashflow] = await Promise.all([loadPortfolioSummary(), API.get('/liquidity?months=12')]);
      allPositions = positions;
      const buckets = view === 'asset' ? (summary.asset_class || []) : (view === 'geo' ? (summary.geo_region || []) : (summary.sector || []));
      animateAum(Number(snapshot.total_aum_usd || 0));
      document.querySelector('.aum-date').textContent = `As of ${fmt.date(snapshot.created_at)} · ${snapshot.position_count} positions`;
      renderDonut(document.querySelector('.chart-wrap svg'), document.querySelector('.legend'), buckets);
      renderHoldings(positions, summary.asset_class || []);
      renderCashflow(document.querySelector('.cashflow-card svg'), cashflow.cash_flows || [], 760);
    }

    document.querySelector('.search-input')?.addEventListener('input', event => {
      const q = event.target.value.trim().toLowerCase();
      const filtered = !q ? allPositions : allPositions.filter(p => `${p.name || ''} ${p.ticker || ''}`.toLowerCase().includes(q));
      renderHoldings(filtered, groupedSummary);
    });
    document.querySelector('.add-position-btn')?.addEventListener('click', () => {
      if (tbody.querySelector('.inline-create')) return;
      tbody.insertAdjacentHTML('afterbegin', `<tr class="inline-create"><td><input class="edit-input asset-ticker" placeholder="Ticker"></td><td><input class="edit-input asset-name" placeholder="Name"></td><td><input class="edit-input asset-class" placeholder="Asset class"></td><td><button class="btn primary asset-save" style="padding:4px 10px;font-size:11px">Save</button></td></tr>`);
      tbody.querySelector('.asset-save')?.addEventListener('click', async () => {
        const row = tbody.querySelector('.inline-create');
        try {
          await API.post('/portfolio/positions', {
            ticker: row.querySelector('.asset-ticker').value.trim(),
            name: row.querySelector('.asset-name').value.trim(),
            asset_class: row.querySelector('.asset-class').value.trim(),
            quantity: 1,
            market_value_usd: 0,
          });
          toast('Position added', 'success');
          await load(seg?.querySelector('button.on')?.dataset.value || 'asset');
        } catch (error) {
          toast(API.detail(error), 'error');
        }
      });
    });
    seg?.addEventListener('seg-change', async event => {
      try {
        await load(event.detail.value || 'asset');
      } catch (error) {
        toast(API.detail(error), 'error');
      }
    });
    try {
      await load('asset');
    } catch (error) {
      toast(API.detail(error), 'error');
    }
  }

  async function initBriefings() {
    if (!(await API.redirectIfUnauth())) return;
    const tbody = document.querySelector('table.list tbody');
    const banner = document.querySelector('.gen-banner');
    const count = document.querySelector('.table-head .uplabel');
    const generateBtn = document.querySelector('.generate-bar .btn.primary');
    let pollId = null;
    let pollStartedAt = 0;
    function render(items) {
      const generating = items.some(b => b.status === 'generating');
      banner.style.display = generating ? 'flex' : 'none';
      if (generating) {
        if (!pollId) {
          pollStartedAt = Date.now();
          pollId = window.setInterval(load, 3000);
        }
        const seconds = Math.max(0, Math.round((Date.now() - pollStartedAt) / 1000));
        const text = banner.querySelector('span');
        if (text) text.innerHTML = `Generating briefing... <strong>${seconds}s</strong>`;
      } else if (pollId) {
        window.clearInterval(pollId);
        pollId = null;
      }
      count.textContent = `${items.length} briefings`;
      tbody.innerHTML = items.length ? items.map(b => `<tr data-id="${b.id}" data-status="${escapeHtml(b.status || 'ready')}">
        <td style="font-weight:600;color:var(--ink);white-space:nowrap">${fmt.date(b.created_at)}</td>
        <td><span class="pill ${b.scope === 'full' ? 'accent' : 'mute'}">${escapeHtml(b.scope || 'full')}</span></td>
        <td class="version">v${b.version || 1}</td>
        <td class="summary">${escapeHtml(briefingSummary(b))}</td>
        <td>${b.status === 'failed' ? '<button class="btn ghost retry-btn" style="padding:4px 10px;font-size:11px">Retry</button>' : '<span class="ms sm" style="color:var(--ink-mute)">chevron_right</span>'}</td>
      </tr>`).join('') : '<tr><td colspan="5" class="muted" style="text-align:center;padding:32px">No briefings yet. Generate your first briefing using the controls above.</td></tr>';
      tbody.querySelectorAll('tr[data-id]').forEach(row => row.addEventListener('click', () => {
        if (row.dataset.status === 'generating') {
          toast('Briefing is still being generated...', 'info');
          return;
        }
        if (row.dataset.status === 'failed') return;
        location.href = `briefing.html?id=${row.dataset.id}`;
      }));
      tbody.querySelectorAll('.retry-btn').forEach(button => button.addEventListener('click', async event => {
        event.stopPropagation();
        const row = button.closest('tr');
        try {
          await API.post('/briefings', { scope: row.querySelector('.pill')?.textContent.trim().toLowerCase() || 'full' });
          toast('Briefing generation retried', 'success');
          await load();
        } catch (error) {
          toast(API.detail(error), 'error');
        }
      }));
    }
    async function load() {
      const payload = await API.get('/briefings');
      render(normalizeList(payload));
    }
    generateBtn?.addEventListener('click', async () => {
      const scope = document.querySelector('#scope-seg button.on')?.dataset.value || 'full';
      setButtonBusy(generateBtn, 'Generating...', true);
      try {
        await API.post('/briefings', { scope });
        toast('Briefing requested', 'success');
        await load();
      } catch (error) {
        toast(API.detail(error), 'error');
      } finally {
        setButtonBusy(generateBtn, 'Generating...', false);
      }
    });
    try { await load(); } catch (error) { toast(API.detail(error), 'error'); }
  }

  async function initBriefing() {
    if (!(await API.redirectIfUnauth())) return;
    const id = new URLSearchParams(location.search).get('id');
    const body = document.querySelector('.briefing-body');
    try {
      const briefing = id ? await API.get(`/briefings/${id}`) : normalizeList(await API.get('/briefings?limit=1'))[0];
      if (!briefing) {
        body.innerHTML = '<div class="card" style="padding:20px">Briefing not found. <a href="briefings.html">Browse all briefings</a>.</div>';
        return;
      }
      document.querySelector('.briefing-title').textContent = briefing.week_label || `Briefing ${briefing.id}`;
      document.querySelector('.briefing-dateline').textContent = `Generated ${fmt.date(briefing.created_at)}`;
      document.querySelector('.briefing-meta .pill').textContent = `${briefing.scope || 'full'} briefing`;
      document.querySelector('.briefing-meta .pill.mute').textContent = `v${briefing.version || 1}`;
      body.innerHTML = briefingHtml(briefing);
      let toc = document.querySelector('.toc-nav');
      if (!toc) {
        toc = document.createElement('nav');
        toc.className = 'toc-nav';
        toc.style.cssText = 'position:sticky;top:88px;align-self:flex-start;margin-bottom:20px;padding:12px 14px;border:1px solid var(--rule);border-radius:6px;background:#fffdfb;font-size:12px';
        document.querySelector('.briefing-wrap')?.insertBefore(toc, document.querySelector('.briefing-header')?.nextSibling || body);
      }
      const headers = [...body.querySelectorAll('h2')];
      if (toc && headers.length) {
        toc.innerHTML = `<ol>${headers.map(header => {
          const idValue = slugify(header.textContent);
          header.id = idValue;
          return `<li><a href="#${idValue}">${escapeHtml(header.textContent)}</a></li>`;
        }).join('')}</ol>`;
      }
      const text = body.textContent.trim();
      const words = text ? text.split(/\s+/).length : 0;
      let meta = document.querySelector('.read-meta');
      if (!meta) {
        meta = document.createElement('span');
        meta.className = 'read-meta';
        document.querySelector('.briefing-meta')?.appendChild(meta);
      }
      meta.textContent = `~${Math.max(1, Math.ceil(words / 200))} min read · ${words.toLocaleString()} words`;
      body.addEventListener('click', event => {
        const link = event.target.closest('a[data-risk-id]');
        if (!link) return;
        event.preventDefault();
        location.href = `cockpit.html?risk_id=${encodeURIComponent(link.dataset.riskId)}`;
      });
      document.querySelector('.briefing-actions .btn.primary')?.addEventListener('click', () => window.print());
      document.querySelector('.briefing-actions .btn:not(.primary)')?.addEventListener('click', async () => {
        if (!window.confirm('Generate a new briefing with the latest data?')) return;
        try {
          const next = await API.post('/briefings', { scope: briefing.scope || 'full' });
          location.href = `briefing.html?id=${next.id}`;
        } catch (error) {
          toast(API.detail(error), 'error');
        }
      });
    } catch (error) {
      toast(API.detail(error), 'error');
    }
  }

  async function initTable() {
    if (!(await API.redirectIfUnauth())) return;
    const tbody = document.querySelector('table.sheet tbody');
    const sourceList = document.querySelector('.sources');
    const chipNodes = [...document.querySelectorAll('.toolbar .chip')];
    const searchInput = document.querySelector('.search input');
    const addRowButton = document.querySelector('.toolbar .btn');
    const tickerFilter = new URLSearchParams(location.search).get('ticker');
    let allPositions = [];
    let visiblePositions = [];
    let total = 1;
    let activeAssetFilters = new Set();

    function currentItems() {
      const search = (searchInput?.value || '').trim().toLowerCase();
      return allPositions.filter(position => {
        const matchesTicker = !tickerFilter || position.ticker === tickerFilter;
        const matchesAsset = !activeAssetFilters.size || activeAssetFilters.has(position.asset_class);
        const haystack = `${position.ticker || ''} ${position.name || ''}`.toLowerCase();
        const matchesSearch = !search || haystack.includes(search);
        return matchesTicker && matchesAsset && matchesSearch;
      });
    }

    function renderRows(items) {
      visiblePositions = items;
      total = items.reduce((sum, p) => sum + Number(p.market_value_usd || 0), 0) || 1;
      document.querySelector('.row-count').textContent = `${items.length} positions`;
      tbody.innerHTML = items.length ? items.map((p, i) => `<tr data-id="${p.id}">
        <td class="rownum">${i + 1}</td><td class="ticker">${escapeHtml(p.ticker)}</td><td data-field="name">${escapeHtml(p.name || '')}</td>
        <td data-field="asset_class"><span class="ac-badge">${escapeHtml(p.asset_class || '')}</span></td>
        <td class="num" data-field="quantity">${fmt.num(p.quantity, 2)}</td><td class="num" data-field="market_value_usd">${fmt.money(p.market_value_usd, 2)}</td>
        <td class="num">${fmt.pct(Number(p.market_value_usd || 0) / total * 100)}</td></tr>`).join('') : '<tr><td colspan="7" class="muted" style="text-align:center;padding:24px">No positions yet. Upload a CSV or drag a document to get started.</td></tr>';
      tbody.querySelectorAll('tr').forEach(row => {
        row.addEventListener('click', () => selectRow(row.dataset.id));
        row.querySelectorAll('[data-field]').forEach(cell => cell.addEventListener('dblclick', () => editCell(row, cell)));
      });
      if (items[0]) selectRow(items[0].id);
    }
    async function load() {
      const [docs, payload] = await Promise.all([API.get('/documents'), API.get('/portfolio/positions')]);
      const docsHtml = normalizeList(docs).map(d => `<div class="src-item"><div class="top-row"><span class="ico ${d.file_type === 'csv' ? 'csv' : 'pdf'}"><span class="ms">${d.file_type === 'csv' ? 'table_view' : 'picture_as_pdf'}</span></span><span class="fname">${escapeHtml(d.filename)}</span></div><div class="meta">${fmt.date(d.created_at)}</div><div class="badges"><span class="src-badge ok">${escapeHtml(d.extraction_status || 'uploaded')}</span></div></div>`).join('');
      sourceList.querySelectorAll('.src-item:not(.active)').forEach(n => n.remove());
      sourceList.insertAdjacentHTML('beforeend', docsHtml);
      allPositions = normalizeList(payload);
      renderRows(currentItems());
    }
    async function selectRow(id) {
      const p = allPositions.find(item => item.id === id);
      if (!p) return;
      tbody.querySelectorAll('tr').forEach(row => row.classList.toggle('sel', row.dataset.id === id));
      document.getElementById('detail-panel').style.display = 'flex';
      const title = document.querySelector('.ticker-big');
      const subtitle = document.querySelector('.sec-name');
      if (title) title.textContent = p.ticker;
      if (subtitle) subtitle.textContent = p.name || p.asset_class || '';
      const inputs = document.querySelectorAll('#detail-panel input');
      if (inputs[0]) inputs[0].value = fmt.num(p.quantity, 2);
      if (inputs[1]) inputs[1].value = fmt.money((Number(p.market_value_usd || 0) / Math.max(Number(p.quantity || 1), 1)), 2).replace('$', '');
      if (inputs[2]) inputs[2].value = fmt.money(p.market_value_usd, 2);
      if (inputs[3]) inputs[3].value = 'USD';
      try {
        const [prices, risks] = await Promise.all([
          API.get(`/market/prices?ticker=${encodeURIComponent(p.ticker)}&period=30d`),
          API.get(`/risk/register?ticker=${encodeURIComponent(p.ticker)}`),
        ]);
        const spark = document.querySelector('.sparkbox svg');
        const priceRows = prices?.prices || [];
        if (spark && priceRows.length) {
          const closes = priceRows.map(item => Number(item.close || 0));
          const min = Math.min(...closes);
          const max = Math.max(...closes);
          const range = max - min || 1;
          const points = closes.map((value, index) => `${index * (260 / Math.max(closes.length - 1, 1))},${38 - ((value - min) / range) * 24}`).join(' ');
          const positive = closes[closes.length - 1] >= closes[0];
          spark.innerHTML = `<polyline points="${points}" fill="none" stroke="${positive ? '#3F7A4F' : '#B91C1C'}" stroke-width="1.5"></polyline>`;
        }
        const linked = document.querySelector('.sparkbox + div');
        if (linked) {
          const riskItems = normalizeList(risks);
          linked.innerHTML = `<div class="uplabel" style="margin-bottom:6px;">Linked risks</div>${riskItems.length ? riskItems.map(item => `<a href="cockpit.html?severity=${encodeURIComponent(item.severity || '')}" style="display:flex;align-items:center;gap:8px;padding:8px 10px;border:1px solid var(--rule);border-radius:5px;text-decoration:none;color:var(--ink-soft);font-size:12px;background:var(--paper-2);margin-top:6px;"><span class="ms sm" style="color:var(--ele-fg)">warning</span>${escapeHtml(item.headline || item.description || 'Risk')}<span style="flex:1"></span><span class="pill ${severityClass(item.severity)}">${escapeHtml(item.severity || 'Risk')}</span></a>`).join('') : '<div class="muted">No linked risks for this position.</div>'}`;
        }
      } catch (_error) {
        // Keep panel usable if enrichment calls fail.
      }
    }
    async function editCell(row, cell) {
      const field = cell.dataset.field;
      const current = allPositions.find(p => p.id === row.dataset.id);
      const raw = field === 'market_value_usd' ? current.market_value_usd : current[field];
      const input = document.createElement('input');
      input.className = 'edit-input';
      input.value = raw ?? '';
      cell.innerHTML = '';
      cell.appendChild(input);
      input.focus();
      input.addEventListener('blur', async () => {
        const value = ['quantity', 'market_value_usd'].includes(field) ? Number(input.value.replace(/[$,]/g, '')) : input.value;
        try {
          await API.patch(`/portfolio/positions/${row.dataset.id}`, { [field]: value });
          toast('Position updated', 'success');
          await load();
        } catch (error) {
          toast(API.detail(error), 'error');
          await load();
        }
      }, { once: true });
    }
    document.getElementById('detail-close')?.addEventListener('click', () => {
      document.getElementById('detail-panel').style.display = 'none';
    });
    document.querySelector('.upload-btn')?.addEventListener('click', () => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.csv,text/csv';
      input.onchange = async () => {
        if (!input.files[0]) return;
        const body = new FormData();
        body.append('file', input.files[0]);
        try { await API.post('/ingest/csv', body); toast('Portfolio uploaded', 'success'); await load(); }
        catch (error) { toast(API.detail(error), 'error'); }
      };
      input.click();
    });
    chipNodes.forEach(chip => chip.addEventListener('click', () => {
      const label = chip.textContent.trim().split('·')[0].trim();
      if (label.toLowerCase() === 'all') {
        activeAssetFilters = new Set();
        chipNodes.forEach(node => node.classList.toggle('on', node === chip));
      } else {
        const mapped = label === 'PE' ? 'Private Equity' : label;
        if (activeAssetFilters.has(mapped)) activeAssetFilters.delete(mapped);
        else activeAssetFilters.add(mapped);
        chipNodes[0]?.classList.remove('on');
        chip.classList.toggle('on', activeAssetFilters.has(mapped));
      }
      renderRows(currentItems());
    }));
    searchInput?.addEventListener('input', () => renderRows(currentItems()));
    addRowButton?.addEventListener('click', () => {
      if (tbody.querySelector('.inline-create')) return;
      tbody.insertAdjacentHTML('afterbegin', `<tr class="inline-create"><td class="rownum">+</td><td><input class="edit-input new-ticker" placeholder="Ticker"></td><td><input class="edit-input new-name" placeholder="Name"></td><td><input class="edit-input new-asset" placeholder="Asset class"></td><td><input class="edit-input new-qty" placeholder="Qty"></td><td><input class="edit-input new-value" placeholder="Market value"></td><td colspan="2"><button class="btn primary save-new" style="padding:4px 10px;font-size:11px">Save</button></td></tr>`);
      tbody.querySelector('.save-new')?.addEventListener('click', async () => {
        const row = tbody.querySelector('.inline-create');
        try {
          await API.post('/portfolio/positions', {
            ticker: row.querySelector('.new-ticker').value.trim(),
            name: row.querySelector('.new-name').value.trim(),
            asset_class: row.querySelector('.new-asset').value.trim(),
            quantity: Number(row.querySelector('.new-qty').value || 0),
            market_value_usd: Number(row.querySelector('.new-value').value || 0),
          });
          toast('Position added', 'success');
          await load();
        } catch (error) {
          toast(API.detail(error), 'error');
        }
      });
    });
    const deleteButton = document.querySelector('#detail-panel .btn.danger');
    deleteButton?.addEventListener('click', async () => {
      const selected = tbody.querySelector('tr.sel');
      if (!selected) return;
      if (!deleteButton.dataset.confirming) {
        deleteButton.dataset.confirming = '1';
        deleteButton.innerHTML = '<span class="ms sm">warning</span> Confirm delete';
        return;
      }
      try {
        await API.del(`/portfolio/positions/${selected.dataset.id}`);
        toast('Position deleted', 'success');
        document.getElementById('detail-panel').style.display = 'none';
        delete deleteButton.dataset.confirming;
        deleteButton.innerHTML = '<span class="ms sm">delete</span> Delete';
        await load();
      } catch (error) {
        toast(API.detail(error), 'error');
      }
    });
    try { await load(); } catch (error) { toast(API.detail(error), 'error'); }
  }

  async function initDocuments() {
    if (!(await API.redirectIfUnauth())) return;
    const tbody = document.querySelector('table.list tbody');
    const drawer = document.getElementById('review-drawer');
    const backdrop = document.getElementById('review-drawer-backdrop');
    const uploadZone = document.querySelector('.upload-zone');
    const reviewFields = document.querySelector('.fields');
    const applyButton = document.querySelector('#review-drawer footer .btn.primary');
    let activeDocumentId = null;
    let activeReview = null;

    function canApply(review) {
      return !!(review && Array.isArray(review.field_reviews) && review.field_reviews.some(field => field.resolved));
    }

    function renderReview(review) {
      activeReview = review;
      if (applyButton) applyButton.disabled = !canApply(review);
      reviewFields.innerHTML = (review.field_reviews || []).map(f => `<div class="extraction-field">
        <div class="ef-header"><span class="ef-label">${escapeHtml(f.field)}</span></div>
        <div class="ef-value">${escapeHtml(f.reason || '')}</div>
        <div class="ef-confidence"><div class="bar"><div class="fill ${f.confidence > .9 ? 'hi' : f.confidence > .7 ? 'mid' : 'lo'}" style="width:${Math.round((f.confidence || 0) * 100)}%"></div></div><span class="conf-pct">${Math.round((f.confidence || 0) * 100)}%</span></div>
        <div class="ef-actions">
          <button class="ef-btn approve${f.resolved ? ' approved' : ''}" data-field="${escapeHtml(f.field)}"><span class="ms">check</span>${f.resolved ? ' Approved' : ' Approve'}</button>
          <button class="ef-btn reject" data-field="${escapeHtml(f.field)}"><span class="ms">close</span> Reject</button>
        </div>
      </div>`).join('') || '<div class="muted">No review fields.</div>';
    }

    async function load() {
      const docs = normalizeList(await API.get('/documents'));
      document.querySelector('.table-head .uplabel').textContent = `${docs.length} documents`;
      tbody.innerHTML = docs.map(d => `<tr data-id="${d.id}">
        <td>${escapeHtml(d.filename)}</td><td><span class="ftype-ico ${d.file_type}"><span class="ms">${d.file_type === 'csv' ? 'table_view' : 'picture_as_pdf'}</span>${escapeHtml(d.file_type.toUpperCase())}</span></td>
        <td>${escapeHtml(d.folder || '')}</td><td><span class="pill ${d.extraction_status === 'approved' ? 'good' : d.extraction_status === 'failed' ? 'pri' : 'ele'}">${escapeHtml(d.extraction_status)}</span></td>
        <td class="muted">${fmt.date(d.created_at)}</td><td>${d.extraction_status === 'failed' ? '<button class="btn ghost retry-btn" style="padding:4px 10px;font-size:11px">Retry</button>' : '<button class="btn ghost" style="padding:4px 10px;font-size:11px">Review</button>'}</td></tr>`).join('');
      tbody.querySelectorAll('tr[data-id]').forEach(row => row.addEventListener('click', () => review(row.dataset.id)));
      tbody.querySelectorAll('.retry-btn').forEach(button => button.addEventListener('click', async event => {
        event.stopPropagation();
        const row = button.closest('tr');
        try {
          await API.post(`/documents/${row.dataset.id}/parse`, {});
          toast('Retry started', 'success');
          await load();
        } catch (error) {
          toast(API.detail(error), 'error');
        }
      }));
    }
    async function review(id) {
      activeDocumentId = id;
      try {
        const data = await API.get(`/documents/${id}/fields`);
        drawer.classList.add('open');
        backdrop.classList.add('open');
        renderReview(data);
      } catch (error) {
        toast(API.detail(error), 'error');
      }
    }

    async function uploadFile(file) {
      const uploadRow = document.querySelector('.upload-row');
      const pct = uploadRow?.querySelector('.pct');
      const fill = uploadRow?.querySelector('.fill');
      const size = uploadRow?.querySelector('.fsize');
      if (uploadRow) uploadRow.style.display = 'flex';
      if (uploadRow?.querySelector('.fname')) uploadRow.querySelector('.fname').textContent = file.name;
      if (size) size.textContent = `${(file.size / 1024 / 1024).toFixed(1)} MB · Uploading...`;
      if (fill) fill.style.width = '0%';
      if (pct) pct.textContent = '0%';
      return await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', API.url('/documents/upload'));
        const token = API.getToken();
        if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        const csrf = document.cookie.split('; ').find(row => row.startsWith('__crb_csrf='))?.split('=').slice(1).join('=');
        if (csrf) xhr.setRequestHeader('X-CSRF-Token', decodeURIComponent(csrf));
        xhr.withCredentials = API.url('/documents/upload').startsWith(location.origin) || API.url('/documents/upload').startsWith('/api');
        xhr.upload.addEventListener('progress', event => {
          if (!event.lengthComputable) return;
          const progress = Math.round((event.loaded / event.total) * 100);
          if (fill) fill.style.width = `${progress}%`;
          if (pct) pct.textContent = `${progress}%`;
        });
        xhr.onload = () => {
          if (xhr.status < 200 || xhr.status >= 300) {
            reject(new Error(xhr.statusText || 'Upload failed'));
            return;
          }
          try {
            resolve(JSON.parse(xhr.responseText || '{}'));
          } catch (_error) {
            reject(new Error('Upload response was not valid JSON'));
          }
        };
        xhr.onerror = () => reject(new Error('Upload failed'));
        const body = new FormData();
        body.append('file', file);
        xhr.send(body);
      });
    }

    uploadZone?.addEventListener('click', () => {
      const input = document.createElement('input');
      input.type = 'file';
      input.onchange = async () => {
        if (!input.files[0]) return;
        try {
          const doc = await uploadFile(input.files[0]);
          if (!doc || !doc.id) throw new Error('Upload did not return a document id');
          await API.post(`/documents/${doc.id}/parse`, {});
          toast('Document uploaded', 'success');
          await load();
        }
        catch (error) { toast(API.detail(error), 'error'); }
      };
      input.click();
    });
    ['dragover', 'dragleave', 'drop'].forEach(type => uploadZone?.addEventListener(type, event => {
      if (type === 'dragover' || type === 'drop') event.preventDefault();
      uploadZone.classList.toggle('drag-over', type === 'dragover');
      if (type === 'dragleave') uploadZone.classList.remove('drag-over');
      if (type === 'drop' && event.dataTransfer?.files?.[0]) {
        uploadZone.classList.remove('drag-over');
        const input = { files: event.dataTransfer.files };
        const file = input.files[0];
        uploadFile(file)
          .then(doc => {
            if (!doc || !doc.id) throw new Error('Upload did not return a document id');
            return API.post(`/documents/${doc.id}/parse`, {}).then(() => doc);
          })
          .then(() => { toast('Document uploaded', 'success'); return load(); })
          .catch(error => toast(API.detail(error), 'error'));
      }
    }));
    document.getElementById('scroll-to-upload')?.addEventListener('click', () => {
      document.getElementById('upload-zone')?.scrollIntoView({ behavior: 'smooth' });
    });
    reviewFields?.addEventListener('click', async event => {
      const button = event.target.closest('.ef-btn');
      if (!button || !activeDocumentId) return;
      const approved = button.classList.contains('approve');
      try {
        const review = await API.put(`/documents/${activeDocumentId}/fields`, { field_id: button.dataset.field, approved });
        renderReview(review);
        toast(`Field ${approved ? 'approved' : 'rejected'}`, 'success');
      } catch (error) {
        toast(API.detail(error), 'error');
      }
    });
    applyButton?.addEventListener('click', async () => {
      if (!activeDocumentId) return;
      try { await API.post(`/documents/${activeDocumentId}/apply`, {}); toast('Applied to portfolio', 'success'); drawer.classList.remove('open'); backdrop.classList.remove('open'); await load(); }
      catch (error) { toast(API.detail(error), 'error'); }
    });
    try { await load(); } catch (error) { toast(API.detail(error), 'error'); }
  }

  async function initLiquidity() {
    if (!(await API.redirectIfUnauth())) return;
    try {
      const summary = await API.get('/liquidity?months=24');
      const buckets = document.querySelectorAll('.bucket');
      const liquid = Number(summary.cash_on_hand_usd || 0);
      const semi = Number(summary.expected_distributions_usd || 0) + Number(summary.recallable_pending_usd || 0);
      const illiquid = Number(summary.total_unfunded_usd || 0);
      const total = liquid + semi + illiquid || 1;
      [liquid, semi, illiquid].forEach((value, i) => {
        buckets[i].querySelector('.bkt-value').textContent = fmt.money(value);
        buckets[i].querySelector('.bkt-pct').textContent = fmt.pct(value / total * 100);
        const fill = buckets[i].querySelector('.fill');
        fill.style.width = '0%';
        requestAnimationFrame(() => { fill.style.width = Math.max(4, value / total * 100) + '%'; });
      });
      const runway = (liquid / Math.max(summary.scheduled_outflows_usd || 1, 1)) * 3;
      document.querySelector('.rw-number').textContent = fmt.num(runway, 1);
      document.querySelector('.rw-basis').textContent = `${fmt.money(summary.cash_on_hand_usd)} cash on hand · ${fmt.money(summary.scheduled_outflows_usd)} scheduled outflows`;
      const basis = document.querySelector('.rw-basis');
      document.querySelector('.rw-number').style.color = '';
      if (runway < 6) {
        document.querySelector('.rw-number').style.color = 'var(--pri-fg)';
        basis.insertAdjacentHTML('beforeend', ' <span class="pill pri">Below threshold</span>');
      } else if (runway < 12) {
        document.querySelector('.rw-number').style.color = 'var(--ele-fg)';
        basis.insertAdjacentHTML('beforeend', ' <span class="pill ele">Watch</span>');
      }
      renderCashflow(document.querySelector('.cashflow-card svg, .ladder-card svg, svg[viewBox="0 0 820 160"]'), summary.cash_flows || [], 820);
      const events = [
        { date: summary.next_call_due_date, description: 'Next capital call', type: 'Outflow', source: 'Private markets', amount: -Number(summary.next_call_amount_usd || 0) },
        { date: 'Next 90 days', description: 'Expected distributions', type: 'Inflow', source: 'Private markets', amount: Number(summary.expected_distributions_usd || 0) },
        { date: 'Next 90 days', description: 'Scheduled outflows', type: 'Outflow', source: 'Portfolio commitments', amount: -Number(summary.scheduled_outflows_usd || 0) },
      ].filter(e => e.amount);
      document.querySelector('table.list tbody').innerHTML = events.length
        ? events.map(e => `<tr><td style="font-weight:600;color:var(--ink);white-space:nowrap">${escapeHtml(e.date || '')}</td><td>${escapeHtml(e.description)}</td><td><span class="pill ${e.amount >= 0 ? 'good' : 'pri'}">${e.type}</span></td><td class="muted">${escapeHtml(e.source)}</td><td class="amount-cell ${e.amount >= 0 ? 'inflow' : 'outflow'}">${fmt.signedMoney(e.amount)}</td></tr>`).join('')
        : '<tr><td colspan="5" class="muted" style="text-align:center;padding:24px">No scheduled events in the selected period.</td></tr>';
    } catch (error) {
      toast(API.detail(error), 'error');
    }
  }

  async function initSettings() {
    // Wire settings-nav scroll-spy (sync)
    const settingSections = document.querySelectorAll('.sec[id]');
    const settingNavLinks = document.querySelectorAll('.settings-nav a');
    if (settingSections.length && settingNavLinks.length) {
      window.addEventListener('scroll', () => {
        let current = '';
        settingSections.forEach(sec => {
          if (sec.getBoundingClientRect().top < 120) current = sec.id;
        });
        if (!current && settingSections[0]) current = settingSections[0].id;
        settingNavLinks.forEach(a => {
          a.classList.toggle('active', a.getAttribute('href') === '#' + current);
        });
      }, { passive: true });
    }

    if (!(await API.redirectIfUnauth())) return;
    try {
      const [settings, keys, session, members, security, billing] = await Promise.all([
        API.get('/settings'),
        API.get('/settings/api-keys'),
        API.get('/auth/me'),
        API.get('/settings/members'),
        API.get('/settings/security'),
        API.get('/settings/billing-portal'),
      ]);
      const workspaceInputs = document.querySelectorAll('#workspace input, #workspace select');
      if (workspaceInputs[0]) workspaceInputs[0].value = session.user?.workspace_name || '';
      if (workspaceInputs[1]) workspaceInputs[1].value = settings.reporting_currency || 'USD';
      const scheduleInputs = document.querySelectorAll('#schedule input, #schedule select');
      if (scheduleInputs[0]) scheduleInputs[0].value = settings.briefing_day || 'Monday';
      if (scheduleInputs[1]) scheduleInputs[1].value = settings.briefing_time || '07:00';
      document.querySelector('#schedule .sw')?.classList.toggle('on', !!settings.briefing_auto_publish);
      const banner = document.querySelector('.new-key-banner');
      if (banner) banner.style.display = 'none';
      const keyList = document.querySelector('#api-keys .body > div:last-child');
      if (keyList) keyList.innerHTML = normalizeList(keys).map(k => `<div class="key-row"><div><div class="key-name">${escapeHtml(k.label)}</div><span class="key-token">${escapeHtml(k.key_prefix)}...</span><div class="key-meta">Created ${fmt.date(k.created_at)}</div></div><button class="btn danger" data-id="${k.id}" style="padding:5px 10px;font-size:11px">Revoke</button></div>`).join('');
      keyList?.querySelectorAll('.btn.danger[data-id]').forEach(button => button.addEventListener('click', async () => {
        try {
          await API.del(`/settings/api-keys/${button.dataset.id}`);
          toast('API key revoked', 'success');
          button.closest('.key-row')?.remove();
        } catch (error) {
          toast(API.detail(error), 'error');
        }
      }));

      const accessBody = document.querySelector('#access .body > div:first-child');
      if (accessBody) {
        accessBody.innerHTML = (members.items || []).map(member => `<div class="member-row" data-id="${member.id}">
          <div class="member-ava" style="background:var(--accent)">${escapeHtml((member.display_name || member.email).split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase())}</div>
          <div class="member-info"><div class="member-name">${escapeHtml(member.display_name || member.email)}</div><div class="member-email">${escapeHtml(member.email)}</div></div>
          <select style="padding:6px 8px;border:1px solid var(--rule);border-radius:4px"><option value="owner"${member.role === 'owner' ? ' selected' : ''}>owner</option><option value="admin"${member.role === 'admin' ? ' selected' : ''}>admin</option><option value="viewer"${member.role === 'viewer' ? ' selected' : ''}>viewer</option></select>
          <div class="member-meta">${member.is_current_user ? 'You' : (member.last_active_at ? fmt.date(member.last_active_at) : 'Active')}</div>
          ${member.is_current_user ? '' : '<button class="btn danger" style="padding:4px 10px;font-size:11px">Remove</button>'}
        </div>`).join('');
        accessBody.querySelectorAll('.member-row select').forEach(select => select.addEventListener('change', async () => {
          const row = select.closest('.member-row');
          try {
            await API.put(`/settings/members/${row.dataset.id}`, { role: select.value });
            toast('Member role updated', 'success');
          } catch (error) {
            toast(API.detail(error), 'error');
          }
        }));
        accessBody.querySelectorAll('.member-row .btn.danger').forEach(button => button.addEventListener('click', async () => {
          const row = button.closest('.member-row');
          try {
            await API.del(`/settings/members/${row.dataset.id}`);
            row.remove();
            toast('Member removed', 'success');
          } catch (error) {
            toast(API.detail(error), 'error');
          }
        }));
      }
      const inviteRow = document.querySelector('#access .invite-row');
      inviteRow?.querySelector('.btn.primary')?.addEventListener('click', async () => {
        const inputs = inviteRow.querySelectorAll('input,select');
        const role = inputs[1].value.toLowerCase().includes('admin') ? 'admin' : 'viewer';
        try {
          await API.post('/settings/members/invite', { email: inputs[0].value.trim(), role });
          toast('Invite sent', 'success');
        } catch (error) {
          toast(API.detail(error), 'error');
        }
      });

      const sessionList = document.querySelector('#security .body > div:nth-child(2)');
      if (sessionList) {
        sessionList.innerHTML = `<div class="uplabel" style="margin-bottom:10px">Active sessions</div>${(security.sessions || []).map(item => `<div class="session-row" data-id="${item.id}"><div class="session-ico"><span class="ms">${item.current ? 'laptop_mac' : 'devices'}</span></div><div class="session-info"><div class="session-device">${escapeHtml(item.device_info || 'Browser session')}</div><div class="session-detail">${escapeHtml(item.last_seen_at ? fmt.date(item.last_seen_at) : 'Active')}</div></div>${item.current ? '<span class="session-current">Current</span>' : '<button class="btn danger" style="padding:4px 10px;font-size:11px;flex-shrink:0">Revoke</button>'}</div>`).join('')}`;
        sessionList.querySelectorAll('.btn.danger').forEach(button => button.addEventListener('click', async () => {
          const row = button.closest('.session-row');
          try {
            await API.del(`/settings/sessions/${row.dataset.id}`);
            row.remove();
            toast('Session revoked', 'success');
          } catch (error) {
            toast(API.detail(error), 'error');
          }
        }));
      }

      const billingBtn = document.querySelector('#payment header .btn');
      if (billingBtn && billing.url) {
        billingBtn.setAttribute('onclick', '');
        billingBtn.addEventListener('click', () => window.open(billing.url, '_blank', 'noopener'));
      }
      const planName = document.querySelector('.plan-name');
      if (planName && billing.plan) planName.textContent = billing.plan;

      const accountRows = document.querySelectorAll('#account .account-row');
      if (accountRows[0]) {
        accountRows[0].querySelector('.ar-value').textContent = session.user?.email || '';
        accountRows[0].querySelector('.btn')?.addEventListener('click', async () => {
          const email = window.prompt('New email address');
          if (!email) return;
          try {
            await API.put('/auth/email', { email });
            accountRows[0].querySelector('.ar-value').textContent = email;
            toast('Email updated', 'success');
          } catch (error) {
            toast(API.detail(error), 'error');
          }
        });
      }
      if (accountRows[1]) {
        accountRows[1].querySelector('.btn')?.addEventListener('click', async () => {
          const currentPassword = window.prompt('Current password');
          const newPassword = window.prompt('New password');
          if (!newPassword) return;
          try {
            await API.put('/auth/password', { current_password: currentPassword || '', new_password: newPassword });
            toast('Password updated', 'success');
          } catch (error) {
            toast(API.detail(error), 'error');
          }
        });
      }
      document.querySelector('#api-keys header .btn')?.addEventListener('click', async () => {
        try {
          const key = await API.post('/settings/api-keys', { label: 'Browser key', key_type: 'live' });
          if (banner) {
            banner.style.display = 'flex';
            banner.querySelector('.key-reveal').textContent = key.plain_text_key;
          }
          toast('API key created', 'success');
        } catch (error) { toast(API.detail(error), 'error'); }
      });
      document.querySelector('#workspace .btn.primary')?.addEventListener('click', async () => {
        try {
          await API.put('/settings', { reporting_currency: workspaceInputs[1]?.value || 'USD' });
          toast('Workspace settings saved', 'success');
        }
        catch (error) { toast(API.detail(error), 'error'); }
      });
      document.querySelector('#schedule .btn.primary')?.addEventListener('click', async () => {
        try { await API.put('/settings', { briefing_day: scheduleInputs[0]?.value, briefing_time: scheduleInputs[1]?.value, briefing_auto_publish: document.querySelector('#schedule .sw')?.classList.contains('on') }); toast('Schedule saved', 'success'); }
        catch (error) { toast(API.detail(error), 'error'); }
      });
      document.querySelector('#account .btn.danger')?.addEventListener('click', async () => {
        try { await API.post('/auth/logout', {}); API.clearToken(); location.href = '/login.html'; }
        catch (_error) { API.clearToken(); location.href = '/login.html'; }
      });
    } catch (error) {
      toast(API.detail(error), 'error');
    }
  }

  async function initOnboarding() {
    let current = 1;
    const nextBtn = document.getElementById('next-btn');
    const backBtn = document.getElementById('back-btn');
    const progress = document.getElementById('enrich-progress');
    const progressMeta = progress?.parentElement?.nextElementSibling;
    const successCard = document.getElementById('success');
    function render() {
      [1, 2, 3].forEach(n => {
        document.getElementById('step-' + n)?.classList.toggle('active', n === current);
        const ind = document.getElementById('step-' + n + '-indicator');
        if (ind) ind.className = 'step' + (n < current ? ' done' : '') + (n === current ? ' active' : '');
        document.getElementById('conn-' + n)?.classList.toggle('done', n < current);
      });
      backBtn.style.display = current > 1 ? 'flex' : 'none';
      nextBtn.style.display = current === 3 ? 'none' : 'inline-flex';
    }

    async function resume() {
      try {
        const status = await API.get('/onboarding/status');
        if (status.state === 'complete') current = 3;
        else if (status.state === 'enriching' || status.state === 'uploading') current = 2;
        else current = 1;
        render();
      } catch (_error) {
        current = 1;
        render();
      }
    }

    async function pollStatus() {
      const startedAt = Date.now();
      const noticeId = 'enrich-slow-notice';
      while (true) {
        const status = await API.get('/onboarding/status');
        const pct = status.total ? Math.round((status.enriched / status.total) * 100) : 100;
        if (progress) progress.style.width = `${pct}%`;
        if (progressMeta) progressMeta.textContent = `${status.enriched || 0} / ${status.total || 0} positions enriched`;
        if (Date.now() - startedAt > 30000 && !document.getElementById(noticeId)) {
          progress?.closest('.enrich-status')?.insertAdjacentHTML('beforeend', `<div id="${noticeId}" style="font-size:11px;color:var(--ink-mute)">This is taking longer than usual. You can continue or come back later. <button class="btn ghost" id="skip-enrich" style="padding:4px 8px;font-size:11px">Skip to step 3</button></div>`);
          document.getElementById('skip-enrich')?.addEventListener('click', () => { current = 3; render(); });
        }
        if (status.state === 'complete') {
          current = 3;
          render();
          return;
        }
        await new Promise(resolve => window.setTimeout(resolve, 2000));
      }
    }

    document.querySelector('.upload-zone')?.addEventListener('click', () => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.csv,.pdf,text/csv,application/pdf';
      input.onchange = async () => {
        if (!input.files[0]) return;
        if (!/\.(csv|pdf)$/i.test(input.files[0].name)) {
          toast('Please upload a CSV or PDF file.', 'error');
          return;
        }
        const body = new FormData();
        body.append('file', input.files[0]);
        try {
          const data = await API.post('/ingest/csv', body);
          document.querySelector('.fname').textContent = input.files[0].name;
          document.querySelector('.fmeta').textContent = `${data.position_count || 0} positions`;
          current = 2;
          render();
          if (progress) progress.style.width = '0%';
          await pollStatus();
        } catch (error) { toast(API.detail(error), 'error'); }
      };
      input.click();
    });
    document.querySelector('#step-3 .btn.primary')?.addEventListener('click', async () => {
      const scope = document.querySelector('#step-3 .seg button.on')?.textContent.trim().toLowerCase() || 'full';
      try {
        const briefing = await API.post('/briefings', { scope });
        document.querySelector('#success a.btn.primary').href = `briefing.html?id=${briefing.id}`;
        document.getElementById('step-3').classList.remove('active');
        document.getElementById('panel-foot').style.display = 'none';
        successCard.classList.add('visible');
      } catch (error) { toast(API.detail(error), 'error'); }
    });
    nextBtn?.addEventListener('click', () => { if (current < 3) { current += 1; render(); } });
    backBtn?.addEventListener('click', () => { if (current > 1) { current -= 1; render(); } });
    await resume();
  }

  const routes = {
    '/login.html': initLogin,
    '/index.html': initDashboard,
    '/cockpit.html': initCockpit,
    '/assets.html': initAssets,
    '/briefings.html': initBriefings,
    '/briefing.html': initBriefing,
    '/table.html': initTable,
    '/documents.html': initDocuments,
    '/liquidity.html': initLiquidity,
    '/settings.html': initSettings,
    '/onboarding.html': initOnboarding,
  };

  // Shell config — href must match a nav entry in _shell.js NAV array
  const SHELL_CONFIG = {
    '/index.html':     ['index.html',     ['Home']],
    '/cockpit.html':   ['cockpit.html',   ['Risk Cockpit']],
    '/assets.html':    ['assets.html',    ['Assets']],
    '/table.html':     ['table.html',     ['Positions']],
    '/briefings.html': ['briefings.html', ['Briefings']],
    '/briefing.html':  ['briefings.html', ['Briefings', 'View']],
    '/documents.html': ['documents.html', ['Documents']],
    '/liquidity.html': ['liquidity.html', ['Liquidity']],
    '/settings.html':  ['settings.html',  ['Settings']],
  };

  document.addEventListener('DOMContentLoaded', () => {
    const path = location.pathname === '/'
      ? '/index.html'
      : location.pathname.includes('.') ? location.pathname : `${location.pathname}.html`;

    const shellConf = SHELL_CONFIG[path];
    if (shellConf && window.Shell) Shell.mount(shellConf[0], shellConf[1]);

    const init = routes[path];
    if (init) init();
  });
})();
