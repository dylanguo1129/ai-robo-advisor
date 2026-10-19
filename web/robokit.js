/* Robo-Kit v2 engine for the browser: a line-by-line port of robokit/engine.py and friends.
 *
 * Every number the page and the chat show comes from these functions, run on the
 * dated data bundle in web/data/. Checked against the Python engine by
 * web/test_robokit.mjs (resampling off, weights to about 1e-4).
 *
 * Plain ES module. Its one dependency is ./engine.js (shrinkage, capped-simplex projection and the
 * seeded bootstrap, also used by the v1 engine test web/test_engine.mjs), which must be published next to it.
 * Works in the browser, in a Web Worker and in Node.
 */
import { chooseCovariance, projectWeightedCappedSimplex, mulberry32, stationaryBootstrapRows, symEig } from './engine.js';

const EPS = 1e-12;
export const MAX_WINDOW = 180;
export const MIN_WINDOW = 36;
export const DELTA = 2.5;
export const TE_BUDGET = 0.01, MAX_TILT = 0.05, TAU = 0.05;
export const LEVEL_NAMES = { 1: 'Conservative', 2: 'Cautious', 3: 'Balanced', 4: 'Growth', 5: 'Aggressive growth' };

/** An error the person can act on (bad input, limits that cannot hold, a solver that did not finish).
 *  kind: 'input' | 'infeasible' | 'solver'; details mirror robokit/errors.py. */
export class RoboKitError extends Error {
  constructor(message, kind, details = {}) { super(message); this.name = 'RoboKitError'; this.kind = kind; this.details = details; }
}
const inputError = (msg, field) => new RoboKitError(msg, 'input', { field });

/** Round halves away from zero, guarded against binary representation (robokit/engine.py _round_half_up). */
export const roundHalfUp = (x, nd = 0) => { const f = 10 ** nd; const v = Math.floor(Math.abs(x) * f + 0.5 + 1e-9) / f; return v === 0 ? 0 : Math.sign(x) * v; };
/** A share as a percentage, rounded the same way in both engines (robokit/engine.py _pct). */
export const pctTxt = (x, nd = 0) => `${roundHalfUp(x * 100, nd).toFixed(nd)}%`;

/** Two shares as percentages with the fewest decimals (1 to 3) that tell them apart (robokit/engine.py _pct_pair). */
const pctPair = (a, b) => { let x, y; for (const nd of [1, 2, 3]) { x = pctTxt(a, nd); y = pctTxt(b, nd); if (x !== y) break; } return [x, y]; };

/** Each view checked and written in one shape (robokit/engine.py _valid_views). */
function validateViews(views, num, share) {
  if (views == null) return [];
  if (!Array.isArray(views)) throw inputError('views must be a list.', 'views');
  return views.map((v, k0) => {
    const k = k0 + 1;
    if (!v || typeof v !== 'object' || Array.isArray(v)) throw inputError(`View ${k} must be an object.`, 'views');
    const type = v.type ?? 'absolute';
    if (type !== 'absolute' && type !== 'relative') throw inputError(`View ${k}: type must be 'absolute' or 'relative'.`, 'views');
    const c = v.confidence == null ? 0.5 : share(v.confidence, `confidence of view ${k}`);
    if (type === 'relative') {
      if (typeof v.long !== 'string' || typeof v.short !== 'string') throw inputError(`View ${k}: a relative view names a 'long' and a 'short' fund.`, 'views');
      if (v.long === v.short) throw inputError(`View ${k}: the 'long' and the 'short' fund must differ.`, 'views');
      return { type: 'relative', long: v.long, short: v.short, difference: num(v.difference, `difference of view ${k}`), confidence: c };
    }
    if (typeof v.ticker !== 'string') throw inputError(`View ${k}: an absolute view names a 'ticker'.`, 'views');
    return { type: 'absolute', ticker: v.ticker, return: num(v.return, `return of view ${k}`), confidence: c };
  });
}

/** Name of the nearest level: halves round up, always within 1-5 (robokit/engine.py level_label). */
export const levelLabel = (lvl5) => LEVEL_NAMES[Math.min(5, Math.max(1, Math.floor(Number(lvl5) + 0.5 + 1e-9)))];

const AMOUNT_MAX = 1e12;  // as robokit/engine.py: more than any account; larger amounts overflow the arithmetic
/** robokit/engine.py validate_request: nothing is silently clamped; a level of 7 or NaN is an error. */
export function validateRequest(r) {
  const num = (v, name) => {  // numbers and plain decimal text only (as robokit/engine.py _finite): not "0x10" or "1_000"
    const ok = typeof v === 'number' || (typeof v === 'string' && /^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(v.trim()));
    const x = ok ? Number(v) : NaN;
    if (!Number.isFinite(x)) throw inputError(`${name} must be a finite number, not ${String(v)}.`, name);
    return x;
  };
  const share = (v, name, lo = 0, hi = 1, loOpen = false) => { const x = num(v, name); if (x < lo || x > hi || (loOpen && x <= lo)) throw inputError(`${name} must be ${loOpen ? 'above' : 'at least'} ${lo} and at most ${hi}; got ${x}.`, name); return x; };
  if (r.risk_level != null) { r.risk_level = num(r.risk_level, 'risk_level'); if (r.risk_level < 1 || r.risk_level > 5) throw inputError(`risk_level must be between 1 and 5; got ${r.risk_level}.`, 'risk_level'); }
  if (r.targetVol != null) r.targetVol = share(r.targetVol, 'target_vol', 0, 1, true);
  r.amount = num(r.amount, 'amount'); if (r.amount <= 0) throw inputError('amount must be above 0.', 'amount');
  if (r.amount > AMOUNT_MAX) throw inputError('amount must be at most 1,000,000,000,000.', 'amount');
  r.monthly = num(r.monthly ?? 0, 'monthly_contribution');
  if (Math.abs(r.monthly) > AMOUNT_MAX) throw inputError('monthly_contribution must be at most 1,000,000,000,000 either way.', 'monthly_contribution');
  const y = num(r.years, 'years'); if (y !== Math.trunc(y) || y < 1 || y > 100) throw inputError(`years must be a whole number from 1 to 100; got ${r.years}.`, 'years'); r.years = y;
  if (r.goal != null) { r.goal = num(r.goal, 'goal'); if (r.goal <= 0) r.goal = null; else if (r.goal > 100 * AMOUNT_MAX) throw inputError('goal must be at most 100,000,000,000,000.', 'goal'); }  // a goal of 0 means "no goal"
  r.maxWeight = share(r.maxWeight, 'max_weight', 0, 1, true);
  if (r.satelliteCap != null) r.satelliteCap = share(r.satelliteCap, 'satellite_cap');
  r.satelliteMaxEach = share(r.satelliteMaxEach, 'satellite_max_each'); r.cryptoMaxEach = share(r.cryptoMaxEach, 'crypto_max_each');
  r.minWeight = share(r.minWeight, 'min_weight', 0, 0.25);
  const nb = num(r.nBoot, 'n_boot'); if (nb !== Math.trunc(nb) || nb < 0 || nb > 5000) throw inputError(`n_boot must be a whole number from 0 to 5000; got ${r.nBoot}.`, 'n_boot'); r.nBoot = nb;
  const sd = num(r.seed, 'seed'); if (sd !== Math.trunc(sd)) throw inputError('seed must be a whole number.', 'seed'); r.seed = sd;
  for (const k of ['satellites', 'exclude']) { const v = r[k] || []; if (!Array.isArray(v) || !v.every(t => typeof t === 'string')) throw inputError(`${k} must be a list of tickers.`, k); r[k] = v; }
  const isMap = (v) => v != null && typeof v === 'object' && !Array.isArray(v);
  for (const [k, name] of [['minimums', 'minimums'], ['fixedWeights', 'fixed_weights']]) if (r[k] != null && !isMap(r[k])) throw inputError(`${name} must map tickers to shares.`, name);
  const mins = {}; for (const [t, v] of Object.entries(r.minimums || {})) mins[t] = share(v, `minimum for ${t}`);
  const mt = sum(Object.values(mins)); if (mt > 1 + 1e-9) throw inputError(`The minimums add up to ${pctTxt(mt)}, more than 100%.`, 'minimums');
  const clash = Object.keys(mins).filter(t => mins[t] > 0 && r.exclude.includes(t)).sort();
  if (clash.length) throw inputError(`${clash.join(', ')} cannot be both excluded and given a minimum.`, 'minimums');
  r.minimums = Object.fromEntries(Object.entries(mins).filter(([, v]) => v > 0));  // "at least 0%" places no limit
  if (r.fixedWeights) {
    const fw = {}; for (const [t, v] of Object.entries(r.fixedWeights)) { fw[t] = num(v, `weight for ${t}`); if (fw[t] < 0) throw inputError('Your own weights cannot be negative.', 'fixed_weights'); }
    if (Object.keys(fw).length && sum(Object.values(fw)) <= 0) throw inputError('Your own weights must add up to more than 0.', 'fixed_weights');
    if (Object.values(fw).some(v => v > AMOUNT_MAX)) throw inputError('Each of your own weights must be at most 1,000,000,000,000.', 'fixed_weights');
    const fclash = Object.keys(fw).filter(t => fw[t] > 0 && r.exclude.includes(t)).sort();
    if (fclash.length) throw inputError(`${fclash.join(', ')} cannot be both excluded and given a weight.`, 'fixed_weights');
    r.fixedWeights = fw;
  }
  if (r.sleeves != null && (!Array.isArray(r.sleeves) || !r.sleeves.every(s => typeof s === 'string'))) throw inputError('sleeves must be a list of slot names.', 'sleeves');
  if (r.swaps != null && (typeof r.swaps !== 'object' || Array.isArray(r.swaps) || !Object.values(r.swaps).every(v => typeof v === 'string'))) throw inputError('swaps must map a slot to a ticker.', 'swaps');
  r.views = validateViews(r.views, num, share);
  if (!['refuse', 'relax'].includes(r.onInfeasible)) throw inputError("on_infeasible must be 'refuse' or 'relax'.", 'on_infeasible');
  for (const [k, name] of [['preferEsg', 'prefer_esg'], ['hedgeUsEquity', 'hedge_us_equity'], ['resample', 'resample'], ['enforceSuitability', 'enforce_suitability'], ['acknowledgedAboveSuggestion', 'acknowledged_above_suggestion']]) if (typeof r[k] !== 'boolean') throw inputError(`${name} must be true or false.`, name);
  if (r.answers != null && (typeof r.answers !== 'object' || Array.isArray(r.answers))) throw inputError('answers must be an object of question ids and answers.', 'answers');
  return r;
}

// ------------------------------------------------------------------ small helpers
const zeros = (n) => new Float64Array(n);
const sum = (a) => { let s = 0; for (const v of a) s += v; return s; };
function matvec(A, x) { const n = x.length, out = zeros(A.length); for (let i = 0; i < A.length; i++) { let s = 0; const r = A[i]; for (let j = 0; j < n; j++) s += r[j] * x[j]; out[i] = s; } return out; }
const dot = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; };
const quad = (A, w) => dot(w, matvec(A, w));
function mean(a) { let s = 0, n = 0; for (const v of a) if (Number.isFinite(v)) { s += v; n++; } return n ? s / n : NaN; }
function std(a, ddof = 1) { const m = mean(a); let s = 0, n = 0; for (const v of a) if (Number.isFinite(v)) { s += (v - m) ** 2; n++; } return Math.sqrt(s / (n - ddof)); }
function pearson(a, b) { const ma = mean(a), mb = mean(b); let sab = 0, saa = 0, sbb = 0; for (let i = 0; i < a.length; i++) { const da = a[i] - ma, db = b[i] - mb; sab += da * db; saa += da * da; sbb += db * db; } return sab / Math.sqrt(saa * sbb); }
function quantile(sorted, q) { if (!sorted.length) return NaN; const pos = (sorted.length - 1) * q, lo = Math.floor(pos), hi = Math.ceil(pos); return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo); }
function percentile(arr, p) { return quantile(Float64Array.from(arr).sort(), p / 100); }
/** Solve A x = b (Gaussian elimination with partial pivoting). A is n x n array of arrays. */
export function solveLinear(A, b) {
  const n = b.length, M = A.map((r, i) => [...r, b[i]]);
  for (let c = 0; c < n; c++) {
    let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    [M[c], M[p]] = [M[p], M[c]];
    const d = M[c][c]; if (Math.abs(d) < 1e-300) throw new Error('singular system');
    for (let r = 0; r < n; r++) if (r !== c) { const f = M[r][c] / d; if (f) for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k]; }
  }
  return M.map((r, i) => r[n] / r[i]);
}
const round = (v, d = 4) => (v == null || !Number.isFinite(v) ? null : Math.round(v * 10 ** d) / 10 ** d);

// ------------------------------------------------------------------ data
function b64ToInt16(s) {
  const bin = typeof atob === 'function' ? atob(s) : Buffer.from(s, 'base64').toString('binary');
  const buf = new ArrayBuffer(bin.length); const u8 = new Uint8Array(buf);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return new Int16Array(buf);
}

// D2: the locked category lists (robokit/classify.py ASSET_CLASSES, REGIONS, STRATEGIES). A value outside them is flagged,
// never used: the fund is treated as ineligible with the reason, here as in the Python screen.
export const LOCKED = {
  asset_class: ['Equity', 'Fixed income', 'Cash', 'Real estate', 'Commodity', 'Multi-asset', 'Alternative', 'Crypto', 'Single stock'],
  region: ['Canada', 'US', 'North America', 'International developed', 'Emerging markets', 'Global', 'Europe', 'Asia-Pacific', 'Japan', 'China', 'Other single country'],
  strategy: ['Index: market cap', 'Index: factor / smart beta', 'Active', 'Options-based', 'Leveraged / inverse (daily reset)'],
};
export function lockedCategoryProblem(r) {
  for (const [field, allowed] of Object.entries(LOCKED)) { const v = r[field]; if (v != null && !allowed.includes(v)) return `category not in the locked list: ${field} '${v}'`; }
  return '';
}
export class Market {
  /** core = web/data/core.json, m = web/data/ca.json or us.json */
  constructor(core, m) {
    this.core = core; this.code = m.market; this.raw = m;
    this.months = m.returns.months; this.T = this.months.length;
    this.monthIndex = new Map(this.months.map((d, i) => [d, i]));
    const cols = m.universe.columns;
    this.rows = m.universe.rows.map(r => Object.fromEntries(cols.map((c, i) => [c, r[i]])));
    for (const r of this.rows) { const bad = lockedCategoryProblem(r); if (bad) { r.eligible = false; r.excluded_because = r.excluded_because ? `${r.excluded_because}; ${bad}` : bad; r.flagged = bad; } }
    this.byTicker = new Map(this.rows.map(r => [r.yahoo, r]));
    this.series = new Map();
    for (const [t, s] of Object.entries(m.returns.series)) {
      const q = b64ToInt16(s.data), a = new Float64Array(this.T).fill(NaN);
      for (let k = 0; k < q.length; k++) a[s.start + k] = q[k] === m.returns.missing ? NaN : q[k] / m.returns.scale;
      this.series.set(t, a);
    }
    this.sleeves = m.sleeves; this.sleeveByKey = new Map(m.sleeves.map(s => [s.key, s])); this.prior = m.prior;
    // FX monthly returns (CAD per USD) aligned to our months
    const fxMap = new Map(core.fx.months.map((d, i) => [d, core.fx.values[i]]));
    this.fxR = new Float64Array(this.T).fill(NaN);
    for (let i = 0; i < this.T; i++) {
      const cur = fxMap.get(this.months[i]), prev = fxMap.get(prevMonth(this.months[i]));
      if (cur != null && prev != null) this.fxR[i] = cur / prev - 1;
    }
    this.rf = core.risk_free[this.code].rate; this.rfSource = core.risk_free[this.code].source;
  }
  fund(t) { return this.byTicker.get(t); }
  returns(t) { return this.series.get(t); }
  /** trading currency from the fund list (USD units such as XUS-U.TO are USD); suffix as fallback */
  currencyOf(t) {
    const c = this.byTicker.get(t)?.currency;
    return c === 'CAD' || c === 'USD' ? c : (/\.(TO|NE)$/.test(t) ? 'CAD' : 'USD');
  }
  /** returns in this market's currency, converted by each fund's trading currency */
  returnsIn(t) {
    const r = this.series.get(t); if (!r) return null;
    const home = this.code === 'CA' ? 'CAD' : 'USD';
    if (this.currencyOf(t) === home) return r;
    const fx = this.fxR;
    return home === 'CAD'
      ? r.map((v, i) => (Number.isFinite(v) && Number.isFinite(fx[i]) ? (1 + v) * (1 + fx[i]) - 1 : NaN))
      : r.map((v, i) => (Number.isFinite(v) && Number.isFinite(fx[i]) ? (1 + v) / (1 + fx[i]) - 1 : NaN));
  }
  rateReturns(col) {  // monthly return of 3-month bills: last month's annual yield / 12
    const rt = this.core.rates[col]; const ym = new Map(rt.months.map((d, i) => [d, rt.values[i]]));
    return this.months.map(d => { const y = ym.get(prevMonth(d)); return y == null ? NaN : y / 12; });
  }
}
function prevMonth(ym) { let [y, m] = ym.split('-').map(Number); m -= 1; if (m === 0) { m = 12; y -= 1; } return `${y}-${String(m).padStart(2, '0')}`; }

// ------------------------------------------------------------------ shelf and history
/** The shelf with swaps. A swap must pass the eligibility gate and the slot's own rule (`members`, from
 * robokit/shelf.py slot_members); a refused or unknown swap keeps the reference fund and says why in `notes`
 * (as robokit/engine.py select_funds). */
export function shelfFor(M, { preferEsg = false, hedgeUsEquity = false, sleeves = null, swaps = {}, exclude = [], present = null } = {}, notes = []) {
  const def = Object.entries(M.prior).filter(([, v]) => v > 0).map(([k]) => k).concat([`${M.code.toLowerCase()}_cash`]);
  let keys = sleeves || def;
  if (M.code === 'CA' && hedgeUsEquity) keys = keys.map(k => (k === 'ca_us_equity' ? 'ca_us_equity_hedged' : k));
  const inShelf = M.sleeves.filter(s => keys.includes(s.key)).map(s => s.key);
  for (const [k, t] of Object.entries(swaps || {})) if (!inShelf.includes(k)) notes.push({ en: `There is no '${k}' slot in this mix, so the swap to ${t} was ignored.` });
  const out = [], empty = [], chosen = [];  // chosen: each slot's fund before the exclusions
  for (const s of M.sleeves) {  // definition order, as robokit/shelf.py does
    const k = s.key; if (!keys.includes(k)) continue;
    const cands = preferEsg ? s.candidates_esg : s.candidates;
    let t = cands[0] || null;
    const sw = swaps && swaps[k];
    if (sw) {
      const f = M.fund(sw);
      if (!f) notes.push({ en: `${sw} is not in the fund list, so the slot keeps ${t}.` });
      else if (!f.eligible) notes.push({ en: `${sw} was not swapped in (${f.excluded_because}), so the slot keeps ${t}.` });
      else if (!((preferEsg ? s.members_esg : s.members) || []).includes(sw)) {  // a bundle without the lists refuses
        notes.push({ en: `${sw} is not one of the funds the ${s.label} slot admits, so the slot keeps ${t}. Add it as an own pick instead.` });
      }
      else if (!M.series.has(sw)) notes.push({ en: `${sw} has no price history in this snapshot, so the slot keeps ${t}.` });
      else t = sw;
    }
    if (!t) { empty.push({ en: `No eligible fund fits the ${s.label} slot, so its share is spread over the other funds.` }); continue; }  // after the swap notes, as robokit/engine.py
    chosen.push(t);
    if (exclude.includes(t)) continue;
    out.push({ sleeve: k, label: s.label, plain: s.plain, asset_class: s.asset_class, role: s.role, prior: s.prior, ticker: t, cap: s.cap, alternatives: cands.filter(c => c !== t).slice(0, 4), reference: cands[0] });
  }
  notes.push(...empty);
  if (present) {  // an exclusion that matches no fund in the mix is said, as in robokit/engine.py select_funds
    const inMix = new Set([...chosen, ...present]);
    for (const t of [...new Set(exclude)]) if (!inMix.has(t)) notes.push({ en: `${t} is not in this mix, so excluding it changes nothing.` });
  }
  return out;
}

function splice(M, series, proxies, isCash) {
  const s = Float64Array.from(series); const notes = [];
  for (const { ticker, convert } of proxies) {
    let first = -1; for (let i = 0; i < M.T; i++) if (Number.isFinite(s[i])) { first = i; break; }
    if (first < 0) break;
    let p;
    const isRate = ticker.startsWith('RATE:');
    if (isRate) p = M.rateReturns(ticker.slice(5));
    else if (M.series.has(ticker)) {
      p = M.series.get(ticker);
      if (convert) p = p.map((v, i) => (Number.isFinite(v) && Number.isFinite(M.fxR[i]) ? (1 + v) * (1 + M.fxR[i]) - 1 : NaN));
    } else continue;
    const before = []; for (let i = 0; i < first; i++) if (Number.isFinite(p[i])) before.push(i);
    if (!before.length) continue;
    const oa = [], ob = []; for (let i = first; i < M.T; i++) if (Number.isFinite(s[i]) && Number.isFinite(p[i])) { oa.push(s[i]); ob.push(p[i]); }
    let corr = oa.length > 2 ? pearson(oa, ob) : NaN;
    if (!isCash && !isRate) {
      if (oa.length < 24) continue;
      if (!(corr >= 0.8)) { notes.push({ proxy: ticker, used: false, why: `correlation ${corr.toFixed(2)} below 0.8` }); continue; }
    }
    for (const i of before) s[i] = p[i];
    notes.push({ proxy: ticker.replace('RATE:', 'rate '), used: true, from: M.months[before[0]], to: M.months[before[before.length - 1]], months: before.length, converted_to_cad: !!convert, overlap_corr: Number.isFinite(corr) ? round(corr, 3) : null });
  }
  return { s, notes };
}

function backfill(M, target, coreCols, coreRows, seed = 11) {
  // coreRows: month indices of the core window (all core present), coreCols: arrays aligned to months
  let first = -1; for (let i = 0; i < M.T; i++) if (Number.isFinite(target[i])) { first = i; break; }
  const missing = coreRows.filter(i => i < first);
  if (!missing.length) return { s: target, info: null };
  const ov = coreRows.filter(i => i >= first && Number.isFinite(target[i]));
  if (ov.length < 36) return { s: target, info: null };
  const k = coreCols.length + 1;
  const X = ov.map(i => [1, ...coreCols.map(c => c[i])]); const y = ov.map(i => target[i]);
  const XtX = Array.from({ length: k }, (_, a) => Array.from({ length: k }, (_, b) => X.reduce((s, r) => s + r[a] * r[b], 0)));
  const Xty = Array.from({ length: k }, (_, a) => X.reduce((s, r, j) => s + r[a] * y[j], 0));
  let tr = 0; for (let a = 0; a < k; a++) tr += XtX[a][a];
  const lam = 1e-4 * tr / k; for (let a = 0; a < k; a++) XtX[a][a] += lam;
  const beta = solveLinear(XtX, Xty);
  const resid = y.map((v, j) => v - dot(X[j], beta)); const n = resid.length;
  const out = Float64Array.from(target);
  const m = missing.length;  // residual draws count back from the fund's first month (as robokit/history.py)
  missing.forEach((i, j) => { out[i] = dot([1, ...coreCols.map(c => c[i])], beta) + resid[((m - 1 - j) * 7919 + seed) % n]; });
  const vy = std(y, 0) ** 2, vr = std(resid, 0) ** 2;
  return { s: out, info: { method: 'regression on core funds + residual from its own history', months: missing.length, from: M.months[missing[0]], to: M.months[missing[missing.length - 1]], r2: round(vy > 0 ? 1 - vr / vy : 0, 3) } };
}

function backfillRegressors(M, cols, gapMonths = 36) {
  const start = new Map(cols.map(([t, s]) => { let f = -1; for (let i = 0; i < M.T; i++) if (Number.isFinite(s[i])) { f = i; break; } return [t, f]; }));
  const keep = cols.map(([t]) => t).filter(t => start.get(t) >= 0);
  while (keep.length > 2) {
    const order = [...keep].sort((a, b) => start.get(a) - start.get(b));
    const last = order[order.length - 1], prev = order[order.length - 2];
    if (start.get(last) - start.get(prev) <= gapMonths) break;  // month indices: the gap in months
    keep.splice(keep.indexOf(last), 1);
  }
  return keep;
}

/** Returns window for the chosen funds: { tickers, rows (month indices), X (T x N), full (Map ticker -> spliced series), notes } */
export function buildReturns(M, shelf, sats) {
  const tickers = [...new Set([...shelf.map(s => s.ticker), ...sats])];  // a fund that fills two slots is one fund (as Python)
  const full = new Map(); const notes = {};
  for (const t of tickers) full.set(t, M.returnsIn(t) || new Float64Array(M.T).fill(NaN));
  for (const row of shelf) {
    const sl = M.sleeveByKey.get(row.sleeve);
    const proxies = M.fund(row.ticker)?.hedged ? (sl.proxies_hedged || sl.proxies) : sl.proxies;  // matched to the fund's hedging
    const { s, notes: n } = splice(M, full.get(row.ticker), proxies, row.role === 'cash');
    full.set(row.ticker, s);
    const used = n.filter(x => x.used); if (used.length) notes[row.ticker] = used;
  }
  // satellites are back-filled as far back as the core funds go, leaving out a core fund that starts years after the rest
  // (robokit/history.py backfill_regressors): one short series must not cut every satellite's history short of 2008
  const core = backfillRegressors(M, shelf.map(s => s.ticker).map(t => [t, full.get(t)]));
  const coreRows = []; for (let i = 0; i < M.T; i++) if (core.every(t => Number.isFinite(full.get(t)[i]))) coreRows.push(i);
  for (const t of sats) {
    const { s, info } = backfill(M, full.get(t), core.map(c => full.get(c)), coreRows);
    full.set(t, s); if (info) notes[t] = [info];
  }
  let rows = []; for (let i = 0; i < M.T; i++) if (tickers.every(t => Number.isFinite(full.get(t)[i]))) rows.push(i);
  rows = rows.slice(-MAX_WINDOW);
  const X = rows.map(i => tickers.map(t => full.get(t)[i]));
  return { tickers, rows, X, full, notes };
}

// ------------------------------------------------------------------ estimation and solver
function fit(X, prior, delta = DELTA, method = 'auto') {
  const { sigma: sm, shrink, method: used } = chooseCovariance(X, method);
  const sigma = sm.map(r => Array.from(r, v => v * 12));
  const mu = Array.from(matvec(sigma, prior), v => delta * v);
  return { sigma, mu, shrink, method: used };
}

// zero the weights below cut that no minimum holds and rescale the rest to 100%, without pushing a fund past its cap or
// the group past its limit; when the rescaling would, project back onto the limits with the dropped funds at zero
// (optimizer/portfolio.py tidy_weights)
function within(w, lb, ub, mask, gcap, tol = 1e-12) {
  let g = 0; for (let i = 0; i < w.length; i++) { if (w[i] < lb[i] - tol || w[i] > ub[i] + tol) return false; if (mask && mask[i]) g += w[i]; }
  return !mask || g <= gcap + tol;
}
function tidy(w, lb, ub, mask, gcap, cut) {
  const drop = Array.from(w, (v, i) => Math.abs(v) < cut && lb[i] <= 0);
  let x = Array.from(w, (v, i) => (drop[i] ? 0 : v)); const s = sum(x); x = x.map(v => v / s);
  if (within(x, lb, ub, mask, gcap)) return x;
  const capS = Array.from(ub, (u, i) => (drop[i] ? 0 : u) - lb[i]); const mass = 1 - sum(lb);
  let lbG = 0; if (mask) for (let i = 0; i < lb.length; i++) if (mask[i]) lbG += lb[i];
  try {
    const u = projectGroup(x.map((v, i) => v - lb[i]), x.map(() => 1), capS, mass, mask, gcap - lbG);
    const y = Array.from(u, (v, i) => v + lb[i]);
    if (within(y, lb, ub, mask, gcap, 1e-9)) return y;
  } catch (e) { if (!(e instanceof RoboKitError)) throw e; }
  return Array.from(w);
}

function projectGroup(x, a, cap, total, mask, gcap) {
  const v = projectWeightedCappedSimplex(x, a, cap, total);
  if (!mask) return v;
  let g = 0; for (let i = 0; i < v.length; i++) if (mask[i]) g += a[i] * v[i];
  if (g <= gcap + 1e-12) return v;
  const idxG = [], idxR = []; for (let i = 0; i < v.length; i++) (mask[i] ? idxG : idxR).push(i);
  let roomR = 0; for (const i of idxR) roomR += a[i] * cap[i];
  if (gcap < total - roomR - 1e-9)  // the rest cannot absorb what the group may not hold: fail closed (optimizer/solver.py)
    throw new RoboKitError('The limit on the group cannot hold together with the other limits.', 'infeasible', { kind: 'group_cap', group_cap: gcap, room_rest: roomR, needed: total });
  const gg = gcap;
  const out = zeros(v.length);
  if (gg > 1e-15) { const p = projectWeightedCappedSimplex(idxG.map(i => x[i]), idxG.map(i => a[i]), idxG.map(i => cap[i]), gg); idxG.forEach((i, k) => { out[i] = p[k]; }); }
  if (idxR.length && total - gg > 1e-15) { const p = projectWeightedCappedSimplex(idxR.map(i => x[i]), idxR.map(i => a[i]), idxR.map(i => cap[i]), total - gg); idxR.forEach((i, k) => { out[i] = p[k]; }); }
  return out;
}

// lam = 0 limit: fill the highest-mu funds up to their caps, and the group's members only up to its room (optimizer/solver.py)
function greedy(mu, lb, ub, mask = null, groom = Infinity) {
  const w = Float64Array.from(lb); let room = 1 - sum(w); const order = [...mu.keys()].sort((i, j) => mu[j] - mu[i]);
  for (const i of order) { const inG = !!(mask && mask[i]); const t = Math.max(Math.min(ub[i] - w[i], room, inG ? groom : Infinity), 0); w[i] += t; room -= t; if (inG) groom -= t; if (room <= EPS) break; }
  if (room > 1e-9) { let rest = 0; for (let i = 0; i < w.length; i++) if (mask && !mask[i]) rest += ub[i] - lb[i]; throw new RoboKitError('The group limit and the room in the other funds cannot hold 100% of the money.', 'infeasible', { kind: 'group_cap', room_rest: rest, needed: 1 - sum(lb) }); }
  return w;
}

/** minimize (lam/2) w'Sw - mu'w  s.t. sum w = 1, lb <= w <= ub, sum(w[mask]) <= gcap */
export function solveQPG(sigma, mu, lam, lb, ub, mask = null, gcap = 1, maxIter = 10000, tol = 1e-10) {
  const n = mu.length;
  if (!Number.isFinite(lam) || !mu.every(Number.isFinite) || !sigma.every(row => row.every(Number.isFinite))) throw new RoboKitError('Sigma, mu and lam must be finite.', 'solver', {});
  const lbSum = sum(lb); if (lbSum > 1 + 1e-9) throw new RoboKitError(`The minimums add up to ${pctTxt(lbSum)}, more than 100%.`, 'infeasible', { kind: 'minimums', minimums_total: lbSum });
  if (sum(ub) < 1 - 1e-9) throw new RoboKitError('The limits on these funds cannot hold 100% of the money.', 'infeasible', { kind: 'caps', capacity: sum(ub), needed: 1 });
  let ghi = 1;
  if (mask) {
    let lbG = 0; for (let i = 0; i < n; i++) if (mask[i]) lbG += lb[i];
    if (gcap - lbG < -1e-9) throw new RoboKitError('The minimums inside the group add up to more than its limit.', 'infeasible', { kind: 'group_minimums', group_cap: gcap, group_minimums: lbG });
    ghi = Math.max(gcap - lbG, 0);
  }
  if (lam <= EPS) return greedy(mu, lb, ub, mask, mask ? ghi : Infinity);
  const mass = 1 - lbSum; const cap = Array.from(ub, (u, i) => u - lb[i]);
  if (mass <= EPS) return Float64Array.from(lb);
  const d = sigma.map((r, i) => Math.sqrt(Math.max(r[i], 1e-16))); const a = d.map(v => 1 / v);
  const corr = sigma.map((r, i) => r.map((v, j) => v / (d[i] * d[j])));
  const capv = cap.map((c, i) => c * d[i]);
  const sLb = matvec(sigma, lb); const gLin = mu.map((m, i) => (lam * sLb[i] - m) / d[i]);
  const proj = (z) => projectGroup(z, a, capv, mass, mask, ghi);
  const step = 1 / Math.max(lam * symEig(corr).values[n - 1], EPS);  // 1/L with L = lam x the largest eigenvalue, exactly as optimizer/solver.py
  let v = proj(d.map(di => (mass / n) * di)); let y = Float64Array.from(v), tk = 1, converged = false, it = 0;
  for (it = 1; it <= maxIter; it++) {
    const cy = matvec(corr, y);
    const vNext = proj(y.map((yi, i) => yi - step * (lam * cy[i] + gLin[i])));
    const dv = vNext.map((vi, i) => vi - v[i]);
    let restart = 0; for (let i = 0; i < n; i++) restart += (y[i] - vNext[i]) * dv[i];
    if (restart > 0) { tk = 1; y = Float64Array.from(vNext); }
    else { const tn = 0.5 * (1 + Math.sqrt(1 + 4 * tk * tk)); y = vNext.map((vi, i) => vi + ((tk - 1) / tn) * dv[i]); tk = tn; }
    let md = 0; for (let i = 0; i < n; i++) md = Math.max(md, Math.abs(dv[i] / d[i]));
    v = vNext; if (md < tol) { converged = true; break; }
  }
  if (!converged) {  // certificate: the projected-gradient step from the answer, in weight units (optimizer/solver.py)
    const cv = matvec(corr, v); const pv = proj(v.map((vi, i) => vi - step * (lam * cv[i] + gLin[i])));
    let resid = 0; for (let i = 0; i < n; i++) resid = Math.max(resid, Math.abs((v[i] - pv[i]) / d[i]));
    if (!(resid <= 1e-6)) throw new RoboKitError('The optimizer did not reach an answer, so nothing was built.', 'solver', { iterations: maxIter, residual: resid });
  }
  const w = v.map((vi, i) => Math.min(ub[i], Math.max(lb[i], vi / d[i] + lb[i])));
  const s = sum(w); return w.map((x, i) => Math.min(ub[i], Math.max(lb[i], x / s)));  // the sum is 1 to rounding; the clip keeps every bound
}

function sub(A, idx) { return idx.map(i => idx.map(j => A[i][j])); }

/** Raise caps that cannot reach 100%, one group at a time (optimizer/portfolio.py relax_caps).
 *  order: arrays of positions into ub; inside a group every cap is multiplied by the same factor, capped at 100%. */
function relaxCaps(ub, order, names) {
  ub = Array.from(ub); const seen = new Set(), groups = [], steps = [];
  for (const g of [...(order || []), ub.map((_, k) => k)]) { const m = g.filter(k => !seen.has(k) && ub[k] > 0); m.forEach(k => seen.add(k)); if (m.length) groups.push(m); }
  for (const m of groups) {
    const need = 1 - sum(ub); if (need <= 1e-12) break;
    const before = m.map(k => ub[k]); const room = sum(before.map(u => 1 - u)); if (room <= 1e-12) continue;
    if (room <= need + 1e-12) m.forEach(k => { ub[k] = 1; });
    else {
      let lo = 1, hi = 1 / Math.min(...before.filter(u => u > 0)); const base = sum(before);
      for (let it = 0; it < 200; it++) { const f = 0.5 * (lo + hi); if (sum(before.map(u => Math.min(1, f * u))) - base < need) lo = f; else hi = f; }
      m.forEach((k, j) => { ub[k] = Math.min(1, hi * before[j]); });
    }
    m.forEach((k, j) => { if (ub[k] > before[j] + 1e-12) steps.push({ limit: 'cap', ticker: names[k], requested: before[j], applied: ub[k] }); });
  }
  return { ub, steps };
}

/** One optimization on a subset of the fitted funds (mirrors RoboKitOptimizer.optimize).
 *  Limits that cannot all hold throw a RoboKitError (onInfeasible 'refuse'), or are relaxed in relaxOrder and listed. */
function optimizeOn(est, lam, idx, bounds, satMask, satCap, { resample = false, nBoot = 0, seed = 0, X = null, prior = null, blViews = null, onInfeasible = 'refuse', relaxOrder = null, names = null } = {}) {
  const S = sub(est.sigma, idx), mu = idx.map(i => est.mu[i]);
  const lb = idx.map(i => bounds.lb[i]); let ub = idx.map(i => bounds.ub[i]);
  const relaxations = []; const nm = idx.map(i => (names ? names[i] : String(i)));
  for (let k = 0; k < ub.length; k++) {  // a client minimum above a fund's limit is a conflict, not a silent override
    if (lb[k] > ub[k] + 1e-12) {
      const details = { kind: 'minimum_above_cap', ticker: nm[k], minimum: lb[k], cap: ub[k] };
      if (onInfeasible !== 'relax') throw new RoboKitError(`The minimum of ${pctTxt(lb[k], 1)} for ${nm[k]} is above its limit of ${pctTxt(ub[k], 1)}.`, 'infeasible', details);
      relaxations.push({ limit: 'cap', ticker: nm[k], requested: ub[k], applied: lb[k], reason: 'minimum' }); ub[k] = lb[k];
    }
  }
  const ubSum = sum(ub);
  if (ubSum < 1 - 1e-9) {
    const details = { kind: 'caps', capacity: ubSum, needed: 1, caps: Object.fromEntries(nm.map((t, k) => [t, ub[k]])) };
    if (onInfeasible !== 'relax') throw new RoboKitError(`The limits on these funds add up to ${Math.round(ubSum * 100)}%, so they cannot hold 100% of the money.`, 'infeasible', details);
    const pos = new Map(idx.map((i, k) => [i, k]));
    const order = (relaxOrder || []).map(g => g.filter(i => pos.has(i)).map(i => pos.get(i)));
    const rc = relaxCaps(ub, order, nm); ub = rc.ub; relaxations.push(...rc.steps);
    if (sum(ub) < 1 - 1e-9) throw new RoboKitError(`Even with every limit relaxed these funds hold only ${Math.round(sum(ub) * 100)}%.`, 'infeasible', details);
  }
  const mask = satMask ? idx.map(i => satMask[i]) : null;
  const hasMask = mask && mask.some(Boolean);
  let gcap = satCap;
  if (hasMask) {  // the group must hold its minimums and whatever the other funds cannot (optimizer/portfolio.py _group_bounds)
    let room = 0, lbG = 0; for (let k = 0; k < ub.length; k++) { if (mask[k]) lbG += lb[k]; else room += ub[k]; }
    const needed = Math.max(lbG, 1 - room);
    if (gcap < needed - 1e-9) {
      const details = { kind: 'group_cap', group: 'satellites', cap: gcap, needed, group_minimums: lbG };
      if (onInfeasible !== 'relax') throw new RoboKitError(`The limit of ${Math.round(gcap * 100)}% on 'satellites' cannot hold: the group needs at least ${Math.round(needed * 100)}%.`, 'infeasible', details);
      relaxations.push({ limit: 'group', group: 'satellites', requested: gcap, applied: needed }); gcap = needed;
    }
  }
  const clean = (w) => tidy(w, lb, ub, hasMask ? mask : null, gcap, 1e-6);
  const wPoint = clean(solveQPG(S, mu, lam, lb, ub, hasMask ? mask : null, gcap));
  if (!resample || nBoot <= 0) return { w: wPoint, band: null, sigma: S, mu, relaxations, ub };
  const rng = mulberry32(seed + 1); const T = X.length; const draws = [];
  for (let b = 0; b < nBoot; b++) {
    const rows = stationaryBootstrapRows(rng, T, 6); const Xb = Array.from(rows, r => X[r]);
    let e = fit(Xb, prior, DELTA, est.method);
    if (blViews) e = blPosterior(e, blViews);
    draws.push(clean(solveQPG(sub(e.sigma, idx), idx.map(i => e.mu[i]), lam, lb, ub, hasMask ? mask : null, gcap)));
  }
  let w = idx.map((_, k) => mean(draws.map(d => d[k])));
  w = tidy(w, lb, ub, hasMask ? mask : null, gcap, 1e-4);
  const band = idx.map((_, k) => { const col = draws.map(d => d[k]).sort((a, b) => a - b); return [quantile(col, 0.05), quantile(col, 0.95)]; });
  return { w, band, sigma: S, mu, wPoint, relaxations, ub };
}

// the regulator's risk rating (robokit/engine.py ni81_102_rating): NI 81-102 Appendix F, the standard deviation of the
// last 120 monthly returns (n - 1), times the square root of 12, in five bands
const APPENDIX_F = [[0.06, 'Low'], [0.11, 'Low to medium'], [0.16, 'Medium'], [0.20, 'Medium to high'], [Infinity, 'High']];
export function ni81102Rating(monthly) {
  const r = Array.from(monthly).slice(-120); const sd = std(r) * Math.sqrt(12);
  return { std_10y: round(sd), rating: APPENDIX_F.find(([cut]) => sd < cut)[1], months: r.length, appendix_f: r.length >= 120,
    method: 'NI 81-102 Appendix F: standard deviation of the last 120 monthly returns (n - 1), times the square root of 12' };
}
function ratingCheck(rating) {
  const short = rating.months >= 120 ? '' : ` It uses the ${rating.months} months available, not the full 10 years.`;
  return { id: 'regulator_rating', level: 'info', en: `On the scale funds use for their published risk rating (NI 81-102 Appendix F, 10-year standard deviation), this mix would rate ${rating.rating} (${pctTxt(rating.std_10y, 1)}).${short}` };
}

const LAM_LO = 0.05, LAM_HI = 2000, CAL_TOL = 5e-5, CAL_MAX = 30, CAL_WIDTH = 1e-5;  // as robokit/engine.py

/** Risk aversion for the mix the person gets (robokit/engine.py _calibrate_final, same algorithm): bracket the target
 *  from the single-solve lambda, then Illinois regula falsi (Dowell and Jarratt 1971) on log(vol / target) over
 *  log(lambda), safeguarded by bisection; the same bootstrap draws at every step; the closest mix seen kept. */
function calibrateFinal(final, target, first, resampled = true) {
  const lu = Math.log(LAM_LO), hu = Math.log(LAM_HI);
  let best = first, evals = 1;
  const fOf = (fx) => Math.log(Math.max(fx.vol, 1e-12) / target);
  let u = Math.log(first.lam), f = fOf(first);
  let a = null, fa = null, b = null, fb = null;  // bracket: a has vol above target (f > 0), b below (f < 0), a < b
  let va = null, vb = null, lastVol = first.vol;  // the volatility at each end, and at the last lambda evaluated
  if (f > 0) { a = u; fa = f; va = first.vol; } else if (f < 0) { b = u; fb = f; vb = first.vol; }
  let step = Math.max(Math.abs(f), 0.05), side = 0, outcome = 'limit'; const widths = [];
  for (;;) {
    if (Math.abs(best.vol - target) <= CAL_TOL) { outcome = 'within tolerance'; break; }
    if (a != null && b != null && b - a < CAL_WIDTH) { outcome = 'jump'; break; }  // a proven jump, whichever evaluation closed it
    if (evals >= CAL_MAX) break;
    if (a == null || b == null) {  // 1. bracket
      const nxt = Math.min(hu, Math.max(lu, u + (f > 0 ? step : -step)));
      if (nxt === u) { outcome = 'out of reach'; break; }
      u = nxt; step *= 2;
    } else {  // 2. narrow: Illinois regula falsi, midpoint when too close to an end or the bracket did not halve
      const width = b - a;
      if (width < CAL_WIDTH) { outcome = 'jump'; break; }
      u = b - fb * (b - a) / (fb - fa);
      if (!(a + 0.01 * width < u && u < b - 0.01 * width) || (widths.length >= 4 && width > 0.5 * widths[widths.length - 4])) u = 0.5 * (a + b);
      widths.push(width);
    }
    const cur = final(Math.exp(u)); evals++; f = fOf(cur); lastVol = cur.vol;
    if (Math.abs(cur.vol - target) < Math.abs(best.vol - target)) best = cur;
    if (a == null || b == null) {
      if (f > 0 && (a == null || u > a)) { a = u; fa = f; va = cur.vol; } else if (f < 0 && (b == null || u < b)) { b = u; fb = f; vb = cur.vol; }
    } else if (f > 0) { if (side === 1) fb *= 0.5; a = u; fa = f; va = cur.vol; side = 1; }  // Illinois: an end kept twice has its value halved
    else if (f < 0) { if (side === -1) fa *= 0.5; b = u; fb = f; vb = cur.vol; side = -1; }
  }
  // the evidence for a stop short of the target: the bound and the volatility there, or the last bracket
  let evidence = null;
  if (outcome === 'out of reach') evidence = { bound_lambda: Math.exp(u), vol_at_bound: lastVol, side: lastVol > target ? 'above' : 'below' };
  else if (a != null && b != null) evidence = { lambda_above: Math.exp(a), vol_above: va, lambda_below: Math.exp(b), vol_below: vb, log_width: b - a };
  return { best, info: { method: `final pipeline (${resampled ? 'resampled' : 'single solve'}, minimum position applied): bracket, then Illinois regula falsi on log lambda`, lambda_single_solve: round(first.lam),
    evaluations: evals, outcome, target_vol: round(target, 6), achieved_vol: round(best.vol, 6), within_tolerance: Math.abs(best.vol - target) <= CAL_TOL, evidence } };
}

/** Say so when the mix cannot be brought to the level's target (checked on the final mix). */
function reachNote(target, vol, outcome) {
  const p1 = (x) => pctTxt(x, 1);
  if (outcome === 'out of reach' && vol < target - 0.005) return { en: `The funds on this list cannot reach the ${p1(target)} volatility this level aims for; the riskiest mix they allow is ${p1(vol)}.` };
  if (outcome === 'out of reach' && vol > target + 0.005) return { en: `Even the steadiest mix of these funds swings about ${p1(vol)} a year, above the ${p1(target)} this level aims for. Adding cash or short-term bonds would bring it down.` };
  if (Math.abs(vol - target) > 0.005) return { en: `This mix swings about ${p1(vol)} a year against the ${p1(target)} this level aims for: with the minimum position size, the risk moves in steps as funds enter or leave the mix.` };
  return null;
}

function calibrate(volOf, target) {
  let lo = LAM_LO, hi = LAM_HI;
  const vLo = volOf(lo), vHi = volOf(hi);
  const p1 = (x) => pctTxt(x, 1);
  if (target >= vLo) return { lam: lo, vol: vLo, note: target > vLo + 0.005 ? { en: `The funds on this list cannot reach the ${p1(target)} volatility this level aims for; the riskiest mix they allow is ${p1(vLo)}.` } : null };
  if (target <= vHi) return { lam: hi, vol: vHi, note: target < vHi - 0.005 ? { en: `Even the steadiest mix of these funds swings about ${p1(vHi)} a year, above the ${p1(target)} this level aims for. Adding cash or short-term bonds would bring it down.` } : null };
  for (let k = 0; k < 40; k++) { const mid = Math.sqrt(lo * hi); if (volOf(mid) > target) lo = mid; else hi = mid; if (hi / lo < 1.002) break; }
  const lam = Math.sqrt(lo * hi); return { lam, vol: volOf(lam), note: null };
}

// ------------------------------------------------------------------ Black-Litterman views
function invert(A) { const n = A.length; return Array.from({ length: n }, (_, j) => solveLinear(A, Array.from({ length: n }, (_, i) => (i === j ? 1 : 0)))).map((col, j, cols) => cols.map(c => c[j])); }
function blPosterior(est, { P, Q, omega }) {
  const n = est.mu.length, K = Q.length, tS = est.sigma.map(r => r.map(v => TAU * v));
  const PtS = P.map(p => Array.from(matvec(tS, p)));                   // K x n  (P tau S)
  const mid = Array.from({ length: K }, (_, a) => Array.from({ length: K }, (_, b) => dot(PtS[a], P[b]) + (a === b ? omega[a] : 0)));
  const inv = invert(mid);
  const resid = Q.map((q, k) => q - dot(P[k], est.mu));
  const coef = Array.from(matvec(inv, resid));
  const mu = est.mu.map((m, i) => m + PtS.reduce((s, row, k) => s + row[i] * coef[k], 0));
  // posterior covariance: S + tS - tS P' inv P tS
  const sigma = est.sigma.map((r, i) => r.map((v, j) => {
    let corr = 0; for (let a = 0; a < K; a++) for (let b = 0; b < K; b++) corr += PtS[a][i] * inv[a][b] * PtS[b][j];
    return v + tS[i][j] - corr;
  }));
  return { ...est, mu, sigma };
}

function viewsToBL(views, tickers, est, rf) {
  const idx = new Map(tickers.map((t, i) => [t, i])); const P = [], Q = [], omega = [], info = [];
  for (const v of views) {
    const c = Number(v.confidence ?? 0.5);
    if (!(c >= 0 && c <= 1)) { info.push({ view: v, used: false, why: 'confidence must be between 0 and 1' }); continue; }
    if (c === 0) { info.push({ view: v, used: false, why: '0% confidence: the view has no effect' }); continue; }
    const p = new Array(tickers.length).fill(0);
    if (v.type === 'relative') {
      if (!idx.has(v.long) || !idx.has(v.short)) { info.push({ view: v, used: false, why: 'both funds must be in the portfolio' }); continue; }
      p[idx.get(v.long)] = 1; p[idx.get(v.short)] = -1; Q.push(Number(v.difference));
    } else {
      if (!idx.has(v.ticker)) { info.push({ view: v, used: false, why: 'fund not in the portfolio' }); continue; }
      p[idx.get(v.ticker)] = 1; Q.push(Number(v.return) - rf);
    }
    const alpha = c < 1 ? (1 - c) / c : 1e-9;
    omega.push(Math.max(TAU * alpha * quad(est.sigma, p), 1e-12)); P.push(p); info.push({ view: v, used: true });
  }
  return P.length ? { P, Q, omega, info } : { P: null, info };
}

function boundTilt(w0, w1, sigma) {
  const d = w1.map((v, i) => v - w0[i]); const te = Math.sqrt(Math.max(quad(sigma, d), 0)); const big = Math.max(...d.map(Math.abs));
  let s = 1; if (te > TE_BUDGET) s = Math.min(s, TE_BUDGET / te); if (big > MAX_TILT) s = Math.min(s, MAX_TILT / big);
  let w = w0.map((v, i) => Math.max(0, v + s * d[i])); const t = sum(w); w = w.map(v => v / t);
  return { w, tilt: { tracking_error_before: round(te), largest_move_before: round(big), scale: round(s), tracking_error_after: round(te * s), budget: { tracking_error: TE_BUDGET, per_fund: MAX_TILT } } };
}

/** Give mass back to the held funds in proportion to their weights, never past room; null if it cannot (robokit/views.py _refill). */
function refill(w, room, mass) {
  w = w.slice();
  for (let it = 0; it < 100; it++) {
    if (mass <= 1e-12) return w;
    const live = w.map((v, i) => v > 0 && room[i] - v > 1e-12);
    if (!live.some(Boolean)) return null;
    let tw = 0; for (let i = 0; i < w.length; i++) if (live[i]) tw += w[i];
    let added = 0;
    for (let i = 0; i < w.length; i++) if (live[i]) { const a = Math.min(mass * w[i] / tw, room[i] - w[i]); w[i] += a; added += a; }
    mass -= added;
  }
  return mass <= 1e-9 ? w : null;
}

/** boundTilt with the portfolio rules applied to the result (robokit/views.py bound_tilt_clean): positions under minWeight are
 *  removed (never the protected ones: forced funds and positions the no-view mix holds below the minimum on purpose) and their
 *  weight goes back to the held funds in proportion, never past ub. The scale is the largest one in [0, s_max] whose result keeps
 *  the tracking error and largest move in budget, every weight within ub and the group within its cap; if none works, w0 itself. */
function boundTiltClean(w0, w1, sigma, { minWeight = 0, protect = new Set(), ub = null, groupMask = null, groupCap = 1, names = [] } = {}) {
  const d = w1.map((v, i) => v - w0[i]); const te = Math.sqrt(Math.max(quad(sigma, d), 0)); const big = Math.max(...d.map(Math.abs));
  let sMax = 1; if (te > TE_BUDGET) sMax = Math.min(sMax, TE_BUDGET / te); if (big > MAX_TILT) sMax = Math.min(sMax, MAX_TILT / big);
  const room = ub ? Array.from(ub) : w0.map(() => 1);
  const clean = (s) => {
    const w = w0.map((v, i) => Math.max(0, v + s * d[i]));
    const small = minWeight > 0 ? w.map((v, i) => (v > 0 && v < minWeight - 1e-9 && !protect.has(names[i]) ? i : -1)).filter(i => i >= 0) : [];
    if (!small.length) { const t = sum(w); return { w: w.map(v => v / t), small: [] }; }
    let mass = 0; for (const i of small) { mass += w[i]; w[i] = 0; }
    if (!w.some(v => v > 0)) return { w: null, small: [] };
    return { w: refill(w, room, mass), small: small.map(i => names[i]) };
  };
  const ok = (w) => {
    if (!w || !w.every(Number.isFinite) || Math.abs(sum(w) - 1) > 1e-9) return false;
    const dd = w.map((v, i) => v - w0[i]);
    if (Math.sqrt(Math.max(quad(sigma, dd), 0)) > TE_BUDGET + 1e-9 || Math.max(...dd.map(Math.abs)) > MAX_TILT + 1e-9) return false;
    if (w.some((v, i) => v > room[i] + 1e-9)) return false;
    if (groupMask) { let g = 0; for (let i = 0; i < w.length; i++) if (groupMask[i]) g += w[i]; if (g > groupCap + 1e-9) return false; }
    return true;
  };
  let s = sMax, c = clean(sMax);
  if (!ok(c.w)) {
    let lo = 0, hi = sMax; for (let k = 0; k < 50; k++) { const mid = 0.5 * (lo + hi); if (ok(clean(mid).w)) lo = mid; else hi = mid; }
    s = lo; c = clean(lo);
    if (lo === 0 || !ok(c.w)) { s = 0; c = { w: w0.slice(), small: [] }; }  // nothing works: the no-view mix, exactly
  }
  const dd = c.w.map((v, i) => v - w0[i]);
  return { w: c.w, tilt: { tracking_error_before: round(te), largest_move_before: round(big), scale: round(s), tracking_error_after: round(Math.sqrt(Math.max(quad(sigma, dd), 0))),
    largest_move_after: round(Math.max(...dd.map(Math.abs))), dropped_after_tilt: c.small.filter(t => w0[names.indexOf(t)] > 0 || w1[names.indexOf(t)] > 0), budget: { tracking_error: TE_BUDGET, per_fund: MAX_TILT, min_weight: minWeight } } };
}

// ------------------------------------------------------------------ planning assumptions (robokit/cma.py)
export function assumption(core, assetClass, region, market) {
  const F = core.cma.fpc_2026, src = core.cma.fpc_source, us = core.cma.us_rates || {};
  const eqKey = { Canada: 'canada_equity', US: 'us_equity', 'North America': 'us_equity', 'Emerging markets': 'em_equity', China: 'em_equity' }[region] || 'intl_equity';
  if (assetClass === 'Equity') return [F[eqKey], src];
  if (assetClass === 'Multi-asset') return [0.6 * F[eqKey] + 0.4 * F.fixed_income, 'Robo-Kit: 60% equity / 40% bonds of ' + src];
  if (assetClass === 'Real estate') return [F[eqKey], 'Robo-Kit assumption: same as equities of its region (' + src + ')'];
  if (assetClass === 'Cash') return market === 'US' && us.bill != null ? [us.bill, 'US 13-week Treasury bill yield today'] : [F.short_term, src];
  if (assetClass === 'Fixed income') return market === 'US' && us.note5 != null ? [us.note5, 'US 5-year Treasury yield today (starting-yield rule of thumb)'] : [F.fixed_income, src];
  if (assetClass === 'Commodity') return [market === 'US' && us.bill != null ? us.bill : F.short_term, 'Robo-Kit assumption: short-term rate, no extra return assumed for gold or commodities'];
  return [null, 'no planning assumption for this asset class; model estimate used'];
}

// ------------------------------------------------------------------ risk levels (robokit/profile.py)
export const riskShare = (lvl10) => Math.min(Math.max(lvl10, 1), 10) / 10;
export const cashCap = (lvl10) => (lvl10 <= 2 ? 1 : lvl10 <= 4 ? 0.30 : 0.15);
export const satelliteCap = (lvl10) => (lvl10 <= 4 ? 0.10 : lvl10 <= 6 ? 0.20 : 0.30);

/** The stock-market yardstick (robokit/engine.py market_vol): a list without stock funds borrows the reference
 *  shelf's stock funds over the same months, and says so; it never falls back to a made-up number. */
function marketVol(M, X, tickers, shelf, rows, notes) {
  const v = equityVol(X, tickers, shelf); if (v != null) return v;
  const refEq = shelfFor(M, {}).filter(s => s.asset_class === 'Equity' && s.prior > 0);
  if (!refEq.length) throw new RoboKitError('No stock fund is available to measure the stock market\'s volatility.', 'input', { kind: 'no_equity' });
  const ref = buildReturns(M, refEq, []);
  const cols = ref.tickers; const ok = rows.filter(i => cols.every(t => Number.isFinite(ref.full.get(t)[i])));
  if (ok.length < MIN_WINDOW) throw new RoboKitError('The stock funds\' history is too short to measure the stock market\'s volatility.', 'input', { kind: 'no_equity' });
  const Xr = ok.map(i => cols.map(t => ref.full.get(t)[i]));
  const out = equityVol(Xr, cols, refEq);
  notes.push(note(`This list holds no stock fund, so the level targets use the reference stock funds' volatility (${pctTxt(out, 1)} a year) over the same months.`));
  return out;
}

function equityVol(X, tickers, shelf) {
  let eq = shelf.filter(s => s.asset_class === 'Equity' && s.prior > 0 && tickers.includes(s.ticker));
  if (!eq.length) eq = shelf.filter(s => s.asset_class === 'Equity' && tickers.includes(s.ticker));
  if (!eq.length) return null;
  const w = new Map(); for (const s of eq) w.set(s.ticker, (w.get(s.ticker) || 0) + (s.prior || 0));
  let tot = sum([...w.values()]); if (tot <= 0) { for (const k of w.keys()) w.set(k, 1); tot = w.size; }
  const cols = [...w.keys()].map(t => tickers.indexOf(t));
  const port = X.map(r => cols.reduce((s, c, k) => s + r[c] * w.get([...w.keys()][k]) / tot, 0));
  return std(port) * Math.sqrt(12);
}

// ------------------------------------------------------------------ stress tests (robokit/stress.py)
function stressTest(M, weights, full, amount = 10000) {
  const out = [];
  for (const sc of M.core.scenarios) {
    const s = sc.start.slice(0, 7), e = sc.end.slice(0, 7);
    const rows = []; for (let i = 0; i < M.T; i++) { const d = M.months[i]; if (d > s && d <= e) rows.push(i); }
    if (!rows.length) continue;
    const peers = (M.core.scenario_peers[M.code] || {})[sc.key] || {};  // peer medians in the portfolio currency
    const r = {}, stand = [];
    for (const [t, w] of weights) {
      const f = full.get(t);
      if (f && rows.every(i => Number.isFinite(f[i]))) { r[t] = rows.reduce((p, i) => p * (1 + f[i]), 1) - 1; continue; }
      const m = M.fund(t) || {};
      const key = `${M.code}|${m.asset_class}|${m.region}`;
      r[t] = peers[key] ?? peers[`*|${m.asset_class}|*`];
      stand.push(t);
    }
    const row = { key: sc.key, scenario: sc.name, from: sc.start, to: sc.end, what: sc.what };
    const missing = weights.map(([t]) => t).filter(t => r[t] == null || !Number.isFinite(r[t]));
    if (missing.length) {  // never drop an episode silently: keep the row and name the funds with no history or stand-in
      out.push({ ...row, portfolio_return: null, dollars: null, worst_fund: null, worst_fund_return: null, stand_ins: stand.filter(t => !missing.includes(t)), estimated: [], not_estimable: missing });
      continue;
    }
    let pr = 0, worst = null; for (const [t, w] of weights) { pr += w * r[t]; if (worst == null || r[t] < r[worst]) worst = t; }
    const firstIn = monthEnd(M.months[rows[0]]);  // spliced or back-filled when the fund starts after the episode's first month
    const estimated = weights.map(([t]) => t).filter(t => !stand.includes(t) && (M.fund(t)?.first_month || '') > firstIn);
    out.push({ ...row, portfolio_return: round(pr), dollars: Math.round(pr * amount), worst_fund: worst, worst_fund_return: round(r[worst]), stand_ins: stand, estimated, not_estimable: [] });
  }
  return out;
}

// ------------------------------------------------------------------ projections (robokit/projection.py)
export function project(Xcols, weights, geoNet, { amount = 10000, monthly = 0, years = 10, goal = null, nPaths = 5000, seed = 7 } = {}) {
  const T = Xcols.length, n = weights.length;
  const X = Xcols.map(r => r.slice());
  for (let j = 0; j < n; j++) {
    const col = X.map(r => r[j]); const m = mean(col), v = std(col) ** 2;
    const target = (1 + geoNet[j]) ** (1 / 12) - 1 + 0.5 * v;
    for (const r of X) r[j] = r[j] - m + target;
  }
  const port = X.map(r => dot(r, weights));
  const months = Math.round(years * 12);
  const finals = new Float64Array(nPaths), byYear = Array.from({ length: years + 1 }, () => new Float64Array(nPaths));
  const oneYear = new Float64Array(nPaths), growth = Array.from({ length: nPaths }, () => new Float64Array(months));
  const lasting = new Float64Array(nPaths).fill(months);  // months of withdrawals paid in full (months = it lasted)
  const yearOne = new Float64Array(nPaths);  // value after 12 months including monthly adds or withdrawals
  for (let p = 0; p < nPaths; p++) {
    // one generator per path: the first year is the same whatever the horizon (robokit/projection.py)
    const rng = mulberry32((seed * 1000003 + p * 7919 + 1) >>> 0);
    let i = 0, val = amount; byYear[0][p] = amount; const rows = new Int32Array(months);
    while (i < months) { const start = Math.floor(rng() * T); let len = 1; while (rng() > 1 / 6) len++; for (let k = 0; k < len && i < months; k++, i++) rows[i] = (start + k) % T; }
    for (let m = 0; m < months; m++) {
      const r = port[rows[m]]; growth[p][m] = r; val = val * (1 + r) + monthly;
      if (val < 0) { if (lasting[p] === months) lasting[p] = m; val = 0; }  // a withdrawal the money could not cover
      if (m === 11) yearOne[p] = val;
      if ((m + 1) % 12 === 0) byYear[(m + 1) / 12][p] = val;
    }
    finals[p] = val; let g = 1; for (let m = 0; m < Math.min(12, months); m++) g *= 1 + growth[p][m]; oneYear[p] = g - 1;
  }
  const q = [10, 25, 50, 75, 90];
  const annRange = (h) => { if (h * 12 > months) return null; const a = growth.map(gr => { let c = 1; for (let m = 0; m < h * 12; m++) c *= 1 + gr[m]; return c ** (1 / h) - 1; }); return { years: h, p10: round(percentile(a, 10)), p50: round(percentile(a, 50)), p90: round(percentile(a, 90)) }; };
  const medG = percentile(growth.map(gr => gr.reduce((c, r) => c * (1 + r), 1)), 50) ** (1 / years) - 1;
  const invested = monthly >= 0 ? amount + monthly * months : null;
  const res = {
    years, amount, monthly_contribution: monthly, invested,
    final: Object.fromEntries(q.map(k => [`p${k}`, round(percentile(finals, k), 2)])),
    median_annual_return: round(medG),
    one_year: months >= 12 ? { p5: round(percentile(oneYear, 5)), p10: round(percentile(oneYear, 10)), p50: round(percentile(oneYear, 50)), p90: round(percentile(oneYear, 90)), prob_loss: round(oneYear.filter(v => v < 0).length / nPaths, 3) } : null,
    by_holding_period: [1, 3, 5, 10].map(annRange).filter(Boolean),
    prob_below_invested: invested == null ? null : round(finals.filter(v => v < invested).length / nPaths, 3),
    one_year_value: months >= 12 ? Object.fromEntries([5, 10, 50, 90].map(k => [`p${k}`, round(percentile(Array.from(yearOne), k), 2)])) : null,
    yearly: byYear.map((arr, y) => ({ year: y, ...Object.fromEntries(q.map(k => [`p${k}`, round(percentile(arr, k), 2)])) })),
    n_paths: nPaths, method: 'stationary bootstrap (mean block 6 months) of monthly fund returns, re-centred on planning assumptions net of fees',
  };
  if (res.one_year) res.one_year_dollars = Object.fromEntries(Object.entries(res.one_year).filter(([k]) => /^p\d+$/.test(k)).map(([k, v]) => [k, Math.round(amount * (1 + v))]));
  if (monthly < 0) res.withdrawal = { monthly: round(-monthly, 2), chance_lasts: round(Array.from(lasting).filter(v => v >= months).length / nPaths, 3), p10_months: Math.floor(percentile(Array.from(lasting), 10)), p50_months: Math.floor(percentile(Array.from(lasting), 50)), months };
  if (goal) { const short = Array.from(finals).filter(v => v < goal); res.goal = goal; res.chance_need_to_adjust = round(short.length / nPaths, 3); res.median_shortfall = short.length ? round(percentile(short.map(v => goal - v), 50), 2) : 0; }
  return res;
}

// ------------------------------------------------------------------ rebalancing (robokit/rebalance.py, same algorithm)
const thousands = (x) => { const s = String(Math.round(x)); let out = ''; for (let k = 0; k < s.length; k++) { if (k && (s.length - k) % 3 === 0 && s[k - 1] !== '-') out += ','; out += s[k]; } return out; };
/** A number for the notes and the rule, written as robokit/rebalance.py _fmt does: up to two decimals, halves up. */
function rebFmt(x, pct = false) {
  const v = pct ? 100 * x : x;
  const r = Math.floor(Math.abs(v) * 100 + 0.5) / 100;
  let [ip, fp] = r.toFixed(2).split('.');
  ip = ip.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  fp = fp.replace(/0+$/, '');
  return (v < 0 && r ? '-' : '') + ip + (fp ? '.' + fp : '') + (pct ? '%' : '');
}
function rebNum(x, name, lo = null, loOpen = false) {
  if (typeof x !== 'number' || !Number.isFinite(x)) throw new RoboKitError(`${name} must be a finite number.`, 'input', { field: name });
  if (lo != null && (loOpen ? x <= lo : x < lo)) throw new RoboKitError(`${name} must be ${loOpen ? 'above' : 'at least'} ${lo}.`, 'input', { field: name });
  return x;
}
/** Dollar trades over the funds in idx that add up to amount (robokit/rebalance.py _spread). */
function rebSpread(amount, value, goal, idx, target) {
  const out = new Array(value.length).fill(0);
  if (amount === 0 || !idx.length) return out;
  if (amount > 0) {
    const gap = new Map(idx.map(i => [i, Math.max(0, goal[i] - value[i])])); let g = 0; for (const i of idx) g += gap.get(i);
    if (g >= amount) for (const i of idx) out[i] = amount * gap.get(i) / g;
    else {
      const rest = amount - g; let tw = 0; for (const i of idx) tw += target[i];
      for (const i of idx) out[i] = gap.get(i) + rest * (tw > 0 ? target[i] / tw : 1 / idx.length);
    }
    return out;
  }
  const need = -amount; const exc = new Map(idx.map(i => [i, Math.max(0, value[i] - goal[i])])); let e = 0; for (const i of idx) e += exc.get(i);
  if (e >= need) for (const i of idx) out[i] = -need * exc.get(i) / e;
  else {
    const left = new Map(idx.map(i => [i, value[i] - exc.get(i)])); let lw = 0; for (const i of idx) lw += left.get(i); const rest = need - e;
    for (const i of idx) out[i] = -(exc.get(i) + (lw > 0 ? rest * left.get(i) / lw : 0));
  }
  return out;
}
/** v_i = clip(x_i - tau a_i, lo_i, hi_i) with sum v = total, tau exact from the sorted breakpoints (robokit/rebalance.py _shift_into). */
function rebShiftInto(x, a, lo, hi, total) {
  const n = x.length;
  const g = (tau) => { let s = 0; for (let i = 0; i < n; i++) s += Math.min(hi[i], Math.max(lo[i], x[i] - tau * a[i])); return s; };
  const raw = []; for (let i = 0; i < n; i++) raw.push((x[i] - hi[i]) / a[i], (x[i] - lo[i]) / a[i]);
  raw.sort((p, q) => p - q); const bp = raw.filter((v, k) => k === 0 || v !== raw[k - 1]);
  let tau;
  if (total >= g(bp[0]) - 1e-15) tau = bp[0];
  else if (total <= g(bp[bp.length - 1]) + 1e-15) tau = bp[bp.length - 1];
  else {
    let k = 0, m = bp.length - 1;
    while (m - k > 1) { const mid = (k + m) >> 1; if (g(bp[mid]) >= total) k = mid; else m = mid; }
    const gk = g(bp[k]), gm = g(bp[m]); tau = gk === gm ? bp[k] : bp[k] + (gk - total) * (bp[m] - bp[k]) / (gk - gm);
  }
  return x.map((xi, i) => Math.min(hi[i], Math.max(lo[i], xi - tau * a[i])));
}

/** Orders that take the account from units (fund -> units held) and cash to targets (fund -> weight, adding to 1) after a
 *  cash flow (new money positive, a withdrawal negative): cash flows first, tolerance bands with a destination, whole
 *  units, a minimum order, residual cash to the fund furthest below target. robokit/rebalance.py explains each rule. */
export function rebalance(targets, units = {}, prices = {}, { cash = 0, flow = 0, bandAbs = 0.02, bandRel = 0.25, destination = 0.875, minTrade = 50,
  cashReserve = 0, wholeUnits = true, costBps = 10, adv = null, advLimit = 0.01, bandTrades = true } = {}) {
  units = units || {}; prices = prices || {};
  if (!targets || typeof targets !== 'object' || Array.isArray(targets) || !Object.keys(targets).length) throw inputError('targets must name at least one fund with its weight.', 'targets');
  const tick = [...Object.keys(targets), ...Object.keys(units).filter(t => !(t in targets))];
  const tw = tick.map(t => rebNum(t in targets ? targets[t] : 0, `targets[${t}]`, 0));  // null is not 0, as in Python
  const tsum = tw.reduce((s, v) => s + v, 0);
  if (Math.abs(tsum - 1) > 1e-6) throw inputError(`The target weights add up to ${tsum.toFixed(4)}, not 1.`, 'targets');
  const held = tick.map(t => rebNum(t in units ? units[t] : 0, `units[${t}]`, 0));
  const missing = tick.filter(t => !(t in prices));
  if (missing.length) throw new RoboKitError(`A price is needed for every fund: ${missing.join(', ')}.`, 'input', { field: 'prices', missing });
  const px = tick.map(t => rebNum(prices[t], `prices[${t}]`, 0, true));
  cash = rebNum(cash, 'cash', 0); flow = rebNum(flow, 'flow');
  bandAbs = rebNum(bandAbs, 'band_abs', 0); bandRel = rebNum(bandRel, 'band_rel', 0); destination = rebNum(destination, 'destination', 0);
  if (destination > 1) throw inputError('destination is a share of the band, from 0 (back to target) to 1 (back to the band edge).', 'destination');
  minTrade = rebNum(minTrade, 'min_trade', 0); cashReserve = rebNum(cashReserve, 'cash_reserve', 0);
  costBps = rebNum(costBps, 'cost_bps', 0); advLimit = rebNum(advLimit, 'adv_limit', 0, true);
  if (costBps >= 1e4) throw inputError('cost_bps must be below 10,000 (100% of the amount traded).', 'cost_bps');

  const n = tick.length;
  const value = held.map((u, i) => u * px[i]);
  const heldValue = value.reduce((s, v) => s + v, 0);
  const avail = cash + flow;  // cash on hand after the flow
  const invest = heldValue + avail - cashReserve;  // the money the targets apply to
  if (invest <= 0) throw new RoboKitError('The withdrawal and the cash kept aside are larger than the account.', 'input', { field: 'flow', account: Math.round((heldValue + cash) * 100) / 100 });
  const goal = tw.map(w => w * invest);
  const everyone = tick.map((_, i) => i);

  // 1. the cash flow
  const flowTrade = rebSpread(avail - cashReserve, value, goal, everyone, tw);
  const v1 = value.map((v, i) => v + flowTrade[i]);
  // 2. bands, after the flow
  const w1 = v1.map(v => v / invest);
  const band = tw.map(w => Math.min(bandAbs, bandRel * w));
  const drifted = tick.map((_, i) => Math.abs(w1[i] - tw[i]) > band[i] + 1e-12);
  const out = drifted.map(d => Boolean(bandTrades) && d);  // bands off: only the flow trades, but the drift is still reported
  let bandTrade = new Array(n).fill(0);
  if (out.some(Boolean)) {
    const lo = tick.map((_, i) => (out[i] ? tw[i] - destination * band[i] : Math.min(w1[i], tw[i] - destination * band[i])));
    const hi = tick.map((_, i) => (out[i] ? tw[i] + destination * band[i] : Math.max(w1[i], tw[i] + destination * band[i])));
    const w2 = rebShiftInto(w1, tw.map(w => Math.max(w, 1e-12)), lo, hi, 1);
    bandTrade = w2.map((w, i) => (w - w1[i]) * invest);
  }
  const trade = flowTrade.map((f, i) => f + bandTrade[i]);

  // 3. whole units, minimum trade
  const round6 = (v) => Math.round(v * 1e6) / 1e6;
  const toUnits = (i, dollars) => {
    if (!wholeUnits) return dollars > 0 ? round6(dollars / px[i]) : -Math.min(held[i], round6(-dollars / px[i]));
    if (dollars > 0) return Math.floor(dollars / px[i] + 1e-9);
    return -Math.min(held[i], Math.ceil(-dollars / px[i] - 1e-9));
  };
  const q = trade.map((d, i) => (Math.abs(d) > 1e-9 ? toUnits(i, d) : 0));
  const short = avail < cashReserve - 1e-9;  // the cash on hand does not cover the reserve
  const neededSell = q.map((qi, i) => (flow < 0 || short) && flowTrade[i] < 0 && qi < 0);  // pay a withdrawal or the reserve
  const reason = tick.map(() => []);
  for (let i = 0; i < n; i++) if (q[i] && Math.abs(q[i] * px[i]) < minTrade && !neededSell[i]) { q[i] = 0; reason[i].push('under the minimum trade'); }
  const rate = costBps / 1e4;
  const cashAfter = () => { let s = avail, g = 0; for (let i = 0; i < n; i++) { s -= q[i] * px[i]; g += Math.abs(q[i]) * px[i]; } return s - rate * g; };  // after the orders and their cost
  const dev = (i) => (held[i] + q[i]) * px[i] - goal[i];  // dollars above target after the orders
  const argmax = (idx, key) => idx.reduce((b, k) => (b == null || key(k) > key(b) ? k : b), null);  // ties: the first fund
  const cap = 10 * n + Math.trunc(q.reduce((s, x) => s + Math.abs(x), 0)) + Math.trunc(held.reduce((s, x) => s + x, 0)) + 2;  // enough to sell every unit
  for (let it = 0; it < cap; it++) {  // trim buys, then sell, until the cash covers the orders
    if (cashAfter() >= cashReserve - 1e-9) break;
    const buys = tick.map((_, i) => i).filter(i => q[i] > 0);
    if (buys.length) { const i = argmax(buys, dev); q[i] -= wholeUnits ? 1 : Math.min(q[i], (cashReserve - cashAfter()) / (px[i] * (1 + rate))); }
    else {
      const sellable = tick.map((_, i) => i).filter(i => held[i] + q[i] > 0);
      if (!sellable.length) break;
      const i = argmax(sellable, dev); const room = held[i] + q[i];  // a fractional holding is sold whole, never short
      q[i] -= wholeUnits ? Math.min(1, room) : Math.min(room, (cashReserve - cashAfter()) / (px[i] * (1 - rate)));
    }
  }
  if (cashAfter() < cashReserve - 1e-6) throw inputError('The holdings cannot be sold for enough cash to pay the withdrawal.', 'flow');
  for (let i = 0; i < n; i++) if (q[i] > 0 && q[i] * px[i] < minTrade) { q[i] = 0; reason[i].push('under the minimum trade'); }  // a trimmed buy under the minimum
  // 4. residual cash, one unit at a time, while it brings a fund closer to target
  if (wholeUnits) {
    for (let it = 0; it < 100000; it++) {
      const spare = cashAfter() - cashReserve;
      const ok = tick.map((_, i) => i).filter(i => tw[i] > 0 && px[i] * (1 + rate) <= spare + 1e-9 && -dev(i) >= px[i] / 2 && (q[i] > 0 || px[i] >= minTrade));
      if (!ok.length) break;
      const i = argmax(ok, k => -dev(k)); q[i] += 1;
      if (!reason[i].includes('residual cash')) reason[i].push('residual cash');
    }
  }

  const afterUnits = held.map((h, i) => h + q[i]);
  const afterValue = afterUnits.map((u, i) => u * px[i]);
  const totalAfter = afterValue.reduce((s, v) => s + v, 0);
  const cAfter = cashAfter();
  let gross = 0; for (let i = 0; i < n; i++) gross += Math.abs(q[i]) * px[i];
  const account = heldValue + avail;
  const rows = tick.map((t, i) => {
    if (q[i] > 0 && flowTrade[i] > 0) reason[i].unshift('new money');
    if (q[i] < 0 && flowTrade[i] < 0 && flow < 0) reason[i].unshift('withdrawal');
    if (q[i] && out[i]) reason[i].unshift(tw[i] === 0 ? 'not in the mix' : 'outside its band');
    if (q[i] && !reason[i].length) reason[i].push('balances the other orders');
    const dollars = q[i] * px[i];
    const row = { ticker: t, target: round6(tw[i]), band: round6(band[i]), units_before: held[i], weight_before: heldValue > 0 ? round6(value[i] / heldValue) : null,
      action: q[i] > 0 ? 'buy' : q[i] < 0 ? 'sell' : 'hold', units: Math.abs(q[i]), price: px[i], amount: Math.round(Math.abs(dollars) * 100) / 100,
      units_after: afterUnits[i], weight_after: totalAfter > 0 ? round6(afterValue[i] / totalAfter) : null, out_of_band_after_flow: drifted[i],
      reason: q[i] ? reason[i] : reason[i].filter(r => r === 'under the minimum trade') };
    if (adv && t in adv && q[i]) { const vol = rebNum(adv[t], `adv[${t}]`, 0, true); row.share_of_daily_volume = round6(Math.abs(dollars) / vol); row.liquidity_flag = Math.abs(dollars) / vol > advLimit; }
    return row;
  });
  const drift = (ws) => ws.reduce((s, w, i) => s + Math.abs(w - tw[i]), 0) / 2;
  const beforeW = heldValue > 0 ? value.map(v => v / heldValue) : null;
  const afterW = totalAfter > 0 ? afterValue.map(v => v / totalAfter) : null;
  const notes = [];
  if (!out.some(Boolean)) {
    const why = drifted.some(Boolean) ? 'The bands are off' : 'No fund is outside its band';
    notes.push(q.some(x => x) ? `${why}, so only the ${flow ? 'cash flow' : 'cash on hand'} is traded.` : `${why}: nothing to trade.`);
  }
  const skipped = tick.filter((_, i) => reason[i].includes('under the minimum trade') && !q[i]);
  if (skipped.length) notes.push(`Skipped because each order would be under ${rebFmt(minTrade)}: ${skipped.join(', ')}.`);
  const flagged = rows.filter(r => r.liquidity_flag).map(r => r.ticker);
  if (flagged.length) notes.push(`Large against daily trading volume (over ${rebFmt(advLimit, true)}): ${flagged.join(', ')}. Consider splitting the order over several days.`);
  const r2 = (v) => Math.round(v * 100) / 100;
  return {
    rows, cash_before: r2(cash), flow: r2(flow), cash_after: r2(cAfter), cash_reserve: r2(cashReserve), traded: r2(gross),
    turnover: account > 0 ? round6(gross / 2 / account) : 0, estimated_cost: r2(gross * costBps / 1e4),
    drift_before: beforeW ? round6(drift(beforeW)) : null, drift_after: afterW ? round6(drift(afterW)) : null,
    largest_gap_after: afterW ? round6(Math.max(...afterW.map((w, i) => Math.abs(w - tw[i])))) : null, notes,
    rule: `cash flows first; bands of min(${rebFmt(bandAbs, true)}, ${rebFmt(bandRel, true)} of target), traded back to ${rebFmt(destination, true)} of the band; whole units, orders under ${rebFmt(minTrade)} skipped; residual cash to the fund furthest below target`,
  };
}

// ------------------------------------------------------------------ buy-only contributions (robokit/engine.py plan_contribution)
/** Split new money across the mix's funds so the holdings move toward the target weights without selling anything.
 *  current: {ticker: dollars held now} (missing = 0). Each fund first gets what it lacks at the new total, in proportion
 *  when the money is short; money left after every gap is closed goes by target weight. Units round down at the last close. */
export function planContribution(holdings, newMoney, current = {}) {
  const fin = (v) => typeof v === 'number' && Number.isFinite(v);  // the same refusals as robokit/engine.py plan_contribution
  if (!fin(newMoney) || !(newMoney > 0 && newMoney <= AMOUNT_MAX)) throw inputError('new_money must be above 0.', 'new_money');
  for (const h of holdings) {
    if (!fin(h.weight) || h.weight < 0 || h.weight > 1) throw new RoboKitError(`The weight of ${h.ticker} must be between 0 and 1.`, 'input', { field: 'weight', ticker: h.ticker });
    if (h.price != null && (!fin(h.price) || h.price <= 0)) throw new RoboKitError(`The price of ${h.ticker} must be above 0.`, 'input', { field: 'price', ticker: h.ticker });
  }
  for (const [t, v] of Object.entries(current || {})) if (v != null && (!fin(v) || v < 0)) throw new RoboKitError(`The amount held in ${t} cannot be negative.`, 'input', { field: 'current', ticker: t });
  const cash = newMoney;
  const cur = Object.fromEntries(holdings.map(h => [h.ticker, Number((current || {})[h.ticker]) || 0]));
  const heldNow = Object.values(cur).reduce((s, v) => s + v, 0), total = heldNow + cash;
  const gaps = holdings.map(h => Math.max(0, h.weight * total - cur[h.ticker]));
  const need = gaps.reduce((s, v) => s + v, 0);
  const buys = holdings.map((h, i) => (need > cash ? (need ? cash * gaps[i] / need : 0) : gaps[i] + (cash - need) * h.weight));
  const rows = holdings.map((h, i) => {
    const buy = roundHalfUp(buys[i], 2), after = cur[h.ticker] + buys[i];
    return { ticker: h.ticker, symbol: h.symbol, target: h.weight, now: cur[h.ticker], now_weight: heldNow ? cur[h.ticker] / heldNow : null, buy,
      units: h.price ? Math.floor(buy / h.price + 1e-9) : null, price: h.price ?? null, after_weight: total ? after / total : null };  // + 1e-9: an exact multiple buys its last unit (robokit/engine.py)
  });
  const drift = (key) => rows.reduce((s, r) => s + Math.abs((r[key] ?? r.target) - r.target), 0) / 2;
  return { new_money: cash, held_now: Math.round(heldNow * 100) / 100, rows, gap_closed: need <= cash + 1e-9,
    drift_before: heldNow ? Math.round(drift('now_weight') * 10000) / 10000 : null, drift_after: Math.round(drift('after_weight') * 10000) / 10000,
    rule: 'buy-only: each fund gets what it lacks at the new total (in proportion when money is short), then the rest by target weight; nothing is sold' };
}

// ------------------------------------------------------------------ the main entry (robokit/engine.py build_portfolio)
/** One row of the five-level ladder at `lvl`: the reference funds by default, or the person's own request (picks, swaps,
 *  minimums, amount, monthly flow, horizon, draws) so the chooser shows the numbers that level would really be built with. */
export function ladderRow(M, req, lvl) {
  const p = buildPortfolio(M, { satellites: [], swaps: {}, exclude: [], minimums: {}, nBoot: 100, ...req, risk_level: lvl, views: [], fixedWeights: null });
  const pr = p.projection, y10 = (pr.yearly || []).find(y => y.year === 10);
  return { level: lvl, label: p.risk.label, mix: p.mix.asset_class, volatility: p.stats.volatility,
    planning_return: p.stats.planning_return, amount: pr.amount, monthly: pr.monthly_contribution, years: pr.years,
    one_year: pr.one_year, one_year_value: pr.one_year_value, ten_year: y10 ? { p10: y10.p10, p50: y10.p50, p90: y10.p90 } : pr.final,
    horizon: pr.final, withdrawal: pr.withdrawal || null, fee_per_year: p.stats.fee_per_year,
    worst: p.stress.filter(s => s.portfolio_return != null).reduce((a, b) => (a == null || b.portfolio_return < a.portfolio_return ? b : a), null),
    stress: p.stress.map(s => ({ key: s.key, scenario: s.scenario, portfolio_return: s.portfolio_return, dollars: s.dollars, not_estimable: s.not_estimable || [] })),
    holdings: p.holdings.map(h => ({ ticker: h.ticker, symbol: h.symbol, weight: h.weight, asset_class: h.asset_class })) };
}

const note = (en) => ({ en });

export function buildPortfolio(M, req = {}) {
  const r = { risk_level: null, preferEsg: false, hedgeUsEquity: false, sleeves: null, swaps: {}, satellites: [], exclude: [], minimums: {},
    maxWeight: 0.5, satelliteCap: null, satelliteMaxEach: 0.10, cryptoMaxEach: 0.05, minWeight: 0.02, views: [], resample: true,
    nBoot: 200, seed: 0, amount: 10000, monthly: 0, years: 10, goal: null, fixedWeights: null, onInfeasible: 'refuse',
    answers: null, enforceSuitability: false, acknowledgedAboveSuggestion: false, ...req };
  validateRequest(r);
  const fixed = Object.fromEntries(Object.entries(r.fixedWeights || {}).map(([t, v]) => [t, Number(v)]).filter(([, v]) => v > 0));
  const isFixed = Object.keys(fixed).length > 0;
  const notes = [];
  const shelf = shelfFor(M, { preferEsg: r.preferEsg, hedgeUsEquity: r.hedgeUsEquity, sleeves: r.sleeves, swaps: r.swaps, exclude: r.exclude, present: [...r.satellites, ...Object.keys(r.fixedWeights || {})] }, notes);
  const changed = shelf.some(s => s.ticker !== s.reference);
  const core = [...new Set(shelf.map(s => s.ticker))];
  const wanted = [...new Set(r.satellites)];
  for (const t of Object.keys(fixed)) if (!core.includes(t) && !wanted.includes(t) && !r.exclude.includes(t)) wanted.push(t);
  const sats = [];
  for (const t of wanted) {
    if (core.includes(t) || r.exclude.includes(t)) continue;
    const f = M.fund(t);
    if (!f) { notes.push(note(`${t} is not in the fund list, so it was left out.`)); continue; }
    if (!f.eligible) { notes.push(note(`${t} was left out: ${f.excluded_because}.`)); continue; }
    if (!M.series.has(t)) { notes.push(note(`${t} has no price history in this snapshot, so it was left out.`)); continue; }
    sats.push(t);
  }
  const home = M.code === 'CA' ? 'CAD' : 'USD', ccyName = { CAD: 'Canadian dollars', USD: 'US dollars' };
  for (const t of [...core, ...sats]) {
    const c = M.currencyOf(t);
    if (c !== home) {
      const us = M.fund(t)?.market === 'US';
      notes.push(note(`${t} trades in ${ccyName[c]} ${us ? 'on a US exchange' : 'on a Canadian exchange'}; its returns are shown in ${ccyName[home]} and buying it means converting currency.`));
    }
  }
  if (!core.length && !sats.length) {
    const why = notes.map(n => n.en).join('; ');
    throw new RoboKitError('No fund is left to build a portfolio from' + (why ? `: ${why}` : ': every fund was excluded.'), 'input', { kind: 'no_funds' });
  }
  if (isFixed && !Object.keys(fixed).some(t => core.includes(t) || sats.includes(t)))
    throw new RoboKitError(`None of the funds in your own weights can be used: ${notes.map(n => n.en).join('; ') || 'none of them is in the fund list'}`, 'input', { kind: 'no_funds' });
  const { tickers, rows, X, full, notes: hist } = buildReturns(M, shelf, sats);
  if (X.length < MIN_WINDOW) throw new RoboKitError(`These funds share only ${X.length} months of history; at least ${MIN_WINDOW} are needed.`, 'input', { kind: 'short_history', months: X.length });
  const eqVol = marketVol(M, X, tickers, shelf, rows, notes);
  let lvl5, lvl10, tv, src;
  const chosen = r.risk_level == null ? null : Number(r.risk_level);
  if (r.targetVol != null) { tv = r.targetVol; lvl10 = Math.max(1, Math.min(10, 10 * tv / eqVol)); lvl5 = lvl10 / 2; src = 'target volatility given directly'; }
  else { lvl5 = Math.max(1, Math.min(5, chosen == null ? 3 : chosen)); lvl10 = 2 * lvl5; tv = riskShare(lvl10) * eqVol; src = chosen == null ? "preset 'mid'" : 'risk level chosen'; }
  // opt-in suitability (robokit/engine.py _suitability, _suitable_level): off by default
  let suit = null, suitability = null;
  if (r.enforceSuitability) {
    if (!r.answers || !Object.keys(r.answers).length) throw inputError('With suitability checks on, the profile answers are needed.', 'answers');
    suit = scoreProfile(M.core.questions, r.answers);
    if (suit.status !== 'complete' || suit.suggested_level == null) { const miss = suit.missing || []; throw new RoboKitError(`With suitability checks on, the profile must be complete first${miss.length ? ': ' + miss.join(', ') : ''}.`, 'input', { field: 'answers', status: suit.status, missing: miss }); }
  }
  const suitableLevel = (lv5, ownWeights = false) => {
    const s = suit.suggested_level, lv = String(roundHalfUp(lv5, 1)), why = `the lower of your capacity (${suit.capacity}) and your tolerance (${suit.tolerance})`;
    const rec = { enforced: true, suggested_level: s, capacity: suit.capacity, tolerance: suit.tolerance, requested_level: Math.round(lv5 * 100) / 100, acknowledged: !!r.acknowledgedAboveSuggestion };
    if (lv5 <= s + 1e-9) { rec.applied_level = Math.round(lv5 * 100) / 100; return [lv5, rec]; }
    if (r.acknowledgedAboveSuggestion) { notes.push(note(`You chose level ${lv}, above the level ${s} your answers suggest (${why}). You confirmed you understand the extra risk; the confirmation is recorded.`)); rec.applied_level = Math.round(lv5 * 100) / 100; return [lv5, rec]; }
    if (ownWeights) throw new RoboKitError(`Your own weights behave like level ${lv}, above the level ${s} your answers suggest (${why}). With suitability checks on, confirm you understand the extra risk to keep them.`, 'input', { field: 'fixed_weights', suggested_level: s });
    notes.push(note(`Your answers suggest level ${s} (${why}). With suitability checks on, the mix is built at level ${s}, not the level ${lv} you chose. To build at level ${lv}, confirm you understand the extra risk.`));
    rec.applied_level = s; return [s, rec];
  };
  if (suit && !isFixed) {
    const [applied, rec] = suitableLevel(lvl5); suitability = rec;
    if (applied !== lvl5) { lvl5 = applied; lvl10 = 2 * applied; tv = riskShare(lvl10) * eqVol; src = 'suggested level (suitability checks on)'; }
  }

  const n = tickers.length;
  const prior = tickers.map(t => shelf.filter(s => s.ticker === t).reduce((s, x) => s + (x.prior || 0), 0));
  let ps = sum(prior); const priorN = ps > 0 ? prior.map(v => v / ps) : prior.map(() => 1 / n);
  const cashRow = shelf.find(s => s.role === 'cash'); const cashT = cashRow ? cashRow.ticker : null;
  const est = fit(X, priorN);

  const satCap = r.satelliteCap != null ? r.satelliteCap : satelliteCap(lvl10);
  const caps = {};
  for (const s of shelf) if (s.cap != null) caps[s.ticker] = Math.min(s.cap, r.maxWeight);
  for (const t of sats) caps[t] = (M.fund(t).asset_class === 'Crypto') ? r.cryptoMaxEach : r.satelliteMaxEach;
  if (cashT && cashCap(lvl10) < 1) caps[cashT] = cashCap(lvl10);
  const forced = Object.fromEntries(Object.entries(r.minimums || {}).filter(([t]) => tickers.includes(t)).map(([t, v]) => [t, Number(v)]));
  if (!isFixed) for (const t of Object.keys(r.minimums || {})) if (!tickers.includes(t)) notes.push(note(`The minimum for ${t} was not used: ${t} is not in this mix.`));
  // bounds exactly as RoboKitOptimizer._bounds
  const lb = zeros(n), ub = new Float64Array(n).fill(r.maxWeight);
  tickers.forEach((t, i) => { if (t === cashT) ub[i] = Math.max(1, r.maxWeight); if (caps[t] != null) ub[i] = Math.min(ub[i], caps[t]); if (r.exclude.includes(t)) ub[i] = 0; else if (forced[t] != null) lb[i] = Math.max(lb[i], forced[t]); });
  const bounds = { lb, ub };  // a minimum above a cap is handled in optimizeOn (refused, or relaxed and recorded)
  const satMask = tickers.map(t => sats.includes(t));
  const allIdx = tickers.map((_, i) => i);
  // when the limits cannot all hold: refuse (default), or relax in this order and say so (robokit/engine.py)
  const onInf = r.onInfeasible === 'relax' ? 'relax' : 'refuse';
  const ix = (ts) => ts.map(t => tickers.indexOf(t)).filter(i => i >= 0);
  const relaxOrder = [ix(core), ix(sats)];  // core funds (cash included) before the person's own picks; the group cap last
  const pol = { onInfeasible: onInf, relaxOrder, names: tickers };
  const plainInfeasible = (e) => {  // robokit/engine.py _plain_infeasible
    const d = e.details || {}; const tip = " To build anyway, ask for the limits to be relaxed (relax_limits in the tools, on_infeasible='relax' in the engine); every relaxed limit is then listed.";
    let msg = e.message;
    if (d.kind === 'caps') msg = `The limits on these funds add up to ${pctTxt(d.capacity ?? 0, 1)}, so together they cannot hold all the money. Add a broad fund or the cash fund, or raise the largest weight allowed per fund.`;
    else if (d.kind === 'group_cap' && (d.needed ?? 0) <= (d.group_minimums ?? 0) + 1e-12) msg = `The minimums you set on your own picks add up to ${pctTxt(d.group_minimums ?? 0, 1)}, above the ${pctTxt(d.cap ?? satCap, 1)} your own picks may hold at this level. Lower a minimum.`;
    else if (d.kind === 'group_cap') msg = `Your own picks may hold at most ${pctTxt(d.cap ?? satCap, 1)} at this level, but the other funds' limits leave ${pctTxt(d.needed ?? 0, 1)} for them. Add a broad fund, or remove one of your own picks.`;
    else if (d.kind === 'minimum_above_cap') msg = `You set a minimum of ${pctTxt(d.minimum ?? 0, 1)} for ${d.ticker}, above its limit of ${pctTxt(d.cap ?? 0, 1)}. Lower the minimum.`;
    else if (d.kind === 'minimums' || d.kind === 'group_minimums') msg = 'The minimums you set cannot all hold together with the limits. Lower a minimum.';
    return new RoboKitError(msg + tip, 'infeasible', d);
  };
  const isInfeasible = (e) => e instanceof RoboKitError && e.kind === 'infeasible';

  let wMap, bandMap = new Map(), lam = null, viewsInfo = null, relaxations = [], viewsApplied = false, calibration = null; const dropped = [];
  if (isFixed) {  // the person's own weights: no optimisation, same report
    if (r.views.length) notes.push(note('Views do not apply to your own weights, so they were not used.'));
    if (Object.keys(r.minimums || {}).length) notes.push(note('Minimums do not apply to your own weights, so they were not used.'));
    if (r.targetVol != null) notes.push(note('A target volatility does not apply to your own weights; the report shows how much they swing.'));
    const tw = sum(tickers.map(t => fixed[t] || 0));
    wMap = new Map(tickers.map(t => [t, (fixed[t] || 0) / tw]));
  } else {
    const volOf = (l) => { const o = optimizeOn(est, l, allIdx, bounds, satMask, satCap, pol); return Math.sqrt(quad(o.sigma, o.w)); };
    let cal; try { cal = calibrate(volOf, tv); } catch (e) { if (isInfeasible(e)) throw plainInfeasible(e); throw e; }
    const opts = { resample: r.resample, nBoot: r.nBoot, seed: r.seed, X, prior: priorN, ...pol };
    const optsTrial = { ...opts, onInfeasible: 'refuse' };
    const mixVol = (wm) => {  // volatility of the held mix (robokit/engine.py _mix_vol)
      const h = tickers.filter(t => wm.get(t) > 1e-6); const tt = sum(h.map(t => wm.get(t)));
      return Math.sqrt(quad(sub(est.sigma, h.map(t => tickers.indexOf(t))), h.map(t => wm.get(t) / tt)));
    };
    // the mix the person gets at this lambda: resampled, then the minimum position applied; the bootstrap is seeded the
    // same way on every call, so every lambda sees the same resampled histories (robokit/engine.py final)
    const finalAt = (lamX) => {
      let res = optimizeOn(est, lamX, allIdx, bounds, satMask, satCap, opts);
      const rel = res.relaxations || [];
      // the limits as applied (relaxed ones included): smaller lists tried when dropping small positions must fit inside them
      const bApplied = { lb, ub: Float64Array.from(res.ub) };
      const gRel = rel.filter(x => x.limit === 'group'); const gcap = gRel.length ? gRel[gRel.length - 1].applied : satCap;
      let wm = new Map(allIdx.map((i, k) => [tickers[i], res.w[k]]));
      let bm = new Map(res.band ? allIdx.map((i, k) => [tickers[i], res.band[k]]) : []);
      const drops = [], fnotes = [];
      // drop tiny positions and re-solve, round after round, until none is left (robokit/engine.py _drop_small);
      // a drop that leaves nothing, or that the remaining funds' limits cannot hold, is not made: those positions stay
      if (r.minWeight > 0) {
        let keep = [...allIdx], keptSmall = [], allSmall = false;
        const line = r.minWeight - 1e-9;  // a weight sitting at a cap equal to the minimum is not "small"
        const isSmall = (i) => wm.get(tickers[i]) > 0 && wm.get(tickers[i]) < line && forced[tickers[i]] == null;
        for (let round = 0; round < tickers.length; round++) {
          const small = keep.filter(isSmall);
          if (!small.length) break;
          const trial = keep.filter(i => !small.includes(i));
          if (!trial.some(i => wm.get(tickers[i]) > 0)) { keptSmall = small; allSmall = true; break; }  // every position is small: keep the list
          let resT;
          try { resT = optimizeOn(est, lamX, trial, bApplied, satMask, gcap, optsTrial); } catch (e) { if (isInfeasible(e)) { keptSmall = small; break; } throw e; }
          drops.push(...small.map(i => tickers[i]));
          keep = trial; res = resT;
          wm = new Map(tickers.map(t => [t, 0])); keep.forEach((i, k) => wm.set(tickers[i], res.w[k]));
          bm = new Map(res.band ? keep.map((i, k) => [tickers[i], res.band[k]]) : []);
        }
        const pc = pctTxt(r.minWeight);
        if (allSmall) fnotes.push(note(`Every position would be under ${pc}, so the minimum position size was not applied.`));
        else if (keptSmall.length) fnotes.push(note(`Kept under ${pc} because the other funds' limits cannot hold the rest: ${keptSmall.map(i => tickers[i]).join(', ')}.`));
        if (drops.length) {
          const k = drops.length;
          fnotes.push(note(`Dropped because ${k > 1 ? 'each' : 'it'} would have held less than ${pc}: ${[...drops].sort((x, y) => tickers.indexOf(x) - tickers.indexOf(y)).join(', ')}. The other funds were re-optimised.`));  // list order, not round order
        }
      }
      return { lam: lamX, wMap: wm, bandMap: bm, dropped: drops, notes: fnotes, relaxations: rel, boundsApplied: bApplied, gcapApplied: gcap, vol: mixVol(wm) };
    };
    const fin = calibrateFinal(finalAt, tv, finalAt(cal.lam), !!r.resample && r.nBoot > 0);
    const best = fin.best; calibration = fin.info;
    lam = best.lam; wMap = best.wMap; bandMap = best.bandMap; relaxations = best.relaxations; dropped.push(...best.dropped);
    const boundsApplied = best.boundsApplied, gcapApplied = best.gcapApplied;
    const reach = reachNote(tv, best.vol, calibration.outcome); if (reach) notes.push(reach);
    notes.push(...best.notes);
    if (cashT && (wMap.get(cashT) || 0) > 0.5) {  // as optimizer/portfolio.py
      notes.push(note(`${pctTxt(wMap.get(cashT))} sits in the cash-like ETF: at this risk aversion the model prefers safety over the small extra return of the other funds.`));
    }
    // optional views, bounded against the no-view weights
    if (r.views && r.views.length) {
      const V = viewsToBL(r.views, tickers, est, M.rf);
      if (V.P) {
        const estV = blPosterior(est, V);
        const volV = (l) => { const o = optimizeOn(estV, l, allIdx, bounds, satMask, satCap, pol); return Math.sqrt(quad(o.sigma, o.w)); };
        const lamV = calibrate(volV, tv).lam;
        const rv = optimizeOn(estV, lamV, allIdx, bounds, satMask, satCap, { ...opts, blViews: V });
        const w0 = tickers.map(t => wMap.get(t) || 0);
        const satSum = sum(tickers.map((t, i) => (satMask[i] ? (wMap.get(t) || 0) : 0)));
        // positions the no-view mix holds below the minimum on purpose (kept, or forced) are never dropped by the tilt
        const protect = new Set([...Object.keys(forced), ...tickers.filter((t, i) => w0[i] > 0 && w0[i] < r.minWeight - 1e-9)]);
        const bt = boundTiltClean(w0, rv.w, est.sigma, { minWeight: r.minWeight, protect, ub: boundsApplied.ub, groupMask: sats.length ? satMask : null, groupCap: Math.max(gcapApplied, satSum), names: tickers });
        if (bt.tilt.scale === 0) notes.push(note('Your view could not be applied within the limits, so the mix is the same as without it.'));
        else if (bt.tilt.dropped_after_tilt.length) {
          const dl = bt.tilt.dropped_after_tilt;
          notes.push(note(`After your view, ${dl.join(', ')} would have held less than ${pctTxt(r.minWeight)}, so ${dl.length === 1 ? 'it was' : 'they were'} left out and the view's effect was scaled to stay within its limits.`));
        }
        viewsInfo = { views: V.info, tilt: bt.tilt, no_view_weights: Object.fromEntries(tickers.filter(t => wMap.get(t) > 0).map(t => [t, round(wMap.get(t))])) };
        viewsApplied = bt.tilt.scale > 0;
        wMap = new Map(tickers.map((t, i) => [t, bt.w[i]]));
      } else viewsInfo = { views: V.info };
    }
  }
  const held = tickers.filter(t => wMap.get(t) > 1e-6);
  const tot = sum(held.map(t => wMap.get(t))); const w = held.map(t => wMap.get(t) / tot);
  const hIdx = held.map(t => tickers.indexOf(t));
  const S = sub(est.sigma, hIdx); const vol = Math.sqrt(quad(S, w));
  if (viewsApplied && calibration) calibration = { ...calibration, applies_to: 'the mix before the view', delivered_vol: Math.round(vol * 1e6) / 1e6, delivered_within_tolerance: Math.abs(vol - tv) <= CAL_TOL };  // as robokit/engine.py
  const muH = hIdx.map(i => est.mu[i]); const modelRet = M.rf + dot(muH, w);
  const Sw = matvec(S, w); const rc = w.map((v, i) => (vol > 0 ? v * Sw[i] / vol ** 2 : 0));
  if (isFixed) { lvl10 = Math.max(2, Math.min(10, 10 * vol / eqVol)); lvl5 = lvl10 / 2; tv = null; src = 'your own weights'; }  // levels run 1-5
  if (isFixed && suit) suitability = suitableLevel(roundHalfUp(lvl5, 1), true)[1];

  for (const t of sats) if (!held.includes(t) && !dropped.includes(t))  // the person's own picks with no weight: say so
    notes.push(isFixed ? note(`${t} has no weight in your own weights. Give it one to hold it.`)
      : note(`${t} is not held: at this level the optimizer gave it no weight. You can set a minimum to hold it anyway.`));

  const geoNet = [], planSrc = {};
  held.forEach((t, k) => {
    const f = M.fund(t); let [a, s] = assumption(M.core, f.asset_class, f.region, M.code);
    if (a == null) a = M.rf + est.mu[hIdx[k]] - 0.5 * est.sigma[hIdx[k]][hIdx[k]];
    geoNet.push(a - (f.mer ?? 0)); planSrc[t] = s;
  });
  const fxLast = M.core.fx.values[M.core.fx.values.length - 1];  // CAD per USD
  const priceIn = (t) => {
    const f = M.fund(t); if (!f || f.last_close == null) return [null, null];
    let px = Number(f.last_close); const c = M.currencyOf(t);
    if (c !== home) px = home === 'CAD' ? px * fxLast : px / fxLast;
    return [px, f.last_close_date || null];
  };
  const sleeveOf = new Map(shelf.map(s => [s.ticker, s]));
  let invested = 0, priced = true;
  const holdings = held.map((t, k) => {
    const f = M.fund(t), sv = sleeveOf.get(t), b = bandMap.get(t);
    const dollars = w[k] * r.amount; const [px, pxDate] = priceIn(t);
    const units = px ? Math.floor(dollars / px + 1e-9) : null;
    if (units == null) priced = false; else invested += units * px;
    return { ticker: t, symbol: f.symbol, name: f.name, role: t === cashT ? 'cash' : (core.includes(t) ? 'core' : 'satellite'),
      sleeve: sv ? sv.sleeve : null, sleeve_label: sv ? sv.label : null,
      plain: sv ? sv.plain : null,
      asset_class: f.asset_class, region: f.region, issuer: f.issuer, weight: round(w[k]), band: b ? [round(b[0]), round(b[1])] : null,
      dollars: round(dollars, 2), price: px == null ? null : round(px, 4), price_date: pxDate, units,
      mer: f.mer, planning_return_net: round(geoNet[k]), planning_source: planSrc[t], model_return: round(M.rf + est.mu[hIdx[k]]),
      volatility: round(Math.sqrt(est.sigma[hIdx[k]][hIdx[k]])), risk_share: round(rc[k]), history_months: f.history_months, aum: f.aum, dollar_volume: f.dollar_volume };
  }).sort((a, b) => b.weight - a.weight);

  const known = held.map(t => M.fund(t).mer).map((m, k) => [m, w[k]]).filter(([m]) => m != null);
  const wmer = known.length ? known.reduce((s, [m, x]) => s + m * x, 0) : null;  // funds with no fee in the data add nothing (said in checks)
  const mixClass = {}, mixRegion = {};
  for (const h of holdings) { mixClass[h.asset_class] = (mixClass[h.asset_class] || 0) + h.weight; mixRegion[h.region] = (mixRegion[h.region] || 0) + h.weight; }
  const sortObj = (o) => Object.fromEntries(Object.entries(o).sort((a, b) => b[1] - a[1]).map(([k, v]) => [k, round(v)]));
  const stress = stressTest(M, held.map((t, k) => [t, w[k]]), full, r.amount);
  // projections resample the longest history every fund has (spliced and back-filled as disclosed),
  // so a bad year reflects 2008 as well as the 15-year estimation window (RESEARCH_LOG section 7)
  const longRows = []; for (let i = 0; i < M.T; i++) if (held.every(t => Number.isFinite(full.get(t)[i]))) longRows.push(i);
  const Xh = longRows.map(i => held.map(t => full.get(t)[i]));
  const proj = project(Xh, w, geoNet, { amount: r.amount, monthly: r.monthly, years: r.years, goal: r.goal });
  proj.history = { start: monthEnd(M.months[longRows[0]]), end: monthEnd(M.months[longRows[longRows.length - 1]]), months: longRows.length };
  const volLong = std(Xh.map(row => dot(row, w))) * Math.sqrt(12);
  const rating = ni81102Rating(Xh.map(row => dot(row, w)));
  for (const rx of relaxations) {  // limits relaxed on request: each one in plain words (never silently)
    const what = rx.limit === 'cap' ? `The limit on ${rx.ticker}` : 'The limit on your own picks together';
    const why = rx.reason === 'minimum' ? 'to hold the minimum you set' : 'so the funds can hold all the money';
    const [before, after] = pctPair(rx.requested, rx.applied);
    notes.push(note(`${what} was raised from ${before} to ${after} ${why}, as you asked.`));
  }
  const out = {
    market: M.code, currency: home, as_of: M.core.meta.prices_through,
    window: { start: M.months[rows[0]], end: M.months[rows[rows.length - 1]], months: rows.length },
    mode: isFixed ? 'own_weights' : 'optimized',
    risk: { level: roundHalfUp(lvl5, 1), label: levelLabel(roundHalfUp(lvl5, 1)), engine_level: round(lvl10, 1),
      risk_share: isFixed ? null : round(riskShare(lvl10)), stock_market_vol: round(eqVol), target_vol: tv == null ? null : round(tv), achieved_vol: round(vol),
      lambda: lam == null ? null : round(lam), calibration, source: src, chosen_level: chosen, cash_cap: cashCap(lvl10), satellite_cap: satCap },
    holdings,
    stats: { volatility: round(vol), volatility_long: round(volLong), ni81_102: rating, planning_return: proj.median_annual_return,
      planning_source: M.code === 'CA' ? 'FP Canada 2026 planning assumptions, after fund fees' : "FP Canada 2026 equity assumptions and today's US Treasury yields, after fund fees",
      model_return: round(modelRet), risk_free: round(M.rf), risk_free_source: M.rfSource, sharpe_model: vol > 0 ? round((modelRet - M.rf) / vol, 3) : null,
      weighted_mer: wmer == null ? null : roundHalfUp(wmer, 6), fee_per_year: wmer == null ? null : roundHalfUp(wmer * r.amount, 2), fee_per_10k: wmer == null ? null : roundHalfUp(wmer * 10000, 2),
      fee_unknown: held.filter(t => M.fund(t).mer == null).map(t => M.fund(t).symbol),
      effective_holdings: round(1 / sum(w.map(x => x * x)), 2), n_holdings: held.length,
      invested: priced ? round(invested, 2) : null, cash_left: priced ? round(r.amount - invested, 2) : null },
    mix: { asset_class: sortObj(mixClass), region: sortObj(mixRegion) },
    stress, projection: proj, views: viewsInfo, history: hist,
    method: { weights: isFixed ? 'your own weights' : 'constrained mean-variance',
      expected_returns_for_weights: viewsApplied ? 'black_litterman (bounded)' : 'equilibrium', delta: DELTA, covariance: est.method, shrinkage: est.shrink == null ? null : round(est.shrink),
      resampled: !!r.resample && r.nBoot > 0 && !isFixed, n_boot: r.resample && r.nBoot > 0 && !isFixed ? r.nBoot : 0, prior: Object.fromEntries(tickers.map((t, i) => [t, round(priorN[i])]).filter(([, v]) => v > 0)), sleeve_caps: caps,
      on_infeasible: r.onInfeasible, relaxations, suitability },
    shelf: shelf.map(s => ({ sleeve: s.sleeve, label: s.label, ticker: s.ticker, alternatives: s.alternatives })),
    notes,
  };
  out.checks = checks(out, X, tickers, r, sats, wmer == null ? null : round(wmer, 5), changed, { fixed: isFixed, lvl5, vol, chosen });
  if (relaxations.length) out.checks.push({ id: 'limits_relaxed', level: 'warn', en: `${relaxations.length} limit(s) were relaxed so these funds could hold all the money; the notes list each one.` });
  out.checks.push(ratingCheck(rating));
  out.explanation = explain(out);
  return out;
}
function monthEnd(ym) { const [y, m] = ym.split('-').map(Number); const d = new Date(Date.UTC(y, m, 0)).getUTCDate(); return `${ym}-${String(d).padStart(2, '0')}`; }

// ------------------------------------------------------------------ a one-fund version at a similar stock share (robokit/engine.py one_fund)
export function oneFundChoice(M, stockShare) {
  if (typeof stockShare !== 'number' || !Number.isFinite(stockShare) || stockShare < 0 || stockShare > 1)  // a share, not a percentage (robokit/engine.py)
    throw inputError(`stock_share must be between 0 and 1 (0.6 for 60%), not ${stockShare}.`, 'stock_share');
  let best = null;
  for (const [t, s] of (M.core.one_fund || {})[M.code] || []) {
    const f = M.fund(t); if (!f || !f.eligible || !M.series.has(t)) continue;
    const key = [Math.round(Math.abs(s - stockShare) * 1e6) / 1e6, f.mer ?? 1];
    if (!best || key[0] < best.key[0] || (key[0] === best.key[0] && key[1] < best.key[1])) best = { key, t, s };
  }
  return best ? [best.t, best.s] : [null, null];
}
export function oneFund(M, stockShare, { amount = 10000, monthly = 0, years = 10 } = {}) {
  const [t, s] = oneFundChoice(M, stockShare); if (!t) return null;
  const p = buildPortfolio(M, { risk_level: null, fixedWeights: { [t]: 1 }, amount, monthly, years, resample: false });
  const h = p.holdings[0];
  return { ticker: t, symbol: h.symbol, name: h.name, stated_stock_share: s, mer: h.mer, volatility: p.stats.volatility, fee_per_year: p.stats.fee_per_year,
    one_year: p.projection.one_year, one_year_dollars: p.projection.one_year_dollars, one_year_value: p.projection.one_year_value,
    stress: p.stress.map(x => ({ key: x.key, scenario: x.scenario, portfolio_return: x.portfolio_return, dollars: x.dollars, estimated: x.estimated, stand_ins: x.stand_ins, not_estimable: x.not_estimable })), history: (p.history || {})[t] || null, window: p.window };
}

// ------------------------------------------------------------------ checks (robokit/engine.py checks)
function checks(p, X, tickers, r, sats, wmer, changed, { fixed = false, lvl5 = null, vol = null, chosen = null } = {}) {
  const out = []; const hold = p.holdings; const top = hold[0];
  const pct = (v, d = 0) => pctTxt(v, d);
  const ccy = p.currency, n0 = (x) => roundHalfUp(x).toLocaleString('en-US');
  out.push({ id: 'concentration', level: top.weight <= 0.5 ? 'info' : 'warn', en: `Largest single fund: ${top.symbol} at ${pct(top.weight)}.` });
  const tk = tickers.filter(t => hold.some(h => h.ticker === t));
  for (let a = 0; a < tk.length; a++) for (let b = a + 1; b < tk.length; b++) {
    const ia = tickers.indexOf(tk[a]), ib = tickers.indexOf(tk[b]);
    const c = pearson(X.map(row => row[ia]), X.map(row => row[ib]));
    if (c > 0.97) {
      const cs = c >= 0.995 ? 'above 0.99' : c.toFixed(2);
      const sa = hold.find(h => h.ticker === tk[a])?.symbol || tk[a], sb = hold.find(h => h.ticker === tk[b])?.symbol || tk[b];
      out.push({ id: 'near_duplicate', level: 'warn', en: `${sa} and ${sb} moved almost identically (correlation ${cs}); holding both adds little diversification.` });
    }
  }
  for (const h of hold) if (h.dollar_volume != null && h.dollar_volume < (p.market === 'CA' ? 100e3 : 1e6))
    out.push({ id: 'liquidity', level: 'warn', en: `${h.symbol} trades about $${n0(h.dollar_volume / 1e3)}K a day. Use limit orders; the bid-ask spread may be wide.` });
  if (wmer != null) {
    const g = Math.max(p.stats.planning_return, 0);
    for (const yrs of [10, 25]) {
      const cost = r.amount * (1 + g + wmer) ** yrs - r.amount * (1 + g) ** yrs;
      const wd = r.monthly < 0;  // withdrawals shrink the balance, so this overstates the cost
      out.push({ id: `fee_drag_${yrs}`, level: 'info', en: `Over ${yrs} years, fund fees of ${pctTxt(wmer, 2)} a year would cost about $${n0(cost)} ${ccy} on $${n0(r.amount)} ${ccy} (at the planning return).` + (wd ? ' Withdrawals make the balance smaller, so the real cost is lower.' : '') });
    }
  }
  const unknown = hold.filter(h => h.mer == null).map(h => h.symbol);
  if (unknown.length) out.push({ id: 'fee_unknown', level: 'info', en: `Fee not in the data for ${unknown.join(', ')}; the fee figures leave it out, so the real total is a little higher.` });
  for (const h of hold) if (h.role === 'satellite' && (h.asset_class === 'Crypto' || h.asset_class === 'Alternative')) {
    const capEn = fixed ? `It is ${pct(h.weight)} of your weights.` : 'It is capped at a small weight.';
    out.push({ id: 'complex_product', level: 'warn', en: `${h.symbol} is a ${h.asset_class.toLowerCase()} fund: harder to understand and more likely to behave unexpectedly. ${capEn}` });
  }
  if (fixed && lvl5 != null) {
    const off = chosen != null && Math.abs(lvl5 - chosen) >= 1;
    out.push({ id: 'own_weights', level: off ? 'warn' : 'info',
      en: `Your own weights, not the model's: they swing like level ${roundHalfUp(lvl5, 1).toFixed(1)} (volatility ${pctTxt(vol, 1)} a year).` + (off ? (r.levelChosen === false ? ` That is not level ${chosen}, the reference level.` : ` That is not level ${chosen}, the level you chose.`) : '') });
  }
  if (changed || sats.length) out.push({ id: 'reference', level: 'info', en: 'You changed the reference fund list. Compare with the reference mix at the same level to see what your changes cost or add.' });
  return out;
}

// ------------------------------------------------------------------ explanations (robokit/explain.py)
const money = (x, ccy) => `$${roundHalfUp(x).toLocaleString('en-US')} ${ccy}`;
const pctS = (x, d = 0) => pctTxt(x, d);
export function explain(p) {
  const s = p.stats, r = p.risk, ccy = p.currency, pr = p.projection || {}, amt = pr.amount ?? 10000; const en = [];
  const mix = Object.entries(p.mix.asset_class).filter(([, v]) => v >= 0.005);
  en.push(`The mix: ${mix.map(([k, v]) => `${pctS(v)} ${k.toLowerCase()}`).join(', ')}, spread over ${s.n_holdings} funds.`);  // each a rounded computed share
  if (r.risk_share == null) {
    en.push(`These are your own weights, not the model's. They swing about ${pctS(s.volatility, 1)} a year, like level ${r.level} of 5.`);
  } else {
    if (r.target_vol != null && Math.abs(r.target_vol - s.volatility) >= 0.002) {  // the target was not reached: say both
      en.push(`Level ${r.level} of 5 (${r.label.toLowerCase()}) aims for about ${pctS(r.risk_share)} of the stock market's ups and downs, a volatility of about ${pctS(r.target_vol, 1)} a year; with these funds the mix gets to about ${pctS(s.volatility, 1)}.`);
    } else {
      en.push(`Level ${r.level} of 5 (${r.label.toLowerCase()}) aims for about ${pctS(r.risk_share)} of the stock market's ups and downs. For these funds that is a volatility of about ${pctS(s.volatility, 1)} a year.`);
    }
  }
  const one = pr.one_year, val = pr.one_year_value, mo = pr.monthly_contribution || 0;
  if (one && val && mo) {  // year-end values with the monthly adds or withdrawals, as the page's headline shows them
    const flowEn = mo > 0 ? `plus ${money(mo, ccy)} a month` : `with ${money(-mo, ccy)} a month taken out`;
    en.push(`In 8 years out of 10, ${money(amt, ccy)} ${flowEn} might end the year between ${money(val.p10, ccy)} and ${money(val.p90, ccy)}. In a bad year (about 1 in 20) it could end the year at about ${money(val.p5, ccy)}. These are ranges, not promises.`);
  } else if (one) {
    en.push(`In 8 years out of 10, ${money(amt, ccy)} might end the year between ${money(amt * (1 + one.p10), ccy)} and ${money(amt * (1 + one.p90), ccy)}. In a bad year (about 1 in 20) it could fall to about ${money(amt * (1 + one.p5), ccy)}. These are ranges, not promises.`);
  }
  en.push(`Using published planning assumptions after fees, a middle outcome is about ${pctS(s.planning_return, 1)} a year over ${pr.years ?? 10} ${(pr.years ?? 10) === 1 ? 'year' : 'years'}; cash pays about ${pctS(s.risk_free, 1)} today.`);
  if (s.weighted_mer != null) {
    en.push(`Fund fees average ${pctS(s.weighted_mer, 2)} a year: about ${money(s.fee_per_year, ccy)} a year on ${money(amt, ccy)}.`);
  }
  const topRisk = p.holdings.reduce((a, b) => (b.risk_share > a.risk_share ? b : a));
  if (roundHalfUp(topRisk.risk_share * 100) > roundHalfUp(topRisk.weight * 100) + 2) {
    en.push(`${topRisk.symbol} is ${pctS(topRisk.weight)} of the money but ${pctS(topRisk.risk_share)} of the risk: the fund that swings most drives most of the ups and downs.`);
  } else {
    en.push(`${topRisk.symbol} is ${pctS(topRisk.weight)} of the money and ${pctS(topRisk.risk_share)} of the risk: the largest source of ups and downs, in line with its size.`);
  }
  const shown = (p.stress || []).filter(x => x.portfolio_return != null), missing = (p.stress || []).filter(x => x.portfolio_return == null);
  if (shown.length) {
    const worst = shown.reduce((a, b) => (b.portfolio_return < a.portfolio_return ? b : a));
    const d = worst.dollars;
    en.push(`Replaying the ${worst.scenario}, this mix would have fallen about ${pctS(-worst.portfolio_return)}` + (d != null && d < 0 ? ` (about ${money(-d, ccy)} on ${money(amt, ccy)})` : '') + ' before recovering.');
  }
  if (missing.length) {
    const funds = [...new Set(missing.flatMap(x => x.not_estimable || []).map(t => t.replace(/\.(TO|NE)$/, '')))].sort();
    en.push(`${missing.map(x => x.scenario).join(', ')}: not shown, because ${funds.join(', ')} has no history or stand-in for that period.`);
  }
  return { en };
}

// ------------------------------------------------------------------ profile scoring (robokit/profile.py score)
export function scoreProfile(items, answers, { assumed = [] } = {}) {
  // port of robokit/profile.py score(): same rules, same wording, same fields (assumed: answers filled in from another answer)
  const a = {}; for (const [k, v] of Object.entries(answers || {})) if (v != null && v !== '') a[k] = v;
  const item = (id) => items.find(x => x.id === id);
  const opt = (id, v) => { const it = item(id); const o = it && it.options.find(o => o.value === String(v)); if (!o) throw new Error(`${id}: unknown answer ${v}`); return o; };
  for (const [k, v] of Object.entries(a)) { const it = item(k); if (it && it.options && it.options.length) opt(k, v); }
  const has = (k) => k in a;
  const ia = (id, v) => { const it = item(id), o = opt(id, v); return { id, question_en: it.text, answer_en: o.text }; };
  const gates = [], flags = [], whyEn = [];
  const b2Asked = has('B2') && a.A1 !== 'wealth';  // no withdrawal date: an old B2 answer no longer counts
  const b2 = b2Asked ? a.B2 : (a.A1 === 'wealth' ? 'unsure' : null);

  const g1 = a.B1 === 'lt2' && b2 === 'once';
  if (g1) gates.push({ id: 'G1', en: 'You need all of this money within two years. Money like that usually sits in cash-like savings, so Robo-Kit will not build a stock mix for it.' });
  let gateCap = 5;
  if (a.A2 === 'no') { gateCap = 2; gates.push({ id: 'G2', en: 'First things first: an emergency fund of 3 to 6 months of expenses usually comes before investing. Until then, Robo-Kit builds at most level 2.' }); }
  if (a.A3 === 'lot') { gateCap = 2; gates.push({ id: 'G3', en: "Paying off high-interest debt is often a better 'return' than investing. Until then, Robo-Kit builds at most level 2." }); }
  if (g1) gateCap = 1;

  const missing = ['B1', 'B2', 'B4', 'B5', 'C1', 'C2', 'C3', 'C4'].filter(k => !has(k) && !(k === 'B2' && b2 != null));
  let capacity = null; const capItems = [];
  if (has('B1') && b2 != null) {
    const b1o = opt('B1', a.B1), b2o = opt('B2', b2);
    const H = b1o.pts + b2o.pts;
    const base = H <= 2 ? 1 : H <= 5 ? 2 : H <= 9 ? 3 : H <= 12 ? 4 : 5;
    const howEn = b2Asked ? b2o.text.toLowerCase() + (assumed.includes('B2') ? ', assumed from your goal' : '') : 'not asked (no fixed date)';
    whyEn.push(`Time horizon (start taking money out: ${b1o.text.toLowerCase()}; for how long: ${howEn}) allows up to level ${base}.`);
    capItems.push({ ...ia('B1', a.B1), effect_en: `allows up to level ${base}` });
    if (b2Asked) capItems.push({ ...ia('B2', b2), effect_en: `allows up to level ${base}` });
    const cushions = [];
    if (has('B4') && opt('B4', a.B4).pts <= 1) cushions.push(['B4', 'this money is most of your savings']);
    if (has('B5') && opt('B5', a.B5).pts <= 1) cushions.push(['B5', 'your income is uneven']);
    if (a.A2 === 'partly') cushions.push(['A2', 'your emergency savings are partial']);
    const steps = Math.min(cushions.length, H >= 13 ? 1 : 2);
    if (steps) {
      const nEn = steps === 1 ? 'one step' : 'two steps';
      const names = cushions.map(c => c[1]);
      const listed = names.length === 1 ? names[0] : names.slice(0, -1).join(', ') + ' and ' + names[names.length - 1];
      const both = cushions.length > 1;
      whyEn.push(`Because ${listed}: ${both ? 'together, ' : ''}${nEn} lower.`);
      for (const [cid] of cushions) capItems.push({ ...ia(cid, a[cid]), lowers: true, effect_en: both ? `together with the others, ${nEn} lower` : `${nEn} lower` });
    }
    capacity = Math.max(1, base - steps);
    if (a.B1 === 'lt2' && !g1) { whyEn.push('Keeping the next 1 to 2 years of withdrawals in cash-like savings is a common approach.'); }
  }

  const tol = {}; for (const k of ['C0', 'C1', 'C2', 'C3', 'C4']) if (has(k)) tol[k] = Number(opt(k, a[k]).level);
  let tolerance = null; const vals = Object.values(tol);
  if (vals.length) {
    tolerance = Math.max(1, Math.floor(vals.reduce((s, v) => s + v, 0) / vals.length));
    if (vals.length >= 3 && Math.max(...vals) - Math.min(...vals) >= 3) {
      tolerance = Math.max(1, tolerance - 1);
      flags.push({ id: 'F_inconsistent', en: 'Two of your answers point different ways: one says you are fine with big swings, another that you would pull back after a drop. Which is closer to you?', items: Object.keys(tol).filter(k => tol[k] === Math.max(...vals) || tol[k] === Math.min(...vals)) });
    }
    if (a.C2 === 'sell_all' && (tol.C1 || 0) >= 5) flags.push({ id: 'F_drop_vs_range', en: 'You chose the widest one-year range but would sell everything after a sharp fall. Selling at the bottom locks in the loss; which answer fits you better?', items: ['C1', 'C2'] });
    // the conversation script's second chance: the self-rating and the reaction to a drop point different ways
    const dropFeel = { sell_all: 'lower', sell_some: 'lower', wait: 'medium', buy: 'higher' }[a.C2], selfFeel = { low: 'lower', medium: 'medium', high: 'higher' }[a.C0];
    if (dropFeel && selfFeel && dropFeel !== selfFeel) flags.push({ id: 'F_self_vs_drop', en: `You rated your comfort with risk as ${a.C0}, but chose "${opt('C2', a.C2).text}" after a sharp fall, which usually signals ${dropFeel} risk tolerance. This gap between how people rate themselves and how they actually react is common. Which feels more accurate: your self-rating or your reaction to the drop?`, items: ['C0', 'C2'] });
    whyEn.push(`Your answers about ups and downs point to level ${tolerance}.`);
  }
  const low = vals.length ? Math.min(...vals) : null;
  const tolItems = Object.keys(tol).filter(k => tol[k] === low).map(k => ({ ...ia(k, a[k]), effect_en: `points to level ${tol[k]}` }));

  const know = {}; for (const k of ['D1', 'D2']) if (has(k)) know[k] = !!opt(k, a[k]).correct;
  if (Object.keys(know).length && !Object.values(know).some(Boolean) && (tolerance || 0) >= 4) flags.push({ id: 'F_knowledge', en: 'You are comfortable with a lot of risk, and the two quiz questions were new to you. Want a quick explanation of bond prices and leveraged funds before choosing?', items: ['D1', 'D2'] });
  if ((tolerance || 0) >= 4 && gates.some(g => g.id === 'G2' || g.id === 'G3')) flags.push({ id: 'F_gate_vs_tolerance', en: 'You are comfortable with risk, but your savings cushion or debt limits how much risk your situation can take right now.', items: ['A2', 'A3'] });
  const gateItems = [['A2', 'no'], ['A3', 'lot']].filter(([g, v]) => a[g] === v).map(([g]) => ({ ...ia(g, a[g]), effect_en: 'keeps the build at level 2 or below' }));

  const explanation = { en: whyEn };
  const L = (l) => (l ? LEVEL_NAMES[l] : null);
  const upTo = (n) => Array.from({ length: n }, (_, i) => i + 1);
  const choose = upTo(gateCap);
  if (g1) return { status: 'not_ready', suggested_level: 1, label: L(1), capacity, tolerance, binding: 'time horizon', gates, flags, missing, knowledge: know, can_choose: [1], explanation, gate_cap: 1, within_check: [1], binding_answers: [ia('B1', a.B1), ia('B2', b2)], capacity_answers: capItems };
  if (capacity == null || tolerance == null) {
    const l = (capacity || tolerance) ? Math.min(capacity || tolerance, gateCap) : null;
    return { status: 'incomplete', suggested_level: l, label: L(l), capacity, tolerance, binding: null, gates, flags, missing, knowledge: know, can_choose: choose, explanation, gate_cap: gateCap, within_check: upTo(Math.min(capacity || 5, gateCap)), binding_answers: gateItems, capacity_answers: capItems };
  }
  const level = Math.min(capacity, tolerance, gateCap);
  let binding, bindItems;
  if (gateCap < Math.min(capacity, tolerance)) {
    binding = 'gate'; bindItems = gateItems;
    whyEn.push(`Your savings cushion or debt answer keeps the build at level ${gateCap} for now.`);
  } else {
    binding = capacity < tolerance ? 'capacity' : tolerance < capacity ? 'tolerance' : 'both';
    bindItems = binding === 'capacity' ? capItems : binding === 'tolerance' ? tolItems : [...capItems, ...tolItems];
  }
  if (capacity === tolerance && binding !== 'gate') { whyEn.push(`Suggested: level ${level}, ${LEVEL_NAMES[level]}. Both point there.`); }
  else { whyEn.push(`Suggested: the lower of the two, level ${level}, ${LEVEL_NAMES[level]}.`); }
  return { status: 'complete', suggested_level: level, label: LEVEL_NAMES[level], capacity, tolerance, binding, gates, flags, missing, knowledge: know, can_choose: choose, explanation, gate_cap: gateCap, within_check: upTo(Math.min(capacity, gateCap)), binding_answers: bindItems, capacity_answers: capItems };
}

// ------------------------------------------------------------------ search, profile, trend (robokit/tools.py, signals.py)
export function searchFunds(M, { query = '', assetClass = null, region = null, theme = null, maxMer = null, minAum = null, eligibleOnly = true, esgOnly = false, hedged = null, sortBy = 'mer', limit = 25 } = {}) {
  let u = M.rows;
  if (eligibleOnly) u = u.filter(r => r.eligible);
  if (query) { const q = query.toLowerCase(); u = u.filter(r => (r.name || '').toLowerCase().includes(q) || (r.symbol || '').toLowerCase() === q || r.yahoo.toLowerCase() === q || (r.theme || '').toLowerCase().includes(q) || (r.issuer || '').toLowerCase().includes(q)); }
  if (assetClass) u = u.filter(r => r.asset_class === assetClass);
  if (region) u = u.filter(r => r.region === region);
  if (theme) u = u.filter(r => (r.theme || '').toLowerCase().includes(theme.toLowerCase()));
  if (maxMer != null) u = u.filter(r => r.mer != null && r.mer <= maxMer);
  if (minAum != null) u = u.filter(r => r.aum != null && r.aum >= minAum);
  if (esgOnly) u = u.filter(r => r.esg);
  if (hedged != null) u = u.filter(r => r.hedged === hedged);
  const keys = { mer: ['mer', 1], aum: ['aum', -1], history: ['history_months', -1], name: ['name', 1] };  // as robokit/tools.py search_etfs
  if (!(sortBy in keys)) throw inputError(`sort_by must be one of ${Object.keys(keys).join(', ')}; got '${sortBy}'.`, 'sort_by');
  if (!Number.isInteger(limit) || limit < 1) throw inputError(`limit must be a whole number of at least 1, not ${limit}.`, 'limit');
  const key = keys[sortBy];
  u = [...u].sort((a, b) => { const x = a[key[0]], y = b[key[0]]; if (x == null) return 1; if (y == null) return -1; return (x > y ? 1 : x < y ? -1 : 0) * key[1]; });
  return { market: M.code, matches: u.length, shown: Math.min(limit, u.length), sorted_by: sortBy, results: u.slice(0, limit), as_of: M.core.meta.prices_through };
}

export function trendState(M, t) {
  const r = M.returns(t); if (!r) return null;
  const idxs = []; for (let i = 0; i < M.T; i++) if (Number.isFinite(r[i])) idxs.push(i);
  if (idxs.length < 13) return null;
  const lvl = []; let c = 1; for (const i of idxs) { c *= 1 + r[i]; lvl.push(c); }
  const L = lvl.length; const sma = mean(lvl.slice(L - 10)); const above = lvl[L - 1] >= sma;
  const mom = lvl[L - 2] / lvl[L - 13] - 1; const dd = lvl[L - 1] / Math.max(...lvl) - 1;
  return { ticker: t, as_of: M.months[idxs[idxs.length - 1]], above_10m_average: above, return_12_1: round(mom), drawdown_from_peak: round(dd), reading: `${above ? 'above' : 'below'} its 10-month average` };
}
