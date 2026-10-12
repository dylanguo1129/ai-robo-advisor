# The data layer's cross-check (3.0.3, 11 Oct 2026)

The team's Canadian ETF data layer (Anna; github.com/shreyajane23/robokit-data, v0.6.3) is built separately from
this repository: its own TSX and Cboe Canada listings, Yahoo fund profiles, classification rules and checks. Its
optimizer bridge (`robokit/optimizer_bridge.py`) compares it fund by fund with `web/data/ca.json` and writes a
sheet of labels that a fund's own name contradicts, the fields this universe lacks, and the funds it does not list.
The bridge files were not attached to the hand-off note, so they were rebuilt here with the same code: the
corrections sheet needs only her name rules and our `ca.json`, and the fields came from her dataset export of
October 10 (Drive, Final Dataset/Version 2). The rebuilt numbers match her note: 9 high-confidence corrections on
eligible funds, 42 eligible funds without an MER of which her data fills 28, and 61 funds not listed here.

## What the comparison found, and the fixes

| | At 3.0.2 | At 3.0.3 |
|---|---|---|
| Corrections suggested (all funds) | 147 | 79 |
| of which high confidence | 59 | 0 |
| High confidence on eligible funds | 9 | 0 |
| "Check" rows on eligible funds | 9 | 5 |

Rather than paste one override per fund, the four rules that produced the errors were fixed in
`robokit/classify.py`, so the same mistake cannot return for funds not yet listed:

1. **"Global X" is an issuer's brand.** Region words are read from the name without it. A Global X fund whose name
   and holdings name no region stays Global (a uranium or robotics theme fund), as before; otherwise the
   listing-market fallback would call every US-listed theme fund a US fund.
2. **"ex U.S." excludes the US.** "ex U.S.", "ex-U.S.", "ex USA" and "ex North Amer" (or "ex Nrth Amer") now read
   as International developed; before, the dots defeated the rule and the US rule matched "U.S.". "Australian"
   now reads as Asia-Pacific.
3. **A leverage multiple keeps its sign.** "(-3X)" lost its minus sign after the bracket, so the four MegaShort
   funds were +3x; garbled multipliers ("3?" for "3×") and "2xLeveraged" are read too.
4. **A fund category alone does not make a fund leveraged.** TMX and Yahoo file "Enhanced" funds (which borrow up
   to 1.25x and do not reset daily), Purpose Solana and some income funds under leverage. The category now applies
   only when the name says leveraged, bull, bear, inverse or similar; an inverse fund keeps its sign ("Daily
   Inverse" is -1x, not +2x) and is -2x only when its name also says leveraged. This follows the meaning the
   screen uses (daily-reset leverage), as the data layer's bridge does.

136 listings change at least one label (86 Canadian, 50 US).
Eligibility changes for two: HDIF.TO (it borrows modestly and does not reset daily, so it is now read at 1x, like the "Enhanced" funds) and
XUSP (an options-based "accelerated" fund). No reference fund changes in any slot, with or without the ESG
preference; HXS.TO joins the US-stock slot's candidates and VDU.TO the international slot's, below the reference
funds. The 10 default funds, their weights and every number in the reports are unchanged.

### Region changes

| Market | Region (3.0.2 -> 3.0.3) | Funds |
|---|---|---|
| CA | Global -> Asia-Pacific | 1 |
| CA | Global -> Canada | 10 |
| CA | Global -> International developed | 3 |
| CA | Global -> US | 54 |
| CA | US -> International developed | 2 |
| US | Global -> International developed | 7 |
| US | Global -> US | 30 |
| US | US -> Asia-Pacific | 1 |
| US | US -> International developed | 1 |

Eligible Canadian funds whose region changes:

| Fund | Name | Region |
|---|---|---|
| DLR.TO | Global X U.S. Dollar Currency ETF | Global -> US |
| HAB.TO | Global X Active Corporate Bond ETF Common | Global -> Canada |
| HBA.TO | Hamilton Australian Bank Equal-Weight Index ETF | Global -> Asia-Pacific |
| HBNK.TO | Global X Equal Weight Banks Index ETF | Global -> Canada |
| HFR.TO | Global X Active Ultra-Short Term Investment Grade Bond ETF | Global -> Canada |
| HPR.TO | Global X Active Preferred Share ETF Common | Global -> Canada |
| HTB.TO | Global X US 7-10 Year Treasury Bond Index Corporate Class ETF | Global -> US |
| HXQ.TO | Global X NASDAQ-100 Index Corporate Class ETF | Global -> US |
| HXS.TO | Global X S&P 500 Corporate Class ETF | Global -> US |
| QQCC.TO | Global X NASDAQ-100 Covered Call ETF | Global -> US |
| USCC.TO | Global X S&P 500 Covered Call ETF | Global -> US |
| USCL.TO | Global X Enhanced S&P 500 Covered Call ETF | Global -> US |
| VBG.NE | Vanguard Global ex-U.S. Aggregate Bond Index ETF (CAD-hedged) | Global -> International developed |
| VDU.TO | Vanguard FTSE Developed All Cap ex U.S. Index ETF | US -> International developed |
| VEF.TO | Vanguard FTSE Developed All Cap ex U.S. Index ETF (CAD-hedged) | US -> International developed |
| VI.TO | Vanguard FTSE Developed All Cap ex Nrth Amer Idx ETF (CAD-Hdd) | Global -> International developed |
| VIU.TO | Vanguard FTSE Developed All Cap ex North Amer Idx ETF | Global -> International developed |

### Leverage changes

| Fund | Market | Name | Leverage | Eligible now |
|---|---|---|---|---|
| CANY.TO | CA | Evolve Canadian Equity UltraYield ETF | 2.0 -> 1.0 | False |
| CGMD.TO | CA | MegaShort (-3X) Canadian Gold Miners Daily Leveraged Alternative ETF | 3.0 -> -3.0 | False |
| CMCL.TO | CA | Global X Enhanced All-In-One Commodity Producers Equity Covered Call ETF | 2.0 -> 1.0 | False |
| CNDI.TO | CA | BetaPro S&P/TSX 60 Daily Inverse ETF | 2.0 -> -1.0 | False |
| HDIF.TO | CA | Harvest Diversified Monthly Income ETF - Class A Units | 2.0 -> 1.0 | True |
| HND.TO | CA | BetaPro Natural Gas Inverse Leveraged Daily Bear ETF | 2.0 -> -2.0 | False |
| HOD.TO | CA | BetaPro Crude Oil Inverse Leveraged Daily Bear ETF | 2.0 -> -2.0 | False |
| JNJY.TO | CA | Harvest JnJ Enhanced High Income Shares ETF Class A CAD | 2.0 -> 1.0 | False |
| QQQD.TO | CA | MegaShort (-3X) NASDAQ-100 Daily Leveraged Alternative ETF | 3.0 -> -3.0 | False |
| SOLL-B.TO | CA | Purpose Solana ETF Currency Non-Hedged Units | 2.0 -> 1.0 | False |
| SOLL-U.TO | CA | Purpose Solana ETF Currency Non-Hedged Units USD | 2.0 -> 1.0 | False |
| SOLL.TO | CA | Purpose Solana ETF Currency Hedged Units | 2.0 -> 1.0 | False |
| SOXD.TO | CA | MegaShort (-3X) US Semiconductors Daily Leveraged Alternative ETF | 3.0 -> -3.0 | False |
| SPXI.TO | CA | BetaPro S&P 500 Daily Inverse ETF | 2.0 -> -1.0 | False |
| SPYD.TO | CA | MegaShort (-3X) S&P 500 Daily Leveraged Alternative ETF | 3.0 -> -3.0 | False |
| TECY.TO | CA | Evolve NASDAQ Technology UltraYield ETF | 2.0 -> 1.0 | False |
| AIQD | US | MicroSectors -3? Short Artificial Intelligence (AI) ETNs | -1.0 -> -3.0 | False |
| AIQU | US | MicroSectors 3? Long Artificial Intelligence (AI) ETNs | 2.0 -> 3.0 | False |
| NVDW | US | Roundhill NVDA WeeklyPay ETF | 2.0 -> 1.0 | False |
| NVII | US | REX NVDA Growth & Income ETF | 2.0 -> 1.0 | False |
| PFFL | US | ETRACS 2xMonthly Pay Leveraged Preferred Stock Index ETN | 1.0 -> 2.0 | False |
| TDAX | US | TDAQ Lift ETF | 2.0 -> 1.0 | False |
| TSII | US | REX TSLA Growth & Income ETF | 2.0 -> 1.0 | False |
| TSLW | US | Roundhill TSLA WeeklyPay ETF | 2.0 -> 1.0 | False |
| TSYX | US | TSPY Lift ETF | 2.0 -> 1.0 | False |
| WMTI | US | REX WMT Growth & Income ETF | 2.0 -> 1.0 | False |
| XUSP | US | Innovator Uncapped Accelerated U.S. Equity ETF | 2.0 -> 1.0 | True |

### "Check" rows left on eligible funds, and the rulings

| Fund | Name | Ours | Name rule says | Ruling |
|---|---|---|---|---|
| MNS.TO | Royal Canadian Mint - Canadian Silver Reserves | Global | Canada | kept Global: bullion is a global commodity, and Canada would take MNT out of the gold slot |
| MNT.TO | Royal Canadian Mint - Canadian Gold Reserves | Global | Canada | kept Global: bullion is a global commodity, and Canada would take it out of the gold slot |
| TCON.TO | TD Conservative ETF Portfolio | Canada | Global | kept: a multi-asset portfolio, which no slot reads by region; its label comes from TMX's holdings data |
| XBM.TO | iShares S&P/TSX Global Base Metals Index ETF | Canada | Global | kept Canada: an S&P/TSX index of miners listed in Canada; Global would put it in the international slot |
| XGD.TO | iShares S&P/TSX Global Gold Index ETF | Canada | Global | kept Canada: an S&P/TSX index of miners listed in Canada; Global would put it in the international slot |

## Fields added from the data layer

`robokit/universe.py:add_team_data` merges `data/v2/robokit_bridge_ca.csv` when it is present (it is local data,
like the rest of `data/v2/`; without it the universe is unchanged): inception date, fund age, a risk rating
calculated with the CSA method (not the issuer's published rating), distribution frequency and yield, and a
secondary theme, in columns `rk_*`. Its MER fills only our blanks and only between 0.05% and 3%; its AUM fills only
our blanks and never with a zero, which the source uses for a missing value (three BMO US Treasury funds would
otherwise have failed the size screen with "0M in assets"). Each filled value says so in the fund's note.

MER coverage of eligible Canadian funds rises from 594 of 636 to 622 of 637. The eligible funds that had none:

| Fund | Name | MER from the data layer |
|---|---|---|
| ARTI.TO | Evolve Artificial Intelligence Fund ETF | 0.96% |
| ATAP.NE | AGF Energy Transition and Adaptation ETF |  |
| BGU.TO | Bristol Gate Concentrated US Equity ETF | 0.85% |
| CBNK.TO | Mulvihill Canadian Bank Enhanced Y ETF | 0.79% |
| CMNY.TO | CI Money Market ETF C$ Series |  |
| FBTC.TO | Fidelity Advantage Bitcoin ETFTM | 0.35% |
| FCGS.NE | Fidelity Global Small Cap Opportunities Fund - ETF | 1.11% |
| FCNS.NE | Fidelity All-in-One Conservative ETF CAD | 0.39% |
| FETH.TO | Fidelity Advantage Ether ETF - L | 0.43% |
| IIMF.TO | CI Invesco International Developed Multifactor Index ETF |  |
| IUMF.TO | CI Invesco Russell 1000 Multifactor Index ETF |  |
| MHCD.TO | Middlefield Healthcare Dividend ETF | 1.23% |
| MNS.TO | Royal Canadian Mint - Canadian Silver Reserves |  |
| MNT.TO | Royal Canadian Mint - Canadian Gold Reserves |  |
| MREL.TO | Middlefield Real Estate Dividend ETF | 1.07% |
| PBY.TO | Lysander-Canso Credit Income ActivETF |  |
| QQQT.TO | Evolve NASDAQ Technology Index Fund CAD Hedged |  |
| RCDC.TO | RBC Canadian Dividend Covered Call ETF | 0.71% |
| SPFD.TO | Mulvihill Enhanced Split Preferred Share ETF | not used: 0.03% is most likely the wrong unit |
| SVR-C.TO | iShares Silver Bullion ETF (Non-Hedged) |  |
| SVR.TO | iShares Silver Bullion ETF (CAD-Hedged) | 0.66% |
| XAGG.TO | iShares U.S. Aggregate Bond Index ETF | 0.19% |
| XCSR.TO | iShares ESG Advanced MSCI Canada Index ETF | 0.17% |
| XDG.TO | iShares Core MSCI Global Quality Dividend Index ETF | 0.22% |
| XDGH.TO | iShares Core MSCI Global Quality Dividend Index ETF (CAD-Hedged) | 0.22% |
| XDU.TO | iShares Core MSCI US Quality Dividend Index ETF | 0.16% |
| XESG.TO | iShares ESG Aware MSCI Canada Index ETF | 0.17% |
| XMC.TO | iShares S&P U.S. Mid-Cap Index ETF | 0.16% |
| XMM.TO | iShares MSCI Min Vol Emerging Markets Index ETF | 0.42% |
| XMU.TO | iShares MSCI Min Vol USA Index ETF | 0.33% |
| XSAB.TO | iShares ESG Aware Canadian Aggregate Bond Index ETF | 0.17% |
| XSEA.TO | iShares ESG Aware MSCI EAFE Index ETF | 0.28% |
| XSTB.TO | iShares ESG Aware Canadian Short Term Bond Index ETF | 0.17% |
| XSTH.TO | iShares 0-5 Year TIPS Bond Index ETF (CAD-Hedged) | 0.12% |
| XSTP.TO | iShares 0-5 Year TIPS Bond Index ETF | 0.13% |
| XSUS.TO | iShares ESG Aware MSCI USA Index ETF | 0.23% |
| XUU.TO | iShares Core S&P U.S. Total Market Index ETF | 0.07% |
| ZGEQ.NE | BMO Global Equity Active ETF Series |  |
| ZGIN.NE | BMO Global Innovators Active ETF Series |  |
| ZGRT.NE | BMO Global REIT Active ETF Series |  |
| ZMMK.TO | BMO Mutual Funds - BMO Money Market Fund |  |
| ZWQT.TO | BMO Global Enhanced Income Fund Series ETF |  |

The 14 still blank are missing in both datasets; the data layer is filling them from ETF Facts.

## Not done

- **The 61 funds this universe does not list** (34 TSX, 27 Cboe Canada; 13 launched before October 2023, 8 after,
  and 40 have no inception date in the data layer). Adding them needs their prices, which means a data refresh that
  changes every number, and at most 13 could pass the 36-month history screen. Left for the next refresh.
- **The other "check" rows** (74, all on ineligible funds: 39 Global where the name rule says US, 13 Canada where
  it says US, and 22 others) were not reviewed fund by fund; none is a fund the optimizer can use.
