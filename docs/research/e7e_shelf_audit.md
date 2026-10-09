# E7(e): the shelf audit (each slot's top five candidates)

Registered in RESEARCH_LOG section 10 (E7(e)): "the top five candidates of every slot checked as broad, low-cost index
funds". Done 9 Oct 2026, after the run. The candidates are listed by the shelf's written score
(robokit/shelf.py `candidates`), from the data snapshot of the run; a research lane judged each against three tests
(tracks a published index; broad for the slot's asset class and region; fee at most 0.30%, or 0.40% for gold and cash)
and noted structural concerns, quoting the issuers' documents. The rulings below are the authors', after checking.

## Rulings on the funds the shelf holds (rank 1)

| Fund | Slot | Finding | Ruling |
|---|---|---|---|
| VBU.NE | Canadian "Global bonds, hedged" | holds US bonds only | true: the slot's matching rule accepts a US aggregate index, so the label overstates its breadth. The truly global CAD-hedged candidates cost 0.31% (VGAB) and 0.38% (VBG, ex-US) against VBU's lower fee. Recommended: relabel the slot or prefer a global aggregate fund; not changed in this release, whose shelf is the one evaluated |
| XRE.TO | Canadian real estate | fee 0.60% | partly true: REIT funds cost more than broad funds, but a cheaper candidate exists (VRE, 0.39%); the score's weight on size beats its weight on fee here, and E5 shows the choice does not change with the fee coefficient at 1.5 times |
| XRB.TO | Canadian real-return bonds | fee 0.39% | partly true: the 0.30% bar was set for broad funds; this is a niche slot |
| XHY.TO | Canadian high yield | fee 0.55% | partly true: a cheaper candidate exists (QHY, 0.46%); same score trade-off as XRE |
| CASH.TO | Canadian cash | not an index fund (bank deposits) | true by design: the cash slot holds high-interest savings, and no index is involved |

## Lower-ranked candidates

The slots' text filters let some candidates through that a reviewer would not want in a core slot: total-return-swap
funds (HXT, HXEM), actively managed funds (RIT, AVEM, DFIP, FLIA, JPIB, MHYB), options or futures strategies (BOXX,
TUA) and maturity or issuer subsets (ZFL, ZPL, XFLB, TIPX, EDV, IGIB, IGLB, SCHI). None is chosen by the score today,
but a client's swap could pick one (swaps are limited to the slot's asset class and region, not to index funds).
Recommended: exclude active, swap-based and options-based funds from the core slots' candidates.

## The lane's full table

| ticker | slot | rank | which test fails or what the concern is | evidence (quote and URL, or the name/MER from the list) |
| --- | --- | --- | --- | --- |
| HXT.TO | ca_equity | 4 | Structural concern: total-return swap (synthetic) structure | “Global X TRI ETFs… use a synthetic structure… the ETF receives the total return of the index by entering into a Total Return Swap” — https://www.globalx.ca/product/hxt; list name: Global X S&P/TSX 60 Corporate Class ETF |
| HXEM.TO | ca_em_equity | 4 | Structural concern: total-return swap structure | “the ETF has entered into one or more swap agreements… Each Swap is a total return swap” — https://www.globalx.ca/wp-content/uploads/2026/04/HXEM-EN-AR2025.pdf; list name: Corporate Class ETF |
| VBU.NE | ca_global_bond | 1 | Broad: US aggregate only, not global bonds | List name: Vanguard U.S. Aggregate Bond Index ETF (CAD-hedged); slot label: Global bonds, hedged |
| ZUAG-F.TO | ca_global_bond | 2 | Broad: US aggregate only, not global bonds | List name: BMO US Aggregate Bond Index ETF (Hedged Units); slot label: Global bonds, hedged |
| XGGB.NE | ca_global_bond | 3 | Broad: government bonds only, not broad global aggregate | List name: IShares Global Government Bond Index ETF (CAD-Hedged) |
| VBG.NE | ca_global_bond | 4 | Low cost: MER 0.38% > 0.30%; also Broad: global ex-U.S. omits U.S. bonds | List: Vanguard Global ex-U.S. Aggregate Bond Index ETF (CAD-hedged) \| MER 0.38% |
| VGAB.NE | ca_global_bond | 5 | Low cost: MER 0.31% > 0.30% | List: Vanguard Global Aggregate Bond Index ETF (CAD-hedged) \| MER 0.31% |
| XRE.TO | ca_reit | 1 | Low cost: MER 0.6% > 0.30% | List: iShares S&P/TSX Capped REIT Index ETF \| MER 0.6% |
| ZRE.TO | ca_reit | 2 | Low cost: MER 0.61% > 0.30% | List: BMO Equal Weight REITs Index ETF \| MER 0.61% |
| VRE.TO | ca_reit | 3 | Low cost: MER 0.39% > 0.30% | List: Vanguard FTSE Canadian Capped REIT Index ETF \| MER 0.39% |
| RIT.TO | ca_reit | 4 | Index: actively managed; Low cost: MER 0.87% > 0.30% | “from an actively managed portfolio comprised primarily of securities of Canadian real estate investment trusts” — https://funds.cifinancial.com/en/documents/static/Fund_ETF_Facts_(POS)/Exchange_Traded_Funds/51839/CICanadianREITETF_ETF_fact_document.pdf; list MER 0.87% |
| CASH.TO | ca_cash | 1 | Index: does not track a published index (bank deposits) | “CASH uses cash accounts and does not track a traditional benchmark but rather receives interest paid on cash deposits” — https://www.globalx.ca/product/cash |
| CMR.TO | ca_cash | 2 | Index: actively managed money market; no underlying index | “Underlying Index: N/A… Management Type: Active Management” — https://www.barchart.com/stocks/quotes/CMR.TO/profile; list name: iShares Premium Money Market ETF |
| ZMMK.TO | ca_cash | 3 | Index: money-market fund (not an index tracker); MER missing from list (UNSURE on exact MER from list alone) | List name: BMO Mutual Funds - BMO Money Market Fund \| MER %; issuer: “invests primarily in high quality money market instruments” (no index) — https://fundfacts.bmo.com/EtfSeriesEnglish/BMO_Money_Market_Fund-EN-ETF_Series.pdf |
| HISA.NE | ca_cash | 4 | Index: deposit-account fund, not a published-index tracker | “investing primarily in high interest deposit accounts” — https://evolveetfs.com/wp-content/uploads/2026/07/ETF-Facts-HISA-High-Interest-Savings-Account-Fund.pdf |
| CBIL.TO | ca_cash | 5 | Broad: 0–3 month T-bills, not high-interest savings deposits | List name: Global X 0-3 Month T-Bill ETF CAD; slot label: Cash (high-interest savings) |
| ZFL.TO | ca_long_bond | 2 | Broad: long federal only, not broad long-term Canadian bonds | List name: BMO Long Federal Bond Index ETF |
| XFLB.TO | ca_long_bond | 4 | Broad: 15+ year federal only subset | List name: iShares Core Canadian 15+ Year Federal Bond Index ETF |
| ZPL.TO | ca_long_bond | 5 | Broad: long provincial only | List name: BMO Long Provincial Bond Index ETF |
| XRB.TO | ca_real_return | 1 | Low cost: MER 0.39% > 0.30% | List: iShares Canadian Real Return Bond Index ETF \| MER 0.39% |
| XHY.TO | ca_high_yield | 1 | Low cost: MER 0.55% > 0.30% | List: iShares U.S. High Yield Bond Index ETF (CAD-Hedged) \| MER 0.55% |
| ZHY.TO | ca_high_yield | 2 | Low cost: MER 0.6% > 0.30% | List: BMO High Yield US Corporate Bond Hedged to CAD Index ETF \| MER 0.6% |
| ZJK.TO | ca_high_yield | 3 | Low cost: MER 0.61% > 0.30% | List: BMO High Yield US Corporate Bond Index ETF \| MER 0.61% |
| QHY.TO | ca_high_yield | 4 | Low cost: MER 0.46% > 0.30% | List: Mackenzie US High Yield Bond Index ETF (CAD-Hedged) \| MER 0.46% |
| MHYB.NE | ca_high_yield | 5 | Index: actively managed; Low cost: MER 0.67% > 0.30% | “Active management using rigorous credit work” — https://www.mackenzieinvestments.com/en/products/etfs/mackenzie-global-high-yield-fixed-income-etf-mhyb; list MER 0.67% |
| XUU.TO | ca_us_equity | 5 | Low cost: UNSURE (MER blank in list) | List: iShares Core S&P U.S. Total Market Index ETF \| MER % |
| AVEM | us_em_equity | 5 | Index: actively managed; Low cost: MER 0.33% > 0.30% | “actively managed exchange-traded fund (ETF) that does not seek to replicate the performance of a specified index” — https://www.sec.gov/Archives/edgar/data/1710607/000171060725000394/acetftavem497k.htm; list MER 0.33% |
| TUA | us_short_treasury | 4 | Index: actively managed futures strategy; Broad: targets 7–10 year duration, not short-term Treasuries; structural: Treasury futures/options | “actively managed… invests primarily in futures contracts, call options, and put options on U.S. Treasury futures… matches or outperforms… ICE US Treasury 7-10 Year Bond Index” — https://www.sec.gov/Archives/edgar/data/1810747/000182912625009169/simplifyetf-tua_497k.htm |
| TIPX | us_tips | 4 | Broad: 1–10 year TIPS only, not full TIPS market | List name: State Street SPDR Bloomberg 1–10 Year TIPS ETF |
| DFIP | us_tips | 5 | Index: actively managed | “actively managed exchange-traded fund and does not seek to replicate the performance of a specific index” — https://www.sec.gov/Archives/edgar/data/1816125/000181612526000079/c497k.htm |
| FLIA | us_intl_bond | 3 | Index: actively managed | “actively managed exchange-traded fund (ETF) that does not seek to replicate the performance of a specified index” — https://www.nasdaqtrader.com/content/newsalerts/2018/infocircular/Franklin06012018.pdf |
| JPIB | us_intl_bond | 4 | Index: actively managed; Low cost: MER 0.5% > 0.30% | “The Fund is not an index fund. The Fund is actively managed and does not seek to replicate the performance of a specified index.” — https://www.sec.gov/Archives/edgar/data/1485894/000119312520243005/d947928d485bpos.htm; list MER 0.5% |
| IYR | us_reit | 5 | Low cost: MER 0.37% > 0.30% | List: iShares U.S. Real Estate ETF \| MER 0.37% |
| BOXX | us_cash | 4 | Index: actively managed options (box-spread) strategy, not a T-bill index fund; structural: options strategy | “actively managed… principal investment strategy… box spread (‘Box Spread’)” — https://www.sec.gov/Archives/edgar/data/1592900/000159290026000392/alphaarchitect1-3monthboxe.htm |
| EDV | us_long_treasury | 3 | Broad: 20–30 year Treasury STRIPS / extended duration, not broad long Treasuries | “Bloomberg U.S. Treasury STRIPS 20–30 Year Equal Par Bond Index” — https://personal1.vanguard.com/pub/Pdf/sp930.pdf; list name: Vanguard Extended Duration Treasury ETF |
| IGIB | us_corp_bond | 2 | Broad: 5–10 year IG corporates only | List name: iShares 5-10 Year Investment Grade Corporate Bond ETF |
| IGLB | us_corp_bond | 4 | Broad: 10+ year IG corporates only | List name: iShares 10 Year Investment Grade Corporate Bond ETF |
| SCHI | us_corp_bond | 5 | Broad: 5–10 year corporates only | List name: Schwab 5-10 Year Corporate Bond ETF |
| HYG | us_high_yield | 5 | Low cost: MER 0.49% > 0.30% | List: iShares iBoxx $ High Yield Corporate Bond ETF \| MER 0.49% |

**5** of the rank-1 funds fail any test.

The shelf’s written rule—broad, low-cost, index-tracking—holds for most core equity and aggregate-bond rank-1 picks (e.g. XIC, VFV, VOO, BND, VNQ). It breaks down where the scoring still elevates products that fail the rule on cost (XRE, XRB, XHY), breadth (VBU as U.S.-only in a global-bond slot), or index tracking (CASH as a deposit HISA ETF). Lower-ranked candidates add swap structures (HXT, HXEM), active managers (RIT, AVEM, JPIB, FLIA, DFIP, MHYB), options/futures cash or duration strategies (BOXX, TUA), and maturity/issuer niches. So the rule is sound, but the shelf’s actual top picks only partly enforce it.


## The candidates audited

```
CA | ca_equity | Canadian stocks | 1 | XIC.TO | iShares Core S&P/TSX Capped Composite Index ETF | MER 0.06% | AUM 34336M
CA | ca_equity | Canadian stocks | 2 | ZCN.TO | BMO S&P/TSX Capped Composite Index ETF | MER 0.06% | AUM 18367M
CA | ca_equity | Canadian stocks | 3 | VCN.TO | Vanguard FTSE Canada All Cap Index ETF | MER 0.06% | AUM 17754M
CA | ca_equity | Canadian stocks | 4 | HXT.TO | Global X S&P/TSX 60 Corporate Class ETF | MER 0.07% | AUM 5619M
CA | ca_equity | Canadian stocks | 5 | QCN.TO | Mackenzie Canadian Equity Index ETF | MER 0.04% | AUM 6183M
CA | ca_us_equity | US stocks | 1 | VFV.TO | Vanguard S&P 500 Index ETF | MER 0.09% | AUM 35156M
CA | ca_us_equity | US stocks | 2 | ZSP.TO | BMO S&P 500 Index ETF (CAD) | MER 0.09% | AUM 25626M
CA | ca_us_equity | US stocks | 3 | XUS.TO | iShares Core S&P 500 Index ETF | MER 0.09% | AUM 13285M
CA | ca_us_equity | US stocks | 4 | TPU.TO | TD U.S. Equity Index ETF | MER 0.07% | AUM 6544M
CA | ca_us_equity | US stocks | 5 | XUU.TO | iShares Core S&P U.S. Total Market Index ETF | MER % | AUM 4777M
CA | ca_intl_equity | International stocks | 1 | FLUR.NE | Franklin International Equity Index ETF | MER 0.1% | AUM 619M
CA | ca_intl_equity | International stocks | 2 | XEF.TO | iShares Core MSCI EAFE IMI Index ETF | MER 0.23% | AUM 23860M
CA | ca_intl_equity | International stocks | 3 | ZEA.TO | BMO MSCI EAFE Index ETF | MER 0.22% | AUM 13639M
CA | ca_intl_equity | International stocks | 4 | TPE.TO | TD International Equity Index ETF | MER 0.19% | AUM 5763M
CA | ca_intl_equity | International stocks | 5 | VIU.TO | Vanguard FTSE Developed All Cap ex North Amer Idx ETF | MER 0.23% | AUM 11588M
CA | ca_em_equity | Emerging-market stocks | 1 | VEE.TO | Vanguard FTSE Emerging Markets All Cap Index ETF | MER 0.26% | AUM 4610M
CA | ca_em_equity | Emerging-market stocks | 2 | XEC.TO | iShares Core MSCI Emerging Markets IMI Index ETF | MER 0.28% | AUM 4975M
CA | ca_em_equity | Emerging-market stocks | 3 | ZEM.TO | BMO MSCI Emerging Markets Index ETF | MER 0.27% | AUM 3550M
CA | ca_em_equity | Emerging-market stocks | 4 | HXEM.TO | Global X Emerging Markets Equity Index Corporate Class ETF | MER 0.25% | AUM 229M
CA | ca_em_equity | Emerging-market stocks | 5 | FLEM.NE | Franklin Emerging Markets Equity Index ETF | MER 0.17% | AUM 66M
CA | ca_agg_bond | Canadian bonds | 1 | ZAG.TO | BMO Aggregate Bond Index ETF | MER 0.09% | AUM 13262M
CA | ca_agg_bond | Canadian bonds | 2 | XBB.TO | iShares Core Canadian Universe Bond Index ETF | MER 0.1% | AUM 10595M
CA | ca_agg_bond | Canadian bonds | 3 | VAB.TO | Vanguard Canadian Aggregate Bond Index ETF | MER 0.09% | AUM 7620M
CA | ca_agg_bond | Canadian bonds | 4 | TDB.TO | TD Canadian Aggregate Bond Index ETF | MER 0.08% | AUM 4211M
CA | ca_agg_bond | Canadian bonds | 5 | SITB.NE | Scotia Canadian Bond Index Tracker ETF | MER 0.09% | AUM 2711M
CA | ca_short_bond | Short-term Canadian bonds | 1 | XSB.TO | iShares Core Canadian Short Term Bond Index ETF | MER 0.1% | AUM 4486M
CA | ca_short_bond | Short-term Canadian bonds | 2 | VSB.TO | Vanguard Canadian Short-Term Bond Index ETF | MER 0.12% | AUM 1627M
CA | ca_short_bond | Short-term Canadian bonds | 3 | CSBI.TO | CIBC Canadian Short-Term Bond Index ETF | MER 0.08% | AUM 419M
CA | ca_short_bond | Short-term Canadian bonds | 4 | ZSB.TO | BMO Short-Term Bond Index ETF | MER 0.1% | AUM 183M
CA | ca_short_bond | Short-term Canadian bonds | 5 | QSB.TO | Mackenzie Canadian Short-Term Bond Index ETF | MER 0.09% | AUM 56M
CA | ca_global_bond | Global bonds, hedged | 1 | VBU.NE | Vanguard U.S. Aggregate Bond Index ETF (CAD-hedged) | MER 0.23% | AUM 1899M
CA | ca_global_bond | Global bonds, hedged | 2 | ZUAG-F.TO | BMO US Aggregate Bond Index ETF (Hedged Units) | MER 0.09% | AUM 1401M
CA | ca_global_bond | Global bonds, hedged | 3 | XGGB.NE | IShares Global Government Bond Index ETF (CAD-Hedged) | MER 0.23% | AUM 439M
CA | ca_global_bond | Global bonds, hedged | 4 | VBG.NE | Vanguard Global ex-U.S. Aggregate Bond Index ETF (CAD-hedged) | MER 0.38% | AUM 1548M
CA | ca_global_bond | Global bonds, hedged | 5 | VGAB.NE | Vanguard Global Aggregate Bond Index ETF (CAD-hedged) | MER 0.31% | AUM 665M
CA | ca_reit | Real estate (REITs) | 1 | XRE.TO | iShares S&P/TSX Capped REIT Index ETF | MER 0.6% | AUM 1106M
CA | ca_reit | Real estate (REITs) | 2 | ZRE.TO | BMO Equal Weight REITs Index ETF | MER 0.61% | AUM 596M
CA | ca_reit | Real estate (REITs) | 3 | VRE.TO | Vanguard FTSE Canadian Capped REIT Index ETF | MER 0.39% | AUM 265M
CA | ca_reit | Real estate (REITs) | 4 | RIT.TO | CI Canadian REIT ETF | MER 0.87% | AUM 383M
CA | ca_gold | Gold | 1 | VALT.TO | CI Gold Bullion ETF | MER 0.17% | AUM 252M
CA | ca_gold | Gold | 2 | KILO.TO | Purpose Gold Bullion Fund | MER 0.28% | AUM 532M
CA | ca_gold | Gold | 3 | HUG.TO | Global X Gold ETF | MER 0.39% | AUM 51M
CA | ca_cash | Cash (high-interest savings) | 1 | CASH.TO | Global X High Interest Savings ETF | MER 0.11% | AUM 6546M
CA | ca_cash | Cash (high-interest savings) | 2 | CMR.TO | iShares Premium Money Market ETF Common Class | MER 0.13% | AUM 2751M
CA | ca_cash | Cash (high-interest savings) | 3 | ZMMK.TO | BMO Mutual Funds - BMO Money Market Fund | MER % | AUM 5975M
CA | ca_cash | Cash (high-interest savings) | 4 | HISA.NE | High Interest Savings Account ETF | MER 0.15% | AUM 2611M
CA | ca_cash | Cash (high-interest savings) | 5 | CBIL.TO | Global X 0-3 Month T-Bill ETF CAD | MER 0.11% | AUM 2740M
CA | ca_long_bond | Long-term Canadian bonds | 1 | XLB.TO | iShares Core Canadian Long Term Bond Index ETF | MER 0.2% | AUM 729M
CA | ca_long_bond | Long-term Canadian bonds | 2 | ZFL.TO | BMO Long Federal Bond Index ETF | MER 0.22% | AUM 1297M
CA | ca_long_bond | Long-term Canadian bonds | 3 | VLB.TO | Vanguard Canadian Long-Term Bond Index ETF | MER 0.17% | AUM 252M
CA | ca_long_bond | Long-term Canadian bonds | 4 | XFLB.TO | iShares Core Canadian 15+ Year Federal Bond Index ETF | MER 0.17% | AUM 46M
CA | ca_long_bond | Long-term Canadian bonds | 5 | ZPL.TO | BMO Long Provincial Bond Index ETF | MER 0.28% | AUM 302M
CA | ca_real_return | Inflation-linked bonds | 1 | XRB.TO | iShares Canadian Real Return Bond Index ETF | MER 0.39% | AUM 259M
CA | ca_real_return | Inflation-linked bonds | 2 | ZRR.TO | BMO Real Return Bond Index ETF | MER 0.28% | AUM 99M
CA | ca_us_equity_hedged | US stocks, hedged | 1 | XSP.TO | iShares Core S&P 500 Index ETF (CAD-Hedged) | MER 0.09% | AUM 16065M
CA | ca_us_equity_hedged | US stocks, hedged | 2 | ZUE.TO | BMO S&P 500 Hedged to CAD Index ETF | MER 0.09% | AUM 4924M
CA | ca_us_equity_hedged | US stocks, hedged | 3 | VSP.TO | Vanguard S&P 500 Index ETF (CAD-hedged) | MER 0.09% | AUM 6326M
CA | ca_us_equity_hedged | US stocks, hedged | 4 | XUH.TO | iShares Core S&P U.S. Total Market Index ETF (CAD-Hedged) | MER 0.07% | AUM 517M
CA | ca_us_equity_hedged | US stocks, hedged | 5 | VUS.TO | Vanguard Morningstar U.S. Total Market Index ETF (CAD-hedged) | MER 0.17% | AUM 1434M
CA | ca_high_yield | High-yield bonds | 1 | XHY.TO | iShares U.S. High Yield Bond Index ETF (CAD-Hedged) | MER 0.55% | AUM 1160M
CA | ca_high_yield | High-yield bonds | 2 | ZHY.TO | BMO High Yield US Corporate Bond Hedged to CAD Index ETF | MER 0.6% | AUM 1502M
CA | ca_high_yield | High-yield bonds | 3 | ZJK.TO | BMO High Yield US Corporate Bond Index ETF | MER 0.61% | AUM 1796M
CA | ca_high_yield | High-yield bonds | 4 | QHY.TO | Mackenzie US High Yield Bond Index ETF (CAD-Hedged) | MER 0.46% | AUM 249M
CA | ca_high_yield | High-yield bonds | 5 | MHYB.NE | Mackenzie Global High Yield Fixed Income ETF | MER 0.67% | AUM 290M
US | us_equity | US stocks | 1 | VOO | Vanguard S&P 500 ETF | MER 0.03% | AUM 1756880M
US | us_equity | US stocks | 2 | VTI | Vanguard Morningstar Total Stock Market ETF | MER 0.03% | AUM 2343737M
US | us_equity | US stocks | 3 | IVV | iShares Core S&P 500 ETF | MER 0.03% | AUM 883985M
US | us_equity | US stocks | 4 | SPY | State Street SPDR S&P 500 ETF Trust | MER 0.09% | AUM 811937M
US | us_equity | US stocks | 5 | SPYM | State Street SPDR Portfolio S&P 500 ETF | MER 0.02% | AUM 171264M
US | us_intl_equity | International stocks | 1 | VXUS | Vanguard Total International Stock ETF | MER 0.05% | AUM 665693M
US | us_intl_equity | International stocks | 2 | VEA | Vanguard FTSE Developed Markets ETF | MER 0.03% | AUM 323821M
US | us_intl_equity | International stocks | 3 | IEFA | iShares Core MSCI EAFE ETF | MER 0.07% | AUM 194386M
US | us_intl_equity | International stocks | 4 | VEU | Vanguard FTSE All World Ex US ETF | MER 0.04% | AUM 98641M
US | us_intl_equity | International stocks | 5 | SCHF | Schwab International Equity ETF | MER 0.03% | AUM 69684M
US | us_em_equity | Emerging-market stocks | 1 | VWO | Vanguard FTSE Emerging Markets ETF | MER 0.06% | AUM 168359M
US | us_em_equity | Emerging-market stocks | 2 | IEMG | iShares Core MSCI Emerging Markets ETF | MER 0.09% | AUM 160899M
US | us_em_equity | Emerging-market stocks | 3 | SPEM | State Street SPDR Portfolio Emerging Markets ETF | MER 0.07% | AUM 17831M
US | us_em_equity | Emerging-market stocks | 4 | SCHE | Schwab Emerging Markets Equity ETF | MER 0.06% | AUM 13003M
US | us_em_equity | Emerging-market stocks | 5 | AVEM | Avantis Emerging Markets Equity ETF | MER 0.33% | AUM 28054M
US | us_agg_bond | US bonds | 1 | BND | Vanguard Total Bond Market ETF | MER 0.03% | AUM 398835M
US | us_agg_bond | US bonds | 2 | AGG | iShares Core U.S. Aggregate Bond ETF | MER 0.03% | AUM 138318M
US | us_agg_bond | US bonds | 3 | SPAB | State Street SPDR Portfolio Aggregate Bond ETF | MER 0.03% | AUM 10218M
US | us_agg_bond | US bonds | 4 | SCHZ | Schwab US Aggregate Bond ETF | MER 0.03% | AUM 10673M
US | us_agg_bond | US bonds | 5 | BKAG | BNY Mellon Core Bond ETF | MER 0.0% | AUM 2264M
US | us_short_treasury | Short-term US Treasuries | 1 | VGSH | Vanguard Short-Term Treasury ETF | MER 0.03% | AUM 39196M
US | us_short_treasury | Short-term US Treasuries | 2 | SPTS | State Street SPDR Portfolio Short Term Treasury ETF | MER 0.03% | AUM 7295M
US | us_short_treasury | Short-term US Treasuries | 3 | SHY | iShares 1-3 Year Treasury Bond ETF | MER 0.15% | AUM 25913M
US | us_short_treasury | Short-term US Treasuries | 4 | TUA | Simplify Short Term Treasury Futures Strategy ETF | MER 0.25% | AUM 522M
US | us_tips | Inflation-protected bonds (TIPS) | 1 | SCHP | Schwab U.S. TIPS ETF | MER 0.03% | AUM 16081M
US | us_tips | Inflation-protected bonds (TIPS) | 2 | TIP | iShares TIPS Bond ETF | MER 0.18% | AUM 15010M
US | us_tips | Inflation-protected bonds (TIPS) | 3 | SPIP | State Street SPDR Portfolio TIPS ETF | MER 0.12% | AUM 1019M
US | us_tips | Inflation-protected bonds (TIPS) | 4 | TIPX | State Street SPDR Bloomberg 1a??10 Year TIPS ETF | MER 0.15% | AUM 2066M
US | us_tips | Inflation-protected bonds (TIPS) | 5 | DFIP | Dimensional Inflation-Protected Securities ETF | MER 0.11% | AUM 1142M
US | us_intl_bond | International bonds, hedged | 1 | BNDX | Vanguard Total International Bond ETF | MER 0.07% | AUM 123027M
US | us_intl_bond | International bonds, hedged | 2 | IAGG | iShares International Aggregate Bond Fund | MER 0.07% | AUM 11387M
US | us_intl_bond | International bonds, hedged | 3 | FLIA | Franklin International Aggregate Bond ETF | MER 0.25% | AUM 762M
US | us_intl_bond | International bonds, hedged | 4 | JPIB | JPMorgan International Bond Opportunities ETF | MER 0.5% | AUM 2194M
US | us_reit | Real estate (REITs) | 1 | VNQ | Vanguard Real Estate ETF | MER 0.13% | AUM 70823M
US | us_reit | Real estate (REITs) | 2 | SCHH | Schwab U.S. REIT ETF | MER 0.07% | AUM 11197M
US | us_reit | Real estate (REITs) | 3 | USRT | iShares Core U.S. REIT ETF | MER 0.08% | AUM 4570M
US | us_reit | Real estate (REITs) | 4 | FREL | Fidelity MSCI Real Estate Index ETF | MER 0.08% | AUM 1476M
US | us_reit | Real estate (REITs) | 5 | IYR | iShares U.S. Real Estate ETF | MER 0.37% | AUM 4395M
US | us_gold | Gold | 1 | GLDM | SPDR Gold MiniShares Trust | MER 0.1% | AUM 32786M
US | us_gold | Gold | 2 | IAUM | iShares Gold Trust Micro Shares | MER 0.09% | AUM 8144M
US | us_gold | Gold | 3 | SGOL | abrdn Physical Gold Shares ETF | MER 0.17% | AUM 7749M
US | us_gold | Gold | 4 | IAU | iShares Gold Trust Shares | MER 0.25% | AUM 67539M
US | us_gold | Gold | 5 | AAAU | Goldman Sachs Physical Gold ETF Shares | MER 0.18% | AUM 2874M
US | us_cash | Cash (Treasury bills) | 1 | SGOV | iShares 0-3 Month Treasury Bond ETF | MER 0.09% | AUM 105976M
US | us_cash | Cash (Treasury bills) | 2 | BIL | State Street SPDR Bloomberg 1-3 Month T-Bill ETF | MER 0.14% | AUM 46753M
US | us_cash | Cash (Treasury bills) | 3 | BILS | State Street SPDR Bloomberg 3-12 Month T-Bill ETF | MER 0.14% | AUM 3882M
US | us_cash | Cash (Treasury bills) | 4 | BOXX | Alpha Architect 1-3 Month Box ETF | MER 0.19% | AUM 14470M
US | us_small_cap | US small companies | 1 | VB | Vanguard Morningstar Small-Cap ETF | MER 0.03% | AUM 185274M
US | us_small_cap | US small companies | 2 | IJR | iShares Core S&P Small-Cap ETF | MER 0.06% | AUM 109250M
US | us_small_cap | US small companies | 3 | IWM | iShares Russell 2000 Index Fund | MER 0.19% | AUM 80461M
US | us_small_cap | US small companies | 4 | SCHA | Schwab U.S. Small-Cap ETF | MER 0.03% | AUM 22646M
US | us_small_cap | US small companies | 5 | VTWO | Vanguard Russell 2000 ETF | MER 0.06% | AUM 17948M
US | us_long_treasury | Long-term US Treasuries | 1 | VGLT | Vanguard Long-Term Treasury ETF | MER 0.03% | AUM 15134M
US | us_long_treasury | Long-term US Treasuries | 2 | TLT | iShares 20+ Year Treasury Bond ETF | MER 0.15% | AUM 47046M
US | us_long_treasury | Long-term US Treasuries | 3 | EDV | Vanguard Extended Duration Treasury ETF | MER 0.05% | AUM 4135M
US | us_corp_bond | US corporate bonds | 1 | LQD | iShares iBoxx $ Investment Grade Corporate Bond ETF | MER 0.14% | AUM 32043M
US | us_corp_bond | US corporate bonds | 2 | IGIB | iShares 5-10 Year Investment Grade Corporate Bond ETF | MER 0.04% | AUM 18716M
US | us_corp_bond | US corporate bonds | 3 | USIG | iShares Broad USD Investment Grade Corporate Bond ETF | MER 0.04% | AUM 17845M
US | us_corp_bond | US corporate bonds | 4 | IGLB | iShares 10  Year Investment Grade Corporate Bond ETF | MER 0.04% | AUM 2937M
US | us_corp_bond | US corporate bonds | 5 | SCHI | Schwab 5-10 Year Corporate Bond ETF | MER 0.03% | AUM 11508M
US | us_high_yield | High-yield bonds | 1 | SPHY | State Street SPDR Portfolio High Yield Bond ETF | MER 0.05% | AUM 12024M
US | us_high_yield | High-yield bonds | 2 | USHY | iShares Broad USD High Yield Corporate Bond ETF | MER 0.08% | AUM 28733M
US | us_high_yield | High-yield bonds | 3 | HYLB | Xtrackers USD High Yield Corporate Bond ETF | MER 0.05% | AUM 3564M
US | us_high_yield | High-yield bonds | 4 | SCYB | Schwab High Yield Bond ETF | MER 0.03% | AUM 2861M
US | us_high_yield | High-yield bonds | 5 | HYG | iShares iBoxx $ High Yield Corporate Bond ETF | MER 0.49% | AUM 16186M
```
