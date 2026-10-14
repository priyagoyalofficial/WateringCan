/* ---------- state ---------- */
let plants = [], pending = {}, sheetId = null;
const examples = [
  {id:'ex1',name:'Kitchen pothos',species:'pothos',where:'in',spot:'north window',pot:'plastic',size:6,soil:'regular',lastWatered:addDays(TODAY,-10),lastFed:addDays(TODAY,-40),learned:1,log:[],example:true},
  {id:'ex2',name:'Patio lemon',species:'citrus',where:'out',spot:'south patio',pot:'terracotta',size:14,soil:'regular',lastWatered:addDays(TODAY,-4),lastFed:addDays(TODAY,-12),learned:1,log:[],example:true},
  {id:'ex3',name:'Desk snake plant',species:'snake',where:'in',spot:'office',pot:'plastic',size:4,soil:'cactus',lastWatered:addDays(TODAY,-6),learned:1,log:[],example:true},
];
const showing = ()=> plants.length ? plants : examples;

/* ---------- persistence ---------- */
function save(){
  if (!Store.saveAll(plants)) showBanner(`<strong>Couldn't save.</strong> This browser is blocking storage (private window or site data turned off). Changes will be lost when you close the page.`);
}
function upsertLocal(p){ const i=plants.findIndex(x=>x.id===p.id); if(i<0) plants.push(p); else plants[i]=p; render(); }
function newId(){ return 'p' + Date.now().toString(36) + Math.random().toString(36).slice(2,6); }
function pushLog(p, entry){ p.log = [entry, ...(p.log||[])].slice(0,80); }

/* ---------- actions ---------- */
function act(id, what){
  const p = plants.find(x=>x.id===id); if (!p) return;
  const np = JSON.parse(JSON.stringify(p));
  if (what==='water-dry' || what==='water-bone' || what==='water-first'){
    if (np.lastWatered && what!=='water-first'){
      const actual = diff(np.lastWatered, TODAY);
      const hadSkip = (np.log||[]).some(e=>e.t==='skip' && e.d>np.lastWatered);
      const base = baseInterval(np);
      let L = np.learned||1;
      if (what==='water-bone') L *= 0.85;
      else if (!hadSkip && actual>0 && actual <= interval(np)+1) L = 0.75*L + 0.25*(actual/base);
      np.learned = +clamp(L,0.5,2).toFixed(3);
    }
    np.lastWatered = TODAY; delete np.checkAfter;
    pushLog(np,{t:'water',d:TODAY,note: what==='water-bone'?'bone dry':''});
  } else if (what==='skip'){
    const iv = interval(np);
    np.learned = +clamp((np.learned||1)*1.1,0.5,2).toFixed(3);
    np.checkAfter = addDays(TODAY, Math.max(1, Math.round(iv*0.25)));
    pushLog(np,{t:'skip',d:TODAY,note:'soil still damp'});
  } else if (what==='feed'){
    np.lastFed = TODAY; pushLog(np,{t:'feed',d:TODAY,note:''});
  }
  delete pending[id];
  upsertLocal(np); save();
  if (sheetId===id) openSheet(id);
}

/* ---------- render ---------- */
function tagHTML(p){
  const ws = waterStatus(p), fs = feedStatus(p), sp = profile(p);
  const ex = !!p.example;
  let pill;
  if (ws.kind==='new') pill = 'no log yet';
  else if (ws.kind==='snooze') pill = `recheck ${rel(ws.d)}`;
  else pill = ws.d<=0 ? (ws.d===0?'check today':rel(ws.d)) : `check ${rel(ws.d)}`;
  const spName = p.custom ? p.custom.n : (SP[p.species]?.n || 'Plant');
  const chips = [
    `<span class="chip">${p.where==='out'?'Outdoor':'Indoor'}</span>`,
    fs.kind==='due' ? `<span class="chip feed">Fertilize</span>` : '',
    ex ? `<span class="chip ex">Example</span>` : ''
  ].join('');
  let acts;
  const dis = ex ? ' disabled' : '';
  if (pending[p.id]==='ask'){
    acts = `<p class="ask">Before you pour: how dry was the soil?</p>
      <button class="btn water" data-a="water-dry" data-id="${p.id}">Dry, watered it</button>
      <button class="btn" data-a="water-bone" data-id="${p.id}">Bone dry / drooping</button>
      <button class="btn ghost" data-a="cancel" data-id="${p.id}">Cancel</button>`;
  } else {
    const urgent = ['late','today','new'].includes(ws.kind);
    acts = `<button class="btn ${urgent?'water':''}" data-a="${ws.kind==='new'?'water-first':'ask'}" data-id="${p.id}"${dis}>${ws.kind==='new'?'Watered today':'Watered'}</button>
      ${ws.kind!=='new' && (urgent||ws.kind==='snooze') ? `<button class="btn" data-a="skip" data-id="${p.id}"${dis}>Still damp</button>`:''}
      ${fs.kind==='due' ? `<button class="btn feed" data-a="feed" data-id="${p.id}"${dis}>Fertilized</button>`:''}
      <button class="btn ghost" data-a="open" data-id="${p.id}"${dis}>Details</button>`;
  }
  const next = ws.kind==='new' ? 'Log a watering to start the schedule'
    : `<span class="mono">${fmt(ws.due)}</span> · about every ${ws.iv} days right now`;
  return `<article class="tag s-${ws.kind}${ex?' example':''}">
    <div class="gauge" title="Estimated soil moisture left"><i style="height:${Math.round(ws.frac*100)}%"></i></div>
    <div class="tbody">
      <div class="trow"><h3>${esc(p.name)}</h3><span class="pill w">${pill}</span></div>
      <p class="meta">${esc(spName)}${p.spot?` · ${esc(p.spot)}`:''}</p>
      <p class="rule">Water when: <b>${esc(dryDepth(p))}</b><br>How much: <b class="amt">${esc(amount(p).short)}</b></p>
      <p class="meta">${next}</p>
      <div class="chips">${chips}</div>
      <div class="acts">${acts}</div>
    </div>
  </article>`;
}

function render(){
  const list = showing();
  const rows = list.map(p=>({p, ws:waterStatus(p), fs:feedStatus(p)}));
  const needs = rows.filter(r=>['late','today','new'].includes(r.ws.kind) || r.fs.kind==='due');
  const rest = rows.filter(r=>!needs.includes(r)).sort((a,b)=>a.ws.d-b.ws.d);
  needs.sort((a,b)=>a.ws.d-b.ws.d);

  document.getElementById('attention').innerHTML = needs.length ? needs.map(r=>tagHTML(r.p)).join('')
    : `<p class="empty">Nothing needs you today. Every plant still has moisture left.</p>`;
  document.getElementById('rest').innerHTML = rest.length ? rest.map(r=>tagHTML(r.p)).join('')
    : `<p class="empty">${list.length?'Every plant is on today\'s list.':'No plants yet.'}</p>`;
  document.getElementById('att-count').textContent = `${needs.length} of ${list.length}`;

  const late = rows.filter(r=>r.ws.kind==='late').length;
  const today = rows.filter(r=>r.ws.kind==='today'||r.ws.kind==='new').length;
  const feed = rows.filter(r=>r.fs.kind==='due').length;
  document.getElementById('tally').innerHTML =
    `<div class="t-late"><b class="mono">${late}</b><span>overdue</span></div>
     <div class="t-today"><b class="mono">${today}</b><span>check today</span></div>
     <div class="t-feed"><b class="mono">${feed}</b><span>to fertilize</span></div>
     <div><b class="mono">${list.length}</b><span>plants</span></div>`;
  renderCal(list);
  renderDash(list);
}


function seasonLine(){
  const m = parse(TODAY).getMonth();
  const s = SEASON[m];
  const notes = [
    'Mid-winter: plants drink much less. Expect schedules about 40% longer and no fertilizing.',
    'Late winter: growth is still slow, so water sparingly. Fertilizing starts again in March.',
    'Early spring: new growth is starting. Resume fertilizing lightly.',
    'Spring growth: baseline schedules apply.',
    'Late spring: pots are drying faster as the days warm up.',
    'June gloom masks the heat. Pots dry faster than they look.',
    'Peak summer heat: outdoor pots can dry in a day or two. Check them in the morning.',
    'Peak summer heat: outdoor pots can dry in a day or two. Check them in the morning.',
    'Still hot and dry. Santa Ana winds can dry outdoor pots in a single afternoon.',
    'Fall: growth slows, so fertilize half as often. Watch for Santa Ana wind days.',
    'Days are shortening. Water and fertilizer needs drop.',
    'Mid-winter: plants drink much less. Expect schedules about 40% longer and no fertilizing.',
  ];
  document.getElementById('dateline').textContent = `${fmt(TODAY)} · Anaheim · USDA zone 10b`;
  document.getElementById('season').textContent = `${notes[m]} Schedules are ${s<1?Math.round((1-s)*100)+'% shorter':s>1?Math.round((s-1)*100)+'% longer':'at baseline'} this month.`;
}

function showBanner(html){ const b=document.getElementById('banner'); b.innerHTML=html; b.hidden=!html; }
function updateBanner(){
  if (!Store.available) showBanner(`<strong>Saving is blocked in this browser.</strong> You can try the app, but anything you add disappears when you close the page.`);
  else if (!plants.length) showBanner(`<strong>These three plants are examples.</strong> Add your first plant and they'll disappear.`);
  else showBanner('');
}

/* ---------- detail sheet ---------- */
function openSheet(id){
  const p = plants.find(x=>x.id===id); if(!p) return;
  sheetId = id;
  const sp = profile(p), ws = waterStatus(p), fs = feedStatus(p);
  const succ = DRY_KEYS.has(p.species);
  const L = p.learned||1;
  const tuned = Math.abs(L-1)<0.04 ? 'Following the care guide. It adjusts as you log.'
    : `Tuned to your home: this plant goes ${Math.round(Math.abs(L-1)*100)}% ${L<1?'faster':'longer'} between waterings than the guide.`;
  const feedTxt = !sp.feed ? 'Rarely. Poor soil suits it.'
    : fs.kind==='rest' ? `Every ~${sp.feed} days from March to September. Paused for winter.`
    : `Every ~${fs.fi} days right now${fs.due?` · next ${fs.due<=TODAY?'due now':fmt(fs.due)}`:''}. Use half-strength liquid fertilizer, poured onto damp soil.`;
  const opt = (obj,val)=>Object.entries(obj).map(([k,v])=>`<option value="${k}"${k===val?' selected':''}>${v}</option>`).join('');
  document.getElementById('sheet').innerHTML = `
    <div class="sh"><div><span class="eyebrow">${esc(sp.l||'')}</span><h2 id="sh-title">${esc(p.name)}</h2></div>
      <button class="btn ghost" id="closeSheet" aria-label="Close">Close</button></div>
    <dl class="care">
      <dt>Light</dt><dd>${esc(sp.light)}</dd>
      <dt>Water when</dt><dd>${esc(sp.dry)}. Check with your finger before every watering.</dd>
      <dt>How much</dt><dd><b>${esc(amount(p).short)}</b> for a ${potIn(p)}-inch pot. ${esc(amount(p).how)}</dd>
      <dt>Schedule</dt><dd>${ws.kind==='new'?'Starts after the first logged watering.':`About every ${ws.iv} days this month · next check <span class="mono">${fmt(ws.due)}</span>`}</dd>
      <dt>Fertilizer</dt><dd>${feedTxt}</dd>
      <dt>Too much</dt><dd>${succ?OVER.succ:OVER.in}</dd>
      <dt>Too little</dt><dd>${succ?UNDER.succ:UNDER.in}</dd>
      <dt>Tip</dt><dd>${esc(sp.tip)}</dd>
    </dl>
    <p class="tuned">${tuned}</p>

    <form class="panel" id="logPast">
      <h3>Log a past watering or feeding</h3>
      <div class="row2">
        <div class="field"><label for="lp-date">Date</label><input type="date" id="lp-date" max="${TODAY}" value="${TODAY}"></div>
        <div class="field"><label for="lp-type">What</label><select id="lp-type"><option value="water">Watered</option><option value="feed">Fertilized</option></select></div>
      </div>
      <button class="btn" type="submit">Log it</button>
    </form>

    <form class="panel" id="editForm">
      <h3>Pot &amp; place</h3>
      <div class="field"><label for="e-name">Nickname</label><input type="text" id="e-name" value="${esc(p.name)}"></div>
      <div class="row2">
        <div class="field"><label for="e-where">Location</label><select id="e-where">${opt({in:'Indoors',out:'Outdoors'},p.where)}</select></div>
        <div class="field"><label for="e-spot">Spot</label><input type="text" id="e-spot" value="${esc(p.spot||'')}"></div>
      </div>
      <div class="row2">
        <div class="field"><label for="e-pot">Pot</label><select id="e-pot">${opt({plastic:'Plastic / glazed',terracotta:'Terracotta',selfwater:'Self-watering',ground:'In the ground'},p.pot)}</select></div>
        <div class="field"><label for="e-size">Pot width</label><select id="e-size">${opt(Object.fromEntries(WIDTHS.map(w=>[w,w===20?'20 in or more':w+' in'])),String(potIn(p)))}</select></div>
      </div>
      <div class="field"><label for="e-soil">Soil</label><select id="e-soil">${opt({regular:'Regular potting mix',chunky:'Chunky / aroid mix',cactus:'Cactus & succulent mix',bark:'Orchid bark',leca:'LECA / semi-hydro',garden:'Garden soil'},p.soil)}</select></div>
      <label class="meta"><input type="checkbox" id="e-reset"> Reset what it has learned (after repotting)</label>
      <button class="btn water" type="submit">Save changes</button>
    </form>

    <section><h3>History</h3>
      ${(p.log||[]).length ? `<ul class="hist">${p.log.slice(0,25).map(e=>`<li><span class="k ${e.t}">${e.t==='water'?'Watered':e.t==='feed'?'Fertilized':'Still damp, skipped'}${e.note&&e.t==='water'?` <span class="meta">(${esc(e.note)})</span>`:''}</span><span class="mono meta">${fmt(e.d)}</span></li>`).join('')}</ul>` : '<p class="empty">Nothing logged yet.</p>'}
    </section>

    <div id="delZone"><button class="btn danger" id="delBtn" type="button">Remove plant</button></div>`;
  document.getElementById('scrim').hidden = false;
  document.getElementById('closeSheet').focus();
}
function closeSheet(){ sheetId=null; document.getElementById('scrim').hidden=true; }

document.getElementById('scrim').addEventListener('click', e=>{
  if (e.target.id==='scrim' || e.target.id==='closeSheet') return closeSheet();
  const p = plants.find(x=>x.id===sheetId); if(!p) return;
  if (e.target.id==='delBtn'){
    document.getElementById('delZone').innerHTML = `<p class="meta">Remove ${esc(p.name)} and its history? This can't be undone.</p>
      <div class="acts"><button class="btn danger" id="delYes" type="button">Yes, remove it</button><button class="btn ghost" id="delNo" type="button">Keep it</button></div>`;
  } else if (e.target.id==='delNo'){ openSheet(p.id); }
  else if (e.target.id==='delYes'){
    plants = plants.filter(x=>x.id!==p.id); closeSheet(); render(); updateBanner();
    save();
  }
});
document.addEventListener('keydown', e=>{ if(e.key==='Escape' && sheetId) closeSheet(); });
document.getElementById('sheet').addEventListener('submit', e=>{
  e.preventDefault();
  const p = plants.find(x=>x.id===sheetId); if(!p) return;
  const np = JSON.parse(JSON.stringify(p));
  if (e.target.id==='logPast'){
    const d = document.getElementById('lp-date').value, t = document.getElementById('lp-type').value;
    if (!d || d>TODAY) return;
    pushLog(np,{t,d,note:'logged later'});
    np.log.sort((a,b)=>b.d.localeCompare(a.d));
    if (t==='water' && (!np.lastWatered || d>np.lastWatered)){ np.lastWatered=d; if(np.checkAfter && np.checkAfter<=d) delete np.checkAfter; }
    if (t==='feed' && (!np.lastFed || d>np.lastFed)) np.lastFed=d;
  } else if (e.target.id==='editForm'){
    np.name = document.getElementById('e-name').value.trim() || np.name;
    np.where = document.getElementById('e-where').value;
    np.spot = document.getElementById('e-spot').value.trim();
    np.pot = document.getElementById('e-pot').value;
    np.size = +document.getElementById('e-size').value;
    np.soil = document.getElementById('e-soil').value;
    if (document.getElementById('e-reset').checked) np.learned = 1;
  }
  upsertLocal(np); save(); openSheet(np.id);
});

/* ---------- tag buttons ---------- */
document.querySelector('.col').addEventListener('click', e=>{
  const b = e.target.closest('button[data-a]'); if(!b || b.disabled) return;
  const id = b.dataset.id, a = b.dataset.a;
  if (a==='ask'){ pending[id]='ask'; render(); }
  else if (a==='cancel'){ delete pending[id]; render(); }
  else if (a==='open') openSheet(id);
  else act(id, a);
});

/* ---------- add form ---------- */
const sel = document.getElementById('f-species');
sel.innerHTML = `<option value="">Choose a plant…</option>
  <optgroup label="Houseplants">${SPECIES.filter(s=>s.w==='in').map(s=>`<option value="${s.k}">${s.n}</option>`).join('')}</optgroup>
  <optgroup label="Patio &amp; garden">${SPECIES.filter(s=>s.w==='out').map(s=>`<option value="${s.k}">${s.n}</option>`).join('')}</optgroup>
  <option value="other">Something else…</option>`;
sel.addEventListener('change', ()=>{
  const v = sel.value;
  document.getElementById('otherBox').hidden = v!=='other';
  if (SP[v]){
    document.getElementById(SP[v].w==='out'?'f-out':'f-in').checked = true;
    if (['succ','cactus','aloe','jade','pearls'].includes(v)) document.getElementById('f-soil').value='cactus';
    else if (v==='orchid') document.getElementById('f-soil').value='bark';
  }
});
document.getElementById('f-last').max = TODAY;
document.getElementById('f-size').innerHTML = WIDTHS.map(w=>`<option value="${w}"${w===6?' selected':''}>${w===20?'20 in or more':w+' in across'}</option>`).join('');

document.getElementById('addForm').addEventListener('submit', e=>{
  e.preventDefault();
  const msg = document.getElementById('addMsg');
  const species = sel.value;
  if (!species){ msg.className='msg err'; msg.textContent='Choose a plant type first. If it isn\'t listed, pick "Something else…".'; return; }
  let custom = null;
  if (species==='other'){
    const nm = document.getElementById('f-other').value.trim();
    if (!nm){ msg.className='msg err'; msg.textContent='Type the plant name.'; return; }
    const days = clamp(Math.round(+document.getElementById('f-days').value||7),1,60);
    custom = {...DEFAULT_SP, n:nm, days, w:document.querySelector('input[name=where]:checked').value};
  }
  const last = document.getElementById('f-last').value;
  const spName = custom ? custom.n : SP[species].n;
  const p = {
    id:newId(), name: document.getElementById('f-name').value.trim() || spName,
    species, where: document.querySelector('input[name=where]:checked').value,
    spot: document.getElementById('f-spot').value.trim(),
    pot: document.getElementById('f-pot').value, size: +document.getElementById('f-size').value,
    soil: document.getElementById('f-soil').value, learned:1, created:TODAY, log:[]
  };
  if (custom) p.custom = custom;
  if (last && last<=TODAY){ p.lastWatered = last; p.log=[{t:'water',d:last,note:''}]; }
  upsertLocal(p); save(); updateBanner();
  msg.className='msg'; msg.textContent = `Added ${p.name}.`;
  ['f-name','f-spot','f-last','f-other'].forEach(i=>document.getElementById(i).value='');
  sel.value=''; document.getElementById('otherBox').hidden=true;
});

/* ---------- calendar ---------- */
let calMonth = TODAY.slice(0,7), calSel = TODAY;
function monthEvents(list, first, last){
  const map = {};
  const add = (d,e)=>{ if(d>=first && d<=last) (map[d] ||= []).push(e); };
  for (const p of list){
    for (const e of (p.log||[])) if (e.d < TODAY) add(e.d, {t:e.t==='feed'?'f':e.t==='skip'?'s':'w', n:p.name, id:p.id, done:true, note:e.note});
    const ws = waterStatus(p);
    if (ws.kind==='new') add(TODAY, {t:'w', n:p.name, id:p.id, late:true});
    else {
      let d = ws.due, guard = 0;
      if (ws.due < TODAY){ add(TODAY, {t:'w', n:p.name, id:p.id, late:true}); d = addDays(TODAY, interval(p, TODAY)); }
      while (d <= last && guard++ < 400){ add(d, {t:'w', n:p.name, id:p.id}); d = addDays(d, interval(p, d)); }
    }
    const fs = feedStatus(p);
    if (fs.kind==='due'||fs.kind==='ok'){
      let d = fs.due < TODAY ? TODAY : fs.due, guard = 0;
      while (d <= last && guard++ < 60){
        const m = parse(d).getMonth();
        if (!(m===11||m<=1)) add(d, {t:'f', n:p.name, id:p.id});
        d = addDays(d, fs.fi);
      }
    }
  }
  return map;
}
function renderCal(list){
  const [y,m] = calMonth.split('-').map(Number);
  const first = `${calMonth}-01`, lastD = new Date(y, m, 0).getDate(), last = `${calMonth}-${pad(lastD)}`;
  const map = monthEvents(list, first, last);
  document.getElementById('calTitle').textContent = new Date(y, m-1, 1).toLocaleDateString('en-US',{month:'long',year:'numeric'});
  const lead = new Date(y, m-1, 1).getDay();
  const cells = Array.from({length:lead},()=>'<div class="day pad" aria-hidden="true"></div>');
  for (let i=1;i<=lastD;i++){
    const d = `${calMonth}-${pad(i)}`, ev = map[d]||[];
    const cls = ['day', d===TODAY?'is-today':'', d<TODAY?'past':'', d===calSel?'sel':''].join(' ');
    const shown = ev.slice(0,3).map(e=>`<span class="ev${e.t==='f'?' f':''}${e.t==='s'?' s':''}${e.done?' done':''}${e.late?' late':''}">${e.done&&e.t!=='s'?'✓ ':''}${esc(e.n)}</span>`).join('');
    const dots = ev.map(e=>`<i class="dot${e.t==='f'?' f':''}${e.t==='s'?' s':''}"></i>`).join('');
    cells.push(`<button type="button" class="${cls}" data-day="${d}" aria-label="${fmt(d)}, ${ev.length} item${ev.length===1?'':'s'}">
      <span class="dn mono">${i}</span>
      <span class="evs">${shown}${ev.length>3?`<span class="more">+${ev.length-3} more</span>`:''}</span>
      <span class="dots">${dots}</span></button>`);
  }
  document.getElementById('cal').innerHTML = cells.join('');
  const selEv = (calSel>=first && calSel<=last) ? (map[calSel]||[]) : null;
  const box = document.getElementById('dayDetail');
  if (!selEv){ box.innerHTML = '<p class="empty">Pick a day to see what is on it.</p>'; return; }
  const when = calSel===TODAY ? 'Today' : fmt(calSel);
  const label = e => e.done ? (e.t==='f'?'Fertilized':e.t==='s'?'Checked, still damp':'Watered') + (e.note&&e.t==='w'?` (${esc(e.note)})`:'')
    : e.t==='f' ? 'Fertilize' : e.late ? 'Overdue: check soil now' : 'Check soil, water if dry';
  box.innerHTML = `<h3>${when}</h3>` + (selEv.length
    ? `<ul class="hist">${selEv.map(e=>{
        const p = list.find(x=>x.id===e.id);
        const amt = (!e.done && e.t==='w' && p) ? `<span class="meta">${esc(amount(p).short)}</span>` : '';
        return `<li><span><span class="k ${e.t==='f'?'feed':e.t==='s'?'skip':'water'}">${label(e)}</span><br><span>${esc(e.n)}</span></span>
          <span class="dd-r">${amt}${p && !p.example ? `<button class="btn ghost" type="button" data-open="${e.id}">Details</button>`:''}</span></li>`;
      }).join('')}</ul>`
    : `<p class="empty">${calSel<TODAY?'Nothing was logged this day.':'Nothing planned.'}</p>`);
}
function setTab(t){
  document.getElementById('tab-plants').hidden = t!=='plants';
  document.getElementById('tab-cal').hidden = t!=='cal';
  document.getElementById('tab-dash').hidden = t!=='dash';
  document.querySelectorAll('.tabs [role=tab]').forEach(b=>{ const on=b.dataset.tab===t; b.setAttribute('aria-selected', on); b.tabIndex = on?0:-1; });
  try{ localStorage.setItem('wc-tab', t); }catch(_){}
}
document.querySelector('.tabs').addEventListener('click', e=>{ const b=e.target.closest('[role=tab]'); if(b) setTab(b.dataset.tab); });
document.querySelector('.tabs').addEventListener('keydown', e=>{
  if (e.key!=='ArrowLeft' && e.key!=='ArrowRight') return;
  const tabs=[...document.querySelectorAll('.tabs [role=tab]')], i=tabs.indexOf(document.activeElement);
  const n=tabs[(i+(e.key==='ArrowRight'?1:tabs.length-1))%tabs.length]; setTab(n.dataset.tab); n.focus();
});
document.getElementById('tab-cal').addEventListener('click', e=>{
  const nav = e.target.closest('[data-nav]');
  if (nav){
    const [y,m] = calMonth.split('-').map(Number);
    if (nav.dataset.nav==='today'){ calMonth = TODAY.slice(0,7); calSel = TODAY; }
    else { const d = new Date(y, m-1 + (nav.dataset.nav==='next'?1:-1), 1); calMonth = `${d.getFullYear()}-${pad(d.getMonth()+1)}`; calSel = `${calMonth}-01`; }
    return render();
  }
  const day = e.target.closest('[data-day]'); if (day){ calSel = day.dataset.day; return render(); }
  const op = e.target.closest('[data-open]'); if (op) openSheet(op.dataset.open);
});
(()=>{ let t='plants'; try{ t = localStorage.getItem('wc-tab')||t; }catch(_){} if (location.hash==='#calendar') t='cal'; if (location.hash==='#dashboard') t='dash'; setTab(['cal','dash'].includes(t)?t:'plants'); })();

/* ---------- backup & restore ---------- */
const dataMsg = document.getElementById('dataMsg');
let importing = null;
document.getElementById('exportBtn').addEventListener('click', ()=>{
  if (!plants.length){ dataMsg.className='msg err'; dataMsg.textContent='Nothing to back up yet. Add a plant first.'; return; }
  Store.exportFile(plants, TODAY);
  dataMsg.className='msg'; dataMsg.textContent=`Downloaded a backup of ${plants.length} plant${plants.length===1?'':'s'}.`;
});
document.getElementById('importBtn').addEventListener('click', ()=>document.getElementById('importFile').click());
document.getElementById('importFile').addEventListener('change', async e=>{
  const file = e.target.files[0]; e.target.value=''; if (!file) return;
  try{
    importing = Store.parseImport(await file.text());
    dataMsg.className='msg';
    dataMsg.innerHTML = `${plants.length?`Replace your ${plants.length} plant${plants.length===1?'':'s'} with`:'Load'} the ${importing.length} in this backup?
      <span class="dataacts"><button class="btn water" type="button" id="importYes">${plants.length?'Replace':'Load'}</button><button class="btn ghost" type="button" id="importNo">Cancel</button></span>`;
  }catch(err){ importing=null; dataMsg.className='msg err'; dataMsg.textContent=err.message; }
});
dataMsg.addEventListener('click', e=>{
  if (e.target.id==='importYes' && importing){
    plants = importing; importing = null; save(); render(); updateBanner();
    dataMsg.className='msg'; dataMsg.textContent=`Restored ${plants.length} plant${plants.length===1?'':'s'}.`;
  } else if (e.target.id==='importNo'){ importing=null; dataMsg.textContent=''; }
});

/* ---------- boot ---------- */
plants = Store.load();
seasonLine(); render(); updateBanner();
// Keep other open tabs in sync
window.addEventListener('storage', e=>{
  if (e.key!==Store.KEY) return;
  plants = Store.load(); render(); updateBanner();
  if (sheetId) plants.some(p=>p.id===sheetId) ? openSheet(sheetId) : closeSheet();
});
