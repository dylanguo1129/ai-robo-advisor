# 4. Method

## 4.1 Problem and notation

The engine chooses weights $w \in \mathbb{R}^N$ over a shelf of $N$ exchange-traded funds: one broad, low-cost fund per asset-class slot, a cash fund, and up to a few funds the client adds ("own picks"). Monthly total returns $r_{t} \in \mathbb{R}^N$, $t = 1, \dots, T$, come from dividend- and split-adjusted month-end prices, so they are net of each fund's fee. The engine solves the long-only mean-variance problem

$$\max_{w}\ \mu^{\top} w - \frac{\lambda}{2}\, w^{\top} \Sigma\, w \quad \text{s.t.} \quad \mathbf{1}^{\top} w = 1,\quad \ell \le w \le u,\quad \textstyle\sum_{i \in G} w_i \le g$$

where $\mu$ are expected excess returns, $\Sigma$ the annual covariance, $\ell$ and $u$ the lower and upper limits, $G$ the own picks and $g$ their joint limit. Three things make this a product rather than a textbook exercise: what goes into $\mu$ and $\Sigma$ (Sections 4.2 and 4.3), how $\lambda$ is set so that a client's chosen level delivers a stated risk (Sections 4.5 and 4.8), and what happens between the optimum and the orders a person places (Sections 4.9 and 4.10).

## 4.2 Risk: shrunk covariance

The sample covariance of a few dozen funds over 15 years is noisy, and a mean-variance optimizer exploits exactly that noise (Michaud 1989; Chopra and Ziemba 1993). The engine shrinks it toward a constant-correlation target (Ledoit and Wolf 2004):

$$\hat{\Sigma} = 12\,\frac{T}{T-1}\left(\hat{s}\,F + (1-\hat{s})\,S\right), \qquad F_{ii} = S_{ii}, \quad F_{ij} = \bar{\rho}\sqrt{S_{ii}S_{jj}}$$

with $S$ the sample covariance (divisor $T$), $\bar{\rho}$ the average sample correlation and $\hat{s}$ the estimated optimal intensity. When the list is wide, with $N/T > 0.25$, linear shrinkage leaves the small eigenvalues too small, and the engine switches to quadratic-inverse shrinkage (QIS; Ledoit and Wolf 2022), which keeps the sample eigenvectors and shrinks the inverse eigenvalues. The switch point is tested by simulation (Section 5, E3).

The factor $12\,T/(T-1)$ annualises the matrix and puts it on the same unbiased footing as the stock-market volatility it is compared with (Section 4.5). It does not move the weights at a given $\lambda$ (Proposition 2).

## 4.3 Expected returns: equilibrium from a written policy mix

Sample means are the largest source of estimation error in mean-variance analysis (Chopra and Ziemba 1993). The engine never uses them. It reverse-engineers the returns that would make a reference portfolio $w^{0}$ optimal (Sharpe 1974; Black and Litterman 1992; He and Litterman 1999):

$$\pi = \delta\, \hat{\Sigma}\, w^{0}, \qquad \delta = 2.5$$

$w^{0}$ is a written policy mix rather than fund sizes: 60% stocks, 35% bonds, 3% real estate and 2% gold, with 30% of the stock share in Canada. The market portfolio is the natural neutral prior (Doeswijk, Lam and Swinkels 2014). Holding Canadian equities at about ten times Canada's 2.7% share of world equity follows Vanguard Investments Canada (2024), which sees "a reasonable equity balance of around 30% home bias, in Canadian securities"; the sensitivity of the mix to this choice is reported (E5). The value of $\delta$ does not matter for the weights once $\lambda$ is calibrated (Proposition 1); 2.5 is He and Litterman's (1999) "world average risk tolerance" and only scales the model returns shown beside the mix.

## 4.4 Limits

Each fund is capped at 50% of the portfolio. Narrow or volatile slots are capped lower (real estate, gold and high-yield bonds 10%; emerging markets and small caps 15%; real-return bonds 20%; long bonds 25%), and cash at 100%, 30% and 15% at levels 1, 2 and 3-5. Own picks are capped at 10% each (crypto 5%) and 10%, 20% or 30% together, depending on the level. Constraints of this kind are known to stabilise optimised portfolios by acting as shrinkage (Jagannathan and Ma 2003); the caps themselves are policy, and their effect is measured (E1 ablation, E5). Limits that cannot all hold are refused, never relaxed silently. A client may ask for relaxation, which proceeds in a fixed order with every step recorded.

## 4.5 Risk levels

A client chooses a level $L \in [1, 5]$. A self-check suggests the lower of capacity and willingness to take risk, as Canadian suitability guidance requires (Companion Policy 31-103CP, s.13.2). The level sets a target volatility as a share of the stock market's:

$$\sigma^{*}(L) = 0.2\,L\;\sigma_{\text{eq}}, \qquad \sigma_{\text{eq}} = \sqrt{12}\;\mathrm{sd}\left(\textstyle\sum_{j \in E} \tilde{w}^{0}_{j}\, r_{j,t}\right)$$

with $E$ the equity slots and $\tilde{w}^{0}$ their policy weights normalised to sum to one. Matching portfolios to risk levels "on volatility" is how Betterment, for example, describes its allocations. Because Canadian funds are rated on a regulator's scale, every mix also reports its NI 81-102 Appendix F rating: the standard deviation of its last 120 monthly returns times $\sqrt{12}$, placed in five bands. With fewer than 120 months the figure is labelled an estimate on that scale, not an Appendix F rating.

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

The three are checked numerically in the test suite (tests/test_v3_propositions.py). Proposition 1 and 2 hold to $10^{-7}$ in the weights, and Proposition 1 also holds through the full pipeline the client receives, single solve and resampled, at a fixed $\lambda/\delta$ (each resampled draw's equilibrium return is $\delta$ times its own covariance times $w^0$); calibrated at $\delta = 1$ and $\delta = 4$, the two mixes' volatility agrees within twice the calibration tolerance. The bounds on $\lambda$ are absolute, so the invariance holds while $\lambda$ stays inside them. and Proposition 3 holds on a 60-point grid of $\lambda$. Proposition 3 does not extend to the resampled average: on the same grid its volatility rises in places by up to 0.005 points. That is why Section 4.8 brackets the target rather than assuming monotonicity.
