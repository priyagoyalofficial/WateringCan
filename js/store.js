/* Persistence: plants live in data/plants.json, saved through the local server (server.py, started by start.bat).
   Each save carries the revision it was based on, so a stale page can't overwrite newer changes
   (from another tab or the plant agent). Backup/restore still moves plants around as a JSON file. */
const Store = (() => {
  const API = '/api/plants';
  const OLD_KEY = 'wateringCan.plants.v1'; // where plants lived before the server existed
  let rev = 0, online = false, chain = Promise.resolve();
  const hooks = { conflict: () => {}, error: () => {}, excelLocked: () => {} };

  async function fetchState() {
    const r = await fetch(API, { cache: 'no-store' });
    if (!r.ok) throw new Error(`Server answered ${r.status}`);
    return r.json();
  }

  /* Plants saved in this browser by the old version move to the file once, if the file is still empty. */
  function oldLocal() {
    try { const d = JSON.parse(localStorage.getItem(OLD_KEY) || '[]'); return Array.isArray(d) ? d : []; }
    catch (e) { return []; }
  }

  async function load() {
    if (location.protocol === 'file:') throw new Error('Opened as a file');
    const s = await fetchState();
    online = true; rev = s.rev;
    const local = oldLocal();
    if (!s.plants.length && local.length) {
      await put(local);
      try { localStorage.removeItem(OLD_KEY); } catch (e) {}
      return local;
    }
    return s.plants;
  }

  async function put(plants) {
    const r = await fetch(API, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rev, plants }),
    });
    const body = await r.json().catch(() => ({}));
    if (r.status === 409) { rev = body.rev; hooks.conflict(body.plants); return; }
    if (!r.ok) throw new Error(body.error || `Server answered ${r.status}`);
    rev = body.rev;
    if (body.excel === false) hooks.excelLocked();
  }

  /* Saves run one at a time, in order. */
  function saveAll(plants) {
    const snapshot = JSON.parse(JSON.stringify(plants));
    chain = chain.then(() => put(snapshot)).catch(e => { online = false; hooks.error(e); });
    return chain;
  }

  /* Returns the plants on disk if someone else changed them since we last loaded or saved, else null. */
  async function refresh() {
    if (!online) return null;
    await chain;
    const s = await fetchState();
    if (s.rev === rev) return null;
    rev = s.rev;
    return s.plants;
  }

  function exportFile(plants, today) {
    const body = JSON.stringify({ app: 'watering-can', version: 1, exported: today, plants }, null, 2);
    const url = URL.createObjectURL(new Blob([body], { type: 'application/json' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `watering-can-backup-${today}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  /* Accepts a backup file (or a bare array) and returns the plant list, or throws with a readable message. */
  function parseImport(text) {
    let data;
    try { data = JSON.parse(text); } catch (e) { throw new Error("That file isn't valid JSON."); }
    const list = Array.isArray(data) ? data : data && data.plants;
    if (!Array.isArray(list)) throw new Error("That file doesn't look like a Watering Can backup.");
    const bad = list.find(p => !p || typeof p !== 'object' || !p.id || !p.name || !p.species);
    if (bad) throw new Error('Some plants in that file are missing a name or type.');
    return list;
  }

  return {
    load, saveAll, refresh, exportFile, parseImport,
    onConflict: f => { hooks.conflict = f; }, onError: f => { hooks.error = f; }, onExcelLocked: f => { hooks.excelLocked = f; },
    get online() { return online; },
  };
})();
