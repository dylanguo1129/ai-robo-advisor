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
