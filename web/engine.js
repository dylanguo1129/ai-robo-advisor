/* Robo-Kit allocation engine, JavaScript port of optimizer/ (Python).
 *
 * Same pipeline, same formulas:
 *   Sigma = Ledoit-Wolf (2003) constant-correlation shrinkage of the monthly covariance, annualized
 *   mu    = delta * Sigma * w_prior   (equilibrium excess returns)
 *   w*    = argmin (lam/2) w'Sigma w - mu'w   s.t. sum w = 1, lb <= w <= ub
 *           solved by FISTA with adaptive restart in the diagonally preconditioned space,
 *           with an exact projection onto the weighted capped simplex (bisection on tau)
 *   resampling: stationary block bootstrap of the monthly history, re-estimate, re-solve, average
 *
 * Checked against the Python reference outputs in output/robokit_web_data.json by web/test_engine.mjs.
 * Plain ES module, no dependencies; works in the browser and in Node.
 */

const MONTHS = 12;
const EPS = 1e-12;

// ---------- small linear algebra helpers (N <= a few hundred) ----------
export function zeros(n) { return new Float64Array(n); }
export function matvec(A, x) {
  const n = x.length, out = zeros(n);
  for (let i = 0; i < n; i++) { let s = 0; const r = A[i]; for (let j = 0; j < n; j++) s += r[j] * x[j]; out[i] = s; }
  return out;
}
export function dot(a, b) { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; }
export function quad(A, w) { return dot(w, matvec(A, w)); }
function sub(A, idx) { return idx.map(i => idx.map(j => A[i][j])); }

function powerMaxEig(A, iters = 300) {
  const n = A.length; let v = new Float64Array(n).fill(1 / Math.sqrt(n)); let lam = 0;
  for (let k = 0; k < iters; k++) {
    const Av = matvec(A, v); const norm = Math.sqrt(dot(Av, Av)); if (norm < EPS) return 0;
    const next = lam; lam = norm; for (let i = 0; i < n; i++) v[i] = Av[i] / norm;
    if (k > 20 && Math.abs(lam - next) < 1e-12 * lam) break;
  }
  return lam;
}

// ---------- estimators ----------
/** Ledoit-Wolf (2003) shrinkage toward the constant-correlation target. X: T x N array of arrays. */
export function ledoitWolfConstantCorrelation(X) {
  const t = X.length, n = X[0].length;
  const mean = zeros(n);
  for (const row of X) for (let j = 0; j < n; j++) mean[j] += row[j] / t;
  const x = X.map(row => row.map((v, j) => v - mean[j]));
  const s = Array.from({ length: n }, () => zeros(n));
  for (const row of x) for (let i = 0; i < n; i++) { const ri = row[i] / t; for (let j = 0; j < n; j++) s[i][j] += ri * row[j]; }
  const vr = s.map((r, i) => r[i]); const sd = vr.map(Math.sqrt);
  let corrSum = 0; for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) corrSum += s[i][j] / (sd[i] * sd[j]);
  const rbar = (corrSum - n) / (n * (n - 1));
  const f = s.map((r, i) => r.map((_, j) => (i === j ? vr[i] : rbar * sd[i] * sd[j])));
  // pi_mat = (x2' x2)/t - s^2 ; term1 = (x^3)' x / t
  const piMat = Array.from({ length: n }, () => zeros(n));
  const term1 = Array.from({ length: n }, () => zeros(n));
  for (const row of x) {
    for (let i = 0; i < n; i++) {
      const xi2 = row[i] * row[i] / t, xi3 = row[i] * row[i] * row[i] / t;
      for (let j = 0; j < n; j++) { piMat[i][j] += xi2 * row[j] * row[j]; term1[i][j] += xi3 * row[j]; }
    }
  }
  let piHat = 0, rhoDiag = 0, rhoOff = 0, gamma = 0;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    piMat[i][j] -= s[i][j] * s[i][j]; piHat += piMat[i][j];
    gamma += (f[i][j] - s[i][j]) ** 2;
  }
  for (let i = 0; i < n; i++) rhoDiag += piMat[i][i];
  const help = term1.map((r, i) => r.map((v, j) => (i === j ? 0 : v - vr[i] * s[i][j])));
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) rhoOff += (sd[j] / sd[i]) * help[i][j] + (sd[i] / sd[j]) * help[j][i];
  rhoOff *= rbar / 2;
  const kappa = gamma > 0 ? (piHat - (rhoDiag + rhoOff)) / gamma : 0;
  const shrink = Math.max(0, Math.min(1, kappa / t));
  const scale = t / (t - 1);
  const sigma = s.map((r, i) => r.map((v, j) => (shrink * f[i][j] + (1 - shrink) * v) * scale));
  return { sigma, shrink };
}

export function equilibriumReturns(sigma, wPrior, delta) { return matvec(sigma, wPrior).map(v => delta * v); }
export function sampleMeanExcess(X, rf) { const n = X[0].length, m = zeros(n); for (const r of X) for (let j = 0; j < n; j++) m[j] += r[j] / X.length; return Array.from(m, v => v * MONTHS - rf); }

// ---------- solver ----------
export function projectWeightedCappedSimplex(x, a, cap, total = 1, tol = 1e-13) {
  const n = x.length;
  let aCap = 0; for (let i = 0; i < n; i++) aCap += a[i] * cap[i];
  if (aCap < total - 1e-9) throw new Error(`infeasible caps: ${aCap.toFixed(4)} < ${total}`);
  let lo = Infinity, hi = -Infinity;
  for (let i = 0; i < n; i++) { lo = Math.min(lo, (x[i] - cap[i]) / a[i]); hi = Math.max(hi, x[i] / a[i]); }
  lo -= 1; hi += 1;
  const clip = (tau) => { const v = zeros(n); for (let i = 0; i < n; i++) v[i] = Math.min(cap[i], Math.max(0, x[i] - tau * a[i])); return v; };
  for (let k = 0; k < 200; k++) {
    const tau = 0.5 * (lo + hi); const v = clip(tau); let s = 0; for (let i = 0; i < n; i++) s += a[i] * v[i];
    if (s > total) lo = tau; else hi = tau;
    if (hi - lo < tol) break;
  }
  const v = clip(0.5 * (lo + hi));
  let gap = total, aa = 0; for (let i = 0; i < n; i++) { gap -= a[i] * v[i]; if (v[i] > 0 && v[i] < cap[i]) aa += a[i] * a[i]; }
  if (aa > 0) for (let i = 0; i < n; i++) if (v[i] > 0 && v[i] < cap[i]) v[i] = Math.min(cap[i], Math.max(0, v[i] + gap * a[i] / aa));
  return v;
}

function greedyMaxReturn(mu, lb, ub) {
  const w = Float64Array.from(lb); let room = 1 - w.reduce((s, v) => s + v, 0);
  const order = Array.from(mu.keys()).sort((i, j) => mu[j] - mu[i]);
  for (const i of order) { const take = Math.min(ub[i] - w[i], room); w[i] += take; room -= take; if (room <= EPS) break; }
  return w;
}

/** minimize (lam/2) w'Sigma w - mu'w  s.t. sum w = 1, lb <= w <= ub. Returns Float64Array. */
export function solveQP(sigma, mu, lam, lb, ub, maxIter = 10000, tol = 1e-10) {
  const n = mu.length;
  lb = lb || zeros(n); ub = ub || new Float64Array(n).fill(1);
  let lbSum = 0; for (const v of lb) lbSum += v;
  if (lbSum > 1 + 1e-9) throw new Error('lower bounds sum above 1');
  if (lam <= EPS) return greedyMaxReturn(mu, lb, ub);
  const mass = 1 - lbSum; const cap = ub.map((u, i) => u - lb[i]);
  if (mass <= EPS) return Float64Array.from(lb);
  const d = sigma.map((r, i) => Math.sqrt(Math.max(r[i], 1e-16)));
  const a = d.map(v => 1 / v);
  const corr = sigma.map((r, i) => r.map((v, j) => v / (d[i] * d[j])));
  const capv = cap.map((c, i) => c * d[i]);
  const sLb = matvec(sigma, lb);
  const gLin = mu.map((m, i) => (lam * sLb[i] - m) / d[i]);
  const lip = lam * powerMaxEig(corr) * 1.02;   // 2% margin on the power-iteration estimate
  const step = 1 / Math.max(lip, EPS);
  let v = projectWeightedCappedSimplex(d.map(di => (mass / n) * di), a, capv, mass);
  let y = Float64Array.from(v); let tk = 1;
  for (let it = 0; it < maxIter; it++) {
    const cy = matvec(corr, y);
    const g = y.map((_, i) => lam * cy[i] + gLin[i]);
    const vNext = projectWeightedCappedSimplex(y.map((yi, i) => yi - step * g[i]), a, capv, mass);
    const dv = vNext.map((vi, i) => vi - v[i]);
    let restart = 0; for (let i = 0; i < n; i++) restart += (y[i] - vNext[i]) * dv[i];
    if (restart > 0) { tk = 1; y = Float64Array.from(vNext); }
    else { const tNext = 0.5 * (1 + Math.sqrt(1 + 4 * tk * tk)); y = vNext.map((vi, i) => vi + ((tk - 1) / tNext) * dv[i]); tk = tNext; }
    let maxd = 0; for (let i = 0; i < n; i++) maxd = Math.max(maxd, Math.abs(dv[i] / d[i]));
    v = vNext;
    if (maxd < tol) break;
  }
  const w = v.map((vi, i) => Math.min(ub[i], Math.max(lb[i], vi / d[i] + lb[i])));
  const sum = w.reduce((s, x) => s + x, 0);
  return w.map(x => x / sum);
}

// ---------- bootstrap ----------
export function mulberry32(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
export function stationaryBootstrapRows(rng, t, blockLength = 6) {
  const p = 1 / blockLength, rows = new Int32Array(t); let i = 0;
  while (i < t) {
    const start = Math.floor(rng() * t);
    let len = 1; while (rng() > p) len++;          // geometric(p)
    for (let k = 0; k < len && i < t; k++, i++) rows[i] = (start + k) % t;
  }
  return rows;
}

// ---------- the optimizer ----------
export class RoboKit {
  /** data = the object in output/robokit_web_data.json */
  constructor(data) {
    this.data = data;
    this.tickers = data.tickers; this.n = data.tickers.length;
    this.rf = data.rf; this.delta = data.delta; this.profiles = data.profiles;
    this.wMax = data.w_max; this.cash = data.cash_ticker;
    this.prior = data.tickers.map(t => data.prior_weights[t]);
    this.X = data.returns_monthly;
    this.fit(this.X);
  }
  fit(X) {
    const { sigma, shrink } = ledoitWolfConstantCorrelation(X);
    this.sigma = sigma.map(r => r.map(v => v * MONTHS)); this.shrink = shrink;
    this.mu = equilibriumReturns(this.sigma, this.prior, this.delta);
    this.muSample = sampleMeanExcess(X, this.rf);
    return this;
  }
  lamFor(profile) { return typeof profile === 'number' ? profile : this.profiles[profile] * this.delta; }
  bounds(idx, opts) {
    const wMax = opts.wMax ?? this.wMax, cashMax = opts.cashMax ?? 1;
    const lb = zeros(idx.length), ub = new Float64Array(idx.length).fill(wMax);
    idx.forEach((gi, k) => {
      const t = this.tickers[gi];
      if (t === this.cash) ub[k] = Math.max(cashMax, wMax);
      if (opts.excluded?.includes(t)) ub[k] = 0;
      else if (opts.forced && t in opts.forced) lb[k] = Math.max(lb[k], opts.forced[t]);
    });
    for (let k = 0; k < idx.length; k++) ub[k] = Math.max(ub[k], lb[k]);
    let s = 0; for (const u of ub) s += u; let relaxed = false;
    if (s < 1 - 1e-9 && s > 0) { for (let k = 0; k < ub.length; k++) ub[k] /= s; relaxed = true; }
    return { lb, ub, relaxed };
  }
  /**
   * opts: { profile, tickers, forced, excluded, wMax, cashMax, resample, nBoot, seed, blockLength, muMethod: 'equilibrium'|'sample', minWeight }
   */
  optimize(opts = {}) {
    const profile = opts.profile ?? 'mid';
    const tick = opts.tickers?.length ? opts.tickers : this.tickers;
    const idx = tick.map(t => { const i = this.tickers.indexOf(t); if (i < 0) throw new Error(`unknown ticker ${t}`); return i; });
    const lam = this.lamFor(profile);
    const muFull = opts.muMethod === 'sample' ? this.muSample : this.mu;
    const sigma = sub(this.sigma, idx), mu = idx.map(i => muFull[i]);
    const { lb, ub, relaxed } = this.bounds(idx, opts);
    const solve = (S, m) => { const w = solveQP(S, m, lam, lb, ub); return w.map(v => (Math.abs(v) < 1e-6 ? 0 : v)).map((v, _, arr) => v / arr.reduce((a, b) => a + b, 0)); };
    const wPoint = solve(sigma, mu);
    let w = wPoint, band = null;
    const nBoot = opts.resample ? (opts.nBoot ?? 300) : 0;
    if (nBoot > 0) {
      const rng = mulberry32(opts.seed ?? 1); const T = this.X.length; const acc = zeros(idx.length); const draws = [];
      for (let b = 0; b < nBoot; b++) {
        const rows = stationaryBootstrapRows(rng, T, opts.blockLength ?? 6);
        const Xb = Array.from(rows, r => this.X[r]);
        const { sigma: sb } = ledoitWolfConstantCorrelation(Xb);
        const Sb = sb.map(r => r.map(v => v * MONTHS));
        const mb = opts.muMethod === 'sample' ? sampleMeanExcess(Xb, this.rf) : equilibriumReturns(Sb, this.prior, this.delta);
        const wb = solve(sub(Sb, idx), idx.map(i => mb[i]));
        draws.push(wb); for (let k = 0; k < wb.length; k++) acc[k] += wb[k] / nBoot;
      }
      w = acc.map(v => (v < 1e-4 ? 0 : v)); const s = w.reduce((a, b) => a + b, 0); w = w.map(v => v / s);
      band = idx.map((_, k) => { const col = draws.map(d => d[k]).sort((a, b) => a - b); const q = (p) => col[Math.min(col.length - 1, Math.floor(p * col.length))]; return { q05: q(0.05), q95: q(0.95) }; });
    }
    let dropped = [];
    if (opts.minWeight > 0) {
      const small = w.map((v, k) => v > 0 && v < opts.minWeight && lb[k] === 0);
      if (small.some(Boolean)) {
        const ub2 = Float64Array.from(ub); small.forEach((s, k) => { if (s) ub2[k] = 0; });
        let s2 = 0; for (const u of ub2) s2 += u;
        if (s2 >= 1 - 1e-9) { w = solveQP(sigma, mu, lam, lb, ub2).map(v => (Math.abs(v) < 1e-6 ? 0 : v)); const s = w.reduce((a, b) => a + b, 0); w = w.map(v => v / s); dropped = tick.filter((_, k) => small[k]); }
      }
    }
    const Sw = matvec(sigma, w); const variance = dot(w, Sw); const vol = Math.sqrt(variance);
    const exc = dot(mu, w);
    const rc = w.map((wi, k) => (variance > 0 ? wi * Sw[k] / variance : 0));
    const effN = 1 / w.reduce((s, v) => s + v * v, 0);
    return {
      profile, lam, tickers: tick, weights: Array.from(w), pointWeights: Array.from(wPoint), band,
      expReturn: this.rf + exc, expVol: vol, sharpe: vol > 0 ? exc / vol : 0, riskContributions: Array.from(rc), effectiveN: effN,
      relaxedCaps: relaxed, dropped, muMethod: opts.muMethod ?? 'equilibrium', resampled: nBoot > 0, nBoot,
    };
  }
  assetRow(t) {
    const i = this.tickers.indexOf(t);
    return { ticker: t, prior: this.prior[i], expExcess: this.mu[i], expReturn: this.mu[i] + this.rf, expVol: Math.sqrt(this.sigma[i][i]), sampleExcess: this.muSample[i], ...this.data.meta[t], ...this.data.hist[t] };
  }
}
