/* Care library and schedule math for Anaheim, CA (USDA zone 10b). */
/* ---------- care library ---------- */
const SPECIES = [
  // indoor
  {k:'pothos',n:'Pothos',l:'Epipremnum aureum',w:'in',days:9,dry:'Top 2 in dry',light:'Medium to bright indirect; handles low light',feed:30,tip:'Leaves soften and droop slightly when thirsty, then perk up within hours of watering.'},
  {k:'monstera',n:'Monstera',l:'Monstera deliciosa',w:'in',days:9,dry:'Top 2–3 in dry',light:'Bright indirect',feed:30,tip:'Yellowing lower leaves with wet soil usually means too much water.'},
  {k:'philo',n:'Heartleaf philodendron',l:'Philodendron hederaceum',w:'in',days:8,dry:'Top 1–2 in dry',light:'Medium indirect',feed:30,tip:'Tolerant and forgiving. Curling leaves mean it wants water.'},
  {k:'snake',n:'Snake plant',l:'Dracaena trifasciata',w:'in',days:21,dry:'Completely dry, top to bottom',light:'Anything from low to bright',feed:60,tip:'Rot is the only real killer. When in doubt, wait another week.'},
  {k:'zz',n:'ZZ plant',l:'Zamioculcas zamiifolia',w:'in',days:21,dry:'Completely dry',light:'Low to bright indirect',feed:60,tip:'Stores water in its rhizomes. Wrinkled stems mean it is finally thirsty.'},
  {k:'peace',n:'Peace lily',l:'Spathiphyllum',w:'in',days:6,dry:'Top 1 in dry',light:'Low to medium indirect',feed:45,tip:'Droops dramatically when thirsty. Water then, but don\'t let it happen often.'},
  {k:'fiddle',n:'Fiddle leaf fig',l:'Ficus lyrata',w:'in',days:10,dry:'Top 2 in dry',light:'Bright, some direct sun',feed:30,tip:'Hates being moved. Brown spots in the middle of leaves usually mean overwatering.'},
  {k:'rubber',n:'Rubber plant',l:'Ficus elastica',w:'in',days:10,dry:'Top 2 in dry',light:'Bright indirect',feed:30,tip:'Drops lower leaves when soil stays wet.'},
  {k:'calathea',n:'Calathea / prayer plant',l:'Goeppertia, Maranta',w:'in',days:6,dry:'Top ½ in dry; keep lightly moist',light:'Medium indirect, no direct sun',feed:30,tip:'Crispy edges come from tap-water minerals and dry air. Use filtered or rain water.'},
  {k:'spider',n:'Spider plant',l:'Chlorophytum comosum',w:'in',days:8,dry:'Top 1 in dry',light:'Bright indirect',feed:30,tip:'Brown tips are often fluoride in tap water, not thirst.'},
  {k:'hoya',n:'Hoya',l:'Hoya spp.',w:'in',days:12,dry:'Mostly dry',light:'Bright indirect, some sun',feed:30,tip:'Likes being snug in its pot. Thin, wrinkly leaves mean it needs water.'},
  {k:'pilea',n:'Chinese money plant',l:'Pilea peperomioides',w:'in',days:8,dry:'Top 1–2 in dry',light:'Bright indirect',feed:30,tip:'Rotate it weekly. Drooping, cupped leaves mean it is thirsty.'},
  {k:'aglaonema',n:'Chinese evergreen',l:'Aglaonema',w:'in',days:10,dry:'Top 2 in dry',light:'Low to medium',feed:45,tip:'Slow grower. It drinks less than you expect.'},
  {k:'dracaena',n:'Dracaena',l:'Dracaena spp.',w:'in',days:12,dry:'Top half dry',light:'Medium indirect',feed:45,tip:'Sensitive to fluoride. Brown tips improve with filtered water.'},
  {k:'anthurium',n:'Anthurium',l:'Anthurium andraeanum',w:'in',days:8,dry:'Top 1–2 in dry',light:'Bright indirect',feed:30,tip:'Needs airy roots. Chunky mix suits it, but soak thoroughly.'},
  {k:'alocasia',n:'Alocasia',l:'Alocasia spp.',w:'in',days:7,dry:'Top 1–2 in dry',light:'Bright indirect',feed:21,tip:'May go dormant and drop leaves in winter. Water much less then.'},
  {k:'bop',n:'Bird of paradise',l:'Strelitzia',w:'in',days:9,dry:'Top 2 in dry',light:'Bright, direct sun ok',feed:21,tip:'Split leaves are normal. Curled leaves mean thirst.'},
  {k:'fern',n:'Boston fern',l:'Nephrolepis exaltata',w:'in',days:4,dry:'Surface just dry; never let it dry out',light:'Medium indirect',feed:30,tip:'Loves humidity. A bathroom window is ideal.'},
  {k:'orchid',n:'Orchid (Phalaenopsis)',l:'Phalaenopsis',w:'in',days:8,dry:'Roots silvery, bark dry',light:'Bright indirect',feed:14,tip:'Soak the pot for 10 minutes, then drain fully. Green roots mean it doesn\'t need water yet.'},
  {k:'violet',n:'African violet',l:'Saintpaulia',w:'in',days:6,dry:'Top just dry',light:'Bright indirect',feed:14,tip:'Water from the bottom. Water on the leaves leaves spots.'},
  {k:'succ',n:'Succulent (Echeveria etc.)',l:'Echeveria, Sedum',w:'in',days:14,dry:'Completely dry',light:'Bright, direct sun',feed:60,tip:'Soak and dry. Soft, squishy leaves mean overwatering; wrinkly leaves mean thirst.'},
  {k:'cactus',n:'Cactus',l:'Cactaceae',w:'in',days:21,dry:'Completely dry for a while',light:'Full sun',feed:60,tip:'In winter, water once a month at most.'},
  {k:'aloe',n:'Aloe vera',l:'Aloe barbadensis',w:'in',days:18,dry:'Completely dry',light:'Bright, direct sun',feed:60,tip:'Thin, curling leaves mean thirst. Mushy base means rot.'},
  {k:'jade',n:'Jade plant',l:'Crassula ovata',w:'in',days:16,dry:'Completely dry',light:'Bright, direct sun',feed:60,tip:'Wrinkled leaves mean water it. It does great outdoors in 10b too.'},
  {k:'pearls',n:'String of pearls',l:'Curio rowleyanus',w:'in',days:12,dry:'Mostly dry',light:'Bright indirect',feed:45,tip:'Shallow roots rot fast. Use a terracotta pot and water lightly.'},
  // outdoor
  {k:'citrus',n:'Citrus in a pot',l:'Citrus spp.',w:'out',days:5,dry:'Top 2 in dry',light:'Full sun',feed:30,tip:'Use a citrus fertilizer. Yellow leaves with green veins mean it is short on iron or nitrogen.'},
  {k:'rose',n:'Rose',l:'Rosa',w:'out',days:4,dry:'Top 1–2 in dry',light:'Full sun, 6+ hours',feed:21,tip:'Water deeply at the base in the morning. Wet leaves invite mildew.'},
  {k:'lavender',n:'Lavender',l:'Lavandula',w:'out',days:10,dry:'Mostly dry',light:'Full sun',feed:0,tip:'Thrives on neglect. Overwatering and rich soil kill it.'},
  {k:'rosemary',n:'Rosemary',l:'Salvia rosmarinus',w:'out',days:9,dry:'Mostly dry',light:'Full sun',feed:0,tip:'Mediterranean plant. Loves 10b and hates soggy roots.'},
  {k:'bougain',n:'Bougainvillea',l:'Bougainvillea',w:'out',days:8,dry:'Top half dry',light:'Full sun',feed:30,tip:'A little drought stress means more flowers. Don\'t pamper it.'},
  {k:'hibiscus',n:'Hibiscus',l:'Hibiscus rosa-sinensis',w:'out',days:3,dry:'Top 1 in dry',light:'Full sun',feed:14,tip:'Very thirsty in summer heat. Dropping buds mean it dried out.'},
  {k:'geranium',n:'Geranium',l:'Pelargonium',w:'out',days:6,dry:'Top 1–2 in dry',light:'Full sun to part shade',feed:21,tip:'Yellow lower leaves mean too much water.'},
  {k:'basil',n:'Basil',l:'Ocimum basilicum',w:'out',days:2,dry:'Top ½ in dry',light:'Full sun',feed:21,tip:'Pinch the flower buds. Wilts fast in afternoon heat.'},
  {k:'mint',n:'Mint',l:'Mentha',w:'out',days:3,dry:'Keep lightly moist',light:'Part sun',feed:30,tip:'Keep it in a pot or it takes over the yard.'},
  {k:'tomato',n:'Tomato (container)',l:'Solanum lycopersicum',w:'out',days:2,dry:'Top 1 in dry',light:'Full sun, 8 hours',feed:14,tip:'Uneven watering causes cracked fruit and blossom-end rot. Keep it steady.'},
  {k:'olive',n:'Olive tree (pot)',l:'Olea europaea',w:'out',days:8,dry:'Top 2–3 in dry',light:'Full sun',feed:45,tip:'Drought tolerant once established. Leaves curl when thirsty.'},
];
const SP = Object.fromEntries(SPECIES.map(s=>[s.k,s]));
const DEFAULT_SP = {n:'Plant',l:'',w:'in',days:7,dry:'Top 1–2 in dry',light:'Bright indirect',feed:30,tip:'Check the soil with your finger before every watering.'};
const SEASON = [1.4,1.3,1.1,1.0,0.95,0.85,0.8,0.8,0.85,0.95,1.15,1.4]; // Anaheim, Jan..Dec
const POT = {plastic:1, terracotta:0.8, selfwater:1.6, ground:1.3};
const WIDTHS = [3,4,5,6,8,10,12,14,16,20];
const potIn = p => ({s:5,m:8,l:12})[p.size] || +p.size || 6;
const sizeFactor = p => clamp(Math.sqrt(potIn(p)/7), 0.7, 1.5);
const MOIST_KEYS = new Set(['fern','calathea','violet','mint','basil','tomato']);
function waterStyle(p){
  const sp = profile(p);
  if (sp.st) return sp.st;
  if (p.species==='orchid') return 'soak';
  if (DRY_KEYS.has(p.species)) return 'dry';
  if (MOIST_KEYS.has(p.species)) return 'moist';
  return 'normal';
}
function cupsText(c){
  const ml = Math.round(c*237/10)*10;
  if (c >= 8){ const qt = Math.round(c/4*2)/2; return `${qt} quarts (${(ml/1000).toFixed(1)} L)`; }
  const q = Math.max(0.25, Math.round(c*4)/4), w = Math.floor(q), f = q-w;
  const fr = f===0.25?'¼':f===0.5?'½':f===0.75?'¾':'';
  return `${w||''}${fr||(w?'':'¼')} cup${q>1?'s':''} (${ml} ml)`;
}
/* Rough pot volume: tapered pot, height ≈ width → ~0.0326·d³ cups. A good soak is ~25% of that. */
function amount(p){
  const d = potIn(p), st = waterStyle(p);
  if (p.pot==='ground') return {short: d>=12?'2–3 gallons, slowly at the base':'1–2 gallons, slowly at the base', how:'Let a hose trickle at the base for 10–15 minutes so the water sinks deep instead of running off. Deep, infrequent watering grows deeper roots.'};
  if (p.soil==='leca') return {short:'Top up the reservoir to ⅓ of the pot height', how:'Keep water only in the bottom third. Let it run out for a day or two before topping up so the roots get air.'};
  if (p.pot==='selfwater') return {short:'Fill the reservoir', how:'Refill only once the reservoir has been empty for a day or two. Keeping it topped up all the time is how self-watering pots rot roots.'};
  if (st==='soak') return {short:'Soak the pot 10 min, then drain', how:'Set the pot in a bowl of room-temperature water for 10 minutes, then lift it out and let it drain completely. Never leave water sitting in the crown or the cachepot.'};
  const frac = st==='dry' ? 0.22 : st==='moist' ? 0.18 : 0.25;
  let c = 0.0326 * d**3 * frac * (p.soil==='chunky'||p.pot==='terracotta' ? 1.1 : 1);
  const bottom = p.species==='violet';
  const how = st==='dry'
    ? 'Soak it thoroughly, then leave it alone. For succulents, how often matters far more than how much. Once the soil is fully dry, water until some runs out the bottom.'
    : st==='moist'
    ? 'Give smaller drinks more often so the soil stays evenly damp, never soggy.'
    : 'Pour slowly over the whole soil surface until about 10–20% runs out the drainage hole.';
  return {short: `About ${cupsText(c)}`, how: `${bottom?'Pour it into the saucer and let the pot drink from below for 20 minutes. ':''}${how} Empty the saucer after 15 minutes, because sitting in runoff rots roots.${p.soil==='chunky'?' Chunky mix drains fast. Pour half, wait 5 minutes, then pour the rest so it can absorb.':''}`};
}
const SOIL = {regular:1, chunky:0.8, cactus:0.9, bark:0.85, leca:1.4, garden:1.1};
const OVER = {in:'Yellow lower leaves, soggy soil, musty smell, mushy stems.',succ:'Soft, translucent, mushy leaves; blackening at the base.'};
const UNDER = {in:'Drooping or curling leaves, crispy edges, soil pulling away from the pot.',succ:'Wrinkled, deflated leaves.'};
const DRY_KEYS = new Set(['snake','zz','succ','cactus','aloe','jade','pearls','lavender','rosemary']);

/* ---------- dates ---------- */
const pad = n=>String(n).padStart(2,'0');
const iso = d=>`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
const parse = s=>{const [y,m,d]=s.split('-').map(Number);return new Date(y,m-1,d)};
const addDays = (s,n)=>{const d=parse(s);d.setDate(d.getDate()+n);return iso(d)};
const diff = (a,b)=>Math.round((parse(b)-parse(a))/864e5);
const TODAY = iso(new Date());
const fmt = s=>parse(s).toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});
const rel = n=> n===0?'today':n===1?'tomorrow':n===-1?'1 day late':n<0?`${-n} days late`:`in ${n} days`;
const esc = s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clamp = (v,a,b)=>Math.min(b,Math.max(a,v));

/* ---------- care math ---------- */
function profile(p){ return p.custom || SP[p.species] || DEFAULT_SP; }
function baseInterval(p, onDate=TODAY){
  const sp = profile(p);
  const m = parse(onDate).getMonth();
  let loc = 1;
  if (p.where==='out' && sp.w==='in') loc = 0.7;
  if (p.where==='in' && sp.w==='out') loc = 1.3;
  return sp.days * SEASON[m] * (POT[p.pot]||1) * sizeFactor(p) * (SOIL[p.soil]||1) * loc;
}
function interval(p, onDate=TODAY){ return Math.max(1, Math.round(baseInterval(p,onDate) * (p.learned||1))); }
function waterStatus(p){
  if (!p.lastWatered) return {kind:'new', due:TODAY, d:0, frac:0, iv:interval(p)};
  const iv = interval(p);
  let due = addDays(p.lastWatered, iv), snoozed = false;
  if (p.checkAfter && p.checkAfter > p.lastWatered){ due = p.checkAfter; snoozed = true; }
  const d = diff(TODAY, due);
  const frac = clamp(1 - diff(p.lastWatered, TODAY)/iv, 0, 1);
  const kind = d<0 ? 'late' : d===0 ? 'today' : snoozed ? 'snooze' : 'ok';
  return {kind, due, d, frac, iv, snoozed};
}
function feedStatus(p){
  const sp = profile(p);
  if (!sp.feed) return {kind:'none'};
  const m = parse(TODAY).getMonth();
  if (m===11||m<=1) return {kind:'rest'};
  const fi = sp.feed * (m===9||m===10 ? 2 : 1);
  if (!p.lastFed) return {kind:'due', due:TODAY, fi};
  const due = addDays(p.lastFed, fi);
  return {kind: due<=TODAY ? 'due' : 'ok', due, fi};
}
function dryDepth(p){ const sp=profile(p); return sp.dry; }
