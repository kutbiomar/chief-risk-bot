(function () {
  const page = document.body.dataset.page || '';

  function qs(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function formatCurrency(value, currency = 'USD', digits = 0) {
    const number = Number(value || 0);
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
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

  function getCookie(name) {
    const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`));
    return match ? decodeURIComponent(match[1]) : '';
  }

  function setStatus(node, message, tone = '') {
    if (!node) return;
    node.hidden = !message;
    node.className = `notice${tone ? ` ${tone}` : ''}`;
    node.textContent = message || '';
  }

  function redirectToLogin() {
    if (page !== 'login') {
      window.location.href = 'login.html';
    }
  }

  function severityClass(value) {
    const normalized = String(value || '').toLowerCase();
    if (normalized === 'critical') return 'critical';
    if (normalized === 'high' || normalized === 'elevated') return 'high';
    if (normalized === 'watch') return 'watch';
    if (normalized === 'info') return 'info';
    return 'good';
  }

  async function api(path, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = new Headers(options.headers || {});
    let body = options.body;

    if (options.formData) {
      body = options.formData;
    } else if (body !== undefined && !(body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    if (headers.get('Content-Type') === 'application/json' && body !== undefined) {
      body = JSON.stringify(body);
    }

    if (method !== 'GET') {
      const csrf = getCookie('__crb_csrf');
      if (csrf && !headers.has('X-CSRF-Token')) {
        headers.set('X-CSRF-Token', csrf);
      }
    }

    const response = await fetch(path.startsWith('/api') ? path : `/api${path}`, {
      method,
      body,
      headers,
      credentials: 'include',
    });
    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json') ? await response.json() : await response.text();
    if (response.status === 401) {
      redirectToLogin();
    }
    if (!response.ok) {
      const detail = typeof payload === 'object' && payload && payload.detail
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
    if (response.status === 401) {
      redirectToLogin();
      throw new Error('Not authenticated');
    }
    if (!response.ok) throw new Error(`Download failed (${response.status})`);
    const blob = await response.blob();
    const disposition = response.headers.get('content-disposition') || '';
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const filename = match ? match[1] : fallbackName;
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function getSession() {
    return api('/auth/session');
  }

  async function requireSession() {
    try {
      const session = await getSession();
      mountShell(session.user);
      return session.user;
    } catch (error) {
      redirectToLogin();
      return null;
    }
  }

  function mountShell(user) {
    const shell = qs('app-shell');
    if (!shell || shell.dataset.mounted === 'true') return;
    shell.dataset.mounted = 'true';
    const nav = `
      <aside class="app-nav">
        <div class="brand">
          <div class="brand-mark">C</div>
          <div>
            <h1>ChiefRiskBot</h1>
            <p>Private market intelligence for Monday morning decisions.</p>
          </div>
        </div>
        <nav class="nav-list">
          <a class="nav-link ${page === 'onboarding' ? 'is-active' : ''}" href="onboarding.html">Onboarding</a>
          <a class="nav-link ${page === 'portfolio' ? 'is-active' : ''}" href="portfolio.html">Portfolio</a>
          <a class="nav-link ${page === 'cockpit' ? 'is-active' : ''}" href="cockpit.html">Cockpit</a>
          <a class="nav-link ${page === 'holdings' ? 'is-active' : ''}" href="holdings.html">Holdings</a>
          <a class="nav-link ${page === 'liquidity' ? 'is-active' : ''}" href="liquidity.html">Liquidity</a>
          <a class="nav-link ${page === 'documents' ? 'is-active' : ''}" href="documents.html">Documents</a>
          <a class="nav-link ${page === 'briefings' ? 'is-active' : ''}" href="briefings.html">Briefings</a>
        </nav>
        <div class="nav-meta">
          <div><strong>${escapeHtml(user.display_name || user.email)}</strong></div>
          <div>${escapeHtml(user.role)} · ${escapeHtml(user.workspace_name || user.workspace_id)}</div>
          <button class="btn secondary" id="logout-button" type="button">Log out</button>
        </div>
      </aside>
    `;
    shell.insertAdjacentHTML('afterbegin', nav);
    const logout = qs('logout-button');
    if (logout) {
      logout.addEventListener('click', async () => {
        try {
          await api('/auth/logout', { method: 'POST' });
        } catch (_) {
          // ignore
        }
        window.location.href = 'login.html';
      });
    }
  }

  function renderEmpty(message) {
    return `<div class="empty">${escapeHtml(message)}</div>`;
  }

  async function initLogin() {
    try {
      await getSession();
      window.location.href = 'cockpit.html';
      return;
    } catch (_) {
      // stay on login
    }

    const form = qs('login-form');
    const status = qs('login-status');
    const totpWrap = qs('totp-wrap');
    let challenge = '';

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      setStatus(status, '');
      try {
        if (challenge) {
          await api('/auth/totp/verify', {
            method: 'POST',
            body: {
              session_challenge: challenge,
              code: qs('totp-code').value.trim(),
            },
          });
        } else {
          const response = await api('/auth/login', {
            method: 'POST',
            body: {
              email: qs('email').value.trim(),
              password: qs('password').value,
            },
          });
          if (response.requires_totp) {
            challenge = response.session_challenge || '';
            totpWrap.hidden = false;
            setStatus(status, 'TOTP required. Use code 000000 in the current stub.', 'success');
            return;
          }
        }
        window.location.href = 'cockpit.html';
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });
  }

  async function initOnboarding() {
    const user = await requireSession();
    if (!user) return;
    const status = qs('onboarding-status');
    const fundForm = qs('fund-form');
    const callForm = qs('call-form');

    fundForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      setStatus(status, '');
      try {
        const fund = await api('/portfolio/funds', {
          method: 'POST',
          body: {
            name: qs('fund-name').value.trim(),
            type: qs('fund-type').value,
            manager_name: qs('manager-name').value.trim(),
            currency: qs('fund-currency').value,
            jurisdiction: qs('fund-jurisdiction').value.trim() || null,
          },
        });
        await api('/portfolio/commitments', {
          method: 'POST',
          body: {
            fund_id: fund.id,
            committed_amount: qs('commitment-amount').value || '0',
            commitment_currency: qs('fund-currency').value,
            committed_amount_base: qs('commitment-amount').value || '0',
            uncalled_capital: qs('commitment-amount').value || '0',
            uncalled_capital_base: qs('commitment-amount').value || '0',
          },
        });
        setStatus(status, 'Fund and starting commitment created.', 'success');
        fundForm.reset();
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    callForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      setStatus(status, '');
      try {
        const funds = await api('/portfolio/funds');
        const fund = funds.items.find((item) => item.name === qs('call-fund').value.trim()) || funds.items[0];
        if (!fund) throw new Error('Create a fund first.');
        await api('/portfolio/capital-events', {
          method: 'POST',
          body: {
            fund_id: fund.id,
            type: 'call',
            amount: qs('call-amount').value || '0',
            amount_base: qs('call-amount').value || '0',
            currency: 'USD',
            due_date: qs('call-date').value || null,
            is_confirmed: true,
          },
        });
        setStatus(status, 'Capital call recorded.', 'success');
        callForm.reset();
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });
  }

  async function initCockpit() {
    const user = await requireSession();
    if (!user) return;
    const status = qs('cockpit-status');
    const refresh = qs('refresh-cockpit');

    async function render() {
      try {
        setStatus(status, '');
        const [summary, liquidity, alerts, deals] = await Promise.all([
          api('/portfolio/summary'),
          api('/portfolio/liquidity'),
          api('/alerts'),
          api('/deals'),
        ]);

        qs('cockpit-kpis').innerHTML = `
          <div class="kpi"><div class="kpi-label">Committed</div><div class="kpi-value">${formatCurrency(summary.total_committed_base)}</div><div class="kpi-meta">Across active commitments</div></div>
          <div class="kpi"><div class="kpi-label">Called</div><div class="kpi-value">${formatCurrency(summary.total_called_base)}</div><div class="kpi-meta">Capital already funded</div></div>
          <div class="kpi"><div class="kpi-label">Uncalled</div><div class="kpi-value">${formatCurrency(summary.total_uncalled_base)}</div><div class="kpi-meta">Future liquidity demand</div></div>
          <div class="kpi"><div class="kpi-label">Open Alerts</div><div class="kpi-value">${formatNumber(alerts.total)}</div><div class="kpi-meta">${deals.total} pipeline deals tracked</div></div>
        `;

        const byType = summary.by_fund_type || [];
        const peak = Math.max(...byType.map((item) => Number(item.value_base || 0)), 1);
        qs('cockpit-allocation').innerHTML = byType.length ? `
          <div class="bar-stack">
            ${byType.map((item) => `
              <div class="bar-row">
                <div class="bar-label">${escapeHtml(item.label)}</div>
                <div class="bar-track"><div class="bar-fill" style="width:${(Number(item.value_base || 0) / peak) * 100}%"></div></div>
                <div class="bar-value">${formatCurrency(item.value_base)}</div>
              </div>
            `).join('')}
          </div>
        ` : renderEmpty('No fund data yet.');

        qs('cockpit-calls').innerHTML = (summary.upcoming_calls || []).length ? `
          <div class="list">
            ${summary.upcoming_calls.slice(0, 6).map((item) => `
              <div class="item">
                <div>
                  <div class="item-title">${escapeHtml(item.type)} · ${escapeHtml(item.due_date || 'TBD')}</div>
                  <div class="item-subtle">Fund ${escapeHtml(item.fund_id)} · confirmed ${item.is_confirmed ? 'yes' : 'no'}</div>
                </div>
                <div class="item-title">${formatCurrency(item.amount_base)}</div>
              </div>
            `).join('')}
          </div>
        ` : renderEmpty('No upcoming capital calls found.');

        qs('cockpit-alerts').innerHTML = alerts.items.length ? `
          <div class="list">
            ${alerts.items.slice(0, 6).map((item) => `
              <div class="item">
                <div>
                  <div class="item-title">${escapeHtml(item.message)}</div>
                  <div class="item-subtle">${escapeHtml(item.rule)} · ${escapeHtml(item.entity_type)}</div>
                </div>
                <span class="pill ${severityClass(item.severity)}">${escapeHtml(item.severity)}</span>
              </div>
            `).join('')}
          </div>
        ` : renderEmpty('No active alerts.');

        qs('cockpit-liquidity').innerHTML = (liquidity.monthly_buckets || []).length ? `
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr><th>Month</th><th class="num">Inflows</th><th class="num">Outflows</th><th class="num">Net</th><th class="num">Cumulative</th></tr>
              </thead>
              <tbody>
                ${liquidity.monthly_buckets.slice(0, 8).map((item) => `
                  <tr>
                    <td>${escapeHtml(item.month)}</td>
                    <td class="num">${formatCurrency(item.inflows)}</td>
                    <td class="num">${formatCurrency(item.outflows)}</td>
                    <td class="num">${formatCurrency(item.net)}</td>
                    <td class="num">${formatCurrency(item.cumulative)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        ` : renderEmpty('Liquidity ladder will appear once commitments and capital events exist.');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    }

    refresh.addEventListener('click', render);
    render();
  }

  async function initDocuments() {
    const user = await requireSession();
    if (!user) return;
    const status = qs('documents-status');
    const uploadForm = qs('upload-form');
    let selectedDocumentId = null;

    async function refreshList() {
      const documents = await api('/documents');
      qs('documents-list').innerHTML = documents.items.length ? `
        <div class="list">
          ${documents.items.map((item) => `
            <div class="item">
              <div>
                <div class="item-title"><button class="btn secondary doc-select" data-id="${escapeHtml(item.id)}" type="button">${escapeHtml(item.filename)}</button></div>
                <div class="item-subtle">${escapeHtml(item.auto_category)} · ${escapeHtml(item.processing_status)}</div>
              </div>
              <span class="pill ${item.needs_review ? 'watch' : 'good'}">${item.needs_review ? 'review' : 'ready'}</span>
            </div>
          `).join('')}
        </div>
      ` : renderEmpty('No documents uploaded yet.');

      document.querySelectorAll('.doc-select').forEach((button) => {
        button.addEventListener('click', () => {
          selectedDocumentId = button.dataset.id;
          renderDetail().catch((error) => setStatus(status, error.message, 'error'));
        });
      });
    }

    async function renderDetail() {
      if (!selectedDocumentId) {
        qs('document-detail').innerHTML = renderEmpty('Select a document to inspect extraction and reconciliation.');
        return;
      }
      const [documentRecord, extraction, reconcile] = await Promise.all([
        api(`/documents/${selectedDocumentId}`),
        api(`/documents/${selectedDocumentId}/extraction`).catch(() => null),
        api(`/documents/${selectedDocumentId}/reconcile`).catch(() => ({ items: [] })),
      ]);

      qs('document-detail').innerHTML = `
        <div class="briefing-output">
          <div>
            <h4>${escapeHtml(documentRecord.filename)}</h4>
            <div class="muted">${escapeHtml(documentRecord.auto_category)} · ${escapeHtml(documentRecord.processing_status)}</div>
          </div>
          <div>
            <strong>Extraction</strong>
            <div class="muted" style="margin-bottom:8px">Classifier confidence: ${escapeHtml(String(extraction ? extraction.classification_confidence || 'n/a' : 'n/a'))}</div>
            <pre>${escapeHtml(JSON.stringify(extraction ? extraction.extracted_json : {}, null, 2))}</pre>
          </div>
          <div>
            <strong>Field confidence</strong>
            <pre>${escapeHtml(JSON.stringify(extraction ? extraction.confidence_json : {}, null, 2))}</pre>
          </div>
          <div>
            <strong>Reconciliation</strong>
            ${reconcile.items && reconcile.items.length ? `
              <div class="list">
                ${reconcile.items.map((item) => `
                  <div class="item">
                    <div>
                      <div class="item-title">${escapeHtml(item.field_name)}</div>
                      <div class="item-subtle">Document: ${escapeHtml(item.document_value || 'n/a')} · System: ${escapeHtml(item.system_value || 'n/a')}</div>
                    </div>
                    <span class="pill ${severityClass(item.severity)}">${escapeHtml(item.severity)}</span>
                  </div>
                `).join('')}
              </div>
            ` : '<div class="muted">No reconciliation flags.</div>'}
          </div>
        </div>
      `;
    }

    uploadForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      setStatus(status, '');
      const fileInput = qs('document-file');
      const file = fileInput.files[0];
      if (!file) {
        setStatus(status, 'Choose a file first.', 'error');
        return;
      }
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('provider_name', qs('provider-name').value.trim());
        const uploaded = await api('/documents/upload', { method: 'POST', formData });
        selectedDocumentId = uploaded.id;
        await api(`/documents/${selectedDocumentId}/parse`, { method: 'POST' });
        await refreshList();
        await renderDetail();
        setStatus(status, 'Document uploaded and parsed.', 'success');
        uploadForm.reset();
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    qs('resolve-reconcile').addEventListener('click', async () => {
      if (!selectedDocumentId) {
        setStatus(status, 'Select a document first.', 'error');
        return;
      }
      try {
        const flags = await api(`/documents/${selectedDocumentId}/reconcile`);
        if (!flags.items.length) {
          setStatus(status, 'No open flags to resolve.', 'success');
          return;
        }
        await api(`/documents/${selectedDocumentId}/reconcile`, {
          method: 'POST',
          body: {
            flag_ids: flags.items.map((item) => item.id),
            action: 'resolved',
            notes: 'Resolved from MVP2 frontend stub',
          },
        });
        await refreshList();
        await renderDetail();
        setStatus(status, 'Reconciliation flags resolved.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    qs('parse-selected').addEventListener('click', async () => {
      if (!selectedDocumentId) {
        setStatus(status, 'Select a document first.', 'error');
        return;
      }
      try {
        await api(`/documents/${selectedDocumentId}/parse`, { method: 'POST' });
        await refreshList();
        await renderDetail();
        setStatus(status, 'Document parsed.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    qs('reopen-reconcile').addEventListener('click', async () => {
      if (!selectedDocumentId) {
        setStatus(status, 'Select a document first.', 'error');
        return;
      }
      try {
        const flags = await api(`/documents/${selectedDocumentId}/reconcile`);
        if (!flags.items.length) {
          setStatus(status, 'No reconciliation flags to reopen.', 'error');
          return;
        }
        await api(`/documents/${selectedDocumentId}/reconcile`, {
          method: 'POST',
          body: {
            flag_ids: flags.items.map((item) => item.id),
            action: 'reopen',
            notes: 'Re-opened from MVP2 frontend stub',
          },
        });
        await refreshList();
        await renderDetail();
        setStatus(status, 'Reconciliation flags reopened.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    refreshList().catch((error) => setStatus(status, error.message, 'error'));
    renderDetail();
  }

  async function initPortfolio() {
    const user = await requireSession();
    if (!user) return;
    const status = qs('portfolio-status');

    async function refresh() {
      try {
        setStatus(status, '');
        const [funds, commitments, deals, events] = await Promise.all([
          api('/portfolio/funds'),
          api('/portfolio/commitments'),
          api('/deals'),
          api('/portfolio/capital-events'),
        ]);

        const fundSelect = qs('portfolio-commitment-fund');
        const fundOptions = funds.items.length
          ? funds.items.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join('')
          : '<option value="">Create a fund first</option>';
        fundSelect.innerHTML = fundOptions;
        qs('portfolio-event-fund').innerHTML = fundOptions;

        const commitmentMap = new Map();
        commitments.items.forEach((item) => {
          if (!commitmentMap.has(item.fund_id)) commitmentMap.set(item.fund_id, []);
          commitmentMap.get(item.fund_id).push(item);
        });

        qs('portfolio-funds-table').innerHTML = funds.items.length ? `
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th>Fund</th>
                  <th>Manager</th>
                  <th>Type</th>
                  <th>Currency</th>
                  <th class="num">Committed</th>
                  <th class="num">Called</th>
                  <th class="num">Uncalled</th>
                </tr>
              </thead>
              <tbody>
                ${funds.items.map((fund) => {
                  const linked = commitmentMap.get(fund.id) || [];
                  const committed = linked.reduce((sum, item) => sum + Number(item.committed_amount_base || item.committed_amount || 0), 0);
                  const called = linked.reduce((sum, item) => sum + Number(item.called_capital_base || item.called_capital || 0), 0);
                  const uncalled = linked.reduce((sum, item) => sum + Number(item.uncalled_capital_base || item.uncalled_capital || 0), 0);
                  return `
                    <tr>
                      <td>${escapeHtml(fund.name)}</td>
                      <td>${escapeHtml(fund.manager_name)}</td>
                      <td>${escapeHtml(fund.type)}</td>
                      <td>${escapeHtml(fund.currency)}</td>
                      <td class="num">${formatCurrency(committed)}</td>
                      <td class="num">${formatCurrency(called)}</td>
                      <td class="num">${formatCurrency(uncalled)}</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        ` : renderEmpty('No funds created yet.');

        qs('portfolio-deals-table').innerHTML = deals.items.length ? `
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Stage</th>
                  <th class="num">Target</th>
                  <th>Close Date</th>
                </tr>
              </thead>
              <tbody>
                ${deals.items.map((deal) => `
                  <tr>
                    <td>${escapeHtml(deal.name)}</td>
                    <td>${escapeHtml(deal.stage)}</td>
                    <td class="num">${formatCurrency(deal.target_commitment_base || deal.target_commitment || 0)}</td>
                    <td>${escapeHtml(deal.target_close_date || 'n/a')}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        ` : renderEmpty('No deals in the pipeline yet.');

        qs('portfolio-events-table').innerHTML = events.items.length ? `
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr><th>Type</th><th class="num">Amount</th><th>Date</th><th>Status</th></tr>
              </thead>
              <tbody>
                ${events.items.slice(0, 10).map((item) => `
                  <tr>
                    <td>${escapeHtml(item.type)}</td>
                    <td class="num">${formatCurrency(item.amount_base || item.amount || 0)}</td>
                    <td>${escapeHtml(item.due_date || item.effective_date || 'n/a')}</td>
                    <td>${escapeHtml(item.is_confirmed ? 'confirmed' : 'estimated')}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        ` : renderEmpty('No capital events recorded yet.');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    }

    qs('portfolio-fund-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      try {
        await api('/portfolio/funds', {
          method: 'POST',
          body: {
            name: qs('portfolio-fund-name').value.trim(),
            type: qs('portfolio-fund-type').value,
            manager_name: qs('portfolio-manager-name').value.trim(),
            currency: qs('portfolio-fund-currency').value,
            vintage_year: qs('portfolio-vintage-year').value ? Number(qs('portfolio-vintage-year').value) : null,
            jurisdiction: qs('portfolio-jurisdiction').value.trim() || null,
          },
        });
        qs('portfolio-fund-form').reset();
        await refresh();
        setStatus(status, 'Fund created.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    qs('portfolio-commitment-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      try {
        const amount = qs('portfolio-commitment-amount').value || '0';
        const called = qs('portfolio-called-capital').value || '0';
        const uncalled = qs('portfolio-uncalled-capital').value || '0';
        await api('/portfolio/commitments', {
          method: 'POST',
          body: {
            fund_id: qs('portfolio-commitment-fund').value,
            committed_amount: amount,
            commitment_currency: 'USD',
            committed_amount_base: amount,
            called_capital: called,
            called_capital_base: called,
            uncalled_capital: uncalled,
            uncalled_capital_base: uncalled,
            nav: qs('portfolio-nav').value || null,
            nav_base: qs('portfolio-nav').value || null,
            nav_date: qs('portfolio-nav-date').value || null,
          },
        });
        qs('portfolio-commitment-form').reset();
        await refresh();
        setStatus(status, 'Commitment added.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    qs('portfolio-deal-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      try {
        const amount = qs('portfolio-deal-amount').value || null;
        await api('/deals', {
          method: 'POST',
          body: {
            name: qs('portfolio-deal-name').value.trim(),
            stage: qs('portfolio-deal-stage').value,
            target_commitment: amount,
            target_commitment_base: amount,
            target_commitment_currency: amount ? 'USD' : null,
            target_close_date: qs('portfolio-deal-date').value || null,
          },
        });
        qs('portfolio-deal-form').reset();
        await refresh();
        setStatus(status, 'Deal added.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    qs('portfolio-capital-event-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      try {
        const amount = qs('portfolio-event-amount').value || '0';
        await api('/portfolio/capital-events', {
          method: 'POST',
          body: {
            fund_id: qs('portfolio-event-fund').value,
            type: qs('portfolio-event-type').value,
            amount,
            amount_base: amount,
            currency: 'USD',
            due_date: qs('portfolio-event-date').value || null,
            effective_date: qs('portfolio-event-date').value || null,
            is_confirmed: true,
          },
        });
        qs('portfolio-capital-event-form').reset();
        await refresh();
        setStatus(status, 'Capital event added.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    refresh();
  }

  async function initHoldings() {
    const user = await requireSession();
    if (!user) return;
    const status = qs('holdings-status');

    qs('holding-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      try {
        const value = qs('holding-value').value || null;
        await api('/portfolio/holdings', {
          method: 'POST',
          body: {
            asset_name: qs('holding-name').value.trim(),
            asset_type: qs('holding-type').value.trim(),
            geo_region: qs('holding-geo').value.trim() || null,
            sector: qs('holding-sector').value.trim() || null,
            currency: 'USD',
            current_value: value,
            current_value_base: value,
            current_value_date: qs('holding-date').value || null,
            current_value_source: 'manager_stated',
          },
        });
        qs('holding-form').reset();
        await render();
        setStatus(status, 'Holding added.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    async function render() {
      try {
        setStatus(status, '');
        const [holdings, summary] = await Promise.all([
          api('/portfolio/holdings'),
          api('/portfolio/summary'),
        ]);

        const totalValue = holdings.items.reduce((sum, item) => sum + Number(item.current_value_base || item.current_value || 0), 0);

        qs('holdings-kpis').innerHTML = `
          <div class="kpi"><div class="kpi-label">Holdings Count</div><div class="kpi-value">${formatNumber(holdings.total)}</div><div class="kpi-meta">Manual and extracted records</div></div>
          <div class="kpi"><div class="kpi-label">Approx Value</div><div class="kpi-value">${formatCurrency(totalValue)}</div><div class="kpi-meta">Using current base values when present</div></div>
          <div class="kpi"><div class="kpi-label">Fund Buckets</div><div class="kpi-value">${formatNumber((summary.by_fund_type || []).length)}</div><div class="kpi-meta">From current commitment mix</div></div>
          <div class="kpi"><div class="kpi-label">Unknown Sector</div><div class="kpi-value">${formatNumber(holdings.items.filter((item) => !item.sector).length)}</div><div class="kpi-meta">Needs classification cleanup</div></div>
        `;

        const groupBy = (key) => {
          const grouped = new Map();
          holdings.items.forEach((item) => {
            const label = item[key] || 'Unknown';
            const value = Number(item.current_value_base || item.current_value || 0);
            if (!grouped.has(label)) grouped.set(label, { label, value: 0, count: 0 });
            const bucket = grouped.get(label);
            bucket.value += value;
            bucket.count += 1;
          });
          return Array.from(grouped.values()).sort((a, b) => b.value - a.value);
        };

        function renderBars(targetId, buckets) {
          const peak = Math.max(...buckets.map((item) => item.value), 1);
          qs(targetId).innerHTML = buckets.length ? `
            <div class="bar-stack">
              ${buckets.map((item) => `
                <div class="bar-row">
                  <div class="bar-label">${escapeHtml(item.label)}</div>
                  <div class="bar-track"><div class="bar-fill" style="width:${(item.value / peak) * 100}%"></div></div>
                  <div class="bar-value">${formatCurrency(item.value)}</div>
                </div>
              `).join('')}
            </div>
          ` : renderEmpty('No holdings data yet.');
        }

        renderBars('holdings-asset-class', groupBy('asset_type').slice(0, 8));
        renderBars('holdings-geo', groupBy('geo_region').slice(0, 8));
        renderBars('holdings-sector', groupBy('sector').slice(0, 8));

        qs('holdings-table').innerHTML = holdings.items.length ? `
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th>Asset</th>
                  <th>Type</th>
                  <th>Geo</th>
                  <th>Sector</th>
                  <th class="num">Value</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                ${holdings.items.map((item) => `
                  <tr>
                    <td>${escapeHtml(item.asset_name)}</td>
                    <td>${escapeHtml(item.asset_type)}</td>
                    <td>${escapeHtml(item.geo_region || 'Unknown')}</td>
                    <td>${escapeHtml(item.sector || 'Unknown')}</td>
                    <td class="num">${formatCurrency(item.current_value_base || item.current_value || 0)}</td>
                    <td>${escapeHtml(item.current_value_date || 'n/a')}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        ` : renderEmpty('No holdings have been entered yet.');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    }

    qs('refresh-holdings').addEventListener('click', render);
    render();
  }

  async function initLiquidity() {
    const user = await requireSession();
    if (!user) return;
    const status = qs('liquidity-status');
    let currentScenario = 'base';

    async function render() {
      try {
        setStatus(status, '');
        const projection = await api(`/portfolio/liquidity?scenario=${encodeURIComponent(currentScenario)}`);
        const months = projection.monthly_buckets || [];
        const peakFlow = Math.max(...months.map((item) => Math.max(Math.abs(Number(item.inflows || 0)), Math.abs(Number(item.outflows || 0)))), 1);

        qs('liquidity-summary').innerHTML = `
          <div class="kpi"><div class="kpi-label">Scenario</div><div class="kpi-value">${escapeHtml(projection.scenario)}</div><div class="kpi-meta">${escapeHtml(projection.base_currency)} reporting currency</div></div>
          <div class="kpi"><div class="kpi-label">Months</div><div class="kpi-value">${formatNumber(projection.projection_months)}</div><div class="kpi-meta">Forward projection horizon</div></div>
          <div class="kpi"><div class="kpi-label">Liquidity Gaps</div><div class="kpi-value">${formatNumber(projection.liquidity_gaps.length)}</div><div class="kpi-meta">Months below configured buffer</div></div>
          <div class="kpi"><div class="kpi-label">Last Cumulative</div><div class="kpi-value">${formatCurrency(months.length ? months[months.length - 1].cumulative : 0)}</div><div class="kpi-meta">End-of-horizon position</div></div>
        `;

        qs('liquidity-chart').innerHTML = months.length ? `
          <div class="bar-stack">
            ${months.slice(0, 12).map((item) => `
              <div class="bar-row">
                <div class="bar-label">${escapeHtml(item.month)}</div>
                <div>
                  <div class="bar-track" style="margin-bottom:6px"><div class="bar-fill" style="width:${(Math.abs(Number(item.outflows || 0)) / peakFlow) * 100}%;background:linear-gradient(90deg,#8b3d2f,#c06f59)"></div></div>
                  <div class="bar-track"><div class="bar-fill" style="width:${(Math.abs(Number(item.inflows || 0)) / peakFlow) * 100}%;background:linear-gradient(90deg,#2f6a4f,#58a07b)"></div></div>
                </div>
                <div class="bar-value">${formatCurrency(item.net)}</div>
              </div>
            `).join('')}
          </div>
        ` : renderEmpty('Liquidity projection will appear once commitments and capital events exist.');

        qs('liquidity-gaps').innerHTML = projection.liquidity_gaps.length ? `
          <div class="list">
            ${projection.liquidity_gaps.map((item) => `
              <div class="item">
                <div>
                  <div class="item-title">${escapeHtml(item.month)}</div>
                  <div class="item-subtle">${escapeHtml(item.description)}</div>
                </div>
                <span class="pill critical">${formatCurrency(item.gap_amount)}</span>
              </div>
            `).join('')}
          </div>
        ` : renderEmpty('No liquidity gaps projected for this scenario.');

        qs('liquidity-table').innerHTML = months.length ? `
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr><th>Month</th><th class="num">Inflows</th><th class="num">Outflows</th><th class="num">Net</th><th class="num">Cumulative</th></tr>
              </thead>
              <tbody>
                ${months.map((item) => `
                  <tr>
                    <td>${escapeHtml(item.month)}</td>
                    <td class="num">${formatCurrency(item.inflows)}</td>
                    <td class="num">${formatCurrency(item.outflows)}</td>
                    <td class="num">${formatCurrency(item.net)}</td>
                    <td class="num">${formatCurrency(item.cumulative)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        ` : renderEmpty('No liquidity rows to display.');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    }

    document.querySelectorAll('[data-scenario]').forEach((button) => {
      button.addEventListener('click', () => {
        currentScenario = button.dataset.scenario;
        document.querySelectorAll('[data-scenario]').forEach((node) => node.classList.remove('primary'));
        button.classList.add('primary');
        render();
      });
    });

    render();
  }

  async function initBriefings() {
    const user = await requireSession();
    if (!user) return;
    const status = qs('briefings-status');
    let selectedBriefingId = null;

    async function refreshList() {
      const briefings = await api('/briefings');
      qs('briefings-list').innerHTML = briefings.items.length ? `
        <div class="list">
          ${briefings.items.map((item) => `
            <div class="item">
              <div>
                <div class="item-title"><button class="btn secondary briefing-select" data-id="${escapeHtml(item.id)}" type="button">${escapeHtml(item.week_label)} · v${escapeHtml(item.version)}</button></div>
                <div class="item-subtle">${escapeHtml(item.status)}</div>
              </div>
              <span class="pill ${item.status === 'published' ? 'good' : 'watch'}">${escapeHtml(item.status)}</span>
            </div>
          `).join('')}
        </div>
      ` : renderEmpty('No briefings generated yet.');

      document.querySelectorAll('.briefing-select').forEach((button) => {
        button.addEventListener('click', () => {
          selectedBriefingId = button.dataset.id;
          renderDetail().catch((error) => setStatus(status, error.message, 'error'));
        });
      });
    }

    async function renderDetail() {
      if (!selectedBriefingId) {
        qs('briefing-detail').innerHTML = renderEmpty('Generate or select a briefing to inspect it here.');
        return;
      }
      const briefing = await api(`/briefings/${selectedBriefingId}`);
      const output = briefing.output || {};
      qs('briefing-detail').innerHTML = `
        <div class="briefing-output">
          <div>
            <h4>${escapeHtml(briefing.week_label)} · version ${escapeHtml(briefing.version)}</h4>
            <div class="muted">${escapeHtml(briefing.status)}</div>
          </div>
          <div>
            <strong>Executive Summary</strong>
            <p>${escapeHtml(output.executive_summary || '')}</p>
          </div>
          <div>
            <strong>Sections</strong>
            ${(output.sections || []).map((section) => `<div class="check"><div class="check-index">•</div><div><strong>${escapeHtml(section.title)}</strong><div class="muted">${escapeHtml(section.body)}</div></div></div>`).join('') || '<div class="muted">No sections.</div>'}
          </div>
          <div>
            <strong>Recommendations</strong>
            ${(output.recommendations || []).map((item, index) => `<div class="check"><div class="check-index">${index + 1}</div><div>${escapeHtml(item)}</div></div>`).join('') || '<div class="muted">No recommendations.</div>'}
          </div>
        </div>
      `;
    }

    qs('generate-briefing').addEventListener('click', async () => {
      setStatus(status, '');
      try {
        const briefing = await api('/briefings/generate', { method: 'POST' });
        selectedBriefingId = briefing.id;
        await refreshList();
        await renderDetail();
        setStatus(status, 'Weekly briefing generated.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    qs('publish-briefing').addEventListener('click', async () => {
      if (!selectedBriefingId) {
        setStatus(status, 'Select a briefing first.', 'error');
        return;
      }
      try {
        await api(`/briefings/${selectedBriefingId}/publish`, { method: 'POST' });
        await refreshList();
        await renderDetail();
        setStatus(status, 'Briefing published.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    qs('export-briefing').addEventListener('click', async () => {
      if (!selectedBriefingId) {
        setStatus(status, 'Select a briefing first.', 'error');
        return;
      }
      try {
        await download(`/briefings/${selectedBriefingId}/export/pdf`, 'briefing-export');
        setStatus(status, 'Briefing export downloaded.', 'success');
      } catch (error) {
        setStatus(status, error.message, 'error');
      }
    });

    refreshList().catch((error) => setStatus(status, error.message, 'error'));
    renderDetail();
  }

  const initMap = {
    login: initLogin,
    onboarding: initOnboarding,
    portfolio: initPortfolio,
    cockpit: initCockpit,
    holdings: initHoldings,
    liquidity: initLiquidity,
    documents: initDocuments,
    briefings: initBriefings,
  };

  window.addEventListener('DOMContentLoaded', () => {
    const init = initMap[page];
    if (init) init();
  });
})();
