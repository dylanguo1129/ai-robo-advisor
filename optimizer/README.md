# How the Robo-Kit optimizer works

Robo-Kit turns a list of ETFs and a risk level (1 to 5) into portfolio weights. This note sets out the method we
settled on, why we chose it over the alternatives we tried, and what our own tests do and do not show. Every
number in it can be recomputed from this repository ([REPRODUCE.md](../REPRODUCE.md)).

In one sentence: **constrained mean-variance optimization with expected returns implied by a written policy mix
(never past averages), a shrunk risk estimate, a risk-aversion parameter λ calibrated so each level hits a stated
share of the stock market's volatility, and weights averaged over 200 resampled histories.**

| Where | What |
|---|---|
| `optimizer/` (this folder) | The numerical core: risk estimators (`estimators.py`), the solver (`solver.py`), the resampling and random numbers (`portfolio.py`, `rng.py`) |
| `robokit/engine.py` | The product pipeline that calls it: fund list, return window, limits, the λ calibration, the report |
| `robokit/shelf.py`, `robokit/history.py`, `robokit/cma.py`, `robokit/projection.py`, `robokit/stress.py` | The reference funds and policy mix, stand-ins for young funds, planning returns, projections, crisis replays |
| `web/robokit.js` | A port of the same engine for the web page; `web/test_robokit.mjs` checks that it reproduces Python |

The longer write-ups are the optimizer report (*Robo-Kit Portfolio Optimizer*, Team Summerhill, October 2026),
the research paper in [docs/paper](../docs/paper), and every design decision with its source or test in
[docs/DECISIONS.md](../docs/DECISIONS.md). The numbers below are those of our reports, for data snapshot
`00a560f4a6d3` (prices to August 31, 2026); version 3.3.2 reproduces them exactly (the optimizer's code has not
changed since 3.0.1).

## 1. The pipeline

1. **Funds.** The client's list: by default one broad fund per asset class from a written reference shelf, plus
   any funds the client swaps in or adds.
2. **Returns.** Monthly total returns (dividends reinvested) over the longest window every fund shares, up to 180
   months; US-listed funds are converted to Canadian dollars for a Canadian portfolio.
3. **Risk estimate Σ.** A shrunk covariance matrix (section 3).
4. **Expected returns π.** The returns implied by a written policy mix (section 4).
5. **Target.** The risk level becomes a volatility target (section 6).
6. **Solve** the mean-variance problem for a trial λ (section 5), with an exact solver (section 8).
7. **Resample.** Repeat steps 3 to 6 on 200 resampled histories and average the weights; drop positions under 2%
   and solve again (section 7).
8. **Calibrate λ** on the output of step 7 until the mix's volatility is within 0.005 percentage points of the
   target (section 6).
9. **Report** the weights with their bands, planning returns, projections, crisis replays and the regulator's risk
   rating (section 9).

Every step is deterministic: the same funds, data and level always give the same weights (fixed seeds), and every
result records the engine version and the data snapshot id.

## 2. The funds and the return window

**Reference shelf.** For each asset class ("slot"), the engine picks the eligible fund with the best score on a
written rule (`robokit/shelf.py`): `1.0·z(log assets) + 0.5·z(log daily trading) − 1.5·z(fee) + 0.5·z(history)`,
where z is a z-score among the slot's candidates and history counts up to 180 months. Low fees weigh most, so the
pick is usually the cheapest large fund, but it is a score, not a sort. Up to four like-for-like runners-up are
offered as alternatives. A fund is eligible if it has at least 36 months of its own returns, at least $20 million in
assets (Canada; $50 million US) and enough daily trading, and is not leveraged, inverse or a single company.

**Policy mix (the prior).** The slots carry fixed shares that sum to 100%: 60% stocks, 35% bonds, 3% real estate and
2% gold. In Canada:

| Slot | Share | Slot | Share |
|---|---|---|---|
| Canadian stocks | 18% | Canadian bonds | 22% |
| US stocks | 27% | Short-term bonds | 6% |
| International stocks | 10.8% | Global bonds | 7% |
| Emerging-market stocks | 4.2% | Real estate | 3% |
| Cash | 0% | Gold | 2% |

**Return window.** The common window is capped at 180 months (15 years) and must be at least 36. A core fund younger
than the window is extended backwards with a written stand-in (for example SPY in Canadian dollars for a US-stock
fund) that overlaps it for at least 24 months with a correlation of at least 0.8; the extension is disclosed.

## 3. Risk: a shrunk covariance matrix

The sample covariance of a few hundred months on ten or more funds is too noisy to optimize on. The engine shrinks it
toward a constant-correlation target (Ledoit and Wolf, 2004), with the shrinkage intensity estimated from the data;
on the 10 default Canadian funds the intensity is 0.174. When there are many funds for the months available
(N/T above 0.25), it switches to quadratic-inverse shrinkage (Ledoit and Wolf, 2022), which handles that case
better. Monthly estimates are annualized by 12. Code: `estimators.choose_covariance`.

## 4. Expected returns: implied by the policy mix, never past averages

Past average returns are the noisiest input in portfolio optimization: small errors in them produce extreme,
unstable weights. Robo-Kit never uses them. Instead it asks which expected returns would make the written policy mix
the optimal portfolio for an average investor (reverse optimization, the starting point of Black and Litterman):

&nbsp;&nbsp;&nbsp;&nbsp;**π = δ · Σ · w⁰**, with δ = 2.5 and w⁰ the policy mix renormalized over the funds on the list.

So π is a statement about risk, not a forecast: a fund earns a higher expected return only by adding risk the policy
mix already accepts. On the default list this gives, for example, 1.94% a year above cash for US stocks and 0.56%
for Canadian bonds. Optional client views can tilt π (Black-Litterman with Idzorek confidence), bounded to 1% of
tracking error; they are off by default.

FP Canada's 2026 planning assumptions are **not** used to set weights. They are used afterwards, net of each fund's
fee, for the returns, projections and dollar figures the client sees (`robokit/cma.py`).

## 5. The optimization problem

For a given λ the engine solves

&nbsp;&nbsp;&nbsp;&nbsp;**maximize π′w − (λ/2) · w′Σw**

subject to:

| Limit | Value |
|---|---|
| Budget | weights sum to 100% |
| Long only | no negative weights |
| Any one fund | at most 50% (cash follows its own row) |
| Narrow asset classes | real estate, gold and high-yield bonds 10% each; emerging-market stocks and US small companies 15%; inflation-linked bonds 20%; long-term bonds 25% |
| Cash | 100% at level 1, 30% at level 2, 15% at levels 3 to 5 |
| The client's own picks | 10% each (crypto 5%); 10% together at levels 1 and 2, 20% at level 3, 30% at levels 4 and 5 |
| Smallest position | 2%: smaller positions are dropped and the rest solved again |

Limits that cannot all hold stop the build with an explanation; nothing is relaxed silently.

## 6. Risk levels and the calibration of λ

The brief asks for weights "as a function of the client's risk attitude". A fixed λ per attitude would give
different risk on different fund lists, so Robo-Kit fixes the **risk** instead and finds the λ that delivers it.

- **Yardstick.** The volatility of the stock part of the policy mix on the funds listed (10.70% a year on the
  default Canadian list).
- **Target.** Level L aims for L × 20% of the yardstick: level 1 = 20% (2.14%), level 3 = 60% (6.42%), level 5 =
  100% (10.70%). The brief's high, mid and low risk aversion are levels 2, 3 and 4.
- **Calibration** (`robokit/engine.py`, `_calibrate_final`). A bisection on log λ over a single solve gives a starting
  point. The final λ is then found on the full pipeline, resampling and the 2% rule included, by bracketing and then
  the Illinois method on log λ, within [0.05, 2000], until the final mix is within 0.005 percentage points of the
  target. Every evaluation reuses the same resampled histories, so volatility is a deterministic function of λ.
  If the target is beyond the riskiest or steadiest mix the limits allow, the closest mix is kept and the result says
  "out of reach".

On the default list:

| Level | Name | Brief's setting | Target | λ found | Volatility reached |
|---|---|---|---|---|---|
| 1 | Conservative | | 2.14% | 8.78 | 2.14% |
| 2 | Cautious | high risk aversion | 4.28% | 4.37 | 4.28% |
| 3 | Balanced | mid risk aversion | 6.42% | 2.88 | 6.42% |
| 4 | Growth | low risk aversion | 8.56% | 2.08 | 8.56% |
| 5 | Aggressive growth | | 10.70% | 0.05 | 10.45% (out of reach) |

Level 5 cannot reach the full stock-market volatility because the averaged resampled solutions sit at the corners of
the limits and their average is less volatile than any one of them.

## 7. Resampling

One history gives one estimate of Σ and π, and the optimal weights are sensitive to both. Robo-Kit repeats the
estimation and the solve on **200 resampled histories** and averages the weights (Michaud's resampling):

- each history is a **stationary block bootstrap** of the actual months (Politis and Romano, 1994): random starting
  months, block lengths with a mean of 6 months, wrapping around the end, the same length as the window;
- each draw re-estimates Σ with the same estimator and re-derives π from it, then solves;
- the 5th to 95th percentile of each weight across draws is shown as a band (a spread of the resampled solutions,
  not a confidence interval);
- positions under 2% are then dropped and the remaining funds resampled and solved again.

The random numbers come from a seeded Mulberry32 generator (seed 0), ported bit for bit to the web page.

## 8. The solver

The quadratic program is solved by accelerated projected gradient (FISTA with adaptive restart; Beck and Teboulle,
2009; O'Donoghue and Candès, 2015) in a diagonally preconditioned space, which makes the problem far better conditioned (25.7 against 4,250 for Σ
on the default list). The projection onto the capped simplex (budget plus bounds, and the one group cap for own
picks) is exact: it evaluates the sorted breakpoints instead of bisecting. The solver stops when no weight moves by
more than 10⁻¹⁰; if it reaches 10,000 iterations first, it refuses to answer when the projected-gradient residual is
above 10⁻⁶. A test checks it against SciPy's SLSQP on random problems (objective within 10⁻⁷). Code: `solver.py`.

## 9. What the client sees

- **Weights** with their resampling bands, and each fund's share of the portfolio's risk.
- **Planning return** after fees: the median growth of 5,000 projected paths, which resample the funds' own history
  (mean block 6 months, seed 7) re-centred on FP Canada's assumptions minus each fund's fee.
- **A bad year**: the 5th percentile of the one-year outcomes, in dollars.
- **Crisis replays**: today's weights held through seven episodes (2008, 2011, 2014-16, late 2018, 2020, 2022,
  2025), with a stated stand-in for funds that did not exist yet.
- **Risk rating** on the scale Canadian funds must publish (NI 81-102 Appendix F: the volatility of the last 120
  months), fees in dollars, and plain-language checks.

## 10. Worked example: the brief's three settings

Canada, the 10 default ETFs, $10,000 (optimizer report Table 1; team report Table A1):

| | Low risk aversion | Mid risk aversion | High risk aversion |
|---|---|---|---|
| Level | 4 Growth | 3 Balanced | 2 Cautious |
| λ found | 2.08 | 2.88 | 4.37 |
| Volatility | 8.6% | 6.4% | 4.3% |
| Stocks / bonds / cash / real estate and gold | 70.7 / 20.8 / 0.0 / 8.5% | 52.5 / 34.1 / 11.1 / 2.3% | 35.6 / 34.4 / 30.0 / 0.0% |
| Typical year after fees (median of 5,000 paths) | 6.1% | 5.2% | 4.3% |
| Bad year (1 in 20) | −11.7% | −7.3% | −4.0% |
| 2008 replay | −27.5% | −18.5% | −10.1% |
| Fees per $10,000 a year | $12 | $11 | $10 |

Weights by level (%) (optimizer report Table 7; team report Table A7):

| Fund | Asset class | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| XIC | Canadian stocks | 6.15 | 11.88 | 16.49 | 20.29 | 26.91 |
| VFV | US stocks | 7.52 | 14.86 | 22.57 | 32.46 | 42.42 |
| FLUR | International stocks | 3.68 | 6.20 | 9.33 | 13.10 | 23.87 |
| VEE | Emerging-market stocks | – | 2.67 | 4.08 | 4.87 | 2.21 |
| ZAG | Canadian bonds | 6.47 | 10.55 | 19.47 | 20.81 | – |
| XSB | Short-term bonds | 2.09 | 18.18 | 7.50 | – | – |
| VBU | Global bonds | 3.49 | 5.66 | 7.13 | – | – |
| XRE | Real estate | – | – | 2.31 | 5.52 | 4.58 |
| VALT | Gold | – | – | – | 2.97 | – |
| CASH | Cash | 70.60 | 30.00 | 11.12 | – | – |

`python scripts/replicate.py tables` recomputes both tables and checks every printed value.

## 11. Why this method: what we tested

Version 3 was tested by an evaluation written down before any of it ran (docs/RESEARCH_LOG.md, sections 9 to 11),
examined in eighteen rounds by AI reviewers from other model families, and run from committed code (the first run
exposed a bug; the results are from the second run, after the disclosed fix: docs/RESEARCH_LOG.md section 11). Every
result is in [output/v3/results.json](../output/v3/results.json). Three defaults could change only by rules written
in advance; none of them was tuned on a back-test.

**Simulation with a known truth (E3).** 500 simulated 15-year histories per world. In world a the policy-implied
returns are true; in world b the true returns are FP Canada's planning assumptions instead; world c adds calm and
stress regimes to b. The loss is how much worse each method does than the true best portfolio under the same limits
(certainty equivalent, basis points a year, level 3):

| Method | a: model right | b: model wrong | c: wrong, with regimes |
|---|---|---|---|
| **Robo-Kit** | **0.17** | **24.07** | **24.42** |
| Robo-Kit without resampling | 0.17 | 24.07 | 24.42 |
| Static policy mix (no optimizer) | 0.53 | 20.95 | 20.95 |
| Sample covariance instead of shrinkage | 0.14 | 25.01 | 24.92 |
| Past average returns | 8.83 | 26.58 | 25.97 |
| Equal weights | 8.74 | 25.15 | 25.15 |
| Textbook optimizer (60 months of past means) | 25.00 | 50.92 | 49.70 |
| Risk parity, mixed with cash to the target | 30.64 | 63.87 | 63.92 |
| Minimum variance, mixed with cash to the target | 63.77 | 128.42 | 127.27 |

When the model is right, Robo-Kit is within 0.2 basis points of the best the limits allow. When it is wrong, it loses
24 basis points a year: less than every other method in the table except the static mix, which loses 3.1 less (the
version without resampling ties). The loss comes from
the wrong prior, not from estimation. Resampling neither helped nor hurt measurably (0.003 basis points in world
b), so under the written rule it stays. The covariance switch stayed at N/T = 0.25 by its rule.

**Walk-forward in Canada (E1, the confirmatory test).** Re-estimated every December from 2009 and held for a year,
January 2010 to August 2026 (200 months), after fees and a 10 basis point trading cost:

| Level | Annual return | Volatility | Volatility ÷ target | Sharpe | Worst fall |
|---|---|---|---|---|---|
| 2 | 6.1% | 4.7% | 1.04 | 0.92 | −9.3% |
| 3 | 8.1% | 7.0% | 1.03 | 0.92 | −14.0% |
| 4 | 10.4% | 9.0% | 0.99 | 0.96 | −16.1% |

Realized volatility came within a few percent of each target, but the registered reading is "inconclusive": the
simultaneous 90% intervals reach just past the 0.80 to 1.25 band. Against the four benchmarks no Sharpe difference
survived the Holm adjustment for twelve comparisons; Robo-Kit was "not worse by more than 0.10" than the static mix
at level 3, and at level 4 in the registered run; with the gold fund VALT's currency label corrected, the level-4
reading becomes "inconclusive" (adjusted p 0.059; docs/RESEARCH_LOG.md section 13). In the shorter US sample (92 months, exploratory) volatility ran about a third above target
(1.38, 1.38 and 1.34).

**The honest reading.** The method delivers the risk it states in Canada, stays close to the best portfolio its
limits allow when its model is right, and fails safely when the model is wrong. It does not beat a well-chosen static
mix, and our 200 months could not reliably show a Sharpe difference smaller than about 0.2 to 0.3. What it adds is a portfolio for
**any** fund list and **any** level, with stable weights that follow from written rules and can be explained step by
step.

**What we tried and set aside.**

| Alternative | Why not |
|---|---|
| Past average returns, or Bayes-Stein shrinkage of them | 8.8 basis points lost even when the model is right; lower Sharpe in Canada (0.88) |
| The textbook optimizer on 60 months | Twice the loss when the model is wrong; three times the trading (2.8% against 0.9% a month) |
| Three fixed λ values for low, mid and high | The same λ gives different risk on different fund lists |
| Equal weights; risk parity; minimum variance | No risk-attitude parameter; kept only as benchmarks (mixed with cash, they could not reach most targets) |
| Neural networks, drawdown or CVaR objectives, trend tilts | Too little data for learned models; a trend view failed its pre-set bar (t = 1.3 against 2) |

## 12. Limitations

- Volatility is a target, not a promise: in the US it ran about a third above.
- The policy mix drives the expected returns; a different mix gives different weights.
- The 15-year window does not contain 2008 (the projections and crisis replays do).
- Survivorship: the fund list is today's, and stand-ins extend young funds backwards.
- Level 5 cannot reach the full stock-market volatility under the limits.
- The examiners were AI models; a later audit used the same model family as the code's author.
- Robo-Kit is an educational prototype, not investment advice.

## 13. Reproduce it

[REPRODUCE.md](../REPRODUCE.md) gives the commands: the tables above in about two minutes from a fresh clone, the
web snapshot rebuilt from the archived data, and the registered evaluation re-run at its own commit and compared
value by value.

**References.** Beck and Teboulle (2009), *SIAM Journal on Imaging Sciences* 2(1); Black and Litterman (1992),
*Financial Analysts Journal* 48(5); Idzorek (2007), in Satchell (ed.), *Forecasting Expected Returns in the Financial
Markets*; Ledoit and Wolf (2004), *Journal of Portfolio Management* 30(4); Ledoit and Wolf (2022), *Bernoulli* 28(3);
Michaud and Michaud (2008), *Efficient Asset Management*, 2nd ed.; O'Donoghue and Candès (2015), *Foundations of
Computational Mathematics* 15(3); Politis and Romano (1994), *Journal of the American Statistical Association*
89(428); FP Canada and Institute of Financial Planning (2026), *Projection Assumption Guidelines*. Full list: the
paper in [docs/paper](../docs/paper).
