# Research notes — portfolio optimization, September 2026

Working notes behind `METHOD.md`. Rule used throughout: a claim carries a URL **and** a verbatim quote only if the page was actually opened; items known only from a search-engine snippet are marked *(snippet, not opened)* and were not relied on for design decisions.

## A. Course materials (local files)

| Position | File | Verbatim | Implication |
| --- | --- | --- | --- |
| History is not a forecast | Session 1 slides, slide 39 | "Historical data is not necessarily a good guide for future scenarios." | Sample means out. |
| Normality is an assumption | slide 39 | "And, multivariate normal distribution is not necessarily a good representation of the joint distributions." | Resample the actual history rather than draw from a fitted normal. |
| Anchor mu | slide 39 | "We also try to anchor the expected returns (mu) and variances to some factors and/or forecast models." | Equilibrium / CAPM anchoring. |
| Instability of unanchored simulation | slide 39 | "Otherwise, dimensionality is too high. Scenarios are too random and extremely unstable." | Shrinkage + resampling. |
| Mean-variance is the norm | slide 41 | "The assumed norm of behavior is mean-variance portfolio construction." | Objective function. |
| Market portfolio | slide 41 | "CAPM reaches the conclusion that the optimal portfolio should be the market portfolio in equilibrium." | Prior portfolio = mid profile. |
| Beta is the priced risk | slide 43 | "Differences in asset returns and risk must be driven by beta to systematic risk." | pi = delta Sigma w_prior rewards covariance with the prior, nothing else. |
| Simplicity | slide 25 | "Truth 3.2: Simpler valuation models do much better than complex ones." | No learned allocators. |
| Back-tests | slide 11 | "the relation between the performance metrics and future reliability may be highly uncertain." | Report the back-test with its t-statistics and turnover, no victory lap. |
| Small data | CFA handbook ch. 1 (Chen & Zhou) | "Fourth, simple ML algorithms outperform more complicated ML algorithms." | Same. |
| Why | same | "since there are not much data to train on, the simpler models, due to their parsimonious nature, are less likely to overfit and thereby perform better out of sample." | Same. |
| Ensembling | same | "ensembling is one of the closest things to a free lunch in ML, much like diversifica- tion for investing." | Resampled weights are an ensemble. |
| Brief | AI Robo Adviser.docx | "Design a portfolio optimization tool prototype to calculate the portfolio weights for the selected ETFs as a function of the client's risk attitude (low-mid-high risk aversion parameter)." | Interface contract. |

### Session 2 module (downloaded 26 Sep 2026 into `../Session 2/`)

| Position | File | Verbatim | Implication |
| --- | --- | --- | --- |
| Small data, impose structure | *A Backtesting Protocol in the Era of Machine Learning* (Arnott, Harvey & Markowitz, JFDS Winter 2019), p. 1 | "It is always necessary to impose structure, perhaps arbitrary structure, on the problem you are trying to solve." | Equilibrium anchoring and shrinkage are exactly that structure. |
| Ex-ante foundation | same, p. 5 | "The hypothesis provides a discipline that reduces the chance of overfitting." | Design fixed before the back-test; recorded in RESEARCH_LOG.md. |
| Track what is tried | same, p. 6 | "Keeping track of the number of strategies tried is crucial, as is measuring their correlations" | RESEARCH_LOG.md lists every configuration, winners and losers. |
| Sample defined ex ante | same, p. 6 | "The sample should never change after the research begins." | 2016 start dictated by XAW; the 2014 variant pre-registered as a robustness check, not a search. |
| Costs | same, p. 8 | "Any research on historical data needs to take transactions costs and, more generally, implementation shortfall into account in both the in-sample and out-of-sample analysis" | 10 bps one-way costs on all turnover, including monthly drift rebalancing. |
| Iterated OOS | same, p. 8 | "The researcher modifies the initial model so it then works both in sample and out of sample. This is no longer an out-of-sample test. It is overfitting." | The one post-hoc change made (risk matching) is disclosed in RESEARCH_LOG.md. |
| Structural change | same, p. 8 | "In finance, we are not dealing with physical constants; we are dealing with human beings and with changing preferences and norms." | Sub-period tables; stock-bond correlation regime noted. |
| Simplicity | same, p. 9 | "If, however, a more elaborate machine learning model beats the linear regression model, it had better win by an economically significant amount before the switch to a more complex model is justified." | Bar for adopting any 2025-26 learned allocator. |
| Interpretability | same, p. 9 | "It cannot be a black box." | Risk contributions, bands and plain-language notes are outputs, not extras. |
| Instructor's summary of the protocol | *Lecture 2_3 Slides 2026*, slide 22 | "Establish an Ex Ante Economic Foundation / Beware an Ex Post Economic Foundation / Keep Track of What Is Tried / Ensure Data Quality / Document Choices in Data Transformations / Do Not Arbitrarily Exclude Outliers / Recognize That Iterated Out of Sample Is Not Out of Sample / Seek Interpretable Machine Learning" | The instructor's own checklist; METHOD.md section 5 maps to it item by item. |
| Back-tests | slide 23 | "The worst ten-year period for any back-test is the next ten years." | Report the back-test as evidence of stability, never as a return forecast. |
| Single history | slide 24 | "the problem is bigger for financial returns data because 'features' are being fitted to a single history. That is why, deep-learning type methods are mainly not that fruitful to predict the future returns." | Same reason we resample the history and refuse learned allocators. |
| Simulation anchoring (repeated from Session 1) | slide 11 | "We also try to anchor the expected returns (mu) and variances to some factors and/or forecast models." | Equilibrium mu. |
| Instructor's own code | *Portfolio Simulation End Values.ipynb* | Cholesky-correlated Monte Carlo of an equal-weighted 4-asset portfolio from historical mean and covariance; 1-day VaR | The notebook is the "unanchored" baseline the slides warn about; our resampling is its non-parametric cousin and our mu is anchored. |
| Data mining | *Seven Sins of Quantitative Investing* (Deutsche Bank, Sep 2014), p. 4 | "if we test enough factors and 'torture' our data hard enough, we can almost always find something that works spectacularly in-sample" | Research log. |
| Storytelling | same, p. 14 | "the fact that we can explain something has nothing to do with its out-of-sample performance" | Explanations in the interface describe the mechanics of the weights, not a market story. |
| Data snooping check | same, p. 18 | "we are strong believers of backtesting on a set of pre-defined rules rather than factors" | The whole pipeline (data hygiene -> shrinkage -> equilibrium -> QP) is one rule applied identically at every rebalance date. |
| Turnover | same, p. 21 | "Even if we have a tight turnover constraint, we may still want to frequently adjust our positions – albeit modestly each time." | Monthly rebalancing to target inside the year; annual re-estimation. |
| Outliers | same, p. 26 | "Backtesting results may be sensitive to the cutoff value we choose." | No winsorization anywhere; `integrity_report` flags, never deletes. |
| Diversification | same, p. 38 | "Once we adjust for those hard-to-borrow names, the diversification benefit clearly outweighs higher conviction." | Long-only, capped, resampled weights favour breadth. |
| Risk estimates | same, p. 41 | "regardless of the portfolio construction technique, portfolio performance almost always improves with better risk estimates" | Covariance shrinkage is where the engineering effort goes. |
| MVO instability | same, p. 42 | "Grinold & Kahn's approach, due to the nature of mean-variance optimization, tends to be quite volatile and concentrated" | Matches our sample-mean MVO exhibit (three funds at their caps). |

### Additional sources opened for the second pass (26 Sep 2026)

| Item | URL | Verbatim | Use |
| --- | --- | --- | --- |
| Tu & Zhou, JFE 99 (2011) 204-215 | https://econpapers.repec.org/article/eeejfinec/v_3a99_3ay_3a2011_3ai_3a1_3ap_3a204-215.htm | "the estimated Markowitz portfolio rule and most of its extensions not only underperform the naive 1/N rule (that invests equally across N assets) in simulations, but also lose money on a risk-adjusted basis in many real data sets"; "we propose an optimal combination of the naive 1/N rule with one of the four sophisticated strategies" | `naive_blend` option; tested at 0.5 in the robustness grid. |
| Canadian ETF bid-ask spreads (National Bank Financial data, Investment Executive, 15 Oct 2024) | https://www.investmentexecutive.com/report-cards/etf-guide/key-insights-about-bid-ask-spread-costs/ | Canadian equities ETFs: "3 to 17" bps, median "9" | 10 bps one-way cost assumption (half-spread plus slippage). |

### Search snippets only, second pass (not opened)

* Friend & Blume (1975): relative risk aversion "well in excess of one and probably in excess of two"; and a snippet that economists agree RRA is below 10. Supports lam in the 1.5-6.25 range for our three profiles, not a measured value.
* Wealthsimple Classic portfolios: risk score 1-10; most conservative about 30% equity / 70% fixed income, most aggressive about 90/10 (third-party reviews). Used only as a sanity check on the equity share of our profiles.
* Stock-bond correlation turned positive in 2022 (FAJ 2024 article "Empirical Evidence on the Stock-Bond Correlation", page 403 on fetch; AQR and Alpha Architect summaries). Motivates the sub-period tables.
* Politis & Romano (1994), stationary bootstrap: blocks of geometric length; implemented as `resample_method="stationary"`.
* Doeswijk, Lam & Swinkels, global multi-asset market portfolio (FAJ 2014; data to 2023 at the Erasmus repository): would be the theoretically right prior by asset class; weights not retrieved, so a stated 60/35/3/2 policy prior is used as the alternative in the grid.

## B. 2025–2026 literature (opened)

| Item | URL | Verbatim | Date | Use |
| --- | --- | --- | --- | --- |
| Shrinkage horse race across six datasets, MV vs GMV, 5 mean and 11 covariance estimators | https://arxiv.org/abs/2601.20643 | "in most scenarios, the GMV model combined with the Ledoit Wolf two parameter shrinkage covariance estimator (COV2) represents the optimal selection for a broad spectrum of investors" and "the MV model utilizing COV2 alongside the sample mean (SM) proves more suitable for return oriented investors" | 28 Jan 2026 | Supports LW shrinkage as the covariance default. |
| Neural nonlinear shrinkage for GMV | https://arxiv.org/abs/2601.15597 | "apply a lightweight transformer-based neural network to learn a nonlinear eigenvalue shrinkage function"; data "stock daily returns from Standard & Poor's 500 Index" | 22 Jan 2026 | Frontier method; data regime does not match ours. |
| Decision-focused covariance for GMV | https://arxiv.org/abs/2508.10776 | "prediction-focused estimation methods may fail to produce optimal allocations in practice, whereas DFL-based methods consistently deliver superior decision performance" | 14 Aug 2025 | Frontier; abstract gives no N/T or magnitudes. |
| Instability of SPO-based DFL | https://arxiv.org/abs/2605.01176 | "SPO(Smart, Predict then Optimize surrogate)-based DFL may produce inflated return signals and unstable portfolio reallocations." | 2 May 2026 (rev. 13 Jul 2026) | Reason to avoid DFL for a retail product. |
| Regret geometry of GMV covariance error under heavy tails | https://arxiv.org/abs/2606.27462 | "the decision-focused advantage is a sharper constant and a concentration discount rather than a faster rate" | 25 Jun 2026 | Theory; no estimator recommendation. |
| Schur complementary allocation (HRP ↔ min-var) | https://arxiv.org/html/2411.05807 | "the inclusion of information using the Schur complement (i.e. taking γ>0) steadily reduces portfolio variance"; "all the choices of γ are superior to naive optimization" | 29 Oct 2024 | HRP has no risk-aversion dial; noted, not used. |
| Hierarchical minimum variance (Schur, recursive) | https://arxiv.org/abs/2503.12328 | abstract only; "a transparent and mathematically rigorous connection between classical Markowitz mean-variance optimization, hierarchical clustering, and the Schur complement method" | 16 Mar 2025 | No empirical results in abstract. |
| When 1/N works | https://arxiv.org/abs/2607.11054 | "equal weighting is minimum-variance optimal when the forecast-error covariance matrix has a uniform eigenstructure"; "a two-stage adaptive strategy that dynamically blends naive and optimized weights" | 13 Jul 2026 | 1/N kept as benchmark; blending is a possible extension. |
| Why 1/N is not so naive | https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/why-naive-1n-diversification-is-not-so-naive-and-how-to-beat-it/4969319F5B1F3E350FB7FC8A73BA9F65 | page opened; abstract paraphrased by the fetch tool, no verbatim captured: 1/N is optimal in a one-factor model as N grows; it can be beaten by combining it with estimated rules when N is small | Yuan & Zhou, JFQA 2023 | Same. |
| QIS | https://projecteuclid.org/journals/bernoulli/volume-28/issue-3/Quadratic-shrinkage-for-large-covariance-matrices/10.3150/20-BEJ1315.full | "keeps the eigenvectors of the sample covariance matrix and applies shrinkage to the inverse sample eigenvalues"; "no cubic or higher-order nonlinearities beat quadratic with respect to Frobenius loss under large-dimensional asymptotics" | Aug 2022 | Implemented. |
| QIS reference code | https://raw.githubusercontent.com/pald22/covShrinkage/main/QIS.py | full source retrieved (BSD 2-clause, Ledoit & Wolf 2021) | 2021 | Ported; oracle in tests. Defect found: `np.linalg.eig` gives non-orthonormal null-space eigenvectors when p > n, so the original reconstruction is off in that case; ours uses `eigh`. |

## C. Practice (opened)

| Item | URL | Verbatim |
| --- | --- | --- |
| Betterment methodology | https://www.betterment.com/resources/portfolio-construction-methodology | "μ = λ Σ ωmarket"; "we find a set of allocation weights subject to constraints that provide the best risk-return trade-off, expressed as the portfolio's Sharpe ratio"; "expected returns are maximized for target volatilities assigned to each risk level"; "generate[s] several thousand random samples of 15 years of expected returns for the selected asset classes based on our latest CMAs, assuming a multivariate normal distribution"; "Averaging the allocation weights across the thousands of return samples gives a single set of allocation weights optimized to perform in the face of a wide range of market scenarios."; "101 individualized risk levels" |
| Betterment 2026 update | https://www.betterment.com/advisors/resources/2026-portfolio-updates-advisors | "updated capital market assumptions, the expected risk and return profiles of asset classes"; no method change disclosed |
| Bank of Canada | https://www.bankofcanada.ca/2026/09/fad-press-release-2026-09-02/ | "The Bank of Canada today held its target for the overnight rate at 2.25%, with the Bank Rate at 2.5% and the deposit rate at 2.20%." |

## D. Search snippets only (not opened; not relied on)

* End-to-end covariance cleaning with neural networks, arXiv 2507.01918 — snippet claims lower realized volatility than nonlinear shrinkage on 2000–2024 data.
* Wealthsimple help-centre pages (403 on fetch) — snippets say four risk profiles / three categories (Conservative, Balanced, Growth), passive, stock/bond split.
* Vanguard Asset Allocation Model whitepaper (PDF not parseable) — snippets describe utility-based optimization over VCMM distributions with a genetic algorithm.
* Kan & Zhou (2007) three-fund rule; Tu & Zhou (2011) combination with 1/N — classic references, seen via snippets.
* Idzorek's step-by-step Black–Litterman guide (PDF not parseable) — the delta = 2.5 convention is from He & Litterman (1999) as commonly cited; treat the exact value as a convention, not a measured quantity.

## E. Unresolved

* Whether nonlinear shrinkage materially changes weights at N = 100–200, T ≈ 127 on Canadian ETFs — will be known once the Data lead's universe exists (`cov_method="auto"` switches at N/T > 0.25).
* How much the AUM prior drifts over time and whether a time-varying prior changes the back-test.
* The instructor's own back-testing protocol (Session 2 file) may impose a different walk-forward design.
