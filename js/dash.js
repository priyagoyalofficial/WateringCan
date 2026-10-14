/* Dashboard: hydration share (donut), moisture left per plant (bars), and what needs attention. */
const HYD = [
  {k:'ok',    label:'Hydrated',            icon:'✓', hint:'Soil should still have moisture'},
  {k:'today', label:'Drying, check today', icon:'!', hint:'Due for a finger test today'},
  {k:'late',  label:'Dehydrated, overdue', icon:'✕', hint:'Past its check date, likely dry'},
  {k:'new',   label:'Not tracked yet',     icon:'?', hint:'No watering logged yet'},
];
const hydKind = ws => ws.kind==='snooze' ? 'ok' : ws.kind;
const pct = (n, t) => t ? Math.round(n/t*100) : 0;

function arcPath(a0, a1, R, r){
  const pt = (a, rad) => `${(100 + rad*Math.sin(a)).toFixed(2)} ${(100 - rad*Math.cos(a)).toFixed(2)}`;
  const big = a1 - a0 > Math.PI ? 1 : 0;
  return `M${pt(a0,R)} A${R} ${R} 0 ${big} 1 ${pt(a1,R)} L${pt(a1,r)} A${r} ${r} 0 ${big} 0 ${pt(a0,r)} Z`;
}

function donutSVG(groups, total){
  const R = 92, r = 62;
  let a = 0, segs = '';
  const shown = groups.filter(g => g.n);
  for (const g of shown){
    const tip = `${g.icon} ${g.label}: ${g.n} of ${total} (${pct(g.n,total)}%)`;
    if (shown.length === 1){
      // A single category is a full ring; an arc can't span 360°.
      segs += `<circle cx="100" cy="100" r="${(R+r)/2}" fill="none" class="seg-${g.k}" stroke-width="${R-r}" data-tip="${esc(tip)}"/>`;
      break;
    }
    const a1 = a + g.n/total * Math.PI*2;
    segs += `<path d="${arcPath(a, a1, R, r)}" class="seg-${g.k}" data-tip="${esc(tip)}"/>`;
    a = a1;
  }
  const hyd = groups.find(g => g.k==='ok').n;
  const summary = groups.filter(g=>g.n).map(g=>`${g.label} ${pct(g.n,total)}%`).join(', ');
  return `<svg viewBox="0 0 200 200" role="img" aria-label="Hydration: ${esc(summary)}">
    ${segs}
    <text x="100" y="102" class="d-big">${pct(hyd,total)}%</text>
    <text x="100" y="126" class="d-sub">hydrated</text>
  </svg>`;
}

function renderDash(list){
  const rows = list.map(p => ({p, ws:waterStatus(p), fs:feedStatus(p)}));
  const total = rows.length;
  document.getElementById('dashNote').hidden = !!plants.length;

  const groups = HYD.map(h => ({...h, n: rows.filter(r => hydKind(r.ws)===h.k).length}));
  const needs = rows.filter(r => ['late','today','new'].includes(r.ws.kind) || r.fs.kind==='due');
  const feed = rows.filter(r => r.fs.kind==='due').length;
  const tracked = rows.filter(r => r.ws.kind!=='new');
  const avg = tracked.length ? Math.round(tracked.reduce((s,r)=>s+r.ws.frac,0)/tracked.length*100) : null;

  document.getElementById('dashStats').innerHTML =
    `<div class="st-ok"><b class="mono">${pct(groups[0].n,total)}%</b><span>hydrated</span></div>
     <div class="st-late"><b class="mono">${pct(needs.length,total)}%</b><span>need attention (${needs.length} of ${total})</span></div>
     <div class="st-feed"><b class="mono">${feed}</b><span>to fertilize</span></div>
     <div><b class="mono">${avg===null?'–':avg+'%'}</b><span>avg moisture left</span></div>`;

  document.getElementById('donut').innerHTML = total ? donutSVG(groups, total) : '<p class="empty">No plants yet.</p>';
  document.getElementById('donutLegend').innerHTML =
    `<thead><tr><th scope="col">Status</th><th scope="col">Plants</th><th scope="col">Share</th></tr></thead><tbody>` +
    groups.map(g => `<tr class="lg-${g.k}" data-tip="${esc(g.hint)}">
      <td><span class="sw" aria-hidden="true">${g.icon}</span>${g.label}</td>
      <td class="mono">${g.n}</td><td class="mono">${pct(g.n,total)}%</td></tr>`).join('') + '</tbody>';

  const order = [...rows].sort((a,b) => (a.ws.kind==='new') - (b.ws.kind==='new') || a.ws.frac - b.ws.frac);
  document.getElementById('moistBars').innerHTML = order.map(({p, ws}) => {
    const k = hydKind(ws), h = HYD.find(x => x.k===k);
    const val = ws.kind==='new' ? 'no log' : `${Math.round(ws.frac*100)}%`;
    const when = ws.kind==='new' ? 'Log a watering to start' : `Next check ${fmt(ws.due)}`;
    return `<div class="bar b-${k}" data-tip="${esc(`${h.icon} ${p.name}: ${h.label}. ${when}`)}">
      <span class="bn">${esc(p.name)}</span><span class="bv mono">${val}</span>
      <span class="bt"><i style="width:${ws.kind==='new'?0:Math.max(2, Math.round(ws.frac*100))}%"></i></span></div>`;
  }).join('') || '<p class="empty">No plants yet.</p>';

  needs.sort((a,b) => a.ws.d - b.ws.d);
  document.getElementById('attnCount').textContent = `${needs.length} of ${total}`;
  document.getElementById('attnList').innerHTML = needs.length ? needs.map(({p, ws, fs}) => {
    const why = [
      ws.kind==='late' ? `<span class="k late">✕ Overdue ${rel(ws.d).replace(' late','')}</span>` : '',
      ws.kind==='today' ? '<span class="k today">! Check soil today</span>' : '',
      ws.kind==='new' ? '<span class="k skip">? No watering logged</span>' : '',
      fs.kind==='due' ? '<span class="k feed">Fertilize</span>' : '',
    ].filter(Boolean).join(' · ');
    return `<li><span>${why}<br><span>${esc(p.name)}</span> <span class="meta">${esc(dryDepth(p))}</span></span>
      <span class="dd-r">${!p.example ? `<button class="btn ghost" type="button" data-open="${p.id}">Details</button>` : ''}</span></li>`;
  }).join('') : '<li><span class="empty">Nothing needs you today.</span></li>';
}

/* One tooltip for every [data-tip] mark on the dashboard. */
(() => {
  const tab = document.getElementById('tab-dash');
  const tip = document.createElement('div');
  tip.className = 'dtip'; tip.hidden = true; tip.setAttribute('role','tooltip');
  document.body.appendChild(tip);
  tab.addEventListener('pointermove', e => {
    const t = e.target.closest('[data-tip]');
    if (!t){ tip.hidden = true; return; }
    tip.textContent = t.dataset.tip; tip.hidden = false;
    const w = tip.offsetWidth, x = Math.min(e.clientX + 14, innerWidth - w - 8);
    tip.style.left = `${Math.max(8, x)}px`; tip.style.top = `${e.clientY + 16}px`;
  });
  tab.addEventListener('pointerleave', () => { tip.hidden = true; });
  tab.addEventListener('click', e => { const op = e.target.closest('[data-open]'); if (op) openSheet(op.dataset.open); });
})();
