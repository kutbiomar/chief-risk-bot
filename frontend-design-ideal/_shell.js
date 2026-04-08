// ChiefRiskBot shared shell — injects sidebar + top bar so static pages stay tight.
(function(){
  const nav = [
    {section:'Workspace', items:[
      {href:'cockpit.html', icon:'dashboard', label:'Risk Cockpit'},
      {href:'briefings.html', icon:'description', label:'Briefings'},
      {href:'markets.html',   icon:'monitoring',  label:'Markets'},
    ]},
    {section:'Data', items:[
      {href:'sources.html',   icon:'cable',       label:'Sources'},
      {href:'table.html',     icon:'table_view',  label:'Table Editor'},
      {href:'documents.html', icon:'folder_open', label:'Documents'},
    ]},
    {section:'Admin', items:[
      {href:'members.html',   icon:'groups',      label:'Members'},
      {href:'audit.html',     icon:'history',     label:'Audit Log'},
      {href:'settings.html',  icon:'settings',    label:'Settings'},
    ]},
  ];

  function sidebar(active){
    const sections = nav.map(s => `
      <div class="section">${s.section}</div>
      ${s.items.map(i => `<a href="${i.href}" class="${active===i.href?'active':''}"><span class="ms">${i.icon}</span> ${i.label}</a>`).join('')}
    `).join('');
    return `
      <aside class="sidebar">
        <div class="brand-row"><div class="logo">C</div><div class="brand-name">ChiefRiskBot</div></div>
        <div class="client">
          <div class="who"><small>Client</small><b>Aldridge Family Office</b></div>
          <span class="ms">unfold_more</span>
        </div>
        <nav class="nav">${sections}</nav>
        <div class="side-foot">
          <div class="avatar">OK</div>
          <div style="display:flex;flex-direction:column;line-height:1.2">
            <span style="font-weight:600;font-size:12px">Omar Kutbi</span>
            <span style="font-size:10px;color:var(--ink-mute)">CIO · Aldridge FO</span>
          </div>
        </div>
      </aside>`;
  }

  function topbar(crumbs){
    const trail = crumbs.map((c,i)=>{
      const last = i===crumbs.length-1;
      return last ? `<b>${c}</b>` : `${c} <span class="ms">chevron_right</span>`;
    }).join(' ');
    return `
      <div class="top">
        <button class="hamburger" id="crb-hamburger" aria-label="Open menu"><span class="ms">menu</span></button>
        <div class="crumbs">${trail}</div>
        <div class="grow"></div>
        <div class="search">
          <span class="ms" style="font-size:16px">search</span>
          <input placeholder="Search positions, risks, briefings"/>
          <span class="kbd">⌘K</span>
        </div>
        <button class="iconbtn" title="Notifications"><span class="ms">notifications</span></button>
        <button class="iconbtn" title="Help"><span class="ms">help</span></button>
      </div>`;
  }

  function wireResponsive(){
    const sb  = document.querySelector('.sidebar');
    const ham = document.getElementById('crb-hamburger');
    if(!sb || !ham) return;
    const bd  = document.createElement('div');
    bd.className = 'sb-backdrop';
    document.body.appendChild(bd);
    const close = () => { sb.classList.remove('open'); bd.classList.remove('open'); };
    ham.addEventListener('click', () => { sb.classList.toggle('open'); bd.classList.toggle('open'); });
    bd.addEventListener('click', close);
    sb.querySelectorAll('a').forEach(a => a.addEventListener('click', close));
    document.addEventListener('keydown', e => { if(e.key === 'Escape') close(); });
  }

  window.CRB = {
    mount(active, crumbs){
      const root = document.getElementById('app-root');
      const main = root.querySelector('main');
      root.insertAdjacentHTML('afterbegin', sidebar(active));
      main.insertAdjacentHTML('afterbegin', topbar(crumbs));
      wireResponsive();
    }
  };
})();
