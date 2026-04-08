(function () {
  const nav = [
    {
      section: 'Workspace',
      items: [
        { href: 'onboarding.html', icon: 'rocket_launch', label: 'Onboarding' },
        { href: 'cockpit.html', icon: 'dashboard', label: 'Risk Cockpit' },
        { href: 'briefings.html', icon: 'description', label: 'Briefings' },
      ],
    },
    {
      section: 'Data',
      items: [
        { href: 'table.html', icon: 'table_view', label: 'Positions' },
        { href: 'documents.html', icon: 'folder_open', label: 'Documents' },
      ],
    },
  ];

  function sidebar(active) {
    const sections = nav
      .map(
        (section) => `
      <div class="section">${section.section}</div>
      ${section.items
        .map(
          (item) => `
            <a href="${item.href}" class="${active === item.href ? 'active' : ''}">
              <span class="ms">${item.icon}</span> ${item.label}
            </a>
          `
        )
        .join('')}
    `
      )
      .join('');

    return `
      <aside class="sidebar">
        <div class="brand-row">
          <div class="logo">C</div>
          <div class="brand-name">ChiefRiskBot</div>
        </div>
        <div class="client">
          <div class="who">
            <small>Workspace</small>
            <b id="mvp-workspace-name">ChiefRiskBot Demo</b>
          </div>
          <span class="ms">unfold_more</span>
        </div>
        <nav class="nav">${sections}</nav>
        <div class="side-foot">
          <div class="avatar" id="mvp-user-avatar">CR</div>
          <div style="display:flex;flex-direction:column;line-height:1.2">
            <span style="font-weight:600;font-size:12px" id="mvp-user-name">Risk User</span>
            <span style="font-size:10px;color:var(--ink-mute)" id="mvp-user-role">Workspace session</span>
          </div>
          <button class="iconbtn" id="mvp-logout" title="Sign out"><span class="ms">logout</span></button>
        </div>
      </aside>
    `;
  }

  function topbar(crumbs) {
    const trail = crumbs
      .map((crumb, index) => {
        const last = index === crumbs.length - 1;
        return last ? `<b>${crumb}</b>` : `${crumb} <span class="ms">chevron_right</span>`;
      })
      .join(' ');

    return `
      <div class="top">
        <button class="hamburger" id="crb-hamburger" aria-label="Open menu">
          <span class="ms">menu</span>
        </button>
        <div class="crumbs">${trail}</div>
        <div class="grow"></div>
        <div class="search">
          <span class="ms" style="font-size:16px">search</span>
          <input placeholder="Search positions, risks, briefings" disabled />
          <span class="kbd">MVP</span>
        </div>
      </div>
    `;
  }

  function wireResponsive() {
    const sidebarNode = document.querySelector('.sidebar');
    const hamburger = document.getElementById('crb-hamburger');
    if (!sidebarNode || !hamburger) return;
    const backdrop = document.createElement('div');
    backdrop.className = 'sb-backdrop';
    document.body.appendChild(backdrop);

    const close = () => {
      sidebarNode.classList.remove('open');
      backdrop.classList.remove('open');
    };

    hamburger.addEventListener('click', () => {
      sidebarNode.classList.toggle('open');
      backdrop.classList.toggle('open');
    });
    backdrop.addEventListener('click', close);
    sidebarNode.querySelectorAll('a').forEach((anchor) => anchor.addEventListener('click', close));
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') close();
    });
  }

  window.CRBMvpShell = {
    mount(active, crumbs) {
      const root = document.getElementById('app-root');
      const main = root.querySelector('main');
      root.insertAdjacentHTML('afterbegin', sidebar(active));
      main.insertAdjacentHTML('afterbegin', topbar(crumbs));
      wireResponsive();
    },
  };
})();
