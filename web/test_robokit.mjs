// Parity test: the browser engine (web/robokit.js) against the Python engine (reference cases in web/data/core.json).
// Run: node web/test_robokit.mjs
import { readFileSync } from 'node:fs';
import { Market, buildPortfolio, scoreProfile, oneFund } from './robokit.js';

const here = new URL('.', import.meta.url);
const core = JSON.parse(readFileSync(new URL('data/core.json', here)));
const mk = { CA: new Market(core, JSON.parse(readFileSync(new URL('data/ca.json', here)))), US: new Market(core, JSON.parse(readFileSync(new URL('data/us.json', here)))) };
let fails = 0;
for (const c of core.reference_cases) {
  const q = c.request; const t0 = Date.now();
  const p = buildPortfolio(mk[q.market], { risk_level: q.risk_level, satellites: q.satellites || [], views: q.views || [], swaps: q.swaps || {}, hedgeUsEquity: !!q.hedge_us_equity, fixedWeights: q.fixed_weights || null, minimums: q.minimums || {}, resample: false });
  const js = Object.fromEntries(p.holdings.map(h => [h.ticker, h.weight]));
  const keys = new Set([...Object.keys(js), ...Object.keys(c.weights)]);
  let maxd = 0; for (const k of keys) maxd = Math.max(maxd, Math.abs((js[k] || 0) - (c.weights[k] || 0)));
  const dv = Math.abs(p.stats.volatility - c.volatility);
  let ds = 0;
  if (c.stress) {  // a crisis row that cannot be estimated is null in both engines
    for (const s of p.stress) { const py = c.stress[s.scenario]; if (py === undefined || (py === null) !== (s.portfolio_return === null)) { ds = Infinity; continue; } if (py !== null) ds = Math.max(ds, Math.abs(s.portfolio_return - py)); }
    if (p.stress.length !== Object.keys(c.stress).length) ds = Infinity;
  }
  const sameNotes = !c.notes || JSON.stringify(p.notes) === JSON.stringify(c.notes);
  const sameChecks = !c.checks || JSON.stringify(p.checks.map(x => x.id)) === JSON.stringify(c.checks);
  const ok = maxd <= 2e-3 && dv <= 1e-3 && p.window.months === c.window.months && ds <= 2e-3 && sameNotes && sameChecks;
  if (!ok) fails++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${JSON.stringify(q)}  max|dw|=${maxd.toExponential(2)}  dvol=${dv.toExponential(2)}  dstress=${ds.toExponential(2)}  window ${p.window.months}/${c.window.months}  ${Date.now() - t0} ms`);
  if (!ok) console.log('   js', js, p.notes, p.checks.map(x => x.id), '\n   py', c.weights, c.notes, c.checks);
}
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
// resampled run: sums to one, bands present, timing
const t1 = Date.now(); const R = buildPortfolio(mk.CA, { risk_level: 3, nBoot: 200 });
const s = R.holdings.reduce((a, h) => a + h.weight, 0);
console.log(`${Math.abs(s - 1) < 1e-3 && R.holdings.every(h => h.band) ? 'ok  ' : 'FAIL'} resampled CA level 3 in ${Date.now() - t1} ms, sum ${s.toFixed(4)}`);
process.exit(fails ? 1 : 0);
