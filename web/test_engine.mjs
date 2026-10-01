// node web/test_engine.mjs  -- checks the JS port against the Python reference outputs
import { readFileSync } from 'node:fs';
import { RoboKit } from './engine.js';

const data = JSON.parse(readFileSync(new URL('../output/robokit_web_data.json', import.meta.url), 'utf8'));
const kit = new RoboKit(data);
let fails = 0;
const check = (name, ok, detail) => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  ' + detail : ''}`); if (!ok) fails++; };

// 1. covariance matches Python (annualized LW constant-correlation). Returns are stored to 8 decimals in the JSON, hence 1e-8 tolerances.
let maxSig = 0;
for (let i = 0; i < kit.n; i++) for (let j = 0; j < kit.n; j++) maxSig = Math.max(maxSig, Math.abs(kit.sigma[i][j] - data.reference.sigma[i][j]));
check('sigma vs python', maxSig < 1e-8, `max abs diff ${maxSig.toExponential(2)}, shrinkage js ${kit.shrink.toFixed(6)} py ${data.reference.cov_shrinkage.toFixed(6)}`);

// 2. equilibrium mu matches
let maxMu = 0;
kit.tickers.forEach((t, i) => { maxMu = Math.max(maxMu, Math.abs(kit.mu[i] - data.reference.mu_excess[t])); });
check('mu vs python', maxMu < 1e-8, `max abs diff ${maxMu.toExponential(2)}`);
let maxMs = 0;
kit.tickers.forEach((t, i) => { maxMs = Math.max(maxMs, Math.abs(kit.muSample[i] - data.reference.mu_excess_sample[t])); });
check('sample mu vs python', maxMs < 1e-8, `max abs diff ${maxMs.toExponential(2)}`);

// 3. the six test cases (point estimates, no resampling)
for (const c of data.reference.test_cases) {
  const inp = c.input;
  const t0 = performance.now();
  const r = kit.optimize({ profile: inp.profile, tickers: inp.tickers, forced: inp.forced, excluded: inp.excluded, wMax: inp.w_max, resample: false });
  const ms = performance.now() - t0;
  let maxW = 0;
  r.tickers.forEach((t, k) => { maxW = Math.max(maxW, Math.abs(r.weights[k] - c.expected_weights[t])); });
  const volOk = Math.abs(r.expVol - c.expected_vol) < 1e-5;
  const sum = r.weights.reduce((a, b) => a + b, 0);
  check(`case ${c.name}`, maxW < c.tolerance && volOk && Math.abs(sum - 1) < 1e-8, `max |dw| ${maxW.toExponential(2)}, vol js ${r.expVol.toFixed(5)} py ${c.expected_vol.toFixed(5)}, lam ${r.lam.toFixed(3)}, ${ms.toFixed(0)} ms`);
}

// 4. resampling: sums to one, band contains the mean, deterministic per seed, fast enough for the browser
const t0 = performance.now();
const a = kit.optimize({ profile: 'high', resample: true, nBoot: 200, seed: 7 });
const ms = performance.now() - t0;
const b = kit.optimize({ profile: 'high', resample: true, nBoot: 200, seed: 7 });
const sameSeed = a.weights.every((w, k) => Math.abs(w - b.weights[k]) < 1e-15);
const sumA = a.weights.reduce((x, y) => x + y, 0);
const inBand = a.weights.every((w, k) => w === 0 || (w >= a.band[k].q05 - 0.05 && w <= a.band[k].q95 + 0.05));
check('resampling 200 draws', sameSeed && Math.abs(sumA - 1) < 1e-8 && inBand, `${ms.toFixed(0)} ms, cash ${a.weights[kit.tickers.indexOf('PSA.TO')].toFixed(3)}, effN ${a.effectiveN.toFixed(2)}`);

// 5. textbook toggle produces the concentrated portfolio the report describes
const tb = kit.optimize({ profile: 'mid', muMethod: 'sample', resample: false });
const nz = tb.weights.filter(w => w > 0.005).length;
check('textbook mu concentrates', nz <= 6 && tb.effectiveN < 5, `non-zero holdings ${nz}, effN ${tb.effectiveN.toFixed(2)}`);

console.log(fails === 0 ? '\nALL CHECKS PASSED' : `\n${fails} CHECK(S) FAILED`);
process.exit(fails === 0 ? 0 : 1);
