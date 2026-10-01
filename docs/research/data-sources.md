STATUS: COMPLETE

# The data bridge: sources for the v2 universe, prices, fundamentals, macro, news and geopolitics

*Lane: data bridge. Tested 2026-09-28 from a Windows 11 machine with Python 3.10, requests 2.32.5, pandas 2.3.3 and yfinance 1.3.0 (the latest yfinance release is 1.7.0, published 2026-08-26). `docs/METHOD.md` §3.1 covers the prototype's data hygiene (Yahoo adjusted closes, 36-month minimum, `integrity_report`), and `README.md` "Hand-off to the dataset" lists the fields the optimizer needs. This report adds what those documents leave out: where each field comes from for the full CAD and US universes, whether the endpoint works today, and whether its licence allows a public product. Every "HTTP" line below is a request I made on 2026-09-28. Every quote was copied from the page or file I opened. Items quoted through the WebFetch summariser rather than raw HTML are marked (WF) and carry medium confidence. Probe scripts and raw downloads are in the session scratchpad (`.../scratchpad/ds/`: `probe.py`, `grab.py`, `t1.py`, `t2.py`). Nothing here is legal advice. Every licence call is a flag for counsel to check.*

---

## 0. Bottom line (plain language)

1. **Both universes can be built for free, and every source was tested and works.** Canada: TMX's ETF-screener JSON (1,805 TSX instruments, rich metadata) plus the Cboe Canada listing API (289 ETF instruments) gives about 1,811–1,821 CAD-traded ETF instruments. US: the Nasdaq Trader symbol files give 5,738 ETF symbols, and SEC N-CEN, the SEC risk/return dataset and N-PORT add leverage flags, expense ratios and holdings.
2. **Being free to download is not the same as being free to publish.** The best Canadian sources (TMX, Cboe), the Nasdaq screener, Yahoo/yfinance, Alpha Vantage, EODHD's free tier and Tiingo's free tier are all licensed for personal, non-commercial or internal use only. Yahoo also forbids automated collection outright. None of their raw data should go into a public, shippable artifact.
3. **Some sources can be published with attribution:** SEC/EDGAR data, public-domain FRED series (not the copyrighted ones), Bank of Canada, Statistics Canada, GDELT, the Caldara-Iacoviello GPR index and the EPU indices.
4. **Recommended design ("bring your own data", the same idea as "bring your own token"):** the public artifact ships code and redistributable data only. Restricted data is fetched on the user's own machine by the MCP server or CLI, under that user's own access and keys, and is never bundled or re-served. A commercial launch that serves prices to users needs a paid licence. I did not verify commercial prices.

---

## 1. Licence traffic light

| Tier | Sources | What Robo-Kit may do |
|---|---|---|
| **Green** (redistribute with attribution) | SEC EDGAR (N-CEN, RR1, N-PORT, XBRL, ticker files, full-text search), FRED public-domain series (e.g. DGS10), Bank of Canada Valet, Statistics Canada WDS, GDELT, GPR (CC BY), EPU (CC BY 4.0), VADER (MIT) | Bundle in the public artifact. Store a citation string per series. |
| **Amber** (usable, but conditions apply) | FRED copyrighted series (SP500, VIXCLS, ICE BofA spreads), Damodaran industry data (loose rules, but upstream data is licensed), Loughran-McDonald (academic free, commercial licence needed), issuer holdings files (terms not reviewed) | Fetch locally, or get permission or a licence. Do not bundle. |
| **Red** (personal / non-commercial only, or automated access prohibited) | TMX Money / etfs.json, Cboe Canada website API, Nasdaq Trader and api.nasdaq.com, Yahoo Finance / yfinance, Alpha Vantage free, EODHD free, Tiingo free, Stooq (bot challenge) | Runs only on the user's machine under their own access. Never re-served from a Robo-Kit server or embedded in the published page. Commercial launch needs a paid licence. |

---

## 2. (a) Canadian-listed ETFs tradeable in CAD

### 2.1 TMX ETF-screener dataset: the richest free Canadian source (Red licence)
* **URL:** `https://dgr53wu9i7rmp.cloudfront.net/etfs/etfs.json`. This is the undocumented JSON behind money.tmx.com's ETF screener. OpenBB's TMX provider uses the same URL (`openbb_tmx/utils/helpers.py`, line 389). OpenBB's LICENSE reads "All files in this repository are licensed under the GNU Affero General Public License v3.0", so borrow the endpoint knowledge, not the code.
* **Test:** HTTP 200, 7,573,041 bytes, 1.3 s, **1,805 rows**, no key. First record: `"symbol":"AAPU","shortname":"SavvyLong (2X) A",...,"currency":"CAD","inceptiondate":"2025-06-03",...,"investmentstyle":"Trading-Leveraged Equity"`.
* **Fields (58 top-level):** symbol, longname, fundfamily, currency, inceptiondate, aum, managementfee, investmentstyle, assetclass (numeric code), prospectobjective, distributionyeld, dividendfrequency, pricetoearnings, pricetobook, beta1y–beta20y, totalreturn 1m–10y and since inception, avgdailyvolume, `top10holdings`, `top10holdingsummary`, `sectors`, `regions`, esg, plus `altData` (assetclassen, fundfamilyen, indexfunden, liquidityrating, mer, regionen, websitefactsheeten, alternativeversions, …).
* **Fill rates measured:** aum 1,804/1,805; managementfee 1,608; inceptiondate 1,613; investmentstyle 1,609; top10holdings, sectors and regions 1,805. **`altData.mer` was empty in all 1,805 rows**, so MER must come from somewhere else (see gaps). 56 issuers; the largest are RBC iShares 216, BMO ETF 208 and CI 196.
* **Coverage:** TSX only. 1,804 of the 1,805 symbols appear in the TSX company directory, and **none of the 289 Cboe Canada ETF symbols appear in it**.
* **Currency quirks (integrity rule needed):** `currency` = CAD 1,386, USD 226, "-" 192. Cross-tab against the `.U` suffix: ("-", no .U) 164, ("-", .U) 28, (USD, no .U) 10, (CAD, .U) 1. So neither the field nor the suffix is reliable on its own. The screener has to combine them and send conflicts to review.
* **Leverage/inverse and hedging:** `investmentstyle` values include "Trading-Leveraged Equity" (25), "Trading-Inverse Equity" (10) and "Leverage Strategy" (36). A regex over name and style flags 103 rows as leveraged or inverse, and 96 names contain "hedg".
* **Licence:** https://www.tmx.com/en/terms-of-use (covers tmx.com and tmxmoney.com): "TMX grants to you a limited non-exclusive, non-transferable license to view and print the material on the Websites for your non-commercial or personal use only." The next clause bars redistribution and derivative works of the "information, data".

### 2.2 Cboe Canada listing directory API (Red licence)
* **URL:** `https://www-api.cboe.com/ca/equities/listing-directory-data/` (found through adanos-software/free-ticker-database's `sources.json`).
* **Test:** HTTP 200, 83,539 bytes, 0.2 s, 398 securities: 289 `etf`, 84 CDRs, 21 common equity, and a few others. ETF currency: CAD 261, USD 28. Sample: `{"symbol":"SCGG","name":"STARLIGHT GLOBAL GROWTH FUND","currency":"CAD","security":"etf","security_sub_type":"etf","marketcap":1083000.0000,...}`.
* **Fields:** symbol, name, currency, security, security_sub_type, marketcap, last, changepcnt, volume. It has **no issuer, MER, inception or asset class**, so those must be enriched from issuer data or Yahoo.
* **Official alternative (not tested):** Cboe Canada reference-data files. From https://cdn.cboe.com/resources/membership/Cboe_Canada_Reference_Data_Files.pdf: "Reports are published in a comma-separated values (“csv”) format. Delivery options include SFTP or download from our website portal (HTTPS)." They include a Daily Closing Price Report with weighted closing prices for ETFs. Access terms are not published on that page.
* **Licence:** https://www.cboe.com/terms: "You may view, print and download one copy of the Materials for your personal non-commercial use in connection with products and services offered by Cboe".

### 2.3 Other Canadian candidates
* **TSX company directory JSON** `https://www.tsx.com/json/company-directory/search/tsx/%5E*`: HTTP 200, 322,316 bytes, `"length":2286` issuers with instrument lists. It has **no ETF flag**. It is useful as a cross-check that a symbol is listed and for its `.U` / `.B` variants. TMX terms apply.
* **CETFA** (cetfa.ca): the page opened once and showed "51 ETF providers across two Canadian exchanges" plus a comparison tool. I found no downloadable data. A second request hit a Cloudflare "Attention Required" page. Not a data source.
* **Yahoo** carries `.TO` tickers. `https://query1.finance.yahoo.com/v8/finance/chart/XIU.TO` returned HTTP 200 with `"currency":"CAD",...,"instrumentType":"ETF"`. Yahoo has no listing endpoint, and its licence is Red (section 4.1).
* **Existing open aggregations:** FinanceDatabase (MIT) has fewer Canadian rows than TMX plus Cboe (count from the prior-art lane, not re-measured here). free-ticker-database (MIT, 25 stars) itself labels both TMX sources `"commercial_use_status": "review_required"` and `"raw_redistribution_allowed": false`.

**Recommended Canadian universe build:** CAD universe = (TMX etfs.json rows whose resolved currency is CAD) ∪ (Cboe CA rows with `security=="etf"` and `currency=="CAD"`). As measured: 1,560 non-`.U` TSX instruments (10 of them carry `currency=USD` and need review) + 261 Cboe CAD instruments = **about 1,821 CAD-traded instruments** (about 1,811 once those 10 are removed). Collapse share classes (`.B`, `.F`, `.U`) to one fund and keep the CAD line.

---

## 3. (b) US-listed ETFs

### 3.1 Nasdaq Trader symbol directory: the complete list (Red licence)
* **URLs:** `https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt` and `.../otherlisted.txt` (also on ftp.nasdaqtrader.com/symboldirectory).
* **Test:** both HTTP 200 (349,721 and 542,331 bytes, 0.3 s). The footer reads `File Creation Time: 0928202612:11`. With `ETF=="Y"` and `Test Issue=="N"`: Nasdaq-listed 1,289; other exchanges 4,449 (Arca "P" 2,723, Cboe BZX "Z" 1,642, NYSE "N" 79, "F" 5). **Total 5,738.**
* **Definition** (https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs): "ETF Identifies whether the security is an exchange traded fund (ETF)." and "The symbol directory files are updated periodically through-out each day." Checked: grantor trusts and commodity pools are flagged Y (GLD, IBIT, USO). ETNs are flagged N (VXX). The files have **no leverage, inverse or expense fields**.
* **Licence** (https://www.nasdaqtrader.com/Trader.aspx?id=CopyDisclaimMain): content may not be copied or distributed without consent "except for one temporary copy in a single computer's memory and one unaltered permanent copy to be used by the viewer for personal and non-commercial use only."
* **api.nasdaq.com screener** `https://api.nasdaq.com/api/screener/etf?download=true`: HTTP 200, 1,155,314 bytes, 5,254 rows (symbol, name, last price, 1-yr % change). It includes ETNs (VXX), and 501 symbol-directory ETFs are missing from it. https://www.nasdaq.com/legal forbids "any process, whether automated or manual, to capture data or content from the Service". **Do not use it.**

### 3.2 SEC data: the licence-clean enrichment layer (Green)
* **Policy** (https://www.sec.gov/privacy): "Information presented on sec.gov is considered public information and may be copied or further distributed by users of the web site without the SEC’s permission." **Fair access** (https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data): "Current max request rate: 10 requests/second." Requests must declare a User-Agent with contact details.
* **Ticker map** `https://www.sec.gov/files/company_tickers_mf.json`: HTTP 200, 1,234,039 bytes, 28,560 rows `["cik","seriesId","classId","symbol"]`. It maps 4,538 of the 5,738 US ETFs; `company_tickers_exchange.json` adds 191 more (the '33-Act trusts are not in the mutual-fund file: GLD and IBIT are missing, SPY too). **1,009 ETFs are in neither file** (e.g. AAPY, ACLO, AFIF), so SEC-based enrichment will have holes.
* **Form N-CEN datasets** (quarterly zips, e.g. `https://www.sec.gov/files/dera/data/form-n-cen-data-sets/2026q2_ncen.zip`): HTTP 200, 8.4 MB. `FUND_REPORTED_INFO.tsv` has 2,335 funds, 696 with `IS_ETF=Y`, and carries `IS_INDEX`, **`IS_MULTI_INVERSE_INDEX`**, `IS_FUND_OF_FUND` and tracking-difference fields (`ETF.tsv`). The readme says: "IS_MULTI_INVERSE_INDEX 'Y' if fundType = 'Multi Inverse Index'". In 2026Q2, 5 ETFs carry the flag (KraneShares 2x Long BABA, …). N-CEN is an annual form spread across quarters, so **four quarters are needed for full coverage**. Its `MANAGEMENT_FEE` / `NET_OPERATING_EXPENSES` fields were empty for ETFs.
* **Risk/return summary (RR1) datasets** (`.../mutual-fund-prospectus-risk/return-summary-data-sets/2026q2_rr1.zip`): HTTP 200, 81.7 MB. `num.tsv` tags include `ExpensesOverAssets` (11,732 facts), `NetExpensesOverAssets` (5,917), `ManagementFeesOverAssets`, `PortfolioTurnoverRate` and 1/5/10-year average annual returns. Facts are keyed by `series`, with share-class detail in `otherdims`. One quarter covered 934 of 4,538 SEC-mapped ETFs (AGG: `NetExpensesOverAssets` 0.0003). Vanguard series return several class values, so the ETF share class has to be parsed out of `otherdims`. Use four quarters.
* **N-PORT holdings:** `https://data.sec.gov/submissions/CIK0001100663.json` returned HTTP 200. The latest iShares Trust NPORT-P was filed 2026-09-25 for period 2026-07-31, and `primary_doc.xml` returned HTTP 200 with 257 `<invstOrSec>` rows (name, lei, cusip, isin, balance, valUSD, **pctVal**, assetCat, issuerCat, **invCountry**). That is about an 8-week lag. Quarterly bulk zips are also available (`2026q2_nport.zip`, 440,699,889 bytes, HEAD 200).
* **Existing tool:** dgunning/edgartools (MIT, 2,754 stars, pushed 2026-09-28) parses "N-PORT fund portfolios" and N-CEN, and says it needs "no keys, no subscriptions".

---

## 4. (c) Adjusted price history at scale

| Source | Test (2026-09-28) | Free limits | Canada? | Licence |
|---|---|---|---|---|
| **Yahoo chart API via yfinance** | `yf.download` of 10 tickers (5 `.TO`), `period="max"`: shape (7056, 50) in 0.6 s. XIC.TO from 2001-02-22, ZAG.TO from 2010-01-25. Raw v8 chart with a browser UA: HTTP 200. **With a python-requests UA: HTTP 429 "Edge: Too Many Requests".** `Ticker.history("XIU.TO")` and `funds_data` raised `YFRateLimitError` even after a 20 s pause | Undocumented; throttled per request pattern | Yes (`.TO`, `.NE`) | **Red**, see 4.1 |
| **Stooq** | Browser UA: HTTP 200 HTML "This site requires JavaScript to verify your browser." plus a proof-of-work script. Python UA: HTTP 404 | n/a | n/a | **Do not use.** It is a bot-detection gate, and bypassing it is off-limits |
| **Alpha Vantage** | Demo key: `TIME_SERIES_DAILY` IBM HTTP 200 (last 2026-09-25) | "25 API requests per day" (free) | Yes, `.TRT` suffix (docs: "SHOP.TRT") | **Red.** Also, `TIME_SERIES_DAILY_ADJUSTED` is marked "this is a premium API function" |
| **EODHD** | Demo `VTI.US`: HTTP 200 with `adjusted_close`. Demo `XIU.TO`: **HTTP 403** (the demo key covers only a few symbols) | "Once you have registered, you will be granted 20 free API calls per day." | Yes (`.TO`), paid | **Red** on free/personal plans |
| **Tiingo** | No key: HTTP 403 `{"detail":"Please supply a token"}`. **Not tested with a key** | (WF) "Max Requests Per Day: 1000", "Unique Symbols per Month: 500" | not verified | **Red** (WF): "Internal use means you may not display or share the data with another person or organization" |

### 4.1 Yahoo / yfinance terms
* yfinance README (https://raw.githubusercontent.com/ranaroussi/yfinance/main/README.md): "It's an open-source tool that uses Yahoo's publicly available APIs, and is intended for research and educational purposes." and "Remember - the Yahoo! finance API is intended for personal use only."
* Yahoo terms (https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) prohibit users to "access or collect data, or attempt to access or collect data, from our Services using any automated means, devices, programs, algorithms or methodologies, including but not limited to robots, spiders, scrapers". They also say: "Unless otherwise expressly stated, you may not access or reuse the Services, or any portion thereof, for any commercial purpose."
* Throttling is a known, recurring problem: issue #2480, "[0.2.59] YFRateLimitError: Too Many Requests. Rate limited." (38 comments), https://github.com/ranaroussi/yfinance/issues/2480. My test reproduced it on the quoteSummary path (`funds_data`), and a raw quoteSummary call without a crumb returned HTTP 401 "Invalid Crumb".
* Alpha Vantage terms (PDF served at https://www.alphavantage.co/terms_of_service/) grant use "for personal, non-commercial use, unless you and Alpha Vantage have agreed otherwise in writing". Their "commercial use" test includes providing information "as part of any type of commercial activity that allows individuals or entities other than User to access information".
* EODHD pricing (https://eodhd.com/pricing), next to the personal plans: "Personal use For commercial use, choose Startups & Enterprise Data Solution Plan".

---

## 5. (d) ETF fundamentals, holdings look-through, sector fundamentals

* **TMX etfs.json** (Red) already holds, for Canadian ETFs, top-10 holdings, sector and region weights, P/E, P/B, yield and betas (section 2.1).
* **yfinance `funds_data`** (description, fund_overview, fund_operations with expense ratio, top_holdings, sector_weightings): **not verified**, because every call raised `YFRateLimitError` on 2026-09-28. Treat it as unreliable.
* **Alpha Vantage `ETF_PROFILE`** (Red), demo QQQ: HTTP 200, `"net_assets": "489000000000","net_expense_ratio": "0.0018",...,"leveraged": "NO","sectors": [...]` plus holdings. At 25 calls per day on the free plan it cannot cover the universe.
* **SEC N-PORT** (Green): US-registered ETFs only. It is the licence-clean look-through: pctVal, assetCat, invCountry. Canadian ETFs do not file N-PORT.
* **Issuer holdings files:** SSGA `https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx` returned HTTP 200 (54,415-byte xlsx). The iShares US `...1467271812596.ajax?fileType=csv&fileName=IVV_holdings` URL returned an HTML page instead of the CSV. The iShares Canada XIU holdings URL returned **HTTP 403 Access Denied** (Akamai). Issuer files are fragile and each has its own terms (not reviewed). Use them only for spot checks.
* **Sector fundamentals: Damodaran** `https://pages.stern.nyu.edu/~adamodar/pc/datasets/pedata.xls`: HTTP 200. Sheet "Industry Averages" (Number of firms, % money-losing, Current/Trailing/Forward PE), dated 2026-01-05. Update cadence: "The data, with a couple of exceptions, gets updated once a year, at the start of the year". Usage rules (https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datahistory.html): "I want the data to be widely used and to be a help, rather than a hindrance." But "I draw on many: Bloomberg, Morningstar, Capital IQ and Compustat", so treat it as Amber: use the industry aggregates with attribution and do not republish the files.
* **Sector fundamentals from SEC XBRL** (Green): `https://data.sec.gov/api/xbrl/frames/us-gaap/NetIncomeLoss/USD/CY2025.json` returned HTTP 200, 865,408 bytes, `"pts":5670`. Combined with N-PORT weights, this can build look-through earnings aggregates for US holdings, with no licence risk.

---

## 6. (e) Macro

* **FRED CSV, no key:** `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd=2026-09-01` returned HTTP 200 in 0.17 s with curl's default UA (`observation_date,DGS10 / 2026-09-01,4.79 ...`) and 0.6 s with python-requests. **With a browser-like UA ("Mozilla/5.0 …") it timed out after 40–60 s**, both for the CSV and for https://fred.stlouisfed.org/legal/. The bridge must send a plain, non-browser UA. The JSON API needs a key: HTTP 400 "Variable api_key is not set."
* **FRED licence is per series.** DGS10 page: "Public Domain: Citation Requested". SP500 page: "Reproduction of S&P 500 in any form is prohibited except with the prior written permission of S&P Dow Jones Indices LLC". VIXCLS: "Copyright, 2016, Chicago Board Options Exchange, Inc." BAMLH0A0HYM2 (ICE): "you are not authorized or permitted to publish, distribute or otherwise furnish Top Level Data to any third-party without prior written approval of ICE Data." FRED legal (WF): "Before using data with a copyright notice for anything other than your own personal use, you must contact the data owner to obtain permission".
* **Bank of Canada Valet:** `https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=3` returned HTTP 200 in 0.1 s, and the payload itself carries `"terms": {"url": "https://www.bankofcanada.ca/terms/"}`. Group endpoint `.../observations/group/bond_yields_benchmark/json?recent=1`: HTTP 200. The series catalogue `/valet/lists/series/json` is 3.6 MB. Terms (https://www.bankofcanada.ca/terms/): "the Bank permits you to freely use, copy, distribute and transmit its website content under the following terms: 1.1. Attribution You must attribute the Bank of Canada as the source". If served inside a paid product, buyers must be told the data is free on the BoC site. Section 2.3 excludes third-party content. Rate limits: not documented on any page I could open (the docs page is JS-rendered).
* **Statistics Canada WDS:** a POST to `https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods` with vector 41690973 returned HTTP 200 (CPI, table 18100004: 2026-07 = 169.9, released 2026-08-17; 2026-08 = 169.8). Limits (https://www.statcan.gc.ca/en/developers/wds/user-guide): "Server limits of 50 requests per second with a individual IP address limit of 25 requests per second." Tables lock from midnight until 8:30 ET (HTTP 409). Licence (https://www.statcan.gc.ca/en/reference/licence): "Statistics Canada grants you a worldwide, royalty-free, non-exclusive licence to: use, reproduce, publish, freely distribute, or sell the Information". Each use needs a "Source: Statistics Canada, …" notice. **Green.**

---

## 7. (f) News and sentiment

* **GDELT DOC 2.0:** `https://api.gdeltproject.org/api/v2/doc/doc?query=...&mode=artlist&maxrecords=5&format=json` returned HTTP 200 in **18.5 s** (a CBC article dated 20260828 among the results). `mode=timelinetone&timespan=7d` returned HTTP 200 in 15.7 s with hourly "Average Tone" values (e.g. -1.449). An immediate second call returned **HTTP 429**: "Please limit requests to one every 5 seconds or contact GDELT for larger queries." Licence (https://www.gdeltproject.org/about.html): datasets "are available for unlimited and unrestricted use for any academic, commercial, or governmental use of any kind without fee". Any use "must include a citation to the GDELT Project and a link to this website". The article text belongs to the publishers, so show headline + link only.
* **RSS, all HTTP 200:** Yahoo `https://feeds.finance.yahoo.com/rss/2.0/headline?s=SPY` (carries `<copyright>Copyright (c) 2026 Yahoo Inc. All rights reserved.</copyright>`, so it is Red); BoC `https://www.bankofcanada.ca/content_type/press-releases/feed/` (Green); Fed `https://www.federalreserve.gov/feeds/press_all.xml` (US government; terms not reviewed); SEC `https://www.sec.gov/news/pressreleases.rss` (Green).
* **yfinance `Ticker.news`:** SPY returned 10 items; XIU.TO returned 0. Red.
* **SEC EDGAR full-text search:** `https://efts.sec.gov/LATEST/search-index?q=%22tariff%22&forms=8-K&dateRange=custom&startdt=2026-09-01&enddt=2026-09-25` returned HTTP 200, `"hits":{"total":{"value":147,...}}`. Green. It is undocumented JSON behind the EDGAR FTS UI, subject to the 10 req/s rule.
* **Alpha Vantage `NEWS_SENTIMENT`** demo: HTTP 200, 50 items with a stated scale ("x <= -0.35: Bearish; ... x >= 0.35: Bullish"). Red (personal use; 25 calls/day).
* **Loughran-McDonald dictionary** (https://sraf.nd.edu/loughranmcdonald-master-dictionary/, updated March 2026, file 1993–2025): "The dictionary/sentiment lists are free for use in academic research. For commercial licenses, please contact us". **It cannot ship in a commercial product without a licence.**
* **Permissive alternatives:** cjhutto/vaderSentiment (MIT, 5,076 stars) is general-purpose, not finance-tuned. ProsusAI/finBERT GitHub repo is Apache-2.0 (2,239 stars, last push 2022-09-09), but the Hugging Face model record returned no licence tag, so check the weights' licence before shipping. GDELT tone is precomputed and commercially usable.

---

## 8. (g) Geopolitics and policy uncertainty

* **Caldara–Iacoviello GPR:** monthly `https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls` returned HTTP 200, 2.7 MB, 1,520 rows × 115 columns (GPR, GPRT threats, GPRA acts, **GPRC_CAN, GPRC_USA**, …), last month 2026-08. Daily `.../data_gpr_daily_recent.xls` returned HTTP 200, last row 2026-09-28 (GPRD 232.3, plus MA7 and MA30). Page (https://www.matteoiacoviello.com/gpr.htm): monthly data "updated at the beginning of each month", daily "updated every Monday". Licence: "completely open access under the Creative Commons BY license". Cite Caldara & Iacoviello (2022, AER). Reading `.xls` needs `xlrd`. **Green.**
* **Economic Policy Uncertainty:** US daily `https://www.policyuncertainty.com/media/All_Daily_Policy_Data.csv` returned HTTP 200 (1985-01-01 to 2026-09-27; last value 628.37). Canada monthly `.../Canada_Policy_Uncertainty_Data.xlsx` returned HTTP 200 (to 2026-08, 576.84). The daily US index is also on FRED as `USEPUINDXD`, and the CSV returned HTTP 200. Licence (https://www.policyuncertainty.com/): "This work is licensed under a Creative Commons Attribution 4.0 International License". **Green.**

---

## 9. Proposed data bridge (what to build)

1. **Two-tier catalog.** `data/catalog.yaml` has one entry per source: URL, method, UA, rate limit, licence tier, citation string and last-verified date. The build that produces the public artifact bundle **fails if any Red or Amber series is in it**, which enforces the licence rule mechanically instead of by convention.
2. **Universe builder (deterministic).** CA: TMX etfs.json ∪ Cboe CA API → resolve currency (field + `.U` rule + review queue) → collapse share classes. US: Nasdaq symbol directory (`ETF=Y`, `Test Issue=N`) → join SEC ticker map → N-CEN flags (index, multi/inverse, fund-of-funds) → RR1 expense ratio → N-PORT look-through. The leverage/inverse flag is the OR of the N-CEN flag, TMX style ∈ {Trading-Leveraged, Trading-Inverse, Leverage Strategy} and a name regex. **Leveraged and inverse ETFs are excluded from optimisation by default.**
3. **Prices.** For the prototype and local use: yfinance ≥ 1.7 `download` in batches, with an on-disk cache, exponential back-off on `YFRateLimitError`, and never a browser UA spoof. For a commercial launch: a licensed EOD vendor with `.TO` coverage (EODHD commercial or TMX Datalinx; price quotes not obtained). The adapter interface stays the same.
4. **Integrity checks, extending `integrity_report`:** row counts against the previous snapshot (flag a >5% drop); symbol present in the exchange list on the as-of date; currency consistency; adjusted-vs-raw ratio jumps without a matching distribution; stale runs; cross-source spot check (e.g. 20 random tickers against a second source) with tolerance; N-PORT `pctVal` sums within 95–105%; freshness SLA per source (GPR monthly ≤ 35 days, EPU daily ≤ 3 days, etc.).
5. **Politeness rules in code:** SEC ≤ 10 req/s with a declared UA; GDELT ≥ 5 s between calls, 30 s timeout; StatCan ≤ 25 req/s and retry on 409 before 8:30 ET; FRED with a plain UA; Stooq and Yahoo quoteSummary never scraped around their gates.
6. **Provenance on every number.** Each value the chat shows carries `{source, series_id, as_of, licence_tier}`, so the assistant can cite rather than invent, and the UI can print "Source: Statistics Canada, table 18100004, 2026-08" automatically.
7. **Survivorship.** Snapshot the universe files daily into the repo's data store so later backtests know which ETFs existed on each date. The current lists alone would bias backtests toward survivors.

---

## 10. Gaps

* **No free source of Canadian ETF MER found.** `altData.mer` was empty in all TMX rows, and only `managementfee` (1,608/1,805) is filled. ETF Facts PDFs (issuer sites / SEDAR+) were not tested.
* **No free Canadian list or price source licensed for public redistribution was found.** A commercial licence is needed; prices unverified.
* Tiingo not tested with a key. Its limits and terms come from the WebFetch summary only.
* yfinance `funds_data` could not be verified (rate-limited all session). Behaviour on yfinance 1.7.0 was not tested (1.3.0 was installed).
* iShares (US and CA), BMO and Vanguard Canada holdings files not obtained or tested. Issuer terms not reviewed.
* Delisted-ETF history (for survivorship-free backtests) was not researched.
* Bank of Canada Valet rate limits are undocumented in what I could open. The Federal Reserve RSS terms were not reviewed.
* The Hugging Face licence for FinBERT weights was not established.
* About 1,009 US ETFs have no SEC ticker mapping. Their cause (new launches versus missing class tickers) was not investigated.
* All licence readings are a layperson's reading of the quoted text and need legal review before launch.
