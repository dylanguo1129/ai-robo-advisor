# Changelog

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
