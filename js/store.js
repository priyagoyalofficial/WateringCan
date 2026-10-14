/* Persistence: plants live in this browser's localStorage.
   Backup/restore moves them between browsers and devices as a JSON file. */
const Store = (() => {
  const KEY = 'wateringCan.plants.v1';
  let available = true;

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      const data = raw ? JSON.parse(raw) : [];
      return Array.isArray(data) ? data : [];
    } catch (e) {
      available = false;
      return [];
    }
  }

  function saveAll(plants) {
    try {
      localStorage.setItem(KEY, JSON.stringify(plants));
      return true;
    } catch (e) {
      available = false;
      return false;
    }
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

  return { KEY, load, saveAll, exportFile, parseImport, get available() { return available; } };
})();
