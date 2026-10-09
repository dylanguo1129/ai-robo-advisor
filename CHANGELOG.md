# Changelog

## 3.0.1 (October 2026)

A second bug hunt after the registered run (docs/DECISIONS.md, 53 findings, regression tests in
tests/test_v3_bug_hunt.py). A verification re-run of the whole evaluation with this version (output/v3_verify,
scripts/v3_verify_rerun.py) leaves Robo-Kit's own results and every benchmark but the textbook optimizer unchanged.

- Requests: unknown MCP arguments refused; `level` and `relax_limits` on the MCP tool; contradictory inputs refused
  (a fund long and short against itself, own weights on an excluded fund); unmatched exclusions, unused minimums and
  inputs that own weights ignore are named in notes; strict types and bounds in both validators and every tool.
- Numerics: the zero-risk-aversion fill keeps the joint cap on own picks; dropping tiny weights never rescales a fund
  past its cap; QIS falls back to constant-correlation shrinkage on a rank-deficient sample; one-fund sample
  covariance; the calibration labels a proven jump correctly and, with a view, reports the delivered volatility.
- The two engines agree on the hedge for a caller's slot list, crisis peers (real histories only), rounding in
  checks, explanations and fees, and unit counts.
- Rebalancer: no sale of more units than held, reserve funding, no orders under the minimum after trimming, notes
  that match the orders, drift reported with band trades off, null inputs and costs of 100% refused.
- Fund labels and the swap gate: option- and futures-based funds kept out of core slots, word-stem theme rules,
  long listing names for generic or damaged ones, 'Ultra' short-term bond funds no longer read as leveraged (37
  funds eligible), PEY, BITW and VI.TO labelled correctly, the ESG shelf keeps every slot.
- Evaluation code: the symmetric studentised interval beside the registered equal-tailed one; the textbook
  benchmark aims at the common target; the static mix fails closed; E7(b) in portfolio currency. The paper
  discloses the registered intervals, the textbook target and the one-sided 5% non-inferiority test.

## 3.0.0 (October 2026)

Engine
- Risk aversion is calibrated on the mix the client receives (resampled, minimum position applied, the same draws at
  every step): bracket, then Illinois regula falsi; every result is within 0.005 percentage points of the target, a
  proven jump of the minimum-position rule, or a bound, with its evidence recorded (both engines).
- Exact projection onto the capped simplex and the exact largest eigenvalue for the step size; solvers fail closed
  without a convergence certificate.
- One random generator (mulberry32) in Python and the browser; QIS in the browser; resampled weights now match.
- One request validator; limits that cannot all hold are refused, or relaxed on request in a fixed, recorded order.
- Fund swaps must pass the slot's own rule (hedged or not) and a like-for-like label: no option- or futures-based
  fund, and no fund labelled narrow when the slot's fund is broad. A stock fund is labelled broad only when its name
  names a whole-market index and nothing narrower (after the run; docs/research/e7e_taxonomy.md). The page offers
  only alternatives the gate accepts.
- Data-integrity screen: 14 funds whose monthly return doubled or halved while their peers did not are not eligible.
- Projections use 5,000 paths (raised from 2,000 by the evaluation's registered precision rule).

Implementation layer
- Rebalancer: cash flows first, tolerance bands with a destination, whole units, minimum order, residual cash,
  estimated cost and a liquidity flag (both engines).
- NI 81-102 Appendix F risk rating of every mix.
- Opt-in suitability checks; the level policy is unchanged.

Evaluation and documentation
- A pre-registered evaluation (scripts/run_v3_evaluation.py; plan in docs/RESEARCH_LOG.md sections 9-11), examined
  in eighteen rounds before it ran; results in output/v3/results.json, the first run archived in output/v3_run1/.
- docs/DECISIONS.md: every design decision with its source, proof or test, and every examiner finding with its ruling.
- docs/paper: the research paper, built from the results by scripts/paper.
- docs/MODEL_CARD.md.
