% Robo-Kit v3: a risk-calibrated, resampled mean-variance engine and its pre-registered evaluation
% Design, proofs and the results of a registered run, for Canadian and US investors
% Robo-Kit team · MMAI 823, AI in Finance · October 2026

# Abstract

Robo-Kit is an open-source portfolio engine for Canadian and US investors. It solves a long-only mean-variance problem on equilibrium returns from a written policy mix, with shrunk covariances, averages the weights over resampled histories, and sets the client's risk level as a volatility target that it calibrates on the mix the client actually receives. This paper sets out the design, ties each decision to a source, a proof or a test, proves three properties the engine relies on, and reports an evaluation whose design was fixed in advance, examined in eighteen rounds by outside reviewers before it ran, and run from a committed protocol. In a simulation with a known truth ({{provenance.replications|int}} histories per world), the engine is within {{E3.summary.a.3.180.robokit.loss_bp|f1}} basis points a year of the best constrained portfolio when its model is right. When its expected returns are wrong, it and the other methods built on the same prior lose about {{E3.summary.b.3.180.robokit.loss_bp|f0}} basis points a year, a static stock-bond mix loses about {{derived.e3.b.static_mix_advantage|f1}} basis points a year less than Robo-Kit, and resampling neither helps nor hurts. Over {{E1.CA.strategies.robokit.3.months|int}} months in Canada, realised volatility was {{E1.CA.risk_delivery.primary.2.ratio|f2}}, {{E1.CA.risk_delivery.primary.3.ratio|f2}} and {{E1.CA.risk_delivery.primary.4.ratio|f2}} times its target at the three primary levels (the pre-registered reading is "inconclusive": two simultaneous intervals reach just past the band), and no Sharpe-ratio difference from four benchmarks survived adjustment for multiple tests; against a static mix the engine was shown not worse by more than 0.10 at two of three levels. In the US ({{E1.US.strategies.robokit.3.months|int}} months, exploratory) realised risk ran about a third above target. A pre-registered precision rule raised the projection paths to {{locked_defaults.projection_paths|int}}. The code, the plan, every examiner finding and every ruling are public.

# 1. Introduction

A robo-adviser turns a few answers about a client into a portfolio. Most of what makes that portfolio good or bad happens in a part the client never sees: how expected returns and risks are estimated, how a risk level becomes a portfolio, and what happens between the optimum and the orders. Descriptions of these methods inside commercial robo-advisers are rare (Beketov, Lehmann and Wittke 2018). Robo-Kit was built in the open to show one way to do it, for Canadian and US exchange-traded funds, and this paper is its full account.

The engine faces the standard problem of mean-variance optimisation: its inputs are estimated, and the optimizer magnifies their errors (Michaud 1989; Chopra and Ziemba 1993). It answers with one tool from each family the literature offers: shrinkage of the inputs, constraints on the solution, and averaging over resampled inputs. Version 3 adds two things the earlier versions lacked. First, a calibration that makes each risk level deliver its stated volatility for the mix the client receives, after resampling and after small positions are dropped, rather than for an intermediate solution. Second, an implementation layer: a rebalancer that turns weights into orders, the regulator's risk rating of every mix, and opt-in suitability checks.

The paper makes four contributions. It ties each of the engine's design decisions to an authentic source, a proof or a test, in a register published with the code (docs/DECISIONS.md), and says which decisions are policy. It proves three properties the engine relies on (Section 4.11). It reports an evaluation whose design was written before any of it ran, examined as a registered report's Stage 1 review would be, by outside reviewers asked to question it as a demanding professor would, and revised until a review accepted it as it stood. And it reports the results of that evaluation as they came out, including the ones that do not favour the engine.

The main findings are these.
- When its model is right, the engine is close to the best portfolio the constraints allow. When its expected returns are wrong, the choice of prior matters far more than resampling or covariance estimation, and a static stock-bond mix did slightly better in simulation.
- Resampling made almost no difference to any result. With equilibrium returns every resampled solution is close to the same portfolio, so averaging them changes little; the registered rule kept it, and this study gives no evidence that it helps.
- In Canada over {{E1.CA.strategies.robokit.3.months|int}} months, each primary level's realised volatility was within a few percent of its target. In the US over {{E1.US.strategies.robokit.3.months|int}} months it was about a third above target, which is the clearest negative result.
- No Sharpe-ratio comparison was conclusive after adjustment, as the power statement written before the run expected; against a static mix in Canada the engine was shown not worse by more than 0.10 at levels 3 and 4.
- The evaluation changed one product default under a pre-registered rule (projection paths, from 2,000 to {{locked_defaults.projection_paths|int}}) and exposed one gap the product should close: no crisis replay covers the 2000-2002 bear market.

Section 2 reviews the literature, Section 3 the data, Section 4 the method and the proofs, Section 5 the evaluation design, Section 6 the results, Section 7 the adversarial validation, and Section 8 the limitations.

# 2. Related literature

**Estimation error.** Mean-variance optimisation is an "estimation-error maximiser" (Michaud 1989). Errors in means matter about ten times more than errors in variances (Chopra and Ziemba 1993), and on short samples the plug-in portfolio can underperform naive diversification (DeMiguel, Garlappi and Uppal 2009), although that comparison depends on how the alternatives are specified (Kritzman, Page and Turkington 2010). The responses fall into three families, and the engine uses one of each.

**Shrinking the inputs.** For covariances, linear shrinkage toward a structured target (Ledoit and Wolf 2004) and, when the number of assets is large relative to the sample, nonlinear shrinkage of the eigenvalues (Ledoit and Wolf 2017, 2022). For means, Bayes-Stein estimation (Jorion 1986), or replacing estimated means with the equilibrium returns implied by a reference portfolio (Sharpe 1974; Black and Litterman 1992; He and Litterman 1999). Black-Litterman then lets an investor's views move the equilibrium, weighted by stated confidence (Idzorek 2007; Walters 2014).

**Constraining the solution.** Long-only and cap constraints act like shrinkage of the covariance matrix (Jagannathan and Ma 2003). Norm constraints generalise this (DeMiguel, Garlappi, Nogales and Uppal 2009). Tracking-error limits bound the departure from a reference (Jorion 2003).

**Averaging over resampled inputs.** Resampled efficiency (Michaud 1989; Michaud and Michaud 2008) averages the optimal weights across bootstrap samples. The evidence is mixed. Markowitz and Usmen (2003) find it beats a diffuse Bayes rule in their experiment; Harvey, Liechty and Liechty (2008) reverse the result with a better-specified Bayes rule; Scherer (2002) shows the averaged portfolio can be inefficient and drift off the investor's risk level. This paper tests resampling in a simulation with a known truth, under a pre-set rule, rather than assuming either side.

**Risk targeting.** Scaling portfolios to a target volatility is common practice. The evidence on timing it is contested (Moreira and Muir 2017; Cederburg, O'Doherty, Wang and Yan 2020), but this engine does not time: it sets a fixed long-run target per risk level and asks whether realised risk stays near it.

**Rebalancing.** With proportional costs the optimal policy leaves a no-trade region and trades back to its boundary (Donohue and Yip 2003). Asset managers' research recommends threshold rebalancing with a destination short of the target (Vanguard 2010, 2024) and using cash flows first.

**Evaluating back-tests.** Sharpe ratios of correlated strategies need tests robust to fat tails and serial dependence (Ledoit and Wolf 2008). Repeated testing inflates apparent skill unless the number of trials is counted (Bailey and Lopez de Prado 2014; Harvey, Liu and Zhu 2016), and a credible back-test fixes its design before it sees the data (Arnott, Harvey and Markowitz 2019). This paper follows that protocol: the evaluation was pre-registered, reviewed by outside examiners in eighteen rounds until a review accepted it as it stood, and run once, with one re-run for a disclosed bug fix.

**Robo-advice.** Robo-advisers improve diversification most for investors who start undiversified (D'Acunto, Prabhala and Rossi 2019; Rossi and Utkus 2020), and descriptions of the quantitative methods inside commercial robo-advisers are rare (Beketov, Lehmann and Wittke 2018). Canadian regulation sets the frame: online advice is given by registered portfolio managers with human oversight (CSA Staff Notice 31-342), suitability starts from the lower of a client's willingness and ability to bear risk (31-103CP s.13.2), and fund risk is disclosed on a standard-deviation scale (NI 81-102 Appendix F).

# 3. Data

**Universe.** The engine's universe is every exchange-traded fund listed in Canada and the US with usable data: {{derived.data.CA.listed|int}} Canadian and {{derived.data.US.listed|int}} US listings in the snapshot used for the run, of which {{derived.data.CA.eligible|int}} and {{derived.data.US.eligible|int}} are eligible. A fund is eligible if it has at least 36 months of its own returns, assets of at least 20 million (Canada) or 50 million (US) in its trading currency, average daily traded value of at least 50,000 or 250,000, and is not leveraged, inverse, a single stock or a depositary receipt (online advisers in Canada use "unleveraged exchange traded funds", CSA Staff Notice 31-342). A data-integrity screen also excludes 14 funds whose monthly return doubled or halved while similar funds did not (decision D9).

**Reference shelves.** Each market has a reference shelf of {{derived.data.CA.shelf_funds|int}} funds, one broad, low-cost fund per asset-class slot plus a cash fund, chosen by a written scoring rule: in Canada {{derived.data.CA.shelf.0|raw}}, {{derived.data.CA.shelf.1|raw}}, {{derived.data.CA.shelf.2|raw}}, {{derived.data.CA.shelf.3|raw}}, {{derived.data.CA.shelf.4|raw}}, {{derived.data.CA.shelf.5|raw}}, {{derived.data.CA.shelf.6|raw}}, {{derived.data.CA.shelf.7|raw}}, {{derived.data.CA.shelf.8|raw}} and {{derived.data.CA.shelf.9|raw}}; in the US {{derived.data.US.shelf.0|raw}}, {{derived.data.US.shelf.1|raw}}, {{derived.data.US.shelf.2|raw}}, {{derived.data.US.shelf.3|raw}}, {{derived.data.US.shelf.4|raw}}, {{derived.data.US.shelf.5|raw}}, {{derived.data.US.shelf.6|raw}}, {{derived.data.US.shelf.7|raw}}, {{derived.data.US.shelf.8|raw}} and {{derived.data.US.shelf.9|raw}}. Clients may add their own picks within caps.

**Returns.** Monthly total returns come from dividend- and split-adjusted month-end closes (Yahoo Finance), so they are net of each fund's fee; the month in progress is dropped and gaps stay gaps. Funds that trade in another currency are converted at month-end exchange rates. Cash earns last month's 3-month bill yield over 12 (Bank of Canada series V80691344; the US 13-week bill), which also gives the risk-free rate. Funds younger than the estimation window are extended back with written stand-ins that overlap them for at least 24 months with a correlation of at least 0.8, matched for currency hedging; each extension is disclosed with every result. The data snapshot ends in {{derived.data.as_of|raw}}.

**Planning returns.** Projections and the simulation's world b use the FP Canada and Institute of Financial Planning 2026 Projection Assumption Guidelines (geometric, before fees, then net of each fund's fee): short term 2.4%, fixed income 3.2%, Canadian equities 6.3%, US equities 6.4%, international developed equities 6.6% and emerging-market equities 7.5%. For US bonds and cash the engine uses today's Treasury yields; real estate takes its region's equity assumption and gold the short-term rate. The optimizer itself never uses these numbers: it uses the equilibrium returns of Section 4.3.

# 4. Method

## 4.1 Problem and notation

The engine chooses weights $w \in \mathbb{R}^N$ over a shelf of $N$ exchange-traded funds: one broad, low-cost fund per asset-class slot, a cash fund, and up to a few funds the client adds ("own picks"). Monthly total returns $r_{t} \in \mathbb{R}^N$, $t = 1, \dots, T$, come from dividend- and split-adjusted month-end prices, so they are net of each fund's fee. The engine solves the long-only mean-variance problem

$$\max_{w}\ \mu^{\top} w - \frac{\lambda}{2}\, w^{\top} \Sigma\, w \quad \text{s.t.} \quad \mathbf{1}^{\top} w = 1,\quad \ell \le w \le u,\quad \textstyle\sum_{i \in G} w_i \le g$$

where $\mu$ are expected excess returns, $\Sigma$ the annual covariance, $\ell$ and $u$ the lower and upper limits, $G$ the own picks and $g$ their joint limit: the mean-variance problem of Markowitz (1952), with limits. Three things make this a product rather than a textbook exercise: what goes into $\mu$ and $\Sigma$ (Sections 4.2 and 4.3), how $\lambda$ is set so that a client's chosen level delivers a stated risk (Sections 4.5 and 4.8), and what happens between the optimum and the orders a person places (Sections 4.9 and 4.10).

## 4.2 Risk: shrunk covariance

The sample covariance of a few dozen funds over 15 years is noisy, and a mean-variance optimizer exploits exactly that noise (Michaud 1989; Chopra and Ziemba 1993). The engine shrinks it toward a constant-correlation target (Ledoit and Wolf 2004):

$$\hat{\Sigma} = 12\,\frac{T}{T-1}\left(\hat{s}\,F + (1-\hat{s})\,S\right), \qquad F_{ii} = S_{ii}, \quad F_{ij} = \bar{\rho}\sqrt{S_{ii}S_{jj}}$$

with $S$ the sample covariance (divisor $T$), $\bar{\rho}$ the average sample correlation and $\hat{s}$ the estimated optimal intensity. When the list is wide, with $N/T > 0.25$, linear shrinkage leaves the small eigenvalues too small, and the engine switches to quadratic-inverse shrinkage (QIS; Ledoit and Wolf 2022), which keeps the sample eigenvectors and shrinks the inverse eigenvalues. The switch point is tested by simulation (Section 5, E3).

The factor $12\,T/(T-1)$ annualises the matrix and puts it on the same unbiased footing as the stock-market volatility it is compared with (Section 4.5). It does not move the weights at a given $\lambda$ (Proposition 2).

## 4.3 Expected returns: equilibrium from a written policy mix

Sample means are the largest source of estimation error in mean-variance analysis (Chopra and Ziemba 1993). The engine never uses them. It reverse-engineers the returns that would make a reference portfolio $w^{0}$ optimal (Sharpe 1974; Black and Litterman 1992; He and Litterman 1999):

$$\pi = \delta\, \hat{\Sigma}\, w^{0}, \qquad \delta = 2.5$$

$w^{0}$ is a written policy mix rather than fund sizes: 60% stocks, 35% bonds, 3% real estate and 2% gold, with 30% of the stock share in Canada. Doeswijk, Lam and Swinkels (2014) call the market portfolio a natural benchmark for investors; the product departs from it on purpose, with class weights that are a product policy (their sensitivity is reported, E5). Holding Canadian equities at about ten times Canada's 2.7% share of world equity follows Vanguard Investments Canada (2024), which sees "a reasonable equity balance of around 30% home bias, in Canadian securities"; the sensitivity of the mix to this choice is reported (E5). The value of $\delta$ does not matter for the weights once $\lambda$ is calibrated (Proposition 1); 2.5 is He and Litterman's (1999) "world average risk tolerance" and only scales the model returns shown beside the mix.

## 4.4 Limits

Each fund is capped at 50% of the portfolio. Narrow or volatile slots are capped lower (real estate, gold and high-yield bonds 10%; emerging markets and small caps 15%; real-return bonds 20%; long bonds 25%), and cash at 100%, 30% and 15% at levels 1, 2 and 3-5. Own picks are capped at 10% each (crypto 5%) and 10%, 20% or 30% together, depending on the level. Constraints of this kind are known to stabilise optimised portfolios by acting as shrinkage (Jagannathan and Ma 2003); the caps themselves are policy, and their effect is measured (E1 ablation, E5). Limits that cannot all hold are refused, never relaxed silently. A client may ask for relaxation, which proceeds in a fixed order with every step recorded.

## 4.5 Risk levels

A client chooses a level $L \in [1, 5]$. A self-check suggests the lower of capacity and willingness to take risk, as Canadian suitability guidance requires (Companion Policy 31-103CP, s.13.2). The level sets a target volatility as a share of the stock market's:

$$\sigma^{*}(L) = 0.2\,L\;\sigma_{\text{eq}}, \qquad \sigma_{\text{eq}} = \sqrt{12}\;\mathrm{sd}\left(\textstyle\sum_{j \in E} \tilde{w}^{0}_{j}\, r_{j,t}\right)$$

with $E$ the equity slots and $\tilde{w}^{0}$ their policy weights normalised to sum to one. The rule $L \times 20\%$ is a product policy, tested by E1's risk delivery. Targets set from a benchmark's volatility have precedent: for its portfolios with 60% or more in bonds, Betterment maximises expected returns "for target volatilities assigned to each risk level", which "are determined by considering the volatility of the equivalent benchmark" (Betterment 2026). Because Canadian funds are rated on a regulator's scale, every mix also reports its NI 81-102 Appendix F rating: the standard deviation of its last 120 monthly returns times $\sqrt{12}$, placed in five bands. With fewer than 120 months the figure is labelled an estimate on that scale, not an Appendix F rating.

## 4.6 Solver

The problem is a strictly convex quadratic program over a capped simplex. The engine solves it with FISTA (Beck and Teboulle 2009) in the diagonally preconditioned variable $v = D(w - \ell)$, $D = \mathrm{diag}(\sqrt{\Sigma_{ii}})$, with step $1/L$ where $L = \lambda \cdot \lambda_{\max}(D^{-1}\Sigma D^{-1})$ is computed exactly, and with adaptive restart (O'Donoghue and Candes 2015). Each step projects onto $\{v : a^{\top}v = 1 - \mathbf{1}^{\top}\ell,\ 0 \le v \le c\}$. The KKT conditions give $v_i = \min(c_i, \max(0, x_i - \tau a_i))$, and the projection finds $\tau$ exactly from the sorted breakpoints (Appendix A). A projected-gradient residual below $10^{-6}$ certifies every answer; otherwise the engine refuses. The same algorithm runs in the browser, and the two agree to rounding on every test case.

## 4.7 Resampling

The weights are averaged over 200 histories drawn by the stationary bootstrap (Politis and Romano 1994; mean block six months, so crises and calm spells cluster as they did). On each history $\hat{\Sigma}$ and $\pi$ are re-estimated and the problem re-solved (Michaud 1989). Averaging spreads weight across funds the single solve treats as interchangeable. Its critics (Scherer 2002; Harvey, Liechty and Liechty 2008) point out that the average of optimal portfolios need not be optimal and can drift off the risk target. The second objection is answered by construction (Section 4.8); the first is tested (E3, with a rule fixed in advance for dropping resampling). The 5th-95th percentile of each fund's resampled weights is shown as the spread of those weights, not as a confidence interval.

## 4.8 Calibrating risk aversion to the target

For a single solve, volatility falls as $\lambda$ rises (Proposition 3), so bisection on $\log\lambda$ finds the $\lambda$ that meets $\sigma^{*}(L)$. The client, however, receives the resampled mix after positions under 2% are dropped. That mix's volatility differs from the single solve's, which is the drift Scherer (2002) describes (in v2, level 5 ended 0.23 points below target), and it is not monotone in $\lambda$: averaging can raise volatility locally, and dropping a fund makes it jump. The engine therefore calibrates on the final pipeline itself, with the same bootstrap draws at every step, so the volatility is a deterministic function $f$ of $\lambda$. It first brackets the target, stepping from the single-solve $\lambda$ in $\log\lambda$ with a doubling step. It then narrows the bracket by Illinois regula falsi (Dowell and Jarratt 1971), replacing a candidate with the midpoint when it falls within 1% of an end or when the bracket has not halved in four steps.

**Guarantee.** Each calibration ends in one of three ways, recorded with the mix: within $5 \times 10^{-5}$ of the target; a bracket narrower than $10^{-5}$ in $\log\lambda$ whose two ends lie on opposite sides of the target, more than the tolerance away (a jump of the minimum-position rule, so no $\lambda$ gives a closer mix); or a bound of $\lambda$ reached with the target still beyond it (out of reach). A fourth outcome, the 30-evaluation limit, would count as a failure. The test suite checks the guarantee on 40 seeded random requests (single solve) and five resampled ones: every one ends within tolerance, at a jump or at a bound, and each claim is re-checked by rebuilding the mix at the $\lambda$ it names (for a jump, both ends of the bracket).

## 4.9 Minimum position

Positions under 2% are dropped and the problem re-solved, round after round, until none is left. A drop that the remaining limits cannot hold is not made and is reported. Weights are never rescaled past a limit. Small positions add little but cost trades (Gurobi Finance's minimum buy-in documentation).

## 4.10 From weights to orders

A rebalancer turns holdings, prices and a cash flow into orders:
1. **Cash flows first.** New money buys the funds furthest below target, and withdrawals sell those furthest above (Vanguard 2010).
2. **Bands.** A fund is traded only when it drifts more than $\min(2\text{ points}, 25\%$ of target$)$, and back to 7/8 of its band rather than to target. This is Vanguard's (2024) "threshold of 200 bps and a destination of 175 bps"; with proportional costs, trading to the edge of the no-trade region is optimal (Donohue and Yip 2003). In-band funds take the other side of those trades through an exact projection that never pushes them past their own band.
3. **Units and cash.** Orders are rounded to whole units, orders under $50 are skipped, and residual cash goes to the fund furthest below target. The cash must cover the orders and their estimated cost (10 bps).
4. **Liquidity.** An order above 1% of a fund's daily traded value is flagged. Under the square-root impact law (Toth et al. 2011) such an order moves the price by about a tenth of a day's volatility, roughly the assumed cost.

## 4.11 Three propositions

**Proposition 1 (delta).** Let $w^{*}(\lambda, \delta)$ solve the problem of Section 4.1 with $\mu = \pi = \delta\Sigma w^{0}$. Then $w^{*}(\lambda, \delta) = w^{*}(\lambda/\delta, 1)$, so the volatility of $w^{*}$ depends on $\lambda$ and $\delta$ only through $\lambda/\delta$. With $\lambda$ calibrated to a volatility target, the weights do not depend on $\delta$.

*Proof.* The objective $\delta\, w^{0\top}\Sigma w - \frac{\lambda}{2} w^{\top}\Sigma w$ equals $\delta$ times $w^{0\top}\Sigma w - \frac{\lambda/\delta}{2} w^{\top}\Sigma w$. Multiplying an objective by a positive constant leaves its maximiser over a fixed feasible set unchanged, and the problem is strictly convex, so the maximiser is unique. If $\lambda_1/\delta_1$ meets the target, so does $\lambda_2 = \lambda_1 \delta_2/\delta_1$ with $\delta_2$, and both give the same weights. $\square$

**Proposition 2 (scale of the covariance).** For $c > 0$, replacing $\Sigma$ by $c\,\Sigma$ (with $\pi = \delta\, c\Sigma w^{0}$) leaves $w^{*}(\lambda)$ unchanged.

*Proof.* The objective becomes $c$ times the original one. $\square$ The annualisation factor 12 and the factor $T/(T-1)$ are such scalings: they change the volatility reported, not the weights at a given $\lambda$. Calibrated to a target, they change only which $\lambda$ meets it.

**Proposition 3 (monotone volatility of the single solve).** For $\lambda_1 < \lambda_2$ with maximisers $w_1, w_2$ and variances $V_k = w_k^{\top}\Sigma w_k$, $V_1 \ge V_2$.

*Proof.* Optimality of each gives $\mu^{\top}w_1 - \frac{\lambda_1}{2}V_1 \ge \mu^{\top}w_2 - \frac{\lambda_1}{2}V_2$ and $\mu^{\top}w_2 - \frac{\lambda_2}{2}V_2 \ge \mu^{\top}w_1 - \frac{\lambda_2}{2}V_1$. Adding them gives $\frac{1}{2}(\lambda_2 - \lambda_1)(V_1 - V_2) \ge 0$. $\square$

The three are checked numerically in the test suite (tests/test_v3_propositions.py). Proposition 1 and 2 hold to $10^{-7}$ in the weights, and Proposition 1 also holds through the full pipeline the client receives, single solve and resampled, at a fixed $\lambda/\delta$ (each resampled draw's equilibrium return is $\delta$ times its own covariance times $w^0$); calibrated at $\delta = 1$ and $\delta = 4$, the two mixes' volatility agrees within twice the calibration tolerance. The bounds on $\lambda$ are absolute, so the invariance holds while $\lambda$ stays inside them. Proposition 3 holds on a 60-point grid of $\lambda$. Proposition 3 does not extend to the resampled average: on the same grid its volatility rises in places by up to 0.005 points. That is why Section 4.8 brackets the target rather than assuming monotonicity.

# 5. Evaluation design

## 5.1 Protocol

The evaluation follows Arnott, Harvey and Markowitz (2019): its design was fixed before any of it was run, and it was run once, with one re-run for a disclosed bug fix (Section 6.9). The plan (RESEARCH_LOG sections 9 and 10) was written, then reviewed in the manner of a registered report's Stage 1 review by outside examiners from model families other than the author's, revised, and reviewed again, eighteen times in all, until a review accepted it as it stood (Section 7). The code that runs it was committed first. The run refuses to start from a working tree with uncommitted changes, and it records the commit, the data snapshot and the package versions with the results. No back-test result changes a default. Two components can change only through rules written in advance and applied by the code: resampling and the point at which QIS takes over. Both rules work on a simulation with a known truth, run first (E3); each runs only on its full sample of 500 replications, and the defaults they lock are the configuration every later part evaluates. After the run, the shipped constants are set to those defaults in both engines in one disclosed commit, and a test fails if they ever differ.

## 5.2 Walk-forward (E1)

For Canada and the US, the shipped engine is re-estimated every December on the data available then, with an expanding window capped at 180 months. The weights are held for 12 months and rebalanced monthly to target, with 10 bps one way charged on all turnover. The funds are today's reference shelf, extended back with their written stand-ins; returns, interest rates and exchange rates stop at each estimation date. The choice of funds and stand-ins is today's knowledge, a look-ahead that E2 removes. A strategy's path stops, and the run records why, if a held fund has no return in a month, if a month is missing, or if a scheduled December has no build.

Robo-Kit is compared with four benchmarks aimed at the same risk:
- a static stock-bond mix (40, 60 or 80% stocks, aimed at the target by its stock share, since each level targets that share of the stock market's volatility; it is not calibrated, and bonds add volatility of their own, so its ex-ante gap to the target is reported with every strategy's);
- the textbook optimizer (sample means, 60-month window, no resampling);
- equal risk contribution mixed with cash to the target;
- minimum variance mixed with cash to the target.

Equal weights and seven one-component ablations are reported descriptively.

One Sharpe ratio is used throughout: the mean monthly excess return over its standard deviation (divisor $T$), times $\sqrt{12}$, the moment form the Ledoit and Wolf (2008) test uses, so a reported difference is exactly the tested one. Differences are tested with their studentised circular block bootstrap (block 6), with Holm's adjustment over the twelve comparisons of each market; a comparison that cannot be made enters with $p = 1$. Each comparison is read by a rule written in advance and applied by the code: "benchmark better" or "robokit better" when the Holm-adjusted two-sided $p$ is below 0.05; otherwise "robokit not worse by more than 0.10" from a non-inferiority test; otherwise "too short to tell" when robokit is ahead but the sample is shorter than the minimum track record (Bailey and Lopez de Prado 2012); otherwise "inconclusive". The claims are nested and read from one interval, a closed test procedure, so no further multiplicity correction is needed (EMEA 2000, CPMP/EWP/482/99, section V.1). The US comparisons are labelled exploratory on every row.

Risk delivery is the standard deviation of monthly returns divided by the monthly target in force. Simultaneous 90% intervals over levels 2-4 must lie inside [0.80, 1.25] for the levels to count as delivering their risk; a point estimate outside the band counts as a miss. The run measures how often such intervals cover the truth, and how often a mix that does deliver is read as delivered. Levels 1 and 5 are reported with their own interval only.

A power statement was written before the run. In Canada, a Sharpe difference has to be about 0.22 to be detected half the time and about 0.31 to be detected 80% of the time; in the US, about 0.31 and 0.45. Most comparisons were therefore expected to be inconclusive.

## 5.3 Strict point-in-time returns (E2)

Every series is cut at the estimation date before anything is computed. Each slot holds the best-scoring fund that already had 36 months of its own returns, with no stand-ins; a date whose funds share fewer than 36 months is skipped, and only such dates, before the first one that builds. A test shows the strict mode cannot see the future: replacing every later return, rate and exchange rate with noise leaves the mix unchanged.

## 5.4 Simulation with a known truth (E3)

The shipped pipeline runs on simulated histories through its own data loader, 500 per world, with common random numbers: one 192-month path per replication, seen by every method, of which a shorter study takes the first months. The truth comes only from months up to and including the walk-forward's first estimation date; the run stops unless the truth windows are the registered ones. There are three worlds:
- **a:** equilibrium means, so the model is right;
- **b:** FP Canada planning returns after fees, so the model is wrong;
- **c:** world (b) with two volatility regimes, the case block resampling is meant for.

Methods are scored by certainty-equivalent loss against the true constrained optimum at the level's own risk aversion. Resampling is dropped only if the one-sided 95% lower bound of its cost exceeds 2 basis points in both worlds b and c. Two sub-studies test the 36-month minimum history and the QIS switch point; the switch moves only if the evidence in both of two truths points one way and nothing points the other.

## 5.5 The rest

- **E4:** covariance estimators, in a walk-forward horse race and a fixed-weight forecast check, with every loss centred on a mean predicted from the past only.
- **E5:** sensitivity to every constant that has no source, including the Politis and White (2004) block length, and the Monte Carlo precision of the projections, measured on the product's own projection inputs.
- **E6:** the shipped rebalancer on simulated accounts at real prices, against monthly and annual rebalancing and other band destinations.
- **E7:** audits of the data rules.
- **E8:** hold-out tests of the stand-in and back-filled histories.

# 6. Results

All numbers in this section come from output/v3/results.json, written by the second registered run, from commit {{provenance.commit|raw}}, with {{provenance.replications|int}} simulated histories per world. It is the second because the first stopped three descriptive paths in E2 on a bug, which was fixed and disclosed (Section 6.9); every other number of the first run is reproduced exactly.

## 6.1 Simulation with a known truth (E3)

Table: Certainty-equivalent loss against the true constrained optimum, level 3, 180 months, basis points a year (mean over {{provenance.replications|int}} histories; standard error in brackets)

| Method | World a (model right) | World b (model wrong) | World c (regimes) |
|---|---|---|---|
| Robo-Kit | {{E3.summary.a.3.180.robokit.loss_bp|f1}} ({{E3.summary.a.3.180.robokit.loss_bp_se|f2}}) | {{E3.summary.b.3.180.robokit.loss_bp|f1}} ({{E3.summary.b.3.180.robokit.loss_bp_se|f2}}) | {{E3.summary.c.3.180.robokit.loss_bp|f1}} ({{E3.summary.c.3.180.robokit.loss_bp_se|f2}}) |
| No resampling | {{E3.summary.a.3.180.no_resample.loss_bp|f1}} | {{E3.summary.b.3.180.no_resample.loss_bp|f1}} | {{E3.summary.c.3.180.no_resample.loss_bp|f1}} |
| Static stock-bond mix | {{E3.summary.a.3.180.static_mix.loss_bp|f1}} | {{E3.summary.b.3.180.static_mix.loss_bp|f1}} | {{E3.summary.c.3.180.static_mix.loss_bp|f1}} |
| Equal weights | {{E3.summary.a.3.180.equal_weight.loss_bp|f1}} | {{E3.summary.b.3.180.equal_weight.loss_bp|f1}} | {{E3.summary.c.3.180.equal_weight.loss_bp|f1}} |
| Sample means | {{E3.summary.a.3.180.sample_mu.loss_bp|f1}} | {{E3.summary.b.3.180.sample_mu.loss_bp|f1}} | {{E3.summary.c.3.180.sample_mu.loss_bp|f1}} |
| Textbook (60 months) | {{E3.summary.a.3.180.textbook_60.loss_bp|f1}} | {{E3.summary.b.3.180.textbook_60.loss_bp|f1}} | {{E3.summary.c.3.180.textbook_60.loss_bp|f1}} |
| Risk parity + cash | {{E3.summary.a.3.180.erc_cash.loss_bp|f1}} | {{E3.summary.b.3.180.erc_cash.loss_bp|f1}} | {{E3.summary.c.3.180.erc_cash.loss_bp|f1}} |
| Minimum variance + cash | {{E3.summary.a.3.180.minvar_cash.loss_bp|f1}} | {{E3.summary.b.3.180.minvar_cash.loss_bp|f1}} | {{E3.summary.c.3.180.minvar_cash.loss_bp|f1}} |

When the model is right (world a), Robo-Kit is within {{E3.summary.a.3.180.robokit.loss_bp|f1}} basis points a year of the best the truth allows. When it is wrong in the realistic way of world b, where expected returns follow published planning assumptions rather than equilibrium, Robo-Kit and the other methods built on the equilibrium prior lose about {{E3.summary.b.3.180.robokit.loss_bp|f0}} basis points, and the static stock-bond mix loses {{derived.e3.b.static_mix_advantage|f1}} basis points a year less than Robo-Kit (paired standard error {{E3.paired_contrasts.b.static_mix.loss_bp.se|f2}}). The loss in world b is the cost of the equilibrium prior being wrong, not of estimation: Robo-Kit's weights sit {{E3.summary.b.3.180.robokit.distance|f2}} from the true optimum (half the sum of absolute weight differences, the turnover convention), against {{E3.summary.a.3.180.robokit.distance|f2}} in world a. Methods that estimate means from the data lose more: sample means by {{derived.e3.b.sample_mu|f1}} basis points, and the textbook optimizer by {{derived.e3.b.textbook_60|f1}}.

**Resampling.** The registered rule drops resampling only if its cost has a one-sided 95% lower bound above 2 basis points in both worlds b and c. The mean cost was {{E3.resampling_rule.b.mean|f3}} basis points in world b (lower bound {{E3.resampling_rule.b.lo95_one_sided|f3}}) and {{E3.resampling_rule.c.mean|f3}} in world c (lower bound {{E3.resampling_rule.c.lo95_one_sided|f3}}), so resampling stays. It also gains nothing: with equilibrium returns $\pi = \delta\hat{\Sigma}w^0$, each bootstrap draw's optimum is close to the prior scaled by $\delta/\lambda$ whatever the draw's covariance, so averaging over draws changes the weights very little. The regime world c, where block resampling should help most, shows the same. Resampling is kept because the rule did not remove it; this study gives no evidence that it helps.

**The resampling band** (the 5th to 95th percentile of each fund's resampled weights) contained the true optimal weight for {{E3.summary.a.3.180.robokit.band_coverage|pct0}} of the funds in world a and {{E3.summary.b.3.180.robokit.band_coverage|pct0}} in world b. It is a measure of the spread of the resampled weights and is shown that way; it is not a confidence interval for the right weight.

**Risk accuracy.** Robo-Kit's true volatility differed from its target by {{E3.summary.b.3.180.robokit.abs_vol_error|pp2}} points on average in world b. All but {{E3.summary.b.3.180.robokit.calibration_outcomes.jump|int}} of the {{provenance.replications|int}} calibrations in that world ended within tolerance.

**The 36-month minimum (sub-study i).** In world b at level 3, Robo-Kit's loss was {{E3.summary.b.3.36.robokit.loss_bp|f1}} basis points with 36 months of data, {{E3.summary.b.3.60.robokit.loss_bp|f1}} with 60, {{E3.summary.b.3.120.robokit.loss_bp|f1}} with 120 and {{E3.summary.b.3.180.robokit.loss_bp|f1}} with 180, on the same simulated paths. A short history costs little here because the expected returns do not come from the history; the minimum is a data-quality rule, and this study does not argue for a different value.

**The QIS switch (sub-study ii).** At $N/T = 0.25$, the true variance of the minimum-variance portfolio from QIS differed from that of constant-correlation shrinkage by {{E3.qis_switch.by_ratio.constant_correlation.0.25.mean_rel|+pct2}} under the structured truth and {{E3.qis_switch.by_ratio.sample.0.25.mean_rel|+pct2}} under the unstructured one, far inside the registered 1% margin either way; none of the three tests came close, and the switch stays at 0.25. The two estimators part only at higher ratios: at $N/T = 0.6$ QIS gave {{E3.qis_switch.by_ratio.constant_correlation.0.6.mean_rel|pct1}} and {{E3.qis_switch.by_ratio.sample.0.6.mean_rel|pct1}} more true variance. The engine's lists rarely reach those ratios.

![Certainty-equivalent loss by world, level 3, 180 months, with 95% intervals for the mean.](img/e3_losses.png)

![QIS against constant-correlation shrinkage: true variance of the minimum-variance portfolio, by N/T, with 95% intervals. The dashed line is the switch point.](img/qis_switch.png)

## 6.2 Walk-forward, Canada (E1, confirmatory)

The Canadian walk-forward has {{E1.CA.strategies.robokit.3.months|int}} out-of-sample months, from {{E1.CA.strategies.robokit.3.from|raw}} to {{E1.CA.strategies.robokit.3.to|raw}}, with {{E1.CA.dates.0|raw}} as the first estimation date.

Table: Robo-Kit in Canada, after costs (CVaR: the mean of the worst 5% of monthly returns; the number of those months in brackets)

| Level | Annual return | Volatility | Sharpe ratio | Maximum drawdown | 2022 return | Monthly CVaR 95% (tail months) |
|---|---|---|---|---|---|---|
| 2 | {{E1.CA.strategies.robokit.2.ann_return|pct1}} | {{E1.CA.strategies.robokit.2.ann_vol|pct1}} | {{E1.CA.strategies.robokit.2.sharpe|f2}} | {{E1.CA.strategies.robokit.2.max_drawdown|pct1}} | {{E1.CA.strategies.robokit.2.2022.return|pct1}} | {{E1.CA.strategies.robokit.2.cvar95_monthly|pct1}} ({{E1.CA.strategies.robokit.2.cvar95_tail_months|int}}) |
| 3 | {{E1.CA.strategies.robokit.3.ann_return|pct1}} | {{E1.CA.strategies.robokit.3.ann_vol|pct1}} | {{E1.CA.strategies.robokit.3.sharpe|f2}} | {{E1.CA.strategies.robokit.3.max_drawdown|pct1}} | {{E1.CA.strategies.robokit.3.2022.return|pct1}} | {{E1.CA.strategies.robokit.3.cvar95_monthly|pct1}} ({{E1.CA.strategies.robokit.3.cvar95_tail_months|int}}) |
| 4 | {{E1.CA.strategies.robokit.4.ann_return|pct1}} | {{E1.CA.strategies.robokit.4.ann_vol|pct1}} | {{E1.CA.strategies.robokit.4.sharpe|f2}} | {{E1.CA.strategies.robokit.4.max_drawdown|pct1}} | {{E1.CA.strategies.robokit.4.2022.return|pct1}} | {{E1.CA.strategies.robokit.4.cvar95_monthly|pct1}} ({{E1.CA.strategies.robokit.4.cvar95_tail_months|int}}) |

**Risk delivery.** The realised volatility over the target in force was {{E1.CA.risk_delivery.primary.2.ratio|f2}}, {{E1.CA.risk_delivery.primary.3.ratio|f2}} and {{E1.CA.risk_delivery.primary.4.ratio|f2}} at levels 2, 3 and 4. The simultaneous 90% intervals were [{{E1.CA.risk_delivery.primary.2.lo|f2}}, {{E1.CA.risk_delivery.primary.2.hi|f2}}], [{{E1.CA.risk_delivery.primary.3.lo|f2}}, {{E1.CA.risk_delivery.primary.3.hi|f2}}] and [{{E1.CA.risk_delivery.primary.4.lo|f2}}, {{E1.CA.risk_delivery.primary.4.hi|f2}}]. Every point estimate is inside the band [0.80, 1.25], but two intervals reach just past its upper edge, so the registered reading is "{{E1.CA.risk_delivery.primary.reading|raw}}". The run's own check shows how demanding the rule is: when a mix delivers its target exactly, three such intervals on 120 months (the check's length; Canada's sample is longer, which narrows them) all fall inside the band only {{risk_delivery_coverage.delivered_when_the_true_ratio_is_1|pct0}} of the time (and cover the true ratio together {{risk_delivery_coverage.simultaneous_0.90_three_levels|pct0}} of the time, against a nominal 90%). Levels 1 and 5, reported on their own, had ratios of {{E1.CA.risk_delivery.level_1.1.ratio|f2}} and {{E1.CA.risk_delivery.level_5.5.ratio|f2}}. On the regulator's scale the realised paths rate {{E1.CA.regulator_rating.2.rating|raw}} at level 2, {{E1.CA.regulator_rating.3.rating|raw}} at level 3 and {{E1.CA.regulator_rating.4.rating|raw}} at level 4.

Table: Confirmatory comparisons, Canada: Robo-Kit minus benchmark, annual Sharpe ratio (Holm-adjusted over the twelve)

| Benchmark | Level | Difference | 95% interval | Holm p | Reading |
|---|---|---|---|---|---|
| Static mix | 2 | {{E1.CA.comparisons.static_mix.2.sharpe_diff_annual|+f2}} | [{{E1.CA.comparisons.static_mix.2.ci95_annual.0|f2}}, {{E1.CA.comparisons.static_mix.2.ci95_annual.1|f2}}] | {{E1.CA.comparisons.static_mix.2.p_holm|f2}} | {{E1.CA.comparisons.static_mix.2.reading|raw}} |
| Static mix | 3 | {{E1.CA.comparisons.static_mix.3.sharpe_diff_annual|+f2}} | [{{E1.CA.comparisons.static_mix.3.ci95_annual.0|f2}}, {{E1.CA.comparisons.static_mix.3.ci95_annual.1|f2}}] | {{E1.CA.comparisons.static_mix.3.p_holm|f2}} | {{E1.CA.comparisons.static_mix.3.reading|raw}} |
| Static mix | 4 | {{E1.CA.comparisons.static_mix.4.sharpe_diff_annual|+f2}} | [{{E1.CA.comparisons.static_mix.4.ci95_annual.0|f2}}, {{E1.CA.comparisons.static_mix.4.ci95_annual.1|f2}}] | {{E1.CA.comparisons.static_mix.4.p_holm|f2}} | {{E1.CA.comparisons.static_mix.4.reading|raw}} |
| Textbook | 2 | {{E1.CA.comparisons.textbook_60.2.sharpe_diff_annual|+f2}} | [{{E1.CA.comparisons.textbook_60.2.ci95_annual.0|f2}}, {{E1.CA.comparisons.textbook_60.2.ci95_annual.1|f2}}] | {{E1.CA.comparisons.textbook_60.2.p_holm|f2}} | {{E1.CA.comparisons.textbook_60.2.reading|raw}} |
| Textbook | 3 | {{E1.CA.comparisons.textbook_60.3.sharpe_diff_annual|+f2}} | [{{E1.CA.comparisons.textbook_60.3.ci95_annual.0|f2}}, {{E1.CA.comparisons.textbook_60.3.ci95_annual.1|f2}}] | {{E1.CA.comparisons.textbook_60.3.p_holm|f2}} | {{E1.CA.comparisons.textbook_60.3.reading|raw}} |
| Textbook | 4 | {{E1.CA.comparisons.textbook_60.4.sharpe_diff_annual|+f2}} | [{{E1.CA.comparisons.textbook_60.4.ci95_annual.0|f2}}, {{E1.CA.comparisons.textbook_60.4.ci95_annual.1|f2}}] | {{E1.CA.comparisons.textbook_60.4.p_holm|f2}} | {{E1.CA.comparisons.textbook_60.4.reading|raw}} |
| Risk parity + cash | 2 | {{E1.CA.comparisons.erc_cash.2.sharpe_diff_annual|+f2}} | [{{E1.CA.comparisons.erc_cash.2.ci95_annual.0|f2}}, {{E1.CA.comparisons.erc_cash.2.ci95_annual.1|f2}}] | {{E1.CA.comparisons.erc_cash.2.p_holm|f2}} | {{E1.CA.comparisons.erc_cash.2.reading|raw}} |
| Risk parity + cash | 3 | {{E1.CA.comparisons.erc_cash.3.sharpe_diff_annual|+f2}} | [{{E1.CA.comparisons.erc_cash.3.ci95_annual.0|f2}}, {{E1.CA.comparisons.erc_cash.3.ci95_annual.1|f2}}] | {{E1.CA.comparisons.erc_cash.3.p_holm|f2}} | {{E1.CA.comparisons.erc_cash.3.reading|raw}} |
| Risk parity + cash | 4 | {{E1.CA.comparisons.erc_cash.4.sharpe_diff_annual|+f2}} | [{{E1.CA.comparisons.erc_cash.4.ci95_annual.0|f2}}, {{E1.CA.comparisons.erc_cash.4.ci95_annual.1|f2}}] | {{E1.CA.comparisons.erc_cash.4.p_holm|f2}} | {{E1.CA.comparisons.erc_cash.4.reading|raw}} |
| Min variance + cash | 2 | {{E1.CA.comparisons.minvar_cash.2.sharpe_diff_annual|+f2}} | [{{E1.CA.comparisons.minvar_cash.2.ci95_annual.0|f2}}, {{E1.CA.comparisons.minvar_cash.2.ci95_annual.1|f2}}] | {{E1.CA.comparisons.minvar_cash.2.p_holm|f2}} | {{E1.CA.comparisons.minvar_cash.2.reading|raw}} |
| Min variance + cash | 3 | {{E1.CA.comparisons.minvar_cash.3.sharpe_diff_annual|+f2}} | [{{E1.CA.comparisons.minvar_cash.3.ci95_annual.0|f2}}, {{E1.CA.comparisons.minvar_cash.3.ci95_annual.1|f2}}] | {{E1.CA.comparisons.minvar_cash.3.p_holm|f2}} | {{E1.CA.comparisons.minvar_cash.3.reading|raw}} |
| Min variance + cash | 4 | {{E1.CA.comparisons.minvar_cash.4.sharpe_diff_annual|+f2}} | [{{E1.CA.comparisons.minvar_cash.4.ci95_annual.0|f2}}, {{E1.CA.comparisons.minvar_cash.4.ci95_annual.1|f2}}] | {{E1.CA.comparisons.minvar_cash.4.p_holm|f2}} | {{E1.CA.comparisons.minvar_cash.4.reading|raw}} |

No comparison found a difference at the 5% level after Holm's adjustment, as the power statement written before the run expected. Against the static mix, the data show Robo-Kit is not worse by more than 0.10 at levels 3 and 4 (Holm-adjusted non-inferiority p = {{E1.CA.comparisons.static_mix.3.p_noninferior_holm|f3}} and {{E1.CA.comparisons.static_mix.4.p_noninferior_holm|f3}}). Against the textbook optimizer and risk parity, Robo-Kit is ahead at every level but the sample is far shorter than the minimum track record that would settle it ({{E1.CA.comparisons.textbook_60.3.min_track_record_months|int}} months at level 3 against the textbook). Against minimum variance it is ahead by about {{E1.CA.comparisons.minvar_cash.3.sharpe_diff_annual|f1}} a year, which does not survive the adjustment.

**How closely each strategy aims at the target.** Robo-Kit is calibrated on the mix it delivers and its model volatility is within a hundredth of a point of the target at every date. The static mix is aimed by its stock share; the volatility its bonds add puts it {{E1.CA.ex_ante_gap.static_mix.2.mean|pp2}}, {{E1.CA.ex_ante_gap.static_mix.3.mean|pp2}} and {{E1.CA.ex_ante_gap.static_mix.4.mean|pp2}} points from the target on average at levels 2 to 4 in Canada (largest {{E1.CA.ex_ante_gap.static_mix.2.max|pp2}}), close but not matched. The textbook optimizer's single solve misses by up to {{E1.CA.ex_ante_gap.textbook_60.4.max|pp2}} points at level 4.

Table: Ex-ante gap between each strategy's model volatility and the target in force: mean (maximum) over the estimation dates, percentage points a year

| Strategy | CA 2 | CA 3 | CA 4 | US 2 | US 3 | US 4 |
|---|---|---|---|---|---|---|
| Robo-Kit | {{E1.CA.ex_ante_gap.robokit.2.mean|pp2}} ({{E1.CA.ex_ante_gap.robokit.2.max|pp2}}) | {{E1.CA.ex_ante_gap.robokit.3.mean|pp2}} ({{E1.CA.ex_ante_gap.robokit.3.max|pp2}}) | {{E1.CA.ex_ante_gap.robokit.4.mean|pp2}} ({{E1.CA.ex_ante_gap.robokit.4.max|pp2}}) | {{E1.US.ex_ante_gap.robokit.2.mean|pp2}} ({{E1.US.ex_ante_gap.robokit.2.max|pp2}}) | {{E1.US.ex_ante_gap.robokit.3.mean|pp2}} ({{E1.US.ex_ante_gap.robokit.3.max|pp2}}) | {{E1.US.ex_ante_gap.robokit.4.mean|pp2}} ({{E1.US.ex_ante_gap.robokit.4.max|pp2}}) |
| Static mix | {{E1.CA.ex_ante_gap.static_mix.2.mean|pp2}} ({{E1.CA.ex_ante_gap.static_mix.2.max|pp2}}) | {{E1.CA.ex_ante_gap.static_mix.3.mean|pp2}} ({{E1.CA.ex_ante_gap.static_mix.3.max|pp2}}) | {{E1.CA.ex_ante_gap.static_mix.4.mean|pp2}} ({{E1.CA.ex_ante_gap.static_mix.4.max|pp2}}) | {{E1.US.ex_ante_gap.static_mix.2.mean|pp2}} ({{E1.US.ex_ante_gap.static_mix.2.max|pp2}}) | {{E1.US.ex_ante_gap.static_mix.3.mean|pp2}} ({{E1.US.ex_ante_gap.static_mix.3.max|pp2}}) | {{E1.US.ex_ante_gap.static_mix.4.mean|pp2}} ({{E1.US.ex_ante_gap.static_mix.4.max|pp2}}) |
| Textbook | {{E1.CA.ex_ante_gap.textbook_60.2.mean|pp2}} ({{E1.CA.ex_ante_gap.textbook_60.2.max|pp2}}) | {{E1.CA.ex_ante_gap.textbook_60.3.mean|pp2}} ({{E1.CA.ex_ante_gap.textbook_60.3.max|pp2}}) | {{E1.CA.ex_ante_gap.textbook_60.4.mean|pp2}} ({{E1.CA.ex_ante_gap.textbook_60.4.max|pp2}}) | {{E1.US.ex_ante_gap.textbook_60.2.mean|pp2}} ({{E1.US.ex_ante_gap.textbook_60.2.max|pp2}}) | {{E1.US.ex_ante_gap.textbook_60.3.mean|pp2}} ({{E1.US.ex_ante_gap.textbook_60.3.max|pp2}}) | {{E1.US.ex_ante_gap.textbook_60.4.mean|pp2}} ({{E1.US.ex_ante_gap.textbook_60.4.max|pp2}}) |
| Risk parity + cash | {{E1.CA.ex_ante_gap.erc_cash.2.mean|pp2}} ({{E1.CA.ex_ante_gap.erc_cash.2.max|pp2}}) | {{E1.CA.ex_ante_gap.erc_cash.3.mean|pp2}} ({{E1.CA.ex_ante_gap.erc_cash.3.max|pp2}}) | {{E1.CA.ex_ante_gap.erc_cash.4.mean|pp2}} ({{E1.CA.ex_ante_gap.erc_cash.4.max|pp2}}) | {{E1.US.ex_ante_gap.erc_cash.2.mean|pp2}} ({{E1.US.ex_ante_gap.erc_cash.2.max|pp2}}) | {{E1.US.ex_ante_gap.erc_cash.3.mean|pp2}} ({{E1.US.ex_ante_gap.erc_cash.3.max|pp2}}) | {{E1.US.ex_ante_gap.erc_cash.4.mean|pp2}} ({{E1.US.ex_ante_gap.erc_cash.4.max|pp2}}) |
| Min variance + cash | {{E1.CA.ex_ante_gap.minvar_cash.2.mean|pp2}} ({{E1.CA.ex_ante_gap.minvar_cash.2.max|pp2}}) | {{E1.CA.ex_ante_gap.minvar_cash.3.mean|pp2}} ({{E1.CA.ex_ante_gap.minvar_cash.3.max|pp2}}) | {{E1.CA.ex_ante_gap.minvar_cash.4.mean|pp2}} ({{E1.CA.ex_ante_gap.minvar_cash.4.max|pp2}}) | {{E1.US.ex_ante_gap.minvar_cash.2.mean|pp2}} ({{E1.US.ex_ante_gap.minvar_cash.2.max|pp2}}) | {{E1.US.ex_ante_gap.minvar_cash.3.mean|pp2}} ({{E1.US.ex_ante_gap.minvar_cash.3.max|pp2}}) | {{E1.US.ex_ante_gap.minvar_cash.4.mean|pp2}} ({{E1.US.ex_ante_gap.minvar_cash.4.max|pp2}}) |

Two benchmarks are not risk-matched in practice. Unleveraged risk parity and minimum variance are already less volatile than the level-2 target ({{E1.CA.strategies.erc_cash.2.ann_vol|pct1}} and {{E1.CA.strategies.minvar_cash.2.ann_vol|pct1}} a year), so they could almost never be mixed up to it and were the same portfolio at every level: {{E1.CA.unreachable_benchmarks|int}} of their {{derived.e1.CA.cash_mixed_builds|int}} builds were counted as unreachable. Their Sharpe ratios are still comparable; their risk is not.

**Calibration.** Of the walk-forward builds, {{E1.CA.calibration_outcomes.within tolerance|int}} in Canada ended within tolerance and {{E1.CA.calibration_outcomes.out of reach|int}} out of reach; none reached the evaluation limit. Rebuilding the dated mixes shows that the out-of-reach case is at level 5, where the fund limits hold the riskiest allowed mix a fraction of a point below the stock market's volatility.

**What the v3 components change.** The ablations with resampling off, and with the risk aversion from the single solve (v2's calibration), had Sharpe ratios of {{E1.CA.strategies.no_resample.3.sharpe|f3}} and {{E1.CA.strategies.single_lambda.3.sharpe|f3}} against Robo-Kit's {{E1.CA.strategies.robokit.3.sharpe|f3}} at level 3. Calibrating on the final mix cut the mean gap between the ex-ante volatility and its target from {{E1.CA.calibration_ablation.ex_ante_gap.single_lambda.mean_abs_gap|pp3}} to {{E1.CA.calibration_ablation.ex_ante_gap.robokit.mean_abs_gap|pp3}} points, which is what it was designed to do, but the realised risk ratios hardly moved. The deflated Sharpe ratio (with {{E1.CA.dsr_trials.n_trials|int}} trials counted) is {{E1.CA.dsr.3.robokit.dsr|f2}} for Robo-Kit at level 3; it says the Sharpe ratio is very likely positive after allowing for every configuration tried, not that Robo-Kit beats its benchmarks.

Table: Descriptive ablations at level 3, each changing one component of the shipped engine (no readings; the US exploratory)

| Strategy | CA Sharpe | CA volatility | US Sharpe | US volatility |
|---|---|---|---|---|
| Robo-Kit | {{E1.CA.strategies.robokit.3.sharpe|f2}} | {{E1.CA.strategies.robokit.3.ann_vol|pct1}} | {{E1.US.strategies.robokit.3.sharpe|f2}} | {{E1.US.strategies.robokit.3.ann_vol|pct1}} |
| Resampling off | {{E1.CA.strategies.no_resample.3.sharpe|f2}} | {{E1.CA.strategies.no_resample.3.ann_vol|pct1}} | {{E1.US.strategies.no_resample.3.sharpe|f2}} | {{E1.US.strategies.no_resample.3.ann_vol|pct1}} |
| Single-solve calibration (v2) | {{E1.CA.strategies.single_lambda.3.sharpe|f2}} | {{E1.CA.strategies.single_lambda.3.ann_vol|pct1}} | {{E1.US.strategies.single_lambda.3.sharpe|f2}} | {{E1.US.strategies.single_lambda.3.ann_vol|pct1}} |
| Sample covariance | {{E1.CA.strategies.sample_cov.3.sharpe|f2}} | {{E1.CA.strategies.sample_cov.3.ann_vol|pct1}} | {{E1.US.strategies.sample_cov.3.sharpe|f2}} | {{E1.US.strategies.sample_cov.3.ann_vol|pct1}} |
| Slot and cash caps removed (50% per fund kept) | {{E1.CA.strategies.no_caps.3.sharpe|f2}} | {{E1.CA.strategies.no_caps.3.ann_vol|pct1}} | {{E1.US.strategies.no_caps.3.sharpe|f2}} | {{E1.US.strategies.no_caps.3.ann_vol|pct1}} |
| Cash caps removed | {{E1.CA.strategies.no_cash_caps.3.sharpe|f2}} | {{E1.CA.strategies.no_cash_caps.3.ann_vol|pct1}} | {{E1.US.strategies.no_cash_caps.3.sharpe|f2}} | {{E1.US.strategies.no_cash_caps.3.ann_vol|pct1}} |
| Sample means | {{E1.CA.strategies.sample_mu.3.sharpe|f2}} | {{E1.CA.strategies.sample_mu.3.ann_vol|pct1}} | {{E1.US.strategies.sample_mu.3.sharpe|f2}} | {{E1.US.strategies.sample_mu.3.ann_vol|pct1}} |
| Bayes-Stein means (Jorion 1986) | {{E1.CA.strategies.james_stein_mu.3.sharpe|f2}} | {{E1.CA.strategies.james_stein_mu.3.ann_vol|pct1}} | {{E1.US.strategies.james_stein_mu.3.sharpe|f2}} | {{E1.US.strategies.james_stein_mu.3.ann_vol|pct1}} |
| Equal weights (not risk-matched) | {{E1.CA.strategies.equal_weight.3.sharpe|f2}} | {{E1.CA.strategies.equal_weight.3.ann_vol|pct1}} | {{E1.US.strategies.equal_weight.3.sharpe|f2}} | {{E1.US.strategies.equal_weight.3.ann_vol|pct1}} |

![Realised over target volatility by level, with simultaneous 90% intervals for levels 2-4 (each level's own 90% interval for levels 1 and 5). The shaded band is the registered range for "delivered".](img/risk_delivery.png)

![Robo-Kit minus each benchmark, annual Sharpe ratio, with studentised 95% intervals. The dotted line is the non-inferiority margin.](img/sharpe_differences.png)

![Growth of one dollar after costs, Canada, level 3.](img/growth_CA_L3.png)

## 6.3 Walk-forward, United States (E1, exploratory)

The US sample has {{E1.US.strategies.robokit.3.months|int}} out-of-sample months, from {{E1.US.strategies.robokit.3.from|raw}} to {{E1.US.strategies.robokit.3.to|raw}}; the power statement called its comparisons exploratory before the run.

Table: Robo-Kit in the US, after costs (exploratory; CVaR as in the Canadian table)

| Level | Annual return | Volatility | Sharpe ratio | Maximum drawdown | 2022 return | Monthly CVaR 95% (tail months) |
|---|---|---|---|---|---|---|
| 2 | {{E1.US.strategies.robokit.2.ann_return|pct1}} | {{E1.US.strategies.robokit.2.ann_vol|pct1}} | {{E1.US.strategies.robokit.2.sharpe|f2}} | {{E1.US.strategies.robokit.2.max_drawdown|pct1}} | {{E1.US.strategies.robokit.2.2022.return|pct1}} | {{E1.US.strategies.robokit.2.cvar95_monthly|pct1}} ({{E1.US.strategies.robokit.2.cvar95_tail_months|int}}) |
| 3 | {{E1.US.strategies.robokit.3.ann_return|pct1}} | {{E1.US.strategies.robokit.3.ann_vol|pct1}} | {{E1.US.strategies.robokit.3.sharpe|f2}} | {{E1.US.strategies.robokit.3.max_drawdown|pct1}} | {{E1.US.strategies.robokit.3.2022.return|pct1}} | {{E1.US.strategies.robokit.3.cvar95_monthly|pct1}} ({{E1.US.strategies.robokit.3.cvar95_tail_months|int}}) |
| 4 | {{E1.US.strategies.robokit.4.ann_return|pct1}} | {{E1.US.strategies.robokit.4.ann_vol|pct1}} | {{E1.US.strategies.robokit.4.sharpe|f2}} | {{E1.US.strategies.robokit.4.max_drawdown|pct1}} | {{E1.US.strategies.robokit.4.2022.return|pct1}} | {{E1.US.strategies.robokit.4.cvar95_monthly|pct1}} ({{E1.US.strategies.robokit.4.cvar95_tail_months|int}}) |

**Risk was not delivered.** The realised volatility over target was {{E1.US.risk_delivery.primary.2.ratio|f2}}, {{E1.US.risk_delivery.primary.3.ratio|f2}} and {{E1.US.risk_delivery.primary.4.ratio|f2}} at levels 2, 3 and 4, outside the band at every level: the registered reading is "{{E1.US.risk_delivery.primary.reading|raw}}". The US mixes swung about a third more than their targets over 2019-2026, a period that holds the 2020 crash and the 2022 fall in stocks and bonds together; the strict point-in-time run (E2) shows the same at levels 2 and 3. This is the clearest negative result of the evaluation. Its cause was not tested. A plausible one is that most of each estimation window predates 2020, when stocks and bonds moved against each other more than they did afterwards, so the model's covariance understated how much a balanced mix could swing.

**Calibration.** {{E1.US.calibration_outcomes.within tolerance|int}} US builds ended within tolerance and {{E1.US.calibration_outcomes.out of reach|int}} out of reach, none at the evaluation limit; rebuilding them shows the out-of-reach ones are level 5 at every date, held a fraction of a point below target by the fund limits. They do not explain the risk miss, which is at levels 2 to 4.

**Sharpe ratios.** No comparison was significant after adjustment. Robo-Kit is not worse than the static mix by more than 0.10 at levels 3 and 4 (Holm-adjusted non-inferiority p = {{E1.US.comparisons.static_mix.3.p_noninferior_holm|f3}} and {{E1.US.comparisons.static_mix.4.p_noninferior_holm|f3}}; exploratory) and trails the textbook optimizer at every level (a difference of {{E1.US.comparisons.textbook_60.3.sharpe_diff_annual|f2}} at level 3, interval [{{E1.US.comparisons.textbook_60.3.ci95_annual.0|f2}}, {{E1.US.comparisons.textbook_60.3.ci95_annual.1|f2}}], Holm p = {{E1.US.comparisons.textbook_60.3.p_holm|f2}}), which held more US stocks when they led; a 92-month sample cannot separate that from luck. The deflated Sharpe ratio at level 3 is {{E1.US.dsr.3.robokit.dsr|f2}}.

## 6.4 Strict point-in-time returns (E2)

With every series cut at the estimation date and only funds that already had 36 months of their own returns, the Canadian ratios of realised to target volatility were {{E2.CA.risk_delivery.2.ratio|f3}}, {{E2.CA.risk_delivery.3.ratio|f3}} and {{E2.CA.risk_delivery.4.ratio|f3}} (reading: "{{E2.CA.risk_delivery.reading|raw}}"), and the US ratios {{E2.US.risk_delivery.2.ratio|f3}}, {{E2.US.risk_delivery.3.ratio|f3}} and {{E2.US.risk_delivery.4.ratio|f3}} ("{{E2.US.risk_delivery.reading|raw}}": the first two lie just outside 1.25). The look-ahead in E1's fund choice and stand-ins therefore did not drive E1's risk results: removing it leaves Canada near its targets and the US above them.

E2's Sharpe-ratio comparisons are descriptive: the plan gives them no reading and no multiplicity adjustment. In Canada ({{E2.CA.comparisons.static_mix.3.months|int}} months), robokit minus the static mix was {{E2.CA.comparisons.static_mix.2.sharpe_diff_annual|+f2}}, {{E2.CA.comparisons.static_mix.3.sharpe_diff_annual|+f2}} and {{E2.CA.comparisons.static_mix.4.sharpe_diff_annual|+f2}} at levels 2 to 4 (two-sided p {{E2.CA.comparisons.static_mix.2.p_two_sided|f2}}, {{E2.CA.comparisons.static_mix.3.p_two_sided|f2}} and {{E2.CA.comparisons.static_mix.4.p_two_sided|f2}}), and minus the textbook optimizer {{E2.CA.comparisons.textbook_60.2.sharpe_diff_annual|+f2}}, {{E2.CA.comparisons.textbook_60.3.sharpe_diff_annual|+f2}} and {{E2.CA.comparisons.textbook_60.4.sharpe_diff_annual|+f2}} (p {{E2.CA.comparisons.textbook_60.2.p_two_sided|f2}}, {{E2.CA.comparisons.textbook_60.3.p_two_sided|f2}} and {{E2.CA.comparisons.textbook_60.4.p_two_sided|f2}}). In the US ({{E2.US.comparisons.textbook_60.3.months|int}} months), the smallest unadjusted p was {{E2.US.comparisons.textbook_60.3.p_two_sided|f3}}, with the textbook optimizer ahead at level 3 (difference {{E2.US.comparisons.textbook_60.3.sharpe_diff_annual|+f2}}); Holm's adjustment over the market's six E2 comparisons would multiply it by six, above 0.05. Strict point-in-time construction therefore detects no difference from either benchmark.

## 6.5 Covariance estimators (E4, descriptive)

Minimum-variance portfolios built from the four estimators had almost the same realised volatility in Canada ({{E4.CA.min_variance.lw_cc.ann_vol|pct2}} with constant correlation, {{E4.CA.min_variance.sample.ann_vol|pct2}} with the sample covariance), and no estimator's loss differed from constant-correlation shrinkage's at the 5% level in Canada (Diebold-Mariano p = {{E4.CA.min_variance.sample.dm_vs_lw_cc.p|f2}} for the sample covariance, {{E4.CA.min_variance.qis.dm_vs_lw_cc.p|f2}} for QIS). The forecast check with fixed weights gave QLIKE losses of {{E4.CA.forecast.lw_cc.qlike|f3}} for constant correlation and {{E4.CA.forecast.sample.qlike|f3}} for the sample covariance over {{E4.CA.forecast.lw_cc.years|int}} years. In the shipped pipeline at level 3 the differences were detectable: the sample covariance and QIS gave squared deviations {{E4.CA.target_risk.sample.dm_vs_lw_cc.relative|pct1}} and {{E4.CA.target_risk.qis.dm_vs_lw_cc.relative|pct1}} different from constant correlation's (Diebold-Mariano p below 0.001), with realised volatility of {{E4.CA.target_risk.sample.ann_vol|pct2}} and {{E4.CA.target_risk.qis.ann_vol|pct2}} against {{E4.CA.target_risk.lw_cc.ann_vol|pct2}} at the same targets. At a fixed target, lower realised volatility means slightly less risk than intended, not better risk control. On this small, well-conditioned list ($N/T$ about 0.06) the choice of estimator matters little for the risk delivered, as the shrinkage literature leads one to expect; constant correlation stays the default on the evidence of E3 and its source, not of this back-test.

## 6.6 Sensitivities (E5, descriptive)

At the latest date, the level-3 Canadian mix moved by at most {{E5.CA.today.block_length.3.max_weight_change|pp1}} points with a block of 3 months and {{E5.CA.today.window.120.max_weight_change|pp1}} points with a 120-month window; home bias of 0% moved it by {{E5.CA.today.home_bias.0.0.max_weight_change|pp0}} points, as a change of policy should. In the walk-forward, a 0% home bias would have given a Sharpe ratio of {{E5.CA.walk_forward.home_0.sharpe|f2}} against {{E1.CA.strategies.robokit.3.sharpe|f2}}, consistent with Canadian stocks lagging over this period. This is descriptive; the home share is policy with a source (Section 4.3), and choosing it from this result would be fitting the past. Halving or doubling the caps, and per-fund maxima of 35% or 70%, changed nothing: no cap binds at level 3. The Politis-White block length was {{E5.CA.today.politis_white_block|f1}} months in Canada and {{E5.US.today.politis_white_block|f1}} in the US, against the default of 6; the walk-forward with that block had a Sharpe ratio of {{E5.CA.walk_forward.block_pw.sharpe|f2}} and a risk ratio of {{E5.CA.walk_forward.block_pw.risk_ratio.ratio|f2}} in Canada, against {{E1.CA.strategies.robokit.3.sharpe|f2}} and {{E1.CA.risk_delivery.primary.3.ratio|f2}} with the default. With $\delta$ = 1 and 4 the calibrated Canadian mixes' volatility differed from the default's by {{E5.CA.today.delta.1.0.vol_gap_vs_delta_2.5|pp4}} and {{E5.CA.today.delta.4.0.vol_gap_vs_delta_2.5|pp4}} points, within twice the calibration tolerance, as Proposition 1 predicts.

**Projection precision changed a default.** The registered rule raises the projection paths from 2,000 to 5,000 if the Monte Carlo standard error of the one-year 5th percentile exceeds 0.25 points at any level. At 2,000 paths it was {{E5.CA.today.projection_se.4.2000.se|pp3}} points at level 4 in Canada, and {{E5.US.today.projection_se.4.2000.se|pp2}} and {{E5.US.today.projection_se.5.2000.se|pp2}} at levels 4 and 5 in the US; at 5,000 paths every level was below the threshold. The shipped default is now {{locked_defaults.projection_paths|int}} paths in both engines (Section 6.9).

## 6.7 Rebalancing on accounts (E6)

On a 100,000 account with no contributions, from {{E6.CA.from|raw}} to {{E6.CA.to|raw}} in Canada, the shipped bands earned {{derived.e6.CA.100000_0.bands_minus_ideal_return|pp2}} points a year more than ideal monthly rebalancing to target, with {{derived.e6.CA.100000_0.bands_cost_share_of_monthly|pct0}} of the monthly rule's trading cost and a tracking error of {{E6.CA.accounts.100000_0.bands.tracking_error_vs_ideal|pp2}} points against it. Annual rebalancing ({{E6.CA.accounts.100000_0.annual.ann_return|pct2}} a year) and bands that trade back to target ({{E6.CA.accounts.100000_0.bands_destination_0.ann_return|pct2}}) earned less than the shipped bands ({{E6.CA.accounts.100000_0.bands.ann_return|pct2}}), and bands that trade only back to their edge slightly more ({{E6.CA.accounts.100000_0.bands_destination_1.ann_return|pct2}}), with more tracking error. The more a rule lets weights drift, the more it earned over this rising window; that is not a property to expect in general, and the bands' lasting advantage is the lower cost. Whole units and the minimum order of 50 kept a 10,000 account with 500 a month within {{E6.CA.accounts.10000_500.bands.tracking_error_vs_ideal|pp2}} points of the ideal. On a 1,000,000 account the largest orders exceeded 1% of a fund's average daily traded value in {{derived.e6.CA.funds_over_1pct_adv_count|int}} Canadian funds ({{derived.e6.CA.funds_over_1pct_adv_text|raw}}; at most {{derived.e6.CA.max_adv_share|pct1}}) and in the US in {{derived.e6.US.funds_over_1pct_adv_text|raw}}; the product flags such orders.

## 6.8 Data rules and extended histories (E7, E8)

**Crisis replays.** The peer-median stand-in used for a fund without data through an episode missed the fund's own episode return by {{E7.crisis_standins.by_rule.class, region and market.median_ae|pp1}} points (median) when its peers came from the same class, region and market, over {{E7.crisis_standins.by_rule.class, region and market.n|int}} fund-episodes. Every fall of more than 15% in each home stock fund since 2000 is covered by a replay except one: the 2000-2002 bear market, in both markets. The replays begin with the 2008 crisis, so a mix's behaviour in a long, slow decline is not shown to clients; this is a gap to close.

**Stand-ins and back-fill.** The written stand-ins tracked their funds closely: the median correlation over the {{derived.e8.standin_rows|int}} fund and stand-in pairs was {{derived.e8.standin_median_corr|f2}} ({{derived.e8.vfv_spy_corr|f3}} for the Canadian S&P 500 fund against SPY). One is an exception: BNDX, a currency-hedged international bond fund, correlates {{derived.e8.bndx_bwx_corr|f2}} with its written stand-in BWX, which is unhedged; the stand-in rule's own correlation check refuses it, so it is never used. The regression back-fill for own picks recovered hidden histories with a median correlation of {{derived.e8.CA.median_corr|f2}} in Canada and {{derived.e8.US.median_corr|f2}} in the US. Its median tracking error ({{derived.e8.US.median_te|pct1}} a year in the US) was no better than simply using the home stock fund ({{derived.e8.US.median_home_te|pct1}}); in Canada it was a little better ({{derived.e8.CA.median_te|pct1}} against {{derived.e8.CA.median_home_te|pct1}}).

## 6.9 Run record and reproducibility

The first registered run stopped E2's three Canadian static-mix paths: the benchmark code looked up a cash fund on a point-in-time shelf that did not yet have one, although the static mix holds no cash. The protocol's fail-closed rule recorded the gap instead of stretching the previous weights over it. The bug was fixed, disclosed and tested; the first run was archived intact, and the evaluation was run again from the fix (RESEARCH_LOG section 11). Compared value by value (scripts/v3_compare_runs.py), every number of the second run equals the first run's except the provenance, those three paths and the values computed from them (their comparisons, ex-ante gaps and build-failure count), which shows the evaluation is deterministic. The locked defaults kept resampling on and the QIS switch at {{locked_defaults.qis_switch|f2}}, and raised the projection paths to {{locked_defaults.projection_paths|int}}.

Two changes followed the run, each in its own disclosed commit. The shipped constants were set to the locked defaults in both engines, and a test fails if they differ. The registered audit of fund labels (E7(e)) found that the fund-swap gate let narrow funds, such as sector or single-country funds, replace a slot's broad fund; the gate now requires the slot's own rule and a like-for-like label (docs/research/e7e_taxonomy.md). The first makes the shipped engine the configuration the evaluation locked. The second does not touch the evaluated path: no slot's candidate list changes and every point-in-time pick of E2 is accepted, so the results above apply to the shipped engine.

# 7. Adversarial validation

A model is not checked well by the people who built it, so outside examiners were asked to question every part of the optimizer. They came from model families other than the author's, because a reviewer from the same family tends to share the author's blind spots. Each was briefed as a professor examining a graduate team's work, from three angles: finance, quantitative statistics and numerical mathematics. They received the code, the documents and the claim under examination, and nothing else: no reasoning from the authors and no conclusions from another examiner. Every finding had to quote the code or text it concerned, and was checked against the repository before it was ruled true, partly true or false.

There were two stages:
1. **The optimizer (round 1).** Nineteen findings after duplicates were merged: fourteen ruled true and fixed with regression tests, three partly true, one false, and one split (its claim about $\delta$ false, its claim about the prior true).
2. **The evaluation plan (Stage 1, eighteen rounds).** The plan and its code were examined before anything ran, until a review accepted them as they stood. The examiners found, among other things:
   - defaults that could have changed while the walk-forward was testing them;
   - a simulation truth estimated from months the walk-forward would later test;
   - reading rules that rewarded an underpowered test, and a locking rule that could move on contradictory evidence;
   - failed builds and missing months that would have silently stretched a holding period;
   - a benchmark solver and several data paths that failed open;
   - a reported Sharpe ratio that was not the one tested;
   - register entries whose cited evidence did not test the decision.

   All were fixed before the run. Rounds 1 to 6 had two examiners from different families; from round 7 the usage limits of the examiners' model pools left one reviewer family, which reviewed rounds 8 to 18.

The record of every finding and ruling is in docs/DECISIONS.md. Testing the fixes found further bugs the examiners had not reported, among them two in the browser engine and an audit that compared a fund with itself.

# 8. Limitations

- **Power.** The Sharpe-ratio comparisons could not detect differences smaller than about 0.2 to 0.3 a year in Canada, or larger ones in the US, and none was detected. "Not detected" is not "equal", except where the non-inferiority test says so.
- **US risk.** Over 2019-2026 the US levels carried about a third more risk than their targets. A client choosing a US level should be told that its stated volatility is a long-run estimate that recent years exceeded.
- **The prior decides a lot.** When expected returns follow planning assumptions rather than equilibrium, the engine loses about as much as any method in simulation, and a static mix loses slightly less. The equilibrium prior (a written policy mix with 30% of equities in Canada) is a choice with a source, not a result of this evaluation.
- **Resampling unproven.** Resampling neither helped nor hurt; with equilibrium returns it has little to work on. It is kept by rule, not by evidence of benefit.
- **Benchmarks that cannot reach the target.** Unleveraged risk parity and minimum variance are less volatile than every primary target, so their comparisons are of lower-risk portfolios.
- **The risk-delivery reading is strict.** With 120 months, three simultaneous intervals around a mix that does deliver its target all fall inside [0.80, 1.25] only about two times in three, and the intervals cover the truth somewhat less often than their nominal level.
- **Fund choice is not point-in-time.** E2 removes the look-ahead in returns and stand-ins, but the list of funds, their eligibility and their scores are today's, and closed funds are absent.
- **Crisis replays.** None covers the 2000-2002 bear market.
- **Own picks.** In the US the regression back-fill of a young fund's history was no better than the home stock fund.
- **Liquidity.** For a 1,000,000 account, the largest orders in several Canadian funds exceed 1% of their average daily traded value; the engine flags them.
- **Data.** Prices and fund data come from Yahoo Finance and TMX for personal, non-commercial use. The registered issuer cross-check (E7(e), after the run, docs/research/e7e_issuer_check.md) found 15 of 17 comparable reference funds within 0.05 points a year of the issuer's five-year return; two BlackRock Canada funds (XIC, XRE) were 0.31 and 0.25 points a year below their published NAV returns, and the gold fund's gap is mostly its discount to NAV. The audit of each slot's top five candidates (docs/research/e7e_shelf_audit.md) found the core equity and aggregate-bond picks broad, cheap index funds, but the Canadian slot labelled global bonds holds a US-only aggregate fund, two niche slots (real estate, high yield) pick a dearer fund than the cheapest candidate because the score weights size, and the slots' filters admit some active and swap-based funds among lower-ranked candidates. The taxonomy sample (docs/research/e7e_taxonomy.md; funds labelled blind from the issuers' pages) found that the swap gate let narrow funds into core slots: of 18 sampled stock funds labelled core-eligible, one was a broad index fund. The gate now requires the slot's own rule and a like-for-like label; on a held-out sample, 29 of 30 narrow labels and 26 of 30 broad labels agree with the issuers (15 of 30 if an ESG screen or a large-cap index counts as narrow). The change does not touch the evaluated shelf: no slot's candidate list changes and every point-in-time pick is accepted. Some region and asset-class labels remain wrong and are listed there.
- **Examiners.** Rounds 8 to 18 of the review came from a single model family, because the other examiners' usage limits were reached; the earlier rounds had two families.
- **Deployment.** In Canada, advice from such an engine must be given by a registered portfolio manager with human oversight (CSA Staff Notice 31-342). This is a research and teaching tool.

# 9. Conclusion

Robo-Kit v3 does what its design says on the questions the evaluation could answer. It comes within {{E3.summary.a.3.180.robokit.loss_bp|f1}} basis points a year of the best constrained portfolio when its model is right; in Canada over sixteen years each level's realised volatility came within a few percent of its target, although the registered reading is "inconclusive" because two of the simultaneous intervals reach just past their band; its calibration and safety rules hold under adversarial testing; and it fails closed rather than producing an unexplained answer. The evaluation could not show that it beats simple alternatives on risk-adjusted return, and it showed that a static stock-bond mix does as well or slightly better when the model's expected returns are wrong. In the US it took more risk than it promised over a turbulent seven years. Both findings belong in what a client is told.

The process mattered as much as the engine. Writing the plan down first, having it examined eighteen times, and letting the code apply the readings found real problems before they could bias a result: defaults that could have changed during the test, truths built from tested months, holding periods that would have stretched silently, a Sharpe ratio reported differently from the one tested, and a benchmark that failed open. The run then found one more bug of its own, which the fail-closed rule caught. We recommend the same discipline to anyone evaluating an investment model, and we have published every finding and ruling so that it can be checked.

# Use of generative AI

The course permits generative AI with citation. The engine, the evaluation code and this paper were developed with an AI assistant (Anthropic's Claude), and the outside examiners of Section 7 were AI models from other families, briefed as described there. Every number in this paper is filled in by a script from the registered run's results file, every finding was checked against the code before it was ruled on, and the authors reviewed and are responsible for the content.

# References

Arnott, R., Harvey, C. R., & Markowitz, H. (2019). A backtesting protocol in the era of machine learning. Journal of Financial Data Science, 1(1), 64-74. https://doi.org/10.3905/jfds.2019.1.064

Bailey, D. H., & Lopez de Prado, M. (2012). The Sharpe ratio efficient frontier. Journal of Risk, 15(2), 3-44. https://doi.org/10.21314/JOR.2012.255

Bailey, D. H., & Lopez de Prado, M. (2014). The deflated Sharpe ratio: correcting for selection bias, backtest overfitting and non-normality. Journal of Portfolio Management, 40(5), 94-107. https://doi.org/10.3905/jpm.2014.40.5.094

Beck, A., & Teboulle, M. (2009). A fast iterative shrinkage-thresholding algorithm for linear inverse problems. SIAM Journal on Imaging Sciences, 2(1), 183-202. https://doi.org/10.1137/080716542

Beketov, M., Lehmann, K., & Wittke, M. (2018). Robo advisors: quantitative methods inside the robots. Journal of Asset Management, 19(6), 363-370. https://doi.org/10.1057/s41260-018-0092-9

Betterment (2026). Betterment's portfolio construction methodology. Updated 15 June 2026. https://www.betterment.com/resources/portfolio-construction-methodology

Black, F., & Litterman, R. (1992). Global portfolio optimization. Financial Analysts Journal, 48(5), 28-43. https://doi.org/10.2469/faj.v48.n5.28

Canadian Securities Administrators. National Instrument 81-102 Investment Funds, Appendix F, Investment Risk Classification Methodology; Companion Policy 31-103CP, s.13.2; CSA Staff Notice 31-342, Guidance for Portfolio Managers Regarding Online Advice (2015); Joint CSA/CIRO Staff Notice 31-368.

Cederburg, S., O'Doherty, M. S., Wang, F., & Yan, X. (2020). On the performance of volatility-managed portfolios. Journal of Financial Economics, 138(1), 95-117. https://doi.org/10.1016/j.jfineco.2020.04.015

Chopra, V. K., & Ziemba, W. T. (1993). The effect of errors in means, variances, and covariances on optimal portfolio choice. Journal of Portfolio Management, 19(2), 6-11. https://doi.org/10.3905/jpm.1993.409440

D'Acunto, F., Prabhala, N., & Rossi, A. G. (2019). The promises and pitfalls of robo-advising. Review of Financial Studies, 32(5), 1983-2020. https://doi.org/10.1093/rfs/hhz014

DeMiguel, V., Garlappi, L., Nogales, F. J., & Uppal, R. (2009). A generalized approach to portfolio optimization: improving performance by constraining portfolio norms. Management Science, 55(5), 798-812. https://doi.org/10.1287/mnsc.1080.0986

DeMiguel, V., Garlappi, L., & Uppal, R. (2009). Optimal versus naive diversification: how inefficient is the 1/N portfolio strategy? Review of Financial Studies, 22(5), 1915-1953. https://doi.org/10.1093/rfs/hhm075

Diebold, F. X., & Mariano, R. S. (1995). Comparing predictive accuracy. Journal of Business and Economic Statistics, 13(3), 253-263. https://doi.org/10.1080/07350015.1995.10524599

Doeswijk, R., Lam, T., & Swinkels, L. (2014). The global multi-asset market portfolio, 1959-2012. Financial Analysts Journal, 70(2), 26-41. https://doi.org/10.2469/faj.v70.n2.1

Donohue, C., & Yip, K. (2003). Optimal portfolio rebalancing with transaction costs. Journal of Portfolio Management, 29(4), 49-63. https://doi.org/10.3905/jpm.2003.319894

Dowell, M., & Jarratt, P. (1971). A modified regula falsi method for computing the root of an equation. BIT, 11(2), 168-174. https://doi.org/10.1007/BF01934364

EMEA, Committee for Proprietary Medicinal Products (2000). Points to consider on switching between superiority and non-inferiority. CPMP/EWP/482/99.

FP Canada and Institute of Financial Planning (2026). Projection Assumption Guidelines.

Harvey, C. R., Liechty, J. C., & Liechty, M. W. (2008). Bayes vs. resampling: a rematch. Journal of Investment Management, 6(1), 29-45.

Harvey, C. R., Liu, Y., & Zhu, H. (2016). ... and the cross-section of expected returns. Review of Financial Studies, 29(1), 5-68. https://doi.org/10.1093/rfs/hhv059

Gurobi Optimization. Minimum buy-in. Gurobi Finance documentation.

He, G., & Litterman, R. (1999). The intuition behind Black-Litterman model portfolios. Goldman Sachs Investment Management Research.

Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics, 6(2), 65-70.

Idzorek, T. (2007). A step-by-step guide to the Black-Litterman model. In S. Satchell (Ed.), Forecasting Expected Returns in the Financial Markets. Elsevier.

Jagannathan, R., & Ma, T. (2003). Risk reduction in large portfolios: why imposing the wrong constraints helps. Journal of Finance, 58(4), 1651-1683. https://doi.org/10.1111/1540-6261.00580

Jorion, P. (1986). Bayes-Stein estimation for portfolio analysis. Journal of Financial and Quantitative Analysis, 21(3), 279-292. https://doi.org/10.2307/2331042

Jorion, P. (2003). Portfolio optimization with tracking-error constraints. Financial Analysts Journal, 59(5), 70-82. https://doi.org/10.2469/faj.v59.n5.2565

Kritzman, M., Page, S., & Turkington, D. (2010). In defense of optimization: the fallacy of 1/N. Financial Analysts Journal, 66(2), 31-39. https://doi.org/10.2469/faj.v66.n2.6

Ledoit, O., & Wolf, M. (2004). Honey, I shrunk the sample covariance matrix. Journal of Portfolio Management, 30(4), 110-119. https://doi.org/10.3905/jpm.2004.110

Ledoit, O., & Wolf, M. (2008). Robust performance hypothesis testing with the Sharpe ratio. Journal of Empirical Finance, 15(5), 850-859. https://doi.org/10.1016/j.jempfin.2008.03.002

Ledoit, O., & Wolf, M. (2017). Nonlinear shrinkage of the covariance matrix for portfolio selection: Markowitz meets Goldilocks. Review of Financial Studies, 30(12), 4349-4388. https://doi.org/10.1093/rfs/hhx052

Ledoit, O., & Wolf, M. (2022). Quadratic shrinkage for large covariance matrices. Bernoulli, 28(3), 1519-1547. https://doi.org/10.3150/20-BEJ1315

Maillard, S., Roncalli, T., & Teiletche, J. (2010). The properties of equally weighted risk contribution portfolios. Journal of Portfolio Management, 36(4), 60-70. https://doi.org/10.3905/jpm.2010.36.4.060

Markowitz, H. (1952). Portfolio selection. Journal of Finance, 7(1), 77-91. https://doi.org/10.1111/j.1540-6261.1952.tb01525.x

Markowitz, H. M., & Usmen, N. (2003). Resampled frontiers versus diffuse Bayes: an experiment. Journal of Investment Management, 1(4), 9-25.

Michaud, R. O. (1989). The Markowitz optimization enigma: is 'optimized' optimal? Financial Analysts Journal, 45(1), 31-42. https://doi.org/10.2469/faj.v45.n1.31

Michaud, R. O., & Michaud, R. O. (2008). Efficient Asset Management (2nd ed.). Oxford University Press. https://doi.org/10.1093/oso/9780195331912.001.0001

Moreira, A., & Muir, T. (2017). Volatility-managed portfolios. Journal of Finance, 72(4), 1611-1644. https://doi.org/10.1111/jofi.12513

Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. Econometrica, 55(3), 703-708. https://doi.org/10.2307/1913610

O'Donoghue, B., & Candes, E. (2015). Adaptive restart for accelerated gradient schemes. Foundations of Computational Mathematics, 15(3), 715-732. https://doi.org/10.1007/s10208-013-9150-3

Patton, A., Politis, D. N., & White, H. (2009). Correction to "Automatic block-length selection for the dependent bootstrap". Econometric Reviews, 28(4), 372-375. https://doi.org/10.1080/07474930802459016

Politis, D. N., & Romano, J. P. (1994). The stationary bootstrap. Journal of the American Statistical Association, 89(428), 1303-1313. https://doi.org/10.1080/01621459.1994.10476870

Politis, D. N., & White, H. (2004). Automatic block-length selection for the dependent bootstrap. Econometric Reviews, 23(1), 53-70. https://doi.org/10.1081/ETC-120028836

Rossi, A. G., & Utkus, S. P. (2020). Who benefits from robo-advising? Evidence from machine learning. SSRN working paper. https://doi.org/10.2139/ssrn.3552671

Scherer, B. (2002). Portfolio resampling: review and critique. Financial Analysts Journal, 58(6), 98-109. https://doi.org/10.2469/faj.v58.n6.2489

Sharpe, W. F. (1974). Imputing expected security returns from portfolio composition. Journal of Financial and Quantitative Analysis, 9(3), 463-472. https://doi.org/10.2307/2329873

Toth, B., Lemperiere, Y., Deremble, C., de Lataillade, J., Kockelkoren, J., & Bouchaud, J.-P. (2011). Anomalous price impact and the critical nature of liquidity in financial markets. Physical Review X, 1, 021006. https://doi.org/10.1103/PhysRevX.1.021006

Vanguard (2010). Best practices for portfolio rebalancing. Vanguard (2024). The rebalancing edge: optimizing target-date fund rebalancing through threshold-based strategies.

Vanguard Investments Canada (2024, June 25). Press release on Canadian home bias (newswire.ca).

Walters, J. (2014). The Black-Litterman model in detail. SSRN. https://doi.org/10.2139/ssrn.1314585

# Appendix A. The exact projection onto the capped simplex

Each step of the solver (Section 4.6) needs the Euclidean projection of a point $x \in \mathbb{R}^N$ onto $C = \{v : a^{\top}v = b,\ 0 \le v \le c\}$ with $a > 0$. The problem $\min_v \frac{1}{2}\lVert v - x \rVert^2$ over $C$ is strictly convex, so its solution is unique, and its Karush-Kuhn-Tucker conditions give, for a multiplier $\tau$ of the equality,

$$v_i(\tau) = \min\left(c_i,\ \max\left(0,\ x_i - \tau a_i\right)\right).$$

The function $g(\tau) = a^{\top}v(\tau)$ is continuous, non-increasing and piecewise linear, with breakpoints at $\tau = x_i / a_i$ and $\tau = (x_i - c_i)/a_i$. If $b$ lies between $g$'s limits ($0 \le b \le a^{\top}c$, which the engine checks before solving), a $\tau^{*}$ with $g(\tau^{*}) = b$ exists. The engine evaluates $g$ at every sorted breakpoint, takes the last one at which $g$ is still at least $b$, and interpolates linearly on the next segment, which gives $\tau^{*}$ exactly; it then removes the floating-point residual of the budget on the coordinates strictly inside their bounds. As implemented this costs $O(N^2)$ operations, negligible for a few dozen funds (running sums would bring it to $O(N \log N)$). The engine's previous version found $\tau$ by numerical bisection instead. On 2,000 random cases the exact projection meets the budget to $10^{-12}$, stays inside the bounds, and agrees with bisection to $10^{-9}$ (tests/test_v3_parity.py).
