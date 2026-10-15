# Model card: Robo-Kit portfolio engine, version 3

## What it is

A long-only mean-variance engine that builds a portfolio of exchange-traded funds for a Canadian or US investor at a
chosen risk level (1-5). Expected returns are equilibrium returns from a written policy mix (60% stocks, 35% bonds, 3%
real estate, 2% gold; 30% of equities in Canada for Canadian investors); risk is Ledoit-Wolf constant-correlation
shrinkage (QIS when there are many funds for the history); the weights are averaged over 200 stationary-bootstrap
histories; risk aversion is calibrated so the mix the client receives meets the level's volatility target. A
rebalancer turns the weights into orders. Python (`robokit/`, `optimizer/`) and the browser (`web/`) run the same
algorithm and are tested against each other. Method: docs/METHOD.md and docs/paper; every decision and its evidence:
docs/DECISIONS.md.

## Intended use

- Research, teaching and demonstration of a transparent robo-adviser engine.
- Building and explaining an example portfolio for a self-directed investor, with its risk, fees, a projection and
  crisis replays shown in plain words.

## Not intended for

- Advice. In Canada, advice from such an engine must be given by a registered portfolio manager with human oversight
  (CSA Staff Notice 31-342). Suitability checks are opt-in and do not replace a know-your-client process.
- Market timing, leverage, short selling, single stocks, or funds outside the screened universe.
- Commercial use of the bundled market data (Yahoo Finance and TMX data are for personal use).

## Data

Monthly adjusted closes of every Canadian and US exchange-traded fund with usable data (snapshot ending 31 Aug 2026):
637 Canadian and 1,998 US funds pass the eligibility screens (630 and 1,966 in the universe the registered evaluation used, before the 3.0.1 label fix). Bank of Canada and US Treasury bill yields for cash.
FP Canada / Institute of Financial Planning 2026 planning assumptions for projections. Sources, refresh and licences:
docs/DATA.md.

## Evaluation (output/v3/results.json; docs/paper section 6)

Pre-registered (docs/RESEARCH_LOG.md sections 9-11), examined in eighteen rounds before it ran, run from a committed
protocol with 500 simulated histories per world (one re-run for a disclosed bug fix; every other number reproduced).

| Question | Result |
|---|---|
| Does each level deliver its stated volatility? | Canada 2010-2026: realised over target 1.04, 1.03, 0.99 at levels 2-4 (registered reading "inconclusive": two intervals reach just past 1.25). US 2019-2026: 1.38, 1.38, 1.34 ("missed"). |
| Does it beat simple alternatives on risk-adjusted return? | Not detected. No Sharpe-ratio difference survived Holm adjustment in either market; against a static mix in Canada, not worse by more than 0.10 at levels 3 and 4. |
| How close is it to the true optimum (simulation)? | Within 0.2 bp a year when the model is right; about 24 bp a year when expected returns follow planning assumptions, where a static mix lost about 3 bp less. |
| Does resampling help? | No measurable effect either way; kept by the registered rule. |
| Is the calibration exact? | Every walk-forward calibration ended within tolerance or at a proven bound; none at the evaluation limit. |
| Did the evaluation change a default? | Yes: projection paths 2,000 to 5,000 (registered precision rule). |

## Limitations

See README "Known limitations" and docs/paper section 8. The most important: US risk above target in recent years;
no proven edge over a static mix; crisis replays start in 2008; for BNDX holders the projections start in 2013.

## Monitoring (each check is automated or part of `make check`)

| Signal | Threshold | Where |
|---|---|---|
| Realised over target volatility, rolling 36 months, each level and market | outside [0.80, 1.25]: review the level targets and the covariance window | recompute with `robokit.evaluation.risk_delivery` on live paths |
| Calibration outcome | any `limit` (evaluation limit reached) is a failure | every build's `risk.calibration.outcome`; tests/test_v3_calibration.py |
| Python and browser engines | any reference case outside parity tolerance | web/test_robokit.mjs (CI) |
| Projection precision | Monte Carlo standard error of the one-year 5th percentile above 0.25 points at 5,000 paths | the E5 rule in scripts/run_v3_evaluation.py |
| Data integrity | a new month in which a fund doubles or halves while its peers do not | the jump screen, at each data refresh |
| Liquidity | an order above 1% of a fund's average daily traded value | the rebalancer's flag |
| Shipped defaults | any difference from the registered run's locked defaults | tests/test_v3_locked_defaults.py |

## Versions

v3.1.0 (October 2026): the web page becomes the guided conversation (team wireframes and conversation script); a risk self-rating (C0, levels 2 / 3 / 4) joins the tolerance answers with a second chance when it disagrees with the drop scenario; answers without it score as before; the default mixes are unchanged.
v3.0.4 (October 2026): the stored data checked against independent sources (docs/research/v304_data_verification.md); the reference funds' MERs come from the issuers' pages; the default mixes are unchanged.
v3.0.3 (October 2026): region and leverage labels corrected after the team data layer's cross-check (docs/research/v303_crosscheck.md) and its fund facts merged; no reference fund, default mix or reported number changes.
v3.0.2 (October 2026): currency-hedging labels corrected (VALT and 36 others; HUG is also futures-based, so the strict point-in-time test would now leave gold out in 2012-2022); a re-run of the Canadian walk-forward with VALT's label corrected leaves the risk readings unchanged and turns the level-4 non-inferiority reading against the static mix to inconclusive (docs/RESEARCH_LOG.md section 13).
v3.0.1 (October 2026): the second bug hunt's fixes (CHANGELOG); Robo-Kit's evaluated results are unchanged.
v3.0.0 (October 2026): this card. Earlier versions: docs/RESEARCH_LOG.md sections 1-8.
