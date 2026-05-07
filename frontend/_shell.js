/* ChiefRiskBot — Shell JS
   Injects sidebar + topbar, wires responsive nav.
   Usage: Shell.mount(activeHref, crumbs)
   e.g.:  Shell.mount('cockpit.html', ['Risk Cockpit']) */

(function() {
  'use strict';

  const NAV = [
    { href: 'index.html',     icon: 'home',          label: 'Home' },
    { href: 'cockpit.html',   icon: 'crisis_alert',  label: 'Risk Cockpit' },
    { href: 'assets.html',    icon: 'pie_chart',     label: 'Assets' },
    { href: 'table.html',     icon: 'table_rows',    label: 'Positions' },
    { href: 'briefings.html', icon: 'description',   label: 'Briefings' },
    { href: 'documents.html', icon: 'folder_open',   label: 'Documents' },
    { href: 'liquidity.html', icon: 'water_drop',    label: 'Liquidity' },
    { type: 'sep' },
    { href: 'settings.html',  icon: 'settings',      label: 'Settings' },
  ];

  function buildSidebar(activeHref) {
    const items = NAV.map(item => {
      if (item.type === 'sep') return '<div class="sep"></div>';
      const active = item.href === activeHref ? ' active' : '';
      return `<a href="${item.href}" class="${active.trim()}">
        <span class="ms">${item.icon}</span>
        <span>${item.label}</span>
      </a>`;
    }).join('');

    return `<div class="brand-row">
      <div class="logo serif">R</div>
      <span class="brand-name">ChiefRiskBot</span>
    </div>
    <nav class="nav">${items}</nav>
    <div class="side-foot">
      <div class="ava md" style="background:var(--brand)">CIO</div>
      <div>
        <div class="who">Chief Investment Officer</div>
        <div class="role">Family Office</div>
      </div>
    </div>`;
  }

  function buildTopbar(crumbs) {
    const crumbHtml = crumbs.map((c, i) => {
      const isLast = i === crumbs.length - 1;
      if (isLast) return `<span class="cur">${c}</span>`;
      return `<span>${c}</span><span class="sep ms sm">chevron_right</span>`;
    }).join('');

    return `<button class="hamburger" id="crb-hamburger" aria-label="Open menu">
        <span class="ms sm">menu</span>
      </button>
      <div class="crumbs">${crumbHtml}</div>
      <div class="grow"></div>
      <button class="iconbtn" title="Notifications"><span class="ms sm">notifications</span></button>
      <button class="iconbtn" title="Help"><span class="ms sm">help_outline</span></button>`;
  }

  function mount(activeHref, crumbs) {
    crumbs = crumbs || [];

    // Inject backdrop for mobile
    const backdrop = document.createElement('div');
    backdrop.className = 'sidebar-backdrop';
    backdrop.id = 'crb-backdrop';
    document.body.appendChild(backdrop);

    // Inject sidebar
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
      sidebar.innerHTML = buildSidebar(activeHref);
    }

    // Inject topbar
    const top = document.querySelector('.top');
    if (top) {
      top.innerHTML = buildTopbar(crumbs);
    }

    wireResponsive();
    if (window.API) window.API.refreshUserPill();
  }

  function toast(message, type) {
    const node = document.createElement('div');
    node.className = 'toast ' + (type || 'info');
    node.textContent = message;
    node.setAttribute('role', 'status');
    document.body.appendChild(node);
    requestAnimationFrame(() => node.classList.add('show'));
    setTimeout(() => {
      node.classList.remove('show');
      setTimeout(() => node.remove(), 180);
    }, 3000);
  }

  function wireResponsive() {
    const hamburger = document.getElementById('crb-hamburger');
    const sidebar   = document.querySelector('.sidebar');
    const backdrop  = document.getElementById('crb-backdrop');

    function openSidebar() {
      sidebar && sidebar.classList.add('open');
      backdrop && backdrop.classList.add('open');
    }
    function closeSidebar() {
      sidebar && sidebar.classList.remove('open');
      backdrop && backdrop.classList.remove('open');
    }

    hamburger && hamburger.addEventListener('click', openSidebar);
    backdrop  && backdrop.addEventListener('click', closeSidebar);

    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') closeSidebar();
    });

    // Close on nav link click (mobile)
    const navLinks = document.querySelectorAll('.sidebar .nav a');
    navLinks.forEach(a => a.addEventListener('click', closeSidebar));
  }

  // Toggle switch wiring
  function wireToggles() {
    document.querySelectorAll('.sw').forEach(sw => {
      sw.addEventListener('click', () => sw.classList.toggle('on'));
    });
  }

  // Segmented control wiring
  function wireSegments() {
    document.querySelectorAll('.seg').forEach(seg => {
      seg.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => {
          seg.querySelectorAll('button').forEach(b => b.classList.remove('on'));
          btn.classList.add('on');
          // Fire custom event for page-level handlers
          seg.dispatchEvent(new CustomEvent('seg-change', { detail: { value: btn.dataset.value || btn.textContent.trim() }, bubbles: true }));
        });
      });
    });
  }

  // Drawer wiring
  function wireDrawers() {
    document.querySelectorAll('[data-drawer-open]').forEach(trigger => {
      trigger.addEventListener('click', () => {
        const id = trigger.dataset.drawerOpen;
        const drawer   = document.getElementById(id);
        const backdrop = document.getElementById(id + '-backdrop');
        if (drawer)   drawer.classList.add('open');
        if (backdrop) backdrop.classList.add('open');
      });
    });

    document.querySelectorAll('[data-drawer-close]').forEach(trigger => {
      trigger.addEventListener('click', () => {
        const id = trigger.dataset.drawerClose;
        const drawer   = document.getElementById(id);
        const backdrop = document.getElementById(id + '-backdrop');
        if (drawer)   drawer.classList.remove('open');
        if (backdrop) backdrop.classList.remove('open');
      });
    });

    document.querySelectorAll('.drawer-backdrop').forEach(bd => {
      bd.addEventListener('click', () => {
        bd.classList.remove('open');
        const drawerId = bd.id.replace('-backdrop', '');
        const drawer = document.getElementById(drawerId);
        if (drawer) drawer.classList.remove('open');
      });
    });
  }

  // Tab wiring
  function wireTabs() {
    document.querySelectorAll('.tab-group').forEach(group => {
      group.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
          group.querySelectorAll('.tab').forEach(t => t.classList.remove('on'));
          tab.classList.add('on');
          const target = tab.dataset.target;
          if (target) {
            document.querySelectorAll('[data-tab-panel]').forEach(p => {
              p.hidden = p.dataset.tabPanel !== target;
            });
          }
        });
      });
    });
  }

  // Auto-init on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', () => {
    wireToggles();
    wireSegments();
    wireDrawers();
    wireTabs();
  });

  window.Shell = { mount, toast, wireToggles, wireSegments, wireDrawers, wireTabs };
})();
