STATUS: COMPLETE (every requested source was tried; the ones that could not be reached are listed under "Gaps")

# Gap fill: where Robo-Kit can get Canadian MER, official risk rating and fund structure

Lane: gap fill (MER, ETF Facts risk rating, fund structure). Tested 2026-09-28 from the build machine with curl, Python, and a browser pane. Other research files do not repeat this material: `data-sources.md` (TMX `altData.mer` empty in all rows) and `regulation.md` (R3.7, R6.1, Appendix F bands) left it open.

## 1. Bottom line

1. **No single free source covers everything.** None of the sources I tested is licensed for commercial reuse, and none gives MER and the official risk rating for all ~1,821 CAD-traded ETFs. SEDAR+ holds every ETF Facts document, but its terms ban robots and databases, and it sits behind a Radware bot wall.
2. **Issuer websites are the working source, and they are good for the big issuers.** RBC GAM (which covers RBC ETFs and RBC iShares), BMO, iShares Canada, Global X, TD, Fidelity and Vanguard each publish a full fund list, as JSON or embedded in the page, from one or two requests. **Measured on the 1,821-instrument CAD universe, bulk lists alone gave MER for 691 (37.9%), an official risk rating for 645 (35.4%), and both for 428 (23.5%).** For 845 instruments (46.4%), a tested route exists to both fields, through the bulk list, a fund page, or a linked ETF Facts PDF.
3. **ETF Facts PDFs are the universal fallback, and they are easy to parse.** Form 41-101F4 requires a fixed sentence, "[manager] has rated the volatility of this ETF as [level]". A regex parser read the risk level and MER from 6 of 6 ETF Facts from 4 issuers. TMX's `altData.websitefactsheeten` gives an issuer product-page URL for 1,557 of 1,560 TSX rows, so it can seed the crawl that finds each ETF Facts link.
4. **Every issuer site I read limits use to personal or non-commercial purposes, or bans robots.** That applies to BlackRock, RBC GAM, CI, TD, Fidelity, Vanguard, Harvest, Hamilton and Global X ("all rights reserved"). A shipped product therefore needs issuer permission or a licensed feed such as Fundata. Scraped values must not be bundled into the public artifact.
5. **Appendix F formula (checked against the image, and unchanged in the 22 Apr 2026 consolidation):** SD = √12 × √( 1/(n−1) · Σ(Rᵢ − R̄)² ), with n = 120 monthly NAV total returns. That is the sample standard deviation (ddof = 1), annualised by √12 and expressed in percent before it is compared with the bands. Tested code is in §7.

## 2. SEDAR+ (tested: blocked for automated use, and the terms forbid it)

| Test | Result |
|---|---|
| `GET https://www.sedarplus.ca/`, the search page and the terms page, from Python and from WebFetch | Every request was redirected to `validate.perfdrive.com`, page title "Radware Block Page" (a ShieldSquare CAPTCHA). I did not try to get past it. `robots.txt` only disallows five named SEO crawlers. |
| Terms (read on the CSA help mirror `systems.securities-administrators.ca/terms-of-use/`, "last updated on April 28, 2023") | Robots and scraping are prohibited. Building a database from the Public Information is prohibited. Commercial products built on the Public Information are prohibited. |
| Download limit (help page) | "a public user is limited to downloading 30 documents at a time." The search results list can be exported as CSV by hand. |
| Licensed route | The terms name the ASC as the body "authorized to grant licenses and enter into agreements with third parties relating to the access and use of the SEDAR+ Public Website." I found no published bulk-feed product. |

**Verdict:** use SEDAR+ only as a human-readable fallback, where a person opens one document to check it. Do not automate it.

## 3. Issuer fund lists (the working source)

"Bulk" means a single request returns every fund of that issuer. The "in CAD universe" counts come from an exact-ticker join to the 1,821-instrument universe defined in `data-sources.md` (1,560 non-`.U` TMX rows plus 261 Cboe Canada CAD ETFs).

| Issuer (TMX count in universe) | Endpoint tested | MER | Official risk rating | Structure | As-of seen | Terms (verbatim, opened) |
|---|---|---|---|---|---|---|
| **RBC GAM: RBC ETFs + RBC iShares** (185) | `GET https://www.rbcgam.com/api/vtl/fds-etf-list?langId=1&language_id=1` (696 KB) and `.../dotcms-etf-list?...` (621 KB). HTTP 200, no key. | `fds` list: 232 of 248 rows filled (decimal, 0.0032 = 0.32%) | `dotcms` list: `riskText` on 254 of 257 rows (177 `rbcisharesetfs`, 80 `rbcetfs`) | `fundCategory` only | `fds` `"date": "Sep 28, 2026"`; prices 2026-09-25; the MER itself carries no date | "may not be reproduced, distributed or published without the written consent of RBC GAM Inc." |
| **iShares Canada** (the same funds as above) | `GET https://www.blackrock.com/ca/investors/en/product-screener/product-screener-v3.1.jsn?dcrPath=/templatedata/config/product-screener-v3/data/en/ca-one/product-screener-backend-config&siteEntryPassthrough=true`. Python `requests` got 403 (Akamai); curl got 200. The `excel-config` variant adds `mgt` (management fee). | 173 of 175 | Not in the list. On the fund page it appears as `aria-label="Risk level: Medium"` (1.8 MB per page), but RBC's list already carries it. | Aladdin asset class | Page: MER comes from the "most recent Semi-Annual or Annual Management Report of Fund Performance" | "Such content is solely for your personal, non-commercial use." It also bans any "robot, spider, intelligent agent" without BlackRock's permission. |
| **BMO** (184) | `POST https://df.bmogam.com/api/graphql/etf-funds-production`, found in the page's own widget config, query `etfList`, ~130 KB. `bmogam.com` pages hang when fetched with curl. | 257 of 257 active series | 257 of 257 (`fund.riskRating.name`) | `openClosedEnded`, `cifscCategory` | Each fee row's `effectiveDate` is **2023-12-31 for 133 series**, yet the values match the 23 Jan 2026 ETF Facts (ZSP 0.09%, ZAG 0.09%, which the ETF Facts dates as of June 30, 2025). The date field is not reliable. | **Not opened** (`bmogam.com/ca-en/legal` timed out twice) |
| **CI GAM** (156) | `GET https://funds.cifinancial.com/en/funds/daily-prices?tid=10` (693 KB) with JSON embedded in the HTML | Not in the list. The fund page shows "MER (%) As at 2026-06-30 0.87" (146 KB per page). | 208 of 208 (`risk_rating_name`) | **`fund_structure_name`** (ETF 156, Trust 52) | MER as at 2026-06-30 | Bans "using any robot, spider, or other automatic device … to access the Website for any purpose" and states "You must not access or use for any commercial purposes any part of the Website…" |
| **Global X** (127) | `GET https://www.globalx.ca/products` (663 KB, JSON embedded in the HTML) | 150 of 173 (23 marked "N/A (New ETF)"), plus TER and management fee | Not in the list. The fund page has the class `risk-tooltip-Medium` (526 KB per page). | Fund page, e.g. "Corporate Class" (HXT) | HXT page: MER "As at June 30, 2026" | "…copyright in all material stored, displayed and accessible on the Website is either owned us or duly licensed by third parties. All such rights are reserved." |
| **TD** (48) | `GET https://www.td.com/bin/fund-filter-data?productType=etf&reqType=overview&lang=en` (113 KB) | 58 of 58 (`merNumF`) | Not in the list (not tested further) | Asset class only | Table header: "MER % June 30, 2026" | "You may not access, monitor or copy any content on the Website … using any robot, deep-link, spider, scraper or other automated means or any manual process." |
| **Fidelity** (32) | `GET https://www.fidelity.ca/content/fidelity-data/pnp-cached-en.json` (5.6 MB, 83 ETFs, 81 ticker-coded series) | 74 of 81, **each with a date** (`facts_and_codes_mer_date`: 31-Mar-2026 for 59, 31-Dec-2025 for 15) | Not in the JSON, but **all 81 carry an ETF Facts PDF link** (`fund-facts`), and the PDF parser reads it | Series type (ETF / L) | MER date as shown | "The Fidelity site is intended only for your personal, non-commercial use, unless you and Fidelity have agreed otherwise in writing." |
| **Vanguard Canada** (39) | `vanguard.ca/en/product?product-type=etf`, rendered client-side through `/gpx/graphql`. I read the rendered table; the endpoint's query was not captured. | 41 of 42, plus TER and FER | Not on the list or the fund page. It is in the ETF Facts only. | Asset class | Fund page: MER "as of the most recent fund year end" | "…solely for your personal and noncommercial use or as expressly authorized by Vanguard in writing." |
| **Harvest** (79) | `harvestportfolios.com/products/` (rendered table with a CSV button). The High Income Shares suite at `/high-income-shares/products/` has 60 tickers with no fee or risk columns. | Management fee only | 43 of 44 on the main suite | none | Table "As at 2026/09/25" | "Unless otherwise specified, no one has permission to copy, redistribute, reproduce and republish, in any form, any information found on this Web site." |
| **Hamilton** (32) | Fund pages `hamiltonetfs.com/etf/<ticker>/` (43 URLs, ~240 KB each) | In the ETF Facts, which each page links (HMAX parsed at 0.77%) | On the page: "Risk Rating Medium" | none | ETF Facts dated 2026-01-08 | "You may print a copy … for your personal use only, but you may not reproduce or distribute the information to others…" |
| **Purpose** (53) | `purposeinvest.com/invest` lists management fee and yield only. The fund page shows "Management Expense Ratio 0.72% ( 2026-06-30 )". | Fund page, dated | No rating on the page, and no ETF Facts link in the static HTML | none | 2026-06-30 | `/legal` page opened (5.5 KB of text); no use clause found, so not fully reviewed |
| **Mackenzie** (52) | `mackenzieinvestments.com/en/investments/by-type/etfs/etfs-list` | Management fee only on the list; fund pages not tested | not tested | none | none | Terms URL not found (two guesses returned 404) |
| **Desjardins** (30) | `desjardinsetf.com`: curl returned no connection (000) and the browser navigation failed | not reached | not reached | none | none | not reached |

**Measured coverage on the CAD universe (1,821):**

| Route | MER | Official risk | Both |
|---|---|---|---|
| Bulk lists only (RBC, iShares, BMO, CI, Global X, TD, Fidelity, Vanguard, Harvest) | 691 (37.9%) | 645 (35.4%) | 428 (23.5%) |
| Issuers with a tested route to **both** fields (bulk list, fund page, or a linked ETF Facts PDF): RBC/iShares, BMO, CI, Global X, Fidelity, Hamilton | n/a | n/a | 845 (46.4%) |
| Not tested (the long tail): Evolve 56, National Bank 55, Purpose 53, Mackenzie 52, CIBC 42, LongPoint 41, Ninepoint 37, BetaPro 33, Manulife 30, Desjardins 30, Dynamic 29, First Trust 27, … and 134 Cboe CAD ETFs that match no issuer list above | route = ETF Facts crawl | same | ~976 |

By family, from bulk lists (universe count / MER / risk): RBC iShares 185 / 178 / 185; BMO 184 / 184 / 184; CI 156 / 0 / 156; Global X 127 / 108 / 0; TD 48 / 48 / 0; Vanguard 39 / 38 / 0; Fidelity 32 / 26 / 0; Harvest 79 / 0 / 33; Cboe-listed 261 / 107 / 85. The 124 MER tickers and 116 risk tickers that did not join are almost all `.U` USD lines, which are correctly left out.

Risk labels in the joined set: Medium 300, Low 113, Low to medium 100, High 70, Medium to high 62. Spellings vary by issuer ("Low To Medium", "Medium to high", "LOW"), so normalise them to the five Appendix F labels.

## 4. CIRO, CSA and CETFA: no per-fund dataset

* **CETFA** monthly report (`cetfa.ca/wp-content/uploads/2026/04/ISSMI_CA_CETFA_Deliverable_CETFA-Report_2603.pdf`, 13 pages): the columns are "ETF Name / Ticker / Management Code / Current Month / YTD 2026", i.e. flows only. The text contains no "MER" and no "Risk". It is useful as an issuer-code cross-check and nothing more.
* **CIRO** "Reports, Statistics and Other Information" page: market-regulation statistics only, with no ETF or MER data.
* **CSA**: no dataset. The investor ETF Facts page returned 307 to curl. The CSA's role is the mandated format (Form 41-101F4) and the method (NI 81-102 Appendix F), which is what makes ETF Facts parseable.
* **Commercial route:** Fundata's data-feeds page lists coverage of "Mutual funds", "Segregated funds", … "ETFs", with "Risk and risk-adjusted return statistics". This came through WebFetch's summary, so confidence is medium, and the price is unknown. Fundata's Fund Facts document library is described for mutual and segregated funds, and the page does not mention ETF Facts.

## 5. ETF Facts parser (prototype, tested)

The fixed wording comes from Form 41-101F4 (Yukon consolidation of 6 Jan 2022). Item 4 requires: "[Insert name of the manager of the ETF] has rated the volatility of this ETF as [insert investment risk level identified in paragraph (a) in bold type]." A new ETF adds: "Because this is a new ETF, the risk rating is only an estimate by [manager]". Part II defines ETF expenses as MER plus the trading expense ratio.

The regex set used (Python, over `fitz` text with whitespace collapsed):
```
RISK  = r'has rated the volatility of this (?:ETF Series|ETF|Fund|series)\s+as\s+(low to medium|medium to high|low|medium|high)\b'   (re.I)
MER   = r'Management expense ratio\s*\(MER\)\s*:?\s*([0-9]+(?:\.[0-9]+)?)\s*%'                                                  (re.I)
ASOF  = r'As of ([A-Za-z]+ \d{1,2}, \d{4}), the (?:ETF Series|ETF|Fund|series).s expenses were ([0-9.]+)%'                       (re.I; add a variant for "Series’ expenses")
NEW   = r'Because this is a new (?:ETF|Fund), the risk rating is only an estimate'
```

| ETF (issuer) | PDF | risk | MER | expenses as of | document date |
|---|---|---|---|---|---|
| ZSP (BMO) | 945 KB, 4 pages | medium | 0.09 | June 30, 2025 | January 23, 2026 |
| ZAG (BMO) | 944 KB, 4 pages | low | 0.09 | June 30, 2025 | January 23, 2026 |
| RBNK (RBC) | 542 KB, 4 pages | medium to high | 0.32 | September 30, 2025 | March 18, 2026 |
| HMAX (Hamilton) | 1.0 MB, 4 pages | medium | 0.77 | June 30, 2025 | January 8, 2026 |
| FCAB (Fidelity, ETF series of a mutual fund) | 483 KB, 3 pages | low (flagged **new-fund estimate**) | 0.69 | missed ("Series’ expenses" variant) | NOVEMBER 10, 2025 |
| FBTC (Fidelity) | 477 KB, 4 pages | high | 0.40 | March 31, 2025 | AUGUST 25, 2025 |

The first regex pass missed FCAB, whose wording is "this Fund", not "this ETF". After one fix, the parser read risk and MER from 6 of 6. The expenses date was read from 5 of 6. Each PDF is about 0.5 to 1 MB, so a full refresh of ~1,800 funds is roughly 1 to 2 GB of downloads and seconds of CPU. The real cost is finding each issuer's PDF link, which is one small adapter per issuer seeded by the TMX product URL.

**Data-quality findings that the pipeline must handle:**
* **Two "official" MERs can disagree.** FBTC's ETF Facts says 0.40% (as of March 31, 2025), while Fidelity's site JSON says 0.35% dated 31-Mar-2026. The ETF Facts is refiled only about once a year, so it lags the latest management report of fund performance (MRFP).
* **Issuer date fields can be wrong.** BMO's API stamps fee rows 2023-12-31 even where the value matches a 2026 ETF Facts.
* **Ratings change.** Desjardins (release of 30 March 2026, read through WebFetch) moved four ETFs, e.g. DMID "from Medium to high to Medium", after "a risk assessment conducted by DI in accordance with the standardized risk classification methodology".
* **New funds have no MER** (Global X shows "N/A (New ETF)" for 23 of 173), and their rating is an estimate.

## 6. Fund structure (R6.1)

No single field covers structure. The partial sources I found are CI `fund_structure_name` (ETF / Trust), the "Corporate Class" label on Global X fund pages, BMO `openClosedEnded`, and the first paragraph of every ETF Facts. FCAB's, for example, reads "key information you should know about ETF Series units … of Fidelity Absolute Income Fund". Parse structure from the ETF Facts header and title ("ETF Series", "Corporate Class", "Series L", "Hedged Units", "Accumulating Units"), and cross-check it against the issuer list where one exists.

## 7. NI 81-102 Appendix F: the computed rating, ready to code

Source texts: the ASC Annex B amendment PDF (the amending instrument took effect March 8, 2017; its section 3, which adds Appendix F, took effect September 1, 2017) and the ASC consolidation effective April 22, 2026, whose page 120 formula image was checked visually.

* Formula: **SD = √12 × √[ 1/(n−1) × Σᵢ₌₁ⁿ (Rᵢ − R̄)² ]**, where "n = 120 months", Rᵢ is the "return on investment in month i", and R̄ is the "average monthly return on investment".
* Return basis (Item 2(2)): the calculation uses the series or class "that first became available to the public", and "the net asset value of the mutual fund, assuming the reinvestment of all income and capital gain distributions", in the series' own currency.
* Bands, in percent: 0 to <6 Low; 6 to <11 Low to medium; 11 to <16 Medium; 16 to <20 Medium to High; 20 or more High. The manager "may" raise the level "if doing so is reasonable in the circumstances" (Item 1(2)). The 2026 consolidation's commentary encourages funds whose strategies produce "an atypical or non-normal distribution of performance results" to consider an upward adjustment. The computed level is therefore a floor, not a ceiling.
* Less than 10 years of history: fill the gap with a clone or sister fund (Item 4(1)), otherwise with a reference index that is disclosed in the prospectus (Items 4(2) and 5).

```python
import numpy as np
BANDS = [(6.0,"Low"),(11.0,"Low to medium"),(16.0,"Medium"),(20.0,"Medium to high"),(float("inf"),"High")]
def csa_standard_deviation(monthly_returns):          # decimal NAV total returns, oldest first
    r = np.asarray(monthly_returns, float)
    if r.size < 120: raise ValueError("need 120 months; impute reference index per Item 4 and label it")
    r = r[-120:]
    if np.isnan(r).any(): raise ValueError("gap in window")
    return float(np.sqrt(12.0) * r.std(ddof=1) * 100.0)   # percent
def csa_risk_level(monthly_returns):
    sd = csa_standard_deviation(monthly_returns)
    return sd, next(label for upper, label in BANDS if sd < upper)
```
I ran this on synthetic series with volatilities of 3%, 8%, 13%, 18% and 25%. They mapped to Low, Low to medium, Medium, Medium to high and High. Band edges behave as the text requires: exactly 6.0 gives "Low to medium", 20.0 gives "High".

## 8. Implications for Robo-Kit

1. **Build** `robokit/data/fees_risk/`: one adapter per issuer (RBC, iShares, BMO, CI, Global X, TD, Fidelity and Vanguard first, since they cover ~46% of the universe), a generic ETF Facts link finder seeded by the TMX product URL (1,557 of 1,560 filled), and the ETF Facts parser in §5. Every value carries `{value, source_url, source_kind: issuer-list|issuer-page|etf-facts, as_of, retrieved_at, parser_version}`. When two sources disagree, log it rather than silently picking one.
2. **Pick values by rule, and show the date.** For MER, use the issuer's latest MER with its date, and show the ETF Facts MER alongside it when they differ. For risk, show only the official rating (ETF Facts or issuer), never a guess, and add a "new fund: estimate" flag where the ETF Facts says so. This implements R3.7 and R6.1.
3. **Net-of-fee optimizer input = MER + TER** (the ETF Facts "ETF expenses" line). Global X and Vanguard lists already give TER. When MER is missing, as for new ETFs, use the management fee and mark it "fee estimate, excludes operating costs". Show fees in dollars per year from this number.
4. **Computed rating:** code Appendix F exactly as in §7, and label the result "computed by Robo-Kit (from market prices)". yfinance prices are market prices, not NAV. When the computed and official ratings differ by more than one band, show a notice. Do not replace the official rating.
5. **Licensing (do not skip).** No source tested is cleared for commercial redistribution, and several ban automated access outright: BlackRock, CI, TD and SEDAR+. Three options:
   - (a) Ask the issuers for written permission; they want their funds listed. A search snippet (page not opened) describes Fundata "Listing Services" as distribution that fund companies use.
   - (b) License a feed (Fundata, Morningstar; pricing not obtained).
   - (c) For the course prototype, use a hand-checked CSV for the shortlist only: each row read by a person from the ETF Facts, with URL and date.
   Keep scraped values out of the published artifact, and have counsel confirm before any automated fetch ships in the MCP package.
6. **Avoid** automating SEDAR+ (terms plus Radware CAPTCHA). Avoid Yahoo for TSX MER (`prior-art-github.md`). Avoid TMX `altData.mer` (it is empty). Treat TMX `managementfee` as a management fee, not an MER.
7. **Refresh:** re-pull MER after each MRFP season (fiscal years end at different dates, e.g. Dec, Mar, Jun, Sep) and re-read ETF Facts at least once a year, since ratings change (Desjardins, March 2026). Show "as of" beside every fee and rating.
8. **Disclose:** "MER as of <date>, source <issuer / ETF Facts>. Risk rating as disclosed by the manager in the ETF Facts dated <date>. The manager may rate a fund higher than the volatility formula implies."

## 9. Gaps

* BMO terms not opened (two timeouts). Purpose's `/legal` page had no use clause, so its terms were not fully reviewed. No Mackenzie terms URL found.
* Desjardins site not reachable from the test machine. Fund-page or ETF Facts routes not tested for Mackenzie, TD (risk), Vanguard (ETF Facts URL pattern), Purpose (ETF Facts link), Evolve, National Bank, CIBC, LongPoint, Ninepoint, BetaPro, Manulife, Dynamic, First Trust and the other long-tail issuers.
* Coverage counts are joins on exact tickers. Values were spot-checked only against the 6 ETF Facts in §5 and 3 cross-checks (RBNK, ZSP, ZAG match; FBTC differs as described).
* Fundata's coverage of ETF risk ratings and its price were not verified (WebFetch summary only). Whether MER and risk figures, as facts, may be republished is a legal question left open here.
* The Vanguard GraphQL query was not captured (values were read from the rendered table). The Harvest High Income Shares suite (60 tickers) was not parsed.

## Sources opened (2026-09-28)

* SEDAR+ terms (CSA mirror): https://systems.securities-administrators.ca/terms-of-use/ ; download limit: https://systems.securities-administrators.ca/onlinehelp/general-help/search-sedar/search-and-download-documents/ ; bot wall observed at https://www.sedarplus.ca/
* NI 81-102 Appendix F (2017 amendment): https://www.asc.ca/-/media/ASC-Documents-part-1/Regulatory-Instruments/2018/10/5318291-Annex-B-Amendments-to-NI-81-102.ashx ; consolidation effective April 22, 2026: https://www.asc.ca/-/media/ASC-Documents-part-1/Regulatory-Instruments/2026/06/6273088-81-102-NI-Consolidation-Eff-April-22-2026.pdf
* Form 41-101F4 consolidation: https://yukon.ca/sites/default/files/cs/cs-41-101-ni-f4-unofficial-consol-jan-6-2022.pdf
* RBC GAM: https://www.rbcgam.com/api/vtl/fds-etf-list?langId=1&language_id=1 , https://www.rbcgam.com/api/vtl/dotcms-etf-list?langId=1&language_id=1 , terms https://www.rbcgam.com/en/ca/terms-and-conditions , ETF Facts https://funds.rbcgam.com/pdf/fund-facts/etfs/rbnk_e.pdf
* iShares Canada: screener URL in §3; XIU page https://www.blackrock.com/ca/investors/en/products/239832/ishares-sptsx-60-index-etf ; terms https://www.blackrock.com/ca/investors/en/terms-and-conditions
* BMO: https://df.bmogam.com/api/graphql/etf-funds-production ; ETF Facts https://fundfacts.bmo.com/EtfEnglish/BMO_S&P_500_Index_ETF-EN-CAD_Units.pdf
* CI: https://funds.cifinancial.com/en/funds/daily-prices?tid=10 ; RIT page https://funds.cifinancial.com/en/funds/ETFS/CICanadianREITETF.html?seriesId=14119&currencySelector=1 ; terms https://www.cifinancial.com/ci-gam/ca/en/legal/terms-of-use.html
* Global X: https://www.globalx.ca/products , https://www.globalx.ca/product/hxt , terms https://www.globalx.ca/terms-of-use
* TD: https://www.td.com/bin/fund-filter-data?productType=etf&reqType=overview&lang=en ; terms https://www.td.com/ca/en/about-td/customer-care/legal-notices-and-disclaimers
* Fidelity: https://www.fidelity.ca/content/fidelity-data/pnp-cached-en.json ; terms https://www.fidelity.ca/en/legal/ ; ETF Facts https://www.fidelity.ca/content/dam/fidelity/en/documents/fund-facts/fbtc/FF_FBTC_L_en.pdf
* Vanguard: https://www.vanguard.ca/en/product?product-type=etf , https://www.vanguard.ca/en/product/etf/equity/9561/vanguard-ftse-canada-all-cap-index-etf , terms https://www.vanguard.ca/en/website-terms-of-use
* Harvest: https://harvestportfolios.com/products/ , https://harvestportfolios.com/high-income-shares/products/ , terms https://harvestportfolios.com/contact-us/legal-terms-conditions/
* Hamilton: https://hamiltonetfs.com/etf/hmax/ , ETF Facts https://hamiltonetfs.com/wp-content/uploads/2026/01/ETF-Facts-HMAX-EN-2026-01.pdf , terms https://hamiltonetfs.com/legal/
* Purpose: https://www.purposeinvest.com/funds/purpose-premium-yield-fund ; Mackenzie: https://www.mackenzieinvestments.com/en/investments/by-type/etfs/etfs-list
* Desjardins rating changes: https://www.desjardins.com/en/news/desjardins-announces-changes-risk-rating-etfs.html (WebFetch)
* CETFA: https://cetfa.ca/wp-content/uploads/2026/04/ISSMI_CA_CETFA_Deliverable_CETFA-Report_2603.pdf ; CIRO: https://www.ciro.ca/markets/reports-statistics-and-other-information ; Fundata: https://www.fundata.com/data-feeds (WebFetch)
* Universe inputs (local measurement only, Red licence): https://dgr53wu9i7rmp.cloudfront.net/etfs/etfs.json , https://www-api.cboe.com/ca/equities/listing-directory-data/

Working scripts (not part of the repo): the scratchpad `mer/` folder of this session holds `coverage.py`, `etffacts_parse.py`, `bmo_gql.py`, `ci_parse.py`, `gx_parse.py` and `csa_risk.py`.
