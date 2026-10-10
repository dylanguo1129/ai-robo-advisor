# 5. Evaluation design

## 5.1 Protocol

The evaluation follows Arnott, Harvey and Markowitz (2019): its design was written down before any of it ran (docs/RESEARCH_LOG.md, sections 9 and 10), examined before the run (Section 5.5), and run from committed code that records the commit, the data snapshot and the package versions with its results. It has eight parts.

Table: The eight parts of the evaluation

| Part | Question | Status |
|---|---|---|
| E1 Walk-forward | Does each level deliver its target risk, and how does its Sharpe ratio compare with four benchmarks? | Confirmatory in Canada, exploratory in the US |
| E2 Strict point-in-time | Do E1's risk results survive when nothing after each estimation date is used? | Descriptive |
| E3 Simulation with a known truth | How far is the engine from the true optimum, does resampling earn its place, and where should QIS take over? | Locks two defaults |
| E4 Covariance estimators | Does the choice of estimator matter on these funds? | Descriptive |
| E5 Sensitivities | How much do constants without a source move the mix, and are the projections precise enough? | Descriptive; locks one default |
| E6 Rebalancing | How do the bands compare with simpler rules on real accounts? | Descriptive |
| E7 Data audits | Do the data rules, the crisis replays and the fund labels hold up? | Descriptive |
| E8 Extended histories | How well do the stand-ins and back-filled histories recover real ones? | Descriptive |

No back-test result changes a default. Three defaults can change only through rules written in advance and applied by the code: resampling and the QIS switch point, by E3, which runs first, and the number of projection paths, by E5 (raised from 2,000 to 5,000 if the standard error of the one-year 5th percentile exceeds 0.25 points at any level). Every later part runs on the configuration they lock, and the shipped constants were then set to it in both engines. Levels 2, 3 and 4 are the main levels on which E1 and E2 are read; levels 1 and 5 are reported on their own.

## 5.2 Walk-forward (E1)

For Canada and the US, the shipped engine is re-estimated every December on the data available then, with an expanding window of up to 180 months, held for 12 months, rebalanced monthly to target and charged 10 bps one way on all turnover. The funds are today's shelf, extended back with their stand-ins; returns, rates and exchange rates stop at each estimation date. A path stops, with the reason recorded, if a held fund has no return in a month or a scheduled build fails.

Robo-Kit is compared with four benchmarks: a static stock-bond mix of 40, 60 or 80% stocks at levels 2, 3 and 4, aimed at the target by its stock share but not calibrated; the textbook optimizer (sample means over 60 months, one solve, no resampling); and equal risk contribution and minimum variance, each mixed with cash toward the target, or used as they are when already less volatile than it. Each strategy's ex-ante gap, how far its model volatility lies from the target, is reported. Equal weights and seven one-component ablations of the engine are descriptive.

The Sharpe ratio is the mean monthly excess return over its standard deviation (divisor $T$), times $\sqrt{12}$, the form the Ledoit and Wolf (2008) test uses. Each difference is tested with their studentised circular block bootstrap (blocks of six months), and p-values are adjusted by Holm's method over the twelve comparisons of each market. The code reads each comparison in this order:
1. "benchmark better" or "robokit better" if the adjusted two-sided p is below 0.05;
2. otherwise "robokit not worse by more than 0.10" if the adjusted p of a non-inferiority test (against Robo-Kit being worse by 0.10 or more) is below 0.05;
3. otherwise "too short to tell" if Robo-Kit is ahead but the sample is shorter than the minimum track record, the number of months the observed difference would need to be significant (Bailey and Lopez de Prado 2012);
4. otherwise "inconclusive".

The intervals reported beside the readings are unadjusted. Risk delivery is the realised standard deviation divided by the target in force; the main levels count as delivered if their simultaneous 90% intervals all lie inside [0.80, 1.25], as missed at any level whose point estimate lies outside, and as inconclusive otherwise. A power statement written before the run put the Sharpe difference detected half the time at about 0.22 in Canada (0.31 in the US) and 80% of the time at about 0.31 (0.45), so most comparisons were expected to be inconclusive.

**Found after the run.** The audit of Section 6.9 found three points on which the registered statistics need a caveat; the results are reported as registered. First, the textbook optimizer's target was measured on its own 60 months, not on the window the other strategies share, so it aimed at a different volatility: at level 3 in E1 its target was {{derived.textbook_target.e1.CA.3.mean_abs_gap_points|f2}} points a year from Robo-Kit's on average in Canada, in both directions, and {{derived.textbook_target.e1.US.3.mean_gap_points|f2}} points higher in the US, and never more than {{derived.textbook_target.max_rel_gap_all|pct0}} away; the code now uses the common target, and a re-run with it leaves the textbook's E1 readings unchanged ({{derived.verify.textbook_readings_unchanged|int}} of {{derived.verify.textbook_readings|int}}; Section 6.9). Second, the intervals are equal-tailed (the bootstrap's 2.5th and 97.5th percentiles of the studentised difference), while the two-sided p inverts the symmetric interval of Ledoit and Wolf (2008); the two disagree in {{derived.intervals.disagree_count|int}} of the {{derived.intervals.rows|int}} Sharpe comparisons of E1 and E2 ({{derived.intervals.disagree_text|raw}}), and the readings use only the p-values. Third, the non-inferiority test is one-sided at 5%, as the plan wrote it, which matches a 90% interval, not the single 95% interval on which the closed-test argument for reading superiority and non-inferiority together rests (EMEA 2000); with the adjusted p held to 2.5% instead, one of the two Canadian non-inferiority readings would not hold (Section 6.2).

## 5.3 Strict point-in-time returns (E2)

E2 repeats the walk-forward without stand-ins: every series is cut at the estimation date, and each slot holds the best-scoring fund that already had 36 months of its own returns; early Decembers whose funds share fewer than 36 months are skipped. The list of funds and their scores are still today's (Section 7). A test replaces every later return, rate and exchange rate with noise and checks that the mix does not change.

## 5.4 Simulation with a known truth (E3)

The shipped pipeline runs on 500 simulated 192-month histories per world, the same paths for every method, with true parameters taken only from months up to the walk-forward's first estimation date. In world a, expected returns are the equilibrium returns, so the model is right; in world b they follow the planning returns of Section 3, so it is wrong; world c adds two volatility regimes to b, the case block resampling is meant for. Methods are scored by certainty-equivalent loss against the true constrained optimum. Resampling is dropped only if the one-sided 95% lower bound of its cost exceeds 2 basis points in both worlds b and c. Two sub-studies test the 36-month minimum history and the QIS switch: on twenty real funds, under a structured truth (their constant-correlation covariance) and an unstructured one (their sample covariance), the switch moves only if one-sided tests at $N/T$ of 0.20, 0.25 and 0.30 find QIS changing the true variance of the minimum-variance portfolio by more than 1% the same way in both truths and no test points the other way.

## 5.5 Examination before the run

The plan and its code were examined, in the manner of a registered report's Stage 1 review, by AI models from families other than the one that wrote them, since a reviewer from the same family tends to share the author's blind spots. Each examiner was briefed as a professor examining a graduate team's work from three angles, finance, statistics and numerical mathematics, and received only the code, the documents and the claim under examination: no reasoning from the authors and no other examiner's conclusions. Every finding had to quote what it concerned and was checked against the repository before it was ruled true, partly true or false (docs/DECISIONS.md).

A first round examined the optimizer itself; of nineteen findings, fourteen were ruled true and fixed with regression tests. The plan was then examined in eighteen rounds, revised after each, until a review accepted it as it stood. The examiners found, among other things, defaults that could have changed while being tested, a simulation truth estimated from months the walk-forward would later test, a reading rule that rewarded an underpowered test, missing months that would have silently stretched a holding period, and a reported Sharpe ratio that was not the one tested. All were fixed before the run.
