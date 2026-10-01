STATUS: COMPLETE

# Dead ETFs: where to find closed, merged and delisted funds, and their price histories

*Lane: gap fill (survivorship). Tested 2026-09-28 on Windows 11, Python 3.10, requests, pandas 2.3.3, yfinance 1.3.0, PyMuPDF. The test year is **2023**, a record year for closures in both countries. This report fills the "Delisted-ETF history ... was not researched" gap in `data-sources.md` §10. It also gives evidence for the unsourced `MIN_AUM` thresholds in `robokit/config.py` (20M CA / 50M US). The licence tiers (Green / Amber / Red) follow `data-sources.md` §1. Every count below is my own measurement unless it is attributed to a source. The raw files and scripts' outputs are in the session scratchpad (`.../scratchpad/dl/`).*

---

## 0. Bottom line (plain language)

1. **For US ETFs there is a free, publishable way to rebuild the list of dead funds.** Two SEC filings do it. The exchange files **Form 25-NSE** about 11 days before it delists a fund, and the fund trust later reports the closure in **Form N-CEN Item B.6**. In 2023 these two filings together found 189 of 213 dead ETFs using ticker matching alone. With a name-matching step added they found about 207 of 213 (97%). Both are SEC data, so they sit in the Green licence tier.
2. **For US ETFs there is also a free, publishable history of monthly returns for dead funds, starting October 2019.** Form **N-PORT** reports each fund's monthly total return (based on net asset value) for the previous three months, together with its net assets. I tested 15 randomly chosen ETFs that closed in 2023, and all 15 have these returns up to 1–3 months before they closed. N-PORT does not cover commodity pools or grantor trusts (for example the Invesco DB funds), and it has nothing before late 2019.
3. **Yahoo cannot supply dead funds.** In the same session, live controls SPY and XIU.TO downloaded fine. Dead tickers returned nothing: 0 of 19 US and 0 of 10 Canadian ETFs, with the error "possibly delisted; no timezone found". **A universe built from today's lists and priced from Yahoo is survivor-only by design.**
4. **Canada has no free, complete, machine-readable history of dead ETFs.** TSX only shows a rolling list of the 25 most recent delistings. Cboe Canada's PDF bulletins only reach back to about mid-2024 at the URL pattern I tested. Archived copies of the TMX ETF screener recovered 24 of 24 TSX-listed ETFs whose 2023 closure was announced, but 0 of 11 NEO/Cboe-listed ones. Full Canadian history needs a licensed or academic source (Norgate, CFMRC) or snapshots that we start taking now.
5. **Small funds close far more often, and the config thresholds are about right.** US: of the ETFs with average net assets under $50M in fiscal 2022, **13.0%** closed in 2023. Above $50M the rate was **1.8%**. Canada (TSX): of the ETFs under C$20M in November 2021, **23.5%** had disappeared by January 2024, against **3.8%** above that level. Young funds close more too (US: 19.2% of funds under one year old, against 1.8% of funds over ten).
6. **Several commonly used feeds give wrong answers on dead funds.** Tiingo's "ETF" label includes closed-end funds and ETNs (48 of its 234 US "ETF" end-dates in 2023). Alpha Vantage's delisted list gives old stock tickers the names of later ETFs that reused the symbol. The SEC's own annual series file keeps dead series for years. Every dead-fund record has to be checked against a second source before we use it.

---

## 1. Source scorecard

"2023 recall" is the share of the 213-fund US reference set (section 2) that a source finds. **Licence tiers:** Green means it can be republished with attribution. Red means personal or non-commercial use only, or no automated access. Paid means a commercial licence is needed. Academic means an institutional licence that cannot ship in a product.

| Source | What it gives | Depth back to 2010 | 2023 recall (US) | Dead-fund prices? | Licence |
|---|---|---|---|---|---|
| **EDGAR Form 25-NSE** (exchange notice of removal) | Fund name, trust CIK, exchange, rule, removal date; filed ~11 days ahead | Weak before ~2014. Full-text hits for "ETF" in 25-NSE: 4 (2010), 25 (2012), 51 (2014), 75 (2016), 158 (2018), 175 (2023). The 2011 quarterly indexes list 1,110 25-NSE filings and **none** from an ETF-sponsor name | **176/213 = 82.6%** (ticker-joined) | No | **Green** |
| **Form N-CEN Item B.6** `TERMINATED_ORGANIZATION` | Series ID, series name, termination month/year | N-CEN began in 2018 (I downloaded 2021Q1–2025Q1) | **153/213 = 71.8%** | No (but gives FY net assets: see §5) | **Green** |
| N-CEN ∪ 25-NSE | | | **189/213 = 88.7%** by ticker; **~207/213 (97%)** after a name join | | **Green** |
| **Form N-8F** (deregistration of a whole trust) | Whole-trust exits only, no tickers | EDGAR | 260 N-8F rows in the 2023 index (applications, notices and orders), of which 10 came from trusts that had ever reported an ETF series (6 distinct trusts) | No | **Green** |
| SEC annual series/class file (June snapshots, 2010–2026) | Series ID → class tickers | 2010+ | Poor: 110 ETF series left between the Jun-2023 and Jun-2024 files, only **12** of them were 2023 N-CEN terminations | No | **Green** |
| **Form N-PORT** `MONTHLY_TOTAL_RETURN`, `NET_ASSETS` | Monthly NAV total return per class, net assets | Oct 2019+ | n/a | **Yes, monthly NAV returns: 15/15 tested** | **Green** |
| Tiingo `supported_tickers.zip` (free, no key) | ticker, exchange, assetType, startDate, endDate | ETF end dates: 1 (2010), 3 (2011), 0 (2012), 3 (2013), 45 (2014), then 100–285/yr | **174/213 = 81.7%**, but 60 of its 234 US "ETF" 2023 end-dates are not dead ETFs | Yes per Tiingo ("latest date we have price data"); **not retrieved (needs key)** | **Red** |
| Wayback copies of Nasdaq Trader symbol files | Point-in-time `ETF=Y` lists | Captures from 2008, irregular | **185/213 = 86.9%**, precision 60% (window mismatch) | No | Red (original publisher's terms; IA terms not reviewed) |
| Alpha Vantage `LISTING_STATUS&state=delisted` | Delisted symbols with dates | Claims history | **Not testable**: the demo key only serves the documented 2014 example (6 ETFs for 2010–mid-2014, at least 2 mislabeled) | No | **Red** |
| Nasdaq Daily List | Nasdaq-listed deletions and symbol changes | 1999+ | Not tested (subscription) | No | **Paid** |
| Yahoo / yfinance | Prices | n/a | n/a | **0/19 US, 0/10 CA** | **Red** |
| EODHD `exchange-symbol-list?delisted=1` | Delisted tickers incl. `TO` | Not stated | Demo key: HTTP 403 | Paid plans | **Red / Paid** |
| Norgate Data | Survivorship-free US and TSX prices | US ETFs "commencing in 1993"; TSX since 1999 | Not tested | Yes (vendor claim) | **Paid** (licence not reviewed) |
| CRSP Survivor-Bias-Free US Mutual Fund DB | Dead funds with `ET_FLAG` (F=ETF, N=ETN) and `DEAD_FLAG` | Long | Not tested | Yes (monthly returns/NAV) | **Academic** |
| **Canada:** TSX "Recently Delisted" JSON | Last 25 delistings (TSX, all issuers) | Rolling ~2.5 months | n/a | No | **Red** |
| **Canada:** Cboe Canada corporate-action bulletins (PDF) | New listings, delistings | From ~mid-2024 at the tested URL pattern | n/a | No | **Red** |
| **Canada:** Wayback copies of TMX `etfs.json` | TSX ETF list with AUM and inception date | 4 captures (2021-11, 2024-01, 2024-05, 2025-08) | 24/24 announced TSX closures; 0/11 NEO | No | **Red** |
| **Canada:** TSX MiG monthly report | Counts only (listings, new ETF listings) | 2017+ | Count check only | No | **Red** |
| **Canada:** issuer press releases (newswire) | Tickers, delisting and termination dates | Yes | Only source that caught NEO-listed closures in my test | No | Publisher terms (facts extractable; legal review) |
| **Canada:** CFMRC/TSX Summary Information | Daily TSX trading since 1975 | Deep | Not tested; ETF and delisted coverage not stated on the page | Likely | **Academic** |

---

## 2. US test year 2023: what each source recovers

### 2.1 Method (deterministic, reproducible)
* **Form 25-NSE.** I downloaded `https://www.sec.gov/Archives/edgar/full-index/2023/QTR{1..4}/form.idx` (HTTP 200, 39–54 MB each). They list 2,282 `25-NSE` and 128 `25` filings. From issuers that are N-CEN registrants or have fund-like names, I parsed 222 25-NSE XML documents. Splitting multi-fund filings and dropping MLPs, closed-end funds and SPACs gave 242 ETF-like items. Of these, 211 map to a ticker: 205 by exact normalised name against the SEC series/class files, 4 by fuzzy match, and 2 more only because the text itself contains a ticker (47 items carry a ticker in the text). That gives 183 unique tickers.
  * Sample filing (https://www.sec.gov/Archives/edgar/data/1424958/0001143362-23-000067.txt): "NYSE Arca hereby notifies the SEC of its intention to remove the entire class of the stated securities from listing and registration on the Exchange at the opening of business on March 07, 2023". The XML carries `<descriptionClassSecurity>Direxion Daily CSI 300 China A Share Bear 1X Shares</descriptionClassSecurity>`.
  * **Lead time:** for the 176 filings with a parsable removal date, the median was **11 days** before removal (interquartile range 11–12). This makes 25-NSE the real-time signal.
  * **The rule code is not a reliable death type.** The split was 147 `12d2-2(a)(3)` ("other securities in substitution"), 90 `(a)(2)`, 4 `(a)(1)` and 1 `(b)`. NYSE Arca used `(a)(3)` for plain liquidations (AdvisorShares Drone Technology, Poseidon Dynamic Cannabis). Some filings are trust reorganisations in which the ticker survives.
* **N-CEN.** I used the quarterly data sets 2021Q1–2025Q1 (`https://www.sec.gov/files/dera/data/form-n-cen-data-sets/{q}_ncen.zip`). The readme reads: "TERMINATED_ORGANIZATION provides information for a series of the registrant terminated during the fiscal year end covered by this report, without primary key." `TERMINATION_DATE` is "Date of termination (month/year)". 662 distinct terminated series carry a 2023 date. **197** of them are ETFs, identified by `IS_ETF=Y` in any N-CEN from 2021–2025 (180) or "ETF" in the name (17). 161 of these have a ticker in the SEC series/class files; 36 show `[NULL]`.
  * **Reporting lag:** of the 197, only **38%** had been reported by the end of 2023, **78%** by 2024Q2 and 100% by 2025Q1. N-CEN confirms closures; it does not detect them early.
* **Tiingo.** `https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip` (HTTP 200, 795,773 bytes, no key) has 108,848 rows, 9,744 of them `assetType=ETF`. 234 rows are ETFs on US exchanges with a 2023 `endDate`.
* **Wayback Nasdaq diff.** The files are `otherlisted.txt` and `nasdaqlisted.txt`, captured on 2022-12-30 (`20221230181301`) and at the nearest later captures: otherlisted 2024-04-26 and nasdaqlisted 2023-09-28. There was no capture near 2024-01-01, and the CDX API returned 503/504 several times.
* **Reference set.** I took the union of N-CEN, 25-NSE and Tiingo tickers (279) and removed symbols still listed as ETFs today with the same listing (7). I kept reused tickers whose current fund started after 2023 (6). The final step kept only symbols that were `ETF=Y` in the 2022-12-30 Nasdaq directory or that the SEC sources confirmed as ETFs. The result is **213 dead US ETFs in 2023**, 8 of which launched and died within 2023. At least one entry is a rename rather than a death: BLHY became VSHY.

### 2.2 Results

| Source | Found (of 213) | Recall | False or out-of-scope hits |
|---|---|---|---|
| N-CEN B.6 (ETF series, 2023 date) | 153 | 71.8% | 7 of 161 tickers still trade today (reorganisations or reused tickers) |
| Form 25-NSE 2023 | 176 | 82.6% | 6 of 183 still trade today |
| Tiingo endDate 2023 | 174 | 81.7% | **48 flagged `ETF=N` by Nasdaq** on 2022-12-30 (closed-end funds and ETNs, e.g. `NBO,NYSE MKT,ETF,USD,2002-09-26,2023-10-20`). **11 were absent from the 2022-12-30 directory** (e.g. `GASL,NYSE ARCA,ETF,USD,2010-07-14,2023-05-12`): stale end dates or OTC prints after delisting, unresolved |
| Wayback Nasdaq diff | 185 | 86.9% | 123 of 308 "gone" symbols were not 2023 deaths: 56 have Tiingo end dates in 2024 (inside the capture window), 17 still trade today, 36 have no Tiingo record |
| **N-CEN ∪ 25-NSE (ticker join)** | **189** | **88.7%** | |
| + name join to unmapped SEC rows | **~207** | **~97%** | Ticker join missed: commodity pools (DBS, DBV, DGL), `[NULL]`-ticker N-CEN rows (SDGA, SDGS, SECD) and renamed funds (BTCR). What is left: BLHY (a rename), GRZZ, HYLD, RSXJ, SESG |

**Published totals do not match each other or my ETF-only set.** InvestmentNews (via Yahoo, 16 Jan 2024), citing Morningstar and Bloomberg Intelligence: "ETF closures hit a three-year high in 2023 with 246 funds shuttered, which is up from 147 in 2022 and 72 in 2021." A Morningstar article (HTTP 403, not opened; seen only as a search snippet) gives 244 and says these include 23 iPath ETNs. That would roughly explain the gap to my ETF-only 213, but I have not verified it. Tiingo's raw ETF end-date counts (152 in 2021, 184 in 2022) run well above the published 72 and 147, which fits its contamination with closed-end funds and ETNs.

**Before 2019 the free route is thin.** Form 25-NSE barely covers ETFs before about 2014. N-CEN starts in 2018. Tiingo's end dates are almost empty before 2014. Alpha Vantage's demo list, as of 2014-07-10, holds only 6 ETFs delisted in 2010–2014, and two of them are mislabeled: `NFS,GRANITESHARES 2X SHORT NFLX DAILY ETF ,NYSE,ETF,1997-03-06,2010-01-08,Delisted` and `PAS,GRANITESHARES 2X SHORT PANW DAILY ETF`. These are the former stocks Nationwide Financial and PepsiAmericas, carrying the names of later ETFs that reused the tickers. A 2010–2018 ETF-level US back-test that is free of survivorship bias therefore needs licensed data (Norgate, CRSP via WRDS for academic use, or Tiingo/EODHD under a commercial licence).

---

## 3. Canada test year 2023

* **The published count conflicts with exchange data.** Wealth Professional (5 Jan 2024), citing a National Bank report: "the Canadian ETF space saw a record number of 122 ETFs delisted in 2023." TSX's own MiG reports give TSX ETF listings of 929 at December 2022, 114 new ETF listings in 2023 and 989 at December 2023. That implies only **54 net TSX exits** in 2023 (65 in 2024: 989 + 127 − 1,051). MiG counts appear to be per fund, while the TMX screener lists 1,262 tickers including `.U`/`.F` classes. National Bank's figure also covers NEO/Cboe Canada. I could not reconcile the counting units.
* **TSX "Recently Delisted" JSON** `https://www.tsx.com/json/company-directory/delisted/tsx` (found in the directory page's script: `$.getJSON('/json/company-directory/'+action+'/'+exchange`) returned `{"last_updated":1790585714,"length":25,...}`. That is the 25 most recent TSX delistings of all types, 2026-07-03 to 2026-09-21, 8 of them funds or ETFs. It is only useful if we snapshot it every day from now on.
* **Cboe Canada corporate-action bulletins.** `https://cdn.cboe.com/resources/ca/corporate_actions/en/2025/Cboe_Canada_Corporate_Action_Bulletin_20251114.pdf` opened: "Cboe Canada Inc. (“Cboe Canada”) has granted final approval for the listing of ETF shares of the following ETF". I probed weekdays in each month and found 3 bulletins in Jan-2025, 1 in Jun-2024, and 0 in Jan-2024, Oct-2023 and Jun-2023. At this URL pattern the archive does not reach 2023, when the exchange was still branded NEO. The index page is rendered by JavaScript, so there is no static link list.
* **Wayback copies of TMX `etfs.json`.** The CDX index shows 4 captures. I diffed 2021-11-07 (1,076 symbols) against 2024-01-26 (1,262): **133 symbols left the list**, 12 of them under a long name that reappears on another symbol (probably renames). Recall test against 2023 terminations announced in issuer press releases:
  * Invesco Canada (newswire, 23 Jan 2023): 15 TSX tickers and 10 NEO tickers. RBC GAM (5 Jun 2023): 9 TSX tickers and RLDR on NEO. The release says units are "anticipated to be voluntarily delisted from the Toronto Stock Exchange or Neo Exchange, as the case may be".
  * **The diff recovers 24 of the 24 TSX-listed tickers and 0 of the 11 NEO-listed ones.** The TMX screener only covers TSX (see `data-sources.md` §2.1).
* **Academic and paid sources.** The CFMRC/TSX Summary Information database has "daily and monthly trading information from the Toronto Stock Exchange about listed securities", with daily data from 1975-01-02. Its page does not say whether ETFs or delisted securities are included, so this needs checking with the Queen's library. Norgate's FAQ says of TSX: "After the restructure in 1999, coverage is excellent for all of the security types covered." It does not say whether Canadian ETFs are among those types.

---

## 4. Can the dead funds' prices be retrieved?

* **Yahoo (Red): no.** I ran a random sample of 20 dead tickers from the US reference set through `yf.download(..., start="2018-01-01")`. Only NEFSX returned data, and it is a live mutual-fund class ticker that entered through the series-to-ticker join (a join bug worth noting), so the real result is **0 of 19**. For 10 dead Canadian `.TO` tickers from the TMX diff the result was 0 of 10. Controls in the same session: SPY returned 625 rows and XIU.TO returned 626. The errors read "$DBS: possibly delisted; no timezone found" and "Quote not found for symbol: BSJN".
* **SEC N-PORT (Green): yes, as monthly NAV total returns, for '40-Act funds from October 2019.**
  * The readme (https://www.sec.gov/files/nport_readme.pdf) says: "MONTHLY_TOTAL_RETURN Contains monthly total return information for each of the preceding three months" and "The N-PORT data sets consists of XML data submitted from October 2019 through current period." `FUND_REPORTED_INFO` also carries `NET_ASSETS` (Item B.1.c), which gives **point-in-time AUM**. `METHOD.md` §7 item 1 asks for exactly this.
  * **The test:** 15 randomly chosen 2023-terminated ETFs, per-filing `primary_doc.xml` via EDGAR browse by series ID. **All 15** have returns. Coverage runs from their first public filing (2019-07 to 2023-02) to 1–3 months before termination; months covered were 6–51, median 42. Example element: `<monthlyTotReturn classId="C000218049" rtn1="1.38000000" rtn2="2.32000000" rtn3="6.34000000"/>`.
  * **Operational caveat:** the EDGAR `browse-edgar` CGI returned HTTP 503 under light load. My first pass reported 8 of 15 funds as empty, which was wrong. The bridge must retry and must treat an error page as a failure, not as "no data". The bulk quarterly zips (hundreds of MB each) avoid the CGI entirely.
  * **Limits:** returns are NAV-based, not market prices. There is nothing before October 2019. Commodity pools and grantor trusts (Invesco DB funds, SESG) do not file N-PORT.
* **Tiingo (Red):** its docs define `endDate` as "The latest date we have price data available for the asset." That suggests dead-ticker prices are stored. Not retrieved, because it needs a key and I did not create an account.
* **EODHD (Red on free plans, paid commercially):** the docs say `delisted` should be "Set to 1 to return delisted tickers instead of active ones." With the demo key I got HTTP 403 for both `TO` and `US`.
* **Norgate (paid):** "Coverage is considered to be essentially complete back to late 1992" (US), and "ETF and ETN coverage is complete back to the introduction of those security types, with ETF coverage commencing in 1993." Not tested; licence not reviewed.
* **CRSP MFDB (academic):** the guide defines `ET_FLAG` as "IDENTIFIES IF A FUND IS AN ETF OR ETN: F = ETF N = ETN". The product page calls it "The Only Complete Database of Both Active and Inactive Mutual Funds". Suitable for a course back-test through WRDS, not for the shipped product.
* **GitHub:** there is no open dataset of dead ETFs with a licence. `rreichel3/US-Stock-Symbols` has 573 stars and **no licence**; its git history works as nightly snapshots of "raw data from NASDAQ list", but I did not verify that it covers ETFs. `datasets/nasdaq-listings` (87 stars, no licence) has 56 monthly commits of Nasdaq-listed securities only. `Acelogic/WayBackMachineStockScraper` (1 star, no licence) rebuilds Yahoo CSVs from Wayback, which is Red; do not use it.

---

## 5. How often do ETFs close, by size and age?

### 5.1 Own measurement: US (Green data)
Method: every ETF series with an N-CEN report for a period ending in 2022, using `MONTHLY_AVG_NET_ASSETS`; outcome = N-CEN B.6 termination dated 2023. That gives 2,762 series, of which 167 closed. Median net assets were $12.2M for the funds that closed and $127.8M for the rest.

| FY2022 avg net assets | n | closed in 2023 | rate |
|---|---|---|---|
| < $5M | 217 | 45 | 20.7% |
| $5–10M | 193 | 31 | 16.1% |
| $10–20M | 209 | 23 | 11.0% |
| $20–50M | 432 | 38 | 8.8% |
| $50–100M | 280 | 17 | 6.1% |
| $100–250M | 417 | 5 | 1.2% |
| $250M–1B | 471 | 5 | 1.1% |
| > $1B | 543 | 3 | 0.6% |

**Threshold view:** under $50M, 13.0% closed (n=1,051); at $50M or more, 1.8% closed (n=1,711). Under $20M the rate was 16.0%, against 3.2% above.

For age I used the fund's age at 2022-12-31, measured from Tiingo's first-price date; this was known for 2,327 funds. By age band: under 1 year 19.2% (n=120); 1–2 years 12.0%; 2–3 years 7.3%; 3–5 years 6.3%; 5–10 years 6.2%; over 10 years 1.8% (n=770). Size and age together:

| | age < 3 years | age ≥ 3 years |
|---|---|---|
| < $20M | 19.9% (n=292) | 14.0% (n=171) |
| $20–50M | 7.9% (n=151) | 11.9% (n=202) |
| ≥ $50M | 3.4% (n=206) | 1.7% (n=1,296) |

These results are for one year only, and N-CEN covers only '40-Act ETFs.

### 5.2 Own measurement: Canada (TSX, Red data, archived)
Method: the TMX `etfs.json` capture from 2021-11-07 gives each fund's `aum` (in its own currency) and `inceptiondate`. Outcome = the symbol is absent from the 2024-01-26 capture and is not a rename (121 funds). The window is about 26 months.

| Nov-2021 AUM | n | gone by Jan-2024 | rate |
|---|---|---|---|
| < 5M | 153 | 43 | 28.1% |
| 5–10M | 117 | 22 | 18.8% |
| 10–20M | 108 | 24 | 22.2% |
| 20–50M | 165 | 10 | 6.1% |
| 50–100M | 147 | 7 | 4.8% |
| ≥ 100M | 379 | 9 | 2.4% |

**Threshold view:** under 20M, 23.5% gone (n=378); at 20M or more, 3.8% gone (n=691). Under 50M, 18.2%; at 50M or more, 3.0%.

Age does **not** follow the US pattern here. Funds under 1 year old were gone at 15.2%, 1–5 years at 5.7–7.4%, and 5 years or older at **13.1%**. The 2023 clean-outs removed older, small products; First Asset had 14 exits, Invesco 13 and RBC 13. I could not compute dollar volume because the 2021 capture has no price field.

### 5.3 Published evidence
* Sherrill & Stark, *ETF liquidation determinants*, Journal of Empirical Finance 48 (2018) 357–373, DOI 10.1016/j.jempfin.2018.07.007 (abstract via Semantic Scholar): "Failures are more likely to occur when an ETF is small and when it is launched by a struggling family or into a struggling investment objective."
* Akhigbe, Balasubramnian & Newman, *Exchange Traded Funds and the likelihood of closure*, American Journal of Business 35(3/4), 2020, sample 1995–2018 (Emerald abstract): "the first three years are the most critical period for the survival of ETFs". They also name early performance, expense ratio and family size.
* Morningstar Australia (Mody, 26 Nov 2025) says "around 30% of ETFs launched over the past decade have shut down". It also says "Industry rule of thumb points to funds needing roughly $50 million AUM to be profitable for issuers", and, citing Sherrill & Stark: "a sample of 2,115 ETFs from 2006 to 2016 and find one in four ETFs failed (549)".
* ETF Deathwatch (Ron Rowland; criteria "since January 2011"): an ETF is added when "Average daily dollar volume for a given month is less than $100,000 for three consecutive months -or- AUM is below $5 million for three consecutive months". There is a "free pass" above $25M AUM and a six-month incubation period.

**Reading for `config.py`.** The US $50M `MIN_AUM` matches the industry profitability rule of thumb. It also sits at the point where the 2023 closure rate drops from 6–21% per year to under 2%. The Canadian C$20M threshold is where the 26-month exit rate drops from about 20–28% to about 6%. Funds between C$20M and C$50M still left at roughly twice the rate of funds above C$100M. Neither liquidity threshold (`MIN_DOLLAR_VOLUME` 50k CA / 250k US) is supported by anything I measured. The only published line I found is Deathwatch's $100k a day.

---

## 6. What Robo-Kit should build, borrow, avoid and disclose

1. **Build a US graveyard from SEC data only (Green).**
   * `robokit/data/graveyard.py` pulls the EDGAR quarterly and daily form indexes, parses `25-NSE` XML (`descriptionClassSecurity`, issuer CIK, exchange, removal date) and treats it as the *announcement*.
   * It joins N-CEN `TERMINATED_ORGANIZATION` (series ID, month) as the *confirmation*. The 38% / 78% / 100% reporting lag means a date-stamped state machine is needed, not a one-off join.
   * It adds N-8F only for whole-trust exits.
   * **Key every fund by SEC series ID, never by ticker.** Tickers are reused (IBIT, NFS, PAS) and renamed (BLHY→VSHY).
2. **Build point-in-time returns and AUM for US ETFs from N-PORT (Green).**
   * Load `MONTHLY_TOTAL_RETURN` (per class) and `FUND_REPORTED_INFO.NET_ASSETS` from the bulk quarterly zips (October 2019 onward). This gives the optimizer's monthly returns **including dead funds**, plus point-in-time AUM for the `MIN_AUM` filter. That removes the look-ahead in the 2026-snapshot AUM prior that `METHOD.md` §5 describes.
   * Commodity pools and grantor trusts need a separate route (10-K/10-Q NAV, not tested) or should be excluded and the exclusion disclosed.
3. **Start snapshots today (all Red, local only).**
   * Every day, snapshot `nasdaqlisted.txt`, `otherlisted.txt`, TMX `etfs.json`, the Cboe Canada directory API and the TSX `delisted/tsx` JSON. Also save any new Cboe Canada bulletin PDFs.
   * Store them on the user's machine (the "bring your own data" design in `data-sources.md` §0). The rolling 25-row TSX list means **each missed day can lose delistings for good.**
4. **Set the back-test history rule by market and date. The planned P3 back-tests should follow it.**
   * US, October 2019 onward: survivorship-free at ETF level with N-PORT.
   * US before October 2019, and Canada before our snapshots began: ETF-level back-tests are survivor-only. Run them on asset-class index proxies, or use licensed data (Norgate for US and TSX; CRSP or CFMRC through Queen's WRDS for the course version only). Never show a pre-2019 ETF-level back-test as if it had no survivorship bias.
   * Each back-test report should print a "graveyard" line: how many funds were in the as-of universe, how many later closed, and that their returns up to closure are included.
5. **Integrity rules (deterministic).**
   * Never trust `assetType=ETF` from Tiingo: cross-check against Nasdaq `ETF=Y` or SEC `IS_ETF`. It includes closed-end funds and ETNs.
   * Flag Tiingo end dates that fall after the symbol left the exchange directory.
   * Never use Alpha Vantage delisted names for funds that reused a ticker.
   * Treat EDGAR 503 responses as failures.
   * Do not read the 25-NSE rule code as a death type.
   * Run the series/class annual file only as a lagging cross-check. The SEC says it "includes series and classes that have ceased operation but have not yet been reclassified as inactive".
6. **Turn the thresholds into user-facing risk labels with our own numbers.**
   * Keep `MIN_AUM` (US $50M, CA C$20M), and cite §5.1 and §5.2 in `config.py`.
   * Add a "closure risk" badge for funds under 3 years old, or in the C$20–50M band, or meeting the Deathwatch rule ($5M AUM or $100k average daily volume for 3 months). The chat can explain it in one sentence, for example: "about 1 in 8 US ETFs under $50M closed within a year in 2023."
   * The liquidity thresholds stay marked "unsourced" until they are measured.
7. **Disclose, in fixed text written in code:** "Back-tests before [date] only include ETFs that still exist today, which makes them look better than reality." Also: "Small and new ETFs close more often; if an ETF closes, you get cash back and must choose a replacement." This follows `papers-robo-llm.md` E7 (survivorship can reverse the sign of reported returns).

---

## 7. Gaps

* **Canada:** there is no complete 2023 list of dead ETFs to test against. My recall test used 35 announced tickers from 2 issuers. The National Bank figure of 122 and the TSX MiG net figure of 54 could not be reconciled. I did not find a NEO or Cboe Canada history before about mid-2024. Whether CFMRC includes ETFs and delisted securities is not confirmed.
* **Paid and keyed price sources** (Tiingo, EODHD, Norgate, CRSP) were not tested for dead-fund prices, because that needs accounts I did not create. Their licence terms beyond what is quoted above were not reviewed.
* **Commodity pools and grantor trusts** (not in N-CEN or N-PORT): no free source of dead-fund NAV history was tested.
* **N-CEN before 2021Q1** was not downloaded, so N-CEN's recall for 2018–2020 is unmeasured. N-CSR and RR1 annual-return bars as a pre-2019 source were not tested.
* The 213-fund US reference set is the union of the sources being tested, so recall is relative. Funds that every source missed are invisible. The published 244–246 totals probably include ETNs (from an unopened snippet).
* The Morningstar 2023 closures article (244 closures, average age 5.4 years, average assets $54M) and the SSRN copy of Sherrill & Stark returned HTTP 403. Their figures here come from the Morningstar Australia article and the Semantic Scholar abstract respectively.
* Licence readings are a layperson's reading and need legal review. I assumed that Wayback copies carry the original publisher's terms; I did not review the Internet Archive's terms.
* Liquidity-based closure rates (dollar volume) were not measured.

---

## 8. Sources opened

SEC: EDGAR full-index `form.idx` and `company.idx` 2011 and 2023; 25-NSE filing https://www.sec.gov/Archives/edgar/data/1424958/0001143362-23-000067.txt; N-CEN data sets 2021q1–2025q1 (readme inside the zip); https://www.sec.gov/files/nport_readme.pdf; https://www.sec.gov/about/opendatasetsshtmlinvestment_company and the series/class CSVs for 2011 and 2022–2026; EDGAR full-text search (`efts.sec.gov/LATEST/search-index`); `browse-edgar` atom by series ID. Tiingo: supported_tickers.zip and https://www.tiingo.com/documentation/end-of-day. Alpha Vantage: LISTING_STATUS demo. EODHD: https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours. Nasdaq Trader: symbol directory files and https://www.nasdaqtrader.com/Trader.aspx?id=DailyListPD. Wayback: CDX API and `id_` captures. TMX: https://www.tsx.com/en/listings/current-market-statistics, the MiG December 2022, 2023 and 2024 PDFs, the TSX ETF Report Q4 2023, and `/json/company-directory/delisted/tsx`. Cboe Canada: the bulletin PDF above. Issuers: https://www.newswire.ca/news-releases/invesco-canada-announces-changes-to-its-product-line-801428421.html and https://www.rbcgam.com/ca/about-us/news-release/rbc-global-asset-management-inc-announces-the-termination-of-seven-rbc-etfs-. Press: https://finance.yahoo.com/news/etf-closures-hit-3-high-004715407.html and https://www.wealthprofessional.ca/investments/etfs/record-delistings-mar-2023-growth-for-canadian-etfs/382572. Research: https://www.emerald.com/ajb/article/35/3-4/105/26778/Exchange-Traded-Funds-and-the-likelihood-of, Semantic Scholar record for DOI 10.1016/j.jempfin.2018.07.007, https://www.morningstar.com.au/etfs/young-invested-is-your-etf-risk-failure, https://investwithanedge.com/etf-deathwatch/criteria. Vendors: https://norgatedata.com/data-package-faq.php, https://www.crsp.org/wp-content/uploads/2023/10/CRSP_US_Mutual_Funds_Guide_SAS_ASCII_R.pdf, https://indexes.morningstar.com/research-data-products/crsp-survivor-bias-free-us-mutual-fund-database, https://www.cfmrc.org/index.php/databases/, https://help.lib.uwo.ca/business/faq/68749. Not opened (HTTP 403): morningstar.com 2023 closures article, etfdb.com closed-ETF category, SSRN 3218511, ScienceDirect S0927539818300562.
