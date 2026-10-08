// v3 safety in the browser engine: the same refusals and records as tests/test_v3_safety.py.
// Run: node web/test_safety.mjs
import { readFileSync } from 'node:fs';
import { Market, buildPortfolio, levelLabel, RoboKitError } from './robokit.js';

const here = new URL('.', import.meta.url);
const core = JSON.parse(readFileSync(new URL('data/core.json', here)));
const CA = new Market(core, JSON.parse(readFileSync(new URL('data/ca.json', here))));
let fails = 0;
const check = (ok, label, extra = '') => { console.log(`${ok ? 'ok  ' : 'FAIL'} ${label}${extra ? '  ' + extra : ''}`); if (!ok) fails++; };
const build = (req) => buildPortfolio(CA, { resample: false, ...req });
const throwsKind = (req, kind) => { try { build(req); return false; } catch (e) { return e instanceof RoboKitError && e.kind === kind; } };

// A1 validation: nothing is silently clamped
for (const [field, req] of [
  ['risk_level NaN', { risk_level: NaN }], ['risk_level 7', { risk_level: 7 }], ['risk_level 0', { risk_level: 0 }],
  ['target_vol 0', { targetVol: 0 }], ['target_vol NaN', { targetVol: NaN }], ['years 0', { years: 0 }], ['years 2.5', { years: 2.5 }],
  ['amount -1', { amount: -1 }], ['max_weight 0', { maxWeight: 0 }], ['min_weight 0.5', { minWeight: 0.5 }],
  ['minimums 120%', { minimums: { 'XIC.TO': 0.6, 'VFV.TO': 0.6 } }], ['minimum on excluded', { minimums: { 'XIC.TO': 0.1 }, exclude: ['XIC.TO'] }],
  ['on_infeasible', { onInfeasible: 'ignore' }],
]) check(throwsKind(req, 'input'), `refuses ${field}`);

// A2 labels: halves round up, always 1-5
for (const [lvl, label] of [[0.5, 'Conservative'], [1.5, 'Cautious'], [2.5, 'Balanced'], [4.5, 'Aggressive growth'], [5, 'Aggressive growth']])
  check(levelLabel(lvl) === label, `label ${lvl} -> ${label}`);
const eq = build({ risk_level: 3 }).risk.stock_market_vol;
for (const tv of [0.05 * eq, 0.0053, 0.5 * eq]) { const p = build({ targetVol: tv }); check(['Conservative', 'Balanced'].includes(p.risk.label), `target vol ${tv.toFixed(4)} builds with a label`, p.risk.label); }

// A3 infeasible limits: refuse by default, relax only on request and record each step
check(throwsKind({ risk_level: 3, maxWeight: 0.05 }, 'infeasible'), 'caps below 100% are refused');
{
  const p = build({ risk_level: 3, maxWeight: 0.05, onInfeasible: 'relax' });
  const rel = p.method.relaxations; const applied = Object.fromEntries(rel.filter(x => x.limit === 'cap').map(x => [x.ticker, x.applied]));
  const within = p.holdings.every(h => applied[h.ticker] == null || h.weight <= applied[h.ticker] + 2e-4);
  check(rel.length > 0 && within && p.checks.some(c => c.id === 'limits_relaxed') && p.notes.some(n => n.en.includes('was raised from')), 'relaxed caps are listed and respected', `${rel.length} relaxed`);
}
const shelfT = new Set(build({ risk_level: 3 }).shelf.map(s => s.ticker));
const eligibleSats = CA.rows.filter(f => f.eligible && f.asset_class === 'Equity' && f.history_months >= 120 && !shelfT.has(f.yahoo) && CA.series.has(f.yahoo)).sort((a, b) => (b.aum || 0) - (a.aum || 0)).slice(0, 3).map(f => f.yahoo);
check(eligibleSats.length === 3, 'three satellites found', eligibleSats.join(','));
check(throwsKind({ risk_level: 3, sleeves: ['ca_reit', 'ca_gold', 'ca_cash'], satellites: eligibleSats }, 'infeasible'), 'satellite group cap is refused, not stretched');
{
  const p = build({ risk_level: 3, sleeves: ['ca_reit', 'ca_gold', 'ca_cash'], satellites: eligibleSats, onInfeasible: 'relax' });
  const satTotal = p.holdings.filter(h => h.role === 'satellite').reduce((s, h) => s + h.weight, 0);
  const g = p.method.relaxations.filter(x => x.limit === 'group'); const cap = g.length ? g[g.length - 1].applied : p.risk.satellite_cap;
  check(p.method.relaxations.length > 0 && satTotal <= cap + 2e-4, 'relaxed group cap is recorded and held', `${satTotal.toFixed(4)} <= ${cap.toFixed(4)}`);
}
check(throwsKind({ risk_level: 3, satellites: eligibleSats.slice(0, 2), minimums: { [eligibleSats[0]]: 0.15, [eligibleSats[1]]: 0.15 } }, 'infeasible'), 'forced satellites above the group cap are refused');
for (const lvl of [1, 2, 3, 4, 5]) check(build({ risk_level: lvl }).method.relaxations.length === 0, `default list never relaxes at level ${lvl}`);

// A4 views keep the 2% minimum and the budgets
for (const resample of [false, true]) {
  const p = buildPortfolio(CA, { risk_level: 3, resample, nBoot: 50, views: [{ type: 'relative', long: 'XIC.TO', short: 'ZAG.TO', difference: 0.03, confidence: 0.8 }] });
  const minW = Math.min(...p.holdings.map(h => h.weight)); const t = p.views.tilt;
  check(minW >= 0.02 - 1e-4 && t.tracking_error_after <= 0.01 + 1e-4 && t.largest_move_after <= 0.05 + 1e-4 && p.method.expected_returns_for_weights === 'black_litterman (bounded)',
    `views keep the minimum position (resample ${resample})`, `min ${minW}`);
}

// A5 a list without stock funds measures the market on the reference stock funds
{
  const p = build({ risk_level: 3, sleeves: ['ca_agg_bond', 'ca_short_bond', 'ca_cash'] });
  check(p.risk.stock_market_vol !== 0.15 && p.risk.stock_market_vol > 0.05 && p.notes.some(n => n.en.includes('holds no stock fund')), 'no-equity list uses the reference stock funds', `${p.risk.stock_market_vol}`);
}
// A7 a minimum that would drop everything keeps a valid portfolio
{ const p = build({ risk_level: 3, minWeight: 0.25 }); const s = p.holdings.reduce((a, h) => a + h.weight, 0); check(Math.abs(s - 1) < 1e-3 && p.holdings.length > 0, 'large min_weight keeps a valid portfolio'); }
check(throwsKind({ risk_level: 3, sleeves: [] }, 'input'), 'no funds left is an input error');

console.log(fails ? `${fails} safety check(s) FAILED` : 'all safety checks passed');
if (fails) process.exit(1);
