(function () {
  const PRIMARY_NAV = [
    { href: 'index.html',     page: 'index',     label: 'Home',        icon: 'home',           num: '01' },
    { href: 'assets.html',    page: 'assets',    label: 'Assets',      icon: 'pie_chart',      num: '02' },
    { href: 'cockpit.html',   page: 'cockpit',   label: 'Risk Cockpit',icon: 'monitoring',     num: '03' },
    { href: 'liquidity.html', page: 'liquidity', label: 'Liquidity',   icon: 'waterfall_chart',num: '04' },
    { href: 'briefings.html', page: 'briefings', label: 'Briefings',   icon: 'auto_stories',   num: '05' },
    { href: 'scenarios.html', page: 'scenarios', label: 'Scenarios',   icon: 'description',    num: '06' },
  ];

  const OPS_NAV = [
    { href: 'table.html',     page: 'table',     label: 'Positions',   icon: 'table_view' },
    { href: 'documents.html', page: 'documents', label: 'Documents',   icon: 'folder_open' },
    { href: 'settings.html',  page: 'settings',  label: 'Settings',    icon: 'tune' },
    { href: 'access.html',    page: 'access',    label: 'Access',      icon: 'key' },
  ];

  // Page-scope labels for the briefing drawer
  const PAGE_SCOPES = {
    index:     { scope: 'daily',    label: 'Full daily briefing — positions, risk, liquidity' },
    assets:    { scope: 'assets',   label: 'Assets — composition, valuation, projections' },
    cockpit:   { scope: 'risk',     label: 'Risk — regime, factor exposures, alerts' },
    liquidity: { scope: 'liquidity',label: 'Liquidity — cash position, flow ladder, stress' },
    scenarios: { scope: 'scenarios',label: 'Scenarios — selected stress impacts' },
    briefings: { scope: 'full',     label: 'Full briefing' },
    documents: { scope: 'full',     label: 'Full briefing' },
    table:     { scope: 'full',     label: 'Full briefing' },
    settings:  { scope: 'full',     label: 'Full briefing' },
    access:    { scope: 'full',     label: 'Full briefing' },
    onboarding:{ scope: 'full',     label: 'Full briefing' },
  };

  function buildSidebar(activePage) {
    const primaryLink = ({ href, page, label, icon, num }) => {
      const cls = page === activePage ? ' class="active"' : '';
      return `<a href="${href}"${cls}><span class="ms">${icon}</span>${label}<span class="nav-num">${num}</span></a>`;
    };
    const opsLink = ({ href, page, label, icon }) => {
      const cls = page === activePage ? ' class="active"' : '';
      return `<a href="${href}"${cls}><span class="ms">${icon}</span>${label}</a>`;
    };

    return `
      <nav class="sidebar" id="crb-sidebar">
        <div class="brand-row">
          <div class="logo">C</div>
          <div class="brand-name">ChiefRiskBot</div>
        </div>

        <div class="client" id="crb-client-widget">
          <div class="who">
            <small>Workspace</small>
            <b id="crb-menu-workspace">—</b>
          </div>
          <span class="ms">unfold_more</span>
        </div>

        <div class="nav">
          <div class="section">Analysis</div>
          ${PRIMARY_NAV.map(primaryLink).join('')}
          <div class="section">Operations</div>
          ${OPS_NAV.map(opsLink).join('')}
        </div>

        <button class="sidebar-cta" id="crb-gen-briefing" data-drawer-trigger>
          <span class="ms">edit_note</span>
          <span class="sidebar-cta-label">
            <span class="sidebar-cta-title">Generate briefing</span>
            <span class="sidebar-cta-meta">For this workspace</span>
          </span>
        </button>

        <div class="side-foot">
          <div class="avatar" id="crb-avatar" aria-label="Account">CR</div>
          <div style="flex:1;min-width:0">
            <div class="side-foot-name" id="crb-menu-name">Loading…</div>
            <div class="side-foot-role" id="crb-menu-role">Risk session</div>
          </div>
          <button class="iconbtn" id="mvp-logout" title="Sign out" aria-label="Sign out">
            <span class="ms">logout</span>
          </button>
        </div>
      </nav>
    `;
  }

  function buildMobileTopBar() {
    return `
      <div class="top" id="crb-mobile-topbar" style="display:none">
        <button class="hamburger" id="crb-hamburger" aria-label="Open navigation">
          <span class="ms">menu</span>
        </button>
        <a href="index.html" style="font-family:'Fraunces';font-weight:900;font-size:15px;letter-spacing:-.01em">
          ChiefRiskBot
        </a>
        <div style="flex:1"></div>
        <button class="btn primary" id="crb-gen-briefing-mobile" data-drawer-trigger style="padding:7px 12px;font-size:11px">
          <span class="ms">edit_note</span>Briefing
        </button>
      </div>
      <div class="sb-backdrop" id="crb-sb-backdrop"></div>
    `;
  }

  function buildDrawer(activePage) {
    const scopeInfo = PAGE_SCOPES[activePage] || { scope: 'full', label: 'Full briefing' };
    return `
      <div class="essay-drawer-backdrop" id="crb-drawer-backdrop"></div>
      <aside class="essay-drawer" id="crb-drawer" role="complementary" aria-label="Briefing generator">
        <div class="essay-drawer-head">
          <div>
            <div class="essay-drawer-eyebrow">Briefing generator</div>
            <div class="essay-drawer-title" id="crb-drawer-title">Generate briefing</div>
          </div>
          <button class="essay-drawer-close" id="crb-drawer-close" aria-label="Close">
            <span class="ms">close</span>
          </button>
        </div>
        <div class="essay-drawer-tabs">
          <button class="essay-drawer-tab active" data-tab="generate" id="crb-tab-generate">Generate</button>
          <button class="essay-drawer-tab" data-tab="history" id="crb-tab-history">History</button>
        </div>
        <div class="essay-drawer-body" id="crb-drawer-body">
          <div id="crb-drawer-generate-panel">
            <div class="essay-drawer-scope">
              <div class="essay-drawer-scope-label">Scope</div>
              <div id="crb-drawer-scope-desc">${scopeInfo.label}</div>
            </div>
            <button class="essay-drawer-cta" id="crb-drawer-generate-btn" data-scope="${scopeInfo.scope}">
              <span class="ms">auto_awesome</span>Generate
            </button>
            <div class="essay-drawer-progress" id="crb-drawer-progress" hidden></div>
            <div id="crb-drawer-result" hidden></div>
          </div>
          <div id="crb-drawer-history-panel" hidden>
            <div id="crb-drawer-history-list">
              <div style="color:rgba(27,43,94,.5);font-size:13px;padding:20px 0">Loading history…</div>
            </div>
          </div>
        </div>
      </aside>
    `;
  }

  // ── Mobile sidebar (off-canvas) ───────────────────────────────────────────
  function wireHamburger() {
    const hamburger = document.getElementById('crb-hamburger');
    const sidebar   = document.getElementById('crb-sidebar');
    const backdrop  = document.getElementById('crb-sb-backdrop');
    if (!hamburger || !sidebar || !backdrop) return;

    function openSidebar() {
      sidebar.classList.add('open');
      backdrop.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
    function closeSidebar() {
      sidebar.classList.remove('open');
      backdrop.classList.remove('open');
      document.body.style.overflow = '';
    }

    hamburger.addEventListener('click', openSidebar);
    backdrop.addEventListener('click', closeSidebar);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSidebar(); });

    // Show/hide top bar based on screen width
    const topbar = document.getElementById('crb-mobile-topbar');
    function syncMobile() {
      const isMobile = window.innerWidth <= 640;
      if (topbar) topbar.style.display = isMobile ? 'flex' : 'none';
      if (!isMobile) closeSidebar();
    }
    syncMobile();
    window.addEventListener('resize', syncMobile);
  }

  // ── Avatar (visual element; logout handled by dedicated button) ───────────
  function wireAvatarMenu() { /* no-op — kept for API compat */ }

  // ── Briefing drawer ───────────────────────────────────────────────────────
  function wireDrawer() {
    const backdrop     = document.getElementById('crb-drawer-backdrop');
    const drawer       = document.getElementById('crb-drawer');
    const closeBtn     = document.getElementById('crb-drawer-close');
    const tabGenerate  = document.getElementById('crb-tab-generate');
    const tabHistory   = document.getElementById('crb-tab-history');
    const generatePanel= document.getElementById('crb-drawer-generate-panel');
    const historyPanel = document.getElementById('crb-drawer-history-panel');
    if (!backdrop || !drawer) return;

    function openDrawer() {
      backdrop.classList.add('open');
      drawer.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
    function closeDrawer() {
      backdrop.classList.remove('open');
      drawer.classList.remove('open');
      document.body.style.overflow = '';
    }

    document.querySelectorAll('[data-drawer-trigger]').forEach((btn) => {
      btn.addEventListener('click', openDrawer);
    });
    if (closeBtn)  closeBtn.addEventListener('click', closeDrawer);
    backdrop.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDrawer(); });

    function switchTab(tab) {
      tabGenerate.classList.toggle('active', tab === 'generate');
      tabHistory.classList.toggle('active', tab === 'history');
      if (generatePanel) generatePanel.hidden = tab !== 'generate';
      if (historyPanel)  historyPanel.hidden  = tab !== 'history';
      if (tab === 'history') loadHistory();
    }

    if (tabGenerate) tabGenerate.addEventListener('click', () => switchTab('generate'));
    if (tabHistory)  tabHistory.addEventListener('click',  () => switchTab('history'));

    window.CRBDrawer = { open: openDrawer, close: closeDrawer, switchTab };
  }

  async function loadHistory() {
    const list = document.getElementById('crb-drawer-history-list');
    if (!list) return;
    try {
      const data = await (window.CRBApi
        ? window.CRBApi('/briefings')
        : window.CRBMvp?.api('/briefings'));
      const briefings = Array.isArray(data) ? data : (data.briefings || []);
      if (!briefings.length) {
        list.innerHTML = '<div style="color:rgba(27,43,94,.5);font-size:13px;padding:20px 0">No briefings yet. Generate one above.</div>';
        return;
      }
      list.innerHTML = briefings.slice(0, 20).map((b) => `
        <a href="briefing.html?id=${encodeURIComponent(b.id)}" class="essay-drawer-history-item">
          <div class="essay-drawer-history-item-date">${new Date(b.created_at || b.date || '').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</div>
          <div class="essay-drawer-history-item-title">${escHtml(b.title || b.headline || 'Briefing')}</div>
        </a>`).join('');
    } catch {
      list.innerHTML = '<div style="color:rgba(185,28,28,.7);font-size:13px;padding:20px 0">Could not load briefing history.</div>';
    }
  }

  function escHtml(v) {
    return String(v ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── Public API ────────────────────────────────────────────────────────────
  window.CRBMvpShell = {
    mount(activePage) {
      const root = document.getElementById('app-root');
      if (!root) return;

      // Inject sidebar as first child of .app grid
      root.insertAdjacentHTML('afterbegin', buildSidebar(activePage));

      // Inject mobile top bar + backdrop before the app root
      root.insertAdjacentHTML('beforebegin', buildMobileTopBar());

      // Briefing drawer + backdrop at end of body
      document.body.insertAdjacentHTML('beforeend', buildDrawer(activePage));

      // Wire everything
      wireHamburger();
      wireAvatarMenu();
      wireDrawer();
    },

    updateUser(user) {
      if (!user) return;
      const initials = ((user.display_name || user.email || 'CR')
        .split(/\s+/)
        .map((w) => w[0] || '')
        .join('')
        .slice(0, 2)
        .toUpperCase()) || 'CR';

      const avatarBtn = document.getElementById('crb-avatar');
      if (avatarBtn) avatarBtn.textContent = initials;

      const menuName = document.getElementById('crb-menu-name');
      if (menuName) menuName.textContent = user.display_name || user.email || '';

      const menuWs = document.getElementById('crb-menu-workspace');
      if (menuWs) menuWs.textContent = user.workspace_name || '—';
    },

    // Legacy compat
    updateCrumbs() {},
  };
})();
