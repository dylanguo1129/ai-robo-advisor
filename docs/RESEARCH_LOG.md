# Research log — everything that was tried

Kept because the Session 2 protocol (Arnott, Harvey & Markowitz 2019) says "Keeping track of the number of strategies tried is crucial", and because the Quantech brief in this course asks teams to "Report how many variables and combination of variables, and how many different predictive models you used". The same standard applies to us. Entries are dated; nothing is removed.

## 1. Design decisions fixed before any back-test (26 Sep 2026, morning)

| Decision | Chosen | Alternatives considered and why not |
| --- | --- | --- |
| Objective | mean-variance with risk aversion lam, long-only, sum-to-one, cap per ETF | CVaR/drawdown (needs tail data we lack); HRP (no risk-aversion dial) |
| Expected returns | equilibrium: pi = delta Sigma w_prior, delta = 2.5 | sample mean (kept as benchmark); Bayes-Stein (kept as benchmark); Black-Litterman views (available, unused: preferences enter as constraints) |
| Covariance | Ledoit-Wolf constant-correlation shrinkage; QIS when N/T > 0.25 | sample (benchmark); identity-target LW (implemented, not default); factor model (not implemented) |
| Prior portfolio | AUM shares of the universe (Yahoo `totalAssets`, 3 of 20 filled with class median) | global market portfolio by asset class (weights not retrieved); 60/35/3/2 policy prior (robustness variant) |
| Risk profiles | lam = 0.6 / 1.0 / 2.5 x delta | target-volatility calibration (implemented; used for the risk-matched back-test) |
| Cap per ETF | 35%; cash ETF uncapped | cash capped at 35% (robustness variant) |
| Resampling | 500 draws, average weights | none (point estimate, reported alongside) |
| History | monthly total returns, Feb 2016 - Aug 2026 (start dictated by XAW's 2015 listing), 36-month minimum | 2014 start without XAW (robustness variant) |

## 2. Back-test design, as first run (26 Sep 2026, midday)

Walk-forward, 60-month estimation window, annual re-estimation, weights held 12 months. Five methods x three profiles. No transaction costs. Each method used its own lam.

**Post-hoc change, disclosed.** After seeing the first table it was clear that "high" under sample-mean mu had 10% realized volatility while "high" under equilibrium mu had 4%: the same lam produces different risk when mu is on a different scale, so the profiles were not comparable across methods. The back-test was changed to *risk-matched*: every method's lam is calibrated so its ex-ante volatility hits 12 / 9 / 4% per profile. This is a change to the comparison, not to the method being sold, but under the protocol ("iterated out of sample is not out of sample") it must be recorded: the reported results are from the second design, and the first design's numbers are kept in git history of this folder (`backtest_stats.csv` as of the midday run: sample-mean high profile 16.6% return at 10.0% vol).

## 3. Changes after reading the Session 2 materials (26 Sep 2026, afternoon)

All added before the robustness grid was run:

* transaction costs, 10 bps one-way on every unit of turnover including monthly drift rebalancing ("Do not ignore trading costs and fees");
* stationary block bootstrap (mean block 6 months) replaces the iid bootstrap as the default resampling, to keep volatility clustering;
* `integrity_report`: stale-price runs and |monthly return| > 30% are flagged, never deleted ("Do not arbitrarily exclude outliers");
* `cash_max`, `naive_blend` (Tu & Zhou 2011) and a policy-prior helper, so the grid below can test them;
* sub-period statistics.

## 4. The pre-registered robustness grid (`scripts/run_robustness.py`)

Written down in full before it was run. Seven configurations x five methods x three profiles = 105 out-of-sample series. Results: `output/robustness_grid.csv`, `output/robustness_subperiods.csv`, `output/robustness_paired.csv`; interpretation in `METHOD.md` section 5.

| # | name | sample | window | prior | 1/N blend | cash cap | cost |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | base_2016_w60 | 2016-, 20 ETFs | 60 | AUM | 0 | none | 10 bps |
| 2 | long_2014_w48 | 2014-, 19 ETFs (no XAW) | 48 | AUM | 0 | none | 10 bps |
| 3 | long_2014_w60 | 2014-, 19 ETFs | 60 | AUM | 0 | none | 10 bps |
| 4 | long_2014_w48_policyprior | 2014-, 19 ETFs | 48 | 60/35/3/2 policy | 0 | none | 10 bps |
| 5 | long_2014_w48_blend50 | 2014-, 19 ETFs | 48 | AUM | 0.5 | none | 10 bps |
| 6 | long_2014_w48_cashcap35 | 2014-, 19 ETFs | 48 | AUM | 0 | 35% | 10 bps |
| 7 | long_2014_w48_cost25 | 2014-, 19 ETFs | 48 | AUM | 0 | none | 25 bps |

Multiple-testing note: seven configurations are highly correlated (same data, small changes), so the effective number of independent tests is well below seven; even so, no configuration is selected on the strength of its result — the default (#1's method) was fixed in section 1.

**Results (run 26 Sep 2026, 14:45–15:05).** Equilibrium minus plug-in, annualized return at matched risk, after costs, with t-statistics: base −1.3% / −3.2% / −0.4% (t −0.9 / −1.7 / −0.5) for low / mid / high; long_2014_w48 −0.6% / −0.1% / +0.3% (t −0.4 / 0.0 / +0.4); long_2014_w60 −1.1% / −2.1% / −0.3% (t −0.7 / −1.3 / −0.4); policy prior −1.1% / −0.8% / +0.1%; blend 50% +0.5% / −0.1% / −0.0%; cash cap 35% −0.6% / −0.1% / +0.3%; costs 25 bps −0.6% / −0.0% / +0.4%. None significant. Drawdowns and turnover favour the equilibrium method in every 2014-sample configuration (e.g. mid: −17.8% vs −22.0%, 21% vs 40% a year). Reading and caveats in METHOD.md section 5.2. Nothing was changed after these results.

## 5. What was *not* tried, and why

* No hyper-parameter search over delta, the profile multipliers, the shrinkage target, the cap or the window length. Each has one pre-specified value or a single pre-specified alternative in the grid.
* No winsorization or outlier removal at any level.
* No learned allocator (decision-focused learning, neural shrinkage) — see METHOD.md section 4.
* No look-ahead: AUM is a single 2026 snapshot used as the prior at every date, which is a *known* mild look-ahead (the 2026 AUM ranking reflects 2016-2026 performance). Recorded as a limitation; a time-varying prior needs AUM history the team does not have.

---

## 6. v2 pre-registration (written 28 Sep 2026, before any v2 back-test was run)

Scope change: the universe is now every CAD-buyable Canadian-listed ETF and every US-listed ETF; the portfolio is built on a reference shelf (one broad, low-cost fund per asset class, chosen by a written rule in `robokit/shelf.py`) plus optional user picks. Young shelf funds are extended with written, correlation-checked proxies (`robokit/history.py`). The risk level (1-5) sets a share of the stock market's volatility (level x 20%), and lambda is calibrated to it.

**What will be run (`scripts/run_backtest_v2.py`), exactly once:**

* Markets: CA (CAD, reference shelf) and US (USD, reference shelf), spliced histories.
* Walk-forward: 60-month rolling estimation window, re-estimated every 12 months, held 12 months with monthly rebalancing back to target; 10 bps one-way cost on all turnover (v1 protocol).
* Levels 2, 3, 4 (the brief's low / mid / high).
* Strategies:
  1. `robokit`: equilibrium returns, shrunk covariance, guardrails of `robokit/engine.py` (sleeve caps, cash cap by level), stationary-bootstrap resampling with 50 draws, lambda calibrated so the in-window volatility equals level share x in-window stock-market volatility.
  2. `robokit_trend`: the same plus Black-Litterman views on every non-cash shelf fund, view = equilibrium excess return + sigma_i x IC x z_i with z_i = 12-1 month return / annual volatility, clipped to +/-2, IC = 0.05 (Grinold's "good forecaster"), confidence 50%, tilt bounded to 1% tracking error and 5 points per fund.
  3. `static_mix`: equity share = level share (40 / 60 / 80%), equity split by the policy prior's equity proportions and the rest by its fixed-income proportions, rebalanced monthly. This is the classic balanced-fund benchmark.
  4. `sample_mvo`: the plug-in (sample-mean) mean-variance with the same covariance, caps and calibration: the textbook foil.
  5. `equal_weight`: 1/N over the non-cash shelf funds (not risk-matched; reported for reference).
* Reported: annual return, volatility, Sharpe versus the cash sleeve, maximum drawdown, turnover, cost drag, realised versus target volatility, sub-periods 2020 and 2022, and paired t-statistics of monthly return differences (robokit vs each other strategy; robokit_trend vs robokit).

**Decision rules fixed now:**

* The trend tilt becomes an opt-in product feature only if `robokit_trend` beats `robokit` at level 3 in BOTH markets with a paired t-statistic above 2. Otherwise the tilt stays off and the product says it was tested and did not pass.
* Robo-Kit's default is not changed by any v2 result. If `robokit` loses to `static_mix` or `sample_mvo`, that is reported as found.
* Known biases, stated in advance: (a) the shelf is chosen with 2026 information (today's cheapest, largest funds), a mild selection bias; (b) proxies are real funds that existed at the time, but choosing them uses 2026 knowledge of which funds survived; (c) no delisted ETFs are in the data (survivorship), which matters little for broad index funds but is not zero.

**v2 results (run 28 Sep 2026, once, 82 s for CA and 136 s for US).** Level 3, Robo-Kit minus other strategy, annualised, after costs (t-statistic): Canada (Dec 2009 to Aug 2026): vs static mix -0.2% (-1.1), vs textbook +0.1% (0.1), vs equal weights +0.8% (1.3); trend minus base +0.2% (1.3). US (Jul 2018 to Aug 2026): vs static -0.2% (-0.7), vs textbook -1.5% (-2.1), vs equal +1.2% (1.1); trend minus base +0.5% (2.6). Decision rule: the trend tilt needed t > 2 in both markets at level 3; it passed in the US and failed in Canada, so it stays off. Realised volatility at level 3: 6.9% vs 6.8% target in Canada, 10.3% vs 8.7% in the US. Nothing was changed after these results.

**Correction after the independent code review (28 Sep 2026, same day).** The review found that `robokit/backtest.py` charged the 10 bps cost only on the monthly drift back to target, not on the move from one year's target to the next, although the protocol above says "cost on all turnover" (v1 charged both). The same review found gold and broad-commodity funds classed as equity, which changed the US gold sleeve's reference fund from IAUM to GLDM (same exposure, fee 0.10% vs 0.09%). Both were fixed and the back-test was re-run once with nothing else changed. The first run is kept in `output/v2/backtest_run1_before_review/`. Effect: every return moved by 0.03 points a year or less; turnover now counts the annual move (level 3 textbook optimizer: 2.6% a month instead of 0.8%). Level 3 results after the correction: Canada vs static -0.2% (t -1.1), vs textbook +0.1% (0.2), vs equal +0.8% (1.3), trend minus base +0.2% (1.3); US vs static -0.2% (-0.7), vs textbook -1.5% (-2.1), vs equal +1.2% (1.1), trend minus base +0.5% (2.5). No conclusion changed, and the trend tilt stays off.

## 7. Self-check scoring and projection window, v2.1 (written 28 Sep 2026, before the changes were run)

Why: seven persona walkthroughs (docs/qa/ux/) found that the capacity cap binds far too often and that the "bad year" figure never saw 2008. Changes, decided before looking at any new output:

1. Capacity deductions for share of savings (B4), uneven income (B5) and a partial emergency fund (A2) combine to at most 2 steps, and at most 1 step when the horizon score is 13 or more. Before: up to 3 separate steps (a 20+ year saver with a partial emergency fund could land on level 2).
2. B2 (how long withdrawals last) gets a "Not sure yet" option worth 3 points, the middle of its scale. When the goal is "building wealth, no fixed date" (A1 = wealth), B2 is not asked and scores 3.
3. Gate G1 ("needs the money within 2 years") fires only when the money is also taken out all at once (B1 = within 2 years and B2 = all at once). A phased drawdown is scored normally. B1's first option is relabelled "In less than 2 years".
4. The suggestion stays the lower of capacity and tolerance. It stops being a ceiling: a person may choose a higher level after a page sheet shows that level's bad year and crisis replays in their own dollars, and the choice is recorded. Gates G2 and G3 (no emergency fund, a lot of high-interest debt) still cap the build at level 2.
5. Projections (one-year range, bad year, ten-year paths, holding-period ranges, the range cards in the self-check) resample from the longest history where every fund in the mix has data, spliced and back-filled as disclosed, instead of the 15-year estimation window. For the reference funds that history starts in the mid-2000s and includes 2008. The weights are still estimated on the 15-year window. Satellites are back-filled over the same long history so crisis replays stop disappearing.

Not changed: the pre-registered back-test (section 6), the optimizer, the level-to-volatility mapping.

## 8. Addendum to section 7: changes made while fixing the round-2 persona findings (29 Sep 2026)

These change what the page shows or how it asks, not the scoring rules in section 7 or the back-test. Each was decided from a reproduced finding (docs/qa/ux/round2/RANKED.md) before looking at new output.

1. B5 (income) gained a fifth option, "a pension or other guaranteed income", worth 2 points (the same as "mostly steady"). Retirees had no truthful answer (RANKED F73). Scoring for the other four options is unchanged.
2. The ladder behind the self-check scenarios, the level chooser and the explore sheet is now built from the person's own request (their funds, amount, monthly flow, horizon, and the same 200 resampled histories and seed as the mix), not from the reference funds on $10,000 with 100 histories. Before, the sheet could quote a bad year $3,735 away from the mix built a moment later (F11). The reference ladder in the Python tools (`risk_ladder`) is unchanged.
3. Year-end ranges in the scenarios, the headline and the chooser include the monthly flow (the value after 12 months of adds or withdrawals), and the bad year is also shown as a loss against zero returns (F12, F62). For withdrawal plans, the chooser, sheet, preview and mix show how often the money lasted (F13).
4. The projection horizon follows the answers until the person sets it: withdrawals use how long they last (B2: 2, 5, 10 or 25 years; 20 when unsure), savers use the time to the first withdrawal (B1: 2, 4, 8, 15 or 25 years). It was 10 years for everyone.
5. The explanation line about the fund with the largest risk share says "but" only when its risk share exceeds its money share by more than 2 points; otherwise it says the two are in line (both engines; F72).
6. (Round 3, written before the change was run.) A young satellite is back-filled by regression on the core funds over the months where every core fund has data. In the US list one core fund, BNDX (international bonds), starts in 2013-07 with no stand-in, so every US satellite was back-filled only to 2013 and a mix holding one (5% BITO) had its ranges and bad year computed on 2013-2026, without 2008: its bad year looked a third smaller than the same mix without BITO (round-3 finding P4-01). Rule: a core fund whose history starts more than 36 months after every other core fund is left out of the regressors. For the US list that drops BNDX (starts 103 months after the next latest); the Canadian list is unchanged (the latest start, VALT, is 13 months after the next). The weights' 15-year estimation window is not affected, and the stress replays keep marking such months "estimated before the fund existed".
7. (Round 3.) For a plan with monthly adds or withdrawals, the explanation's one-year sentence uses the year-end values that include the flow (the same figures as the page headline) and says so ("with $1,500 a month taken out"). Withdrawal results add the median month the money ran out (`p50_months`). The fee-cost checks say that withdrawals make the real cost lower. The explanation says both the target and the reached volatility when the optimizer cannot reach the target.
