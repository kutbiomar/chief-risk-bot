(function () {
  const STEP_LABELS = {
    workspace_created: 'Workspace created',
    portfolio_uploaded: 'Portfolio uploaded',
    enrichment_run: 'Market enrichment and VaR ready',
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

  function severityClass(value) {
    const normalized = String(value || '').toLowerCase();
    if (normalized === 'priority') return 'priority';
    if (normalized === 'elevated') return 'elevated';
    if (normalized === 'watch') return 'watch';
    return 'good';
  }

  function setStatus(node, message, tone) {
    if (!node) return;
    node.className = `mvp-notice${tone ? ` ${tone}` : ''}`;
    node.textContent = message;
    node.hidden = !message;
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
    if (workspace) workspace.textContent = 'ChiefRiskBot MVP';
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

  async function initIndex() {
    try {
      await getSession();
      window.location.href = 'cockpit.html';
    } catch {
      window.location.href = 'login.html';
    }
  }

  async function initLogin() {
    try {
      await getSession();
      window.location.href = getQueryParam('next') || 'cockpit.html';
      return;
    } catch {
      // stay on login
    }

    const form = document.getElementById('login-form');
    const totpWrap = document.getElementById('totp-wrap');
    const status = document.getElementById('login-status');
    const submit = document.getElementById('login-submit');
    let challenge = '';

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      setStatus(status, '', '');
      submit.disabled = true;
      try {
        if (challenge) {
          await api('/auth/totp/verify', {
            method: 'POST',
            body: {
              session_challenge: challenge,
              code: document.getElementById('totp-code').value.trim(),
            },
          });
        } else {
          const payload = {
            email: document.getElementById('email').value.trim(),
            password: document.getElementById('password').value,
          };
          const response = await api('/auth/login', { method: 'POST', body: payload });
          if (response.requires_totp) {
            challenge = response.session_challenge || '';
            totpWrap.hidden = false;
            setStatus(status, 'TOTP required. Use code 000000 in the current backend stub.', 'success');
            submit.textContent = 'Verify code';
            submit.disabled = false;
            return;
          }
        }

        await getSession();
        window.location.href = getQueryParam('next') || 'onboarding.html';
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

    async function refreshState() {
      const state = await api('/onboarding/state');
      stateNode.innerHTML = stepMarkup(state);
      stateMeta.textContent = `${state.completed_steps.length} of ${state.total_steps} steps complete`;
      if (!state.completed_steps.includes('workspace_created')) {
        await markOnboardingStep('workspace_created');
        return refreshState();
      }
      return state;
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
        await markOnboardingStep('enrichment_run');
        await refreshState();
        setStatus(status, `Portfolio uploaded. Snapshot ${response.snapshot_id} is now current.`, 'success');
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
        await api('/risk/run', { method: 'POST' });
        await markOnboardingStep('risk_run');
        await refreshState();
        setStatus(status, 'Risk analysis completed for the current snapshot.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    document.getElementById('generate-briefing').addEventListener('click', async () => {
      try {
        const briefing = await api('/briefings/generate', { method: 'POST' });
        await markOnboardingStep('briefing_generated');
        await refreshState();
        setStatus(status, `Briefing ${briefing.week_label} generated.`, 'success');
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
    const allocations = document.getElementById('cockpit-allocations');
    const contributions = document.getElementById('cockpit-contribs');
    const register = document.getElementById('cockpit-register');

    async function loadCockpit() {
      try {
        const body = await api('/cockpit');
        const summary = body.portfolio_summary;
        const varResult = body.var_result;
        const risks = body.risk_register || [];

        kpis.innerHTML = `
          <div class="mvp-kpi"><div class="uplabel">Total AUM</div><div class="value">${formatCurrency(summary.total_aum_usd)}</div><div class="meta">snapshot ${escapeHtml(body.snapshot_id.slice(0, 8))}</div></div>
          <div class="mvp-kpi"><div class="uplabel">1-Day VaR (95%)</div><div class="value">${formatCurrency(varResult.var_1d_95)}</div><div class="meta">${formatPct(varResult.model_coverage_pct, 0)} modeled coverage</div></div>
          <div class="mvp-kpi"><div class="uplabel">Liquidity</div><div class="value">${formatPct(summary.liquidity_score_pct, 1)}</div><div class="meta">T+1 estimate</div></div>
          <div class="mvp-kpi"><div class="uplabel">Active Risks</div><div class="value">${formatNumber(risks.length)}</div><div class="meta">${formatNumber(risks.filter((item) => item.severity === 'priority').length)} priority</div></div>
        `;

        allocations.innerHTML = summary.asset_class
          .map(
            (bucket) => `
              <div class="mvp-item">
                <div style="min-width:0">
                  <div class="mvp-item-title">${escapeHtml(bucket.label)}</div>
                  <div class="mvp-item-subtle">${bucket.position_count} positions</div>
                  <div class="mvp-bar">
                    <div class="mvp-bar-track"><div class="mvp-bar-fill" style="width:${Math.min(bucket.pct_of_portfolio, 100)}%"></div></div>
                    <div class="mvp-bar-meta">${formatPct(bucket.pct_of_portfolio, 1)}</div>
                  </div>
                </div>
                <div class="mvp-item-subtle">${formatCurrency(bucket.market_value_usd)}</div>
              </div>
            `
          )
          .join('');

        contributions.innerHTML = (varResult.position_contributions || [])
          .slice(0, 6)
          .map(
            (item) => `
              <div class="mvp-item">
                <div>
                  <div class="mvp-item-title">${escapeHtml(item.ticker)}</div>
                  <div class="mvp-item-subtle">${escapeHtml(item.method)}</div>
                </div>
                <div style="text-align:right">
                  <div class="mvp-item-title">${formatCurrency(item.contribution_usd)}</div>
                  <div class="mvp-item-subtle">${formatPct(item.contribution_pct, 1)}</div>
                </div>
              </div>
            `
          )
          .join('');

        register.innerHTML = risks.length
          ? risks
              .map(
                (item) => `
                  <tr>
                    <td><span class="mvp-pill ${severityClass(item.severity)}">${escapeHtml(item.severity)}</span></td>
                    <td>${escapeHtml(item.title || item.rule || 'Risk flag')}</td>
                    <td>${escapeHtml(item.ticker || 'Portfolio')}</td>
                    <td>${escapeHtml(item.description || item.headline || '')}</td>
                  </tr>
                `
              )
              .join('')
          : '<tr><td colspan="4" class="mvp-empty">No risk flags yet. Run analysis to populate the register.</td></tr>';

        setStatus(status, `Cockpit refreshed for snapshot ${body.snapshot_id}.`, 'success');
      } catch (error) {
        kpis.innerHTML = '';
        allocations.innerHTML = '';
        contributions.innerHTML = '';
        register.innerHTML = '<tr><td colspan="4" class="mvp-empty">No cockpit data available.</td></tr>';
        setStatus(status, error.message, 'error');
      }
    }

    document.getElementById('refresh-cockpit').addEventListener('click', loadCockpit);
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

    async function loadBriefings() {
      try {
        const response = await api('/briefings');
        const items = response.items || [];
        list.innerHTML = items.length
          ? items
              .map(
                (item) => `
                  <a class="mvp-card pad" href="briefing.html?id=${encodeURIComponent(item.id)}" style="display:block;color:inherit">
                    <div class="mvp-metadata">
                      <span class="mvp-pill ${item.status === 'published' ? 'good' : 'elevated'}">${escapeHtml(item.status)}</span>
                      <span>${escapeHtml(item.week_label)}</span>
                      <span>v${escapeHtml(item.version)}</span>
                    </div>
                    <h3 style="font-family:'Fraunces',serif;margin:12px 0 6px">${escapeHtml(item.output.headline || 'Weekly briefing')}</h3>
                    <p style="margin:0;color:var(--ink-soft);font-size:12px">${escapeHtml(briefingSummary(item.output))}</p>
                  </a>
                `
              )
              .join('')
          : '<div class="mvp-empty mvp-card">No briefings yet. Generate the first one from this page.</div>';
        setStatus(status, `${items.length} briefings loaded.`, 'success');
      } catch (error) {
        list.innerHTML = '<div class="mvp-empty mvp-card">Unable to load briefings.</div>';
        setStatus(status, error.message, 'error');
      }
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
    const user = await requireSession('briefings.html', ['Workspace', 'Briefings', 'Detail']);
    if (!user) return;

    const status = document.getElementById('briefing-status');
    const meta = document.getElementById('briefing-meta');
    const title = document.getElementById('briefing-title');
    const body = document.getElementById('briefing-body');
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
          <span>${escapeHtml(briefing.week_label)}</span>
          <span>Version ${escapeHtml(briefing.version)}</span>
        `;
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
        setStatus(status, `Loaded briefing ${briefing.week_label}.`, 'success');
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

    document.getElementById('export-briefing').addEventListener('click', async () => {
      try {
        const path = await api(`/briefings/${briefingId}/export/pdf`);
        setStatus(status, `Export written to ${path}`, 'success');
      } catch (error) {
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
    let selected = null;

    function setForm(position) {
      selected = position;
      formTitle.textContent = position ? `Edit ${position.ticker}` : 'Add position';
      deleteButton.disabled = !position;
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
      document.getElementById('form-notes').value = position?.notes || '';
    }

    async function loadPositions(selectId) {
      try {
        const response = await api('/portfolio/positions');
        snapshotMeta.textContent = `${response.total} positions · snapshot ${response.snapshot_id.slice(0, 8)}`;
        tableBody.innerHTML = response.items
          .map(
            (item) => `
              <tr data-id="${escapeHtml(item.id)}" class="${selectId === item.id || (!selectId && selected?.id === item.id) ? 'is-selected' : ''}">
                <td>${escapeHtml(item.ticker)}</td>
                <td>${escapeHtml(item.name || '')}</td>
                <td class="num">${formatNumber(item.quantity, 2)}</td>
                <td class="num">${formatCurrency(item.market_value_usd || 0)}</td>
                <td>${escapeHtml(item.asset_class)}</td>
                <td>${escapeHtml(item.custodian || '')}</td>
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

        setStatus(status, `Loaded ${response.total} positions.`, 'success');
      } catch (error) {
        tableBody.innerHTML = '<tr><td colspan="6" class="mvp-empty">Unable to load positions.</td></tr>';
        setStatus(status, error.message, 'error');
      }
    }

    document.getElementById('new-position').addEventListener('click', () => {
      tableBody.querySelectorAll('tr').forEach((node) => node.classList.remove('is-selected'));
      setForm(null);
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const basePayload = {
        name: document.getElementById('form-name').value.trim() || null,
        quantity: Number(document.getElementById('form-quantity').value || 0),
        market_value_usd: Number(document.getElementById('form-market-value').value || 0),
        asset_class: document.getElementById('form-asset-class').value,
        geo_region: document.getElementById('form-region').value.trim() || null,
        sector: document.getElementById('form-sector').value.trim() || null,
        market_segment: document.getElementById('form-segment').value.trim() || null,
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
      }
    });

    deleteButton.addEventListener('click', async () => {
      if (!selected) return;
      try {
        const response = await api(`/portfolio/positions/${selected.id}`, { method: 'DELETE' });
        setForm(null);
        await loadPositions(null);
        setStatus(status, `Position removed from snapshot ${response.snapshot_id}.`, 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
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
    let selectedId = '';

    async function loadExtraction(documentId) {
      try {
        return await api(`/documents/${documentId}/extraction`);
      } catch {
        return null;
      }
    }

    async function renderPreview(documentRecord) {
      if (!documentRecord) {
        preview.innerHTML = '<div class="mvp-empty">Select a document to inspect extraction results.</div>';
        return;
      }
      const extraction = documentRecord.extraction_result_id ? await loadExtraction(documentRecord.id) : null;
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
      `;
    }

    async function loadDocuments() {
      try {
        const response = await api('/documents');
        const items = response.items || [];
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
        setStatus(status, `${items.length} documents loaded.`, 'success');
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

    document.getElementById('parse-document').addEventListener('click', async () => {
      if (!selectedId) return;
      try {
        const response = await api(`/documents/${selectedId}/parse`, { method: 'POST' });
        setStatus(status, response.detail, 'success');
        await loadDocuments();
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    document.getElementById('approve-document').addEventListener('click', async () => {
      if (!selectedId) return;
      try {
        const response = await api(`/documents/${selectedId}/approve`, { method: 'POST' });
        setStatus(status, response.detail, 'success');
        await loadDocuments();
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
        await loadDocuments();
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
        await loadDocuments();
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
    formatNumber,
    formatPct,
    setStatus,
    escapeHtml,
  };
})();
