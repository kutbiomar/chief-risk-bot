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
    const max = Math.max(1, ...buckets.flatMap(b => [Math.abs(b.inflows || 0), Math.abs(b.outflows || 0), Math.abs(b.cumulative || 0)]));
    const step = (width - 70) / buckets.length;
    const base = 130;
    const bars = buckets.map((b, i) => {
      const x = 44 + i * step;
      const inH = Math.max(2, Math.abs(Number(b.inflows || 0)) / max * 110);
      const outH = Math.max(2, Math.abs(Number(b.outflows || 0)) / max * 110);
      const label = String(b.month || '').slice(5) || String(b.month || '').slice(0, 3);
      return `<rect x="${x}" y="${base - inH}" width="12" height="${inH}" rx="2" fill="#3F7A4F"></rect>
        <rect x="${x + 14}" y="${base - outH}" width="12" height="${outH}" rx="2" fill="#B91C1C" opacity=".72"></rect>
        <text x="${x + 13}" y="148" text-anchor="middle" font-size="7" fill="#81756f" font-family="JetBrains Mono">${escapeHtml(label)}</text>`;
    }).join('');
    const points = buckets.map((b, i) => {
      const x = 57 + i * step;
      const y = base - ((Number(b.cumulative || b.net || 0) / max) * 55);
      return `${x},${Math.max(12, Math.min(134, y))}`;
    }).join(' ');
    svg.innerHTML = '<line x1="40" y1="130" x2="' + (width - 5) + '" y2="130" stroke="var(--rule)" stroke-width=".5"/>' +
      bars + `<polyline points="${points}" fill="none" stroke="#1B2B5E" stroke-width="1.5" stroke-linejoin="round"></polyline>`;
  }

  async function initLogin() {
    try {
      await API.get('/auth/me', { redirectOnUnauthorized: false });
      API.markLoggedIn();
      window.location.href = '/index.html';
      return;
    } catch (_error) {
      API.clearToken();
    }

    const panels = document.querySelectorAll('[data-panel]');
    function panel(name) { return [...panels].find(p => p.dataset.panel === name); }
    function values(name) { return [...panel(name).querySelectorAll('input')].map(input => input.value.trim()); }
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

    panel('sign-in')?.querySelector('.btn.primary')?.addEventListener('click', async () => {
      const [email, password] = values('sign-in');
      try {
        const data = await API.post('/auth/login', { email, password });
        if (data && data.access_token) API.setToken(data.access_token);
        else API.markLoggedIn();
        window.location.href = '/index.html';
      } catch (error) {
        notice(panel('sign-in'), API.detail(error) || 'Invalid credentials');
      }
    });

    panel('register')?.querySelector('.btn.primary')?.addEventListener('click', async () => {
      const [display_name, workspace_name, email, password] = values('register');
      try {
        const data = await API.post('/auth/register', {
          display_name,
          workspace_name,
          email,
          password,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
          reporting_currency: 'USD',
        });
        if (data && data.access_token) API.setToken(data.access_token);
        else API.markLoggedIn();
        window.location.href = '/onboarding.html';
      } catch (error) {
        notice(panel('register'), API.detail(error));
      }
    });

    panel('forgot')?.querySelector('.btn.primary')?.addEventListener('click', async () => {
      const [email] = values('forgot');
      try {
        await API.post('/auth/forgot-password', { email });
        notice(panel('forgot'), 'Check your email for a reset link', 'ok');
      } catch (error) {
        notice(panel('forgot'), API.detail(error));
      }
    });
  }

  async function initDashboard() {
    if (!(await API.redirectIfUnauth())) return;
    document.querySelectorAll('.kpi-tile,.briefing-card,.events-card').forEach(el => el.classList.add('loading'));
    try {
      const [snapshot, positions, varResult, liquidity, risk, briefings] = await Promise.all([
        API.get('/portfolio/snapshot'),
        API.get('/portfolio/positions'),
        API.get('/var'),
        API.get('/liquidity'),
        API.get('/risk/register'),
        API.get('/briefings?limit=1'),
      ]);
      const kpis = document.querySelectorAll('.kpi-tile');
      kpis[0].querySelector('.kpi-value').textContent = fmt.money(snapshot.total_aum_usd);
      kpis[0].querySelector('.kpi-sub').textContent = `${snapshot.position_count} positions`;
      kpis[1].querySelector('.kpi-value').textContent = '$0.0M';
      kpis[1].querySelector('.kpi-delta').innerHTML = '<span class="ms sm">trending_flat</span> Live P&L pending';
      kpis[2].querySelector('.kpi-value').textContent = fmt.money(varResult.var_1d_95);
      kpis[3].querySelector('.kpi-value').textContent = fmt.num(((liquidity.cash_on_hand_usd || 0) / Math.max(liquidity.scheduled_outflows_usd || 1, 1)) * 3, 1);

      const counts = { priority: 0, elevated: 0, watch: 0 };
      normalizeList(risk).forEach(item => { if (counts[item.severity] !== undefined) counts[item.severity] += 1; });
      const riskRow = document.querySelector('.risk-row');
      riskRow.querySelector('.pill.pri').innerHTML = `<span class="dot"></span>${counts.priority} priority`;
      riskRow.querySelector('.pill.ele').innerHTML = `<span class="dot"></span>${counts.elevated} elevated`;
      riskRow.querySelector('.pill.wat').innerHTML = `<span class="dot"></span>${counts.watch} watch`;

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
      document.querySelector('.events-card tbody').innerHTML = events.map(e => `<tr><td class="muted">${escapeHtml(e.date || '')}</td><td>${escapeHtml(e.description)}</td><td class="amount ${e.amount >= 0 ? 'pos' : 'neg'}">${fmt.signedMoney(e.amount)}</td></tr>`).join('');
      void positions;
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
    try {
      const data = await API.get('/cockpit');
      const ps = data.portfolio_summary || {};
      const kpis = document.querySelectorAll('.kpi-tile');
      kpis[0].querySelector('.kpi-value').textContent = fmt.money(ps.total_aum_usd);
      kpis[1].querySelector('.kpi-value').textContent = '$0.0M';
      kpis[2].querySelector('.kpi-value').textContent = fmt.money(data.var_result?.var_1d_95);
      kpis[3].querySelector('.kpi-value').textContent = fmt.num(((ps.liquidity_summary?.cash_on_hand_usd || 0) / Math.max(ps.liquidity_summary?.scheduled_outflows_usd || 1, 1)) * 3, 1);
      renderDonut(document.querySelector('.donut-svg'), document.querySelector('.legend'), ps.asset_class || []);
      const rows = normalizeList(data.risk_register);
      document.querySelector('.risk-table tbody').innerHTML = rows.map(item => `<tr><td><span class="sev-dot ${severityClass(item.severity)}"></span></td><td class="dim">${escapeHtml(item.kind || item.agent || 'Risk')}</td><td class="headline">${escapeHtml(item.headline || item.description || '')}</td><td class="reasoning">${escapeHtml(item.reasoning || item.rule || item.description || '')}</td></tr>`).join('');
      const stats = document.querySelectorAll('.var-stat .vs-value');
      if (stats[0]) stats[0].textContent = fmt.money(data.var_result?.var_1d_95);
      if (stats[1]) stats[1].textContent = fmt.money(data.var_result?.var_1d_99);
      if (stats[2]) stats[2].textContent = fmt.pct(Math.abs(data.var_result?.max_drawdown_1y || 0) * 100);
      if (stats[3]) stats[3].textContent = fmt.date(data.var_result?.worst_scenario_date);
    } catch (error) {
      toast(API.detail(error), 'error');
    }
  }

  async function initAssets() {
    if (!(await API.redirectIfUnauth())) return;
    try {
      const [{ snapshot, summary, positions }, cashflow] = await Promise.all([loadPortfolioSummary(), API.get('/liquidity?months=12')]);
      document.querySelector('.aum-value').textContent = fmt.money(snapshot.total_aum_usd);
      document.querySelector('.aum-date').textContent = `As of ${fmt.date(snapshot.created_at)} · ${snapshot.position_count} positions`;
      renderDonut(document.querySelector('.chart-wrap svg'), document.querySelector('.legend'), summary.asset_class || []);
      const total = Number(snapshot.total_aum_usd || 1);
      const grouped = (summary.asset_class || []).map(group => {
        const children = positions.filter(p => p.asset_class === group.label).slice(0, 6);
        return `<tr class="group-header"><td colspan="4">${escapeHtml(group.label)} - ${fmt.money(group.market_value_usd)} · ${fmt.pct(group.pct_of_portfolio)}</td></tr>` +
          children.map(p => `<tr><td>${escapeHtml(p.name || p.ticker)}</td><td class="muted">${escapeHtml(p.ticker)}</td><td class="num">${fmt.money(p.market_value_usd)}</td><td class="num">${fmt.pct((Number(p.market_value_usd || 0) / total) * 100)}</td></tr>`).join('');
      }).join('');
      document.querySelector('.table-card tbody').innerHTML = grouped || '<tr><td colspan="4">No positions loaded.</td></tr>';
      renderCashflow(document.querySelector('.cashflow-card svg'), cashflow.cash_flows || [], 760);
    } catch (error) {
      toast(API.detail(error), 'error');
    }
  }

  async function initBriefings() {
    if (!(await API.redirectIfUnauth())) return;
    const tbody = document.querySelector('table.list tbody');
    const banner = document.querySelector('.gen-banner');
    const count = document.querySelector('.table-head .uplabel');
    function render(items) {
      banner.style.display = items.some(b => b.status === 'generating') ? 'flex' : 'none';
      count.textContent = `${items.length} briefings`;
      tbody.innerHTML = items.map(b => `<tr data-id="${b.id}">
        <td style="font-weight:600;color:var(--ink);white-space:nowrap">${fmt.date(b.created_at)}</td>
        <td><span class="pill ${b.scope === 'full' ? 'accent' : 'mute'}">${escapeHtml(b.scope || 'full')}</span></td>
        <td class="version">v${b.version || 1}</td>
        <td class="summary">${escapeHtml(briefingSummary(b))}</td>
        <td><span class="ms sm" style="color:var(--ink-mute)">chevron_right</span></td>
      </tr>`).join('');
      tbody.querySelectorAll('tr[data-id]').forEach(row => row.addEventListener('click', () => {
        location.href = `briefing.html?id=${row.dataset.id}`;
      }));
    }
    async function load() {
      const payload = await API.get('/briefings');
      render(normalizeList(payload));
    }
    document.querySelector('.generate-bar .btn.primary')?.addEventListener('click', async () => {
      const scope = document.querySelector('#scope-seg button.on')?.dataset.value || 'full';
      try {
        await API.post('/briefings', { scope });
        toast('Briefing generated', 'success');
        await load();
      } catch (error) {
        toast(API.detail(error), 'error');
      }
    });
    try { await load(); } catch (error) { toast(API.detail(error), 'error'); }
  }

  async function initBriefing() {
    if (!(await API.redirectIfUnauth())) return;
    const id = new URLSearchParams(location.search).get('id');
    try {
      const briefing = id ? await API.get(`/briefings/${id}`) : normalizeList(await API.get('/briefings?limit=1'))[0];
      if (!briefing) return;
      document.querySelector('.briefing-title').textContent = briefing.week_label || `Briefing ${briefing.id}`;
      document.querySelector('.briefing-dateline').textContent = `Generated ${fmt.date(briefing.created_at)}`;
      document.querySelector('.briefing-meta .pill').textContent = `${briefing.scope || 'full'} briefing`;
      document.querySelector('.briefing-meta .pill.mute').textContent = `v${briefing.version || 1}`;
      document.querySelector('.briefing-body').innerHTML = briefingHtml(briefing);
      document.querySelector('.briefing-actions .btn.primary')?.addEventListener('click', () => window.print());
      document.querySelector('.briefing-actions .btn:not(.primary)')?.addEventListener('click', async () => {
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
    let positions = [];
    let total = 1;
    function renderRows(items) {
      positions = items;
      total = items.reduce((sum, p) => sum + Number(p.market_value_usd || 0), 0) || 1;
      document.querySelector('.row-count').textContent = `${items.length} positions`;
      tbody.innerHTML = items.map((p, i) => `<tr data-id="${p.id}">
        <td class="rownum">${i + 1}</td><td class="ticker">${escapeHtml(p.ticker)}</td><td data-field="name">${escapeHtml(p.name || '')}</td>
        <td data-field="asset_class"><span class="ac-badge">${escapeHtml(p.asset_class || '')}</span></td>
        <td class="num" data-field="quantity">${fmt.num(p.quantity, 2)}</td><td class="num" data-field="market_value_usd">${fmt.money(p.market_value_usd, 2)}</td>
        <td class="num">${fmt.pct(Number(p.market_value_usd || 0) / total * 100)}</td></tr>`).join('');
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
      renderRows(normalizeList(payload));
    }
    async function selectRow(id) {
      const p = positions.find(item => item.id === id);
      if (!p) return;
      tbody.querySelectorAll('tr').forEach(row => row.classList.toggle('sel', row.dataset.id === id));
      document.getElementById('detail-panel').style.display = 'flex';
      const title = document.querySelector('.ticker-big');
      const subtitle = document.querySelector('.sec-name');
      if (title) title.textContent = p.ticker;
      if (subtitle) subtitle.textContent = p.name || p.asset_class || '';
      const inputs = document.querySelectorAll('#detail-panel input');
      if (inputs[0]) inputs[0].value = fmt.num(p.quantity, 2);
      if (inputs[2]) inputs[2].value = fmt.money(p.market_value_usd, 2);
      if (inputs[3]) inputs[3].value = 'USD';
    }
    async function editCell(row, cell) {
      const field = cell.dataset.field;
      const current = positions.find(p => p.id === row.dataset.id);
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
    try { await load(); } catch (error) { toast(API.detail(error), 'error'); }
  }

  async function initDocuments() {
    if (!(await API.redirectIfUnauth())) return;
    const tbody = document.querySelector('table.list tbody');
    const drawer = document.getElementById('review-drawer');
    const backdrop = document.getElementById('review-drawer-backdrop');
    let activeDocumentId = null;
    async function load() {
      const docs = normalizeList(await API.get('/documents'));
      document.querySelector('.table-head .uplabel').textContent = `${docs.length} documents`;
      tbody.innerHTML = docs.map(d => `<tr data-id="${d.id}">
        <td>${escapeHtml(d.filename)}</td><td><span class="ftype-ico ${d.file_type}"><span class="ms">${d.file_type === 'csv' ? 'table_view' : 'picture_as_pdf'}</span>${escapeHtml(d.file_type.toUpperCase())}</span></td>
        <td>${escapeHtml(d.folder || '')}</td><td><span class="pill ${d.extraction_status === 'approved' ? 'good' : d.extraction_status === 'failed' ? 'pri' : 'ele'}">${escapeHtml(d.extraction_status)}</span></td>
        <td class="muted">${fmt.date(d.created_at)}</td><td><button class="btn ghost" style="padding:4px 10px;font-size:11px">Review</button></td></tr>`).join('');
      tbody.querySelectorAll('tr[data-id]').forEach(row => row.addEventListener('click', () => review(row.dataset.id)));
    }
    async function review(id) {
      activeDocumentId = id;
      try {
        const data = await API.get(`/documents/${id}/fields`);
        drawer.classList.add('open');
        backdrop.classList.add('open');
        document.querySelector('.fields').innerHTML = (data.field_reviews || []).map(f => `<div class="extraction-field">
          <div class="ef-header"><span class="ef-label">${escapeHtml(f.field)}</span></div>
          <div class="ef-value">${escapeHtml(f.reason || '')}</div>
          <div class="ef-confidence"><div class="bar"><div class="fill ${f.confidence > .9 ? 'hi' : f.confidence > .7 ? 'mid' : 'lo'}" style="width:${Math.round((f.confidence || 0) * 100)}%"></div></div><span class="conf-pct">${Math.round((f.confidence || 0) * 100)}%</span></div>
          <div class="ef-actions"><button class="ef-btn approve" data-field="${escapeHtml(f.field)}"><span class="ms">check</span>${f.resolved ? ' Approved' : ' Approve'}</button></div>
        </div>`).join('') || '<div class="muted">No review fields.</div>';
      } catch (error) {
        toast(API.detail(error), 'error');
      }
    }
    document.querySelector('.upload-zone')?.addEventListener('click', () => {
      const input = document.createElement('input');
      input.type = 'file';
      input.onchange = async () => {
        if (!input.files[0]) return;
        const body = new FormData();
        body.append('file', input.files[0]);
        try { const doc = await API.post('/documents/upload', body); await API.post(`/documents/${doc.id}/parse`, {}); toast('Document uploaded', 'success'); await load(); }
        catch (error) { toast(API.detail(error), 'error'); }
      };
      input.click();
    });
    document.querySelector('#review-drawer footer .btn.primary')?.addEventListener('click', async () => {
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
        buckets[i].querySelector('.fill').style.width = Math.max(4, value / total * 100) + '%';
      });
      document.querySelector('.rw-number').textContent = fmt.num((liquid / Math.max(summary.scheduled_outflows_usd || 1, 1)) * 3, 1);
      document.querySelector('.rw-basis').textContent = `${fmt.money(summary.cash_on_hand_usd)} cash on hand · ${fmt.money(summary.scheduled_outflows_usd)} scheduled outflows`;
      renderCashflow(document.querySelector('.cashflow-card svg, .ladder-card svg, svg[viewBox="0 0 820 160"]'), summary.cash_flows || [], 820);
      const events = [
        { date: summary.next_call_due_date, description: 'Next capital call', type: 'Outflow', source: 'Private markets', amount: -Number(summary.next_call_amount_usd || 0) },
        { date: 'Next 90 days', description: 'Expected distributions', type: 'Inflow', source: 'Private markets', amount: Number(summary.expected_distributions_usd || 0) },
        { date: 'Next 90 days', description: 'Scheduled outflows', type: 'Outflow', source: 'Portfolio commitments', amount: -Number(summary.scheduled_outflows_usd || 0) },
      ].filter(e => e.amount);
      document.querySelector('table.list tbody').innerHTML = events.map(e => `<tr><td style="font-weight:600;color:var(--ink);white-space:nowrap">${escapeHtml(e.date || '')}</td><td>${escapeHtml(e.description)}</td><td><span class="pill ${e.amount >= 0 ? 'good' : 'pri'}">${e.type}</span></td><td class="muted">${escapeHtml(e.source)}</td><td class="amount-cell ${e.amount >= 0 ? 'inflow' : 'outflow'}">${fmt.signedMoney(e.amount)}</td></tr>`).join('');
    } catch (error) {
      toast(API.detail(error), 'error');
    }
  }

  async function initSettings() {
    if (!(await API.redirectIfUnauth())) return;
    try {
      const [settings, keys, session] = await Promise.all([
        API.get('/settings'),
        API.get('/settings/api-keys'),
        API.get('/auth/me'),
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
        try { await API.put('/settings', { reporting_currency: workspaceInputs[1]?.value || 'USD' }); toast('Workspace settings saved', 'success'); }
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
    document.querySelector('.upload-zone')?.addEventListener('click', () => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.csv,text/csv';
      input.onchange = async () => {
        if (!input.files[0]) return;
        const body = new FormData();
        body.append('file', input.files[0]);
        try {
          const data = await API.post('/ingest/csv', body);
          document.querySelector('.fname').textContent = input.files[0].name;
          document.querySelector('.fmeta').textContent = `${data.position_count || 0} positions`;
          current = 2;
          render();
          document.getElementById('enrich-progress').style.width = '100%';
          setTimeout(() => { current = 3; render(); }, 900);
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
        document.getElementById('success').classList.add('visible');
      } catch (error) { toast(API.detail(error), 'error'); }
    });
    nextBtn?.addEventListener('click', () => { if (current < 3) { current += 1; render(); } });
    backBtn?.addEventListener('click', () => { if (current > 1) { current -= 1; render(); } });
    current = 1;
    render();
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

  document.addEventListener('DOMContentLoaded', () => {
    const path = location.pathname === '/' ? '/index.html' : location.pathname;
    const init = routes[path];
    if (init) init();
  });
})();
