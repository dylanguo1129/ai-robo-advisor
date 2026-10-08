# Optimizer v3: production-grade engine and research paper

*Design spec, 8 Oct 2026. Inputs: a four-lane research sprint (code audit with reproductions, published industry methodology, 67 verified papers, a digest of this repo's own research commitments) and two cross-family outside reviews. Raw notes are kept outside the repo; the decisions and their sources are below.*

## Goal

Make the engine safe and complete enough for a regulated robo-adviser to run, without changing the core method that the earlier research chose and tested, and rewrite the optimizer report as a research paper whose every number is produced by code.

## What does not change

The core method stays: equilibrium expected returns from the written policy mix, Ledoit-Wolf shrinkage (QIS when N/T > 0.25), long-only mean-variance with guardrails, lambda calibrated to level x 20% of stock-market volatility, stationary-bootstrap resampling, the 2% minimum position. The level policy (suggestion = lower of capacity and tolerance; the person chooses) is unchanged by default; README asks for the owner's approval before it changes. Cash caps by level stay: the cash sleeve is a T-bill ETF earning the market bill rate, not low-yield sweep cash, and the paper explains this. Commitments in RESEARCH_LOG hold: no default changes because of a back-test result, pre-register before running, run once, count what was tried, never delete outliers (flag; a fund with a corrupt series is refused, its data is not altered).

## Track A: correctness and safety (fail closed)

| # | Change | Why (evidence) |
| --- | --- | --- |
| A1 | One `validate_request` at the engine boundary (Python and JS): finite level in [1, 5]; 0 < target_vol <= 1; integer years >= 1; amount > 0; known market; minimums >= 0, summing to at most 1, not on excluded funds; caps in (0, 1]; bounded n_boot and min_weight. Raise `RoboKitInputError`; `tools.call` returns it as a message. | NaN level builds a 100% equity mix; years = 0 raises an uncaught ZeroDivisionError (audit). |
| A2 | Level label: clamp to 1..5 and round half up, the same rule in both engines. | K1 KeyError for target_vol <= 0.1 sigma_eq; Python and JS disagree at half levels. |
| A3 | Infeasible limits refuse by default (`RoboKitInfeasible` with the limits that conflict and the smallest fix). An explicit `on_infeasible="relax"` relaxes in a fixed order (satellite group cap, sleeve caps, per-fund cap, cash cap) and records every step in `relaxations`, `notes`, `checks` and `method` (requested vs applied). Group-cap expansion in the solver follows the same policy. | K3: caps silently scaled up (gold + REIT list held 50% each), satellite cap 20% held 46%; MSCI/Axioma report every violation; Grok: refuse by default. |
| A4 | Views: after the bounded tilt, enforce the 2% minimum by searching the largest tilt scale s in [0, s_max] whose cleaned weights keep TE <= 1% and |dw| <= 5 points; record the method as Black-Litterman (bounded). | K2: XRE 1.78%, VALT 0.01% after a tilt. |
| A5 | Fail closed: SLSQP and FISTA report convergence; a non-converged solve raises; no hard-coded 15% stock-market volatility (fall back to the reference shelf's equity sleeves over the same window, with a note); NaN checks on returns and Sigma. | Audit; Grok item 4. |
| A6 | Data-integrity gate for the funds in a request: a month whose return is beyond an asset-class bound and far from the same-month peer median marks the fund unusable, with the month and size in plain words. | HSH.TO +104.6% in Jul 2021 gives it 38% volatility; ZCSH (cash) +393%. |
| A7 | `min_weight` that would drop every fund keeps the largest positions instead of silently re-solving on all funds. | Audit. |

## Track B: one model, two runtimes

| # | Change | Why |
| --- | --- | --- |
| B1 | One random generator in both engines (mulberry32 with the same seeding and the same geometric-block algorithm), for resampling and for projections. | Same request: Python bad year -18.9%, browser -22.7% (US level 5). |
| B2 | Port QIS to the browser engine, so both pick the same estimator. | Wide US list: 6-point weight gap. |
| B3 | Parity tests on resampled weights, projections, views, target-vol requests, both markets, wide lists. | Only point-estimate weights were tested. |
| B4 | More projection paths with the Monte Carlo standard error reported. | Bad-year SD of 1.6 points across seeds at 2,000 paths. |

## Track C: implementation layer

| # | Change | Why |
| --- | --- | --- |
| C1 | `rebalance`: from current holdings, prices and a cash flow to a trade list. Cash flows first (buy underweights / sell overweights), tolerance bands with a defined destination, whole units, minimum trade size, residual cash placed to stay closest to target, an estimated cost and an ADV participation flag. Python and JS. | Vanguard 2010/2024 bands, cash-flow rebalancing (Betterment, Wealthfront, Wealthsimple); Donohue-Yip 2003 no-trade region. |
| C2 | NI 81-102 Appendix F risk rating for every mix (10-year standard deviation bands). | Regulation; open item R3.7. |
| C3 | Opt-in suitability enforcement (`enforce_suitability`): with scored answers, the build is capped at the suggestion unless an explicit acknowledgement is recorded. Default behaviour unchanged. | CSA/CIRO 31-368; level policy kept. |
| C4 | Model card and monitoring plan (OSFI E-23 style): purpose, limits, validation evidence, monitored metrics with breach thresholds (realised vs target volatility, weight drift, data integrity), change log. | OSFI E-23 (effective 2027). |

## Track D: risk-target accuracy (decided before any new test)

D1. Calibrate lambda on the final pipeline (resampled, min-position applied) with the same random draws at every step, so every level hits its target within 0.01 points when reachable. Reason: Scherer (2002) critique of resampled portfolios drifting off target; the report's own level-5 miss. Decided on principle, not on a back-test.

## Track E: v3 evaluation (pre-registered in RESEARCH_LOG section 9 before it runs, then run once)

1. Walk-forward of the shipped configuration (expanding window from 60 to 180 months, 200 draws, final-pipeline calibration), CA and US, levels 2-4.
2. Benchmarks: static mix, equal weights, minimum-variance plus cash calibrated to target, equal risk contribution plus cash calibrated to target, Bayes-Stein mean-variance, and the textbook optimizer on an expanding window (not only 60 months).
3. Ablations, one component removed at a time: no resampling, sample covariance, no caps, sample means instead of equilibrium.
4. Statistics: Ledoit-Wolf (2008) studentized block-bootstrap test for Sharpe differences, block-bootstrap intervals for realised/target volatility, Holm adjustment across the comparison family, deflated Sharpe ratio for any apparent winner, minimum track-record length.
5. A simulation study with known truth (returns drawn from a model calibrated to the data): certainty-equivalent loss against the true optimum, volatility-target error, turnover and weight stability, for the method, its ablations and the benchmarks.
6. Covariance estimator comparison (constant correlation, single index, identity, QIS, sample) by the realised volatility of minimum-variance and target portfolios, with a pre-set rule for changing the default (economically significant and significant in both markets).
7. Sensitivities: block length 3/6/12 (plus the Politis-White estimate), delta, window, policy mix alternatives, cap levels.

## Track F: the paper

A research-paper structure (abstract, contributions, literature, data, method, evaluation design, results with intervals and tests, simulation study, robustness, implementation and governance, limitations, conclusion, references, appendices with derivations). Every number is read from `output/v3/results.json` written by one script, so the number check is mechanical. Adversarial validation: referee lanes (methodology, statistics, practitioner, reproducibility, course alignment) including two cross-family reviewers, repeated until a round finds nothing new.

## Tests

Property tests on random requests: weights sum to 1; every position is at or above the minimum or forced; limits hold or the request is refused (or relaxations are recorded when relaxing was asked for); labels defined; no uncaught exceptions; Python and JS agree. Regression tests for each audit finding. Back-test regression before any engine change ships.

## Delivery

Branch `optimizer-v3`; commits per track; pull request with CI; merge after CI passes. Version 3.0.0. Docs: METHOD.md (v3 section), RESEARCH_LOG.md (section 9), VERIFICATION.md, MODEL_CARD.md, README known limitations.
