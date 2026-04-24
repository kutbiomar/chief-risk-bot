(function () {
  const ANALYSIS_PAGES = ['index', 'assets', 'cockpit', 'liquidity', 'scenarios'];
  const OPS_PAGES = ['documents', 'table', 'positions', 'settings', 'access'];

  const PRIMARY_NAV = [
    { href: 'index.html', page: 'index', label: 'Home' },
    { href: 'assets.html', page: 'assets', label: 'Assets' },
    { href: 'cockpit.html', page: 'cockpit', label: 'Risk' },
    { href: 'liquidity.html', page: 'liquidity', label: 'Liquidity' },
    { href: 'scenarios.html', page: 'scenarios', label: 'Scenarios' },
  ];

  const OPS_NAV = [
    { href: 'documents.html', page: 'documents', label: 'Documents' },
    { href: 'table.html', page: 'table', label: 'Positions' },
    { href: 'access.html', page: 'access', label: 'Access' },
    { href: 'settings.html', page: 'settings', label: 'Settings' },
  ];

  // Page-scope labels for the briefing drawer
  const PAGE_SCOPES = {
    index: { scope: 'daily', label: 'Full daily briefing — positions, risk, liquidity' },
    assets: { scope: 'assets', label: 'Assets — composition, valuation, projections' },
    cockpit: { scope: 'risk', label: 'Risk — regime, factor exposures, alerts' },
    liquidity: { scope: 'liquidity', label: 'Liquidity — cash position, flow ladder, stress' },
    scenarios: { scope: 'scenarios', label: 'Scenarios — selected stress impacts' },
    documents: { scope: 'full', label: 'Full briefing' },
    table: { scope: 'full', label: 'Full briefing' },
    positions: { scope: 'full', label: 'Full briefing' },
    settings: { scope: 'full', label: 'Full briefing' },
  };

  function buildNav(activePage) {
    const isOps = OPS_PAGES.includes(activePage);

    const primaryLinks = PRIMARY_NAV.map(({ href, page, label }) => {
      const active = page === activePage ? ' class="active"' : '';
      return `<a href="${href}"${active}>${label}</a>`;
    }).join('');

    const opsSubnav = isOps ? `
      <div class="essay-subnav" id="crb-subnav">
        <div class="essay-subnav-inner">
          ${OPS_NAV.map(({ href, page, label }) => {
            const active = page === activePage ? ' class="active"' : '';
            return `<a href="${href}"${active}>${label}</a>`;
          }).join('')}
        </div>
      </div>` : '';

    return `
      <header class="essay-topnav" id="crb-topnav">
        <div class="essay-topnav-inner">
          <a href="index.html" class="essay-wordmark">ChiefRiskBot</a>
          <nav class="essay-nav-primary" id="crb-nav-primary">${primaryLinks}</nav>
          <div class="essay-nav-actions">
            <button class="essay-nav-btn" id="crb-gen-briefing" data-drawer-trigger>
              <span class="ms">edit_note</span>Generate briefing
            </button>
            <button class="essay-nav-avatar" id="crb-avatar" aria-label="Account menu" aria-expanded="false">CR</button>
          </div>
          <button class="essay-nav-hamburger" id="crb-hamburger" aria-label="Open menu">
            <span class="ms">menu</span>
          </button>
        </div>
        ${opsSubnav}
        <div class="essay-nav-mobile" id="crb-mobile-nav" hidden>
          <div class="essay-nav-mobile-inner">
            <div class="essay-nav-mobile-section">Analysis</div>
            ${PRIMARY_NAV.map(({ href, page, label }) => {
              const active = page === activePage ? ' class="active"' : '';
              return `<a href="${href}"${active}>${label}</a>`;
            }).join('')}
            <div class="essay-nav-mobile-section">Operations</div>
            ${OPS_NAV.map(({ href, page, label }) => {
              const active = page === activePage ? ' class="active"' : '';
              return `<a href="${href}"${active}>${label}</a>`;
            }).join('')}
          </div>
        </div>
      </header>
    `;
  }

  function buildAvatarMenu() {
    return `
      <div class="essay-avatar-menu" id="crb-avatar-menu" hidden>
        <div class="essay-avatar-menu-header">
          <div class="essay-avatar-menu-name" id="crb-menu-name">Loading…</div>
          <div class="essay-avatar-menu-ws" id="crb-menu-workspace"></div>
        </div>
        <a href="settings.html" class="essay-avatar-menu-item">
          <span class="ms">tune</span>Settings
        </a>
        <button class="essay-avatar-menu-item" id="mvp-logout">
          <span class="ms">logout</span>Sign out
        </button>
      </div>
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

  function wireHamburger() {
    const hamburger = document.getElementById('crb-hamburger');
    const mobileNav = document.getElementById('crb-mobile-nav');
    if (!hamburger || !mobileNav) return;

    hamburger.addEventListener('click', () => {
      const open = !mobileNav.hidden;
      mobileNav.hidden = open;
      hamburger.setAttribute('aria-expanded', String(!open));
    });

    mobileNav.querySelectorAll('a').forEach((a) =>
      a.addEventListener('click', () => { mobileNav.hidden = true; })
    );
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') mobileNav.hidden = true;
    });
  }

  function wireAvatarMenu() {
    const avatarBtn = document.getElementById('crb-avatar');
    const menu = document.getElementById('crb-avatar-menu');
    if (!avatarBtn || !menu) return;

    avatarBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const open = !menu.hidden;
      menu.hidden = open;
      avatarBtn.setAttribute('aria-expanded', String(!open));
    });

    document.addEventListener('click', (e) => {
      if (!menu.contains(e.target) && e.target !== avatarBtn) {
        menu.hidden = true;
        avatarBtn.setAttribute('aria-expanded', 'false');
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        menu.hidden = true;
        avatarBtn.setAttribute('aria-expanded', 'false');
      }
    });
  }

  function wireDrawer() {
    const backdrop = document.getElementById('crb-drawer-backdrop');
    const drawer = document.getElementById('crb-drawer');
    const trigger = document.getElementById('crb-gen-briefing');
    const closeBtn = document.getElementById('crb-drawer-close');
    const tabGenerate = document.getElementById('crb-tab-generate');
    const tabHistory = document.getElementById('crb-tab-history');
    const generatePanel = document.getElementById('crb-drawer-generate-panel');
    const historyPanel = document.getElementById('crb-drawer-history-panel');
    if (!backdrop || !drawer) return;

    function open() {
      backdrop.classList.add('open');
      drawer.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
    function close() {
      backdrop.classList.remove('open');
      drawer.classList.remove('open');
      document.body.style.overflow = '';
    }

    if (trigger) trigger.addEventListener('click', open);
    if (closeBtn) closeBtn.addEventListener('click', close);
    backdrop.addEventListener('click', close);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });

    function switchTab(tab) {
      tabGenerate.classList.toggle('active', tab === 'generate');
      tabHistory.classList.toggle('active', tab === 'history');
      generatePanel.hidden = tab !== 'generate';
      historyPanel.hidden = tab !== 'history';
      if (tab === 'history') loadHistory();
    }

    if (tabGenerate) tabGenerate.addEventListener('click', () => switchTab('generate'));
    if (tabHistory) tabHistory.addEventListener('click', () => switchTab('history'));

    // Expose drawer API for _app.js to wire generate + history
    window.CRBDrawer = { open, close, switchTab };
  }

  async function loadHistory() {
    const list = document.getElementById('crb-drawer-history-list');
    if (!list) return;
    try {
      const data = await (window.CRBApi ? window.CRBApi('/briefings') : fetch('/api/briefings').then((r) => r.json()));
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

  window.CRBMvpShell = {
    mount(activePage) {
      const root = document.getElementById('app-root');
      if (!root) return;

      // Switch app container to full-width editorial layout
      root.classList.add('editorial');
      document.body.classList.add('essay-mode');

      // Inject editorial nav before the app root
      root.insertAdjacentHTML('beforebegin', buildNav(activePage));

      // Avatar menu anchored relative to the avatar button
      const actionsEl = document.querySelector('.essay-nav-actions');
      if (actionsEl) {
        actionsEl.style.position = 'relative';
        actionsEl.insertAdjacentHTML('beforeend', buildAvatarMenu());
      }

      // Briefing drawer + backdrop at end of body
      document.body.insertAdjacentHTML('beforeend', buildDrawer(activePage));

      // Wire interactions
      wireHamburger();
      wireAvatarMenu();
      wireDrawer();
    },

    updateUser(user) {
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
      if (menuWs) menuWs.textContent = user.workspace_name || '';
    },

    // Legacy compat — _app.js calls mount(activePage, crumbs); crumbs ignored
    updateCrumbs() {},
  };
})();
