# 5. Evaluation design

## 5.1 Protocol

The evaluation follows Arnott, Harvey and Markowitz (2019): its design was fixed before any of it was run, and it was run once. The plan (RESEARCH_LOG section 10) was written, then reviewed in the manner of a registered report's Stage 1 review by two outside examiners from different model families, revised, and reviewed again until both accepted it (Section 7). The code that runs it was committed first. The run refuses to start from a working tree with uncommitted changes, and it records the commit, the data snapshot and the package versions with the results. No back-test result changes a default. Two components can change only through rules written in advance and applied by the code: resampling and the point at which QIS takes over. Both rules work on a simulation with a known truth, run first (E3), and they lock the configuration that every later part evaluates.

## 5.2 Walk-forward (E1)

For Canada and the US, the shipped engine is re-estimated every December on the data available then, with an expanding window capped at 180 months. The weights are held for 12 months and rebalanced monthly to target, with 10 bps one way charged on all turnover. The funds are today's reference shelf, extended back with their written stand-ins; returns, interest rates and exchange rates stop at each estimation date. The choice of funds and stand-ins is today's knowledge, a look-ahead that E2 removes.

Robo-Kit is compared with four risk-matched benchmarks:
- a static stock-bond mix;
- the textbook optimizer (sample means, 60-month window, no resampling);
- equal risk contribution mixed with cash to the target;
- minimum variance mixed with cash to the target.

Equal weights and seven one-component ablations are reported descriptively.

Sharpe-ratio differences use the Ledoit and Wolf (2008) studentised circular block bootstrap with a Holm adjustment. Each comparison is read by a rule written in advance and applied by the code: "benchmark better" or "robokit better" when the Holm-adjusted p is below 0.05; otherwise "robokit not worse by more than 0.10" from a non-inferiority test; otherwise "too short to tell" when robokit is ahead but the sample is shorter than the minimum track record; otherwise "inconclusive".

Risk delivery is the standard deviation of monthly returns divided by the monthly target in force. Simultaneous 90% intervals over levels 2-4 must lie inside [0.80, 1.25] for the levels to count as delivering their risk; a point estimate outside the band counts as a miss.

A power statement was written before the run. In Canada, a Sharpe difference has to be about 0.22 to be detected half the time and about 0.31 to be detected 80% of the time; in the US, about 0.31 and 0.45. Most comparisons were therefore expected to be inconclusive.

## 5.3 Strict point-in-time returns (E2)

Every series is cut at the estimation date before anything is computed. Each slot holds the best-scoring fund that already had 36 months of its own returns, with no stand-ins. A test shows the strict mode cannot see the future: replacing every later return, rate and exchange rate with noise leaves the mix unchanged.

## 5.4 Simulation with a known truth (E3)

The shipped pipeline runs on simulated histories through its own data loader, 500 per world, with common random numbers. The truth comes only from months before the walk-forward's first estimation date. There are three worlds:
- **a:** equilibrium means, so the model is right;
- **b:** FP Canada planning returns after fees, so the model is wrong;
- **c:** world (b) with two volatility regimes, the case block resampling is meant for.

Methods are scored by certainty-equivalent loss against the true constrained optimum at the level's own risk aversion. Two sub-studies test the 36-month minimum history and the QIS switch point.

## 5.5 The rest

- **E4:** covariance estimators, in a walk-forward horse race and a fixed-weight forecast check.
- **E5:** sensitivity to every constant that has no source, including the Politis and White (2004) block length and the Monte Carlo precision of the projections.
- **E6:** the shipped rebalancer on simulated accounts at real prices.
- **E7:** audits of the data rules.
- **E8:** hold-out tests of the stand-in and back-filled histories.

# 7. Adversarial validation

A model is not checked by the people who built it, so two outside examiners were asked to question every part of the optimizer. They came from model families different from the author's, because a reviewer from the same family tends to share the author's blind spots. Each was briefed as a professor examining a graduate team's work in an oral defence, from three angles: finance, quantitative statistics and numerical mathematics. They received the code, the documents and the claim under examination, and nothing else: no reasoning from the authors and no conclusions from the other examiner. Every finding had to quote the code or text it concerned. Each was checked against the repository before it was ruled true, partly true or false.

There were five rounds:
1. **The optimizer (round 1).** The examiners raised 15 questions and 9 bug reports. Thirteen were true and fixed with regression tests, four partly true and two false.
2. **The evaluation plan (Stage 1, three rounds).** The plan and its code were examined before anything ran. The examiners found, among other things:
   - defaults that could have changed while the walk-forward was testing them;
   - a simulation truth estimated from months the walk-forward would later test;
   - reading rules that rewarded an underpowered test;
   - synthetic prices in the rebalancing test;
   - a reading that mislabelled a losing comparison as "too short to tell".

   All of these were fixed before the run.
3. **The final round.** [result of Stage 1 round 4]

The record of every finding and ruling is in docs/DECISIONS.md. The tests written in response found further bugs the examiners had not reported, including two in the browser engine.
