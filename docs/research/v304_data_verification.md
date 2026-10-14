# The data checked against independent sources (3.0.4, 12 Oct 2026)

Every number the engine reads comes from three scripts: listings and fund facts, monthly prices, and rates. This
note checks what they stored against sources that do not share their code, and the values derived from them
against a second implementation. The scripts are in `scripts/dataverify/`; their outputs go to
`data/v2/dataverify/` (local data, like the rest of `data/v2/`).

## Summary

| What | Checked against | Result |
|---|---|---|
| Monthly total returns (`close_monthly.pkl`) | Daily adjusted closes from the same source, month-ends taken here (`price_check.py`): the 637 eligible Canadian funds, every stand-in, the first five candidates of every US slot and CAD=X | 707 series, 88,535 months; 704 series agree within 0.5% in every month. The three others are explained below |
| USD/CAD (`usdcad_monthly.pkl`, Yahoo CAD=X) | Bank of Canada FXUSDCAD, month-end, 2017-2026 | Mean absolute difference 0.21%, maximum 0.73% (timing: the Bank's rate is set at 16:30 ET). SPY converted with either: 15.79% against 15.80% a year, volatility 13.01% against 12.89% |
| Bank of Canada series (`context_monthly.pkl`) | A fresh download from the Valet API | Policy rate, 3-month T-bill, 2-year and 10-year yields: identical in every month to August 2026. September 2026 differs because the snapshot was taken on the 28th, before the month's last readings (the data note discloses this) |
| History months, 1-, 3- and 5-year returns, 3-year volatility, maximum drawdown (`universe.pkl`) | A second implementation from the stored closes (`verify_stats.py`) | 7,792 funds: identical (largest difference 4e-16) |
| The eligibility screen | Re-implemented from the written thresholds | The same 2,635 eligible funds (637 Canadian, 1,998 US) |
| MER, assets, first price, returns, volatility (Canadian funds) | The team data layer's dataset (github.com/shreyajane23/robokit-data, export of 10 Oct 2026), fetched and computed by separate code (`anna_compare.py`) | MER: 1,238 of 1,250 within 0.02 points; the other 12 are mostly unit slips in the data layer (100x). 3-year returns: correlation 0.993. The other differences are explained below |
| MER of the reference funds | The issuers' own pages, read by two independent lookups with URL and quote (`data/issuer_mer.csv`) | 33 funds: 26 equal; 7 differ by 0.01 or 0.02 points, where the issuer had published a new fiscal year's figure. The issuers' figures are used from 3.0.4 |

## The exceptions, and the rulings

| Finding | Ruling |
|---|---|
| ZLH.TO, September 2021: one month 4.1% apart | The daily series is wrong: it has a -4.6% step on 16 Sep 2021 with no distribution and a flat market, and its earlier prices are rescaled. The stored monthly series has no step |
| CJP.NE, March and April 2013: 1.6% apart, offsetting | Yahoo's monthly bar closed March at 7.74 against the last daily close of 7.85; two months of 211, offsetting. No change |
| CAD=X: 27 months more than 0.5% apart between monthly bars and daily closes | Both are 0.21% from the Bank of Canada on average; timing, not error. No change |
| 100 Canadian funds whose price history starts more than two months before the data layer's inception date | The data layer's date is wrong: it is Yahoo's profile date (ZLB.TO 2026-08-31, CASH.TO 2026-05-08), while TMX's listing date matches our first price month. 3.0.4 takes `rk_inception` and fund age from TMX's date wherever there is one |
| 302 funds whose data-layer inception is earlier than TMX's | Mostly a mutual fund's own start before its ETF series was listed; the ETF series' date is the one that matches its prices |
| Assets: 171 Canadian funds more than 1.5x apart | Mostly the data layer's figure in thousands or a fund's total over all series, ours the ETF series. No eligible fund changes: one fund excluded only for size (VOLX: 19.75M ours, 20.4M theirs) and one eligible fund (HLIT: 21.4M, 18.2M) sit at the threshold either way |
| 3-year volatility: correlation 0.695 with the data layer | Its volatility uses daily prices and, for 1-year funds, a 1-year window; ours, monthly returns over 36 months, is reproduced exactly from prices verified above |
| QCN.TO and QCE.TO at 0.04% | Correct: Mackenzie's annual report gives 0.04% |
| PFLS.TO at 4.01% | Correct: the latest ETF Facts (May 2026) gives 4.01% including performance fees; one lookup found the 2024 document (6.48%) |
| HXS, VALT, VBU, VDU, VEE, VFV, XHY: 0.01-0.02 points from the issuer | The issuer's new figure is used (VFV 0.08%, VEE 0.24%, VBU 0.21%, VALT 0.18%, among the default funds) |

## Effect

The default mixes are unchanged: an MER does not enter the optimization, and no slot's reference fund changes. The
fee figures and the projections after fees move: in the Optimizer Report, the level-3 fee falls from $12 to $11 per
$10,000 (0.12% to 0.11%), the level-2 fee from $11 to $10, and level 2's bad year from -4.1% to -4.0%. Every other
reported number is unchanged.
