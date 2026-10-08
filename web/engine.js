/* Robo-Kit allocation engine, JavaScript port of optimizer/ (Python).
 *
 * Same pipeline, same formulas:
 *   Sigma = Ledoit-Wolf (2003) constant-correlation shrinkage of the monthly covariance, annualized;
 *           Ledoit-Wolf (2022) quadratic-inverse shrinkage (QIS) when the list is wide (N/T > 0.25)
 *   mu    = delta * Sigma * w_prior   (equilibrium excess returns)
 *   w*    = argmin (lam/2) w'Sigma w - mu'w   s.t. sum w = 1, lb <= w <= ub
 *           solved by FISTA with adaptive restart in the diagonally preconditioned space,
 *           with an exact projection onto the weighted capped simplex (sorted breakpoints)
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

/** Eigen-decomposition of a symmetric matrix by cyclic Jacobi rotations (accurate to rounding for the sizes used here).
 *  Returns { values, vectors }: eigenvalues ascending, vectors[i][k] = component i of the k-th eigenvector. */
export function symEig(A, maxSweeps = 100) {
  const n = A.length;
  const a = A.map(r => Float64Array.from(r));
  const V = Array.from({ length: n }, (_, i) => { const r = zeros(n); r[i] = 1; return r; });
  for (let sweep = 0; sweep < maxSweeps; sweep++) {
    let off = 0, scale = 0;
    for (let i = 0; i < n; i++) { scale += a[i][i] * a[i][i]; for (let j = i + 1; j < n; j++) off += a[i][j] * a[i][j]; }
    if (off <= 1e-30 * scale) break;
    for (let p = 0; p < n - 1; p++) for (let q = p + 1; q < n; q++) {
      const apq = a[p][q]; if (apq === 0) continue;
      const theta = (a[q][q] - a[p][p]) / (2 * apq);
      const t = (theta >= 0 ? 1 : -1) / (Math.abs(theta) + Math.sqrt(theta * theta + 1));
      const c = 1 / Math.sqrt(t * t + 1), s = t * c;
      for (let k = 0; k < n; k++) { const akp = a[k][p], akq = a[k][q]; a[k][p] = c * akp - s * akq; a[k][q] = s * akp + c * akq; }
      for (let k = 0; k < n; k++) { const apk = a[p][k], aqk = a[q][k]; a[p][k] = c * apk - s * aqk; a[q][k] = s * apk + c * aqk; }
      for (let k = 0; k < n; k++) { const vkp = V[k][p], vkq = V[k][q]; V[k][p] = c * vkp - s * vkq; V[k][q] = s * vkp + c * vkq; }
    }
  }
  const order = Array.from({ length: n }, (_, k) => k).sort((i, j) => a[i][i] - a[j][j]);
  return { values: Float64Array.from(order, k => a[k][k]), vectors: V.map(r => Float64Array.from(order, k => r[k])) };
}

/** Quadratic-inverse shrinkage (Ledoit and Wolf, Bernoulli 2022): port of optimizer/estimators.py qis (itself a port
 *  of the authors' reference code). Keeps the sample eigenvectors and shrinks the inverse eigenvalues; for wide lists. */
export function qis(X) {
  const N = X.length, p = X[0].length;
  const mean = zeros(p); for (const row of X) for (let j = 0; j < p; j++) mean[j] += row[j] / N;
  const y = X.map(row => Array.from(row, (v, j) => v - mean[j]));
  const n = N - 1, c = p / n;  // effective sample size after demeaning; concentration ratio
  const S = Array.from({ length: p }, () => zeros(p));
  for (const row of y) for (let i = 0; i < p; i++) { const ri = row[i] / n; for (let j = 0; j < p; j++) S[i][j] += ri * row[j]; }
  for (let i = 0; i < p; i++) for (let j = i + 1; j < p; j++) { const m = 0.5 * (S[i][j] + S[j][i]); S[i][j] = m; S[j][i] = m; }
  const { values, vectors: U } = symEig(S);
  const lam = Array.from(values, v => Math.max(0, v));
  const h = Math.min(c * c, 1 / (c * c)) ** 0.35 / p ** 0.35;  // smoothing parameter
  const start = Math.max(1, p - n + 1) - 1;
  const inv = lam.slice(start).map(v => 1 / v), m = inv.length;
  const theta = zeros(m), htheta = zeros(m);
  for (let j = 0; j < m; j++) {  // the smoothed Stein shrinker and its conjugate at x = 1/lambda_j, kernels centred on every 1/lambda_i
    const x = inv[j]; let th = 0, hth = 0;
    for (let i = 0; i < m; i++) { const li = inv[i], d = li - x, den = d * d + li * li * h * h; th += li * d / den; hth += li * li * h / den; }
    theta[j] = th / m; htheta[j] = hth / m;
  }
  let delta;
  if (p <= n) delta = inv.map((v, j) => 1 / ((1 - c) ** 2 * v + 2 * c * (1 - c) * v * theta[j] + c * c * v * (theta[j] ** 2 + htheta[j] ** 2)));
  else {
    const delta0 = 1 / ((c - 1) * (inv.reduce((s, v) => s + v, 0) / m));  // shrinkage of the null eigenvalues
    delta = [...new Array(p - n).fill(delta0), ...inv.map((v, j) => 1 / (v * (theta[j] ** 2 + htheta[j] ** 2)))];
  }
  const lamSum = lam.reduce((s, v) => s + v, 0), dSum = delta.reduce((s, v) => s + v, 0);
  const dq = delta.map(v => v * lamSum / dSum);  // preserve the trace
  const sigma = Array.from({ length: p }, () => zeros(p));
  for (let i = 0; i < p; i++) for (let j = i; j < p; j++) {
    let s = 0; for (let k = 0; k < p; k++) s += U[i][k] * dq[k] * U[j][k];
    sigma[i][j] = s; sigma[j][i] = s;
  }
  return sigma;
}

/** The engine's covariance rule (optimizer/estimators.py choose_covariance): constant-correlation shrinkage when
 *  N/T <= 0.25, QIS above. Resampled draws pass the method chosen on the full window, as the Python engine does. */
export function chooseCovariance(X, method = 'auto') {
  const t = X.length, n = X[0].length, conc = n / t;
  if (method === 'auto') method = conc > 0.25 ? 'qis' : 'lw_cc';
  if (method === 'qis') return { sigma: qis(X), shrink: null, method, concentration: conc };
  if (method === 'lw_cc') { const { sigma, shrink } = ledoitWolfConstantCorrelation(X); return { sigma, shrink, method, concentration: conc }; }
  throw new Error(`unknown covariance method ${method}`);
}

export function equilibriumReturns(sigma, wPrior, delta) { return matvec(sigma, wPrior).map(v => delta * v); }
export function sampleMeanExcess(X, rf) { const n = X[0].length, m = zeros(n); for (const r of X) for (let j = 0; j < n; j++) m[j] += r[j] / X.length; return Array.from(m, v => v * MONTHS - rf); }

// ---------- solver ----------
/** Euclidean projection of x onto {v : a'v = total, 0 <= v <= cap}, a > 0 (optimizer/solver.py).
 *  KKT gives v_i = clip(x_i - tau a_i, 0, cap_i); g(tau) = a'v(tau) is piecewise linear and non-increasing with
 *  breakpoints (x_i - cap_i)/a_i and x_i/a_i, so tau is found exactly on the segment of sorted breakpoints that
 *  contains total (binary search over the breakpoints, then linear interpolation). */
export function projectWeightedCappedSimplex(x, a, cap, total = 1) {
  const n = x.length;
  let aCap = 0; for (let i = 0; i < n; i++) aCap += a[i] * cap[i];
  if (aCap < total - 1e-9) throw new Error(`infeasible caps: ${aCap.toFixed(4)} < ${total}`);
  if (total <= 0) return zeros(n);  // a'v = 0 with v >= 0 is the single point v = 0
  const raw = new Float64Array(2 * n);
  for (let i = 0; i < n; i++) { raw[2 * i] = (x[i] - cap[i]) / a[i]; raw[2 * i + 1] = x[i] / a[i]; }
  raw.sort();
  const bp = []; for (let k = 0; k < raw.length; k++) if (k === 0 || raw[k] !== raw[k - 1]) bp.push(raw[k]);
  const g = (tau) => { let s = 0; for (let i = 0; i < n; i++) s += a[i] * Math.min(cap[i], Math.max(0, x[i] - tau * a[i])); return s; };
  let tau;
  if (total >= g(bp[0]) - 1e-15) tau = bp[0];  // every coordinate at its cap
  else {
    let lo = 0, hi = bp.length - 1;  // invariant: g(bp[lo]) >= total > g(bp[hi]) (g at the last breakpoint is 0)
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (g(bp[mid]) >= total) lo = mid; else hi = mid; }
    const gl = g(bp[lo]), gh = g(bp[hi]);
    tau = gl === gh ? bp[lo] : bp[lo] + (gl - total) * (bp[hi] - bp[lo]) / (gl - gh);
  }
  const v = zeros(n); for (let i = 0; i < n; i++) v[i] = Math.min(cap[i], Math.max(0, x[i] - tau * a[i]));
  const free = Array.from(v, (vi, i) => vi > 0 && vi < cap[i]);
  let gap = total, aa = 0; for (let i = 0; i < n; i++) { gap -= a[i] * v[i]; if (free[i]) aa += a[i] * a[i]; }
  if (aa > 0) for (let i = 0; i < n; i++) if (free[i]) v[i] = Math.min(cap[i], Math.max(0, v[i] + gap * a[i] / aa));  // exact budget fix
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
