// Parity test: the browser engine (web/robokit.js) against the Python engine (reference cases in web/data/core.json).
// Run: node web/test_robokit.mjs
import { readFileSync } from 'node:fs';
import { Market, buildPortfolio, scoreProfile, oneFund, rebalance } from './robokit.js';
import { mulberry32, qis } from './engine.js';

const here = new URL('.', import.meta.url);
const core = JSON.parse(readFileSync(new URL('data/core.json', here)));
const mk = { CA: new Market(core, JSON.parse(readFileSync(new URL('data/ca.json', here)))), US: new Market(core, JSON.parse(readFileSync(new URL('data/us.json', here)))) };
let fails = 0;
// at a jump of the minimum-position rule the last bisection step depends on the 15th digit of log(lambda): one more
// or fewer evaluation, the same side of the jump
const sameSteps = (x, y) => x.outcome === y.outcome && (x.outcome === 'jump' ? Math.abs(x.evaluations - y.evaluations) <= 2 : x.evaluations === y.evaluations);
for (const c of core.reference_cases) {
  const q = c.request; const t0 = Date.now();
  const p = buildPortfolio(mk[q.market], { risk_level: q.risk_level, satellites: q.satellites || [], views: q.views || [], swaps: q.swaps || {}, hedgeUsEquity: !!q.hedge_us_equity, fixedWeights: q.fixed_weights || null, minimums: q.minimums || {}, maxWeight: q.max_weight ?? 0.5, onInfeasible: q.on_infeasible || 'refuse', answers: q.answers ?? null, enforceSuitability: !!q.enforce_suitability, acknowledgedAboveSuggestion: !!q.acknowledged_above_suggestion, sleeves: q.sleeves ?? null, minWeight: q.min_weight ?? 0.02, satelliteMaxEach: q.satellite_max_each ?? 0.10, ...(q.target_vol != null ? { targetVol: q.target_vol } : {}), resample: false });
  const js = Object.fromEntries(p.holdings.map(h => [h.ticker, h.weight]));
  const keys = new Set([...Object.keys(js), ...Object.keys(c.weights)]);
  let maxd = 0; for (const k of keys) maxd = Math.max(maxd, Math.abs((js[k] || 0) - (c.weights[k] || 0)));
  const dv = Math.abs(p.stats.volatility - c.volatility);
  let ds = 0;
  if (c.stress) {  // a crisis row that cannot be estimated is null in both engines
    for (const s of p.stress) { const py = c.stress[s.scenario]; if (py === undefined || (py === null) !== (s.portfolio_return === null)) { ds = Infinity; continue; } if (py !== null) ds = Math.max(ds, Math.abs(s.portfolio_return - py)); }
    if (p.stress.length !== Object.keys(c.stress).length) ds = Infinity;
  }
  // near-duplicate funds (VOO and IVV) split by differences below the solver's tolerance: one engine may give a twin a
  // sliver it then drops as small, the other exactly zero. Same funds unheld either way; other notes must match exactly.
  const unheld = (ns) => { const out = new Set(), rest = [];
    for (const n of ns) { const m = n.en.match(/^Dropped because each would have held less than [0-9.]+%: (.*)\. The other/); const z = n.en.match(/^(\S+) is not held: at this level the optimizer gave it no weight/);
      if (m) m[1].split(', ').forEach(t => out.add(t)); else if (z) out.add(z[1]); else rest.push(n.en); }
    return JSON.stringify([[...out].sort(), rest]); };
  const sameNotes = !c.notes || JSON.stringify(p.notes) === JSON.stringify(c.notes) || (c.checks.includes('near_duplicate') && unheld(p.notes) === unheld(c.notes));
  const sameChecks = !c.checks || JSON.stringify(p.checks.map(x => x.id)) === JSON.stringify(c.checks);
  // final-pipeline calibration: the same number of steps and the same volatility reached (null for own weights)
  const pc = p.risk.calibration, cc = c.calibration;
  const sameCal = (pc == null) === (cc == null) && (pc == null || (sameSteps(pc, cc) && Math.abs(pc.achieved_vol - cc.achieved_vol) <= 1e-4 && pc.within_tolerance === cc.within_tolerance));
  const sameRating = !c.ni81_102 || (p.stats.ni81_102.rating === c.ni81_102.rating && Math.abs(p.stats.ni81_102.std_10y - c.ni81_102.std_10y) <= 1e-4 + 1e-12 && p.stats.ni81_102.months === c.ni81_102.months);
  const ok = maxd <= 2e-3 && dv <= 1e-3 && p.window.months === c.window.months && ds <= 2e-3 && sameNotes && sameChecks && sameCal && sameRating;
  if (!ok) fails++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${JSON.stringify(q)}  max|dw|=${maxd.toExponential(2)}  dvol=${dv.toExponential(2)}  dstress=${ds.toExponential(2)}  window ${p.window.months}/${c.window.months}  ${Date.now() - t0} ms`);
  if (!ok) console.log('   js', js, p.notes, p.checks.map(x => x.id), '\n   py', c.weights, c.notes, c.checks);
}
// resampled builds with projections: the engines share one random generator, so these agree to rounding
const jsReq = (q) => ({ risk_level: q.risk_level, satellites: q.satellites || [], views: q.views || [], amount: q.amount ?? 10000, monthly: q.monthly_contribution ?? 0, years: q.years ?? 10, goal: q.goal ?? null });
const relGap = (a, b) => Math.abs(a - b) / Math.max(1, Math.abs(b));
for (const c of core.resampled_cases || []) {
  const q = c.request; const t0 = Date.now();
  const p = buildPortfolio(mk[q.market], jsReq(q));
  const js = Object.fromEntries(p.holdings.map(h => [h.ticker, h])); let maxd = 0, maxb = 0;
  for (const k of new Set([...Object.keys(js), ...Object.keys(c.weights)])) {
    maxd = Math.max(maxd, Math.abs((js[k]?.weight || 0) - (c.weights[k] || 0)));
    const bj = js[k]?.band, bp = c.bands[k]; if (bj && bp) maxb = Math.max(maxb, Math.abs(bj[0] - bp[0]), Math.abs(bj[1] - bp[1])); else if (!!bj !== !!bp) maxb = Infinity;
  }
  const P = p.projection, C = c.projection; let dr = 0, dm = 0;  // dr: largest gap in a return or a chance; dm: largest relative gap in money
  for (const k of ['p5', 'p10', 'p50', 'p90', 'prob_loss']) dr = Math.max(dr, Math.abs(P.one_year[k] - C.one_year[k]));
  for (const y of C.yearly) { const z = P.yearly.find(v => v.year === y.year); for (const k of ['p10', 'p50', 'p90']) dm = Math.max(dm, z ? relGap(z[k], y[k]) : Infinity); }
  for (const h of C.by_holding_period) { const z = P.by_holding_period.find(v => v.years === h.years); for (const k of ['p10', 'p50', 'p90']) dr = Math.max(dr, z ? Math.abs(z[k] - h[k]) : Infinity); }
  if (C.chance_need_to_adjust != null) dr = Math.max(dr, Math.abs(P.chance_need_to_adjust - C.chance_need_to_adjust));
  if (C.withdrawal) dr = Math.max(dr, Math.abs(P.withdrawal.chance_lasts - C.withdrawal.chance_lasts), Math.abs(P.withdrawal.p50_months - C.withdrawal.p50_months) / C.withdrawal.months);
  const pc = p.risk.calibration, cc = c.calibration;
  const sameCal = sameSteps(pc, cc) && Math.abs(pc.achieved_vol - cc.achieved_vol) <= 1e-4 && pc.within_tolerance === cc.within_tolerance;
  const ok = maxd <= 2e-3 && maxb <= 5e-3 && Math.abs(p.stats.volatility - c.volatility) <= 1e-3 && dr <= 5e-3 && dm <= 5e-3 && sameCal;
  if (!ok) fails++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} resampled ${JSON.stringify(q)}  max|dw|=${maxd.toExponential(2)}  max|dband|=${maxb.toExponential(2)}  projection: returns ${dr.toExponential(2)}, money ${dm.toExponential(2)}  ${Date.now() - t0} ms`);
}
// QIS on the same generated inputs as Python (robokit/bundle.py qis_checks)
for (const c of core.qis_checks || []) {
  const r = mulberry32(c.seed); const X = Array.from({ length: c.t }, () => Array.from({ length: c.n }, () => (r() - 0.5) * 0.1));
  const S = qis(X); let md = 0, mx = 0;
  for (let i = 0; i < c.n; i++) for (let j = 0; j < c.n; j++) { md = Math.max(md, Math.abs(S[i][j] - c.sigma[i][j])); mx = Math.max(mx, Math.abs(c.sigma[i][j])); }
  const ok = md / mx < 1e-10; if (!ok) fails++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} QIS T=${c.t} N=${c.n}  max|dSigma|/max|Sigma| = ${(md / mx).toExponential(2)}`);
}
// rebalancer: the same orders as Python on hand-made and seeded random accounts (robokit/bundle.py rebalance_cases)
const camel = { cash: 'cash', flow: 'flow', min_trade: 'minTrade', cash_reserve: 'cashReserve', whole_units: 'wholeUnits', adv: 'adv' };
let rb = 0, rbn = 0;
for (const c of core.rebalance_cases || []) {
  rbn++;
  const o = Object.fromEntries(Object.entries(c.opts).map(([k, v]) => [camel[k], v])); let res;
  try { res = rebalance(c.targets, c.units, c.prices, o); } catch (e) { res = { error: e.message }; }
  const P = c.result; let ok;
  if (P.error || res.error) ok = P.error === res.error;
  else ok = res.rows.length === P.rows.length && res.rows.every((x, i) => x.ticker === P.rows[i].ticker && x.action === P.rows[i].action && Math.abs(x.units - P.rows[i].units) < 1e-9
    && JSON.stringify(x.reason) === JSON.stringify(P.rows[i].reason) && (x.liquidity_flag ?? null) === (P.rows[i].liquidity_flag ?? null))
    && Math.abs(res.cash_after - P.cash_after) <= 0.011 && Math.abs(res.traded - P.traded) <= 0.011 && JSON.stringify(res.notes) === JSON.stringify(P.notes);
  if (!ok) { rb++; if (rb <= 3) console.log('   rebalance differs', JSON.stringify(c).slice(0, 300), '\n   js', JSON.stringify(res).slice(0, 600), '\n   py', JSON.stringify(P).slice(0, 600)); }
}
console.log(`${rb ? 'FAIL' : 'ok  '} rebalancer on ${rbn} accounts, ${rb} differ`); if (rb) fails++;
// profile scorer: every Python-scored random answer set must come out identical
const canon = (o) => JSON.stringify(o, (k, v) => (v && typeof v === 'object' && !Array.isArray(v) ? Object.fromEntries(Object.keys(v).sort().map(x => [x, v[x]])) : v));
let pf = 0;
const profiles = JSON.parse(readFileSync(new URL('test_profiles.json', here)));
for (const c of profiles) { const js = scoreProfile(core.questions, c.answers); if (canon(js) !== canon(c.result)) { pf++; if (pf <= 3) console.log('   profile differs', JSON.stringify(c.answers), '\n   js', canon(js).slice(0, 600), '\n   py', canon(c.result).slice(0, 600)); } }
console.log(`${pf ? 'FAIL' : 'ok  '} profile scorer on ${profiles.length} random answer sets, ${pf} differ`); if (pf) fails++;
// one-fund benchmark: an 80% stock asset-allocation ETF in each market
for (const [code, share] of [['CA', 0.8], ['US', 0.6]]) { const o = oneFund(mk[code], share, { amount: 50000 }); const okO = o && o.stress.length > 0 && o.volatility > 0; console.log(`${okO ? 'ok  ' : 'FAIL'} one-fund ${code} ${share}: ${o && o.ticker} vol ${o && o.volatility} replays ${o && o.stress.length}`); if (!okO) fails++; }
// profile scorer: a few answer sets
const P = scoreProfile(core.questions, { A2: 'yes', A3: 'no', B1: '10to19', B2: '10plus', B4: '10to25', B5: 'mostly', C1: '4', C2: 'wait', C3: '3', C4: 'both' });
const okP = P.status === 'complete' && P.suggested_level === 3 && P.capacity === 5 && P.tolerance === 3;
console.log(`${okP ? 'ok  ' : 'FAIL'} profile scorer`, P.suggested_level, P.capacity, P.tolerance); if (!okP) fails++;
process.exit(fails ? 1 : 0);
