/* Robo-Kit v2.1 page logic. Engine: robokit.js (+ worker2.js). Chat: assistant.js. Text: strings.js.
 *
 * One rule keeps the page tidy: the thread is the conversation, and state lives in single live cards
 * that update in place (the self-check, the mix). Nothing that describes the current state is ever
 * appended twice, and superseded previews are frozen with a note.
 */
import { Market, buildPortfolio, ladderRow, scoreProfile, searchFunds, trendState, shelfFor, oneFund, planContribution } from './robokit.js';
import { COMMON_WORDS } from './validate.js';
import { icon } from './icons.js';
import { Assistant } from './assistant.js';
import { S } from './strings.js';
import { parseAmount, parseMonthly, parseOpener, isQuestion, BUILD_RX } from './parse.js';

const CLASS_COLOR = { Equity: 'var(--c-equity)', 'Fixed income': 'var(--c-fi)', Cash: 'var(--c-cash)', 'Real estate': 'var(--c-re)', Commodity: 'var(--c-com)', 'Multi-asset': 'var(--c-multi)', Alternative: 'var(--c-alt)', Crypto: 'var(--c-alt)', 'Single stock': 'var(--c-alt)' };
// The self-check: a setup screen, then the scored questions (B2 skipped when there is no withdrawal date)
const STEPS = ['setup', 'A2', 'A3', 'B1', 'B2', 'B4', 'B5', 'C1', 'C2', 'C3', 'C4'];
const SHORT = { A2: { en: 'Emergency savings' }, A3: { en: 'High-interest debt' }, B1: { en: 'When you start taking money out' }, B2: { en: 'How long you take money out' },
  B4: { en: 'Share of your savings' }, B5: { en: 'Income' }, C1: { en: 'One-year range' }, C2: { en: 'After a sharp fall' }, C3: { en: 'Ten-year outcomes' }, C4: { en: 'Losing vs missing out' },
  D1: { en: 'Bond prices' }, D2: { en: 'Leveraged funds' }, A1: { en: 'Goal' } };
const POPULAR = /^(qqq|schd|bito|voo|vti|spy|ivv|vxus|bnd|agg|vea|vwo|iwm|dia|arkk|tqqq|sqqq|soxl|jepi|vig|vym|xeqt|veqt|vgro|xgro|vbal|xbal|vfv|xic|vcn|zag|xaw|vxc|zsp|xuu|hxq|zeb|zcn|xiu)$/;
const CONTEXT_RX = /market|news|war|crash|tariff|geopolit|recession|inflation/i;
const SERIES = { V80691344: { en: 'Bank of Canada 3-month T-bill' }, '^IRX': { en: 'US 13-week T-bill' } };
const FLAG_CONTEXT = { CA: ['vix', 'gpr', 'epu_ca', 'hy_spread', 'ca_policy', 'ca_cpi', 'ca_curve', 'usdcad'], US: ['vix', 'gpr', 'epu_us', 'hy_spread', 'us_curve'] };

const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const store = { get(k, d) { try { const v = localStorage.getItem('robokit2.' + k); return v == null ? d : JSON.parse(v); } catch { return d; } }, set(k, v) { try { if (v == null) localStorage.removeItem('robokit2.' + k); else localStorage.setItem('robokit2.' + k, JSON.stringify(v)); } catch { /* storage off */ } } };
const sym = (t) => String(t || '').replace(/\.(TO|NE)$/, '');
const ordinal = (n) => { const s = ['th', 'st', 'nd', 'rd'], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); };

class App {
  constructor() {
    this.st = { market: store.get('market', 'CA'), tier: store.get('tier', 'default'),
      level: 3, levelChosen: false, amount: 10000, monthly: 0, years: 10, goal: null, mix: this.emptyMix(), mixByMarket: {}, userChanged: false,
      answers: {}, echo: {}, profile: null, explore: null, adult: false, check: { open: false, step: null, reviewing: false, flagsSeen: false, preselect: null, hint: null, knowledge: false },
      ui: { shelf: false, weights: false, draftWeights: null }, ladder: {}, result: null, opener: null, picks: [], textScale: store.get('textScale', 1) };
    this.markets = {}; this.pending = new Map(); this.seq = 0; this.buildSeq = 0; this.live = {}; this.oneFundCache = new Map();
    this.ai = new Assistant(this);
  }
  /** Fees in dollars, saying which held funds have no fee in the data (their cost is not in the figure). */
  feeText(p) { const unk = p.holdings.filter(h => h.mer == null).map(h => h.symbol); return this.fmtMoney(p.stats.fee_per_year) + (unk.length ? this.L.feeExcl(unk.join(', ')) : ''); }
  /** Replace a note in place with another string key (for example once a pre-selected answer has been tapped). */
  rewriteNote(node, key, ...args) {
    if (!node?.isConnected) return;
    const make = () => { const v = this.L[key]; return this.el(`<p class="note">${esc(typeof v === 'function' ? v(...args.map(a => (typeof a === 'function' ? a() : a))) : v)}</p>`, 'turn turn-note'); };
    node.replaceWith(make());
  }
  emptyMix() { return { swaps: {}, satellites: [], exclude: [], minimums: {}, fixedWeights: null, lastFixedWeights: null }; }
  get L() { return S.en; }
  get M() { return this.markets[this.st.market]; }
  get ccy() { return this.st.market === 'CA' ? 'CAD' : 'USD'; }
  levelName(l) { const n = this.core.levels[Math.round(l)]; return n ? n.en : ''; }
  fmtMoney(x) { if (x == null || !Number.isFinite(x)) return '-'; const neg = x < 0 ? '−' : ''; return `${neg}$${Math.round(Math.abs(x)).toLocaleString('en-US')} ${this.ccy}`; }
  /** A monthly flow with its sign spelled out: "+$300 CAD/mo" or "−$1,500 CAD/mo (taking out)". */
  fmtMonthly(v) { return v < 0 ? this.L.monthlyOut(this.fmtMoney(v)) : this.L.monthlyIn(this.fmtMoney(v)); }
  pct(x, d = 0) { return x == null || !Number.isFinite(x) ? '-' : `${(x * 100).toFixed(d)}%`.replace(/^-/, '−'); }
  sgnPct(x, d = 0) { if (x == null) return '-'; const v = Number((x * 100).toFixed(d)); return v === 0 ? `0%` : `${v > 0 ? '+' : '−'}${Math.abs(v).toFixed(d)}%`; }
  fmtAum(x) {
    if (x == null) return '-';
    return x >= 1e9 ? `$${(x / 1e9).toFixed(1)}B` : `$${Math.round(x / 1e6).toLocaleString('en-US')}M`;
  }
  sleeveLabel(h) {
    if (!h.sleeve) return [h.asset_class, h.region].filter(Boolean).join(' · ');  // a pick: its class and region
    return h.sleeve_label || h.asset_class;
  }
  /** Whole percentages that add up to exactly 100 (largest remainder), for the weights grid. */
  toPercents(w) {
    const e = Object.entries(w).filter(([, v]) => v > 0), tot = e.reduce((s, [, v]) => s + v, 0) || 1;
    const rows = e.map(([t, v]) => { const x = v / tot * 100; return [t, Math.floor(x), x - Math.floor(x)]; });
    let left = 100 - rows.reduce((s, r) => s + r[1], 0);
    [...rows].sort((a, b) => b[2] - a[2]).forEach(r => { if (left > 0) { r[1]++; left--; } });
    return Object.fromEntries(rows.map(([t, v]) => [t, v]));
  }
  /** Rebuild, then say in the thread which weights moved (never a silent re-optimisation): funds that came in or went out
   *  first, then the largest changes, then how many others moved by less than half a point. */
  async rebuildMoved(label, { addedTicker = null } = {}) {
    const before = this.st.result, after = await this.rebuild();
    if (!before || !after || after === before) return;
    const wb = new Map(before.holdings.map(h => [h.ticker, h.weight])), wa = new Map(after.holdings.map(h => [h.ticker, h.weight]));
    if (addedTicker && !wa.get(addedTicker)) { this.noteL('addNotHeld', sym(addedTicker)); return; }  // added but given no weight: say so, not "weights moved"
    const all = [...new Set([...wb.keys(), ...wa.keys()])].map(t => [t, wb.get(t) || 0, wa.get(t) || 0]).filter(([, a, b]) => Math.abs(a - b) >= 0.0005);
    if (!all.length) return;
    const added = all.filter(([, a, b]) => !a && b), gone = all.filter(([, a, b]) => a && !b);
    const big = all.filter(([, a, b]) => a && b && Math.abs(a - b) >= 0.005).sort((x, y) => Math.abs(y[2] - y[1]) - Math.abs(x[2] - x[1]));
    const small = all.length - added.length - gone.length - Math.min(4, big.length);
    const [k, ...args] = label;
    this.noteL('movedNote', () => this.L[k](...args), () => {
      const L = this.L, j = '; ';
      const parts = [...added.map(([t, , b]) => L.movedIn(sym(t), this.pct(b, 1))), ...gone.map(([t, a]) => L.movedOut(sym(t), this.pct(a, 1))), ...big.slice(0, 4).map(([t, a, b]) => `${sym(t)} ${this.pct(a, 1)} → ${this.pct(b, 1)}`)];
      return parts.join(j) + (small ? (parts.length ? j : '') + L.movedRest(small, parts.length > 0) : '');
    });
  }
  /** A note with an Undo button; after Undo it says so (doneKey) and the button goes. */
  undoNote(key, undo, { args = [], doneKey = 'undone' } = {}) {
    let used = false;
    const text = (k) => { const v = this.L[k]; return typeof v === 'function' ? v(...args) : v; };
    const make = () => {
      const n = this.el(`<p class="note">${esc(text(used ? doneKey : key))}${used ? '' : ` <button class="link" data-undo>${esc(this.L.undo)}</button>`}</p>`, 'turn turn-note');
      n.querySelector('[data-undo]')?.addEventListener('click', () => { used = true; undo(); n.replaceWith(make()); this.announce(text(doneKey)); });
      return n;
    };
    this.push(make()); this.announce(text(key));
  }
  /** Leave own-weights mode, keeping the weights so they can come back. */
  toModel() { const m = this.st.mix; if (m.fixedWeights) m.lastFixedWeights = m.fixedWeights; m.fixedWeights = null; this.st.ui.weights = false; this.st.userChanged = true; }
  noteText(n) { return typeof n === 'string' ? n : n.en; }
  qText(id) { const it = this.core.questions.find(q => q.id === id); return it ? it.text : id; }
  optText(id, v) { const it = this.core.questions.find(q => q.id === id); const o = it && it.options.find(x => x.value === String(v)); return o ? o.text : String(v); }

  // ---------------------------------------------------------------- boot
  async boot() {
    this.core = await (await fetch('data/core.json')).json();
    await this.loadMarket(this.st.market);
    this.workers = {};
    for (const lane of ['main', 'ladder']) this.startWorker(lane);  // two lanes: the mix never waits behind a ladder
    this.applyTextScale();
    this.bindChrome();
    this.renderChrome();
    this.st.result = buildPortfolio(this.M, this.req({ resample: false }));  // a quick point estimate paints the tray at once
    this.renderTray();
    this.rebuild();
    this.ensureLadder(this.st.market);
    this.ai.init().then(() => this.renderAIState());
    this.offerResume();
  }
  loadMarket(code) {  // one download per market, however many callers ask at once
    this.loading = this.loading || {};
    if (!this.loading[code]) this.loading[code] = fetch(`data/${code.toLowerCase()}.json`).then(r => r.json()).then(j => (this.markets[code] = new Market(this.core, j)));
    return this.loading[code];
  }
  universeSet() { const s = new Set(); for (const M of Object.values(this.markets)) for (const r of M.rows) { s.add(r.yahoo); s.add(r.symbol); } return s; }
  stateNumbers() { return [this.st.level, this.st.amount, this.st.monthly, this.st.years, this.M ? this.M.rows.length : 0, ...(this.st.profile ? [this.st.profile.capacity, this.st.profile.tolerance, this.st.profile.suggested_level] : [])].filter(v => v != null); }
  startWorker(lane) {
    let w; try { w = new Worker('worker2.js', { type: 'module' }); } catch { return; }
    w.onmessage = (ev) => { const p = this.pending.get(ev.data.id); if (!p) return; if (ev.data.partial) { p.onPartial?.(ev.data.rows); return; } this.pending.delete(ev.data.id); ev.data.ok ? p.resolve(ev.data) : p.reject(new Error(ev.data.error)); };
    w.onerror = () => {  // the worker did not load (or died): finish its jobs here instead
      delete this.workers[lane];
      for (const [id, j] of [...this.pending]) if (j.lane === lane) { this.pending.delete(id); this.runLocal(j.type, j.req, j.onPartial, j.code).then(j.resolve, j.reject); }
    };
    this.workers[lane] = w;
  }
  run(type, req, onPartial, code = this.st.market) {
    const lane = type === 'ladder' && this.workers.ladder ? 'ladder' : 'main', w = this.workers[lane];
    if (!w) return this.runLocal(type, req, onPartial, code);
    const id = ++this.seq;
    return new Promise((resolve, reject) => { this.pending.set(id, { resolve, reject, onPartial, type, req, code, lane }); w.postMessage({ id, type, market: code, req }); });
  }
  async runLocal(type, req, onPartial, code) {  // same engine calls on the main thread, yielding between ladder levels
    const M = await this.loadMarket(code);
    if (type === 'build') return { result: buildPortfolio(M, req) };
    if (type === 'onefund') return { result: oneFund(M, req.share, req) };
    const rows = [];
    for (const lvl of [1, 2, 3, 4, 5]) { await new Promise(r => setTimeout(r, 0)); rows.push(ladderRow(M, req, lvl)); onPartial?.(rows.slice()); }
    return { rows };
  }
  req(extra = {}) {
    const m = this.st.mix;
    return { risk_level: this.st.level, levelChosen: !!this.st.levelChosen, swaps: m.swaps, satellites: m.satellites, exclude: m.exclude, minimums: m.minimums, fixedWeights: m.fixedWeights,
      amount: this.st.amount, monthly: this.st.monthly, years: this.st.years, goal: this.st.goal, nBoot: 200, ...extra };
  }
  async rebuild() {
    const my = ++this.buildSeq;
    $('#tray').classList.add('is-busy');
    try {
      const { result } = await this.run('build', this.req());
      if (my !== this.buildSeq) return this.st.result;
      if (this.st.ui.addMoney && this.st.result && JSON.stringify(this.st.result.holdings.map(h => [h.ticker, h.weight])) !== JSON.stringify(result.holdings.map(h => [h.ticker, h.weight]))) this.st.ui.addMoney.result = null;
      this.st.result = result;
      this.renderTray();
      this.refreshMix();
      this.refreshFundCards();
      if (this.st.check.open || this.sheet || this.st.profile) this.ensureLadder();
      this.save();
    } catch (e) { this.note(this.L.error + e.message); }
    finally { if (my === this.buildSeq) $('#tray').classList.remove('is-busy'); }
    return this.st.result;
  }
  /** The ladder behind the self-check scenarios, the chooser and the explore sheet is built from the person's own request
   *  (funds, amount, monthly flow, horizon) with the same draws as the mix, so the row at the current level ties out to it. */
  ladderReq(code = this.st.market) {
    const st = this.st, m = code === st.market ? st.mix : (st.mixByMarket[code] || this.emptyMix());
    return { swaps: m.swaps, satellites: m.satellites, exclude: m.exclude, minimums: m.minimums, amount: st.amount, monthly: st.monthly || 0, years: Math.max(10, st.years), nBoot: 200, seed: 0 };
  }
  ensureLadder(code = this.st.market) {
    const req = this.ladderReq(code), key = JSON.stringify(req), old = this.st.ladder[code];
    if (old && old.key === key) return old.promise;
    const entry = { key, running: true, rows: old?.rows || [] };
    const merge = (rows) => [1, 2, 3, 4, 5].map(l => { const f = rows.find(r => r.level === l); if (f) { f._key = key; return f; } return entry.rows.find(r => r.level === l); }).filter(Boolean);
    this.st.ladder[code] = entry;
    entry.promise = this.run('ladder', req, (rows) => { if (this.st.ladder[code] !== entry) return; entry.rows = merge(rows); document.dispatchEvent(new CustomEvent('ladder')); }, code)
      .then(({ rows }) => { if (this.st.ladder[code] === entry) { entry.rows = merge(rows); entry.done = true; entry.running = false; document.dispatchEvent(new CustomEvent('ladder')); } return rows; },
        (e) => { entry.running = false; if (this.st.ladder[code] === entry) this.note(this.L.error + (e && e.message || e)); return entry.rows; });
    return entry.promise;
  }
  ladderRows() { return this.st.ladder[this.st.market]?.rows || []; }
  /** True when a ladder row was built for exactly this amount and monthly flow (otherwise it is scaled until the new one lands). */
  /** True when a row was built for exactly this request (funds, amount, flow, horizon); a row from before a change is
   *  never shown as the person's numbers: it waits as "updating" until its replacement lands. */
  rowOwn(r) { return !!r && (r._preview || r._key === JSON.stringify(this.ladderReq())); }
  ladderStale() { return this.ladderRows().some(r => !this.rowOwn(r)) || this.ladderRows().length < 5; }
  /** A built mix (a chat preview) seen as a ladder row, so the explore sheet can show the mix that will actually be built. */
  rowFromMix(p) { const pr = p.projection; return { level: Math.round(p.risk.level), one_year: pr.one_year, one_year_value: pr.one_year_value, amount: pr.amount, monthly: pr.monthly_contribution, years: pr.years, withdrawal: pr.withdrawal || null, ten_year: pr.final, stress: p.stress, _preview: true }; }
  /** Money after a year at a row's level, on the person's amount and monthly flow. */
  rowYear(r) { if (r.one_year_value && this.rowOwn(r)) return r.one_year_value; const a = this.st.amount; return Object.fromEntries(['p5', 'p10', 'p50', 'p90'].map(k => [k, a * (1 + r.one_year[k])])); }
  rowTen(r) { const k = this.rowOwn(r) ? 1 : this.st.amount / (r.amount || 10000); return { p10: r.ten_year.p10 * k, p50: r.ten_year.p50 * k, p90: r.ten_year.p90 * k }; }
  /** The money with zero returns after n months: the amount plus (or minus) the monthly flow. */
  flat(n) { return this.st.amount + n * (this.st.monthly || 0); }
  /** A crisis replay in dollars on the person's amount: the engine's own figure when the row was built for them. */
  rowCrisis(r, x) { return x == null || x.portfolio_return == null ? null : (this.rowOwn(r) && x.dollars != null ? x.dollars : this.st.amount * x.portfolio_return); }
  /** A built mix's one-year dollars (with the monthly flow) and the change from zero returns. */
  yearNums(p) {
    const pr = p.projection, v = pr.one_year_value || Object.fromEntries(['p5', 'p10', 'p50', 'p90'].map(k => [k, pr.amount * (1 + pr.one_year[k])]));
    return { ...v, base: pr.amount + 12 * (pr.monthly_contribution || 0) };
  }
  /** Years default from the answers until the person sets them: how long until withdrawals start, or how long they last. */
  autoYears() {
    const st = this.st; if (st.yearsSet) return false;
    const a = st.answers;
    const y = st.monthly < 0 ? ({ once: 2, '2to5': 5, '6to10': 10, '10plus': 25, unsure: 20 }[a.B2] ?? 25) : ({ lt2: 2, '2to4': 4, '5to9': 8, '10to19': 15, '20plus': 25 }[a.B1] ?? st.years);
    if (y === st.years) return false;
    st.years = y; return true;
  }
  refreshFundCards() {
    document.querySelectorAll('.card-fund[data-fund]').forEach(n => {
      const t = n.dataset.fund, b = n.querySelector('[data-add]'); if (!b) return;
      const held = this.st.result?.holdings.find(h => h.ticker === t), pick = this.st.mix.satellites.includes(t), L = this.L;
      const label = held ? `${L.added} · ${this.pct(held.weight, 1)}` : pick ? L.addedNotHeld : null;
      b.disabled = !!label; b.classList.toggle('is-on', !!label); b.innerHTML = label ? esc(label) : icon('plus', 14) + ' ' + esc(L.add);
    });
  }
  trayTickers() { return (this.st.result?.holdings || []).map(h => h.ticker); }

  // ---------------------------------------------------------------- persistence (per-viewer convenience only)
  save() {
    clearTimeout(this.saveT);
    this.saveT = setTimeout(() => {
      const s = this.st;
      if (!Object.keys(s.answers).length && !s.userChanged) return;
      store.set('state', { v: 2, at: new Date().toISOString(), market: s.market, level: s.level, levelChosen: s.levelChosen, amount: s.amount, monthly: s.monthly, years: s.years, goal: s.goal,
        answers: s.answers, echo: s.echo, adult: s.adult, explore: s.explore, mix: s.mix, mixByMarket: s.mixByMarket, userChanged: s.userChanged, checked: !!s.profile && !s.check.open });
    }, 300);
  }
  offerResume() {
    const saved = store.get('state', null);
    if (!saved || saved.v !== 2 || (!Object.keys(saved.answers || {}).length && !saved.userChanged)) return;
    this.push(this.resumeNode(saved), { key: 'resume', keepLanding: true });
  }
  resumeNode(saved) {
    const L = this.L, n = STEPS.filter(x => x !== 'setup' && (saved.answers || {})[x] != null).length;
    const node = (this.el(`<h3>${esc(L.resumeTitle)}</h3><p class="muted">${esc(saved.mix?.fixedWeights ? L.resumeOwn(Object.keys(saved.mix.fixedWeights).length, `$${Math.round(saved.amount).toLocaleString('en-US')} ${saved.market === 'CA' ? 'CAD' : 'USD'}`, n) : L.resumeLine(saved.level, n, `$${Math.round(saved.amount).toLocaleString('en-US')} ${saved.market === 'CA' ? 'CAD' : 'USD'}`))}</p>
      <div class="row"><button class="btn primary" data-resume>${esc(L.resume)}</button><button class="btn ghost" data-fresh>${esc(L.freshStart)}</button></div>`, 'card card-resume'));
    node.querySelector('[data-resume]').addEventListener('click', async () => {
      this.live.resume?.remove(); delete this.live.resume;
      if (saved.market !== this.st.market) await this.setMarket(saved.market, { keepMix: true });
      Object.assign(this.st, { level: saved.level, levelChosen: saved.levelChosen ?? !!saved.userChanged, amount: saved.amount, monthly: saved.monthly || 0, years: saved.years || 10, goal: saved.goal ?? null, answers: saved.answers || {}, echo: saved.echo || {},
        adult: !!saved.adult, explore: saved.explore || null, mix: { ...this.emptyMix(), ...(saved.mix || {}) }, mixByMarket: saved.mixByMarket || {}, userChanged: !!saved.userChanged });
      this.st.profile = Object.keys(this.st.answers).length ? scoreProfile(this.core.questions, this.cleanAnswers()) : null;
      if (this.st.profile && saved.checked) this.renderCheck();
      else if (Object.keys(this.st.answers).length) this.openCheck();
      if (!this.reconcileLevel()) this.renderTray();  // the same status rules as every other path (an unconfirmed level moves)
      await this.rebuild();
      await this.showMix({ scroll: false, focus: !this.st.check.open });
    });
    node.querySelector('[data-fresh]').addEventListener('click', () => { this.live.resume?.remove(); delete this.live.resume; store.set('state', null); });
    return node;
  }

  // ---------------------------------------------------------------- chrome
  bindChrome() {
    const form = $('#composer');
    form.addEventListener('submit', (e) => { e.preventDefault(); const t = $('#q').value.trim(); if (t) { $('#q').value = ''; this.autosize(); this.onInput(t); } });
    $('#q').addEventListener('input', () => this.autosize());
    $('#q').addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); form.requestSubmit(); } });
    $('#stop').addEventListener('click', () => this.ctl?.abort());
    document.querySelectorAll('[data-market]').forEach(b => b.addEventListener('click', () => this.setMarket(b.dataset.market)));
    $('#textsize').addEventListener('click', () => { const s = this.st.textScale; this.st.textScale = s >= 1.3 ? 1 : s >= 1.15 ? 1.3 : 1.15; store.set('textScale', this.st.textScale); this.applyTextScale(); });
    $('#settings-btn').addEventListener('click', () => { const p = $('#settings'); p.hidden = !p.hidden; $('#settings-btn').setAttribute('aria-expanded', String(!p.hidden)); });
    document.addEventListener('click', (e) => { const p = $('#settings'); if (!p.hidden && !p.contains(e.target) && !$('#settings-btn').contains(e.target)) { p.hidden = true; $('#settings-btn').setAttribute('aria-expanded', 'false'); } });
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      if (this.sheet) { this.closeSheet('dismissed'); return; }
      if (!$('#settings').hidden) { $('#settings').hidden = true; $('#settings-btn').setAttribute('aria-expanded', 'false'); $('#settings-btn').focus(); return; }
      if (document.body.classList.contains('tray-open')) this.toggleTray(false);
    });
    document.querySelectorAll('input[name="tier"]').forEach(r => r.addEventListener('change', () => { this.st.tier = r.value; store.set('tier', r.value); }));
    document.querySelectorAll('[data-chip]').forEach(c => c.addEventListener('click', () => this.onChip(c.dataset.chip)));
    $('#tray-toggle').addEventListener('click', () => this.toggleTray());
    $('#tray-close').addEventListener('click', () => this.toggleTray(false));
    $('#tray-done').addEventListener('click', () => this.toggleTray(false));
    // a tap outside the open phone tray closes it (the path is read at click time: a level tap re-renders its button)
    document.addEventListener('click', (e) => { const path = e.composedPath ? e.composedPath() : [e.target]; if (document.body.classList.contains('tray-open') && this.narrow.matches && !path.includes($('#tray')) && !path.some(n => n.classList?.contains('sheet-wrap'))) this.toggleTray(false); });
    this.narrow = matchMedia('(max-width: 1099px)');
    this.narrow.addEventListener?.('change', () => this.trayInert());
    this.trayInert();
    document.addEventListener('ladder', () => { const c = this.st.check; if (c.open && ['C1', 'C3', 'result'].includes(c.step)) this.renderCheck(); this.sheet?._redraw?.(); });
    $('#sources').addEventListener('click', (e) => { e.preventDefault(); this.cardSources(); });
  }
  applyTextScale() {
    const s = this.st.textScale, b = $('#textsize'); document.documentElement.style.setProperty('--text-scale', String(s));
    if (!b) return; b.setAttribute('aria-pressed', String(s > 1)); b.textContent = s >= 1.3 ? 'A++' : 'A+'; b.setAttribute('aria-label', `${this.L.textSize}: ${s >= 1.3 ? this.L.textLargest : s > 1 ? this.L.textLarger : this.L.textNormal}`);
  }
  toggleTray(open) {
    const on = open ?? !document.body.classList.contains('tray-open');
    document.body.classList.toggle('tray-open', on);
    $('#tray-toggle').setAttribute('aria-expanded', String(on));
    this.trayInert(); this.peekLabel();
    if (on) $('#tray-close').focus(); else $('#tray-toggle').focus();
  }
  /** On a phone the collapsed tray keeps only its toggle in the Tab order; the open tray keeps focus inside it. */
  trayInert() {
    const narrow = this.narrow?.matches, open = document.body.classList.contains('tray-open');
    for (const el of $('#tray').children) if (el.id !== 'tray-toggle') el.inert = !!narrow && !open;
    for (const el of [$('main .col'), $('header.top'), $('#footer')]) if (el) el.inert = !!narrow && open;
  }
  autosize() { const q = $('#q'); q.style.height = 'auto'; q.style.height = Math.min(q.scrollHeight, 160) + 'px'; q.style.overflowY = q.scrollHeight > 160 ? 'auto' : 'hidden'; }
  renderChrome() {
    const L = this.L, st = this.st;
    document.documentElement.lang = 'en';
    $('#tagline').textContent = L.tagline;
    $('#textsize').setAttribute('aria-label', L.textSize);
    document.querySelectorAll('[data-market]').forEach(b => { const on = b.dataset.market === st.market; b.setAttribute('aria-pressed', String(on)); b.innerHTML = `${esc(b.dataset.market === 'CA' ? L.ca : L.us)} <span>${esc(b.dataset.market === 'CA' ? L.caSub : L.usSub)}</span>`; });
    $('#hero-title').textContent = L.heroTitle;
    $('#hero-sub').textContent = L.heroSub(this.countListings('CA'), this.countListings('US'));
    $('#q').placeholder = L.placeholder; requestAnimationFrame(() => this.autosize());
    $('#q').setAttribute('aria-label', L.placeholder);
    $('#send').setAttribute('aria-label', L.send); $('#stop').setAttribute('aria-label', L.stop);
    $('#send').innerHTML = icon('arrow-up', 18); $('#stop').innerHTML = icon('stop', 16);
    $('#settings-btn').innerHTML = `${icon('sparkle', 16)}<span>${esc(L.settings)}</span>`; $('#settings-btn').setAttribute('aria-label', L.settings);
    const chips = { build: L.chipBuild, etf: L.chipEtf, compare: L.chipCompare, market: L.chipMarket };
    document.querySelectorAll('[data-chip]').forEach(c => { c.textContent = chips[c.dataset.chip]; });
    $('#data-line').textContent = L.dataLine(this.core.meta.prices_through);
    $('#sources').textContent = L.sources;
    $('#footer').textContent = L.footer;
    $('#tier-legend').textContent = L.tierLabel;
    $('#tier-quick').textContent = L.tierQuick; $('#tier-default').textContent = L.tierDefault; $('#tier-complex').textContent = L.tierDeep;
    $('#tier-note').textContent = L.tierNote;
    $('#tray-close').setAttribute('aria-label', L.closeMix); $('#tray-done').textContent = L.done;
    $('#mkt-group').setAttribute('aria-label', L.market); $('#chip-group').setAttribute('aria-label', L.suggestions);
    $('#tray').setAttribute('aria-label', L.trayTitle); $('#q').setAttribute('aria-label', L.messageLabel);
    this.applyTextScale();
    const r = document.querySelector(`input[name="tier"][value="${st.tier}"]`); if (r) r.checked = true;
    this.renderAIState();
  }
  countListings(code) { const n = { CA: 2187, US: 5770 }; return this.markets[code] ? this.markets[code].rows.length : n[code]; }
  renderAIState() {
    const L = this.L;
    $('#disclosure').textContent = this.ai.available ? L.disclosureAI : L.disclosureNoAI;
    $('#ai-state').textContent = this.ai.available ? L.aiOn : L.aiOff;
    $('#ai-state').dataset.on = String(this.ai.available);
  }
  async setMarket(code, { keepMix = false, quiet = false } = {}) {
    if (code === (this.wantMarket ?? this.st.market)) return;
    this.wantMarket = code;
    await this.loadMarket(code);  // switch only once the data is here, and only if no later click changed the choice
    if (this.wantMarket !== code) return;
    if (!keepMix) { this.st.mixByMarket[this.st.market] = this.st.mix; this.st.mix = this.st.mixByMarket[code] || this.emptyMix(); }
    const from = this.st.market;
    this.st.market = code; store.set('market', code);
    if (!quiet && !keepMix && from !== code && (this.st.answers.B3 || this.st.userChanged) && !(this.st.check.open && this.st.check.step === 'setup')) {
      const mo = this.st.monthly;
      this.noteL('amountKept', `$${Math.round(this.st.amount).toLocaleString('en-US')}`, this.ccy, mo ? () => this.fmtMonthly(mo) : '');
    }
    if (from !== code) document.querySelectorAll('.card-prop:not(.is-done)').forEach(n => this.resolveProp(n, 'propOtherMarket'));  // made for the other market's funds
    this.renderChrome();
    this.st.result = buildPortfolio(this.M, this.req({ resample: false }));
    this.renderTray(); this.refreshMix(); this.rebuild(); this.ensureLadder(code);
    if (this.st.check.open) this.renderCheck();
  }

  // ---------------------------------------------------------------- thread
  thread() { return $('#thread'); }
  /** Append a node; with {key}, keep one live copy (re-render in place). While the self-check is open it stays last. */
  /** Where focus sat inside a card, as a selector and index, so a re-rendered copy can take it back. */
  focusSpot(root) {
    const a = document.activeElement; if (!a || !root.contains(a) || a === root) return null;
    const mark = (el) => [...el.attributes].find(x => x.name.startsWith('data-') && x.name !== 'data-live');
    const attr = (d) => `[${d.name}${d.value ? `="${CSS.escape(d.value)}"` : ''}]`;
    const d = mark(a);
    let sel = d ? `${a.tagName.toLowerCase()}${attr(d)}` : a.id ? `#${CSS.escape(a.id)}` : null;
    if (!sel) { let anc = a.parentElement; while (anc && anc !== root && !mark(anc)) anc = anc.parentElement; sel = (anc && anc !== root ? attr(mark(anc)) + ' ' : '') + a.tagName.toLowerCase(); }
    return { sel, i: [...root.querySelectorAll(sel)].indexOf(a) };
  }
  push(node, { key = null, scroll = true, keepLanding = false } = {}) {
    if (!keepLanding) document.body.classList.remove('is-landing');
    if (key && this.live[key]?.isConnected) {
      const spot = this.focusSpot(this.live[key]);
      this.live[key].replaceWith(node);
      const found = spot && node.querySelectorAll(spot.sel)[Math.max(0, spot.i)];
      if (spot && !found) node._pendingSpot = spot;  // restored once the card's slots are filled (renderMix)
      const t = spot && (found || node.querySelector('h3'));
      if (t) { if (!t.matches('a[href],button,input,select,textarea,summary,[tabindex]')) t.setAttribute('tabindex', '-1'); t.focus({ preventScroll: true }); }
    }
    else {
      const anchor = this.st.check.open && this.live.check?.isConnected && key !== 'check' ? this.live.check : null;
      if (anchor) this.thread().insertBefore(node, anchor); else this.thread().appendChild(node);
    }
    if (key) { this.live[key] = node; node.dataset.live = key; }
    if (scroll) requestAnimationFrame(() => node.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: key === 'mix' ? 'start' : 'nearest' }));
    return node;
  }
  el(html, cls = 'card') { const d = document.createElement('section'); d.className = cls; d.innerHTML = html; return d; }
  userBubble(text) { return this.push(this.el(`<p>${esc(text)}</p>`, 'turn turn-user')); }
  note(text) { return this.push(this.el(`<p class="note">${esc(text)}</p>`, 'turn turn-note')); }
  /** A note written from a string key; arguments may be functions. */
  noteL(key, ...args) {
    const make = () => { const v = this.L[key]; return this.el(`<p class="note">${esc(typeof v === 'function' ? v(...args.map(a => (typeof a === 'function' ? a() : a))) : v)}</p>`, 'turn turn-note'); };
    const n = this.push(make()); this.announce(n.textContent); return n;
  }
  /** Live-region messages sent within a moment of each other are joined, so a note is not wiped by the "Mix updated" after it. */
  announce(text) {
    const a = $('#announcer'); if (!a || !text) return;
    this.annText = this.annPending ? `${this.annText} ${text}` : text; this.annPending = true;
    clearTimeout(this.annT); a.textContent = '';
    this.annT = setTimeout(() => { a.textContent = this.annText; this.annPending = false; }, 60);
  }

  async onChip(kind) {
    if (kind === 'build') this.openCheck();
    else if (kind === 'etf') this.cardTerm('etf');
    else if (kind === 'compare') { $('#q').value = ''; $('#q').placeholder = this.L.compareHint; $('#q').focus(); }
    else if (kind === 'market') this.cardContext();
  }

  async onInput(text) {
    this.userBubble(text);
    const facts = parseOpener(text);
    const first = !this.st.openerDone; this.st.openerDone = true;
    const fresh = first && !Object.keys(this.st.answers).length && !this.st.userChanged;
    const tickers = await this.tickersIn(text);
    if (fresh && (facts.amount || facts.goal || facts.market || facts.monthly || facts.amountChoices || tickers.length)) await this.applyOpener(facts, text, tickers);
    else if (!fresh && !isQuestion(text)) this.offerFacts(facts);
    if (this.st.check.open && this.matchTyped(text)) return;
    if (tickers.length === 1 && text.replace(/[^A-Za-z.\-]/g, '').length <= tickers[0].length + 2) { this.cardFund(tickers[0]); return; }
    if (!this.ai.available) return this.route(text, tickers, facts);
    await this.askAI(text);
  }
  /** Tickers in a message, from either market: the other market's list loads when a word looks like a ticker it may hold. */
  async tickersIn(text) {
    const other = this.st.market === 'CA' ? 'US' : 'CA';
    if (!this.markets[other]) {
      const words = [...text.matchAll(/(?<![A-Za-z0-9])([A-Za-z]{2,5})(?:\.(?:TO|to|NE|ne))?(?![A-Za-z0-9])/g)].map(m => m[1]);
      const maybe = words.filter(w => (w === w.toUpperCase() && !COMMON_WORDS.has(w)) || POPULAR.test(w.toLowerCase()));
      if (maybe.some(w => !this.resolveFund(w))) await this.loadMarket(other).catch(() => null);
    }
    return this.findTickers(text);
  }
  async applyOpener(f, text, tickers) {
    const build = BUILD_RX.test(text) || (!!f.amount && !isQuestion(text));
    const markets = [...new Set(tickers.map(t => this.resolveFund(t)?.market).filter(Boolean))];
    const inferred = !f.market && build && markets.length === 1 ? markets[0] : null;  // "qqq schd bito, 5k" means the US list
    this.st.opener = { ...f, market: f.market || inferred, inferred: !!inferred, tickers };
    if (f.amount) { this.st.amount = f.amount; this.st.answers.B3 = String(f.amount); }
    if (f.monthly) this.st.monthly = f.monthly;
    if (f.goal) this.st.answers.A1 = f.goal;
    const mk = f.market || inferred;
    if (mk && mk !== this.st.market) await this.setMarket(mk, { quiet: true });  // nothing was converted: the amount was typed for this market
    this.st.picks = tickers.filter(t => this.resolveFund(t)?.market === this.st.market);
    this.renderTray(); this.rebuild();
    if (build) this.openCheck();
  }
  /** Numbers in a later message are offered as a button, never applied silently. */
  offerFacts(f) {
    const L = this.L, st = this.st, offers = [];
    if (f.amount && f.amount !== st.amount) offers.push(['amount', f.amount, L.useAmount(this.fmtMoney(f.amount))]);
    if (f.monthly && f.monthly !== st.monthly) offers.push(['monthly', f.monthly, L.useMonthly(this.fmtMonthly(f.monthly))]);
    if (!offers.length) return;
    const node = this.push(this.el(`<p class="small muted">${esc(L.factsSeen)}</p><div class="row">${offers.map(([k, v, label]) => `<button class="btn small" data-fact="${k}" data-v="${v}">${esc(label)}</button>`).join('')}<button class="link" data-nofact>${esc(L.dismiss)}</button></div>`, 'turn turn-note turn-offer'));
    const done = (text) => { node.querySelectorAll('button').forEach(b => { b.disabled = true; }); const p = document.createElement('p'); p.className = 'small muted'; p.textContent = text; node.appendChild(p); };
    node.querySelectorAll('[data-fact]').forEach(b => b.addEventListener('click', () => {
      const v = Number(b.dataset.v);
      if (b.dataset.fact === 'amount') { st.amount = v; st.answers.B3 = String(v); } else st.monthly = v;
      st.check.draft = null;
      this.renderTray(); this.rebuild();
      if (st.check.open && st.check.step === 'setup') this.renderCheck();
      this.refreshMix(); done(L.factUsed); this.save();
    }));
    node.querySelector('[data-nofact]').addEventListener('click', () => done(L.propDismissed));
  }
  findTickers(text) {
    // A ticker is a word typed in capitals (VFV, XEQT) or with an exchange suffix (vfv.to), or a message that is
    // only one short word ("vfv"). Lower-case words are never tickers: "the", "war", "bond" are also listed funds.
    const out = [], raw = [];
    const lone = text.trim().match(/^[A-Za-z]{2,5}(?:[.-][A-Za-z]{1,2})?(?:\.(?:to|ne|TO|NE))?$/);
    if (lone) raw.push(lone[0]);
    for (const m of text.matchAll(/(?<![A-Za-z0-9])([A-Z]{2,5}(?:[.-][A-Z]{1,2})?(?:\.(?:TO|NE))?|[A-Za-z]{2,5}(?:-[A-Za-z])?\.(?:to|ne|TO|NE))(?![A-Za-z0-9])/g)) {
      if (/\.(?:to|ne)$/i.test(m[1]) || !COMMON_WORDS.has(m[1])) raw.push(m[1]);
    }
    // short lower-case tickers typed in a list ("qqq schd bito") count when every word is a known fund
    const words = text.toLowerCase().split(/[\s,;]+/).filter(Boolean);
    if (words.length >= 2 && words.every(w => /^[a-z]{2,5}$/.test(w) && this.resolveFund(w.toUpperCase()) && !COMMON_WORDS.has(w.toUpperCase()))) raw.push(...words.map(w => w.toUpperCase()));
    for (const w of text.split(/[\s,;.]+/)) if (/^[a-z]{3,5}$/.test(w) && !COMMON_WORDS.has(w.toUpperCase()) && POPULAR.test(w)) raw.push(w.toUpperCase());
    for (const r of raw) { const f = this.resolveFund(r); if (f && !out.includes(f.yahoo)) out.push(f.yahoo); }
    return out;
  }
  resolveFund(t) {
    const T = String(t).toUpperCase().trim();
    const order = [this.st.market, this.st.market === 'CA' ? 'US' : 'CA'];
    for (const code of order) { const f = this.markets[code]?.byTicker.get(T); if (f) return { ...f, market: code }; }  // exact ticker first
    for (const code of order) {
      const M = this.markets[code]; if (!M) continue;
      const f = M.byTicker.get(T + '.TO') || M.byTicker.get(T.replace('.', '-') + '.TO') || M.byTicker.get(T + '.NE') || M.rows.find(r => r.symbol === T);
      if (f) return { ...f, market: code };
    }
    return null;
  }
  route(text, tickers, facts = {}) {
    const L = this.L;
    if (BUILD_RX.test(text) || /^(build|portfolio)$/i.test(text.trim()) || (facts.amount && !tickers.length)) return this.openCheck();
    if (tickers.length >= 2) return this.cardCompare(tickers);
    if (tickers.length === 1) return this.cardFund(tickers[0]);
    const term = this.matchTerm(text); if (term) return this.cardTerm(term);
    if (CONTEXT_RX.test(text)) return this.cardContext();
    this.noteL('noAIroute');
    const words = text.replace(/[^\p{L}\p{N}\s&/-]/gu, ' ').trim();
    const r = searchFunds(this.M, { query: words.split(/\s+/).filter(w => w.length > 2).slice(-2).join(' '), limit: 8 });
    if (r.results.length) this.cardResults(r);
  }
  matchTerm(text) {
    const t = text.toLowerCase();
    const map = [['mer', /\bmer\b|expense|fee/], ['volatility', /volatil/], ['leverage', /leverag|inverse|2x|3x/], ['hedged', /hedg/], ['bond_prices_rates', /bond.*rate|rate.*bond/], ['bond', /\bbonds?\b/], ['tfsa_rrsp', /tfsa|rrsp/], ['etf', /what is an etf|\betf\b.*\?/], ['diversification', /diversif/], ['rebalancing', /rebalanc/], ['drawdown', /drawdown/], ['reit', /\breits?\b/], ['resampling', /resampl/], ['equilibrium_return', /equilibrium/], ['sharpe', /sharpe/]];
    for (const [k, re] of map) if (re.test(t)) return k;
    return null;
  }

  // ---------------------------------------------------------------- chat
  async askAI(text) {
    const L = this.L;
    const node = this.push(this.el(`<header class="who">${icon('sparkle', 14)}<span data-k="guide">${esc(L.guide)}</span></header><div class="ai-text" aria-live="polite"><span class="thinking">${esc(L.thinking)}</span></div><footer class="ai-foot" hidden></footer>`, 'turn turn-ai'));
    const out = $('.ai-text', node);
    this.aiNode = node;
    this.ctl = new AbortController();
    document.body.classList.add('is-streaming');
    try {
      const res = await this.ai.ask(text, { tier: this.st.tier, signal: this.ctl.signal, onText: ({ text: t }) => { out.innerHTML = this.md(t); } });
      out.innerHTML = this.md(res.text, res.check.unsupported_numbers);
      const bad = [...res.check.unsupported_numbers, ...res.check.unknown_tickers];
      const foot = $('.ai-foot', node);
      node._foot = () => {
        const L2 = this.L;
        if (bad.length) { foot.hidden = false; foot.innerHTML = `<span class="warn">${icon('warning', 14)}${esc(L2.notFromTool)} ${esc(bad.join(', '))}</span>`; }
        else if (/\d/.test(res.text) && res.toolCalls) { foot.hidden = false; foot.innerHTML = `${icon('check', 14)}<span>${esc(L2.checked)}${res.retried ? ', ' + esc(L2.rewritten) : ''}.</span>`; }
      };
      node._foot();
    } catch (e) {
      const code = e && e.code;
      if (code === 'cancelled') { out.innerHTML = this.md(e.text || ''); }
      else if (code === 'not_granted' || code === 'sampling_disabled' || code === 'capability_disabled' || code === 'not_declared') { this.ai.available = false; this.renderAIState(); out.textContent = L.declined; this.route(text, this.findTickers(text)); }
      else if (code === 'rate_limited') out.textContent = L.rate;
      else if (code === 'refused') out.textContent = L.refused;
      else { out.innerHTML = this.md(e && e.text ? e.text : '') + `<p class="note">${esc(L.error + (e && (e.message || e.code) || ''))}</p>`; }
    } finally { document.body.classList.remove('is-streaming'); this.ctl = null; this.aiNode = null; }
  }
  md(t, flag = []) {
    // minimal, safe Markdown: paragraphs, bullets, bold, links; flag unsupported numbers in visible text only
    let h = esc(t || '');
    h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    const blocks = h.split(/\n{2,}/).map(b => /^\s*[-*] /m.test(b) ? `<ul>${b.split(/\n/).filter(x => x.trim()).map(li => `<li>${li.replace(/^\s*[-*] /, '')}</li>`).join('')}</ul>` : `<p>${b.replace(/\n/g, '<br>')}</p>`);
    const html = blocks.join('');
    const marks = flag.filter(Boolean);
    if (!marks.length) return html;
    const tpl = document.createElement('template'); tpl.innerHTML = html;
    const re = new RegExp(marks.map(f => f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'g');
    const walker = document.createTreeWalker(tpl.content, NodeFilter.SHOW_TEXT); const texts = [];
    while (walker.nextNode()) texts.push(walker.currentNode);
    for (const n of texts) {
      const v = n.nodeValue; re.lastIndex = 0; if (!re.test(v)) continue;
      const frag = document.createDocumentFragment(); let last = 0; re.lastIndex = 0;
      for (const m of v.matchAll(re)) { frag.append(v.slice(last, m.index)); const mk = document.createElement('mark'); mk.title = 'not from a tool'; mk.textContent = m[0]; frag.append(mk); last = m.index + m[0].length; }
      frag.append(v.slice(last)); n.replaceWith(frag);
    }
    return tpl.innerHTML;
  }

  // ---------------------------------------------------------------- tools for the assistant (compact, JSON-safe)
  compactFund(f) { return { ticker: f.yahoo, symbol: f.symbol, name: f.name, asset_class: f.asset_class, region: f.region, theme: f.theme || null, mer: f.mer, aum_millions: f.aum == null ? null : Math.round(f.aum / 1e6), history_months: f.history_months, return_1y: f.ret_1y, return_5y_per_year: f.ret_5y, worst_drop: f.max_drawdown, distribution_yield: f.dividend_yield, hedged: f.hedged, currency: f.currency, eligible: f.eligible, excluded_because: f.excluded_because || null }; }
  toolSearch(i) {
    const r = searchFunds(this.M, { query: i.query || '', assetClass: i.asset_class || null, region: i.region || null, maxMer: i.max_mer ?? null, sortBy: i.sort_by || 'mer', eligibleOnly: !i.include_excluded, limit: 8 });
    if (r.results.length) this.cardResults(r);
    return { market: r.market, matches: r.matches, sorted_by: r.sorted_by, as_of: r.as_of, funds: r.results.map(f => this.compactFund(f)) };
  }
  toolProfile(i) { const f = this.resolveFund(i.ticker || ''); if (!f) return { found: false, ticker: i.ticker }; this.cardFund(f.yahoo); return { found: true, market: f.market, ...this.compactFund(f), classification_notes: f.why || null, trend: trendState(this.markets[f.market], f.yahoo), as_of: this.core.meta.prices_through }; }
  toolCompare(i) { const ts = (i.tickers || []).map(t => this.resolveFund(t)).filter(Boolean).map(f => f.yahoo).slice(0, 5); if (ts.length < 2) return { error: 'need at least two known tickers' }; const card = this.cardCompare(ts); return { funds: ts.map(t => this.compactFund(this.resolveFund(t))), correlation_5y: card.corr, as_of: this.core.meta.prices_through }; }
  async toolCurrentMix() { const p = this.st.result || await this.rebuild(); return this.mixSummary(p); }
  mixSummary(p) {
    const s = p.stats, pr = p.projection;
    return { market: p.market, currency: p.currency, as_of: p.as_of, mode: p.mode, level: p.risk.level, level_name: p.risk.label,
      above_self_check: (() => { const lv = Math.round(p.risk.level); return p.mode !== 'own_weights' && this.isAbove(lv) ? { level: lv, suggested: this.st.profile.suggested_level, confirmed_on_explore_sheet: this.consented(lv) } : null; })(), level_chosen_by_person: !!this.st.levelChosen,
      funds: p.holdings.map(h => ({ ticker: h.ticker, symbol: h.symbol, name: h.name, asset_class_slot: h.sleeve_label, slot_key: h.sleeve, weight: h.weight, dollars: h.dollars, units: h.units, price: h.price, price_date: h.price_date, fee: h.mer })),
      cash_left: s.cash_left, mix_by_asset_class: p.mix.asset_class, volatility: s.volatility, planning_return_a_year: s.planning_return, fees_a_year_dollars: s.fee_per_year, fee_rate: s.weighted_mer,
      amount: pr.amount, monthly: pr.monthly_contribution, years: pr.years, one_year: pr.one_year, one_year_dollars: pr.one_year_value || pr.one_year_dollars,
      one_year_dollars_basis: pr.monthly_contribution ? 'money at the end of one year: the amount plus 12 months of the monthly flow (the page headline uses these)' : 'money at the end of one year on the amount', fees_note: p.holdings.some(h => h.mer == null) ? `fees leave out ${p.holdings.filter(h => h.mer == null).map(h => h.symbol).join(', ')} (no fee in the data)` : null, horizon_outcomes: { years: pr.years, ...pr.final }, withdrawal: pr.withdrawal || null, goal: pr.goal || null, chance_need_to_adjust: pr.chance_need_to_adjust ?? null,
      levels_in_chooser: this.ladderRows().filter(r => this.rowOwn(r)).map(r => ({ level: r.level, bad_year_value: Math.round(this.rowYear(r).p5), crisis_2008_dollars: (() => { const v = this.rowCrisis(r, r.stress?.find(s => s.key === 'gfc')); return v == null ? null : Math.round(v); })(), money_lasted_share: this.rowOwn(r) ? r.withdrawal?.chance_lasts ?? null : null, built_for_this_request: this.rowOwn(r) })),
      stress_tests: p.stress.map(x => ({ scenario: x.scenario, portfolio_return: x.portfolio_return, dollars: x.dollars, estimated_funds: x.estimated })),
      not_held_picks: this.notHeld(p), explanation_en: p.explanation.en, checks: p.checks.map(c => ({ en: c.en })), notes: p.notes };
  }
  notHeld(p) { const held = new Set(p.holdings.map(h => h.ticker)); return [...this.st.mix.satellites, ...Object.keys(this.st.mix.fixedWeights || {})].filter(t => !held.has(t)); }
  profileSummary() {
    const p = this.st.profile; if (!p) return null;
    return { status: p.status, suggested_level: p.suggested_level, capacity: p.capacity, tolerance: p.tolerance, binding: p.binding, gate_cap: p.gate_cap, within_check: p.within_check,
      binding_answers: (p.binding_answers || []).map(b => ({ question: b.question_en, answer: b.answer_en, effect: b.effect_en })),
      explanation: p.explanation.en, gates: p.gates.map(g => ({ id: g.id, text: g.en })) };
  }
  openQuestion() {
    const c = this.st.check; if (!c.open || !c.step || c.step === 'setup' || c.step === 'result' || c.step === 'flags') return null;
    const it = this.core.questions.find(q => q.id === c.step); if (!it) return null;
    return { id: it.id, text: it.text, options: it.options.map(o => ({ value: o.value, text: o.text })), knowledge_quiz: it.kind === 'knowledge' };
  }
  /** A proposal is a diff (add, remove, swaps, weights) applied to whatever the mix is when the person taps Apply,
   *  so an older preview never throws away edits made after it. */
  mixWithDiff(mix, d, held = this.trayTickers()) {
    const m = JSON.parse(JSON.stringify(mix));
    for (const t of d.add || []) { if (!m.satellites.includes(t)) m.satellites.push(t); m.exclude = m.exclude.filter(x => x !== t); }
    for (const t of d.remove || []) { m.satellites = m.satellites.filter(x => x !== t); delete m.minimums[t]; if (held.includes(t) && !m.exclude.includes(t)) m.exclude.push(t); }
    Object.assign(m.swaps, d.swaps || {});
    if (d.weights !== undefined) m.fixedWeights = d.weights;
    return m;
  }
  async toolPropose(i) {
    const before = this.st.result || await this.rebuild();
    const level = i.level ? Math.max(1, Math.min(5, Math.round(i.level))) : this.st.level;
    const refused = [], diff = { add: [], remove: [], swaps: {} };
    for (const t of i.add || []) { const f = this.resolveFund(t); if (!f) refused.push(`${t}: not in the fund list`); else if (f.market !== this.st.market) refused.push(this.L.otherMarket(f.symbol, f.market)); else if (!f.eligible) refused.push(`${f.symbol}: ${f.excluded_because}`); else diff.add.push(f.yahoo); }
    for (const t of i.remove || []) { const f = this.resolveFund(t); if (f) diff.remove.push(f.yahoo); }
    const slots = new Map((before.holdings || []).filter(h => h.sleeve).map(h => [h.ticker, h.sleeve]));
    for (const [k, t] of Object.entries(i.swap || {})) {  // accepts a slot key or the ticker currently in the slot
      const f = this.resolveFund(t); if (!f) { refused.push(`${t}: not in the fund list`); continue; }
      const key = this.M.sleeveByKey.has(k) ? k : slots.get(this.resolveFund(k)?.yahoo || k);
      if (!key) { refused.push(`${k}: no such slot; use slot_key from current_mix`); continue; }
      diff.swaps[key] = f.yahoo;
    }
    if (i.weights && typeof i.weights === 'object') { const fw = {}; for (const [t, v] of Object.entries(i.weights)) { const f = this.resolveFund(t); if (f && f.market === this.st.market && f.eligible) fw[f.yahoo] = Number(v); } diff.weights = Object.keys(fw).length ? fw : null; }
    const mix = this.mixWithDiff(this.st.mix, diff);
    const status = this.levelStatus(level);
    const needsAck = status === 'explore', locked = status === 'locked';
    const sameLevel = level === this.st.level;
    const { result: after } = await this.run('build', { ...this.req(), risk_level: level, swaps: mix.swaps, satellites: mix.satellites, exclude: mix.exclude, fixedWeights: mix.fixedWeights, nBoot: 200, seed: 0 });
    const same = sameLevel && JSON.stringify(after.holdings.map(h => [h.ticker, h.weight])) === JSON.stringify(before.holdings.map(h => [h.ticker, h.weight]));
    const out = { before: this.mixSummary(before), after: this.mixSummary(after), not_added: refused.length ? refused : null };
    if (same) return { ...out, status: 'no change: the preview equals the current mix, so no card was shown' };
    this.cardProposal(before, after, { level, diff, needsAck, locked, mixAt: JSON.stringify(this.st.mix), market: this.st.market });
    if (locked) return { ...out, status: `level ${level} is locked by a savings or debt answer; the card shows it read-only`, binding_answers: this.profileSummary()?.binding_answers };
    if (needsAck) return { ...out, status: `level ${level} is above the self-check; the card shows it read-only with an Explore button the person may tap. You cannot confirm it for them.`, binding_answers: this.profileSummary()?.binding_answers };
    return { ...out, status: 'shown to the person with an Apply button; nothing has changed yet' };
  }
  toolContext() { this.cardContext(); const c = this.core.context, keys = FLAG_CONTEXT[this.st.market]; return { flags: c.flags.filter(f => f.available && keys.includes(f.key)).map(f => ({ key: f.key, label: f.label, value: f.value, unit: f.unit, as_of: f.as_of, percentile: f.percentile, percentile_since: f.percentile_since, reading: f.reading, evidence: f.evidence })), news: c.news && c.news.available ? c.news.topics.map(t => ({ topic: t.topic, tone_vs_average: t.tone_vs_average, headlines: t.headlines.slice(0, 4).map(h => ({ title: h.title, source: h.domain, url: h.url })) })) : 'not available', note: 'Context only; never changes the mix.' }; }
  toolTerm(i) { const k = this.matchTerm(i.term || '') || (i.term || '').toLowerCase().replace(/[\s-]+/g, '_'); const g = this.core.glossary[k]; if (!g) return { found: false, known: Object.keys(this.core.glossary) }; this.cardTerm(k); return { found: true, key: k, ...g }; }
  toolBacktest(i) {
    const bt = this.core.backtest?.[this.st.market]; if (!bt) return { available: false };
    const lvl = Math.round(i.level || this.st.level); const map = { 1: 2, 2: 2, 3: 3, 4: 4, 5: 4 }; const L = map[lvl];
    this.cardBacktest(L, lvl);
    return { label: 'Hypothetical back-test, after 10 bps trading costs; funds chosen with today\'s information', market: this.st.market, level_asked: lvl, nearest_tested_level: L, stats: bt.stats.filter(r => r.level === L), subperiods: bt.subperiods.filter(r => r.level === L), paired_t_tests: bt.paired.filter(r => r.level === L).map(r => ({ comparison: `${r.a} minus ${r.b}`, annualized_difference: r.annualized_diff, t_stat: r.t_stat })) };
  }
  toolStartCheck() { this.openCheck(); return { shown: this.st.check.step, question: this.openQuestion() }; }
  toolAnswerCheck(i) {  // pre-select only: the person records an answer by tapping it
    const q = this.openQuestion();
    if (!q || q.id !== i.question_id) return { ok: false, why: 'that question is not open', open_question: q };
    if (!q.options.some(o => o.value === String(i.value))) return { ok: false, why: 'not one of the options', options: q.options };
    this.st.check.preselect = String(i.value); this.st.check.hint = this.L.typedMatch(this.optText(q.id, i.value)); this.renderCheck();
    return { ok: true, status: 'pre-selected; the person must tap it to record the answer' };
  }
  async toolOneFund() {
    const p = this.st.result || await this.rebuild();
    if (!this.live.mix?.isConnected) await this.showMix({ scroll: false });  // the comparison lives in the mix card
    const o = await this.oneFundFor(p);
    return o ? { ...o, label: 'A one-fund version at a similar stock share. Hypothetical; not a recommendation.' } : { available: false };
  }

  // ---------------------------------------------------------------- self-check: one live stepper
  applicable(id) { return !(id === 'B2' && this.st.answers.A1 === 'wealth'); }
  scoredSteps() { return STEPS.filter(id => id !== 'setup' && this.applicable(id)); }
  cleanAnswers() { const a = {}; for (const [k, v] of Object.entries(this.st.answers)) if (v != null && v !== '' && /^[A-D]\d$/.test(k) && k !== 'B3' && this.applicable(k)) a[k] = v; return a; }
  firstOpen() {
    if (!this.st.adult || !this.st.answers.A1) return 'setup';
    const id = this.scoredSteps().find(x => !(x in this.st.answers));
    if (id) return id;
    const p = scoreProfile(this.core.questions, this.cleanAnswers());
    return p.flags.length && !this.st.check.flagsSeen ? 'flags' : 'result';
  }
  openCheck(step = null) {
    const c = this.st.check;
    if (this.live.check?.isConnected && !c.open) { this.live.check.remove(); delete this.live.check; }  // a reopened check comes to the end
    c.open = true; c.step = step || this.firstOpen(); c.preselect = null; c.hint = null;
    this.ensureLadder(this.st.market);
    this.renderCheck({ focus: true, scroll: true });
  }
  closeCheck() { this.st.check.open = false; this.st.check.pick = null; this.renderCheck(); this.reconcileLevel(); this.save(); }
  goto(step) {
    const c = this.st.check; c.step = step; c.preselect = null; c.hint = null;
    if (step === 'B1' && !('B1' in this.st.answers) && this.st.opener?.retiredNow) { c.preselect = 'lt2'; c.hint = this.L.fromYourMsgHint(this.optText('B1', 'lt2')); }  // "I'm retired" in the first message
    this.renderCheck({ focus: true, scroll: true });
  }
  nextStep(from) {
    const order = STEPS.filter(id => id === 'setup' || this.applicable(id));
    const i = order.indexOf(from);
    const rest = order.slice(i + 1).find(id => !(id in this.st.answers));
    if (rest) return rest;
    const any = order.find(id => id !== 'setup' && !(id in this.st.answers));
    if (any) return any;
    const p = scoreProfile(this.core.questions, this.cleanAnswers());
    return p.flags.some(f => f.id === 'F_inconsistent' || f.id === 'F_drop_vs_range') && !this.st.check.flagsSeen ? 'flags' : 'result';
  }
  prevStep(from) {
    const order = STEPS.filter(id => id === 'setup' || this.applicable(id));
    const i = order.indexOf(from); return i > 0 ? order[i - 1] : (from === 'result' || from === 'flags' ? order[order.length - 1] : null);
  }
  answerQ(id, value) {
    const c = this.st.check, L = this.L;
    const had = id in this.st.answers, prev = this.st.answers[id], next = value === 'skip' ? null : value;
    this.st.answers[id] = next;
    const beforeP = this.st.profile, before = beforeP && beforeP.status !== 'incomplete' ? beforeP.suggested_level : null;
    this.st.profile = scoreProfile(this.core.questions, this.cleanAnswers());
    const p = this.st.profile;
    if (c.typedNote?.id === id) { this.rewriteNote(c.typedNote.node, 'typedDone', () => this.optText(id, next)); c.typedNote = null; }
    if (beforeP && this.profileFP(beforeP) !== this.profileFP(p)) document.querySelectorAll('.card-prop:not(.is-done)').forEach(n => this.resolveProp(n, 'propOutdated'));
    if (had && prev !== next && before != null && p.suggested_level != null && p.status !== 'incomplete') {
      const qf = () => (SHORT[id]?.en || id);
      if (before !== p.suggested_level) this.noteL('noteChanged', qf, before, p.suggested_level);
      else {
        const b = this.limitAnswers(p).find(x => x.id !== id), was = beforeP ? this.limitAnswers(beforeP).some(x => x.id === b?.id) : false;
        this.noteL(was ? 'noteSame' : 'noteSameNow', qf, p.suggested_level, () => (b && SHORT[b.id] ? SHORT[b.id].en : ''));
      }
    }
    // the gate applies at once; the rest of the policy once the check is complete (a level that is now above it and
    // unconfirmed moves to the suggestion, with a note that says why)
    if (!this.reconcileLevel({ gateOnly: p.status !== 'complete', firstDone: !beforeP || beforeP.status !== 'complete' })) { this.renderTray(); this.refreshMix(); }
    if ((id === 'B1' || id === 'B2') && this.autoYears()) this.rebuild();
    if (p.status === 'not_ready') { this.goto('result'); return; }
    if (c.reviewing) { c.reviewing = false; this.goto(this.firstOpen() === 'setup' ? 'setup' : (this.scoredSteps().find(x => !(x in this.st.answers)) || 'result')); }
    else this.goto(this.nextStep(id));
    this.save();
  }
  renderCheck({ focus = false, scroll = false } = {}) {
    const c = this.st.check, L = this.L;
    let node;
    if (!c.open) node = this.checkSummary();
    else if (c.step === 'setup') node = this.stepSetup();
    else if (c.step === 'flags') node = this.stepFlags();
    else if (c.step === 'result') node = this.stepResult();
    else node = this.stepQuestion(c.step);
    if (!node) return;
    node.classList.add('card-check');
    this.push(node, { key: 'check', scroll });
    if (focus) { const h = node.querySelector('h3'); if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); } }
    if (c.open && c.step && /^[A-C]\d$/.test(c.step)) { const n = this.scoredSteps().indexOf(c.step) + 1; this.announce(`${L.stepTitle}: ${L.stepMeta(n, this.scoredSteps().length)}`); }
    else if (c.open && /^D\d$/.test(c.step || '')) this.announce(L.quizMeta(c.step === 'D1' ? 1 : 2));
  }
  stepHead(n, m, { back = true, start = false, done = false } = {}) {
    const L = this.L;
    return `<header class="q-head"><span class="q-count">${esc(L.stepTitle)} · ${esc(done ? L.stepMetaDone : start ? L.stepMetaStart(m) : L.stepMeta(n, m))}</span>${back ? `<button class="link" data-back>${esc(L.back)}</button>` : ''}<button class="link" data-later>${esc(L.later)}</button></header>
      <div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="${m}" aria-valuenow="${n}"><span style="width:${Math.round(100 * n / m)}%"></span></div>`;
  }
  bindHead(node, step) {
    node.querySelector('[data-back]')?.addEventListener('click', () => { const p = this.prevStep(step); if (p) this.goto(p); });
    node.querySelector('[data-later]')?.addEventListener('click', () => this.closeCheck());
  }
  stepSetup() {
    const L = this.L, st = this.st, a1 = this.core.questions.find(q => q.id === 'A1');
    const f = st.opener || {}, d = st.check.draft || (st.check.draft = {});
    const other = (f.tickers || []).filter(t => this.resolveFund(t)?.market && this.resolveFund(t).market !== st.market).map(sym);
    const known = [f.market ? (f.market === 'CA' ? L.ca : L.us) + (f.inferred ? ` (${L.fromTickers})` : '') : null, f.goal ? this.optText('A1', f.goal) : null, f.amount ? this.fmtMoney(f.amount) : null, f.monthly ? this.fmtMonthly(f.monthly) : null,
      (f.tickers || []).length ? L.tickersSeen((f.tickers || []).map(sym).join(', ')) : null].filter(Boolean);
    const held = new Set(this.trayTickers());
    const picks = st.picks.filter(t => this.M.fund(t) && !held.has(t));
    const monthlyVal = d.monthly ?? (st.monthly ? (st.monthly < 0 ? `−${Math.abs(st.monthly)}` : String(st.monthly)) : '');
    const node = this.el(`${this.stepHead(0, this.scoredSteps().length, { back: false, start: true })}
      <h3>${esc(L.setupTitle)}</h3>
      ${known.length && !d.edited ? `<p class="small muted" data-known>${esc(L.fromMsg)} ${esc(known.join(' · '))}</p>` : ''}
      ${f.amountChoices && !f.amount ? `<p class="small muted">${esc(L.amountChoices(f.amountChoices.map(v => this.fmtMoney(v)).join(', ')))}</p>` : ''}
      ${other.length ? `<p class="small muted">${esc(L.otherMarketPicks(other.join(', '), st.market === 'CA' ? L.us : L.ca))}</p>` : ''}
      <div class="field"><span>${esc(L.market)}</span><div class="seg2" role="group">${['CA', 'US'].map(m => `<button data-mk="${m}" aria-pressed="${st.market === m}">${esc(m === 'CA' ? L.ca : L.us)} <small>${esc(m === 'CA' ? L.caSub : L.usSub)}</small></button>`).join('')}</div></div>
      <div class="field"><span>${esc(L.goalQ)}</span><div class="chips2" role="group">${a1.options.map(o => `<button data-goal="${o.value}" aria-pressed="${st.answers.A1 === o.value}">${esc(o.text)}</button>`).join('')}</div></div>
      <div class="two"><label class="field"><span>${esc(L.amountLabel(this.ccy))}</span><input data-amount inputmode="decimal" autocomplete="off" value="${esc(d.amount ?? (st.amount ? String(st.amount) : ''))}" placeholder="${esc(L.amountHint)}"></label>
      <label class="field"><span>${esc(L.monthlyLabel(this.ccy))}</span><input data-monthly inputmode="decimal" autocomplete="off" value="${esc(monthlyVal)}" placeholder="${esc(L.monthlyHint)}"></label></div>
      <p class="small warnline" data-err role="alert" hidden></p>
      ${picks.length ? `<button class="checkline ${d.usePicks ? 'is-on' : ''}" data-picks aria-pressed="${!!d.usePicks}">${icon('check', 16)}<span>${esc(L.picksLabel(picks.map(sym).join(', ')))}</span></button>` : ''}
      <p class="small muted">${esc(L.adultNeeded)}</p>
      <div class="row"><button class="btn primary" data-go>${esc(st.adult ? L.continue : L.adultContinue)}</button></div>`, 'card card-q');
    node.dataset.q = 'setup';
    this.bindHead(node, 'setup');
    node.querySelectorAll('[data-mk]').forEach(b => b.addEventListener('click', async () => { const mk = b.dataset.mk; await this.setMarket(mk); this.live.check?.querySelector(`[data-mk="${mk}"]`)?.focus(); }));
    const keep = (k, inp) => inp.addEventListener('input', () => { d[k] = inp.value; if (!d.edited) { d.edited = true; node.querySelector('[data-known]')?.remove(); } });
    keep('amount', node.querySelector('[data-amount]')); keep('monthly', node.querySelector('[data-monthly]'));
    node.querySelectorAll('[data-goal]').forEach(b => b.addEventListener('click', () => { st.answers.A1 = b.dataset.goal; node.querySelectorAll('[data-goal]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); const qc = node.querySelector('.q-count'); if (qc) qc.textContent = `${L.stepTitle} · ${L.stepMetaStart(this.scoredSteps().length)}`; }));
    const pickBtn = node.querySelector('[data-picks]');
    pickBtn?.addEventListener('click', () => { d.usePicks = !d.usePicks; pickBtn.classList.toggle('is-on', d.usePicks); pickBtn.setAttribute('aria-pressed', String(d.usePicks)); });
    const err = node.querySelector('[data-err]');
    node.querySelector('[data-go]').addEventListener('click', () => {
      const amtIn = node.querySelector('[data-amount]'), moIn = node.querySelector('[data-monthly]');
      const amt = parseAmount(amtIn.value), monthly = parseMonthly(moIn.value);
      const problems = []; let focus = null;
      if (!st.answers.A1) { problems.push(L.goalNeeded); focus = focus || node.querySelector('[data-goal]'); }
      if (!amt || amt < 100) { problems.push(L.amountMin); focus = focus || amtIn; }
      if (monthly == null) { problems.push(L.monthlyBad); focus = focus || moIn; }
      if (problems.length) { err.hidden = false; err.textContent = problems.join(' '); focus?.focus(); return; }
      st.adult = true;  // the button says "I am 18 or older"
      st.amount = amt; st.answers.B3 = String(amt); st.monthly = monthly; st.answers.A0 = st.market;
      if (d.usePicks && picks.length) { for (const t of picks) if (!st.mix.satellites.includes(t)) st.mix.satellites.push(t); st.userChanged = true; }
      st.picks = []; st.check.draft = null; this.autoYears();
      this.renderTray(); this.rebuild(); this.ensureLadder(st.market);
      this.goto(this.nextStep('setup'));
    });
    return node;
  }
  stepQuestion(id) {
    const L = this.L, st = this.st, it = this.core.questions.find(q => q.id === id), c = st.check;
    const steps = this.scoredSteps(), n = steps.indexOf(id) + 1;
    let text = it.text;
    const amt = st.amount;
    if (id === 'C2') text = text.replace('{amount}', this.fmtMoney(amt)).replace('{after}', this.fmtMoney(amt * 0.8));
    const gates = (st.profile?.gates || []).filter(g => g.id === 'G2' || g.id === 'G3').map(g => `<p class="gateline">${icon('info', 14)}<span>${esc(L.gateLine[g.id])}</span></p>`).join('');
    let body;
    if (it.scenario === 'one_year' || it.scenario === 'ten_year') {
      const rows = this.ladderRows(), one = it.scenario === 'one_year';
      const base = one ? Math.max(this.flat(12), amt * 0.25) : Math.max(this.flat(120), amt * 0.25);
      body = `<div class="scen" role="group" aria-label="${esc(text)}">${it.options.map(o => {
        const r = rows.find(x => x.level === Number(o.value)); let v = '<span class="skel"></span>', extra = '', bar = '';
        if (r && this.rowOwn(r)) {
          const q = one ? this.rowYear(r) : this.rowTen(r);
          v = L.between(this.fmtMoney(q.p10), this.fmtMoney(q.p90));
          if (!one && r.worst) extra = `<small class="muted">${esc(L.crisisWorst(this.fmtMoney(this.rowCrisis(r, r.worst))))}</small>`;
          bar = this.rangeBar([q.p10 / base, q.p90 / base], it.scenario);
        }
        const chosen = st.answers[id] === o.value, pre = c.preselect === o.value;
        const ready = r && this.rowOwn(r);
        return `<button class="scen-opt ${chosen ? 'is-chosen' : ''} ${pre ? 'is-pre' : ''}" data-v="${o.value}" ${ready ? `data-range="${esc(v)}"` : ''} aria-pressed="${chosen}" ${ready ? '' : `disabled aria-busy="true" title="${esc(L.updating)}"`}><span class="scen-range">${v}${extra}</span>${bar}</button>`;
      }).join('')}</div>`;
      body = `<p class="small muted" id="scen-note-${id}">${esc(one ? L.ranges1 : L.ranges10)}${st.monthly ? ` ${esc(L.rangesFlow(this.fmtMonthly(st.monthly)))}` : ''}</p>` + body.replace('<div class="scen" role="group"', `<div class="scen" role="group" aria-describedby="scen-note-${id}"`);
    } else {
      body = `<div class="opts" role="group" aria-label="${esc(text)}">${it.options.map(o => { const chosen = st.answers[id] === o.value, pre = c.preselect === o.value; return `<button class="opt ${chosen ? 'is-chosen' : ''} ${pre ? 'is-pre' : ''}" data-v="${esc(o.value)}" aria-pressed="${chosen}">${esc(o.text)}</button>`; }).join('')}</div>`;
    }
    const node = this.el(`${it.kind === 'knowledge' ? '' : this.stepHead(n, steps.length)}${gates}<h3>${esc(text)}</h3>${c.hint ? `<p class="hint">${esc(c.hint)}</p>` : ''}${body}
      ${['C4', 'D1', 'D2'].includes(id) ? `<div class="row"><button class="link" data-skip>${esc(L.skip)}</button></div>` : ''}`, 'card card-q');
    node.dataset.q = id;
    this.bindHead(node, id);
    node.querySelectorAll('[data-v]').forEach(b => b.addEventListener('click', () => { if (b.dataset.range) this.st.echo = { ...(this.st.echo || {}), [id]: b.dataset.range }; return it.kind === 'knowledge' ? this.answerKnowledge(id, b.dataset.v) : this.answerQ(id, b.dataset.v); }));
    node.querySelector('[data-skip]')?.addEventListener('click', () => (it.kind === 'knowledge' ? this.answerKnowledge(id, 'skip') : this.answerQ(id, 'skip')));
    if (c.preselect) requestAnimationFrame(() => node.querySelector('.is-pre')?.focus());
    return node;
  }
  answerKnowledge(id, v) {
    if (v === 'skip') this.st.answers[id] = null; else this.st.answers[id] = v;
    this.st.profile = scoreProfile(this.core.questions, this.cleanAnswers());
    if (id === 'D1') this.goto('D2'); else { this.st.check.knowledge = false; this.goto('result'); }
    this.save();
  }
  stepFlags() {
    const L = this.L, p = scoreProfile(this.core.questions, this.cleanAnswers());
    const flags = p.flags.filter(f => f.id === 'F_inconsistent' || f.id === 'F_drop_vs_range');
    if (!flags.length) { this.st.check.flagsSeen = true; return this.stepResult(); }
    const items = [...new Set(flags.flatMap(f => f.items))].filter(k => k in this.st.answers);
    const node = this.el(`${this.stepHead(this.scoredSteps().length, this.scoredSteps().length)}<h3>${esc(L.flagTitle)}</h3>
      ${flags.map(f => `<p>${esc(f.id === 'F_inconsistent' ? L.flagLead : f.en)}</p>`).join('')}
      <ul class="quoted">${items.map(k => `<li>${esc(L.youAnswered(SHORT[k].en, k.startsWith('C1') || k === 'C3' ? `${L.level} ${this.st.answers[k]}` : this.optText(k, this.st.answers[k])))}</li>`).join('')}</ul>
      <div class="row"><button class="btn primary" data-keep>${esc(L.keepAnswers)}</button>${items.map(k => `<button class="btn ghost" data-redo="${k}">${esc(L.changeQ(SHORT[k].en))}</button>`).join('')}</div>`, 'card card-q');
    node.dataset.q = 'flags';
    this.bindHead(node, 'flags');
    node.querySelector('[data-keep]').addEventListener('click', () => { this.st.check.flagsSeen = true; this.goto('result'); });
    node.querySelectorAll('[data-redo]').forEach(b => b.addEventListener('click', () => { this.st.check.reviewing = true; this.st.check.flagsSeen = true; this.goto(b.dataset.redo); }));
    return node;
  }
  /** The answers behind a level: first the ones that set the limit, then (muted) the ones that allowed more. For the two
   *  range questions the dollar range the person tapped is echoed, not "level N". */
  /** The answers that set a limit (not the ones that allowed more than it). */
  limitAnswers(p, limit = p.suggested_level, list = p.binding_answers) {
    const allows = (b) => { const m = /allows up to level (\d)/.exec(b.effect_en || ''); return m && limit != null && Number(m[1]) > limit && !b.lowers; };
    return (list || []).filter(b => !allows(b));
  }
  bindingHTML(p, list = p.binding_answers, limit = p.suggested_level) {
    const L = this.L;
    const answer = (b) => {
      if (b.id === 'C1' || b.id === 'C3') {
        const e = this.st.echo?.[b.id]; if (e) return L.youPicked(e);  // the range as it was on screen when tapped
        const r = this.ladderRows().find(x => x.level === Number(this.st.answers[b.id])); if (r) { const q = b.id === 'C1' ? this.rowYear(r) : this.rowTen(r); return L.youPicked(L.between(this.fmtMoney(q.p10), this.fmtMoney(q.p90))); }
      }
      return b.answer_en;
    };
    const qn = (b) => (SHORT[b.id] ? SHORT[b.id].en : b.question_en);
    const li = (b, muted) => `<li class="${muted ? 'muted' : ''}"><span><b>${esc(qn(b))}:</b> ${esc(answer(b))}</span> <small class="muted">${esc(b.effect_en)}</small> <button class="link" data-change="${b.id}" aria-label="${esc(`${L.change}: ${qn(b)}`)}">${esc(L.change)}</button></li>`;
    const set = this.limitAnswers(p, limit, list), also = (list || []).filter(b => !set.includes(b));
    return set.map(b => li(b, false)).join('') + (also.length ? `<li class="also small muted">${esc(L.alsoConsidered)}</li>` + also.map(b => li(b, true)).join('') : '');
  }
  // ---------------------------------------------------------------- level policy: one derived status, one consent record
  profileFP(p = this.st.profile) { return p ? `${p.capacity}|${p.tolerance}|${p.gate_cap}` : ''; }
  checkMax(p = this.st.profile) { return Math.max(...(p?.within_check?.length ? p.within_check : [5])); }
  /** Above a finished self-check. Derived on every render, never stored. */
  isAbove(l = this.st.level, p = this.st.profile) { return !!p && p.status === 'complete' && l > this.checkMax(p); }
  /** Consent from the explore sheet counts only for the profile it was given on. */
  consented(l, p = this.st.profile) { const e = this.st.explore; return !!e && e.level >= l && e.fp === this.profileFP(p); }
  /** 'locked' above a savings/debt gate (as soon as that answer exists), 'explore' above a finished check without consent, else 'ok'.
   *  The tray, chooser, chat preview, resume and page state all use this one function. */
  levelStatus(l, p = this.st.profile) {
    if (!p) return 'ok';
    if (l > (p.gate_cap || 5)) return 'locked';
    if (this.isAbove(l, p) && !this.consented(l, p)) return 'explore';
    return 'ok';
  }
  levelTags(l, p = this.st.profile) {
    const L = this.L; if (!p) return [];
    if (l > (p.gate_cap || 5)) return [L.tagLocked];
    if (p.status === 'incomplete') return [];
    if (l === p.suggested_level) return [L.tagSuggested];
    if (this.isAbove(l, p)) return [L.tagAbove];
    if (p.tolerance != null && l > p.tolerance) return [L.tagComfort];
    return [];
  }
  levelTag(l, p = this.st.profile) { return this.levelTags(l, p)[0] || ''; }
  /** After a rescore (answer, close, resume): a level above a gate moves down to it; a level above a finished check with no
   *  valid consent moves to the suggestion. Each move is said in the thread. Returns true when the level moved. */
  reconcileLevel({ gateOnly = false, firstDone = false } = {}) {
    const st = this.st, p = st.profile; if (!p) return false;
    let to = null, why = '';
    const cb = st.chosenBefore;
    if (st.level > (p.gate_cap || 5)) { to = p.gate_cap; why = 'noteGateMove'; if (st.levelChosen && !cb) st.chosenBefore = st.level; }
    else if (cb && cb !== st.level && cb <= (p.gate_cap || 5) && (gateOnly ? p.status !== 'complete' : this.levelStatus(cb) === 'ok')) { to = cb; why = 'noteRestored'; }
    else if (!gateOnly && this.levelStatus(st.level) === 'explore') {
      to = p.suggested_level;
      why = !st.levelChosen ? 'noteRefMove' : (st.explore && st.explore.level >= st.level) ? 'noteConfirmAgain' : firstDone ? 'noteCheckBelow' : 'noteConsentMove';
    }
    else if (!gateOnly && !st.levelChosen && p.status === 'complete' && st.level !== p.suggested_level && this.levelStatus(p.suggested_level) === 'ok') { to = p.suggested_level; why = 'noteFollow'; }  // until a choice, the mix follows the check
    if (to == null || to === st.level) return false;
    const from = st.level;
    st.level = to; st.levelChosen = why === 'noteRestored'; if (why === 'noteRestored') st.chosenBefore = null;
    if (why !== 'noteRestored') st.explore = null;
    st.check.pick = null;  // a level the page moved to is not a choice (a restored one is the person's own)
    this.noteL(why, from, to);
    this.renderTray(); this.rebuild(); this.refreshMix();
    if (this.live.check && !st.check.open) this.renderCheck();
    this.save();
    return true;
  }
  stepResult() {
    const L = this.L, st = this.st;
    const p = st.profile = scoreProfile(this.core.questions, this.cleanAnswers());
    const rows = this.ladderRows(), amt = st.amount, wd = st.monthly < 0;
    if (p.status === 'not_ready') {
      const node = this.el(`${this.stepHead(this.scoredSteps().length, this.scoredSteps().length, { done: true })}<h3>${esc(L.resultTitle)}</h3><p>${esc(L.notReady)}</p>
        <ul class="binding">${this.bindingHTML(p)}</ul><div class="row"><button class="btn" data-later2>${esc(L.close)}</button></div>`, 'card card-q');
      node.dataset.q = 'result'; this.bindHead(node, 'result');
      node.querySelectorAll('[data-change]').forEach(b => b.addEventListener('click', () => { st.check.reviewing = true; this.goto(b.dataset.change); }));
      node.querySelector('[data-later2]').addEventListener('click', () => this.closeCheck());
      return node;
    }
    const current = st.levelChosen && this.levelStatus(st.level) !== 'locked' ? st.level : null;
    const pick = st.check.pick ?? current ?? p.suggested_level;
    const lines = [];
    if (p.capacity) lines.push(`<p><b>${esc(L.capLine(p.capacity))}</b></p>`);
    if (p.tolerance) lines.push(`<p><b>${esc(L.tolLine(p.tolerance))}</b></p>`);
    if (p.binding === 'gate') lines.push(`<p class="gateline">${icon('info', 14)}<span>${esc(L.gateBind(p.gate_cap))}</span></p>`);
    const choose = [1, 2, 3, 4, 5].map(l => {
      const r = rows.find(x => x.level === l), own = this.rowOwn(r), tags = this.levelTags(l, p), g08 = r?.stress?.find(s => s.key === 'gfc');
      if (l === current) tags.unshift(L.tagCurrent);
      return `<button class="lad-row ${l === pick ? 'is-on' : ''} ${l > (p.gate_cap || 5) ? 'is-locked' : ''}" data-l="${l}" aria-pressed="${l === pick}">
        <span class="lad-name"><b>${l}</b> ${esc(this.levelName(l))}${tags.map(tag => `<em class="tag ${tag === L.tagLocked ? 'lock' : tag === L.tagSuggested ? 'ok' : tag === L.tagCurrent ? 'cur' : ''}">${esc(tag)}</em>`).join('')}</span>
        ${r ? this.classBar(r.mix, 'thin') : '<span class="skel wide"></span>'}
        <span class="lad-num"><small>${esc(L.stocksShare)}</small>${r ? this.pct(r.mix.Equity || 0) : ''}</span>
        <span class="lad-num"><small>${esc(L.bad)}</small>${own ? esc(this.fmtMoney(this.rowYear(r).p5 - this.flat(12))) : '<span class="skel"></span>'}</span>
        <span class="lad-num"><small>${esc(wd ? L.lastsCol(Math.max(10, st.years)) : L.crisis2008)}</small>${!own ? '<span class="skel"></span>' : r ? (wd ? (r.withdrawal ? this.pct(r.withdrawal.chance_lasts) : '<span class="skel"></span>') : g08 && g08.portfolio_return != null ? esc(this.fmtMoney(this.rowCrisis(r, g08))) : `<abbr title="${esc(L.notEstimable((g08?.not_estimable || []).map(sym).join(', ')))}">${esc(L.na)}</abbr>`) : ''}</span></button>`;
    }).join('');
    // a plan that takes money out: say plainly when the suggested level is the one most likely to run out
    let lastsWarn = '';
    if (wd) {
      const own = rows.filter(r => this.rowOwn(r) && r.withdrawal), sr = own.find(r => r.level === p.suggested_level);
      const best = own.filter(r => r.level <= (p.gate_cap || 5)).reduce((a, b) => (!a || b.withdrawal.chance_lasts > a.withdrawal.chance_lasts ? b : a), null);
      if (sr && best && sr.withdrawal.chance_lasts < 0.5 && best.withdrawal.chance_lasts - sr.withdrawal.chance_lasts >= 0.2)
        lastsWarn = `<p class="warnline">${icon('warning', 14)}<span>${esc(L.lastsWarn(sr.level, this.pct(sr.withdrawal.chance_lasts), best.level, this.pct(best.withdrawal.chance_lasts), sr.years))}</span></p>`;
    }
    const cashBucket = wd && st.answers.B1 === 'lt2' ? `<p class="small muted">${esc(L.cashBucket)}</p>` : '';
    const answered = STEPS.filter(x => x !== 'setup' && this.applicable(x) && x in st.answers && st.answers[x] != null);
    const review = `<details class="review" ${st.check.showReview ? 'open' : ''}><summary>${esc(L.reviewAnswers)}</summary><dl class="pairs">
      <div><dt>${esc(L.goalQ)}</dt><dd>${esc(this.optText('A1', st.answers.A1))} <button class="link" data-goto="setup" aria-label="${esc(`${L.change}: ${L.goalQ}`)}">${esc(L.change)}</button></dd></div>
      <div><dt>${esc(L.amount)}</dt><dd>${esc(this.fmtMoney(st.amount))} <button class="link" data-goto="setup" aria-label="${esc(`${L.change}: ${L.amount}`)}">${esc(L.change)}</button></dd></div>
      ${answered.map(x => `<div><dt>${esc(SHORT[x].en)}</dt><dd>${esc(x === 'C1' || x === 'C3' ? (st.echo?.[x] ? L.youPicked(st.echo[x]) : `${L.level} ${st.answers[x]}`) : this.optText(x, st.answers[x]))} <button class="link" data-goto="${x}" aria-label="${esc(`${L.change}: ${SHORT[x].en}`)}">${esc(L.change)}</button></dd></div>`).join('')}</dl></details>`;
    const node = this.el(`${this.stepHead(this.scoredSteps().length, this.scoredSteps().length, { done: true })}<h3>${esc(L.resultTitle)}</h3>
      ${lines.join('')}${p.binding_answers?.length ? `<p class="small muted">${esc(L.becauseOf)}:</p><ul class="binding">${this.bindingHTML(p)}</ul>` : ''}
      <p class="strong">${esc((p.capacity != null && p.capacity === p.tolerance && p.binding !== 'gate' ? L.suggestedBoth : L.suggestedLine)(p.suggested_level, this.levelName(p.suggested_level)))}</p>
      ${lastsWarn}${cashBucket}
      <fieldset class="chooser"><legend>${esc(L.chooseTitle)}</legend><p class="small muted">${esc(wd ? L.chooseSubWd(this.fmtMoney(amt), this.fmtMonthly(st.monthly)) : st.monthly > 0 ? L.chooseSubFlow(this.fmtMoney(amt), this.fmtMonthly(st.monthly)) : L.chooseSub(this.fmtMoney(amt)))}</p><div class="ladder" aria-busy="${this.ladderStale()}">${choose}</div>${this.ladderStale() ? `<p class="small muted" role="status">${esc(L.updating)}</p>` : ''}${rows.length ? this.legend(Object.assign({}, ...rows.map(r => r.mix))) : ''}<p class="small muted">${esc(wd ? L.badVsLasts : L.badVs2008)}</p></fieldset>
      <div class="row"><button class="btn primary" data-use>${esc(pick === current ? L.keepLevel(pick) : L.useLevel(pick))}</button>${!('D1' in st.answers) ? `<button class="btn ghost" data-quiz>${esc(L.knowledge)}</button>` : ''}</div>
      ${review}`, 'card card-q');
    node.dataset.q = 'result';
    this.bindHead(node, 'result');
    node.querySelectorAll('.lad-row').forEach(b => b.addEventListener('click', () => { st.check.pick = Number(b.dataset.l); this.renderCheck(); this.live.check?.querySelector(`.lad-row[data-l="${b.dataset.l}"]`)?.focus(); }));
    node.querySelectorAll('[data-change]').forEach(b => b.addEventListener('click', () => { st.check.reviewing = true; this.goto(b.dataset.change); }));
    node.querySelectorAll('[data-goto]').forEach(b => b.addEventListener('click', () => { st.check.reviewing = b.dataset.goto !== 'setup'; this.goto(b.dataset.goto); }));
    node.querySelector('details.review')?.addEventListener('toggle', (e) => { st.check.showReview = e.target.open; });
    node.querySelector('[data-quiz]')?.addEventListener('click', () => this.goto('D1'));
    node.querySelector('[data-use]').addEventListener('click', () => this.chooseLevel(pick, { from: 'check' }));
    return node;
  }
  checkSummary() {
    const L = this.L, p = this.st.profile;
    if (!p || p.status === 'incomplete' || !p.suggested_level) {  // paused before the end: one line to pick it up again
      const done = this.scoredSteps().filter(x => x in this.st.answers).length;
      const node = this.el(`<p class="summary-line">${icon('info', 16)}<span>${esc(L.checkPaused(done, this.scoredSteps().length))}</span></p><div class="row"><button class="link" data-resume>${esc(L.continue)}</button></div>`, 'card card-summary');
      node.querySelector('[data-resume]').addEventListener('click', () => this.openCheck());
      return node;
    }
    const st = this.st, ex = this.isAbove(), s = p.suggested_level, c = st.level;
    const line = ex ? L.summaryAbove(s, c) : st.levelChosen ? L.summary(s, c) : s === c ? L.summaryUsing(s) : L.summaryRef(s, c);
    const useS = !st.levelChosen && s !== c && this.levelStatus(s) === 'ok';
    const node = this.el(`<p class="summary-line">${icon('check', 16)}<span>${esc(line)}</span></p>
      <div class="row">${useS ? `<button class="btn small primary" data-uses>${esc(L.useLevel(s))}</button>` : ''}<button class="link" data-review>${esc(L.reviewAnswers)}</button><button class="link" data-level>${esc(L.changeLevel)}</button><button class="link" data-over>${esc(L.startOver)}</button></div>`, 'card card-summary');
    node.querySelector('[data-uses]')?.addEventListener('click', () => this.chooseLevel(s, { from: 'summary' }));
    node.querySelector('[data-review]').addEventListener('click', () => { this.st.check.showReview = true; this.openCheck('result'); });
    node.querySelector('[data-level]').addEventListener('click', () => this.openCheck('result'));
    node.querySelector('[data-over]').addEventListener('click', () => { if (this.isAbove()) this.noteL('noteStartOver', this.st.level); const keep = { A1: this.st.answers.A1, B3: this.st.answers.B3 }; this.st.answers = keep; this.st.echo = {}; this.st.profile = null; this.st.explore = null; this.st.chosenBefore = null; this.st.check.flagsSeen = false; this.st.check.pick = null; this.renderTray(); this.refreshMix(); this.openCheck(); });
    return node;
  }
  /** The one place a level is set. Locked: the gate sheet. Above a finished check without consent: the explore sheet.
   *  prepare() runs just before the level is applied (a chat preview's funds); onDone(outcome) reports what happened:
   *  'applied' | 'explored' | 'stayed' | 'suggested' | 'changed' | 'dismissed'. */
  chooseLevel(l, { from = 'tray', prepare = null, onDone = null, preview = null } = {}) {
    const s = this.levelStatus(l);
    if (s === 'locked') { this.sheetGate(l, onDone); return false; }
    if (s === 'explore') { this.sheetExplore(l, from, { prepare, onDone, preview }); return false; }
    prepare?.();
    this.applyLevel(l, from);
    onDone?.('applied');
    return true;
  }
  applyLevel(l, from, { fromSheet = false } = {}) {
    const st = this.st, p = st.profile, before = st.level, L = this.L, wasAbove = this.isAbove(before, p);
    st.chosenBefore = null;
    st.level = l; st.levelChosen = true; st.userChanged = true; st.check.pick = null;
    const finish = from === 'check' || (st.check.open && st.check.step === 'result');  // a level chosen on the result screen (or from a chat preview while it is open) ends the check
    if (finish) { st.check.open = false; this.renderCheck(); }
    else if (this.live.check) this.renderCheck();
    if (wasAbove && !this.isAbove(l, p) && before !== l) this.noteL('noteBackWithin', l);
    else if (!fromSheet && this.isAbove(l, p) && before !== l) this.noteL('noteExploreAgain', l, p.suggested_level);  // under an earlier confirmation
    this.renderTray(); this.rebuild();
    if (finish) this.showMix({ scroll: true, focus: true });
    this.announce(L.announceLevel(l, this.levelName(l)));
    this.save();
  }

  // ---------------------------------------------------------------- sheets (dialogs rendered in the page, never by chat)
  openSheet(html, bind, onDone = null) {
    this.closeSheet('replaced');
    const wrap = document.createElement('div'); wrap.className = 'sheet-wrap';
    wrap.innerHTML = `<div class="sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-title">${html}</div>`;
    document.body.appendChild(wrap);
    this.sheet = wrap; this.sheetReturn = document.activeElement; this.sheetReturnSel = this.selFor(document.activeElement); this.sheetDone = onDone;
    if (wrap.querySelector('#sheet-desc')) wrap.firstElementChild.setAttribute('aria-describedby', 'sheet-desc');
    wrap.addEventListener('click', (e) => { if (e.target === wrap) this.closeSheet('dismissed'); });
    wrap.addEventListener('keydown', (e) => { if (e.key !== 'Tab') return; const f = [...wrap.querySelectorAll('button, a, input, select')].filter(x => !x.disabled); if (!f.length) return; const i = f.indexOf(document.activeElement); if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); } else if (!e.shiftKey && i === f.length - 1) { e.preventDefault(); f[0].focus(); } });
    bind(wrap);
    const h = wrap.querySelector('#sheet-title'); h?.setAttribute('tabindex', '-1');
    requestAnimationFrame(() => (wrap.querySelector('[data-autofocus]') || h)?.focus());  // the heading first: the sheet's numbers are read before its buttons
  }
  /** A selector that finds a control again after its card or the tray re-rendered. */
  selFor(el) {
    if (!el || el === document.body || !el.getAttribute) return null;
    if (el.id) return `#${CSS.escape(el.id)}`;
    const seg = el.closest?.('#tray-levels .seg'); if (seg) return `#tray-levels .seg[data-l="${seg.dataset.l}"]`;
    const d = [...el.attributes].find(x => x.name.startsWith('data-') && x.name !== 'data-live');
    return d ? `[${d.name}${d.value ? `="${CSS.escape(d.value)}"` : ''}]` : null;
  }
  /** Close the sheet and tell whoever opened it how it ended. refocus=false when the caller moves focus itself. */
  closeSheet(reason = 'dismissed', { refocus = true } = {}) {
    if (!this.sheet) return;
    const done = this.sheetDone; this.sheetDone = null;
    this.sheet.remove(); this.sheet = null;
    if (refocus) { const t = this.sheetReturn?.isConnected ? this.sheetReturn : (this.sheetReturnSel && document.querySelector(this.sheetReturnSel)); t?.focus?.(); }
    done?.(reason);
  }
  /** Above the check: the level's bad year and crisis replays in the person's dollars, next to the suggestion.
   *  The primary button keeps the current level (a no-op); the suggestion is offered, never applied by default. */
  sheetExplore(l, from, { prepare = null, onDone = null, preview = null } = {}) {
    const L = this.L, st = this.st, p = st.profile, amt = st.amount, s = p.suggested_level, cur = st.level;
    this.ensureLadder();
    const line = (row) => row && this.rowOwn(row) ? [`${L.badYear}: ${this.fmtMoney(this.rowYear(row).p5)} (${this.fmtMoney(this.rowYear(row).p5 - this.flat(12))})`,
      ...(st.monthly < 0 && row.withdrawal && this.rowOwn(row) ? [L.lastsLine(this.pct(row.withdrawal.chance_lasts), row.years)] : []),
      ...['gfc', 'covid', 'rates_2022'].map(key => { const x = row.stress?.find(y => y.key === key); return x ? `${x.scenario}: ${x.portfolio_return != null ? this.fmtMoney(this.rowCrisis(row, x)) : L.na}` : null; }).filter(Boolean)] : [];
    const nums = () => { const rows = this.ladderRows(), r = preview ? this.rowFromMix(preview) : rows.find(x => x.level === l), rs = rows.find(x => x.level === s); return `<ul class="plain">${line(r).map(x => `<li>${esc(x)}</li>`).join('') || '<li><span class="skel"></span></li>'}</ul><ul class="plain muted"><li>${esc(L.exploreVs(s))}</li>${line(rs).map(x => `<li>${esc(x)}</li>`).join('')}</ul>`; };
    const caps = p.capacity_answers || [];
    const stay = cur !== l && st.levelChosen && this.levelStatus(cur) === 'ok';  // never offer to "stay" at an untouched default
    const sugg = s !== cur && s !== l;
    this.openSheet(`<h3 id="sheet-title">${esc(L.exploreTitle(l))}</h3><p>${esc(L.exploreBody(s))} ${esc(L.exploreCap(p.capacity))}</p>
      ${caps.length ? `<ul class="binding">${this.bindingHTML(p, caps, p.capacity)}</ul>` : ''}
      <p><b>${esc(st.monthly ? L.exploreMeansFlow(l, this.fmtMoney(amt), this.fmtMonthly(st.monthly)) : L.exploreMeans(l, this.fmtMoney(amt)))}</b></p>
      <div class="two" data-nums id="sheet-desc">${nums()}</div>
      <p class="small muted">${esc(L.exploreSmall)}</p>
      <div class="row">${stay ? `<button class="btn primary" data-stay>${esc(L.stayLevel(cur))}</button>` : ''}${sugg ? `<button class="btn ${stay ? '' : 'primary'}" data-sugg>${esc(L.useSuggested(s))}</button>` : ''}<button class="btn ghost" data-explore>${esc(L.exploreAnyway(l))}</button>${!stay ? `<button class="link" data-back>${esc(L.sheetBack)}</button>` : ''}</div>`, (w) => {
      w._redraw = () => { const n = w.querySelector('[data-nums]'); if (n) n.innerHTML = nums(); };
      const resetPick = () => { if (st.check.open && st.check.step === 'result') { st.check.pick = null; this.renderCheck(); } };  // the chooser goes back to the current level
      w.querySelector('[data-stay]')?.addEventListener('click', () => { this.closeSheet('stayed'); resetPick(); });
      w.querySelector('[data-back]')?.addEventListener('click', () => { this.closeSheet('dismissed'); resetPick(); });
      w.querySelector('[data-sugg]')?.addEventListener('click', () => { this.applyLevel(s, from); this.closeSheet('suggested', { refocus: from !== 'check' }); });
      w.querySelectorAll('[data-change]').forEach(x => x.addEventListener('click', () => { this.closeSheet('changed', { refocus: false }); st.check.reviewing = true; this.openCheck(x.dataset.change); }));
      w.querySelector('[data-explore]').addEventListener('click', () => {
        st.explore = { level: l, suggested: s, fp: this.profileFP(p), at: new Date().toISOString() };
        prepare?.();
        this.noteL('noteAbove', l, s);  // said once, where the choice is made
        this.applyLevel(l, from, { fromSheet: true });
        this.closeSheet('explored', { refocus: from !== 'check' });
      });
    }, onDone);
  }
  /** Own weights are on and a level was tapped: ask before handing the weights back to the model. */
  sheetToModel(l) {
    const L = this.L;
    this.openSheet(`<h3 id="sheet-title">${esc(L.switchModelTitle(l))}</h3><p>${esc(L.switchModelBody)}</p>
      <div class="row"><button class="btn primary" data-model>${esc(L.switchModel(l))}</button><button class="btn ghost" data-keep>${esc(L.keepOwn)}</button></div>`, (w) => {
      w.querySelector('[data-keep]').addEventListener('click', () => this.closeSheet('stayed'));
      w.querySelector('[data-model]').addEventListener('click', () => { this.closeSheet('model', { refocus: false }); this.chooseLevel(l, { from: 'tray', prepare: () => this.toModel() }); });
    });
  }
  sheetGate(l, onDone = null) {
    const L = this.L, p = this.st.profile;
    const g = p.gates.find(x => x.id === 'G2' || x.id === 'G3') || p.gates[0];
    this.openSheet(`<h3 id="sheet-title">${esc(L.gateTitle(p.gate_cap))}</h3><p>${esc(g ? g.en : '')}</p>
      ${p.binding_answers?.length ? `<ul class="binding">${this.bindingHTML(p)}</ul>` : ''}<p class="small muted">${esc(L.gateSee)}</p>
      <div class="row"><button class="btn primary" data-close>${esc(L.close)}</button></div>`, (w) => {
      w.querySelector('[data-close]').addEventListener('click', () => this.closeSheet('dismissed'));
      w.querySelectorAll('[data-change]').forEach(x => x.addEventListener('click', () => { this.closeSheet('changed', { refocus: false }); this.st.check.reviewing = true; this.openCheck(x.dataset.change); }));
    }, onDone);
  }

  /** Typed text while a question is open: pre-select a matching option (never record it). */
  matchTyped(text) {
    const q = this.openQuestion(); if (!q) return false;
    const t = text.toLowerCase().trim();
    let v = null;
    for (const o of q.options) { const a = o.text.toLowerCase(); if (t === a || (a.length > 3 && t.includes(a))) { v = o.value; break; } }
    const num = Number((t.match(/(\d+(?:\.\d+)?)/) || [])[1]);
    if (!v && q.id === 'B1' && /never|not planning/.test(t)) v = '20plus';
    if (!v && q.id === 'B1' && Number.isFinite(num) && /year|yr/.test(t)) v = num < 2 ? 'lt2' : num <= 4 ? '2to4' : num <= 9 ? '5to9' : num <= 19 ? '10to19' : '20plus';
    if (!v && q.id === 'B4' && Number.isFinite(num) && /%|percent/.test(t)) v = num < 10 ? 'lt10' : num <= 25 ? '10to25' : num <= 50 ? '25to50' : num <= 75 ? '50to75' : 'gt75';
    if (!v && ['A2', 'A3'].includes(q.id)) {
      if (/^(yes|yeah|yep|y)$/.test(t)) v = q.id === 'A2' ? 'yes' : 'lot';
      else if (/^(no|nope|n)$/.test(t)) v = 'no';
      else if (/partly|some|a bit/.test(t)) v = q.id === 'A2' ? 'partly' : 'little';
    }
    const c = this.st.check;
    if (v) { c.preselect = v; c.hint = this.L.typedMatch(this.optText(q.id, v)); c.typedNote = { id: q.id, node: this.noteL('typedNote', () => this.optText(q.id, v)) }; this.renderCheck(); return true; }
    if (!this.ai.available) {
      if (this.findTickers(text).length || this.matchTerm(text) || CONTEXT_RX.test(text) || isQuestion(text)) return false;  // a question, not an answer: answer it
      c.hint = this.L.typedNoMatch; this.renderCheck(); return true;
    }
    return false;
  }

  // ---------------------------------------------------------------- the mix: one live card
  async showMix({ scroll = true, focus = false } = {}) {
    if (!this.st.result) await this.rebuild();
    this.renderMix({ scroll, move: true });
    if (focus) { const h = this.live.mix?.querySelector('h3'); if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); } }
  }
  refreshMix() { if (this.live.mix?.isConnected) this.renderMix({ scroll: false, move: false }); }
  /** Set the monthly flow; a withdrawal that flips to an addition (a missing minus sign) is said, with Undo. */
  setMonthly(v) {
    const st = this.st, old = st.monthly || 0;
    st.monthly = v; this.renderTray(); this.rebuild();
    if (old < 0 && v > 0) this.undoNote('signFlip', () => { st.monthly = -v; this.renderTray(); this.rebuild(); }, { args: [this.fmtMonthly(v), this.fmtMonthly(-v)], doneKey: 'signFlipDone' });
  }
  async oneFundFor(p) {
    const share = (p.mix.asset_class.Equity || 0) + 0.5 * (p.mix.asset_class['Multi-asset'] || 0);
    const mo = p.projection.monthly_contribution || 0, yrs = p.projection.years || 10, key = `${p.market}|${share.toFixed(2)}|${p.projection.amount}|${mo}|${yrs}`;
    if (!this.oneFundCache.has(key)) this.oneFundCache.set(key, this.run('onefund', { share, amount: p.projection.amount, monthly: mo, years: yrs }).then(r => r.result).catch(() => null));
    return this.oneFundCache.get(key);
  }
  renderMix({ scroll = false, move = false } = {}) {
    const p = this.st.result; if (!p) return;
    const L = this.L, st = this.st;
    if (move && this.live.mix?.isConnected) { this.live.mix.remove(); delete this.live.mix; }
    const one = p.projection.one_year, amt = p.projection.amount, yr = this.yearNums(p);
    const lvlLabel = p.mode === 'own_weights' ? L.ownTag : p.risk.label;
    const ex = this.isAbove();
    const maxW = Math.max(...p.holdings.map(h => (h.band ? h.band[1] : h.weight)), 0.05);
    const rows = p.holdings.map(h => {
      const w = h.weight / maxW * 100, b = h.band ? [h.band[0] / maxW * 100, h.band[1] / maxW * 100] : null;
      return `<tr><th scope="row"><button class="linkish" data-t="${esc(h.ticker)}"><b>${esc(h.symbol)}</b></button><small class="muted">${esc(this.sleeveLabel(h))}</small></th>
        <td class="bar"><span class="hold-bar"><span class="fill" style="--w:${w / 100};background:${CLASS_COLOR[h.asset_class] || 'var(--ink-3)'}"></span>${b ? `<span class="band" style="left:${b[0]}%;width:${Math.max(0.5, b[1] - b[0])}%"></span>` : ''}</span></td>
        <td class="num">${this.pct(h.weight, 1)}<small class="muted">${h.mer != null ? `${this.pct(h.mer, 2)} ${esc(L.mer)}` : esc(L.feeNA)}</small></td>
        <td class="num">${esc(this.fmtMoney(h.dollars))}<small class="${h.units === 0 ? 'warn' : 'muted'}">${h.units === 0 && h.price ? esc(L.zeroUnits(`$${h.price.toLocaleString('en-US', { maximumFractionDigits: 2 })}`)) : h.units != null ? esc(L.units(h.units)) : ''}</small></td></tr>`;
    }).join('');
    const zeroUnits = p.holdings.some(h => h.units === 0), cashShare = p.stats.cash_left != null && amt ? p.stats.cash_left / amt : 0;
    const pxDate = p.holdings.find(h => h.price_date)?.price_date;
    const own = p.mode === 'own_weights';
    const minCtl = (t) => `<label class="inline">${esc(L.holdAtLeast)} <input type="number" min="2" max="10" step="1" value="${Math.round(100 * (st.mix.minimums[t] || 0.02))}" data-min="${esc(t)}" aria-label="${esc(L.holdAtLeastFor(sym(t)))}">%</label><button class="btn small" data-minapply="${esc(t)}" aria-label="${esc(L.applyMinFor(sym(t)))}">${esc(L.apply)}</button>`;
    const noteFor = (t) => (p.notes || []).map(n => this.noteText(n)).find(x => x.includes(t) || new RegExp(`\\b${sym(t).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`).test(x));
    const shownNotes = new Set(this.notHeld(p).map(noteFor).filter(Boolean));
    const notHeld = this.notHeld(p).map(t => `<li class="warn">${icon('warning', 14)}<span>${esc((noteFor(t) || L.notHeld(sym(t))).replace(/\b([A-Z0-9-]+)\.(TO|NE)\b/g, '$1'))}</span>${own ? `<button class="btn small" data-giveweight="${esc(t)}">${esc(L.giveWeight(sym(t)))}</button>` : minCtl(t)}</li>`).join('')
      + (own ? '' : Object.keys(st.mix.minimums).filter(t => p.holdings.some(h => h.ticker === t)).map(t => `<li>${icon('info', 14)}<span>${esc(L.minSet(sym(t), this.pct(st.mix.minimums[t])))}</span>${minCtl(t)}<button class="link" data-minremove="${esc(t)}">${esc(L.removeMin)}</button></li>`).join(''));
    const changedFunds = Object.keys(st.mix.swaps).length || st.mix.satellites.length || st.mix.exclude.length;
    const hp = p.projection.by_holding_period.map(r => { const x = (v) => Math.max(0, Math.min(100, (v + 0.2) / 0.5 * 100)); return `<div class="hp-row"><span>${esc(L.yearsN(r.years))}</span><span class="hp-bar"><span class="rb-zero" style="left:${x(0)}%"></span><span class="hp-seg" style="left:${x(r.p10)}%;width:${Math.max(1, x(r.p90) - x(r.p10))}%"></span><span class="hp-mid" style="left:${x(r.p50)}%"></span></span><span class="hp-val">${this.pct(r.p10, 1)} to ${this.pct(r.p90, 1)}</span></div>`; }).join('');
    const worstAbs = Math.max(...p.stress.map(s => Math.abs(s.portfolio_return)), 0.05);
    const stress = p.stress.map(s => {
      const est = [...(s.estimated || [])].map(sym), sti = (s.stand_ins || []).map(sym), na = (s.not_estimable || []).map(sym);
      if (s.portfolio_return == null) return `<div class="st-row is-na"><span>${esc(s.scenario)}<small class="muted">${esc(s.from.slice(0, 7))} to ${esc(s.to.slice(0, 7))} · ${esc(L.notEstimable(na.join(', ')))}</small></span><span class="st-bar"></span><span class="st-val">${esc(L.na)}</span></div>`;
      return `<div class="st-row"><span>${esc(s.scenario)}<small class="muted">${esc(s.from.slice(0, 7))} to ${esc(s.to.slice(0, 7))}${est.length ? ` · ${esc(`${est.join(', ')}: ${L.estimated}`)}` : ''}${sti.length ? ` · ${esc(`${sti.join(', ')}: ${L.standIn}`)}` : ''}</small></span><span class="st-bar"><span class="${s.portfolio_return < 0 ? 'neg' : 'pos'}" style="width:${Math.abs(s.portfolio_return) / worstAbs * 100}%"></span></span><span class="st-val">${esc((s.dollars > 0 ? '+' : '') + this.fmtMoney(s.dollars))}<small>${this.sgnPct(s.portfolio_return)}</small></span></div>`;
    }).join('');
    const checks = p.checks.map(c => `<li class="${c.level}">${c.level === 'warn' ? icon('warning', 14) : icon('info', 14)}<span>${esc(c.en)}</span></li>`).join('')
      + (p.notes || []).filter(n => !shownNotes.has(this.noteText(n))).map(n => `<li>${icon('info', 14)}<span>${esc(this.noteText(n).replace(/\b([A-Z0-9-]+)\.(TO|NE)\b/g, '$1'))}</span></li>`).join('');
    const expl = p.explanation.en.map(s => `<li>${esc(s)}</li>`).join('');
    const lossN = one?.prob_loss ? Math.max(2, Math.round(1 / one.prob_loss)) : null;
    const wd = p.projection.withdrawal, goal = p.projection.goal;
    const region = Object.entries(p.mix.region).filter(([, v]) => v >= 0.005);
    const lookThrough = p.holdings.some(h => h.asset_class === 'Multi-asset' || h.region === 'Global');
    const goalLine = st.answers.A1 && st.profile ? L.goalContext(this.optText('A1', st.answers.A1), st.answers.B1 && this.applicable('B1') ? this.optText('B1', st.answers.B1) : '') : '';
    const fxExposed = p.holdings.filter(h => { const f = this.M.fund(h.ticker); return f && !f.hedged && h.asset_class !== 'Cash' && ((p.market === 'CA' && h.region !== 'Canada') || (p.market === 'US' && !['US', 'North America'].includes(h.region))) && !(h.asset_class === 'Fixed income' && f.hedged); }).reduce((s, h) => s + h.weight, 0);
    const node = this.el(`
      <header class="mix-head"><h3>${p.mode === 'own_weights' ? esc(L.mixTitleOwn(p.stats.n_holdings, p.risk.level)) : `${esc(L.mixTitle(p.risk.level, p.stats.n_holdings))} <span class="muted">· ${esc(lvlLabel)}</span>`}</h3>
        ${ex ? `<p class="tagline-above">${esc(L.trayAbove(st.level, st.profile.suggested_level))}</p>` : ''}
        ${goalLine ? `<p class="small">${esc(goalLine)}</p>` : ''}
        <p class="small muted">${esc(own ? L.mixSubOwn : changedFunds ? L.mixSub : L.mixSubRef)} ${esc(L.dataLine(p.as_of))}.</p></header>
      ${this.classBar(p.mix.asset_class)}${this.legend(p.mix.asset_class)}
      <dl class="keynums">
        <div><dt>${esc(L.typicalYear)}</dt><dd>${esc(L.between(this.fmtMoney(yr.p10), this.fmtMoney(yr.p90)))}</dd></div>
        <div><dt>${esc(L.badYear)}</dt><dd>${esc(this.fmtMoney(yr.p5))} <small>${esc(`(${this.fmtMoney(yr.p5 - yr.base)})`)}</small></dd></div>
        ${wd ? `<div><dt>${esc(L.lastsKey(Math.round(wd.months / 12)))}</dt><dd>${esc(L.ofPaths(this.pct(wd.chance_lasts)))}</dd></div>` : `<div><dt>${esc(L.lossChance)}</dt><dd>${lossN ? esc(L.oneIn(lossN)) : '-'}</dd></div>`}
        <div><dt>${esc(L.fees)}</dt><dd>${esc(this.feeText(p))} <small>${esc(`(${this.pct(p.stats.weighted_mer, 2)})`)}</small></dd></div>
      </dl>
      ${wd && wd.chance_lasts < 0.5 ? `<p class="small warnline">${icon('warning', 14)}<span>${esc(L.lastsLow(Math.round(wd.months / 12), wd.p50_months != null ? Math.round(wd.p50_months / 12) : null))}</span></p>` : ''}
      ${p.projection.monthly_contribution ? `<p class="small muted">${esc(L.flowNote(this.fmtMonthly(p.projection.monthly_contribution)))}</p>` : ''}
      ${cashShare >= 0.02 ? `<p class="small ${cashShare >= 0.1 ? 'warnline' : 'muted'}">${esc(L.cashShare(this.fmtMoney(p.stats.cash_left), this.pct(cashShare)))}</p>` : ''}
      <section class="blk"><div class="blk-head"><h4>${esc(L.holdings)}</h4><div class="row"><button class="btn small" data-shelf aria-expanded="${st.ui.shelf}">${esc(L.editFunds)}</button><button class="btn small" data-weights aria-expanded="${st.ui.weights}">${esc(p.mode === 'own_weights' ? L.letModel : L.ownWeights)}</button><button class="btn small" data-copy>${esc(L.copyList)}</button></div></div>
        <div class="tablewrap"><table class="holds-t"><thead><tr><th scope="col">${esc(L.colFund)}</th><th scope="col" class="bar"><span class="sr">${esc(L.band)}</span></th><th scope="col" class="num">${esc(L.colWeight)}</th><th scope="col" class="num">${esc(L.colDollars)}</th></tr></thead><tbody>${rows}</tbody></table></div>
        <p class="small muted"><span class="band-key"></span> ${esc([L.band, pxDate ? L.unitsNote(pxDate) : '', p.stats.cash_left != null ? L.cashLeft(this.fmtMoney(p.stats.cash_left)) : ''].filter(Boolean).join(' · '))}</p>
        ${zeroUnits ? `<p class="small warnline">${icon('warning', 14)}<span>${esc(L.zeroUnitsNote)}${p.market === 'US' ? ' ' + esc(L.fractional) : ''}</span></p>` : ''}
        ${notHeld ? `<ul class="checks">${notHeld}</ul>` : ''}
        <div data-slot="weights"></div><div data-slot="shelf"></div></section>
      <section class="blk" data-slot="addmoney">${this.addMoneyHTML(p)}</section>
      <section class="blk" data-slot="onefund"><h4>${esc(L.oneFundTitle)}</h4><div class="skel-line"><span class="skel wide"></span></div></section>
      <section class="blk"><h4>${esc(L.explain)}</h4><ul class="expl">${expl}</ul></section>
      <section class="blk"><h4>${esc(L.stress)}</h4><div class="stress">${stress}</div></section>
      <section class="blk"><h4>${esc(L.whereTitle)}</h4><div class="regions">${region.map(([r, v]) => `<span class="reg"><b>${this.pct(v)}</b> ${esc(r)}</span>`).join('')}</div>${fxExposed > 0.005 ? `<p class="small muted">${esc(L.currencyLine(this.pct(fxExposed)))}</p>` : ''}${lookThrough ? `<p class="small muted">${esc(L.lookThrough)}</p>` : ''}</section>
      <section class="blk"><h4>${esc(L.periods)}</h4><div class="hp">${hp}</div></section>
      <section class="blk"><h4>${esc(L.projection)}</h4>
        <div class="proj-ctl"><label class="field"><span>${esc(L.amount)}</span><input data-k="amount" inputmode="decimal" value="${st.amount}"></label><label class="field"><span>${esc(L.monthlyWithdraw)}</span><input data-k="monthly" inputmode="decimal" value="${st.monthly}"></label><label class="field"><span>${esc(L.years)}</span><input data-k="years" type="number" value="${st.years}" min="1" max="40"></label><label class="field"><span>${esc(L.goal)}</span><input data-k="goal" inputmode="decimal" value="${st.goal ?? ''}"></label></div>
        ${this.fan(p.projection)}<p class="small muted">${esc(L.fanNote)}</p>
        ${wd ? `<p>${esc(L.withdrawLine(this.fmtMoney(wd.monthly), this.pct(wd.chance_lasts), Math.round(wd.months / 12)))}${wd.chance_lasts < 0.5 && wd.p50_months != null ? ' ' + esc(L.median50(Math.round(wd.p50_months / 12))) : ''}${wd.chance_lasts < 0.9 ? ' ' + esc(L.worst10(Math.round(wd.p10_months / 12))) : ''}</p>` : ''}
        ${goal ? `<p>${esc((wd ? L.goalLineWd : L.goalLine)(this.pct(1 - p.projection.chance_need_to_adjust), this.fmtMoney(goal)))}</p><div data-slot="levers"><span class="skel wide"></span></div>` : ''}</section>
      <section class="blk"><h4>${esc(L.checks)}</h4><ul class="checks">${checks}</ul></section>
      <div class="row"><button class="btn small" data-summary>${esc(L.copySummary)}</button><button class="btn small" data-forai>${esc(L.copyAI)}</button></div>
      <details class="how"><summary>${esc(L.showHow)}</summary>${this.mechanism(p)}</details>
      <p class="disc small muted">${esc(this.core.projection_disclosure.en)}</p>`, 'card card-mix');
    this.push(node, { key: 'mix', scroll });
    node.querySelectorAll('[data-t]').forEach(b => b.addEventListener('click', () => this.cardFund(b.dataset.t)));
    node.querySelectorAll('.proj-ctl input').forEach(inp => inp.addEventListener('change', () => {
      const k = inp.dataset.k, raw = inp.value.trim();
      if (k === 'amount') { const v = parseAmount(raw); if (!v || v < 100) { inp.setCustomValidity(L.amountMin); inp.reportValidity(); return; } inp.setCustomValidity(''); st.amount = v; }
      else if (k === 'monthly') { const v = parseMonthly(raw); if (v == null) { inp.setCustomValidity(L.monthlyBad); inp.reportValidity(); return; } inp.setCustomValidity(''); this.setMonthly(v); return; }
      else if (k === 'goal') { st.goal = raw ? parseAmount(raw) : null; }
      else { st.years = Math.max(1, Math.min(40, Number(raw) || 10)); st.yearsSet = true; }
      this.renderTray(); this.rebuild();
    }));
    node.querySelector('[data-shelf]').addEventListener('click', () => {
      st.ui.shelf = !st.ui.shelf; this.renderMix();
      if (st.ui.shelf) requestAnimationFrame(() => { const b = this.live.mix?.querySelector('.shelf-box'); b?.scrollIntoView({ block: 'nearest' }); b?.querySelector('select, button')?.focus({ preventScroll: true }); });
    });
    node.querySelector('[data-weights]').addEventListener('click', () => {
      if (p.mode === 'own_weights') {
        this.toModel(); this.rebuild();
        this.undoNote('modelBack', () => { st.mix.fixedWeights = st.mix.lastFixedWeights; st.userChanged = true; this.rebuild(); });
        return;
      }
      st.ui.weights = !st.ui.weights; st.ui.draftWeights = this.weightDraft(p); this.renderMix();
      if (st.ui.weights) requestAnimationFrame(() => { const i = this.live.mix?.querySelector('[data-w]'); i?.scrollIntoView({ block: 'nearest' }); i?.focus(); });
    });
    node.querySelectorAll('[data-giveweight]').forEach(b => b.addEventListener('click', () => {
      const t = b.dataset.giveweight; st.ui.weights = true; st.ui.draftWeights = { ...this.weightDraft(p), [t]: 0 }; this.renderMix();
      requestAnimationFrame(() => { const i = this.live.mix?.querySelector(`[data-w="${CSS.escape(t)}"]`); i?.scrollIntoView({ block: 'nearest' }); i?.focus(); });
    }));
    node.querySelectorAll('[data-minremove]').forEach(b => b.addEventListener('click', () => { const t = b.dataset.minremove; delete st.mix.minimums[t]; st.userChanged = true; this.rebuildMoved(['lblMinOff', sym(t)]); }));
    node.querySelector('[data-copy]').addEventListener('click', (e) => this.copy(this.listText(p), e.currentTarget));
    node.querySelector('[data-summary]').addEventListener('click', (e) => this.copy(this.summaryText(p), e.currentTarget));
    node.querySelector('[data-forai]').addEventListener('click', (e) => this.copy(this.aiText(p), e.currentTarget));
    node.querySelectorAll('[data-minapply]').forEach(b => b.addEventListener('click', () => {
      const t = b.dataset.minapply, v = Number(node.querySelector(`[data-min="${CSS.escape(t)}"]`).value) / 100;
      if (v > 0.1) this.noteL('minCapped', sym(t)); else if (!(v >= 0.02)) this.noteL('minFloor', sym(t));  // said, never silently changed
      st.mix.minimums[t] = Math.max(0.02, Math.min(0.1, v || 0.02)); st.userChanged = true; this.rebuildMoved(['lblMin', sym(t), this.pct(st.mix.minimums[t])]);
    }));
    if (st.ui.shelf) this.renderShelf(node.querySelector('[data-slot="shelf"]'));
    if (st.ui.weights) this.renderWeights(node.querySelector('[data-slot="weights"]'), p);
    if (node._pendingSpot) { const t = node.querySelectorAll(node._pendingSpot.sel)[Math.max(0, node._pendingSpot.i)]; if (t) t.focus({ preventScroll: true }); delete node._pendingSpot; }
    this.bindAddMoney(node.querySelector('[data-slot="addmoney"]'), p);
    if (goal) this.goalLevers(p).then(ls => { const slot = node.querySelector('[data-slot="levers"]'); if (slot && node.isConnected) slot.innerHTML = this.leversHTML(p, ls); });
    this.oneFundFor(p).then(o => { const slot = node.querySelector('[data-slot="onefund"]'); if (slot && node.isConnected) slot.innerHTML = this.oneFundHTML(p, o); });
  }
  /** "Add money without selling": new money split so the holdings move toward the mix, nothing sold (Passiv-style). */
  addMoneyHTML(p) {
    const L = this.L, st = this.st, am = st.ui.addMoney || (st.ui.addMoney = { cash: st.monthly > 0 ? String(st.monthly) : '', now: {} });
    return `<h4>${esc(L.addMoneyTitle)}</h4><p class="small muted">${esc(L.addMoneySub)}</p>
      <details class="addmoney" ${am.open ? 'open' : ''}><summary class="small">${esc(L.addMoneyOpen)}</summary>
      <div class="wgrid">${p.holdings.map(h => `<label class="field"><span>${esc(L.holdNow(h.symbol, this.ccy))}</span><input inputmode="decimal" autocomplete="off" data-now="${esc(h.ticker)}" value="${esc(am.now[h.ticker] ?? '')}" placeholder="0"></label>`).join('')}</div>
      <div class="row"><label class="field"><span>${esc(L.newMoney(this.ccy))}</span><input inputmode="decimal" autocomplete="off" data-cash value="${esc(am.cash)}" placeholder="1000"></label><button class="btn small primary" data-plan>${esc(L.showBuys)}</button></div>
      <div data-plan-out role="status" aria-live="polite">${am.result ? this.planHTML(am.result) : ''}</div></details>`;
  }
  planHTML(r) {
    const L = this.L;
    // whole units at the last close: what is actually bought, what stays in cash, and the weights after those buys
    const spend = (x) => (x.units != null && x.price ? x.units * x.price : x.buy);
    const spent = r.rows.reduce((s, x) => s + spend(x), 0), left = Math.max(0, r.new_money - spent), tot = r.held_now + spent;
    const after = (x) => (tot ? (x.now + spend(x)) / tot : null);
    const driftAfter = r.rows.reduce((s, x) => s + Math.abs((after(x) ?? x.target) - x.target), 0) / 2;
    const rows = r.rows.map(x => `<tr><th scope="row">${esc(x.symbol)}</th><td class="num">${esc(this.fmtMoney(x.buy))}</td><td class="num">${x.units != null ? esc(L.units(x.units)) : '-'}</td><td class="num">${x.now_weight != null ? this.pct(x.now_weight, 1) : '-'}</td><td class="num">${this.pct(after(x), 1)}</td><td class="num">${this.pct(x.target, 1)}</td></tr>`).join('');
    return `<div class="tablewrap"><table><thead><tr><th scope="col">${esc(L.colFund)}</th><th scope="col" class="num">${esc(L.colBuy)}</th><th scope="col" class="num">${esc(L.colUnits)}</th><th scope="col" class="num">${esc(L.colNow)}</th><th scope="col" class="num">${esc(L.colAfter)}</th><th scope="col" class="num">${esc(L.colTarget)}</th></tr></thead><tbody>${rows}</tbody></table></div>
      <p class="small muted">${esc(r.held_now ? L.planDrift(this.pct(r.drift_before, 1), this.pct(driftAfter, 1), r.gap_closed || driftAfter < 0.0005) : L.planFresh)} ${esc(L.planLeft(this.fmtMoney(left)))}${this.st.market === 'US' && left > 0 ? ' ' + esc(L.fractional) : ''} ${esc(L.planNote)}</p>`;
  }
  bindAddMoney(slot, p) {
    if (!slot) return;
    const st = this.st, am = st.ui.addMoney, L = this.L;
    slot.querySelector('details')?.addEventListener('toggle', (e) => { am.open = e.target.open; });
    slot.querySelectorAll('[data-now]').forEach(i => i.addEventListener('input', () => { am.now[i.dataset.now] = i.value; }));
    slot.querySelector('[data-cash]')?.addEventListener('input', (e) => { am.cash = e.target.value; });
    slot.querySelector('[data-plan]')?.addEventListener('click', () => {
      const cashIn = slot.querySelector('[data-cash]'), cash = parseAmount(cashIn.value);
      if (!cash) { cashIn.setCustomValidity(L.newMoneyBad); cashIn.reportValidity(); return; }
      cashIn.setCustomValidity('');
      const now = {}; for (const [t, v] of Object.entries(am.now)) { const x = parseAmount(v); if (x) now[t] = x; }
      am.result = planContribution(p.holdings, cash, now);
      slot.querySelector('[data-plan-out]').innerHTML = this.planHTML(am.result);
    });
  }
  /** Three levers on the goal, each a full re-run of the same mix (weights do not depend on the amount, flow or horizon). */
  goalLevers(p) {
    const st = this.st, req = this.req(), key = JSON.stringify([p.market, req]);
    this.leverCache = this.leverCache || new Map();
    if (!this.leverCache.has(key)) {
      const moves = [['monthly', { monthly: (st.monthly || 0) + 100 }], ['years', { years: st.years + 2 }], ['lump', { amount: st.amount + 5000 }]];
      this.leverCache.set(key, Promise.all(moves.map(([k, extra]) => this.run('build', { ...req, ...extra }).then(r => ({ key: k, chance: 1 - r.result.projection.chance_need_to_adjust })).catch(() => null))));
    }
    return this.leverCache.get(key);
  }
  leversHTML(p, ls) {
    const L = this.L, base = 1 - p.projection.chance_need_to_adjust, ok = (ls || []).filter(Boolean);
    if (!ok.length) return '';
    const wd = (p.projection.monthly_contribution || 0) < 0;  // for a withdrawal plan the monthly lever is taking out less, and more years is a harder test
    const label = { monthly: wd ? L.leverWithdrawLess(this.fmtMoney(100)) : L.leverMonthly(this.fmtMoney(100)), years: wd ? L.leverLastLonger(2) : L.leverYears(2), lump: L.leverLump(this.fmtMoney(5000)) };
    return `<ul class="levers small">${ok.map(x => `<li><span>${esc(label[x.key])}</span><b>${esc(this.pct(x.chance))}</b><small class="muted">${esc(L.pts(Math.round(x.chance * 100) - Math.round(base * 100)))}</small></li>`).join('')}</ul><p class="small muted">${esc(L.leverNote)}</p>`;
  }
  toolPlanContribution(i) {
    const p = this.st.result; if (!p) return { available: false };
    const now = {}; for (const [t, v] of Object.entries(i.current || {})) { const f = this.resolveFund(t); if (f) now[f.yahoo] = Number(v) || 0; }
    const r = planContribution(p.holdings, Number(i.new_money) || 0, now);
    this.st.ui.addMoney = { open: true, cash: String(r.new_money), now: Object.fromEntries(Object.entries(now).map(([t, v]) => [t, String(v)])), result: r };
    this.refreshMix();
    return { ...r, currency: p.currency, level: p.risk.level, label: 'Hypothetical buy-only split; not an order.' };
  }
  oneFundHTML(p, o) {
    const L = this.L; if (!o) return '';
    const g = (x) => x.stress.find(s => s.key === 'gfc' || s.scenario === '2008 financial crisis');
    const pg = p.stress.find(s => s.key === 'gfc'), og = g(o), yr = this.yearNums(p);
    const row = (label, a, b) => `<tr><th scope="row">${esc(label)}</th><td class="num">${esc(a)}</td><td class="num">${esc(b)}</td></tr>`;
    const crisis = (x) => (x.portfolio_return == null ? L.na : this.fmtMoney(x.dollars) + ((x.estimated || []).length ? ` (${L.estShort})` : ''));
    return `<h4>${esc(L.oneFundTitle)}</h4><p class="small">${esc(L.oneFundLine(sym(o.symbol || o.ticker), this.pct(o.stated_stock_share)))}</p>
      <div class="tablewrap"><table><thead><tr><th></th><th class="num">${esc(L.thisMix)}</th><th class="num">${esc(L.oneFund)}${esc(` (${sym(o.ticker)})`)}</th></tr></thead><tbody>
      ${row(L.fees, this.feeText(p), this.fmtMoney(o.fee_per_year))}
      ${row(L.volatility, this.pct(p.stats.volatility, 1), this.pct(o.volatility, 1))}
      ${row(L.badYear, this.fmtMoney(yr.p5), this.fmtMoney(o.one_year_value?.p5 ?? o.one_year_dollars?.p5))}
      ${pg && og ? row(pg.scenario, crisis(pg), crisis(og)) : ''}
      </tbody></table></div><p class="small muted">${esc(L.oneFundNote)}${p.projection.monthly_contribution ? ' ' + esc(L.oneFundFlow(this.fmtMonthly(p.projection.monthly_contribution), this.fmtMoney(p.projection.amount))) : ''}</p>`;
  }
  renderShelf(slot) {
    const L = this.L, st = this.st, M = this.M;
    if (!st.adult) {  // building is for adults: one line, not the whole self-check (search and cards stay open to all)
      slot.innerHTML = `<div class="shelf-box"><p class="small muted">${esc(L.adultNeeded)}</p><button class="btn small" data-adult2>${esc(L.adult)}</button></div>`;
      slot.querySelector('[data-adult2]').addEventListener('click', () => { st.adult = true; this.save(); this.renderMix(); });
      return;
    }
    const shelf = shelfFor(M, { swaps: st.mix.swaps, exclude: [] });
    const held = new Set(this.trayTickers());
    const row = (s) => {
      const sl = M.sleeveByKey.get(s.sleeve);
      const opts = [...new Set([s.ticker, ...sl.candidates])].slice(0, 6).map(t => { const f = M.fund(t); return `<option value="${esc(t)}" ${t === s.ticker ? 'selected' : ''}>${esc(f.symbol)}${t === s.reference ? ` · ${esc(L.refTag)}` : ''} · ${f.mer != null ? esc(this.pct(f.mer, 2)) + ' ' + esc(L.mer) : esc(L.feeNA)} · ${esc(f.name)}</option>`; }).join('');
      const off = st.mix.exclude.includes(s.ticker);
      return `<div class="shelf-row ${off ? 'is-off' : ''}" data-sleeve="${s.sleeve}" data-cur="${esc(s.ticker)}"><span class="dot" style="background:${CLASS_COLOR[s.asset_class]}"></span><div class="shelf-main"><b>${esc(s.label)}</b><span class="small muted">${esc(s.plain)}</span><select aria-label="${esc(s.label)}" ${off ? 'disabled' : ''}>${opts}</select></div><button class="link" data-toggle aria-label="${esc(off ? L.addBackClass(s.label, M.fund(s.ticker)?.symbol || sym(s.ticker)) : L.removeClass(s.label, M.fund(s.ticker)?.symbol || sym(s.ticker)))}">${esc(off ? L.addBack : L.remove)}</button></div>`;
    };
    const inMix = shelf.filter(s => held.has(s.ticker) || st.mix.exclude.includes(s.ticker)), other = shelf.filter(s => !inMix.includes(s));
    const sats = st.mix.satellites.map(t => { const f = M.fund(t); return `<div class="shelf-row" data-sat="${esc(t)}"><span class="dot" style="background:${CLASS_COLOR[f?.asset_class] || 'var(--ink-3)'}"></span><div class="shelf-main"><b>${esc(f?.symbol || t)}</b><span class="small muted">${esc(f?.name || '')}${held.has(t) ? '' : ' · ' + esc(L.addedNotHeld)}</span></div><button class="link" data-unsat aria-label="${esc(L.removeAdded(f?.symbol || sym(t)))}">${esc(L.remove)}</button></div>`; }).join('');
    slot.innerHTML = `<div class="shelf-box"><h5>${esc(L.shelfTitle)}</h5><p class="small muted">${esc(L.shelfSub)}</p><div class="shelf">${inMix.map(row).join('')}${sats}</div>
      ${other.length ? `<details><summary class="small">${esc(L.otherClasses)}</summary><div class="shelf">${other.map(row).join('')}</div></details>` : ''}
      <form class="shelf-add"><label class="field"><span>${esc(L.addOwn)}</span><input type="search" data-shelfadd placeholder="${esc(L.searchHere)}" list="dl-funds" autocomplete="off"></label><button class="btn" type="submit" data-shelfaddbtn>${icon('plus', 16)} ${esc(this.L.add)}</button></form>
      <div class="row"><button class="btn primary small" data-done>${esc(L.done)}</button></div></div>`;
    slot.querySelectorAll('.shelf-row select').forEach(sel => sel.addEventListener('change', () => {
      const row = sel.closest('.shelf-row'), k = row.dataset.sleeve, was = row.dataset.cur, now = sel.value, fw = st.mix.fixedWeights;
      st.mix.swaps[k] = now; st.userChanged = true;
      if (fw && was && fw[was] != null && was !== now) {  // own weights: the new fund takes the old one's weight, in place
        fw[now] = (fw[now] || 0) + fw[was]; delete fw[was];
        this.noteL('weightMoved', sym(now), sym(was), this.pct(fw[now]));
        this.rebuild();
      } else this.rebuildMoved(['lblSwap', sym(was), sym(now)]);
    }));
    slot.querySelectorAll('[data-toggle]').forEach(b => b.addEventListener('click', () => { const row = b.closest('.shelf-row'); const t = row.querySelector('select').value; const ex = st.mix.exclude; const i = ex.indexOf(t); if (i >= 0) ex.splice(i, 1); else ex.push(t); st.userChanged = true; this.rebuildMoved([i >= 0 ? 'lblAddBack' : 'lblRemove', sym(t)]); }));
    slot.querySelectorAll('[data-unsat]').forEach(b => b.addEventListener('click', () => { const t = b.closest('.shelf-row').dataset.sat; st.mix.satellites = st.mix.satellites.filter(x => x !== t); delete st.mix.minimums[t]; if (st.mix.fixedWeights) delete st.mix.fixedWeights[t]; this.rebuildMoved(['lblRemove', sym(t)]); }));
    slot.querySelector('.shelf-add').addEventListener('submit', (e) => { e.preventDefault(); const inp = e.target.querySelector('input'), v = inp.value.trim(); if (!v) return; const f = this.resolveFund(v.split(' ')[0]); if (f) { this.addFund(f.yahoo); inp.value = ''; } else { const r = searchFunds(this.M, { query: v, limit: 8 }); if (r.results.length) this.cardResults(r); else this.noteL('noMatch', v); } });
    slot.querySelector('[data-done]').addEventListener('click', () => { st.ui.shelf = false; this.renderMix(); });
    this.fillDatalist();
  }
  /** Starting numbers for the weights grid: the last own weights if there are any, else the model's, as whole percents
   *  adding up to 100, with every pick listed (at 0 when it has no weight). */
  weightDraft(p) {
    const m = this.st.mix, src = m.fixedWeights || m.lastFixedWeights || Object.fromEntries(p.holdings.map(h => [h.ticker, h.weight]));
    const d = this.toPercents(src);
    for (const t of [...p.holdings.map(h => h.ticker), ...m.satellites]) if (!(t in d)) d[t] = 0;
    return d;
  }
  renderWeights(slot, p) {
    const L = this.L, st = this.st, d = st.ui.draftWeights || this.weightDraft(p);
    st.ui.draftWeights = d;
    const total = () => Math.round(Object.values(d).reduce((s, v) => s + (Number(v) || 0), 0) * 100) / 100;
    const name = (t) => this.M.fund(t)?.symbol || sym(t);
    slot.innerHTML = `<div class="weights-box"><div class="wgrid">${Object.keys(d).map(t => `<label class="field"><span>${esc(name(t))}</span><input type="number" min="0" max="100" step="1" value="${d[t] ?? 0}" data-w="${esc(t)}" aria-label="${esc(L.weightFor(name(t)))}"></label>`).join('')}</div>
      <p class="small" data-total role="status" aria-live="polite"></p><div class="row"><button class="btn primary small" data-use>${esc(L.useWeights)}</button><button class="btn ghost small" data-cancel>${esc(L.cancel)}</button></div></div>`;
    const show = () => { const t = total(), ok = Math.abs(t - 100) < 0.01, el = slot.querySelector('[data-total]'); el.textContent = ok ? L.weightsOk : L.weightsOff(t, Math.round((t - 100) * 100) / 100); el.classList.toggle('warn', !ok); slot.querySelector('[data-use]').disabled = !ok; };
    show();
    slot.querySelectorAll('[data-w]').forEach(inp => inp.addEventListener('input', () => { d[inp.dataset.w] = Math.max(0, Number(inp.value) || 0); show(); }));
    slot.querySelector('[data-use]').addEventListener('click', () => { if (Math.abs(total() - 100) >= 0.01) return; st.mix.fixedWeights = Object.fromEntries(Object.entries(d).filter(([, v]) => v > 0).map(([t, v]) => [t, v / 100])); st.ui.weights = false; st.ui.draftWeights = null; st.userChanged = true; this.rebuild(); });
    slot.querySelector('[data-cancel]').addEventListener('click', () => { st.ui.weights = false; st.ui.draftWeights = null; this.renderMix(); });
  }
  listText(p) {
    const L = this.L;
    const m = this.st.mix, head = p.mode === 'own_weights' ? L.listHeadOwn(p.holdings.length, this.fmtMoney(p.projection.amount)) : (Object.keys(m.swaps).length || m.satellites.length || m.exclude.length) ? L.listHead(p.risk.level, this.fmtMoney(p.projection.amount)) : L.listHeadRef(p.risk.level, this.fmtMoney(p.projection.amount));
    return [head, ...p.holdings.map(h => `${h.symbol}\t${this.pct(h.weight, 1)}\t${this.fmtMoney(h.dollars)}${h.units != null ? `\t${L.units(h.units)}` : ''}${h.price ? `\t${L.priceAt(h.price.toLocaleString('en-US', { maximumFractionDigits: 2 }), h.price_date || '')}` : ''}`),
      p.stats.cash_left != null ? L.cashLeft(this.fmtMoney(p.stats.cash_left)) : '', L.dataLine(p.as_of)].filter(Boolean).join('\n');
  }
  summaryText(p) {
    const L = this.L, pr = this.st.profile, yr = this.yearNums(p);
    return [`Robo-Kit · ${L.mixTitle(p.risk.level, p.stats.n_holdings)} · ${L.dataLine(p.as_of)}`,
      pr && pr.status !== 'incomplete' ? (this.isAbove() ? L.summaryAbove(pr.suggested_level, this.st.level) : this.st.levelChosen ? L.summary(pr.suggested_level, this.st.level) : L.summaryRef(pr.suggested_level, this.st.level)) : '',
      '', this.listText(p), '',
      `${L.typicalYear}: ${L.between(this.fmtMoney(yr.p10), this.fmtMoney(yr.p90))}`, `${L.badYear}: ${this.fmtMoney(yr.p5)}`, `${L.fees}: ${this.feeText(p)}`,
      ...(p.projection.monthly_contribution ? [L.flowNote(this.fmtMonthly(p.projection.monthly_contribution))] : []),
      ...(p.projection.withdrawal ? [L.withdrawLine(this.fmtMoney(p.projection.withdrawal.monthly), this.pct(p.projection.withdrawal.chance_lasts), Math.round(p.projection.withdrawal.months / 12))] : []),
      '', `${L.stress}:`, ...p.stress.map(s => `- ${s.scenario}: ${this.fmtMoney(s.dollars)} (${this.sgnPct(s.portfolio_return)})`),
      '', ...p.explanation.en, '', this.core.projection_disclosure.en, L.footer].join('\n');
  }
  aiText(p) { return '```json\n' + JSON.stringify({ source: 'Robo-Kit (hypothetical, educational)', profile: this.profileSummary(), mix: this.mixSummary(p) }, null, 1) + '\n```'; }
  async copy(text, btn) {
    const L = this.L, old = btn.textContent;
    try { await navigator.clipboard.writeText(text); btn.textContent = L.copied; setTimeout(() => { btn.textContent = old; }, 1600); }
    catch {
      const row = btn.closest('.row') || btn.parentElement;
      let box = row.nextElementSibling?.classList.contains('copywrap') ? row.nextElementSibling : null;
      if (!box) { box = document.createElement('div'); box.className = 'copywrap'; row.after(box); }
      box.innerHTML = `<p class="small muted">${esc(L.copyFail)}</p><textarea class="copybox" readonly rows="8" aria-label="${esc(old)}">${esc(text)}</textarea>`;
      btn.textContent = L.copySeeBelow; setTimeout(() => { btn.textContent = old; }, 2400);
      const ta = box.querySelector('textarea'); ta.focus(); ta.select();
    }
  }
  fillDatalist() {
    let dl = $('#dl-funds'); if (dl && dl.dataset.m === this.st.market) return;
    if (!dl) { dl = document.createElement('datalist'); dl.id = 'dl-funds'; document.body.appendChild(dl); }
    dl.dataset.m = this.st.market;
    dl.innerHTML = this.M.rows.filter(r => r.eligible).map(r => `<option value="${esc(r.symbol)} ${esc(r.name)}"></option>`).join('');
  }
  addFund(t) {
    const f = this.resolveFund(t); if (!f) return false;
    if (f.market !== this.st.market) { this.noteL('otherMarket', f.symbol, f.market); return false; }
    if (!f.eligible) { this.noteL('notUsed', f.symbol, f.excluded_because); return false; }
    const held = this.st.result?.holdings.find(h => h.ticker === f.yahoo);
    if (held || this.st.mix.satellites.includes(f.yahoo)) { if (held) this.noteL('alreadyIn', f.symbol, () => this.sleeveLabel(held), this.pct(held.weight)); else this.noteL('alreadyPick', f.symbol); return true; }
    this.st.mix.satellites.push(f.yahoo); this.st.userChanged = true;
    document.body.classList.add('stamp'); setTimeout(() => document.body.classList.remove('stamp'), 400);
    this.rebuildMoved(['lblAdd', f.symbol], { addedTicker: f.yahoo });
    return true;
  }
  rangeBar([lo, hi], kind) {
    const min = kind === 'one_year' ? 0.7 : 0.8, max = kind === 'one_year' ? 1.45 : 4.2;
    const x = (v) => Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100));
    return `<span class="rb" aria-hidden="true"><span class="rb-zero" style="left:${x(1)}%"></span><span class="rb-seg" style="left:${x(lo)}%;width:${Math.max(1, x(hi) - x(lo))}%"></span></span>`;
  }
  classBar(mix, size = '') {
    const parts = Object.entries(mix).filter(([, v]) => v > 0.001);
    return `<span class="cbar ${size}" role="img" aria-label="${esc(parts.map(([k, v]) => `${k} ${this.pct(v)}`).join(', '))}">${parts.map(([k, v]) => `<span style="flex-grow:${v};background:${CLASS_COLOR[k] || 'var(--ink-3)'}"></span>`).join('')}</span>`;
  }
  legend(mix) { return `<div class="legend">${Object.keys(CLASS_COLOR).filter(k => mix[k]).map(k => `<span><i style="background:${CLASS_COLOR[k]}"></i>${esc(k)}</span>`).join('')}</div>`; }
  fan(pr) {
    const W = 640, H = 220, pl = 64, pr_ = 12, pt = 12, pb = 28;
    const ys = pr.yearly; const maxV = Math.max(...ys.map(y => y.p90)) * 1.05, minV = 0;
    const x = (i) => pl + (i / (ys.length - 1)) * (W - pl - pr_); const y = (v) => pt + (1 - (v - minV) / (maxV - minV)) * (H - pt - pb);
    const area = (a, b) => ys.map((r, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(r[a]).toFixed(1)}`).join('') + ys.slice().reverse().map((r, i) => `L${x(ys.length - 1 - i).toFixed(1)},${y(r[b]).toFixed(1)}`).join('') + 'Z';
    const line = ys.map((r, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(r.p50).toFixed(1)}`).join('');
    const step = maxV / 4; const nice = Math.pow(10, Math.floor(Math.log10(step || 1))); const stp = Math.ceil(step / nice) * nice;
    const grid = []; for (let v = 0; v <= maxV; v += stp) grid.push(v);
    const last = ys[ys.length - 1];
    return `<div class="fanwrap"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(`${this.L.projection}: ${this.L.fanAria(last.year, this.fmtMoney(last.p10), this.fmtMoney(last.p90))}`)}">
      ${grid.map(v => `<line x1="${pl}" x2="${W - pr_}" y1="${y(v)}" y2="${y(v)}" class="grid"/><text x="${pl - 8}" y="${y(v) + 4}" text-anchor="end" class="axis">${v >= 1000 ? '$' + Math.round(v / 1000).toLocaleString('en-US') + 'k' : '$' + Math.round(v)}</text>`).join('')}
      ${ys.filter((_, i) => i % Math.max(1, Math.round(ys.length / 6)) === 0 || i === ys.length - 1).map(r => `<text x="${x(r.year)}" y="${H - 8}" text-anchor="middle" class="axis">${r.year}</text>`).join('')}
      <path d="${area('p10', 'p90')}" class="fan-outer"/><path d="${area('p25', 'p75')}" class="fan-inner"/><path d="${line}" class="fan-line"/>
      <circle cx="${x(ys.length - 1)}" cy="${y(last.p50)}" r="3.5" class="fan-dot"/>
      <text x="${x(ys.length - 1) - 6}" y="${y(last.p50) - 8}" text-anchor="end" class="val">${esc(this.fmtMoney(last.p50))}</text></svg></div>`;
  }
  mechanism(p) {
    const L = this.L;
    const priorHeld = p.holdings.reduce((s, h) => s + (p.method.prior?.[h.ticker] || 0), 0);
    const rows = p.holdings.map(h => `<tr><th scope="row">${esc(h.symbol)}</th><td>${this.pct(p.method.prior[h.ticker] || 0, 1)}</td><td>${this.pct(h.model_return, 1)}</td><td>${this.pct(h.planning_return_net, 1)}</td><td>${this.pct(h.volatility, 1)}</td><td>${this.pct(h.risk_share)}</td></tr>`).join('');
    const series = (x) => { const m = String(x).match(/^rate (.+)$/); return m ? (SERIES[m[1]] ? SERIES[m[1]].en : m[1]) : sym(x); };
    const hist = Object.entries(p.history || {}).filter(([t]) => p.holdings.some(h => h.ticker === t)).map(([t, ns]) => `<li><b>${esc(this.M.fund(t)?.symbol || t)}:</b> ${ns.map(n => n.proxy ? `${esc(series(n.proxy))} ${esc(n.from)} to ${esc(n.to)}${n.converted_to_cad ? ' (CAD)' : ''}${n.overlap_corr != null ? `, r = ${n.overlap_corr}` : ''}` : `${esc(n.method)} ${esc(n.from)} to ${esc(n.to)}, R² = ${n.r2}`).join('; ')}</li>`).join('');
    const lvAsk = Math.round(p.risk.level), lv = { 1: 2, 2: 2, 3: 3, 4: 4, 5: 4 }[lvAsk];
    const ph = p.projection.history;
    return `<div class="mech">
      <dl class="pairs small">
        ${p.risk.target_vol != null ? `<div><dt>${esc(L.target)}</dt><dd>${this.pct(p.risk.target_vol, 1)} = ${this.pct(p.risk.risk_share)} × ${this.pct(p.risk.stock_market_vol, 1)}${esc(` (${L.stockVol})`)}${p.risk.achieved_vol != null && Math.abs(p.risk.achieved_vol - p.risk.target_vol) >= 0.002 ? esc(` (${L.reached(this.pct(p.risk.achieved_vol, 1))})`) : ''}</dd></div>` : ''}
        ${p.risk.lambda != null ? `<div><dt>${esc(L.lambda)}</dt><dd>${p.risk.lambda}</dd></div>` : ''}
        <div><dt>${esc(L.shrink)}</dt><dd>${p.method.shrinkage}</dd></div>
        <div><dt>${esc(L.draws)}</dt><dd>${p.method.n_boot}</dd></div>
        <div><dt>${esc(L.window)}</dt><dd>${esc(p.window.start)} to ${esc(p.window.end)}${esc(` (${p.window.months} ${L.months})`)}</dd></div>
        ${ph ? `<div><dt>${esc(L.projWindow)}</dt><dd>${esc(ph.start.slice(0, 7))} to ${esc(ph.end.slice(0, 7))}${esc(` (${ph.months} ${L.months})`)}</dd></div><div><dt>${esc(L.volLong)}</dt><dd>${this.pct(p.stats.volatility_long, 1)}</dd></div>` : ''}
      </dl>
      ${priorHeld < 0.995 && priorHeld > 0 ? `<p class="small muted">${esc(L.priorRest(this.pct(1 - priorHeld)))}</p>` : ''}
      <div class="tablewrap"><table><thead><tr><th scope="col">${esc(L.tableFund)}</th><th scope="col">${esc(L.priorW)}</th><th scope="col">${esc(L.modelR)}</th><th scope="col">${esc(L.planR)}</th><th scope="col">${esc(L.volC)}</th><th scope="col">${esc(L.rs)}</th></tr></thead><tbody>${rows}</tbody></table></div>
      ${hist ? `<h5>${esc(L.splices)}</h5><ul class="small">${hist}</ul>` : ''}
      ${this.backtestTable(p.market, lv, lvAsk)}
    </div>`;
  }
  backtestTable(market, lv, asked = lv) {
    const L = this.L, bt = this.core.backtest?.[market]; if (!bt) return '';
    const rows = bt.stats.filter(r => r.level === lv); if (!rows.length) return '';
    const body = rows.map(r => `<tr><th scope="row">${esc(L.btNames[r.strategy] || r.strategy)}</th><td>${this.pct(r.ann_return, 1)}</td><td>${this.pct(r.ann_vol, 1)}</td><td>${this.pct(r.max_drawdown, 1)}</td><td>${r.sharpe_vs_cash.toFixed(2)}</td></tr>`).join('');
    return `<h5>${esc(L.backtest)} · ${esc(asked !== lv ? L.btNotTested(asked, lv) : `${L.level} ${lv}`)} · ${esc(rows[0].from?.slice(0, 7) || '')} to ${esc(rows[0].to?.slice(0, 7) || '')}</h5><div class="tablewrap"><table><thead><tr><th scope="col">${esc(L.btStrategy)}</th><th scope="col">${esc(L.btRet)}</th><th scope="col">${esc(L.btVol)}</th><th scope="col">${esc(L.btDD)}</th><th scope="col">${esc(L.btSharpe)}</th></tr></thead><tbody>${body}</tbody></table></div>`;
  }
  cardBacktest(lv, asked) { return this.push(this.el(`<div class="mech">${this.backtestTable(this.st.market, lv, asked)}</div>`, 'card')); }

  // ---------------------------------------------------------------- funds, search, compare, context, terms, proposals
  cardResults(r) {
    const L = this.L;
    const inMix = new Set([...this.trayTickers(), ...this.st.mix.satellites]);
    const rows = r.results.map(f => `<div class="res-row"><button class="res-main" data-t="${esc(f.yahoo)}"><b>${esc(f.symbol)}</b><span>${esc(f.name)}</span><small class="muted">${esc(f.asset_class)} · ${esc(f.region)}${f.mer != null ? ' · ' + this.pct(f.mer, 2) + ' ' + esc(L.mer) : ''}${f.aum != null ? ' · ' + this.fmtAum(f.aum) : ''}</small></button>${f.eligible ? `<button class="btn small ${inMix.has(f.yahoo) ? 'is-on' : ''}" data-add="${esc(f.yahoo)}" ${inMix.has(f.yahoo) ? 'disabled' : ''}>${inMix.has(f.yahoo) ? esc(L.added) : icon('plus', 14) + ' ' + esc(L.add)}</button>` : `<span class="tag" title="${esc(f.excluded_because)}">${esc(L.excluded)}</span>`}${!f.eligible && f.excluded_because ? `<small class="muted res-why">${esc(f.excluded_because)}</small>` : ''}</div>`).join('');
    const node = this.push(this.el(`<p class="small muted">${esc(L.results(r.matches, r.shown))}</p><div class="results">${rows}</div>`, 'card card-results'));
    node.querySelectorAll('.res-main').forEach(b => b.addEventListener('click', () => this.cardFund(b.dataset.t)));
    node.querySelectorAll('[data-add]').forEach(b => b.addEventListener('click', () => { if (this.addFund(b.dataset.add)) { b.textContent = L.added; b.disabled = true; b.classList.add('is-on'); } }));
    return node;
  }
  cardFund(t) {
    const L = this.L, f = this.resolveFund(t); if (!f) return;
    const tr = trendState(this.markets[f.market], f.yahoo);
    const facts = [[L.mer, f.mer != null ? this.pct(f.mer, 2) : L.feeNA], [L.aum, this.fmtAum(f.aum)], [L.history, `${f.history_months} ${L.months}`], [L.ret1, this.pct(f.ret_1y, 1)], [L.ret5, this.pct(f.ret_5y, 1)], [L.maxdd, this.pct(f.max_drawdown, 1)], [L.yield, this.pct(f.dividend_yield, 1)], [L.trend, tr ? tr.reading : '-']];
    const held = this.st.result?.holdings.find(h => h.ticker === f.yahoo);
    const inPicks = this.st.mix.satellites.includes(f.yahoo);
    const label = held ? `${L.added} · ${this.pct(held.weight, 1)}` : inPicks ? L.addedNotHeld : null;
    const node = this.push(this.el(`
      <header class="fund-head"><div><h3>${esc(f.symbol)} <span class="muted">${esc(f.exchange || '')} · ${esc(f.currency || '')}</span></h3><p>${esc(f.name)}</p><p class="small muted">${esc(f.asset_class)} · ${esc(f.region)}${f.theme ? ' · ' + esc(f.theme) : ''} · ${esc(f.issuer || '')}</p></div>
      ${f.eligible && f.market === this.st.market ? `<button class="btn ${label ? 'is-on' : ''}" data-add ${label ? 'disabled' : ''}>${label ? esc(label) : icon('plus', 14) + ' ' + esc(L.add)}</button>` : ''}</header>
      ${!f.eligible ? `<p class="warnline">${icon('warning', 14)}<span><b>${esc(L.notEligible)}:</b> ${esc(f.excluded_because)}</span></p>` : ''}
      ${f.market !== this.st.market ? `<p class="small muted">${esc(L.otherMarket(f.symbol, f.market))}</p>` : ''}
      <dl class="facts">${facts.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v || '-')}</dd></div>`).join('')}</dl>
      ${f.why ? `<p class="small muted">${esc(L.classNotes)}: ${esc(f.why)}</p>` : ''}
      <p class="small muted">${esc(L.dataLine(this.core.meta.prices_through))}. ${esc(this.core.meta.sources.prices)}.</p>`, 'card card-fund'));
    node.dataset.fund = f.yahoo;
    node.querySelector('[data-add]')?.addEventListener('click', (e) => { const b = e.currentTarget; if (this.addFund(f.yahoo)) { b.textContent = L.addedNotHeld; b.disabled = true; } });
    return node;
  }
  cardCompare(ts) {
    const L = this.L; const fs = ts.map(t => this.resolveFund(t)).filter(Boolean);
    const cols = fs.map(f => this.markets[f.market].returns(f.yahoo));
    const corr = {}; const rows = [];
    for (let a = 0; a < fs.length; a++) for (let b = a + 1; b < fs.length; b++) {
      const xa = cols[a], xb = cols[b]; if (!xa || !xb) continue; const pa = [], pb = [];
      for (let i = Math.max(0, xa.length - 60); i < xa.length; i++) if (Number.isFinite(xa[i]) && Number.isFinite(xb[i])) { pa.push(xa[i]); pb.push(xb[i]); }
      if (pa.length > 12) { const m = (v) => v.reduce((s, x) => s + x, 0) / v.length; const ma = m(pa), mb = m(pb); let sab = 0, saa = 0, sbb = 0; pa.forEach((v, i) => { sab += (v - ma) * (pb[i] - mb); saa += (v - ma) ** 2; sbb += (pb[i] - mb) ** 2; }); const c = sab / Math.sqrt(saa * sbb); corr[`${fs[a].symbol}/${fs[b].symbol}`] = Math.round(c * 1000) / 1000; rows.push(`${fs[a].symbol} / ${fs[b].symbol}: ${c >= 0.995 ? 'above 0.99' : c.toFixed(2)}`); }
    }
    const fields = [[L.feeRow, f => (f.mer != null ? this.pct(f.mer, 2) : L.feeNA)], [L.aum, f => this.fmtAum(f.aum)], [L.history, f => `${f.history_months} ${L.months}`], [L.ret1, f => this.pct(f.ret_1y, 1)], [L.ret5, f => this.pct(f.ret_5y, 1)], [L.maxdd, f => this.pct(f.max_drawdown, 1)], [L.yield, f => this.pct(f.dividend_yield, 1)]];
    const node = this.push(this.el(`<h3>${esc(L.compareTitle)}</h3><div class="tablewrap"><table><thead><tr><th></th>${fs.map(f => `<th scope="col">${esc(f.symbol)}</th>`).join('')}</tr></thead><tbody><tr><th scope="row">${esc(L.name)}</th>${fs.map(f => `<td class="small">${esc(f.name)}</td>`).join('')}</tr>${fields.map(([k, fn]) => `<tr><th scope="row">${esc(k)}</th>${fs.map(f => `<td>${esc(fn(f) || '-')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${rows.length ? `<p class="small"><b>${esc(L.corr)}:</b> ${esc(rows.join('; '))}</p>` : ''}<p class="small muted">${esc(L.dataLine(this.core.meta.prices_through))}</p>`, 'card card-compare'));
    node.corr = corr; return node;
  }
  cardContext() {
    const L = this.L, c = this.core.context, keys = FLAG_CONTEXT[this.st.market];
    const flags = c.flags.filter(f => f.available && keys.includes(f.key)).map(f => { const p = f.percentile; return `<div class="flag"><div><b>${esc(f.label)}</b><small class="muted">${esc(String(f.as_of || '').slice(0, 7))}</small></div><div class="flag-val">${esc(String(f.value))}${f.unit === '%' ? '%' : ''}</div>${p != null ? `<span class="pctl" title="${esc(L.pctl(ordinal(Math.round(p * 100)), f.percentile_since))}"><span style="left:${p * 100}%"></span></span>` : '<span></span>'}<div class="small">${esc(f.reading)}</div></div>`; }).join('');
    const news = c.news && c.news.available ? c.news.topics.map(t => `<div class="news-topic"><b>${esc(t.topic)}</b> <span class="muted small">${esc(L.toneLabel)}: ${esc(t.tone_vs_average)}</span><ul>${t.headlines.slice(0, 3).map(h => `<li>${/^https?:\/\//i.test(h.url || '') ? `<a href="${esc(h.url)}" target="_blank" rel="noopener noreferrer">${esc(h.title)}</a>` : esc(h.title)} <span class="muted small">${esc(h.domain)}</span></li>`).join('')}</ul></div>`).join('') + `<p class="small muted">${esc(String(c.news.note || '').replace(/(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}):\d{2}Z/g, '$1 $2 UTC'))}</p>` : `<p class="small muted">${esc(L.noNews)}</p>`;
    return this.push(this.el(`<h3>${esc(L.contextTitle)}</h3><p class="small muted">${esc(L.contextSub)}</p><div class="flags">${flags}</div><h4>${esc(L.headlines)}</h4>${news}`, 'card card-context'), { key: 'context' });
  }
  cardTerm(k) {
    const g = this.core.glossary[k]; if (!g) return; const t = g.en;
    return this.push(this.el(`<p class="kicker">${esc(this.L.termTitle)}</p><h3>${esc(t.term)}</h3><p>${esc(t.definition)}</p>`, 'card card-term'));
  }
  resolveProp(node, key, ...args) {
    node.classList.add('is-done'); node.querySelectorAll('button').forEach(b => { b.disabled = true; });
    let tag = node.querySelector('.prop-status'); if (!tag) { tag = document.createElement('p'); tag.className = 'small muted prop-status'; tag.setAttribute('role', 'status'); node.appendChild(tag); }
    const v = this.L[key]; tag.textContent = typeof v === 'function' ? v(...args) : v;
  }
  cardProposal(before, after, change) {
    const L = this.L, key = JSON.stringify([change.level, change.diff]);
    const same = [...document.querySelectorAll('.card-prop:not(.is-done)')].find(n => n.dataset.key === key);
    document.querySelectorAll('.card-prop:not(.is-done)').forEach(n => { if (n !== same) this.resolveProp(n, 'replaced'); });
    const w = (p) => new Map(p.holdings.map(h => [h.ticker, h.weight]));
    const wb = w(before), wa = w(after), all = [...new Set([...wb.keys(), ...wa.keys(), ...(change.diff.add || [])])];
    const col = (p) => `<div class="prop-col">${this.classBar(p.mix.asset_class, 'thin')}<dl class="pairs small"><div><dt>${esc(L.level)}</dt><dd>${p.risk.level} · ${esc(p.risk.label)}</dd></div><div><dt>${esc(L.volatility)}</dt><dd>${this.pct(p.stats.volatility, 1)}</dd></div><div><dt>${esc(L.badYear)}</dt><dd>${esc(this.fmtMoney(this.yearNums(p).p5))}</dd></div>${p.projection.withdrawal ? `<div><dt>${esc(L.lastsKey(Math.round(p.projection.withdrawal.months / 12)))}</dt><dd>${esc(L.ofPaths(this.pct(p.projection.withdrawal.chance_lasts)))}</dd></div>` : ''}<div><dt>${esc(L.fees)}</dt><dd>${esc(this.feeText(p))}</dd></div></dl></div>`;
    const moves = all.map(t => `<tr><th scope="row">${esc(sym(t))}</th><td class="num">${this.pct(wb.get(t) || 0, 1)}</td><td class="num">${this.pct(wa.get(t) || 0, 1)}${!wa.get(t) && (change.diff.add || []).includes(t) ? ` <small class="muted">${esc(L.noRoom)}</small>` : ''}</td></tr>`).join('');
    const readOnly = change.needsAck || change.locked;
    const node = this.el(`<h3>${esc(L.proposal)}</h3><div class="prop"><div><h5>${esc(L.before)}</h5>${col(before)}</div><div><h5>${esc(L.after)}</h5>${col(after)}</div></div>
      <div class="tablewrap"><table><thead><tr><th></th><th class="num">${esc(L.before)}</th><th class="num">${esc(L.after)}</th></tr></thead><tbody>${moves}</tbody></table></div>
      ${change.locked ? `<p class="small warnline">${icon('warning', 14)}<span>${esc(L.propLocked(change.level, this.st.profile?.gate_cap))}</span></p>` : change.needsAck ? `<p class="small">${esc(L.propAbove(change.level, this.st.profile?.suggested_level))}</p>` : ''}
      <div class="row">${readOnly ? (change.locked ? '' : `<button class="btn primary" data-explore>${esc(L.exploreBtn(change.level))}</button>`) : `<button class="btn primary" data-apply>${esc(L.apply)}</button>`}<button class="btn ghost" data-no>${esc(L.dismiss)}</button></div>`, 'card card-prop');
    node.dataset.key = key;
    if (same) { same.replaceWith(node); } else this.push(node);
    const prepare = () => {  // the diff lands on the mix as it is now, so later hand edits survive
      const stale = JSON.stringify(this.st.mix) !== change.mixAt;
      this.st.mix = this.mixWithDiff(this.st.mix, change.diff); this.st.userChanged = true;
      return stale;
    };
    let stale = false;
    const onDone = (outcome) => {
      if (outcome === 'applied') this.resolveProp(node, stale ? 'propStale' : 'propApplied');
      else if (outcome === 'explored') this.resolveProp(node, 'propExplored', change.level);
      else if (outcome === 'stayed') this.resolveProp(node, 'propStayed', this.st.level);
      else if (outcome === 'suggested') this.resolveProp(node, 'propSuggested', this.st.profile?.suggested_level ?? this.st.level);
      else node.querySelectorAll('button').forEach(b => { b.disabled = false; });  // dismissed or went to change an answer: the card stays live
    };
    const go = () => {
      if (change.market && change.market !== this.st.market) { this.resolveProp(node, 'propOtherMarket'); return; }
      node.querySelectorAll('button').forEach(b => { b.disabled = true; });
      if (change.level === this.st.level) { stale = prepare(); this.rebuild(); onDone('applied'); }
      else this.chooseLevel(change.level, { from: 'chat', prepare: () => { stale = prepare(); }, onDone, preview: after });
    };
    node.querySelector('[data-apply]')?.addEventListener('click', go);
    node.querySelector('[data-explore]')?.addEventListener('click', go);
    node.querySelector('[data-no]').addEventListener('click', () => this.resolveProp(node, 'propDismissed'));
    return node;
  }
  cardSources() {
    const m = this.core.meta;
    const items = [
      `Data to ${m.prices_through}, snapshot ${m.data_snapshot}, engine ${m.engine_version}.`,
      `Fund lists: ${m.sources.listings}. Prices: ${m.sources.prices}. Rates and currency: ${m.sources.rates}; ${m.sources.fx}. Market context: ${m.sources.context}.`,
      "Classification: Robo-Kit's written rules (name, category, holdings). Every fund carries the reasons for its labels and for any exclusion.",
      'Weights: equilibrium returns implied by a written market anchor, shrunk covariance, a volatility target set by the level, caps, and an average over resampled histories. Weights use the last 15 years; ranges and the bad year use the longest history every fund has, including 2008.',
      "Long-run return figures: FP Canada 2026 planning assumptions, after fund fees. US bonds and cash use today's Treasury yields.",
      'Self-check: the suggestion is the lower of your ability and your willingness to take risk. It is a suggestion, not a ceiling; before a higher level is used, the page shows its bad year and crisis replays in your dollars.',
      'Back-tests and projections are hypothetical. The back-test was written down before it was run, and re-run once under the same rules after a cost error was found (docs/RESEARCH_LOG.md sections 6 and 7).',
      'Licensing: prices and fund lists are licensed for personal use, so this page is for private or team educational use.',
    ];
    return this.push(this.el(`<h3>${esc(this.L.sources)}</h3><ul class="src">${items.map(i => `<li>${esc(i)}</li>`).join('')}</ul>`, 'card'), { key: 'sources' });
  }

  // ---------------------------------------------------------------- tray
  peekLabel() {
    const p = this.st.result; if (!p) return;
    $('#tray-toggle').setAttribute('aria-label', this.L.trayPeek(p.risk.level, this.fmtMoney(this.yearNums(p).p5), this.fmtMoney(p.stats.fee_per_year), this.isAbove(), document.body.classList.contains('tray-open')));
  }
  renderTray() {
    const L = this.L, p = this.st.result, st = this.st, pr = st.profile;
    if (!p) return;
    const amt = p.projection.amount, yr = this.yearNums(p);
    $('#tray-title').textContent = L.trayTitle;
    const ex = this.isAbove(), done = pr && pr.status !== 'incomplete' && pr.suggested_level;
    $('#tray-sub').textContent = p.mode === 'own_weights' ? L.trayOwn(p.risk.level) : ex ? L.trayAbove(st.level, pr.suggested_level) : done ? (st.levelChosen ? L.trayChecked(st.level, pr.suggested_level) : st.level === pr.suggested_level ? L.trayUsing(st.level) : L.trayRefChecked(st.level, pr.suggested_level)) : st.userChanged ? L.trayUser(st.level) : L.trayRef(st.level);
    $('#tray-sub').classList.toggle('above', !!ex);
    const own = p.mode === 'own_weights', focusedL = document.activeElement?.closest?.('#tray-levels') ? document.activeElement.dataset.l : null;
    $('#tray-levels').innerHTML = [1, 2, 3, 4, 5].map(l => { const tag = this.levelTag(l); return `<button class="seg ${tag === L.tagLocked ? 'is-locked' : ''}" data-l="${l}" aria-pressed="${!own && l === st.level}" aria-label="${esc(`${L.level} ${l}, ${this.levelName(l)}${tag ? ', ' + tag : ''}`)}"><b>${l}</b>${tag && tag !== L.tagComfort ? `<i>${esc(tag === L.tagSuggested ? '•' : tag === L.tagLocked ? '×' : '↑')}</i>` : ''}</button>`; }).join('');
    $('#tray-levels-legend').textContent = L.levelsLegend;
    $('#tray-levels').querySelectorAll('.seg').forEach(b => b.addEventListener('click', () => { const l = Number(b.dataset.l); if (own) this.sheetToModel(l); else this.chooseLevel(l, { from: 'tray' }); }));
    if (focusedL) $(`#tray-levels .seg[data-l="${focusedL}"]`)?.focus();
    $('#tray-bar').innerHTML = this.classBar(p.mix.asset_class);
    $('#tray-classes').innerHTML = Object.entries(p.mix.asset_class).map(([k, v]) => `<li><i style="background:${CLASS_COLOR[k]}"></i><span>${esc(k)}</span><b>${this.pct(v)}</b></li>`).join('');
    $('#tray-nums').innerHTML = `<div><dt>${esc(L.typicalYear)}</dt><dd>${esc(L.between(this.fmtMoney(yr.p10), this.fmtMoney(yr.p90)))}</dd></div><div><dt>${esc(L.badYear)}</dt><dd>${esc(this.fmtMoney(yr.p5))} <small>${esc(`(${this.fmtMoney(yr.p5 - yr.base)})`)}</small></dd></div><div><dt>${esc(L.fees)}</dt><dd>${esc(this.feeText(p))}</dd></div><div><dt>${esc(L.volWindow(String(p.window.start).slice(0, 4), String(p.window.end).slice(0, 4)))}</dt><dd>${this.pct(p.stats.volatility, 1)}</dd></div>${p.projection.monthly_contribution ? `<div class="tray-flow"><dd class="small muted">${esc(L.trayFlow(this.fmtMonthly(p.projection.monthly_contribution)))}</dd></div>` : ''}`;
    $('#tray-funds-h').textContent = L.funds;
    $('#tray-funds').innerHTML = p.holdings.map(h => `<li><button data-t="${esc(h.ticker)}" aria-label="${esc(L.fundRow(h.symbol, this.sleeveLabel(h), this.pct(h.weight)))}"><i style="background:${CLASS_COLOR[h.asset_class]}"></i><b>${esc(h.symbol)}</b><span class="muted">${esc(this.sleeveLabel(h))}</span><span class="w">${this.pct(h.weight)}</span></button></li>`).join('');
    $('#tray-funds').querySelectorAll('button').forEach(b => b.addEventListener('click', () => this.cardFund(b.dataset.t)));
    $('#tray-amount-l').textContent = L.amountLabel(this.ccy); $('#tray-amount').value = String(st.amount);
    $('#tray-amount').onchange = () => { const v = parseAmount($('#tray-amount').value); if (!v || v < 100) { $('#tray-amount').setCustomValidity(L.amountMin); $('#tray-amount').reportValidity(); return; } $('#tray-amount').setCustomValidity(''); st.amount = v; this.rebuild(); };
    $('#tray-monthly-l').textContent = L.monthlyShort; $('#tray-monthly').value = String(st.monthly || 0);
    $('#tray-monthly').onchange = () => { const inp = $('#tray-monthly'), v = parseMonthly(inp.value); if (v == null) { inp.setCustomValidity(L.monthlyBad); inp.reportValidity(); return; } inp.setCustomValidity(''); this.setMonthly(v); };
    $('#tray-open').textContent = L.openMix; $('#tray-open').onclick = () => { this.toggleTray(false); this.showMix(); };
    $('#tray-edit').textContent = L.editFunds; $('#tray-edit').onclick = async () => { this.toggleTray(false); st.ui.shelf = true; await this.showMix(); requestAnimationFrame(() => this.live.mix?.querySelector('.shelf-box select, .shelf-box button')?.focus()); };
    $('#tray-reset').textContent = L.reset; $('#tray-reset').onclick = () => { st.mix = this.emptyMix(); st.userChanged = false; st.ui.shelf = false; st.ui.weights = false; this.rebuild(); };
    $('#tray-computing').textContent = L.computing;
    this.peekLabel();
    $('#tray-toggle').innerHTML = `${this.classBar(p.mix.asset_class, 'thin')}<span><b>${esc(L.level)} ${p.risk.level}${ex ? ' ↑' : ''}</b> · ${esc(L.badYear)} ${esc(this.fmtMoney(yr.p5))} · ${esc(L.fees)} ${esc(this.fmtMoney(p.stats.fee_per_year))}</span>${icon('caret-down', 16)}`;
  }
}

const app = new App();
window.robokit = app;  // handy for debugging in the console
app.boot().catch((e) => { const t = document.getElementById('thread'); if (t) t.innerHTML = `<p class="note">Could not load Robo-Kit data: ${esc(e.message)}</p>`; });
