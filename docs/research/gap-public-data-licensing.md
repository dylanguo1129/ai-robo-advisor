STATUS: COMPLETE

# What the public web artifact may legally carry: vendor prices and terms, issuer downloads, and the law on facts and derived statistics

*Lane: gap fill (public data licensing). Researched 2026-09-28. This extends `docs/research/data-sources.md`, which rated every Canadian listing and price source Red (TMX, Cboe Canada website, Yahoo) and obtained no commercial price. That report's licence quotes for Yahoo, TMX, Cboe, Nasdaq, Alpha Vantage, SEC, FRED, Bank of Canada and StatCan are not repeated here. Every price and clause below was copied from a page or PDF I opened on 2026-09-28 (raw HTML through Python `requests`, or rendered in a browser when the page needs JavaScript). Tests I ran myself are marked "Test". Probe files are in the session scratchpad (`.../scratchpad/lic/`). I did not create any vendor account, so no paid-key or trial-key coverage test was possible; only public demo keys and public files were tested. Nothing here is legal advice; every legal reading is a flag for counsel.*

---

## 0. Bottom line (plain language)

1. **The data file the web page ships today should not be published to other people.** `web/robokit_web_data.json` contains 127 monthly returns for each of the 20 Canadian ETFs (2016-02 to 2026-08), computed from Yahoo prices. A full return series can be turned back into a price history, so vendors treat it as the price data itself (Tiingo, TMX and Intrinio all say this in their terms; section 5). Yahoo's terms forbid automated collection in the first place (quoted in `data-sources.md`).
2. **Copyright is not the problem; contracts are.** In both the US (*Feist*) and Canada (*CCH*, *Tele-Direct*), bare facts such as a ticker, a fund name, an exchange, a price, or a volatility computed by a standard formula are not protected by copyright. But the website and API terms the team accepted are contracts. Courts in both countries enforce them against people who knew about them (*ProCD*, *Century 21 v. Rogers*; *Nguyen* on notice). The team documented those terms in `data-sources.md`, so it cannot claim it had no notice.
3. **US: a free, licence-clean path exists.** SEC Form N-PORT filings carry each fund's monthly total return (Items B.5.a-b), and SEC data is public information. SPY has 28 public quarterly N-PORT filings covering periods 2019-09-30 to 2026-06-30, which gives about 84 monthly returns. Coverage gaps: nothing before mid-2019, and no grantor trusts or commodity pools (GLD, IBIT) or ETNs.
4. **US: the cheapest paid path is Tiingo.** Its commercial plan ($50/month) comes with an explicit "Derived Products" clause. That clause lets you publish volatilities, correlations, model outputs and aggregate back-test statistics, but not return series. Its display licence costs $250/month for start-ups. **Tiingo has no Canadian coverage.** I tested this: its public ticker file has zero TSX or Cboe Canada rows.
5. **Canada: no source found with a published price that allows public display.** EODHD (Custom plan "from $399/mo", quote needed), FMP (Enterprise, "Contact Us"), Intrinio (Canadian data "via our trusted data partners", quote needed), Barchart ("start at $500/month", a 2021 help article) and TMX Datalinx all require a negotiated licence. TMX sells an end-of-day file for CAD 127–762/month, but only for the buyer's own use. Cboe Canada's exchange fees are low: free for real-time display on public websites, $375/month for non-real-time distribution. But they cover only Cboe Canada's own trading data, and a data agreement must be signed first.
6. **Minimum licence for a free public launch:** US = **none**, if the page uses SEC N-PORT returns and SEC listing maps. Canada = **a written licence** from a Canadian-coverage vendor, or permission from TMX. Until one exists, Canadian numbers stay out of the published page and are computed on the user's own machine through the MCP server or CLI ("bring your own data").
7. **The ETF issuers do not help.** SSGA publishes full NAV history as a spreadsheet (Test: SPY, 5,744 daily rows, 2003-12-01 to 2026-09-25), but BlackRock, Vanguard (US and Canada) and SSGA all limit their site content to personal, non-commercial use or require written consent.

---

## 1. What the page ships now, and why it matters

| Field in `web/robokit_web_data.json` | Content (checked 2026-09-28) | Reconstructs the source data? | Can it go in a shared artifact? |
|---|---|---|---|
| `returns_monthly`, `dates` | 127 × 20 monthly returns, 2016-02 to 2026-08, from Yahoo adjusted closes | **Yes.** A complete sequence can be chained back into a price index | No (Yahoo collection terms; every vendor's reconstructability rule, section 5) |
| `reference.sigma`, `mu_excess`, `cov_shrinkage` | Covariance matrix and expected returns | No (20×20 aggregate) | Copyright allows it. The contract does not when the input is Yahoo, because collecting it breached Yahoo's terms. It is fine when the input is SEC data or Tiingo paid data under clause 1.6(c) |
| `hist` | Annualized return and volatility per ETF | No (one number per fund over the whole window) | Same as above |
| `meta` (name, issuer, MER, AUM) | From `etf_info_yf.csv` (Yahoo) and hand entry | Names and issuers are facts; AUM comes from Yahoo | Facts yes (section 6). The Yahoo-sourced AUM falls under Yahoo's terms |
| `prior_weights`, optimizer outputs | Robo-Kit's own computation | No | Yes. These are Robo-Kit's own work, subject to the input licence (Massive's "investment strategy" clause, section 3.4) |

---

## 2. Cost-and-terms table (vendors covering, or claiming to cover, both markets)

Prices are as published on 2026-09-28, in USD unless marked. "Derived stats" means whether volatility, correlations or weights computed from the data may be shown publicly.

| Vendor / plan | Published price | Canada (.TO / .NE) | Public display of raw data | Derived stats shown publicly | Source opened |
|---|---|---|---|---|---|
| **EODHD** personal (EOD All World) | $19.99/mo; All-in-one $99.99/mo | Claims TO and NEO exchanges. Test: demo key returned **403** for `exchange-symbol-list/TO`, `/NEO`, `eod/XIU.TO`, `eod/ZEB.NEO` | Prohibited | Prohibited ("original or repackaged form") | eodhd.com/pricing, /financial-apis/terms-conditions |
| EODHD commercial Internal Use / Enterprise / Custom | $399/mo ($3,990/yr) / $2,499/mo ($24,990/yr) / "from $399.00 /mo", quote | as above | Internal: no. Custom: "partially download" allowed | Not stated; needs the Data Services Agreement | eodhd.com/commercial-pricing |
| **Tiingo** Power (individual) / Commercial | $30/mo / $50/mo ($499/yr) | **None.** Test: 108,848 tickers, 0 TSX or NEO rows | "Internal Use Only" | **Yes, if not reconstructable** (ToS 1.6(c)) | tiingo.com/about/pricing, app.tiingo.com/tos |
| Tiingo EOD + IEX Redistribution | $250/mo start-ups; $500/mo enterprise | None | "Display Redistribution" | Yes | tiingo.com/products/end-of-day-stock-price-data |
| **FMP** Premium (personal) | $49/mo billed annually ("UK and Canada Coverage"); Ultimate $99/mo | Claimed on Premium. Test: `apikey=demo` returned **401** | Needs a "Data Display and Licensing Agreement" | **No** ("contained in or derived from") | site.financialmodelingprep.com/pricing-plans, /terms-of-service |
| FMP Enterprise | "Contact Us" | Claimed | "Commercial - Display and Redistribution" | By agreement | same |
| **Massive (ex-Polygon)** Stocks Advanced / Stocks Business | $199/mo individual / $2,499/mo business | **US only** ("US Coverage") | Business: may reach "Edge Users" | Derivative "investment strategy" needs a licence | massive.com/pricing, /business, /legal/businesses-terms-of-service |
| **Intrinio** Individual / Startup / Enterprise | $150/mo / $333→$666→$999/mo / "$1,250 /mo+" | US in plans. Canada "via our trusted data partners" (quote) | Individual: no. Startup: "Commercial Use and Display Rights" | Display licence needed even for AI or transformed output | intrinio.com/pricing, about.intrinio.com/terms |
| **Barchart OnDemand** | "start at $500/month" (help article modified 2021-09-20) | TMX exchanges per search snippet only (**not opened**) | **Terms not opened** (bot challenge, HTTP 202) | Unknown | help.barchart.com article 252001 |
| **Databento** US Equities Standard / Plus / Unlimited | $199/mo / $1,500/mo licence fees / $4,000/mo | **US only.** US equities history "8+ years" | Plus: "External distribution"; most datasets redistributable "after 24 hours" | Per dataset (pass-through) | databento.com/pricing |
| **TMX Datalinx** (exchange) | Delayed TL1/CL1 distribution CAD 570/mo; derived-data licence CAD 2,172/mo; EOD "Equities Trading Summary" CAD 762/mo daily or CAD 127/mo monthly | TSX/TSXV (not Cboe Canada) | Delayed data may **not** go to a "third party website"; purchased files are "for your own use" | Separate derived-data licence (for real-time) | tmxinfoservices.com resources 460, 400, 91; tmxwebstore.com/faq |
| **Cboe Canada** (exchange) | Digital media (public website, real-time): **Free**; non-real-time distribution NEO-L **$375/mo**, NEO-N/NEO-D free; non-display analysis $500/mo (NEO-L, NEO-N) | Cboe Canada books only | Allowed under the Data Agreement | Not addressed in the fee schedule | cdn.cboe.com/.../cboe-canada-data-fee-schedule-en.pdf (dated 02/01/2025) |
| **Morningstar** | No published price ("Connect with us") | Not stated | By licence | By licence | morningstar.com/business/products/data |

---

## 3. Vendor details: verbatim clauses and tests

### 3.1 EODHD
* **Commercial prices** (https://eodhd.com/commercial-pricing): "Internal Use $ 399.00 /mo. $ 3990.00 /year Enterprise $ 2499.00 /mo. $ 24990.00 /year Custom from $399.00 /mo." Display on the Internal plan: "Displaying the data or sharing it with individuals outside your company is not permissible under this package." End-user downloads: "Can my users/clients partially download the data? Absolutely. This feature is available with the Custom plan."
* **Terms** (https://eodhd.com/financial-apis/terms-conditions): non-professional users are prohibited from "Selling, reselling, retransmitting, redistributing, displaying, or granting access to the Information or Services, whether in its original or repackaged form." "Repackaged" reaches derived tables.
* **Commercial onboarding** (https://eodhd.com/financial-apis/commercial-vs-personal-license-use/): "We can onboard you as a commercial user in as little as 3 business days." EODHD reports commercial users to exchanges.
* **Provenance contradiction (ask in the RFQ):** the commercial FAQ says "We procure end-of-day (EOD) and delayed data through direct contracts with various exchanges, including Nasdaq Cloud API for USA data", but the site-wide footer says "We are not using exchanges data feeds for the pricing data, we are using OTC, peer to peer trades and trading platforms over 100+ sources".
* **Coverage claim** (https://eodhd.com/list-of-stock-markets): "NEO Exchange NEO / NEOE TSX Venture Exchange V / XTSX Toronto Exchange TO / XTSE". **Test:** the public `demo` key returned HTTP 403 "Forbidden" on all Canadian endpoints, so coverage was not verified.
* **Useful for "bring your own data":** EODHD runs its own MCP server with an OAuth version for Claude (https://eodhd.com/financial-apis/mcp-server-for-financial-data-by-eodhd): "v2 https://mcp.eodhd.com/v2/mcp OAuth 2.1 (built-in OAuth server) Claude Desktop and other clients with native OAuth support". A user can connect their own EODHD account next to Robo-Kit's MCP.

### 3.2 Tiingo (the only vendor with a clear derived-data rule)
* **Prices** (https://www.tiingo.com/about/pricing): "It is simply $30/month (or $300/year) for individuals and $50/month (or $499/year) for internal commercial use." Display (https://www.tiingo.com/products/end-of-day-stock-price-data): "$250/month for startups $500/month for enterprise Includes Both End-of-Day Prices and IEX".
* **Coverage** (same page): "80,000+ tickers (US Equities, ETFs, Mutual Funds, ...)". **Test:** `https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip` returned HTTP 200 (795,773 bytes, 108,848 rows). Exchanges: NMFQS, PINK, NASDAQ, NYSE, SHE, SHG, OTC tiers, BATS, NYSE ARCA, AMEX, LSE (11 rows). Currencies: USD, CNY, HKD, AUD. **No TSX/NEO rows, no CAD.** XIU, XIC, ZEB and VFV are absent. Against `data/raw` Nasdaq Trader ETFs (5,738), 5,729 symbols appear in some form and 5,286 appear as active ETFs (a ticker-string match only, not a security-ID match). There are 2,135 ETF rows with an end date before 2026, which could help survivorship-free US back-tests.
* **Terms** (https://app.tiingo.com/tos/, "Last Updated Date: August 5th, 2026"):
  * 7.3: "All data via the API is for internal consumption only." "Redistribution is only available upon special request and permission, and comes with additional fees."
  * 1.6(a), free and trial plans: "you may not write, save, archive, back up, or otherwise retain Tiingo Data in any persistent or durable storage." The free tier therefore cannot feed a cached data bridge, even for personal use.
  * 1.6(c), derived products: "you may create, retain, use, and distribute a Derived Product without separate written approval only if the Derived Product at all times satisfies both of the following requirements". The two requirements: (i) it is not a substitute for the data, and (ii) it cannot be reverse-engineered or reconstructed. Listed as potentially permitted: "aggregated statistics calculated across multiple instruments or time periods, such as averages, medians, volatility measures, correlations, percentiles, or distributions", plus rankings, signals and "model parameters". Listed as prohibited: "returns, differences, ratios, or other calculations supplied with an anchor, reference value, key, lookup table, or sufficiently complete sequence that permits reconstruction of underlying Tiingo Data". Also: "Derived Products that satisfy this Section may be retained after your subscription ends; Tiingo Data may not."

### 3.3 Financial Modeling Prep (FMP)
* **Prices** (https://site.financialmodelingprep.com/pricing-plans): Starter "$19 .00 /mo. billed annually" (US); Premium "$49 .00 /mo. billed annually" with "UK and Canada Coverage"; Ultimate $99/mo with "Global Coverage". Commercial: "ENTERPRISE ... Display and Redistribution*", price "Contact Us". Page note: "Displaying or redistributing data sourced from FMP requires a specific Data Display and Licensing Agreement with FMP."
* **Terms** (https://site.financialmodelingprep.com/terms-of-service, "Last updated: August 1, 2023"): 2.2.2 "customers are prohibited from showcasing FMP Services or Data on platforms including but not limited to websites, blogs, software products, or applications designed for utilization by multiple individuals, irrespective of whether such usage is complimentary or paid". 2.6.1 bars providing "data or information contained in or derived from The Services, to any third party". **Derived statistics are covered.** 6.2 requires destroying derived data on termination.
* **Test:** `apikey=demo` returned HTTP 401 "Invalid API KEY" for AAPL, XIU.TO and ZEB.NE, so no free coverage test was possible.

### 3.4 Massive (formerly Polygon.io)
* **Prices:** individual "Stocks Advanced ... $199 /month Individual use only" (https://massive.com/pricing). Business (https://massive.com/business): "Stocks Business Perfect for getting up and running instantly. $2,499 /month Billed monthly Sign up US Coverage Unlimited API Calls 20+ Years Historical Data No Exchange Fees or Approvals". Start-ups: "Qualifying startups can get 25% or more off their first year". Its TMX partner dataset is a "Corporate event calendar", not prices.
* **Terms** (https://massive.com/legal/businesses-terms-of-service, "Last Updated: September 2, 2025"): customers may not make Information available "to anyone other than Customer, its Authorized Users, or its Edge Users". "Edge Users" means "individuals or entities that are users of Customer's products and services", so display to app users is inside the grant. But clause (j) bars using "the Information to create derivative works (including, without limitation, any index, indicative value, net asset value, investment product, financial contract, (including, without limitation, contracts for difference or spread betting), settlement value or investment strategy) based on the Information unless licensed to do so". **Optimized portfolios are arguably an "investment strategy",** so this needs explicit licence wording.

### 3.5 Intrinio
* **Prices** (https://intrinio.com/pricing): Individual "$150 /mo" with "No redistribution or display 1 seat license". "Startup AI-Ready, Commercial use $333 /mo to start" with "Commercial Use and Display Rights Business-wide license" and "6 mo at $333, 6 mo at $666, $999 thereafter". Enterprise "$1,250 /mo+". The plan data feeds are "US EOD & Historical Data for Stocks".
* **Canada** (https://intrinio.com/real-time-prices): "We can also provide real-time prices from any US or Canadian exchange via our trusted data partners." Custom, not priced.
* **Terms** (https://about.intrinio.com/terms, "Effective Date: June 3, 2026"): "Display" covers "any external presentation, publication, or making available to any third party through any means, including websites, applications, dashboards, APIs". The AI clause matters directly for a chat product. Intrinio counts as redistribution "(b) transmission of Intrinio Data to any third-party AI model provider, large language model API, or externally hosted machine learning service, regardless of whether the resulting outputs are used internally". Its guidance adds: "AI-generated output does not automatically qualify as 'derived' or exempt from display licensing."

### 3.6 Barchart
* Price (https://help.barchart.com/support/solutions/articles/252001-api-inquiry-response, "Modified on: Mon, 20 Sep, 2021"): "Barchart OnDemand API's start at $500/month". This price is five years old.
* The barchart.com product, FAQ and terms pages returned HTTP 202 with an empty body (a bot challenge) to both scripted and WebFetch requests, and the browser tool refused the domain. **Terms not opened.** The TSX coverage claim comes from a search snippet only (low confidence).

### 3.7 Databento
* **Prices** (https://databento.com/pricing, US equities tab): Standard "$199 per month" with "No license fees"; Plus "$1,500 license fees per month Annual contract required" including "External distribution"; Unlimited "$4,000 license fees per month". Coverage "45 venues", history "8+ years", all US.
* **Redistribution FAQ:** "Your redistribution rights depend on the dataset. Databento doesn't apply any redistribution restrictions. However, for each dataset, we have to pass through the licensing restrictions from the original publisher." and "Most of our datasets can be redistributed internally or externally after 24 hours."
* **Fit:** no Canada, and about 8 years of history is shorter than the 10-year window Robo-Kit uses.

### 3.8 Morningstar
* https://www.morningstar.com/business/products/data: "Our licensed data gives clients independent, comprehensive, and timely data and research they can use to empower investor success. Connect with us". No price or public licence text was found. Treat it as an enterprise quote.

---

## 4. The Canadian exchanges themselves

### 4.1 TMX Datalinx (TSX, TSXV)
* **Price list** (https://www.tmxinfoservices.com/resource/en/460, "Effective Date: August 12, 2026"; tables read from the rendered PDF): Delayed TL1/CL1 distribution CAD 570/month. Real-time TL1/CL1 external distribution CAD 3,421/month. "Use of real-time TL1/CL1 and/or TL2/CL2 market data for creation and distribution of derived data (see note 13)" CAD 2,172/month. Stored data for historical reference CAD 1,329/month. Note 13: "This license fee is for the creation of original works which are based in whole or in part from the Market Data that (a) cannot be reverse-engineered to recreate the Market Data, and/or (b) is not a reasonable facsimile of the Market Data." Note 2 says TMX treats anything "derived from or based on" its data as receipt of market data.
* **Delayed-data exhibit** (https://www.tmxinfoservices.com/resource/en/400, version 2026-01-01): the distributor must "acknowledge that you are not permitted to distribute Delayed Market Data to a third party website", and must carry a "15 minutes delayed" disclaimer when distributing outside its own organization.
* **End-of-day files** (Historical Market Data Product Catalogue, https://www.tmxinfoservices.com/resource/en/91): the Equities Trading Summary "Includes essential end of day trading information for all listed securities. History is available back to September 1998 for Toronto Stock Exchange." TSX subscription CAD 762.00/month (daily) or CAD 127.00/month (monthly). Ad hoc: 1 day CAD 47, 1 month CAD 163.
* **Use restriction** (https://www.tmxwebstore.com/faq): "No, unless you obtain specific permission from TMX Datalinx to do so, the data you purchase is for your own use and is not to be redistributed to any other party in any other format."
* **Reading:** a CAD 127/month monthly file can feed Robo-Kit's own calculations. Publishing anything built from it needs written TMX permission, and the price for that is unknown.

### 4.2 Cboe Canada
* **Data fee schedule** (https://cdn.cboe.com/resources/membership/cboe-canada-data-fee-schedule-en.pdf, dated 02/01/2025): "Cboe Canada supports digital media licensing for public Website distribution of real-time Data. No data licensing fees are payable at this time." It lists Free for both Listed and Other Traded Securities. The "DISTRIBUTION FEE FOR NON-REAL TIME CBOE CANADA DATA" is a flat $375 for NEO-L and free for NEO-N, NEO-D and MATCHNow. The non-display fee for "analysis usage" is $500 for NEO-L and NEO-N. All fees are "governed by the Cboe Global Markets Global Data Agreement". Historical data falls under a separate "Cboe Canada Historical Data Agreement" (not opened).
* **Reading:** licence fees are low, but they cover only trades on Cboe Canada's books. They do not cover TSX consolidated prices, and a data agreement plus a feed is still required. This is **not** a practical 10-year history source for the full CAD universe.

---

## 5. (b) ETF issuers: downloads exist, reuse rights do not

| Issuer | Download test (2026-09-28) | Site terms (verbatim) |
|---|---|---|
| State Street (SPDR) | `.../fund-data/etfs/us/navhist-us-en-spy.xlsx`: HTTP 200, 277,335 bytes, **5,744 daily NAV rows, 01-Dec-2003 to 25-Sep-2026**, no key | https://www.ssga.com/us/en/individual: "The whole or any part of this work may not be reproduced, copied or transmitted or any of its contents disclosed to third parties without SSGA’s express written consent." |
| iShares US (BlackRock) | IVV `...1467271812596.ajax?fileType=xls...dataType=fund`: HTTP 200 but returned the HTML product page, not data | https://www.blackrock.com/corporate/compliance/terms-and-conditions: "Such content is solely for your personal, non-commercial use." It also bars any "robot, spider, intelligent agent, other automatic device, or manual process to search, monitor or copy this Website". |
| iShares Canada | XIU fund download: **HTTP 403 Access Denied** (Akamai) | BlackRock group terms; the Canadian-site terms were not opened separately |
| Vanguard US | not tested | https://investor.vanguard.com/terms-conditions: licence "solely for your personal, informational, and noncommercial use or as expressly authorized by Vanguard in writing" |
| Vanguard Canada | not tested | https://www.vanguard.ca/en/website-terms-of-use: "solely for your personal and noncommercial use or as expressly authorized by Vanguard in writing" |
| BMO GAM | site timed out; guessed legal URL returned 404 | **not opened** |

**Regulator-published alternatives.** US: the SEC's Form N-PORT data sets (https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets) run "October 2019 - June 2026". N-PORT is used by "registered management funds other than money market funds, and exchange-traded funds organized as unit investment trusts". The readme (https://www.sec.gov/files/nport_readme.pdf) has a table "MONTHLY_TOTAL_RETURN Contains monthly total return information for each of the preceding three months". **Test:** SPY (CIK 884394) has 28 public NPORT-P filings, report dates 2019-09-30 to 2026-06-30. The latest carries `<monthlyTotReturn rtn1="10.48000000" rtn2="5.25000000" rtn3="-0.96000000"/>`. An iShares Trust filing dated 2026-09-25 carries the same element per class ID. SEC reuse terms are quoted in `data-sources.md` ("may be copied or further distributed ... without the SEC’s permission"). Canada: SEDAR+ holds ETF Facts and MRFPs, but https://www.sedarplus.ca/onlinehelp/terms-of-use/ redirected to a Radware bot-block page, so its **terms were not opened**.

---

## 6. (c) The law: facts, compilations, derived numbers, and contracts

### 6.1 United States
* *Feist Publications v. Rural Telephone*, 499 U.S. 340 (1991) (https://www.law.cornell.edu/supremecourt/text/499/340): "The first is that facts are not copyrightable; the other, that compilations of facts generally are." And: "the copyright in a factual compilation is thin. Notwithstanding a valid copyright, a subsequent compiler remains free to use the facts contained in another's publication to aid in preparing a competing work, so long as the competing work does not feature the same selection and arrangement." Rural's white pages failed because "there is nothing remotely creative about arranging names alphabetically".
* 17 U.S.C. §103(b) (https://www.law.cornell.edu/uscode/text/17/103): "The copyright in a compilation or derivative work extends only to the material contributed by the author of such work, as distinguished from the preexisting material employed in the work". §102(b) excludes any "idea, procedure, process, system, method of operation".
* **Applied:** a ticker, name, exchange, NAV, monthly return, or a volatility or correlation computed by a standard formula is a fact. A complete exchange list sorted by symbol resembles the white pages. Robo-Kit's optimized weights are its own output. The selection and arrangement of a vendor's curated screen (for example a vendor's own category labels) could carry thin protection, so do not copy such taxonomies wholesale.

### 6.2 Canada
* *CCH Canadian Ltd. v. Law Society of Upper Canada*, 2004 SCC 13 (https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/2125/index.do): "an original work must be the product of an author’s exercise of skill and judgment. The exercise of skill and judgment required to produce the work must not be so trivial that it could be characterized as a purely mechanical exercise."
* *Tele-Direct (Publications) Inc. v. American Business Information, Inc.*, [1998] 2 F.C. 22 (FCA). **CanLII was blocked (HTTP 403 and a bot challenge), so this is quoted through CCH, para. 21:** the FCA "held, at para. 29, that those cases which had adopted the sweat of the brow approach to originality should not be interpreted as concluding that labour, in and of itself, could ground a finding of originality." Medium confidence, because this is secondary to the FCA text.
* Copyright Act, R.S.C. 1985, c. C-42, s. 2 (https://laws-lois.justice.gc.ca/eng/acts/C-42/page-1.html): "compilation means ... (b) a work resulting from the selection or arrangement of data". The test applies to the selection or arrangement, not to the data.
* **Applied:** mechanical computations (volatility, correlation) and exhaustive exchange lists fail the "skill and judgment" test. Robo-Kit's own screening rules, explanations and portfolio construction pass it and belong to Robo-Kit.

### 6.3 Terms of use bind separately from copyright
* *ProCD v. Zeidenberg*, 86 F.3d 1447 (7th Cir. 1996) (https://law.resource.org/pub/us/case/reporter/F3/086/86.F3d.1447.96-1139.html). This case was also about an uncopyrightable listings database: "Contracts, by contrast, generally affect only their parties; strangers may do as they please, so contracts do not create 'exclusive rights.'" It concludes that such a contract "may be enforced". **Effect:** the team's contract limits bind the team, not the people who later view the page.
* *Nguyen v. Barnes & Noble*, 763 F.3d 1171 (9th Cir. 2014) (https://cdn.ca9.uscourts.gov/datastore/opinions/2014/08/18/12-56628.pdf): "where, as here, there is no evidence that the website user had actual knowledge of the agreement, the validity of the browsewrap agreement turns on whether the website puts a reasonably prudent user on inquiry notice". **Effect:** browse-wrap terms can fail for lack of notice. Robo-Kit, however, has actual knowledge, because it quoted the terms in its own research. API keys also come with sign-up click-wraps.
* *Century 21 Canada v. Rogers Communications*, 2011 BCSC 1196 (https://www.bccourts.ca/jdb-txt/SC/11/11/2011BCSC1196.htm), para. 134: "where notice of the Terms of Use is established along with the knowledge that using the Website will serve as agreement to the Terms of Use, then I am satisfied that agreement is proven." That case involved a real-estate listing indexer that scraped the site.
* **Practical rule:** "facts are free" answers copyright only. Where Robo-Kit collected data (Yahoo, TMX, Cboe website, Nasdaq) decides whether publishing, even of derived numbers, breaches a contract Robo-Kit knowingly entered.

---

## 7. A mechanical rule that all these licences share: reconstructability

Tiingo (1.6(c) requirement (ii)), TMX (note 13, "cannot be reverse-engineered to recreate the Market Data") and Intrinio ("Any system that exposes, leaks, or could reconstruct Intrinio data externally is treated as redistribution") all draw the same line. This rule can be written as a build check:

| Allowed in a public bundle (when the input licence allows derived products) | Treated as the underlying data (not allowed without a display licence) |
|---|---|
| Covariance and correlation matrices; one annualized volatility and one full-window annualized return per fund; optimized weights; back-test summary statistics (Sharpe, maximum drawdown, CAGR); rankings and flags | Monthly or daily return series; rebased growth-of-$10k lines; prices; returns shipped with a start value; month-by-month back-test equity curves built from vendor data |

Note: Robo-Kit's in-page stationary bootstrap and walk-forward back-test need the return series, so for a non-Green market those must be precomputed (only summaries shipped) or run locally.

---

## 8. Minimum licence needed for a free public launch

| Market | Content in the public page | Minimum licence | Cost |
|---|---|---|---|
| US | Listing facts: SEC `company_tickers_mf.json` / `company_tickers_exchange.json` plus N-CEN (Green, per `data-sources.md`) | None (cite SEC) | $0 |
| US | Monthly total returns for 1940-Act ETFs, including UIT ETFs such as SPY, from N-PORT `MONTHLY_TOTAL_RETURN`, about 2019-07 onward | None (cite SEC Form N-PORT) | $0 |
| US | Longer history, or grantor-trust ETFs (GLD, IBIT) | Tiingo Commercial, publishing derived statistics only; or Tiingo Redistribution, showing series | $50/mo ($499/yr); or $250/mo (start-ups) |
| Canada | Any prices, returns or statistics derived from them | **A written licence.** No option with a published price allows public display or derived publication. Candidates: EODHD Custom (from $399/mo, quote), FMP Enterprise (quote), TMX EOD file (CAD 127–762/mo) plus redistribution permission (quote), Barchart (≥ $500/mo in 2021, terms unknown) | Unknown until quoted |
| Canada | Listing facts (ticker, name, exchange) | Copyright does not stop it. The TMX and Cboe website terms bind the collector, so get TMX/Cboe permission or a licensed list, or build the list on the user's machine | Unknown |
| Both | The same numbers passed to the viewer's Claude chat | Only licence-clean or derived-permitted numbers. Intrinio-style clauses count LLM transmission as redistribution | n/a |

**Interim design until a Canadian licence exists:** the published artifact holds the US market (SEC-sourced) with Canada switched off or marked "run locally". The Canadian market runs through the MCP server or CLI on the user's machine, using the user's own access (Yahoo for personal use, or the user's own EODHD/FMP key). Only Robo-Kit's code and Green data are distributed.

---

## 9. What this means for Robo-Kit (build, borrow, avoid, disclose)

1. **Stop sharing the current `robokit_web_data.json`.** It contains a reconstructable Yahoo return series. Keep the page private, or regenerate it from a Green source before anyone else gets the link.
2. **Add two fields per series to `data/catalog.yaml`: `public_ok` and `llm_ok`.** Also add a build check that fails if any field in the public bundle is a per-period series from a source without `public_ok: true`, or if an `llm_ok: false` value can reach a tool result sent to Claude.
3. **Build an N-PORT returns loader for the US market** (quarterly SEC zips, `MONTHLY_TOTAL_RETURN` joined on class ID through `company_tickers_mf.json`). Mark as out of scope: '33-Act trusts, ETNs, and anything before 2019. Show "Source: SEC Form N-PORT" on each number.
4. **Precompute or localise bootstraps and back-tests for Canada.** The page ships only covariance, expected returns, weights and summary statistics, and only once a licence allows them.
5. **Send one RFQ with the same questions to EODHD (Custom), FMP (Enterprise), TMX Datalinx and Barchart.** The questions are: (a) coverage of all TSX and Cboe Canada ETFs with total-return adjustments and delisted history; (b) public display of derived statistics; (c) whether sending data to an LLM API counts as redistribution; (d) retention of derived results after termination; (e) EODHD's exchange-sourced vs "OTC ... VWAP" price provenance.
6. **Prefer Tiingo for paid US data.** It is the only vendor found whose terms spell out what derived output may be published. Avoid Massive for the optimizer input unless its licence explicitly permits "investment strategy" outputs. Treat FMP's personal plan as local-only.
7. **Do not work around bot walls.** Barchart, SEDAR+, CanLII, Morningstar and Stooq all blocked scripted access. Record them as "not opened" instead of scraping.
8. **Disclose on the page:** each data source and its as-of date; "NAV total return, not market price" for N-PORT data; a delay disclaimer if TMX delayed data is ever used; and "Data sourced by Tiingo" if Tiingo data is redistributed (ToS 7.3 requires the phrase).
9. **Survivorship (a gap in `data-sources.md`):** Tiingo's ticker file lists 2,135 ended ETF rows, and SEC N-PORT filings persist after a fund closes. Both can seed a US delisted-ETF list. For Canada this is still open.

---

## 10. Gaps

* **No vendor trial was run.** Account creation is out of scope, so .TO/.NE coverage for EODHD and FMP rests on their own claims; their demo keys returned 403/401.
* **Terms not opened:** Barchart (bot challenge), SEDAR+ (Radware block), BMO GAM (timeout/404), Cboe Canada Historical Data Agreement and Global Data Agreement, Morningstar licence terms, iShares Canada site terms, EODHD Data Services Agreement.
* *Tele-Direct* was quoted through *CCH*; the FCA text itself was not opened (CanLII blocked).
* US exchange policies on end-of-day or delayed data for public websites (Nasdaq, NYSE, Cboe US) were not reviewed; the vendor prices above are assumed to include them.
* N-PORT coverage was checked on two trusts only (SPY; one iShares Trust filing). The share of the 5,738 US ETFs with a usable monthly return history was not measured.
* Not covered: US "hot news" misappropriation, trespass-to-chattels claims for scraping, the EU sui generis database right (relevant if EU users are served), and Quebec-specific consumer law on browse-wraps.
* The Barchart price dates from 2021 and may be stale.
