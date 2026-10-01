# Robo-Kit portfolio optimizer — method

*Workstream WS4 (Finance lead). Written 26 Sep 2026, revised the same day after the Session 2 materials. Replaces "Step 3 — Optimizer spec" in the project outline (short version: `archive/SUMMARY_FOR_OUTLINE.md`); the report's methods section can be lifted from sections 2–5.*

## 1. What the brief asks for

> "Design a portfolio optimization tool prototype to calculate the portfolio weights for the selected ETFs as a function of the client's risk attitude (low-mid-high risk aversion parameter)." — *AI Robo Advisor* brief

So the engine must take (a) a shortlist of ETFs chosen through the selection tool, (b) one of three risk-aversion settings, and return weights, fast enough to run inside the chat interface, and explainable to a grant panel that "does not have much knowledge on ETFs".

## 2. Design principles, and where they come from

The course sets the constraints before the literature does.

| Principle | Instructor's words | What it forces |
| --- | --- | --- |
| Do not extrapolate history | "Historical data is not necessarily a good guide for future scenarios." (Session 1, slide 39; repeated Session 2, slide 11) | Sample-mean returns are not an input. |
| Anchor expected returns to a model | "We also try to anchor the expected returns (mu) and variances to some factors and/or forecast models. Otherwise, dimensionality is too high. Scenarios are too random and extremely unstable." (slide 39) | Expected returns come from an equilibrium model (CAPM / reverse optimization). |
| Mean-variance is the reference framework | "The assumed norm of behavior is mean-variance portfolio construction." … "CAPM reaches the conclusion that the optimal portfolio should be the market portfolio in equilibrium." (slide 41) | The objective is mean-variance with a risk-aversion parameter; the prior portfolio is the mid-risk answer. |
| Simple beats complex | "Truth 3.2: Simpler valuation models do much better than complex ones." (slide 25) | No neural networks, no learned allocators. |
| Impose structure on small data | "It is always necessary to impose structure, perhaps arbitrary structure, on the problem you are trying to solve." (Arnott, Harvey & Markowitz 2019, assigned in Session 2) | Shrinkage and equilibrium anchoring are that structure. |
| One history, no learned allocators | "'features' are being fitted to a single history. That is why, deep-learning type methods are mainly not that fruitful to predict the future returns." (Session 2, slide 24) | Resample the one history instead of fitting a model to it. |

The assigned CFA chapter (Chen & Zhou) says the same for our data size: "Fourth, simple ML algorithms outperform more complicated ML algorithms." and "since there are not much data to train on, the simpler models, due to their parsimonious nature, are less likely to overfit and thereby perform better out of sample." We have 127 monthly observations on 20 ETFs; the full Canadian universe would be 100–200 ETFs on the same months.

## 3. The pipeline

```
adjusted daily prices  ->  monthly total returns on a common window; integrity report (data.py)
        |
        v
Sigma  = shrunk covariance          (Ledoit-Wolf linear shrinkage; nonlinear QIS when N/T > 0.25)
mu     = delta * Sigma * w_prior    (equilibrium excess returns implied by a prior portfolio, delta = 2.5)
        |
        v
lam    = multiplier(profile) * delta      low 0.6 | mid 1.0 | high 2.5   (or calibrated to target vol)
        |
        v
w*     = argmin (lam/2) w'Sigma w - mu'w   s.t. sum w = 1, 0 <= w <= cap, client rules
        |
        v
resampling: 500 stationary-bootstrap histories, re-estimate, re-solve, average; keep the 5-95% band
        |
        v
outputs: weights, expected return/vol, risk contributions, effective N, band, plain-language notes
```

### 3.1 Data (`optimizer/data.py`)

Yahoo adjusted closes (dividends and splits included, i.e. total return), month-end sampling, bounded forward fill for holiday gaps, minimum 36 months of history, every survivor restricted to the same window so all covariances use the same months. `integrity_report` flags stale-price runs and |monthly return| > 30%; it never deletes ("Do not arbitrarily exclude outliers"). On the prototype it flags three 7–9-day stale runs in 2017 in low-volatility bond/cash ETFs, all plausible, all kept. The prototype universe is 20 TSX-listed ETFs, February 2016 to August 2026 (127 months); the 2016 start is dictated by XAW (listed 2015).

### 3.2 Covariance (`optimizer/estimators.py`)

The sample covariance is never used directly. With N assets and T months:

* **N/T ≤ 0.25** (prototype: 20/127 = 0.16): Ledoit–Wolf (2003) linear shrinkage toward the constant-correlation target — each ETF keeps its own variance, all pairwise correlations are pulled toward their average by a data-driven intensity (0.175 on the prototype).
* **N/T > 0.25** (the 100–200 ETF dataset): quadratic-inverse shrinkage, QIS (Ledoit & Wolf, *Bernoulli* 2022), which "keeps the eigenvectors of the sample covariance matrix and applies shrinkage to the inverse sample eigenvalues". Invertible even when N exceeds T. Ported from the authors' code and checked against it in the tests.

These are the estimators the 2026 horse-race literature still lands on for portfolios of this size (section 6). The Deutsche Bank handbook's summary applies: "regardless of the portfolio construction technique, portfolio performance almost always improves with better risk estimates."

### 3.3 Expected returns

Reverse optimization (the Black–Litterman prior, He & Litterman 1999):

    pi = delta * Sigma * w_prior

`w_prior` is the AUM-weighted portfolio of the universe — what Canadian ETF investors collectively hold — and `delta = 2.5` is the conventional market risk aversion. This is what Betterment documents for its own portfolios: "μ = λ Σ ωmarket". Each ETF's expected excess return is proportional to its covariance with the prior portfolio: an ETF earns a premium for the risk it *adds* to a diversified portfolio, not for its stand-alone volatility. On the prototype the prior has 9.3% volatility and an implied premium of 2.2% over the 2.25% risk-free rate.

Two alternatives are kept for comparison only: the sample mean and Bayes–Stein shrinkage (Jorion 1986). Client views can be added through the Black–Litterman posterior, but the interface expresses preferences as *constraints* (regions, ESG, no leverage, forced funds), which is more honest than turning a questionnaire answer into a return forecast. A policy prior (e.g. 60% equity / 35% fixed income / 3% cash / 2% commodity, split by AUM within each class) is available through `prior_from_class_weights` and tested in the grid.

### 3.4 Risk aversion: the low / mid / high mapping

Because expected returns are the equilibrium ones, the risk-aversion scale has a meaning:

| Profile | lam | What it means |
| --- | --- | --- |
| mid | 1.0 × delta | With no binding constraints the optimizer returns the prior portfolio itself: "hold the market". |
| high | 2.5 × delta | About 40% of the prior portfolio and 60% in the cash-like ETF: the classic two-fund split. |
| low | 0.6 × delta | Would want 1.7× the prior portfolio; with no borrowing and a 35% cap per fund, it tilts toward the higher-premium equity ETFs instead. |

Prototype result: expected volatility 11.7 / 9.3 / 3.7% for low / mid / high; the equity share of the high profile (~30%) matches the most conservative portfolio of the large Canadian robo-advisors (reviews put Wealthsimple's range at roughly 30/70 to 90/10 equity/fixed income). The absolute values lam = 1.5 / 2.5 / 6.25 sit inside the range the empirical literature reports for relative risk aversion (above 2, below 10). `calibrate_to_target_vol` replaces the multipliers with ones that hit stated volatilities (12 / 9 / 4%), which is how Betterment defines its bond-heavy levels ("expected returns are maximized for target volatilities assigned to each risk level").

Why the cautious client ends up in cash rather than bonds: under the equilibrium model a bond ETF's premium is delta times its covariance with an equity-heavy prior, about 0.4% a year, while its volatility is about 6%; the cash-like ETF has almost no premium and almost no volatility. At a 2.25% policy rate the trade-off favours cash. `cash_max` lets the team cap cash (robo-advisors usually do) and the grid tests a 35% cap; in the 2018–2026 sample the capped version did worse for the cautious client (bonds fell with equities in 2022), so the uncapped default stands, with the cap exposed as a product choice.

### 3.5 Optimization (`optimizer/solver.py`)

    minimize (lam/2) w'Sigma w - mu'w   subject to   sum w = 1,  0 <= w_i <= cap_i

Long-only, fully invested, 35% cap per ETF (cash ETF capped by `cash_max`, default 100%), plus client rules: forced minimum weights, exclusions, optional group limits (e.g. "at most 70% equity"), optional minimum position size. Solved by accelerated projected gradient in a diagonally preconditioned space with an exact projection onto the capped simplex — sixty lines of NumPy that port to JavaScript, 30 ms per solve, verified against SciPy's SLSQP to 1e-7 in the tests. Group limits fall back to SLSQP.

### 3.6 Resampling (`RoboKitOptimizer.optimize(resample=True)`)

The history is resampled 500 times with the stationary block bootstrap (Politis & Romano 1994; mean block six months, so volatility clustering survives), Sigma and mu are re-estimated on each draw, the problem re-solved, and the reported weights are the average with a 5–95% band per weight. This is Michaud's resampled efficiency and what Betterment does: "Averaging the allocation weights across the thousands of return samples gives a single set of allocation weights optimized to perform in the face of a wide range of market scenarios." The band is shown to the client as "how sure the model is". An optional Tu–Zhou blend with equal weights (`naive_blend`) exists; the grid shows it lowers turnover without improving risk-adjusted return, so it is off by default.

### 3.7 What the interface receives

For every client: weights; expected return and volatility; the share of portfolio risk each ETF contributes; the effective number of holdings; the resampling band; and sentences generated from the numbers. `output/robokit_spec.json` carries Sigma, mu, delta, the multipliers, the solver description and six test vectors so the JavaScript port can be checked against Python.

## 4. Why not the alternatives

| Alternative | Why it was rejected for Robo-Kit | Evidence |
| --- | --- | --- |
| Sample-mean mean-variance ("plug-in") | Puts the mid-risk client in three funds at their caps (gold, S&P 500, banks) and moves 21–40% of the portfolio every year. The Deutsche Bank handbook's description of the same algorithm at factor level: "tends to be quite volatile and concentrated". | `output/mu_method_comparison_mid.png`; section 5 |
| Hierarchical risk parity and successors | No risk-aversion parameter — one portfolio, the brief asks for three; the 2024 Schur-complement paper shows HRP is one end of a family whose other end is minimum variance. | arXiv 2411.05807 |
| Decision-focused / end-to-end learning; neural nonlinear shrinkage (2025–26) | Trained on daily S&P 500 panels; a May 2026 paper documents "inflated return signals and unstable portfolio reallocations"; fails the protocol's bar ("it had better win by an economically significant amount before the switch to a more complex model is justified") and the "cannot be a black box" test. | arXiv 2601.15597, 2507.01918, 2605.01176 |
| Distributionally robust (Wasserstein) optimization | Adds a radius that must be tuned on the same short history; gains reported on tail measures, not the mean-variance objective the brief specifies. | RESEARCH_NOTES.md |
| CVaR / drawdown objectives | Need many more tail observations than 127 months supply. | — |
| 1/N | Kept as a benchmark and as the optional blend. It ignores the client's risk aversion and the asset mix. | Tu & Zhou 2011; Feng et al. 2026 |

## 5. The walk-forward test, run under the Session 2 protocol

### 5.1 Design

At each annual re-estimation date the optimizer sees only the trailing window of months, sets weights for each profile, and holds them (rebalanced monthly to target) for a year. Every method is **risk-matched** — its lam is calibrated so its ex-ante volatility is 12 / 9 / 4% per profile — because a method whose expected returns are on a bigger scale would otherwise look better simply by taking more risk. **Transaction costs** of 10 bps one-way are charged on every unit of turnover, including monthly drift rebalancing (Canadian equity ETFs trade at 3–17 bps spreads, median 9, per National Bank Financial data). Results are reported per **sub-period** and with **paired t-statistics**. The grid of seven configurations was written down before it was run (`RESEARCH_LOG.md`).

### 5.2 Results

Equilibrium (Robo-Kit) versus the plug-in optimizer at matched risk, after costs:

| Configuration | Out-of-sample | Profile | Robo-Kit Sharpe / max DD / turnover | Plug-in Sharpe / max DD / turnover | Return gap, t-stat |
| --- | --- | --- | --- | --- | --- |
| base_2016_w60 | 2021-02 to 2026-08 (67 m) | mid | 1.09 / −12.9% / 10% | 1.39 / −11.2% / 21% | −3.2% a year, t = −1.7 |
| long_2014_w48 | 2018-02 to 2026-08 (103 m) | mid | 0.74 / −17.8% / 21% | 0.65 / −22.0% / 40% | −0.1%, t = 0.0 |
| long_2014_w48 | same | high | 0.71 / −10.0% / 13% | 0.54 / −12.2% / 28% | +0.3%, t = +0.4 |
| long_2014_w60 | 2019-02 to 2026-08 (91 m) | mid | 0.87 / −17.6% / 17% | 1.10 / −16.5% / 23% | −2.1%, t = −1.3 |
| policy prior (48) | 2018-02 to 2026-08 | mid | 0.67 / −17.3% / 24% | 0.65 / −22.0% / 40% | −0.8%, t = −0.5 |
| 1/N blend 50% (48) | same | mid | 0.70 / −16.0% / 14% | 0.68 / −17.4% / 21% | −0.1%, t = −0.1 |
| cash cap 35% (48) | same | high | 0.63 / −10.0% / 13% | 0.49 / −12.2% / 30% | +0.3%, t = +0.3 |
| costs 25 bps (48) | same | mid | 0.74 / −17.8% / 21% | 0.64 / −22.0% / 40% | −0.0%, t = 0.0 |

Full tables: `output/robustness_grid.csv`, `output/robustness_subperiods.csv`, `output/robustness_paired.csv`.

Read honestly:

1. **No configuration separates the two methods statistically.** Across 21 profile-configuration pairs the annualized return gap runs from −3.2% to +0.5% and every t-statistic lies between −1.7 and +0.5. The plug-in's advantage is a 2021–2026 phenomenon (S&P 500, gold and banks kept winning); over 2018–2026, which includes the 2020 crash and the 2022 rate shock, the two are tied on return and the equilibrium method has the smaller drawdowns (−17.8% vs −22.0% at mid) and half the turnover (21% vs 40% a year).
2. **The ranking flips with the window.** A 48-month window over the same 2014–2026 data favours the equilibrium method; a 60-month window favours the plug-in. This is the point the instructor makes with "The worst ten-year period for any back-test is the next ten years": what a back-test can establish here is stability and cost, not which method will earn more.
3. **Costs do not decide it.** At annual re-estimation even 40% turnover costs 4 bps a year at 10 bps; at 25 bps the drag is 10 bps. The argument for low turnover is behavioural and explanatory, not a cost argument.
4. **Risk models under-estimate risk in a crash.** The cautious (4% target) portfolio realized 11.7% volatility in 2020 under the equilibrium method, 14.2% under the plug-in and 17.9% for the static prior; over 2018–2026 it realized 5.4% against a 4% target. The Deutsche Bank handbook reports the same: "risk models on average tend to under-estimate risk in optimized portfolios". The interface should say "target", never "guaranteed".
5. **The prior matters and carries a mild look-ahead.** Switching from the AUM prior to a 60/35/3/2 policy prior moves the mid Sharpe from 0.74 to 0.67. The AUM prior is a 2026 snapshot, so funds that performed well in 2016–2026 are over-weighted in it at every past date; the static "prior" row's Sharpe of 0.83 is inflated by this and so, to a lesser degree, is the equilibrium method's. The policy-prior configuration is the clean comparison, and it still shows the equilibrium method tied on return with lower drawdowns and lower turnover.

### 5.3 Protocol compliance (Arnott, Harvey & Markowitz 2019, seven categories; Session 2 slide 22)

| Protocol item | Where it is met |
| --- | --- |
| Ex-ante economic foundation | CAPM / equilibrium anchoring fixed before any test (RESEARCH_LOG §1) |
| Keep track of what is tried | RESEARCH_LOG §§1–5, including the one post-hoc change and what was not tried |
| Define the test sample ex ante | 2016 start dictated by data; the 2014 variant pre-registered |
| Ensure data quality; document transformations; no arbitrary outlier exclusion | `integrity_report`; total-return prices; no winsorization |
| Out of sample is not really out of sample; iterated OOS is overfitting | One iteration disclosed (risk matching); no parameter was tuned on results |
| Trading costs | 10 and 25 bps configurations |
| Structural change | Sub-period tables; realized-vs-target volatility |
| Simplicity and regularization; interpretability | Shrinkage + equilibrium; risk contributions, bands and notes as outputs |

## 6. Evidence

Sources opened, with verbatim quotes; search-snippet items are marked in `RESEARCH_NOTES.md` and not relied on.

| # | Claim used above | Source | Verbatim quote |
| --- | --- | --- | --- |
| 1 | Shrunk-covariance GMV/MV still wins 2026 horse races | Yadav, Sharma & Mehra, arXiv 2601.20643 (Jan 2026) | "in most scenarios, the GMV model combined with the Ledoit Wolf two parameter shrinkage covariance estimator (COV2) represents the optimal selection for a broad spectrum of investors" |
| 2 | QIS definition | Ledoit & Wolf, *Bernoulli* 28(3), 2022 | "keeps the eigenvectors of the sample covariance matrix and applies shrinkage to the inverse sample eigenvalues" |
| 3 | Betterment anchors returns by reverse optimization and averages over simulated histories | betterment.com/resources/portfolio-construction-methodology | "μ = λ Σ ωmarket"; "Averaging the allocation weights across the thousands of return samples gives a single set of allocation weights optimized to perform in the face of a wide range of market scenarios." |
| 4 | Betterment defines conservative levels by target volatility | same | "expected returns are maximized for target volatilities assigned to each risk level" |
| 5 | Decision-focused learning is unstable | Wang & Hasuike, arXiv 2605.01176 (May 2026) | "SPO(Smart, Predict then Optimize surrogate)-based DFL may produce inflated return signals and unstable portfolio reallocations." |
| 6 | Neural shrinkage needs large daily equity panels | Yang, Zhao & Chai, arXiv 2601.15597 (Jan 2026) | "apply a lightweight transformer-based neural network to learn a nonlinear eigenvalue shrinkage function"; "stock daily returns from Standard & Poor's 500 Index" |
| 7 | HRP is one end of a continuum ending in minimum variance | Cotton, arXiv 2411.05807 (2024) | "the inclusion of information using the Schur complement (i.e. taking γ>0) steadily reduces portfolio variance" |
| 8 | 1/N is hard to beat; blend it | Feng, Huang, Wang & Zhang, arXiv 2607.11054 (Jul 2026); Tu & Zhou, JFE 2011 | "equal weighting is minimum-variance optimal when the forecast-error covariance matrix has a uniform eigenstructure"; "we propose an optimal combination of the naive 1/N rule with one of the four sophisticated strategies" |
| 9 | Risk-free rate | Bank of Canada, 2 Sep 2026 | "The Bank of Canada today held its target for the overnight rate at 2.25%, with the Bank Rate at 2.5% and the deposit rate at 2.20%." |
| 10 | Trading costs | National Bank Financial via Investment Executive, 15 Oct 2024 | Canadian equities ETFs "3 to 17" bps, median "9" |
| 11 | Protocol | Arnott, Harvey & Markowitz, JFDS 2019 (course site) | "Any research on historical data needs to take transactions costs and, more generally, implementation shortfall into account in both the in-sample and out-of-sample analysis"; "Keeping track of the number of strategies tried is crucial" |
| 12 | Risk under-estimation; MVO concentration; better risk estimates | Deutsche Bank, *Seven Sins* (course site) | "risk models on average tend to under-estimate risk in optimized portfolios"; "tends to be quite volatile and concentrated"; "portfolio performance almost always improves with better risk estimates" |
| 13 | Course positions | Session 1 slides 25, 39, 41; Session 2 slides 11, 22–24; CFA handbook ch. 1 | quoted in section 2 |

## 7. Open items

1. **Prior portfolio.** AUM is a single 2026 snapshot (mild look-ahead in the back-test; three of twenty values filled with the asset-class median). The Data lead's dataset should carry AUM as a field; if AUM history can be found, the back-test should use point-in-time AUM.
2. **Risk-free rate** is a constant 2.25%; a monthly Bank of Canada series would tighten the back-test.
3. **Suitability.** The mapping from questionnaire answers to low / mid / high is the conversation script's job (WS5); Canadian dealers do this under CIRO know-your-client rules, and the report should say the prototype is educational, not advice.
4. **Interface wording.** Expected volatility is a target that history shows can be exceeded by a factor of three in a crash; the education layer should show the 2020 sub-period alongside the target.

---

## 8. v2 (28 Sep 2026): what changed and why

Sections 1-7 describe the v1 optimizer on the 20-ETF prototype and still hold for its core. v2 keeps the core and changes what surrounds it. Full specification: `docs/PRODUCT_SPEC.md` sections 6-11.

| Topic | v1 | v2 | Why |
| --- | --- | --- | --- |
| Universe | 20 hand-picked Canadian ETFs | 7,957 listings (Canada in CAD, US), 2,610 eligible, every exclusion explained | Scope: all CAD-buyable Canadian ETFs and all US ETFs |
| Fund selection | Fixed list | Reference shelf: one broad, low-cost fund per asset class chosen by a written rule and a published score; user swaps and additions | Path A: the person builds the shortlist (docs/research/regulation.md) |
| Prior | AUM weights of the shortlist | Written policy anchor per asset class (60/35/3/2, 30% home bias for Canada) | AUM weights made the prior depend on which funds happen to be large |
| Young funds | Common window only | Correlation-checked proxy splices for core funds, matched to the fund's currency hedging (a CAD-hedged S&P 500 fund is extended with SPY's own US-dollar return, not SPY converted to CAD); regression back-fill for satellites; all disclosed | Five-year windows let one unusual period decide everything; correlation alone cannot tell hedged from unhedged (0.87) |
| Currency | CAD only | Every fund converted into the portfolio currency by its trading currency from the fund list (USD units on the TSX are USD); stress stand-ins too | Suffixes misread USD units and cross-border picks |
| Risk mapping | Three fixed volatility targets | Level L targets L x 20% of the measured stock-market volatility; lambda by bisection | Every level stays reachable; people understand "60% of the market's swings" |
| Guardrails | 35% cap per fund, cash cap | 50% per fund; sleeve caps (REITs, gold 10%, EM 15%); cash cap by level; satellite caps by level | Equilibrium returns reward high-beta assets; caps stop corner solutions |
| Solver | FISTA (box + budget); SLSQP for groups | FISTA with an exact one-group projection (satellite cap), verified against SLSQP to machine precision | Keeps the browser port fast and exact |
| Views | Available, unused | Idzorek-style confidence, tilt bounded to 1% tracking error and 5 points per fund, off by default | Research: views are machinery, not a strategy |
| Self-check (v2.1) | Not in v1 | Suggested level = lower of capacity and tolerance, as a suggestion, not a ceiling; cushions (most of savings, uneven income, partial emergency fund) at most 2 steps, 1 on a long horizon; a riskier level is explored through a sheet with its bad year and crisis replays in the person's dollars; only savings/debt gates cap the build | Personas: the old cap bound far too often (a 20+ year saver landed on level 2) and was hidden in a tooltip; Path A has the person choose |
| Ranges and bad year (v2.1) | Resampled 15-year window | Resampled over the longest history every fund has (2003 onward for the reference funds, spliced and back-filled as disclosed), so 2008 is inside the range; weights still use 15 years | A level-5 bad year of -10% next to a -37% 2008 replay was not credible |
| Level chooser numbers (v2.1, round 3) | Not in v1 | Every row of the self-check scenarios, the level chooser and the explore sheet is built from the person's own request (funds, amount, monthly flow, horizon, same 200 histories and seed as the mix), so the row at the current level equals the built mix; year-end values include the monthly flow; withdrawal plans show how often the money lasted | Round 2: the sheet quoted a bad year $3,735 away from the mix built a moment later, and a retiree never saw that the suggested level 1 lasted 25 years in only 27% of paths |
| Own weights and one-fund benchmark (v2.1) | Not in v1 | The same report for the person's own weights (with the level they behave like) and for the closest asset-allocation ETF (XEQT, VGRO, AOR...) on the same window | Do-it-yourself investors compare against one-ticket funds |
| Displayed returns | Equilibrium (low absolute level) | FP Canada 2026 planning assumptions after fees; equilibrium kept for relative returns inside the optimizer | A published, neutral planning anchor for what people read |
| Back-test | 2016/2018 samples, one market | Pre-registered walk-forward on both markets, 2009-2026 (CA) and 2018-2026 (US), five strategies, three levels | See PRODUCT_SPEC.md section 10 and RESEARCH_LOG.md section 6 |

v2 back-test in one paragraph (hypothetical, after costs): in Canada the risk levels delivered almost exactly their target volatility, and Robo-Kit, a static 60/40 of the same funds and the textbook optimizer are statistically tied. In the shorter US window (2018-2026) the textbook optimizer beat Robo-Kit by 1.5% a year at level 3 (t = -2.1), and realised volatility ran above target through 2020 and 2022. The trend tilt failed its pre-registered bar and stays off. v1's open items 1 and 2 are closed (written prior; Bank of Canada and US bill rates by month); item 3 is answered by `robokit/profile.py`; item 4 is in the page (stress tests next to every mix).
