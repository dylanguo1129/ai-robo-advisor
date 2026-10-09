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
