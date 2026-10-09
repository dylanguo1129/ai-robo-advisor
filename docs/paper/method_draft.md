# 4. Method

## 4.1 Problem and notation

The engine chooses weights $w \in \mathbb{R}^N$ over the $N$ funds of the shelf and the client's own picks (Section 3). With monthly total returns $r_{t} \in \mathbb{R}^N$, $t = 1, \dots, T$, it solves the long-only mean-variance problem of Markowitz (1952) with limits:

$$\max_{w}\ \mu^{\top} w - \frac{\lambda}{2}\, w^{\top} \Sigma\, w \quad \text{s.t.} \quad \mathbf{1}^{\top} w = 1,\quad \ell \le w \le u,\quad \textstyle\sum_{i \in G} w_i \le g$$

where $\mu$ are expected excess returns, $\Sigma$ the annual covariance, $\lambda$ the risk aversion, $\ell$ and $u$ the lower and upper limits, $G$ the own picks and $g$ their joint limit. What makes this a product rather than a textbook exercise is what goes into $\Sigma$ and $\mu$ (Sections 4.2-4.3), how $\lambda$ is set so that a client's level delivers a stated risk (4.5, 4.8), and what happens between the optimum and the orders (4.9-4.10).

## 4.2 Risk: shrunk covariance

An optimizer exploits the noise in a sample covariance, so the engine shrinks it toward a constant-correlation target (Ledoit and Wolf 2004):

$$\hat{\Sigma} = 12\,\frac{T}{T-1}\left(\hat{s}\,F + (1-\hat{s})\,S\right), \qquad F_{ii} = S_{ii}, \quad F_{ij} = \bar{\rho}\sqrt{S_{ii}S_{jj}}$$

with $S$ the sample covariance (divisor $T$), $\bar{\rho}$ the average sample correlation and $\hat{s}$ the estimated optimal intensity; the factor $12\,T/(T-1)$ annualises it without moving the weights (Proposition 2). When the list is wide ($N/T > 0.25$) the engine switches to quadratic-inverse shrinkage (QIS; Ledoit and Wolf 2022), which keeps the sample eigenvectors and shrinks the inverse eigenvalues; the switch point was tested by simulation (Section 6.1).

## 4.3 Expected returns: equilibrium from a written policy mix

Sample means are the largest source of estimation error (Chopra and Ziemba 1993), and the engine never uses them. It reverse-engineers the returns that would make a reference portfolio $w^{0}$ optimal (Sharpe 1974; Black and Litterman 1992; He and Litterman 1999):

$$\pi = \delta\, \hat{\Sigma}\, w^{0}, \qquad \delta = 2.5$$

The market portfolio is the natural reference (Doeswijk, Lam and Swinkels 2014), but the engine departs from it on purpose. $w^{0}$ is a written policy mix of 60% stocks, 35% bonds, 3% real estate and 2% gold, with 30% of the stocks in Canada, about ten times Canada's 2.7% share of world equity. The class weights are product policy; the home share follows Vanguard Investments Canada (2024), which sees "a reasonable equity balance of around 30% home bias". Section 6.6 reports how much both move the mix. The value of $\delta$, He and Litterman's "world average risk tolerance", does not affect the weights once $\lambda$ is calibrated (Proposition 1).

## 4.4 Limits

Each fund is capped at 50% of the portfolio; narrow or volatile slots lower (real estate, gold and high-yield bonds 10%, emerging markets and small caps 15%, real-return bonds 20%, long bonds 25%), and cash at 100%, 30% and 15% at levels 1, 2 and 3-5. Own picks are capped at 10% each (crypto 5%) and at 10%, 20% or 30% together, by level. Such constraints act as shrinkage (Jagannathan and Ma 2003); the caps themselves are policy, and their effect is measured (Sections 6.2, 6.6). Limits that cannot all hold are refused, never relaxed silently.

## 4.5 Risk levels

A client chooses a level $L \in [1, 5]$; a self-check suggests the lower of capacity and willingness to take risk, as Canadian suitability guidance requires (Companion Policy 31-103CP, s.13.2). The level sets a target volatility as a share of the stock market's:

$$\sigma^{*}(L) = 0.2\,L\;\sigma_{\text{eq}}, \qquad \sigma_{\text{eq}} = \sqrt{12}\;\mathrm{sd}\left(\textstyle\sum_{j \in E} \tilde{w}^{0}_{j}\, r_{j,t}\right)$$

with $E$ the equity slots and $\tilde{w}^{0}$ their policy weights normalised to sum to one. The 20% step is policy, tested by how closely realised risk meets the target (Section 6.2). Setting targets from a benchmark's volatility has precedent: for its portfolios with 60% or more in bonds, Betterment sets "target volatilities assigned to each risk level", which "are determined by considering the volatility of the equivalent benchmark" (Betterment 2026). Every mix also reports its rating on the regulator's scale (NI 81-102 Appendix F: the annualised standard deviation of its last 120 monthly returns, in five bands).

## 4.6 Solver

The problem is a strictly convex quadratic program over a capped simplex. The engine solves it with accelerated projected gradient steps (FISTA; Beck and Teboulle 2009) on a diagonally rescaled problem, projecting exactly onto the constraint set at each step (Appendix A), and refuses any answer whose optimality residual is above $10^{-6}$. The browser runs the same algorithm, and the two agree to rounding on every test case.

## 4.7 Resampling

The weights are averaged over 200 histories drawn by the stationary bootstrap (Politis and Romano 1994; mean block six months, so crises and calm spells cluster as they did), with $\hat{\Sigma}$ and $\pi$ re-estimated on each (Michaud 1989); this spreads weight across funds a single solve treats as interchangeable. Its critics point out that an average of optimal portfolios need not be optimal and can drift off the risk target (Scherer 2002; Harvey, Liechty and Liechty 2008). The drift is answered by construction (Section 4.8); the efficiency cost is tested, with a rule set in advance for dropping resampling (Section 6.1). The spread of each fund's resampled weights (5th to 95th percentile) is shown as a spread, not as a confidence interval.

## 4.8 Calibrating risk aversion to the target

For a single solve, volatility falls as $\lambda$ rises (Proposition 3), so a search on $\lambda$ finds the value that meets $\sigma^{*}(L)$. But the client receives the resampled mix after positions under 2% are dropped, whose volatility differs (in v2, level 5 ended 0.23 points below target) and is not monotone in $\lambda$: averaging can raise it locally, and dropping a fund makes it jump. The engine therefore calibrates on the final mix itself, with the same bootstrap draws at every step, so that its volatility is a deterministic function of $\lambda$: it brackets the target and narrows the bracket by Illinois regula falsi (Dowell and Jarratt 1971). Each calibration ends in one of three recorded ways: within $5 \times 10^{-5}$ of the target; at a jump of the minimum-position rule, where no $\lambda$ gives a closer mix; or out of reach, at a bound of $\lambda$. Anything else counts as a failure.

## 4.9 Minimum position

Positions under 2% are dropped and the problem re-solved until none is left; a drop that the remaining limits cannot hold is not made, and weights are never rescaled past a limit. Small positions add little but cost trades (Gurobi Finance's minimum buy-in documentation).

## 4.10 From weights to orders

A rebalancer turns holdings, prices and a cash flow into orders. New money buys the funds furthest below target and withdrawals sell those furthest above (Vanguard 2010). A fund that drifts more than $\min(2\text{ points}, 25\%$ of target$)$ is traded back to 7/8 of its band, Vanguard's (2024) "threshold of 200 bps and a destination of 175 bps", and the funds still inside their bands take the other side without leaving them; trading only to the band's edge is optimal under proportional costs (Donohue and Yip 2003), and Section 6.7 compares both. Orders are whole units, orders under $50 are skipped, the cash must cover the orders and their estimated cost (10 bps), and an order above 1% of a fund's daily traded value is flagged: under the square-root impact law (Toth et al. 2011) it moves the price by about a tenth of a day's volatility, roughly the assumed cost.

## 4.11 Projections and crisis replays

**Projections** show a range of futures, not a forecast. Each fund's monthly history is re-centred on its planning return after fees (Section 3), and blocks of months are drawn by the stationary bootstrap, the same months for every fund so that they move together. The engine draws {{locked_defaults.projection_paths|int}} paths and shows the 10th to 90th percentiles. **Crisis replays** show what the mix would have returned through seven episodes, from the 2008 financial crisis to the 2025 tariff shock; a fund without data for an episode is given the median episode return of similar eligible funds.

## 4.12 Three propositions

**Proposition 1 (delta).** Let $w^{*}(\lambda, \delta)$ solve the problem of Section 4.1 with $\mu = \pi = \delta\Sigma w^{0}$. Then $w^{*}(\lambda, \delta) = w^{*}(\lambda/\delta, 1)$, so the volatility of $w^{*}$ depends on $\lambda$ and $\delta$ only through $\lambda/\delta$. With $\lambda$ calibrated to a volatility target, the weights do not depend on $\delta$.

*Proof.* The objective $\delta\, w^{0\top}\Sigma w - \frac{\lambda}{2} w^{\top}\Sigma w$ equals $\delta$ times $w^{0\top}\Sigma w - \frac{\lambda/\delta}{2} w^{\top}\Sigma w$. Multiplying an objective by a positive constant leaves its maximiser over a fixed feasible set unchanged, and the problem is strictly convex, so the maximiser is unique. If $\lambda_1/\delta_1$ meets the target, so does $\lambda_2 = \lambda_1 \delta_2/\delta_1$ with $\delta_2$, and both give the same weights. $\square$

**Proposition 2 (scale of the covariance).** For $c > 0$, replacing $\Sigma$ by $c\,\Sigma$ (with $\pi = \delta\, c\Sigma w^{0}$) leaves $w^{*}(\lambda)$ unchanged.

*Proof.* The objective becomes $c$ times the original one. $\square$ The factors 12 and $T/(T-1)$ are such scalings: they change the volatility reported, not the weights at a given $\lambda$.

**Proposition 3 (monotone volatility of the single solve).** For $\lambda_1 < \lambda_2$ with maximisers $w_1, w_2$ and variances $V_k = w_k^{\top}\Sigma w_k$, $V_1 \ge V_2$.

*Proof.* Optimality of each gives $\mu^{\top}w_1 - \frac{\lambda_1}{2}V_1 \ge \mu^{\top}w_2 - \frac{\lambda_1}{2}V_2$ and $\mu^{\top}w_2 - \frac{\lambda_2}{2}V_2 \ge \mu^{\top}w_1 - \frac{\lambda_2}{2}V_1$. Adding them gives $\frac{1}{2}(\lambda_2 - \lambda_1)(V_1 - V_2) \ge 0$. $\square$

The test suite checks all three numerically (tests/test_v3_propositions.py). Proposition 3 does not extend to the resampled average, whose volatility rises in places by up to 0.005 points as $\lambda$ grows; that is why Section 4.8 brackets the target rather than assuming monotonicity.
