// node web/test_engine.mjs  -- the building blocks in web/engine.js against Python and against their definitions.
// The whole engine (web/robokit.js) is checked against Python by web/test_robokit.mjs.
import { readFileSync } from 'node:fs';
import { ledoitWolfConstantCorrelation, equilibriumReturns, sampleMeanExcess, projectWeightedCappedSimplex, symEig, qis, chooseCovariance, mulberry32, stationaryBootstrapRows } from './engine.js';

const data = JSON.parse(readFileSync(new URL('../output/robokit_web_data.json', import.meta.url), 'utf8'));
let fails = 0;
const check = (name, ok, detail) => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  ' + detail : ''}`); if (!ok) fails++; };

// 1. Ledoit-Wolf constant-correlation shrinkage matches Python (returns are stored to 8 decimals, hence 1e-8)
const X = data.returns_monthly, n = data.tickers.length;
const { sigma: sm, shrink } = ledoitWolfConstantCorrelation(X);
const sigma = sm.map(r => Array.from(r, v => v * 12));
let maxSig = 0; for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) maxSig = Math.max(maxSig, Math.abs(sigma[i][j] - data.reference.sigma[i][j]));
check('Ledoit-Wolf sigma vs python', maxSig < 1e-8, `max abs diff ${maxSig.toExponential(2)}, shrinkage js ${shrink.toFixed(6)} py ${data.reference.cov_shrinkage.toFixed(6)}`);
check('the rule picks constant correlation for this list', chooseCovariance(X).method === 'lw_cc', `N/T = ${(n / X.length).toFixed(3)}`);

// 2. equilibrium and sample means match Python
const prior = data.tickers.map(t => data.prior_weights[t]);
const mu = equilibriumReturns(sigma, prior, data.delta); let maxMu = 0;
data.tickers.forEach((t, i) => { maxMu = Math.max(maxMu, Math.abs(mu[i] - data.reference.mu_excess[t])); });
check('equilibrium mu vs python', maxMu < 1e-8, `max abs diff ${maxMu.toExponential(2)}`);
const ms = sampleMeanExcess(X, data.rf); let maxMs = 0;
data.tickers.forEach((t, i) => { maxMs = Math.max(maxMs, Math.abs(ms[i] - data.reference.mu_excess_sample[t])); });
check('sample mu vs python', maxMs < 1e-8, `max abs diff ${maxMs.toExponential(2)}`);

// 3. the exact projection: on the set, and equal to a 300-step bisection on tau (its definition), 2,000 random cases
const rng = mulberry32(3); let worst = 0, onSet = true;
for (let c = 0; c < 2000; c++) {
  const k = 1 + Math.floor(rng() * 11); const x = [], a = [], cap = [];
  for (let i = 0; i < k; i++) { x.push((rng() - 0.5) * 2); a.push(0.2 + 2.8 * rng()); cap.push(0.05 + 0.95 * rng()); }
  let acap = 0; for (let i = 0; i < k; i++) acap += a[i] * cap[i]; const total = (0.01 + 0.98 * rng()) * acap;
  const v = projectWeightedCappedSimplex(x, a, cap, total);
  let s = 0; for (let i = 0; i < k; i++) { s += a[i] * v[i]; if (v[i] < 0 || v[i] > cap[i] + 1e-15) onSet = false; }
  if (Math.abs(s - total) > 1e-12) onSet = false;
  let lo = Math.min(...x.map((xi, i) => (xi - cap[i]) / a[i])) - 1, hi = Math.max(...x.map((xi, i) => xi / a[i])) + 1;
  for (let it = 0; it < 300; it++) { const tau = 0.5 * (lo + hi); let g = 0; for (let i = 0; i < k; i++) g += a[i] * Math.min(cap[i], Math.max(0, x[i] - tau * a[i])); if (g > total) lo = tau; else hi = tau; }
  const tau = 0.5 * (lo + hi); for (let i = 0; i < k; i++) worst = Math.max(worst, Math.abs(v[i] - Math.min(cap[i], Math.max(0, x[i] - tau * a[i]))));
}
check('exact projection = bisection definition', onSet && worst < 1e-9, `max |dv| ${worst.toExponential(2)}`);
check('projection with a zero budget is zero', projectWeightedCappedSimplex([0.3, -0.1, 0.5], [1, 1, 1], [1, 1, 1], 0).every(v => v === 0));

// 4. Jacobi eigen-decomposition: A U = U diag(values), U orthonormal
const B = Array.from({ length: 8 }, () => Array.from({ length: 8 }, () => rng() - 0.5));
const A = B.map((_, i) => B.map((__, j) => B[i].reduce((s, v, k) => s + v * B[j][k], 0)));
const { values, vectors: U } = symEig(A); let res = 0, orth = 0;
for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) {
  let s = 0, o = 0; for (let k = 0; k < 8; k++) { s += U[i][k] * values[k] * U[j][k]; o += U[k][i] * U[k][j]; }
  res = Math.max(res, Math.abs(s - A[i][j])); orth = Math.max(orth, Math.abs(o - (i === j ? 1 : 0)));
}
check('symEig reconstructs A with orthonormal vectors', res < 1e-12 && orth < 1e-12, `residual ${res.toExponential(2)}, orthogonality ${orth.toExponential(2)}`);

// 5. QIS keeps the trace of the sample covariance and is positive definite (Python equality is in test_robokit.mjs)
const W = Array.from({ length: 40 }, () => Array.from({ length: 30 }, () => (rng() - 0.5) * 0.1));
const Q = qis(W); let trQ = 0, trS = 0; const m = W[0].map((_, j) => W.reduce((s, r) => s + r[j], 0) / W.length);
for (let j = 0; j < 30; j++) { trQ += Q[j][j]; trS += W.reduce((s, r) => s + (r[j] - m[j]) ** 2, 0) / (W.length - 1); }
check('QIS keeps the trace and is positive definite', Math.abs(trQ - trS) < 1e-12 * trS && symEig(Q).values[0] > 0, `trace ${trQ.toExponential(4)} vs ${trS.toExponential(4)}`);

// 6. the bootstrap is deterministic per seed and stays inside the history
const r1 = stationaryBootstrapRows(mulberry32(8), 40, 6), r2 = stationaryBootstrapRows(mulberry32(8), 40, 6);
check('bootstrap rows are deterministic and in range', r1.every((v, i) => v === r2[i] && v >= 0 && v < 40), Array.from(r1.slice(0, 8)).join(','));

console.log(fails === 0 ? '\nALL CHECKS PASSED' : `\n${fails} CHECK(S) FAILED`);
process.exit(fails === 0 ? 0 : 1);
