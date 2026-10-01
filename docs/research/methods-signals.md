STATUS: COMPLETE

# Portfolio-construction methods and the evidence behind each candidate signal

*Research lane for Robo-Kit v2, 28 Sep 2026. Extends `docs/METHOD.md` and `docs/RESEARCH_NOTES.md` (which already cover covariance shrinkage, the equilibrium prior, resampling, 1/N, decision-focused learning and the backtest protocol); none of that is repeated here.*

**How to read this.** Every claim below carries the URL that was actually opened and a verbatim quote of 40 words or fewer. The "check" column in section 9 says how each quote was verified: **raw** means a script downloaded the page or PDF and confirmed the exact string is in the text; **fetch** means it came through the WebFetch summariser only (and is marked medium confidence). Items not opened are listed as gaps, not used.

**Evidence grades used for signals.**
- **Strong**: several peer-reviewed studies, including independent out-of-sample (OOS) replication, at the level Robo-Kit needs (asset classes or broad indices, monthly horizon).
- **Mixed**: published positive results, but with a credible failed replication, OOS failure, or evidence at a different level (stocks, daily, factors).
- **Weak**: in-sample only, a single study, a horizon mismatch, or failed replications.

---

## 0. Bottom line (plain language)

1. **Map risk to a volatility target, not to a label.** The leading robo-advisors turn a questionnaire into a small number of portfolios on one risk dial (Wealthfront: 20 allocations; Betterment: target volatility per level; Vanguard: a utility model with risk-aversion and loss-aversion inputs). Canadian regulators now say the risk profile should be **the lower of risk tolerance and risk capacity**. Robo-Kit should do the same and then call its existing `calibrate_to_target_vol`.
2. **Questionnaires are noisy.** They explain under 15% of how much risk people actually hold. So keep the dial coarse, show people what the dial means in dollars, and don't let one panicked answer during a crash cut their risk overnight.
3. **Black-Litterman views are machinery, not a strategy.** Build Idzorek's 0-100% confidence method and a tracking-error budget so any view can only nudge the portfolio. Leave views **off by default**.
4. **Almost nothing predicts monthly asset-class returns reliably.** A 2022 update of the main survey of market-timing variables found that 0 of 17 monthly predictors still worked both in-sample and OOS through 2020 (from the authors' conference slides; the published abstract is milder). Trend, carry and valuation have real long-run evidence, but it is contested or weak at the monthly timing level.
5. **News, geopolitics, policy uncertainty, VIX and LLM-scored headlines are for explanation and risk flags only, not for weights.** Where these signals predict anything, high fear tends to come before *higher* returns (EPU, news-implied volatility, variance risk premium). That is the opposite of what the "scary news, sell" story says. A chatbot that de-risks on headlines would work against the evidence.
6. **Keep mean-variance as the core.** Hierarchical risk parity, risk parity and CVaR optimisation are fine as benchmarks and reported metrics. CVaR as an *objective* is fragile to estimate, and risk parity needs leverage to reach equity-like returns.
7. **Goal projections must be ranges, labelled hypothetical.** Show percentile fans and a "chance you'll need to adjust" rather than a "success %". Use FP Canada's 2026 assumptions as the Canadian default, and follow FINRA 2214-style disclosures. Evidence shows the display itself changes how much risk people choose, so show both the 1-year loss view and the long-horizon view.

### Signal scorecard

| Signal | Level of evidence needed (asset class, monthly) | Grade | Recommendation |
| --- | --- | --- | --- |
| Time-series momentum / trend (12-month) | futures on indices, bonds, FX, commodities | **Mixed** | Opt-in bounded BL view only (TE-capped), after passing Robo-Kit's own pre-registered walk-forward; otherwise narrative ("above/below its 12-month trend") |
| Valuation (CAPE, yield spreads) for timing | broad equity index | **Weak** (monthly timing); **Strong** as a 10-year return anchor | Use only in long-horizon capital-market assumptions for projections; do not use for weights |
| Carry (yield minus cash, term, roll) | cross-asset | **Mixed** | Narrative / yield display; optional bounded view inside fixed income; disclose crash risk in recessions |
| Macro and technical regime indicators | equity premium | **Mixed–weak** | Risk flag / narrative only |
| Investor-sentiment indices (Baker-Wurgler, aligned) | equity premium | **Mixed** | Do not use for weights |
| Media tone / news sentiment (dictionary) | market, daily | **Weak** at monthly | Narrative only |
| LLM-scored news | stocks daily; one market-level monthly working paper | **Weak** | Narrative only; never an optimizer input |
| Geopolitical Risk index (Caldara-Iacoviello) | macro VAR; conditional return studies | **Weak** for returns | Disclosed risk flag and stress scenario only |
| Economic Policy Uncertainty (Baker-Bloom-Davis) | market, 3-month | **Weak–mixed**, sign is contrarian | Risk flag; never a de-risking trigger |
| VIX level / variance risk premium | market, quarterly | **Mixed** | Risk flag and "what volatility means" teaching; no volatility timing |
| Volatility-managed exposure | equity factors and market | **Mixed** (fails OOS in a 103-strategy test) | Do not use |
| News-implied volatility (NVIX) | market, historical | **Mixed** (contrarian sign) | Narrative only |
| Past performance of an ETF | — | covered by trend row; METHOD.md already rejects sample means | Show with the standard warning; never as expected return |

---

## 1. Mapping a risk score to portfolio risk

### 1.1 What leading robo-advisors actually do

| Firm | Mechanism | Verbatim |
| --- | --- | --- |
| Wealthfront | One composite score, weighted toward the more cautious of subjective and objective risk; score indexes one of 20 allocations | "Our overall Risk Score combines subjective and objective risk tolerance, with a heavier weighting to whichever component is more risk averse." / "The composite Risk Scores range from 0.5 (most risk averse) to 10.0 (most risk tolerant) in 0.5 increments." |
| Wealthfront | Inconsistent answers lower the score | "The less consistent the answers, the exponentially less risk-tolerant you are likely to be." |
| Wealthfront | Expected returns: Black-Litterman blending CAPM with long-run model expectations; 35% cap | "use the Black-Litterman model to blend expected returns from the Capital Asset Pricing Model"; "We selected 35% as the maximum allocation for most asset classes" |
| Betterment | Target volatility per risk level (already in RESEARCH_NOTES §C) | "expected returns are maximized for target volatilities assigned to each risk level" |
| Schwab Intelligent Portfolios | Willingness *and* capacity; CVaR across simulated histories | "based on your goal, time horizon and both willingness and capacity to take risk"; "we find portfolios that perform relatively well across all of the simulated histories, finding the right mix between return and downside risk (CVaR)" |
| Vanguard (Advice / VLCM) | Utility-based life-cycle model, separate risk-aversion and loss-aversion inputs, >1,000 glide paths | "Utility measures an investor's satisfaction with a glide path's risk and return."; "PGPs consist of over 1,000 glide paths created by the VLCM." |

Two things to take from this. First, **every firm reduces the answers to one dial**, and the dial's meaning is fixed by the optimiser: a volatility target (Betterment), a position on the frontier (Wealthfront) or a utility parameter (Vanguard). Second, **Wealthfront's "weight toward the more cautious component" and Schwab's "willingness and capacity" match what Canadian regulators now ask for** (1.2). Robo-Kit's 35% per-ETF cap is the same number Wealthfront uses per asset class.

Vanguard reports that "86% of participants whose accounts were auto-enrolled into Advice received more utility than if their account balances had been invested in a target-date fund". This is Vanguard evaluating its own product with its own utility model, so it is not independent evidence.

### 1.2 The Canadian rule (binding context for a Canadian launch)

The Joint CSA/CIRO Staff Notice 31-368 (10 Dec 2025) says a client's overall risk profile "should reflect the lower of the two", meaning tolerance and capacity. It also warns against a design where "a client with a low risk capacity and high risk tolerance is determined to have a high risk profile". Questionnaires are allowed but should "include separate questions for risk tolerance and risk capacity".

**Implication.** Robo-Kit's profile engine should compute two separate scores, take `min(tolerance, capacity)`, and log both plus any override reason. That rule is a deterministic script, not a model judgement.

### 1.3 How good are questionnaires? (the measurement problem)

- Klement (CFA Institute Research Foundation brief, 2015): questionnaires are "inadequate and unreliable, typically explaining less than 15% of the variation in risky assets between investors." In a cited study, adding the advisor raised explained variation from 13.1% to 31.6%, so the advisor mattered more than the questionnaire.
- Barsky, Juster, Kimball & Shapiro (NBER w5213, 1995; QJE 1997) measured relative risk aversion with hypothetical income gambles: "The mean risk tolerance is 0.25"; "The majority of respondents fall into the least risk-tolerant group". A risk tolerance of 0.25 corresponds to relative risk aversion γ ≈ 4.
- Goldstein, Johnson & Sharpe (JCR 2008): the "distribution builder" lets people pick outcome distributions directly. They "provide evidence of the technique's reliability and predictive validity" and "estimate parameters of risk aversion and loss aversion". This is the most defensible elicitation format for a chat UI: show outcome ranges in dollars, not abstract statements.
- Vanguard's advice flow (search snippet only, not opened for a quote) also asks three outcome-based questions with personalised dollar amounts.

### 1.4 The mapping math

Three equivalent ways to set the dial. The engine already supports the first two.

1. **Utility / CRRA.** With one risky asset and CRRA utility, the Merton fraction is π = (μ − r)/(σ²γ). Wikipedia states this as "commonly referred to as Merton's fraction", with the property that "a constant fraction of wealth is invested in stocks, no matter what the age or prosperity of the investor". The unconstrained mean-variance solution w = Σ⁻¹μ/λ is the same rule with **λ = γ**. So Barsky et al.'s median-type investor (γ ≈ 4) sits between Robo-Kit's current mid (λ = 2.5) and high-aversion (λ = 6.25) settings. That is a published anchor for the existing numbers.
2. **Target volatility** (Betterment; Robo-Kit's `calibrate_to_target_vol`). The score maps to an ex-ante volatility, and λ is solved to hit it. It is the most explainable option ("about how much this could swing in a normal year"). It is also the only one that stays comparable when μ changes, which is why METHOD.md §5 had to switch the backtest to risk-matching.
3. **Glide path / horizon.** Vanguard builds capacity into the utility model through age, savings, retirement income and other inputs. The simplest defensible Robo-Kit version: *capacity* falls as the goal date gets close (fewer years to recover), and the target volatility steps down along a published table. Tolerance does not change with time.

### 1.5 Behavioural guardrail

Capponi, Ólafsson & Zariphopoulou (Management Science 2022; arXiv 1911.01391) model a robo-advisor whose client's risk profile moves with markets. They find that "the optimal portfolio's Sharpe ratio and return distribution improve if the robo-advisor counters the client's tendency to reduce market exposure during economic contractions". **Implication:** a re-profiling request made during a drawdown should trigger a cooling-off step. Show the dollar consequence, ask again after a delay, and log it. It should not trigger an immediate de-risk. (Capacity changes such as job loss or a shorter horizon are different and should take effect.)

### 1.6 Recommended design (proposed; parameters are design choices, not evidence)

| Step | Rule | Why |
| --- | --- | --- |
| Tolerance score (1–10) | 4–6 outcome-framed questions (distribution-builder style: "which range of year-end values would you accept for a chance at X?"), plus a consistency penalty | GJS 2008; Wealthfront consistency rule |
| Capacity score (1–10) | Deterministic rules on horizon, emergency fund, income stability, share of net worth, goal importance | CSA/CIRO 31-368; Schwab "capacity" |
| Profile | `min(tolerance, capacity)`; overrides logged | CSA/CIRO 31-368 |
| Dial | Score → ex-ante volatility target (proposal: 3% at score 1 rising to ~15% at score 10; team to fix), then `calibrate_to_target_vol` | Betterment; comparability across μ methods |
| Horizon | Capacity steps down within 5 years of the goal date | Vanguard VLCM idea, simplified |
| Crash rule | Tolerance downgrades during a >10% drawdown go through cool-off plus consequence display | Capponi et al. 2022 |
| Disclosure | "The score is an estimate; questionnaires explain little of real behaviour; you can change it" | Klement 2015 |

---

## 2. Black-Litterman with views and confidence

The code already has `black_litterman_posterior(pi, Sigma, P, Q, tau, omega)` and `mu_method="black_litterman"`. What is missing is (a) a human-meaningful way to set Ω, (b) a disciplined way to turn signals into Q, and (c) a hard bound on how far views can move the weights.

### 2.1 Confidence: Idzorek's method

Idzorek's guide says "the magnitude of the tilts should be controlled by the user-specified confidence level based on an intuitive 0% to 100% confidence level". He also suggests that confidence can reflect "the historical accuracy or score of the model, screen, or analyst that produced the view". PyPortfolioOpt (MIT licence, ~6.1k GitHub stars, repo now `PyPortfolio/PyPortfolioOpt`) implements it: choose `omega="idzorek"` and pass `view_confidences`. Its docs note this "is particularly applicable if your views are the output of some statistical model".

**Build:** port Idzorek's Ω calibration (one scalar root-find per view) into `estimators.py` and the JS port. A 0% view must reproduce the equilibrium weights and a 100% view must reproduce the full-view weights. Both make exact unit tests.

### 2.2 Turning a quantitative signal into a view (Q)

Grinold's rule (via Zhipeng Yan's study notes on Grinold & Kahn, *Active Portfolio Management*; the book itself was not opened): "ALPHA = VOLATILITY*IC*SCORE". The same notes give a scale: "A good forecaster has an IC of 0.05, a great forecaster has an IC = 0.1, and a world class forecaster has an IC = 0.15." Applied to Robo-Kit:

    view_i = sigma_i x IC x z_i      (z_i = standardised signal, capped at +/-2; IC set ex ante, e.g. 0.02-0.05)

With IC = 0.03 and σ = 15%, a two-standard-deviation signal gives a 0.9% a-year view. This "garbage in, zeros out" scaling is the point: a signal with no demonstrated IC produces no tilt. The IC must come from Robo-Kit's own pre-registered walk-forward, not from the paper that introduced the signal. Section 3 explains why.

### 2.3 Bounding tilts

- Jorion (FAJ 2003): optimising against a benchmark with only a tracking-error limit "results in seriously inefficient portfolios unless some additional constraints are imposed"; "adding a constraint on total portfolio volatility can substantially improve the performance".
- **Rule for Robo-Kit:** the view-tilted portfolio must (i) keep the client's volatility target (re-calibrate λ after views), (ii) stay within a tracking-error budget versus the *no-view* portfolio (proposal: ≤1.0% a year for the whole signal layer), and (iii) move no single ETF by more than ±5 percentage points. Riskfolio-Lib already offers "Portfolio optimization with constraints on tracking error and turnover" (BSD-3 licence, ~4.5k stars), which serves as a reference implementation to test against. The JS FISTA solver would need the TE constraint as a penalty or bisection on λ.
- Show both portfolios, "with signals" and "without", in the UI. The no-view weights are the product's default.

### 2.4 Does BL help out of sample?

- Bessler, Opfer & Wolff (European Journal of Finance 2017; multi-asset, 1993–2011): BL portfolios "significantly outperform naïve-diversified portfolios (1/N rule and strategic weights)". Their abstract attributes this to "more stable mixed return estimates that incorporate the reliability of return predictions, smaller estimation errors, and lower turnover." Their views are sample-based, the data are pre-2012, and it is one study. Grade: supportive but not decisive.
- Allaj (Computational Management Science 2020): "Overall our results suggest that the BL model is a valid asset allocation strategy." Abstract only; weak.

**Net:** the BL machinery is worth building because it is the standard, auditable way to let *any* signal in with a confidence number and a bound. The evidence in sections 3–4 says the signals themselves should mostly stay switched off.

---

## 3. Asset-class signals: trend, value, carry, macro regime

| Signal | For | Against / limits | Grade |
| --- | --- | --- | --- |
| **Time-series momentum** | Moskowitz, Ooi & Pedersen (JFE 2012), 58 futures: "the past 12-month excess return of each instrument is a positive predictor of its future return"; it "persists for about a year and then partially reverses". Hurst, Ooi & Pedersen (AQR/JPM 2017): back to 1880, "consistently profitable over the next 110 years", noting "increased correlations across markets since the credit crisis". | Huang, Li, Wang & Zhou (JFE 2020): "asset-by-asset time series regressions reveal little evidence of TSM, both in- and out-of-sample"; the strategy's profit "is virtually the same as that of a similar strategy that is based on historical sample mean"; "the evidence on TSM is weak". | **Mixed** |
| **Value / valuation** | Asness, Moskowitz & Pedersen (JF 2013): "consistent value and momentum return premia across eight diverse markets and asset classes" (a cross-sectional, long-short result). FP Canada's 2026 planning assumptions use "the Shiller earnings to price average" as an input to long-run returns. | Asness, Ilmanen & Maloney (JOIM 2017) on CAPE timing: "encouraging in-sample long-horizon evidence and directionally right but weak and disappointing out-of-sample performance"; contrarian timing "has underperformed in the latter half of the sample". | **Weak** for monthly timing; **useful** as a long-run anchor |
| **Carry** | Koijen, Moskowitz, Pedersen & Vrugt (NBER w19325; JFE 2018): "carry predicts returns both in the cross section and time series" across equities, bonds, currencies, commodities, Treasuries, credit and index options. | Same paper: carry strategies do poorly together at times that "coincide with global recessions". | **Mixed** |
| **Technical + macro regime** | Neely, Rapach, Tu & Zhou (Mgmt Sci 2014): technical indicators "display statistically and economically significant in-sample and out-of-sample predictive power" for the US equity premium. Campbell & Thompson (NBER w11468): with sign restrictions, "The out-of-sample predictive power is small, but we find that it is economically meaningful." Mulliner et al., *Regimes* (JPM 2025): similarity to past macro states predicts **long-short equity factor** returns, 1985–2024. | Goyal & Welch (RFS 2008): predictors "have predicted poorly both in-sample (IS) and out-of-sample (OOS) for 30 years now". Goyal, Welch & Zafirov (RFS 2024): of 29 newer variables, "More than one-third of these new variables no longer have empirical significance even in-sample. Of those that do, half have poor out-of-sample performance." Their May 2022 slides go further: "0 out of 17 Monthly Freq IS Performance still by 2020. and OOS Performance still by 2020", and all 45 timing strategies "underperformed unconditional buy-and-hold". Campbell & Thompson also warn a real predictor can look bad "for an extended period of time". | **Mixed–weak** |

**What this means for Robo-Kit.**
1. **Default: no timing signals in weights.** This is consistent with the course line already adopted ("the worst ten-year period for any back-test is the next ten years").
2. **If an opt-in "evidence tilt" mode is offered,** the only candidates with multi-asset, multi-decade support are 12-month trend and carry. Each enters as a Grinold-scaled BL view with a pre-set IC, all under the 1% TE budget. The mode must first pass a pre-registered walk-forward on Robo-Kit's own ETF data, recorded in RESEARCH_LOG.md, before it ships.
3. **Valuation belongs in the projection engine, not the optimiser.** It is a reasonable input to 10-year capital-market assumptions (FP Canada does this). It is not a monthly timing rule.
4. **Regime detection** (the Man/Duke *Regimes* method) is shown on long-short factors, not long-only ETF allocations. At most it is a narrative ("today's conditions most resemble 20XX").

---

## 4. News, text, geopolitics, policy uncertainty, VIX, LLM-scored news

The requirement asks for evidence at *asset-class or broad-index, monthly* horizons, including negative results.

| Signal | Evidence | Direction | Grade |
| --- | --- | --- | --- |
| **Media pessimism** (Tetlock, JF 2007, WSJ column, daily) | "high media pessimism predicts downward pressure on market prices followed by a reversion to fundamentals" | Short-lived; reverses | **Weak** at monthly |
| **Aligned investor sentiment** (Huang, Jiang, Tu & Zhou, RFS 2015) | In GWZ's re-check it is one of ≈10 variables whose OOS performance was "described and confirmed in author's own sample", and one of 3 still showing in-sample power by 2020. But per the same slides, none of the 17 monthly variables kept both IS and OOS power by 2020. | High sentiment → lower returns | **Mixed** |
| **Economic Policy Uncertainty** (Baker, Bloom & Davis, NBER w21633 / QJE 2016) | Index built from newspaper coverage; "policy uncertainty innovations foreshadow declines in investment, output, and employment". Brogaard & Detzel (2014 WP, Mgmt Sci 2015): "EPU positively forecasts log excess market returns." | **Higher** uncertainty → **higher** expected returns (risk premium) | **Weak–mixed** |
| **Geopolitical Risk (GPR)** (Caldara & Iacoviello, AER 2022) | Macro: "higher GPR increases the probability of an economic disaster and predicts lower investment and employment". VAR: a GPR shock is followed "by a decline in stock prices and oil prices". Return prediction: Ma, Lu & Tao (Finance Research Letters 2022): the threats index "can help in predicting stock returns, especially during expansion" (with 14 macro variables). | Adverse for activity and prices on impact; return predictability conditional and thinly replicated | **Weak** for returns |
| **News-implied volatility (NVIX)** (Manela & Moreira, JFE 2017, WSJ front page since 1890) | "periods when NVIX is high are followed by periods of above average stock returns"; war and policy news "explains most of the time variation in risk premia" | Fear → higher later returns | **Mixed** |
| **Variance risk premium** (Bollerslev, Tauchen & Zhou, RFS 2009) | Explains "a nontrivial fraction of the time-series variation in post-1990 aggregate stock market returns"; strongest "at the intermediate quarterly return horizon". Needs model-free implied vol and intraday realised vol. | High premium → high returns | **Mixed** |
| **Volatility-managed exposure** | Moreira & Muir (NBER w22208 / JF 2017): taking less risk when volatility is high produces "large alphas". Cederburg, O'Doherty, Wang & Yan (JFE 2020), 103 strategies: they "do not systematically outperform"; realistic OOS versions "generally earn lower certainty equivalent returns and Sharpe ratios". | — | **Mixed** (fails OOS) |
| **LLM-scored news, market level** | Chen, Tang & Zhou (arXiv 2502.10008, Feb 2025): ChatGPT-3.5 good/bad-news ratios from WSJ front pages predict the market monthly, "𝑅²_OS of 1.17% for the out-of-sample period from January 2006 to December 2022". The authors themselves flag look-ahead: the model "is trained from a text corpus up until September 2021". They also find "Negative news correlates with returns but lacks predictive value." | Good-news underreaction | **Weak** (one WP, look-ahead) |
| **LLM-scored news, stock level** | Lopez-Lira & Tang (arXiv 2304.07619, v6 Oct 2025): GPT-4 headline scores predict next-day drift, but "Strategy returns decline as LLM adoption rises". Glasserman & Lin (arXiv 2309.17322): backtests suffer look-ahead bias and a "distraction effect"; anonymising headlines helps. He, Lv, Manela & Wu (arXiv 2502.21206): chronologically consistent models suggest "lookahead bias is modest" in their next-day application. | Daily, single stocks; decays | Not applicable to monthly ETF weights |
| **LLM forecasting practice review** (arXiv 2605.05211, Apr 2026) | Flags "fragility in sentiment analysis, dataset and horizon design, performance evaluation metrics, data leakage, illiquidity premia, and limits of stock price predictability" | — | Context |

**Three lessons that should shape the chatbot.**
1. **The sign is contrarian.** EPU, NVIX and the variance risk premium all say *high measured fear comes before higher average returns*. Capponi et al. say the advisor should *counter* the client's urge to cut risk in bad times. A Robo-Kit agent that answers a war headline with "consider reducing equities" would go against every study in this section. The agent spec should forbid headline-triggered allocation advice and instead route to (a) the client's own volatility target, (b) the historical drawdown and recovery table, and (c) a scenario stress test.
2. **LLM news scores cannot be backtested honestly with a model trained after the period tested.** If Robo-Kit ever experiments with an LLM news index, it needs timestamped news archives, a model whose training cutoff precedes the test window (or a ChronoGPT-style model), anonymised entity names (Glasserman & Lin), and a live paper-trading log before anything touches weights.
3. **Geopolitics and policy uncertainty are risk flags.** The defensible uses are: a dashboard badge ("geopolitical risk index is in its top decile since 1985"), a deterministic stress scenario (e.g., replay the ETF portfolio through the 1990 Gulf War, 2001, 2014 and 2022 GPR spikes using the bootstrap engine), and plain-language context. None of them changes weights.

---

## 5. Alternatives and complements to mean-variance for small ETF sets

| Method | Evidence | Fit for Robo-Kit |
| --- | --- | --- |
| **Hierarchical risk parity (HRP)** | Theory: Lipton, Antonov & López de Prado (ADIA Lab 2024) derive "analytical values for the noise of allocation weights" and show HRP "is indeed less noisy (and thus more robust)" than Markowitz. Empirical support found is weak: two NIFTY-50 sector studies with 8–11-month test windows (arXiv 2202.02728, 2210.00984). A 2026 *Empirical Economics* out-of-sample comparison exists but was behind a login (not opened). | Still no risk-aversion dial (METHOD.md §4). Could serve as the risky sleeve of a two-fund split (HRP sleeve + cash, mixed to hit the target vol) and as a benchmark in the backtest. Available in PyPortfolioOpt, Riskfolio-Lib and skfolio. |
| **Risk parity / equal risk contribution** | AQR (FAJ 2012): RP invests "more money in low-risk assets than in high-risk assets, and leveraging the resulting portfolio to a desired volatility". Theory rests on leverage aversion. | Unlevered, long-only RP in a retail account is bond-heavy and cannot reach mid or high risk targets. Benchmark only. |
| **CVaR / drawdown objectives** | Practice: Schwab optimises return against CVaR across simulated histories. Theory: Lim, Shanthikumar & Vahn (OR Letters 2011), as summarised by Ban, El Karoui & Lim (arXiv 1111.2091): they show "how fragile the solution to the empirical mean-CVaR problem is, even in the ideal situation of having iid Gaussian log-return data". The fix proposed there is regularisation, or solving Markowitz when returns are elliptical. | Keep MV as the objective. Compute CVaR(95%) and maximum drawdown on the 500 stationary-bootstrap histories Robo-Kit already generates, **report** them, and optionally use them as a **guardrail** (reject a profile's portfolio if its 1-in-20-year loss exceeds the loss the client said they could bear). Riskfolio-Lib and skfolio implement CVaR/CDaR for cross-checking. |
| **1/N** | DeMiguel, Garlappi & Uppal (RFS 2009): none of 14 models "is consistently better than the 1-N rule"; beating it needs "around 3000 months for a portfolio with 25 assets". | Already a benchmark and optional blend (METHOD.md). With the v2 universe of thousands of ETFs, the shortlist size matters. Keep the shortlist small (roughly 5–15 ETFs) so estimation error stays manageable. |
| **Minimum variance** | Ovalle et al. (arXiv 2607.18624, Jul 2026): minimum-variance portfolios are "highly sensitive to covariance estimation error"; fragility comes from "threshold effects" between correlation structure and volatilities. | Supports keeping shrinkage and resampling (already in place). |

**When do these beat mean-variance for small ETF sets?** The honest reading is: *when expected returns are unanchored.* Robo-Kit's MV already anchors μ to equilibrium, shrinks Σ and resamples, which removes most of the instability that HRP and 1/N were designed to fix. None of the evidence opened shows HRP, RP or CVaR beating an anchored, shrunk, resampled MV at matched risk on multi-asset ETF data. Add HRP and 1/N to the pre-registered backtest grid as benchmarks, and let the data speak.

**Borrow, don't rebuild:** skfolio (BSD-3, ~2.4k stars, pushed 28 Sep 2026) ships "Walk Forward", "Combinatorial Purged Cross-Validation", Black & Litterman, entropy pooling, HRP/HERC and CVaR/CDaR on a scikit-learn API. It is a good independent oracle for Robo-Kit's Python tests. Nothing needs to be imported into the JS runtime.

---

## 6. Monte Carlo / bootstrap goal projections for retail users

### 6.1 Assumptions

- **FP Canada / Institute of Financial Planning, 2026 Projection Assumption Guidelines** (the Canadian planning standard): "Short term 2.4% Fixed income 3.2% Canadian equities 6.3% U.S. equities 6.4% International developed-market equities 6.6% Emerging market equities 7.5%". These are before fees ("fees paid by clients both for products and advice must be subtracted"). The guidelines are geometric means: "For the purposes of Monte Carlo analysis, a conversion needs to be done from geometric to arithmetic mean (AM) assumptions." They also recommend sensitivity analysis, which "might take the form of a Monte Carlo analysis, scenario testing using an adjusted rate of return, or determining a client's minimum required rate of return."
- **Vanguard's VCMM** "forecasts distributions of future returns for a wide array of broad asset classes". This confirms the industry norm of simulating distributions, not point paths.

**Build.** A deterministic `project_goal()` that:
1. takes the optimiser's weights;
2. uses Robo-Kit's stationary block bootstrap of monthly ETF returns, **re-centred** so each asset class's mean equals the FP Canada 2026 assumption net of the ETF's MER (the US market toggle needs its own published CMA source; see gaps);
3. adds contributions and withdrawals;
4. returns 10th / 25th / 50th / 75th / 90th percentile paths, the probability of ending below the goal, the median shortfall *size* in those cases, and the worst 12-month loss at the 5th percentile.

Re-centring keeps the bootstrap's fat tails and volatility clustering (already justified in METHOD.md) without projecting 2016–2026 returns forward.

### 6.2 Presenting uncertainty honestly

| Finding | Source | Design consequence |
| --- | --- | --- |
| "success" really means an excess left over, and failure means "some kind of mid-course adj[ustment]"; Kitces suggests relabelling as "probability of adjustment" and "probability of excess" | Kitces (kitces.com) | Show "chance you'll need to adjust (save more, spend less, retire later)", plus how big that adjustment would be. Never show "X% success" alone. |
| Showing long-horizon rather than one-year return distributions makes workers "invest more of their retirement savings in stocks" | Benartzi & Thaler (Mgmt Sci 1999) | The display changes the choice. Show **both** the 1-year loss range and the long-horizon range on the same screen. Don't pick the frame that sells more equity. |
| Experience sampling and a combined "risk tool" raised risky allocations and made participants "more accurate on recall questions regarding the expected return and the probability of a loss", with "no evidence of greater dissatisfaction" | Kaufmann, Weber & Haisley (Mgmt Sci 2013) | Add a "play 20 random years" button that draws single bootstrap paths one by one. It is cheap and deterministic. |
| Letting people build outcome distributions elicits risk and loss aversion reliably | Goldstein, Johnson & Sharpe (JCR 2008) | Reuse the same engine for the risk questionnaire (section 1.6). |

### 6.3 Required disclosures (US rules as the stricter template; see gaps for Canada)

- **FINRA Rule 2214** (broker-dealer "investment analysis tools"): the mandated sentence is "The projections or other information generated by [tool] regarding the likelihood of various investment outcomes are hypothetical in nature, do not reflect actual investment results and are not guarantees of future results." Firms must also explain that "results may vary with each use and over time" and "describe the criteria and methodology used, including the investment analysis tool's limitations and key assumptions".
- **SEC Marketing Rule 206(4)-1** (investment advisors): "Hypothetical performance means performance results that were not actually achieved by any portfolio of the investment adviser", and advertising it requires relevance "to the likely financial situation and investment objectives of the intended audience". The definition excludes "An interactive analysis tool where a client ... uses the tool to produce simulations and statistical analyses that present the likelihood of various investment outcomes", subject to the conditions in the rule.

**Implication:** Robo-Kit's projection panel and backtest panel should carry fixed, script-rendered disclosure text (not LLM-generated). The text should name the method (block bootstrap, re-centred to FP Canada 2026 means net of fees), the ETF universe considered, the fact that results change with each run, and that backtests are hypothetical. The chatbot may paraphrase but must link to the fixed text.

---

## 7. What Robo-Kit should build, borrow, avoid, disclose

**Build (deterministic, unit-tested, ported to JS):**
1. `risk_profile(answers) -> {tolerance, capacity, profile=min(...), target_vol}` with the consistency penalty, horizon step-down and crash cool-off rule (1.6).
2. `idzorek_omega(views, confidences)` plus a tracking-error-budget check (≤1% TE vs no-view; ±5pp per ETF; volatility target preserved). Unit tests: 0% confidence reproduces equilibrium; 100% reproduces full view.
3. `signal_to_view(z, sigma, IC)` implementing Grinold scaling, with IC read from a pre-registered config file. Default IC = 0, which means views are off.
4. Risk-flag endpoints (no weight effect): GPR percentile, EPU percentile, VIX percentile, trend state per ETF, each with its source date. These give the chatbot facts to cite instead of opinions.
5. `stress_test(weights, episode)`: replays named historical episodes (2008, 2020, 2022 rates, GPR spikes) on the portfolio.
6. `project_goal(...)`: re-centred bootstrap percentiles, "probability of adjustment", shortfall size, fixed disclosure text.
7. Report CVaR(95%) and maximum drawdown from the existing bootstrap draws next to volatility.

**Borrow (as test oracles, not runtime dependencies):** PyPortfolioOpt (Idzorek Ω), Riskfolio-Lib (TE constraint, CVaR/CDaR, HRP/HERC), skfolio (walk-forward, CPCV, BL, entropy pooling).

**Avoid:**
- Headline- or LLM-driven changes to weights.
- Volatility timing.
- CVaR as the optimisation objective.
- Unlevered risk parity as a default.
- Any signal whose IC was taken from its original paper rather than Robo-Kit's own pre-registered test.
- "Success probability" labels.
- Picking the long-horizon frame alone.

**Disclose:**
- Questionnaire limits (Klement).
- "Target, not guarantee" volatility (METHOD.md §5.2 already shows the 4% target realised 11.7% in 2020).
- Hypothetical nature of projections and backtests (FINRA 2214 / SEC 206(4)-1 language).
- That news and geopolitical indicators are shown for context and do not move the portfolio.
- The number of signal configurations tried (RESEARCH_LOG.md).

---

## 8. Agent-behaviour rules implied by this evidence (for the chatbot's .md spec)

1. Every number comes from a page function (risk_profile, optimize, project_goal, stress_test, risk_flags). The model never computes or estimates returns.
2. If the user brings a headline ("war in X, should I sell?"), the agent (a) states the portfolio's volatility target and historical worst-year range from `stress_test`, (b) shows the relevant risk flag with its date, (c) says that research finds high fear readings have historically come before *higher*, not lower, average returns, without promising anything, and (d) offers to re-run the risk questionnaire *only* for capacity changes, with the cool-off rule for tolerance.
3. The agent may explain trend, carry and valuation as concepts. It may only say "your portfolio tilts toward X because of signal Y" if the opt-in tilt mode is on, and it must then quote the TE budget.
4. Projections are always spoken as ranges with the fixed disclosure link.

---

## 9. Sources opened (verbatim quotes above were taken from these)

| # | Source | URL | Check |
| --- | --- | --- | --- |
| 1 | Wealthfront Classic Portfolio Investment Methodology | https://research.wealthfront.com/whitepapers/investment-methodology/ | raw |
| 2 | Schwab Intelligent Portfolios, portfolio construction | https://www.schwab.com/automated-investing/portfolio-construction | raw |
| 3 | Schwab Intelligent Portfolios, asset allocation | https://www.schwab.com/automated-investing/asset-allocation | raw |
| 4 | Vanguard, value of personalized glide paths | https://ownyourfuture.vanguard.com/content/en/advice-profile/resources/insights/value-of-personalized-glide-paths.html | raw |
| 5 | Vanguard, target-date approach (VCMM) | https://workplace.vanguard.com/investment/strategies/target-date-funds-approach.html | raw |
| 6 | Joint CSA/CIRO Staff Notice 31-368 (10 Dec 2025) | https://www.osc.ca/en/securities-law/instruments-rules-policies/3/31-368/joint-csaciro-staff-notice-31-368-client-focused-reforms-review-registrants-know-your-client-know | raw |
| 7 | Klement, Investor Risk Profiling (CFA RF brief) | https://rpc.cfainstitute.org/sites/default/files/-/media/documents/article/rf-brief/rfbr-v1-n1-1-pdf.pdf | raw |
| 8 | Barsky, Juster, Kimball & Shapiro, NBER w5213 | https://www.nber.org/papers/w5213 | raw |
| 9 | Merton's portfolio problem (Wikipedia) | https://en.wikipedia.org/wiki/Merton%27s_portfolio_problem | raw |
| 10 | Capponi, Ólafsson & Zariphopoulou, arXiv 1911.01391 | https://arxiv.org/abs/1911.01391 | raw |
| 11 | Goldstein, Johnson & Sharpe, JCR 2008 | https://www.dangoldstein.com/papers/GoldsteinJohnsonSharpe_OutcomesVsProducts_JCR08.pdf | raw |
| 12 | Idzorek, step-by-step BL guide | https://people.duke.edu/~charvey/Teaching/BA453_2006/Idzorek_onBL.pdf | raw |
| 13 | PyPortfolioOpt BL docs | https://pyportfolioopt.readthedocs.io/en/latest/BlackLitterman.html | raw |
| 14 | Grinold & Kahn study notes (Z. Yan) | https://people.brandeis.edu/~yanzp/Study%20Notes/Active%20Portfolio%20Management.pdf | raw (TLS cert invalid; secondary source) |
| 15 | Jorion, FAJ 2003 abstract | https://rpc.cfainstitute.org/research/financial-analysts-journal/2003/portfolio-optimization-with-tracking-error-constraints | raw |
| 16 | Bessler, Opfer & Wolff, EJF 2017 | https://ideas.repec.org/a/taf/eurjfi/v23y2017i1p1-30.html | raw |
| 17 | Allaj, CMS 2020 | https://ideas.repec.org/a/spr/comgts/v17y2020i3d10.1007_s10287-020-00373-6.html | raw |
| 18 | Moskowitz, Ooi & Pedersen, JFE 2012 | http://pages.stern.nyu.edu/~lpederse/papers/TimeSeriesMomentum.pdf | raw |
| 19 | Hurst, Ooi & Pedersen, century of trend | https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing | raw |
| 20 | Huang, Li, Wang & Zhou, JFE 2020 | https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html | raw |
| 21 | Asness, Moskowitz & Pedersen, JF 2013 | https://www.aqr.com/Insights/Research/Journal-Article/Value-and-Momentum-Everywhere | raw |
| 22 | Asness, Ilmanen & Maloney, JOIM 2017 | https://www.aqr.com/-/media/AQR/Documents/Insights/White-Papers/Market-Timing-Sin-a-Little.pdf | raw |
| 23 | Koijen, Moskowitz, Pedersen & Vrugt, Carry | https://www.nber.org/papers/w19325 | raw |
| 24 | Neely, Rapach, Tu & Zhou, Mgmt Sci 2014 | https://ideas.repec.org/a/inm/ormnsc/v60y2014i7p1772-1791.html | raw |
| 25 | Campbell & Thompson, NBER w11468 | https://www.nber.org/papers/w11468 | raw |
| 26 | Goyal & Welch, RFS 2008 | https://ideas.repec.org/a/oup/rfinst/v21y2008i4p1455-1508.html | raw |
| 27 | Goyal, Welch & Zafirov, RFS 2024 | https://ideas.repec.org/a/oup/rfinst/v37y2024i11p3490-3557..html | raw |
| 28 | Goyal, Welch & Zafirov slides, May 2022 | https://www.ivo-welch.info/research/presentations/gwz-apr22.pdf | raw |
| 29 | Mulliner et al., Regimes | https://people.duke.edu/~charvey/Research/Published_Papers/P176_Regimes.pdf | raw |
| 30 | Tetlock, JF 2007 | https://ideas.repec.org/a/bla/jfinan/v62y2007i3p1139-1168.html | raw |
| 31 | Baker, Bloom & Davis, NBER w21633 | https://www.nber.org/papers/w21633 | raw |
| 32 | Brogaard & Detzel, 2014 WP | https://www.aeaweb.org/conference/2015/retrieve.php?pdfid=8971&tk=bkynzSa8 | raw |
| 33 | Caldara & Iacoviello, AER 2022 | https://www.matteoiacoviello.com/gpr_files/GPR_PAPER.pdf | raw |
| 34 | Ma, Lu & Tao, FRL 2022 | https://ideas.repec.org/a/eee/finlet/v50y2022ics1544612322004160.html | raw |
| 35 | Manela & Moreira, JFE 2017 | https://ideas.repec.org/a/eee/jfinec/v123y2017i1p137-162.html | raw |
| 36 | Bollerslev, Tauchen & Zhou, RFS 2009 | https://ideas.repec.org/a/oup/rfinst/v22y2009i11p4463-4492.html | raw |
| 37 | Moreira & Muir, NBER w22208 | https://www.nber.org/papers/w22208 | raw |
| 38 | Cederburg et al., JFE 2020 | https://econpapers.repec.org/RePEc:eee:jfinec:v:138:y:2020:i:1:p:95-117 | raw |
| 39 | Chen, Tang & Zhou, arXiv 2502.10008 | https://arxiv.org/abs/2502.10008 (PDF grepped) | raw |
| 40 | Lopez-Lira & Tang, arXiv 2304.07619 | https://arxiv.org/abs/2304.07619 | raw |
| 41 | Glasserman & Lin, arXiv 2309.17322 | https://arxiv.org/abs/2309.17322 | raw |
| 42 | He, Lv, Manela & Wu, arXiv 2502.21206 | https://arxiv.org/abs/2502.21206 | raw |
| 43 | LLM forecasting review, arXiv 2605.05211 | https://arxiv.org/abs/2605.05211 | raw |
| 44 | Lipton, Antonov & López de Prado (ADIA Lab) | https://www.adialab.ae/research-series/overcoming-markowitzs-instability-with-the-help-of-the-hierarchical-risk-parity | raw |
| 45 | HRP NIFTY studies | https://arxiv.org/abs/2202.02728 ; https://arxiv.org/abs/2210.00984 | raw |
| 46 | Asness, Frazzini & Pedersen, risk parity | https://www.aqr.com/Insights/Research/Journal-Article/Leverage-Aversion-and-Risk-Parity | raw |
| 47 | Ban, El Karoui & Lim (cites Lim et al. 2011) | https://arxiv.org/pdf/1111.2091v2 | raw |
| 48 | DeMiguel, Garlappi & Uppal, RFS 2009 | https://ideas.repec.org/a/oup/rfinst/v22y2009i5p1915-1953.html | raw |
| 49 | Ovalle et al., arXiv 2607.18624 | https://arxiv.org/abs/2607.18624 | raw |
| 50 | FP Canada / IFP 2026 Projection Assumption Guidelines | https://www.fpcanada.ca/docs/professionalsitelibraries/standards/projection-assumption-guidelines.pdf?sfvrsn=6e32eebb_1 | raw |
| 51 | Kitces, renaming Monte Carlo outcomes | https://www.kitces.com/blog/renaming-the-outcomes-of-a-monte-carlo-retirement-projection/ | raw |
| 52 | Benartzi & Thaler, Mgmt Sci 1999 | https://ideas.repec.org/a/inm/ormnsc/v45y1999i3p364-381.html | raw |
| 53 | Kaufmann, Weber & Haisley, Mgmt Sci 2013 | https://ideas.repec.org/a/inm/ormnsc/v59y2013i2p323-340.html | raw |
| 54 | FINRA Rule 2214 | https://www.finra.org/rules-guidance/rulebooks/finra-rules/2214 | fetch (script got HTTP 403) |
| 55 | SEC Rule 206(4)-1 (Cornell LII) | https://www.law.cornell.edu/cfr/text/17/275.206(4)-1 | raw |
| 56 | GitHub metadata: PyPortfolioOpt, Riskfolio-Lib, skfolio | `gh api repos/...` (28 Sep 2026: 6,060 / 4,519 / 2,443 stars; MIT / BSD-3 / BSD-3) | API |

---

## 10. Gaps (not resolved in this lane)

- **Not opened (blocked or paywalled):** López de Prado (2016) HRP original (SSRN 403); Lim, Shanthikumar & Vahn (2011) original (ScienceDirect 403; used via the Ban et al. citation); the 2026 *Empirical Economics* HRP comparison (login); the IMF April 2025 GFSR chapter on geopolitical risk and asset prices (403); Schlosky et al. (IRFA 2024) on GPR-conditional forecasting (403); Faber (2007) 10-month moving average (SSRN); Kolm & Ritter's BL survey (403); the Grinold & Kahn book itself (used secondary study notes).
- **Canadian disclosure rules for projections** (CIRO communications rules, CSA guidance on hypothetical performance for advisors) were not researched in this lane. FINRA 2214 and SEC 206(4)-1 are used as the stricter template. The legal lane should confirm.
- **US capital-market assumptions** for the US-ETF market toggle: no neutral US equivalent of FP Canada's guidelines was opened. Candidates are the firms' own published CMAs (Vanguard, BlackRock, JPMorgan), which differ from each other; picking one needs a sourcing decision.
- **Goyal-Welch-Zafirov discrepancy:** the May 2022 slides ("0 out of 17 ... still by 2020") are stronger than the published 2024 abstract ("A small number of variables still perform reasonably well"). The published paper's final variable list was not opened; the direction (monthly market timing is fragile) is the same in both.
- **No asset-class, monthly, post-publication OOS evidence was found for GPR, EPU or LLM news indices.** Robo-Kit's own walk-forward would be the first honest test, and it should be pre-registered before it is run.
- The proposed numeric parameters (score→volatility table, 1% TE budget, ±5pp per-ETF tilt cap, IC 0.02–0.05, crash cool-off threshold) are **design choices**, not findings. They need team sign-off and a line in RESEARCH_LOG.md.
