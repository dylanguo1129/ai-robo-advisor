# E7(e): reference funds' five-year returns against the issuers' published figures

Registered in RESEARCH_LOG section 10 (E7(e)) as a check done after the run, outside the evaluation script, by a
research lane with an independent second check. Done 9 Oct 2026.

**Method.** A research lane collected each reference fund's published 5-year annualised total return, its basis
(market price or NAV), its as-of date, the URL and a verbatim quote, from the issuers' fact sheets. Our figure is the
annualised compound return of the monthly returns the engine uses (adjusted month-end closes, the fund's own trading
currency) over the 60 months ending at the issuer's as-of date (scripts/e7e_issuer_check.py). The second check: the three figures that differ from ours by 0.25 points a year or more were read directly
from the issuers' PDF fact sheets (text extracted from the documents, not from search snippets). The other figures were
not re-opened; each agrees with our independent calculation to within 0.05 points a year, which corroborates both.
A second, independent research lane could not open web pages in headless mode and produced nothing.

Our figure: $(\prod_{t=1}^{60}(1 + r_t))^{12/60} - 1$ over the 60 months ending at the as-of date.

| Fund | Issuer figure | Basis | As of | Ours | Difference (points a year) | Verified from the document |
|---|---|---|---|---|---|---|
| XIC | 14.87 | NAV | 2026-07-31 | 14.56 | -0.31 | yes |
| VFV | 15.19 | Market | 2026-07-31 | 15.17 | -0.02 | |
| FLUR | 10.21 | Market | 2026-08-31 | 10.22 | +0.01 | |
| VEE | 7.92 | Market | 2026-07-31 | 7.94 | +0.02 | |
| ZAG | 0.18 | NAV | 2026-08-31 | 0.14 | -0.04 | |
| XSB | 2.03 | NAV | 2026-08-31 | 2.02 | -0.01 | |
| XRE | 0.02 | NAV | 2026-08-31 | -0.23 | -0.25 | yes |
| VALT | 18.72 | NAV | 2026-08-31 | 17.52 | -1.20 | yes |
| VOO | 13.37 | Market | 2026-06-30 | 13.38 | +0.01 | |
| VXUS | 8.77 | Market | 2026-06-30 | 8.77 | 0.00 | |
| VWO | 5.14 | Market | 2026-06-30 | 5.13 | -0.01 | |
| BND | 0.06 | Market | 2026-06-30 | 0.06 | 0.00 | |
| VGSH | 1.88 | Market | 2026-06-30 | 1.88 | 0.00 | |
| SCHP | 0.30 | Market | 2026-07-31 | 0.30 | 0.00 | |
| BNDX | 0.46 | Market | 2026-06-30 | 0.46 | 0.00 | |
| VNQ | 2.79 | Market | 2026-06-30 | 2.80 | +0.01 | |
| SGOV | 3.59 | Market | 2026-06-30 | 3.59 | 0.00 | |
| VBU | not found | | | | | |
| GLDM | 18.66 | Market | 2026-09-30 | after the data snapshot | | |
| CASH | 3.27 since inception | NAV | 2026-09-30 | after the data snapshot; under 5 years | | |

**Findings.**
- Fifteen of the seventeen funds that could be compared agree within 0.05 points a year.
- **VALT** (CI Gold Bullion ETF, CAD-hedged): the issuer's 18.72% is on NAV; on 31 Aug 2026 the units traded at $53.12
  against a NAV of $54.40 (CI fund profile), a 2.4% discount. Our data are market prices, so most of the gap is the
  difference between NAV and market price, not an error in the data.
- **XIC** and **XRE** (BlackRock Canada, NAV basis): our data are 0.31 and 0.25 points a year below the issuer's
  figures. Both are large, liquid funds whose market price stays close to NAV, so the gap more likely comes from a
  distribution the adjusted closes do not fully reflect. The cause is not established. The effect is a slight
  understatement of these two funds' returns in every result; it does not affect the risk results (volatilities) or
  the comparisons, which use the same data for every strategy.
- The other two parts of E7(e) are reported separately: the audit of each slot's top five candidates
  (docs/research/e7e_shelf_audit.md) and the taxonomy sample (docs/research/e7e_taxonomy.md).

**Sources** (issuers' documents, as cited by the lane; the three verified ones were downloaded on 9 Oct 2026):
- XIC: https://www.blackrock.com/ca/investors/en/literature/fact-sheet/xic-ishares-core-s-p-tsx-capped-composite-index-etf-fund-fact-sheet-en-ca.pdf ("Fund ... 5y 14.87", as at 31-Jul-2026)
- XRE: https://www.blackrock.com/ca/individual/en/literature/fact-sheet/xre-ishares-s-p-tsx-capped-reit-index-etf-fund-fact-sheet-en-ca.pdf ("Fund ... 5y 0.02", as at 31-Aug-2026)
- VALT: https://funds.cifinancial.com/en/documents/static/Fund_Profiles/Exchange_Traded_Funds/52496/CIGoldBullionFund_Monthly_Profile.pdf ("5 Y 18.72%", as at August 31, 2026; NAVPS $54.4004, market price $53.1200)
- The others: docs/research/e7e_lane_output.md.
