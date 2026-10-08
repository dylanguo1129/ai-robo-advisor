# Design decisions and their evidence

Every design decision in the optimizer is listed here with the evidence behind it. The rule: a decision stands on a
**verified source** (a paper, regulator text or asset-manager research that was opened and quoted), on a **proof**
(a derivation in the paper, checked numerically by a test), or on a **test we ran** (a unit or property test, or a
pre-registered evaluation in `docs/RESEARCH_LOG.md` section 10). Where a decision is a **policy** (a choice the product
owner makes, such as a cap), it says so, and the test shows how much the result depends on it. Nothing is marked as
evidence until it has been checked; a source quoted from a summary rather than the original says so.

Status: **done** (the evidence exists and the test passes), **E1 ... E7** (pre-registered; the result is added here
after the single run), **policy** (owner's choice, with its sensitivity test).

Inventory: an independent reviewer listed 53 decisions from the code and docs (8 Oct 2026). This register covers all
of them and the ones added since (rebalancer, regulator rating, suitability checks, calibration algorithm).

## 1. Data

| # | Decision | Value | Evidence | Status |
|---|---|---|---|---|
| D1 | Monthly total returns from dividend- and split-adjusted month-end closes; the current month is dropped; gaps stay gaps | | Test: gaps are never filled (tests/test_v3_fixtures.py); each reference fund's 5-year return against the issuer's published figure (E7(e): after the run, outside the script) | E7(e) |
| D2 | Cash before an ETF existed earns last month's 3-month bill yield / 12; the risk-free rate is the latest yield | Bank of Canada V80691344; US ^IRX | Source: the official yield series | done |
| D3 | A young core fund is extended with a written stand-in only if they overlap 24+ months with correlation 0.8+; currency hedging matched | | Policy (data quality), disclosed with every result; the evaluation's look-ahead from it is removed in E2 (no stand-ins) | E2 |
| D4 | A young own pick is back-filled by ridge regression on the core funds plus resampled residuals | ridge 1e-4 tr(X'X)/k, 36+ months overlap | Policy; affects own picks only (not the reference mix or any evaluation). Test: 20 mature funds per market with their first 60 months hidden and back-filled, against the hidden truth and the home stock fund as the simple alternative (E8(b)) | E8(b) |
| D5 | Estimation window: the latest 180 months every fund has | 180 | Test: 120 and all months against the 180 default (E5) | E5(w) |
| D6 | At least 36 months of common history, or the build stops | 36 | Test of the gate: 35 shared months refused, 36 built (tests/test_v3_research.py). Sensitivity: known-truth simulation with 36 / 60 / 120 / 180 months | done; E3(i) |
| D9 | Data-integrity screen: a month in which a fund's log return is at least ln 2 in size and at least ln 2 away from the median of its market and asset class (at least five funds with data that month, itself included) marks it ineligible (crypto exempt) | ln 2 | Test: thresholds ln 1.5 / ln 2 / ln 3 and the funds each flags; the 14 exclusions listed with month and peer move; the stricter reading with the fund left out of its peers | E7(a) |

## 2. Universe and reference shelf

| # | Decision | Value | Evidence | Status |
|---|---|---|---|---|
| D7 | Liquidity screens | 36 months history; AUM 20M CAD / 50M USD; daily value traded 50k CAD / 250k USD | Policy; test: every reference fund's margin over each screen | E7(c) |
| D8 | No leveraged, inverse, single-stock or depositary-receipt funds | | Source: CSA Staff Notice 31-342 (online advisers use "unleveraged exchange traded funds"), docs/research/regulation.md R5.4 | done |
| D10 | Crypto, thematic, covered-call and other narrow funds are own picks only (satellite caps), never a core slot | | Source: 31-342 as D8; test: tests/test_v3_exam_r1.py (a crypto fund cannot take a core slot) | done |
| D11 | One broad, low-cost fund per slot, chosen by a written rule | robokit/shelf.py | Policy; tests: every slot's top five candidates checked as broad, low-cost index funds (E7(e): after the run, outside the script); the slots that change when the score's coefficients move (E5) | E5, E7(e) |
| D12 | The ranking score | +1.0 log AUM, +0.5 log volume, -1.5 fee, +0.5 history | Policy; test: each coefficient +/-50%, slots whose fund changes | E5 |

## 3. Expected returns

| # | Decision | Value | Evidence | Status |
|---|---|---|---|---|
| D13 | Equilibrium returns from a written policy mix, not from fund sizes or past returns | 60% stocks, 35% bonds, 3% real estate, 2% gold | Source: Sharpe (1974) and He and Litterman (1999) for reverse optimisation; Doeswijk, Lam and Swinkels (2014): the market portfolio is "a natural benchmark for investors". Test: alternative priors | E5(w) |
| D13b | 30% of equity in Canada | 0.18 / 0.60 | Source: Vanguard Investments Canada (25 June 2024): "a reasonable equity balance of around 30% home bias, in Canadian securities"; Canada is about 2.7% of world equity. The full report (minimum-variance analysis) is no longer online; its finding is quoted from press coverage only. Test: 0 / 20 / 40% against the 30% default | E5(w) |
| D17 | pi = delta Sigma w_prior | | Source: Sharpe (1974); Black and Litterman (1992); He and Litterman (1999) | done |
| D18 | delta = 2.5 | | Source: He and Litterman (1999): "we use delta = 2.5 as the risk aversion parameter representing the world average risk tolerance". Proof: with lambda calibrated to a volatility target the weights do not depend on delta (paper, Proposition 1); tests: at fixed lambda / delta the weights are identical, in the optimizer and through the final pipeline, single solve and resampled (tests/test_v3_propositions.py); calibrated at delta 1 and 4, the model volatility agrees within twice the calibration tolerance (the same file, and E5) | done; E5 |

## 4. Risk model

| # | Decision | Value | Evidence | Status |
|---|---|---|---|---|
| D15 | Ledoit-Wolf constant-correlation shrinkage; QIS when N/T > 0.25 | | Source: Ledoit and Wolf (2004, 2022). Test of the switch point: simulation with a pre-set rule (E3(ii)). Descriptive: the four estimators walk-forward (E4; no back-test result changes a default) | E3, E4 |
| D16 | Monthly covariance x 12; the shrunk matrix x T/(T-1) | | Proof: scaling Sigma scales pi by the same factor, so the weights at a given lambda do not change; only the risk yardstick moves (0.28% at T = 180), consistently with the n-1 market volatility it is compared with (paper, Proposition 2); test: tests/test_v3_propositions.py | done |

## 5. Objective and constraints

| # | Decision | Value | Evidence | Status |
|---|---|---|---|---|
| D19 | Long-only, fully invested mean-variance | max mu'w - (lambda/2) w'Sigma w | Source: Markowitz (1952); the course's Session 1 formulation | done |
| D20 | Per-fund maximum and sleeve caps | 50%; REIT, gold, high yield 10%; EM, small cap 15%; real return 20%; long bonds 25% | Policy (concentration guardrails). Source for why constraints help: Jagannathan and Ma (2003). Test: no-caps ablation (E1) and caps halved / doubled (E5) | E1, E5 |
| D21 | Cash cap by level | 100% at level 1, 30% at 2, 15% at 3-5 | Policy; test: no-caps ablation | E1 |
| D22 | Own picks: 10% each, crypto 5%, all together 10 / 20 / 30% by level | | Policy; tests/test_v3_review.py, tests/test_v3_properties.py (limits always hold) | policy |
| D23 | Minimum position | 2% | Source: Gurobi Finance documentation, "Holding tiny positions is undesirable because they have a marginal, if any, impact on the expected return but can lead to non-negligible transaction costs" (partial: cost, not diversification). Test: 0 / 1 / 5% against the 2% default (E5) | E5 |
| D38 | Limits that cannot all hold are refused; relaxing is opt-in, in a fixed order, every step recorded | | Policy (fail closed); tests/test_v3_safety.py, tests/test_v3_review.py | done |

## 6. Risk levels and suitability

| # | Decision | Value | Evidence | Status |
|---|---|---|---|---|
| D25-27 | Self-check: capacity, tolerance, gates; the suggestion is the lower of capacity and tolerance | | Source: 31-103CP s.13.2 ("the lower of" willingness and ability); Joint CSA/CIRO Staff Notice 31-368; tests: persona walkthroughs (docs/qa/ux) and the scorer tests in tests/test_v2.py; the browser scorer matches Python on 400 random answer sets (web/test_robokit.mjs) | done |
| D24 | The brief's three settings are levels 2 / 3 / 4 | | Policy; names in both directions (tests/test_v3_exam_r1.py) | done |
| D28 | Level L targets L x 20% of the stock market's volatility | | Source (partial): Betterment matches risk levels "on volatility". Test: realised over target volatility by level (E1); the regulator's rating of each level | E1 |
| D29 | The stock-market yardstick: the policy-weighted equity slots over the same window | | Policy; test: the yardstick replaced by the home stock fund alone, at the latest date and walk-forward (E5) | E5 |
| C2 | Every mix shows its NI 81-102 Appendix F rating | 10-year standard deviation of monthly returns x sqrt(12), five bands | Source: NI 81-102 Appendix F, Items 1 and 2 (opened); tests/test_v3_rating.py | done |
| C3 | Suitability checks are opt-in (off by default) | | Source: 31-103CP s.13.2; README's level policy; tests/test_v3_suitability.py | done |

## 7. Calibration

| # | Decision | Value | Evidence | Status |
|---|---|---|---|---|
| D30 | First, lambda for the single solve: bisection on log lambda | [0.05, 2000], ratio 1.002 | Proof: the single solve's volatility falls as lambda rises (paper, Proposition 3) | done |
| D31 | Then lambda for the mix the person gets (resampled, minimum position applied, the same draws every step): bracket, then Illinois regula falsi with a bisection safeguard | tolerance 0.005 percentage points of volatility (5e-5); bracket 1e-5 in log lambda; at most 30 evaluations | Source: Scherer (2002) for why; Dowell and Jarratt (1971) for the method. Test: 40 random single-solve requests and five resampled ones end within tolerance, at a proven jump or at a bound, each jump and bound re-checked by rebuilding at the lambdas its evidence names (tests/test_v3_calibration.py); in E1 any `limit` is listed as a failure. Test of the benefit: against single-solve calibration | done; E1 |
| D32 | A note when the final mix is more than 0.5 percentage points of volatility from target | | Policy (what is worth telling a person) | policy |

## 8. Resampling

| # | Decision | Value | Evidence | Status |
|---|---|---|---|---|
| D33 | Average the weights over stationary-bootstrap histories | 200 draws, mean block 6 months, seed 0 | Source: Michaud (1989), Politis and Romano (1994); critiques Scherer (2002), Harvey et al. (2008). Test: ablation (E1) and a known-truth simulation with a pre-set keep/drop rule (E3); block lengths and Politis-White (E5); Monte Carlo spread at 100 / 200 / 500 draws (E5) | E1, E3, E5 |
| D34 | One random generator in both engines | mulberry32 | Test: bit-exact against the browser (tests/test_v3_parity.py) | done |
| D35 | The 5-95% band of each fund's resampled weights | | Labelled as the spread of the resampled weights, not a confidence interval. Test: coverage of the true weights in the simulation | E3 |

## 9. Views (off unless a person gives one)

| # | Decision | Value | Evidence | Status |
|---|---|---|---|---|
| D36 | Black-Litterman with Idzorek confidence | tau 0.05; confidence 50% if not given | Source: Black and Litterman (1992); He and Litterman (1999); Idzorek (2007); Walters (2014) closed form | done |
| D37 | The tilt is bounded | 1% tracking error, 5 points per fund, every limit | Source (partial): Jorion (2003) for tracking-error limits; the thresholds are policy. Test: tests/test_v3_review.py (limits always hold) | policy |

## 10. Solver

| # | Decision | Value | Evidence | Status |
|---|---|---|---|---|
| D39 | FISTA with diagonal preconditioning and adaptive restart; exact projection onto the capped simplex (breakpoints) | step 1/L, L = lambda x the largest eigenvalue | Source: Beck and Teboulle (2009), O'Donoghue and Candes (2015). Proof: the projection's KKT conditions (paper, Appendix). Tests: against bisection on 2,000 cases; against SLSQP; a convergence certificate (projected-gradient residual under 1e-6) | done |

## 11. Projections and crisis replays

| # | Decision | Value | Evidence | Status |
|---|---|---|---|---|
| D41 | Canadian planning returns | FP Canada 2026 | Source: FP Canada / IQPF 2026 Projection Assumption Guidelines | done |
| D42 | US bonds and cash: today's Treasury yields | 13-week bill; 5-year note | Source: T. Rowe Price (2018): for the US Aggregate, "peak correlation reaches 0.97 at a time period of 1.08 times the initial duration" | done |
| D43 | Re-centre the history on the planning return, made arithmetic | g + variance / 2 | Source: FP Canada guidelines ("a conversion needs to be done from geometric to arithmetic mean") | done |
| D44 | 2,000 paths, stationary bootstrap, mean block 6 months, seed 7 | | Test: Monte Carlo standard error with a pre-set rule to raise the paths | E5 |
| D47-48 | Seven fixed crisis replays; a fund without the episode uses its peers' median | | Policy (episodes); test: the stand-in's error on funds that have the episode | E7(b) |

## 12. Rebalancer

| # | Decision | Value | Evidence | Status |
|---|---|---|---|---|
| D49 | Bands with a destination | min(2 points, 25% of target); back to 7/8 of the band | Source: Vanguard (2024) "a threshold of 200 bps and a destination of 175 bps"; Donohue and Yip (2003) "back to the boundary of the no-trade region". Test: against monthly and annual | E6 |
| D50 | Cash flows first | | Source: Vanguard (2010) "Rebalance with portfolio cash flows"; tests/test_v3_rebalance.py | done |
| D51 | Minimum order and cost | $50; 10 bps | Policy (cost as in every back-test); source for small trades as D23. Test: the shipped bands with minimum orders of 0, 50 and 250 on three account sizes (E6) | E6 |
| D52 | Flag orders over 1% of daily volume | | Source (partial): Toth et al. (2011), impact = Y sigma sqrt(Q/V); at Q/V = 1% that is a tenth of a day's volatility, about the 10 bps cost assumed for a fund moving 1% a day. The threshold itself is policy | policy |

## 13. One model in two runtimes

Python and the browser engine are tested against each other on every reference case (point and resampled weights,
bands, projections, notes, checks, calibration (the same outcome and steps; at a jump the two engines may take one or two
steps more or fewer and stop at different brackets, each checked to straddle the target), the regulator rating, the
rebalancer on 51 accounts, QIS on
generated inputs): web/test_robokit.mjs, web/test_engine.mjs, web/test_safety.mjs.

## Examination record

Two outside examiners from different model families (cross-family, so neither shares the author's blind spots) were
asked to question every part of the optimizer as a professor would, from finance, quant and mathematical angles.
Their findings and the rulings on them, after each claim was checked against the code:

**Round 1 (8 Oct 2026), on the code and the earlier report.** 15 questions and 9 bug reports after merging duplicates.

| Finding | Ruling | Action |
|---|---|---|
| Final-pipeline calibration was not tested | true | single-solve ablation (E1); calibration sweep |
| The report describes the old method | true | the paper is rebuilt from the v3 results |
| The covariance rule and its 0.25 switch are untested | true | E4 and E3(ii) with pre-set rules |
| T/(T-1) on Ledoit-Wolf is ad hoc | partly true | Proposition 2; numeric check (E5) |
| delta and the policy prior are conventions | delta false, prior true | Proposition 1; sources and E5 for the prior |
| Resampling is unproven | true | ablation and simulation with a keep/drop rule |
| A swap could put crypto in a core slot | true | fixed and tested in both engines |
| The browser step size used a power-iteration estimate x 1.02 | true | exact eigenvalue in both engines |
| A legacy browser class scaled caps silently and skipped QIS | true | retired |
| Rescaling after the clip can break bounds | partly true (1e-16) | hardened and tested |
| A named-ETF mix for a profiled user is advice | true, a deployment question | the paper states the registration route |
| v2 used naive t-statistics | true | Ledoit-Wolf (2008), Newey-West, Holm |
| Look-ahead in the back-test | true | as-of modes, invariance test, point-in-time shelf (E2) |
| The weight bands are not confidence intervals | true | relabelled; coverage in E3 |
| Eight secant steps do not guarantee the target | true | bracket + Illinois; every miss proven |
| The textbook benchmark changes both mu and Sigma | false for the reported back-test | none (v1 harness only) |
| Rebalancer cash ignores costs | true | fixed |
| A list where a map belongs crashes | true | fixed |
| low / high presets are ambiguous | partly true | aliases in the brief's terms |

The tests written for these also found two browser bugs the examiners did not report (a fund filling two slots was
optimized twice; the dropped-funds note depended on the round), both fixed.

**Stage 1 (8 Oct 2026), on the evaluation plan before it ran.** One examiner: accept after required changes; the
other: reject until a revised plan is reviewed again. The rulings, and what changed in RESEARCH_LOG section 10:

| Finding | Ruling | Change |
|---|---|---|
| The runner and its tests were not frozen | true (the invariance test existed but was not in the review copy) | runner, library and tests committed before the run; commit, clean tree and data snapshot recorded; a calibration `limit` counts as a failure |
| Rules that change defaults ran alongside E1, so E1 might not test what ships | true | E3 runs first and locks the defaults; E4 (a back-test) is descriptive only |
| Fixed-mode stand-ins pass their check on later data | true | kept as the fixed-shelf design, and disclosed exactly; E2 removes it |
| E2 is not a point-in-time shelf (the list, eligibility and score inputs are today's) | true | renamed "past returns, today's universe"; no conclusion about fund selection |
| "No benchmark significantly beats robokit" rewards an underpowered test | true | confirmatory family limited to the four risk-matched benchmarks; a 0.10 Sharpe non-inferiority test; the minimum track record beside every difference; a power statement written in advance |
| "The interval contains 1" can pass with no precision | true | ratio defined (returns over the target in force); "delivered" only if simultaneous intervals lie inside [0.80, 1.25] |
| The QIS rule searched the grid | true | three primary one-sided tests, Holm-adjusted, two truths that must agree, a monotone rule |
| The simulation could not test block resampling; methods had different targets | true | the full data-generating process written down; a regime-switching world; common random numbers; certainty-equivalent loss at the level's risk aversion; 500 replications with standard errors |
| E4 used uncentred squares and tested a different problem | true | past-only centring; both the minimum-variance and the shipped target-risk portfolios; a fixed-weight forecast check; descriptive |
| E6 used fractional units | true | the production rebalancer on simulated accounts (whole units, contributions, minimum order) against the fractional ideal |
| The deflated Sharpe trial count was undefined | true | N = 54, enumerated |
| Decisions still without evidence (section C of both reviews) | mostly true | added: stand-in and back-fill hold-outs (E8), the cash-cap ablation, per-fund maximum and yardstick sensitivities, minimum order 0/50/250, the crisis-episode rule, classification and shelf audits, unit fixtures (tests/test_v3_fixtures.py); the self-check vignette study is scoped out as the suitability layer |
| Subperiod tail risk from one year of data | true | removed; full-sample CVaR with its tail count |

**Stage 1, second round (8 Oct 2026), on the revised plan and its code.** One examiner: accept after required
changes; the other: reject before execution (its captured review held only an addendum of six blockers; it reviews
again in full). The rulings, after each point was checked against the repository:

| Finding | Ruling | Change |
|---|---|---|
| The data layer (robokit/data) is missing | false: present in the repository, left out of the review copy; the dry run and smoke runs import it | the next review copy includes it |
| E3's truths use months that E1 later tests | true | truths built only from months before each market's first E1 estimation date (computed by E1's own rule) |
| E6 used synthetic prices starting at 100 | true | real adjusted closes at their price levels |
| The "annual" rule could still trade between Januaries | true | no band can trigger outside January |
| The largest-order share of volume was computed, not measured | true | measured from the orders the shipped bands place on a 1,000,000 account |
| The projection-path rule was not executed, and 0.25 points is 0.0025 | true | applied by the code and recorded with the locked defaults |
| The confirmatory readings were left to a person | true | written into results.json by code, from the pre-registered rule |
| The US 60/40 prior missed two bond slots | true | slots by asset class; every prior variant must sum to one |
| E8 converted a stand-in that the engine uses unconverted | true | each stand-in tested exactly as the engine uses it |
| The jump screen's "five peers" include the fund itself | partly true: the code is consistent, the description was not | description corrected; the stricter reading reported in E7(a) |
| "All months" was coded as 300; a missing return counted as flat; median error by asset class, and the ex-ante gap per strategy, missing; untracked files ignored; two evidence mappings wrong (D1, D11) | true | all fixed |

**Stage 1, third round (8 Oct 2026).** One examiner: accept after four required changes; the other's captured review
again held only an addendum (four required changes and one recommendation); it reviews once more in full.

| Finding | Ruling | Change |
|---|---|---|
| An infinite minimum track record (robokit not ahead) was read "too short to tell" | true | "inconclusive" then; "too short to tell" only when robokit is ahead but the sample is short; a "robokit better" reading added for symmetry; every branch tested |
| Provenance did not check that git worked | true | refuses without a git checkout and a full commit id |
| The registered run accepted any number of simulated histories | true | refuses anything but 500 |
| A missing path crashed E1 instead of being recorded | true | recorded; comparisons that need it carry the error |
| E6 returns left out trading costs | true | time-weighted returns after each month's costs |
| E3's oracle ignores the 2% minimum | partly true: a valid oracle whose loss includes the cost of discretising, which cancels in the resampling rule's paired differences | stated in the plan; a second oracle with the minimum-position rule reported too |
| E3 lacked paired contrasts for the other methods | true | paired contrast table (mean, Monte Carlo SE, pairs) |
| Band coverage left out funds the minimum position dropped | true | every fund counts (a dropped fund's band is [0, 0]); fixture with a dropped 1% position |
| The ESG coefficient was not varied | true | varied on the ESG shelf |
| D28 cited a rating E1 did not compute | true | E1 now reports the Appendix F rating of each level's realised path |

**Stage 1, fourth round (8 Oct 2026).** One examiner: accept after six required changes; the other's captured review
again held only an addendum (four required changes and one bug). The capture kept only the agent's last message; the
next round records every message.

| Finding | Ruling | Change |
|---|---|---|
| The round-2 "annual" fix still sold a fund whose target is zero (its band is zero) | true | a bands-off switch in both engines (`band_trades`); the annual rule uses it between Januaries; tested, with three parity cases |
| E7(b) scored a different stand-in rule from the replay's (no fallback, at least three peers) | true | one rule, `standin_peers`, used by both; the fund itself left out; funds with no peer counted; tested against the replay rule |
| A missing benchmark path crashed the deflated Sharpe and the calibration ablation | true | both use only the paths that exist and say so |
| Holm ran over fewer than 12 comparisons when a path was missing | true | always the registered 12, a missing comparison entering with p = 1 |
| The QIS truths could rest on fewer than 120 joint months | true | exactly the 120 months before 2019, from funds complete over all of them; the run refuses otherwise |
| A failed December build let the previous weights run for 24 months | true | a scheduled date without its build stops the path, recorded; so does a missing month (E2's registered leading skips excepted) |
| An infinite minimum track record was written as null | true | written as "inf" |
| D15 cited E4 as a test with a rule; D6 cited E3(i) for the 36-month gate | true | D15: E4 is descriptive; D6: the gate tested at 35 and 36 months |
| The plan still said "full extended history" for E3's truth | true | one definition: months up to the first E1 estimation date |
| path_errors lacked market and stage | true | added |
| E2 lacked the 2020 and 2022 subperiods | true | added |
| E4's target-risk loss was centred on the full-sample mean (later months moved earlier losses) | true | centred on the mean the weights in force predicted from the funds' past 180 months |
| D31 cited 120 random requests; the test has 40, single-solve, and accepted the outcome label | partly true: 40 is the committed number (120 was an earlier probe), and the label alone proved nothing | each jump or bound carries its evidence in both engines, re-checked by rebuilding at the lambdas it names; five resampled requests added; any `limit` listed in E1 |
| A rating on fewer than 120 months was labelled an Appendix F rating; tests/test_v3_rating.py absent | partly true: the build already said how many months it used; the test file exists but was left out of the review copy | an `appendix_f` flag (120 months or not) in both engines; 119/120-month boundary tests; the plan labels a short path an estimate; the review copy now has every test |
| (Found by the authors' own smoke run, not by an examiner) E8(a) compared each slot's reference fund with itself, because the stand-in chain starts with the fund: a NaN correlation for five funds | true | the fund itself skipped; a test that every row compares two funds and every statistic is finite |

**Stage 1, fifth round (8 Oct 2026).** Both reviews were captured in full. The usual second examiner's model pool had
reached its monthly limit, so the second review came from a third model family, on the same brief and the same copy.
Both examiners: accept after required changes (two each, no overlap).

| Finding | Ruling | Change |
|---|---|---|
| A missing robokit path (even at level 1 or 5) returned early, dropping ratings, risk delivery, deflated Sharpe ratios and calibration counts the plan registers | true | every registered output computed from the paths that exist; a comparison without its paths enters Holm with p = 1 |
| E6's summary dropped the month the starting cash is invested, so its cost left the return but stayed in total cost | true | that month is chained into the first invested month (the cost stays in the return; no month out of the market counted); tested |
| A month without a cash return was treated as a zero rate | true | fails closed: describe and compare raise, the runner records the error |
| A series with no variance would divide by zero in compare | partly true: numpy gives an infinite Sharpe ratio, not an exception, but silently | compare raises; recorded |
| The deflated Sharpe ratio stores monthly Sharpe ratios beside annual ones | true (labelling) | labelled in the results |
| E2's "skipped" counted every build failure, not the registered leading skips | true | `leading_skips` listed apart from `build_failures` |
| The register pointed to RESEARCH_LOG section 10, which was not yet in the file; METHOD said 500 resampled histories; the design spec said 0.01 points | true | sections 9 and 10 now in RESEARCH_LOG; METHOD says 200; the spec notes 0.005 |
| D18's test fixed lambda / delta but the plan claimed a calibrated test | true | a final-pipeline test at fixed lambda / delta and a calibrated check at delta 1 and 4 |
| "Too short to tell" could be read with robokit behind | partly true: compare cannot produce a finite minimum track record with robokit behind (both Sharpe ratios use the same months, and the n - 1 correction scales both alike), but the rule relied on that | the reading checks the sign itself; tested |
| E7(e) is in the plan but not in the script | partly true: the plan put it after the run, by a research lane, but did not say the script does not produce it | the plan and D1, D11 say so |
| E3's rules used normal critical values | true (a 0.2% difference at 499 degrees of freedom) | Student t |
| D13b listed a 30% home-bias test that is the default itself | partly true | worded as 0 / 20 / 40% against the 30% default |

**Stage 1, sixth round (8 Oct 2026).** Both examiners (the same two model families as round 5, fresh sessions): accept
after required changes.

| Finding | Ruling | Change |
|---|---|---|
| A default could lock on fewer than 500 pairs if a replication failed | true | a locking rule runs only on its full sample; otherwise the run stops and nothing is locked |
| The projection-path default was recorded per market | true | one number for the product (5,000 if either market needs it) |
| The interval's coverage check was in a test, not in results.json | true | computed by the run (1,000 samples, at the nominal 90% and at 96.7%) and written to results.json |
| The plan said the truths use months "before" the first estimation date; the code includes that month, and the windows were not checked | true (wording; E1 tests only later months, so nothing leaks) | "up to and including"; the run stops unless the truths use the registered windows |
| D16's status ignored its committed test | true | done; E5 |
| The calibration tolerance should be 0.005, not 5e-5 | false: the registered tolerance is 0.005 percentage points of volatility, which is 5e-5 as a decimal; 0.005 as a decimal would be 0.5 points, a hundred times looser. The wording invited the misreading | units written out in the plan, the register and the code |
| D18's calibrated check uses twice 5e-5, not twice 0.005 | false (follows from the above) | none |
| E5 records the delta builds but not the registered agreement | true | the volatility gap to delta 2.5 and whether it is within twice the tolerance are recorded |
| Sub-study (i) lacks a 180-month arm | false: the 180-month arm is the main grid's level-3 robokit row in world b, the same replications; the summary groups by months | the plan says so |

**Stage 1, seventh round (8 Oct 2026).** The third-family examiner: accept as is, with two recommendations. The
first examiner's review was cut off by its model pool's usage limit before its final message; its recorded reasoning
re-checked the round-6 fixes as holding and raised the points below, which were checked and ruled on like any finding.

| Finding | Ruling | Change |
|---|---|---|
| The interval check covers one interval, but "delivered" needs three at once | true | the run also measures the joint coverage of three simultaneous intervals on series correlated 0.9 |
| The 54 deflated-Sharpe trials are in the plan but not in results.json | true | the inventory is written beside the deflated Sharpe ratios |
| (Cut-off review) The QIS rule's `all(...)` runs over the truths present, so a truth with no samples would pass unseen | true (not reachable today: a failed sample stops the run) | the rule and the full-sample check run over the registered truths by name |
| (Cut-off review) `static_mix` is called risk-matched but holds a fixed stock share | true (wording): it is matched by construction, not calibrated | the plan says so; its ex-ante gap is reported |
| (Cut-off review) E6 starts at the first E1 target, later than the first common price | true (wording) | the plan says the account starts once a target exists |

**Stage 1, eighth round (8 Oct 2026).** Both Cursor model pools had reached their monthly limits; the review came from
Cursor's automatic routing, which reported itself as the same family as the round-5 to round-7 second examiner. Accept
after required changes.

| Finding | Ruling | Change |
|---|---|---|
| The variance of the trial Sharpe ratios, registered for the deflated Sharpe ratio, was not written | true | written beside each deflated Sharpe ratio |
| The round-5 Proposition 1 test switched resampling off, so it did not test the shipped pipeline | true (the round-5 fix was incomplete) | a resampled case added at fixed lambda / delta and calibrated at delta 1 and 4 |
| The calibration label said "resampled" for single-solve builds | true | the label says which, in both engines; tested |
| D9 named one of the screen's two conditions | true | both stated |
| The US readings were not labelled exploratory in the results | true | labelled |

**Stage 1, ninth round (8 Oct 2026).** The same reviewer as round 8 (Cursor's automatic routing). Accept after
required changes.

| Finding | Ruling | Change |
|---|---|---|
| The "exploratory" label sat on the US market, not on each comparison the paper will quote | true (the round-8 fix was incomplete) | every comparison carries its family |
| If T1 and T2 both held, the QIS rule moved the switch down although T2 says QIS is worse at 0.25 | true | registered rule changed before the run: down only if T1 holds in both truths and T2 in neither, up only the other way round, otherwise no change |
| The projection-path lock, and the E3 locks, never reach the engines | partly true: applying them after the run was planned but not written down or enforced | the plan states the post-run commit; tests/test_v3_locked_defaults.py fails whenever a shipped constant differs from a locked default |
| The random calibration suite let a refused request pass and trusted the "within tolerance" label | true (no request is refused today) | a refusal fails the test; within tolerance is checked from the rebuilt mix at its lambda |
| E6 reported the first price month, not the first month an account runs | true (metadata) | both reported |
| The power sentence: 0.3 is detected about 80% of the time, not half | true | corrected: about 0.22 (half) and 0.31 (80%) in Canada, 0.31 and 0.45 in the US |
| The register says the engines take the same calibration steps; at a jump they may differ | partly true: the parity test allows it (two steps) and checks each bracket | the register says so |

**Stage 1, tenth round (8 Oct 2026).** The same reviewer as rounds 8 and 9. Accept after required changes.

| Finding | Ruling | Change |
|---|---|---|
| E6 built its targets from the successful builds only, so a failed December would hold a mix past 12 months | true (the round-4 rule had not reached E6) | E6 refuses an incomplete schedule and records it under path_errors; tested |
| E2's leading skips listed any early failure, not only the registered short-history refusals | true | each failure records its kind; leading skips keep only short-history refusals |
| Nothing tested that the E3 locks reach the evaluation builds | true | each build records its covariance method and calibration label; a test checks both switches end to end |
| D16 claimed an E5 test, D23 a 2% arm that is the default, D29 a window test for the yardstick | true | register corrected to the tests that exist |

**Stage 1, eleventh round (8 Oct 2026).** The same reviewer as rounds 8-10. Accept after required changes.

| Finding | Ruling | Change |
|---|---|---|
| Sub-study (i)'s shorter histories were not the first months of the 180-month ones in world b (the Student t scale draws start at different points of the stream), so window lengths were not paired | true | one 192-month path per replication, shorter studies take its first months; the 180-month histories, and so the main grid, are unchanged; tested |
| E2's schedule skipped any failure before the first build, not only short-history refusals | true (the round-10 fix reached the listing, not the schedule) | only short-history refusals are skipped; any other failure stops the path; the test that encoded the old behaviour corrected |
| D5 listed 180 months as a sensitivity arm | true | worded against the 180 default |
| Levels 1 and 5 carried the registered reading's labels | true | labelled descriptive |

## Sources checked for this register

Each was opened and the quoted text checked; DOIs resolved through doi.org (8 Oct 2026).

* Beck, A., & Teboulle, M. (2009). A fast iterative shrinkage-thresholding algorithm for linear inverse problems. SIAM Journal on Imaging Sciences, 2(1), 183-202. https://doi.org/10.1137/080716542
* Black, F., & Litterman, R. (1992). Global portfolio optimization. Financial Analysts Journal, 48(5), 28-43. https://doi.org/10.2469/faj.v48.n5.28
* Canadian Securities Administrators. National Instrument 81-102 Investment Funds, Appendix F, Investment Risk Classification Methodology (in force 1 September 2017).
* Canadian Securities Administrators. Companion Policy 31-103CP, s.13.2; CSA Staff Notice 31-342 (2015); Joint CSA/CIRO Staff Notice 31-368.
* Doeswijk, R., Lam, T., & Swinkels, L. (2014). The global multi-asset market portfolio, 1959-2012. Financial Analysts Journal, 70(2), 26-41. https://doi.org/10.2469/faj.v70.n2.1
* Donohue, C., & Yip, K. (2003). Optimal portfolio rebalancing with transaction costs. Journal of Portfolio Management, 29(4), 49-63. https://doi.org/10.3905/jpm.2003.319894
* Dowell, M., & Jarratt, P. (1971). A modified regula falsi method for computing the root of an equation. BIT, 11(2), 168-174. https://doi.org/10.1007/BF01934364
* FP Canada and IQPF (2026). Projection Assumption Guidelines.
* He, G., & Litterman, R. (1999). The intuition behind Black-Litterman model portfolios. Goldman Sachs Investment Management Research.
* Idzorek, T. (2007). A step-by-step guide to the Black-Litterman model. In Forecasting Expected Returns in the Financial Markets. Elsevier.
* Jagannathan, R., & Ma, T. (2003). Risk reduction in large portfolios: why imposing the wrong constraints helps. Journal of Finance, 58(4), 1651-1683.
* Jorion, P. (2003). Portfolio optimization with tracking-error constraints. Financial Analysts Journal, 59(5), 70-82. https://doi.org/10.2469/faj.v59.n5.2565
* Ledoit, O., & Wolf, M. (2004). Honey, I shrunk the sample covariance matrix. Journal of Portfolio Management, 30(4), 110-119. https://doi.org/10.3905/jpm.2004.110
* Ledoit, O., & Wolf, M. (2022). Quadratic shrinkage for large covariance matrices. Bernoulli, 28(3), 1519-1547. https://doi.org/10.3150/20-BEJ1315
* Michaud, R. O. (1989). The Markowitz optimization enigma: is 'optimized' optimal? Financial Analysts Journal, 45(1), 31-42. https://doi.org/10.2469/faj.v45.n1.31
* O'Donoghue, B., & Candes, E. (2015). Adaptive restart for accelerated gradient schemes. Foundations of Computational Mathematics, 15(3), 715-732. https://doi.org/10.1007/s10208-013-9150-3
* Politis, D. N., & Romano, J. P. (1994). The stationary bootstrap. Journal of the American Statistical Association, 89(428), 1303-1313. https://doi.org/10.1080/01621459.1994.10476870
* Scherer, B. (2002). Portfolio resampling: review and critique. Financial Analysts Journal, 58(6), 98-109. https://doi.org/10.2469/faj.v58.n6.2489
* Sharpe, W. F. (1974). Imputing expected security returns from portfolio composition. Journal of Financial and Quantitative Analysis, 9(3), 463-472. https://doi.org/10.2307/2329873
* T. Rowe Price (2018). Fixed income: what's the simplest way to forecast bond returns?
* Toth, B., et al. (2011). Anomalous price impact and the critical nature of liquidity in financial markets. Physical Review X, 1, 021006. https://doi.org/10.1103/PhysRevX.1.021006
* Vanguard (2010). Best practices for portfolio rebalancing; Vanguard (2024). The rebalancing edge.
* Vanguard Investments Canada (25 June 2024). Press release on Canadian home bias (newswire.ca).
* Walters, J. (2014). The Black-Litterman model in detail. SSRN. https://doi.org/10.2139/ssrn.1314585
* Gurobi Optimization. Minimum buy-in (Gurobi Finance documentation).
* Betterment. Our approach to initial allocations.

The statistics used in the evaluation (Ledoit and Wolf 2008; Newey and West 1987; Holm 1979; Diebold and Mariano 1995;
Bailey and Lopez de Prado 2012, 2014; Jorion 1986) are cited with the results in the paper.
