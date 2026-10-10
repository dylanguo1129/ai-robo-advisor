# Currency-hedging labels corrected in 3.0.2

Found on 9 Oct 2026 while the team's optimizer report was reviewed: VALT, the Canadian gold fund, is CI's CAD-hedged
unit but was labelled unhedged, because the label is read from the fund's name and VALT's name has no hedging word.
A search of the fund list for the same pattern, checked against the issuers' own documents, found the rest. The
name rule (robokit/classify.py) now reads "C$ Hedged Series" and "Currency Neutral" as hedged and "Non-Currency"
or "Non-FX Hedged" as not hedged; units whose names carry no hedging word get a sourced override
(`LABEL_OVERRIDES`), and the source is shown in the fund's `why` note.

Checks: `python scripts/e7e_universe_diff.py data/v2/universe_3.0.1.pkl data/v2/universe.pkl` reports the changed
columns below and no slot whose candidate list changes; eligibility is unchanged (636 Canadian, 1,997 US).
VALT is the only changed fund on either reference shelf. HUG leaves the gold slot's swap list (futures-based), and
with it the strict point-in-time shelf of 2012 to 2022 (robokit/research.py now applies the swap gate's rule). Its stand-in before February 2021 is now GLD in US dollars,
unconverted (correlation 0.986 with VALT's own returns), instead of CGL-C and GLD converted to CAD (0.917 and
0.926). The effect on the registered evaluation is in docs/RESEARCH_LOG.md section 13.

37 listings changed:

| Listing | Market | Name | Change | Eligible | Why |
|---|---|---|---|---|---|
| BASE.TO | CA | Evolve Global Materials & Mining Enhanced Yield Index ETF | hedged False → True | yes | issuer: Evolve: BASE (CAD Hedged), BASE.B (CAD Unhedged) (BASE fund overview, Sep 2026) |
| BND-U.TO | CA | Purpose Global Bond Fund USD ETF Non-Currency Hedged | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| BTCC-B.TO | CA | Purpose Bitcoin ETF Non-Currency Hedged Units | hedged True → False | yes | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| BTCC-J.TO | CA | Purpose Bitcoin CAD ETF Non-Currency Hedged Carbon Offset Units | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| BTCC-U.TO | CA | Purpose Bitcoin ETF Non-Currency Hedged Units | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| BTCO-B.TO | CA | Purpose Core Bitcoin ETF CAD Non-Currency Hedged | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| BTCO-U.TO | CA | Purpose Core Bitcoin ETF USD Non-Currency Hedged | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| BTCX.TO | CA | CI Galaxy Bitcoin ETF C$ Hedged Series | hedged False → True | no | name rule: 'C$ Hedged Series' is hedged to CAD |
| BTCY-B.TO | CA | Purpose Bitcoin Yield ETF CAD ETF Non-Currency Hedged Units | hedged True → False | yes | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| BTCY-U.TO | CA | Purpose Bitcoin Yield ETF - USD ETF Non-Currency Hedged Units | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| CCCX.TO | CA | CI Galaxy Core Multi-Crypto ETF C$ Hedged Series | hedged False → True | no | name rule: 'C$ Hedged Series' is hedged to CAD |
| CDLB.TO | CA | CI DoubleLine Total Return Bond US$ Fund ETF C$ Hedged Series | hedged False → True | no | name rule: 'C$ Hedged Series' is hedged to CAD |
| CESG.NE | CA | CI MSCI World ESG Impact Index ETF - Common Units | hedged False → True | no | issuer: CI: CESG's currency is CAD Hedged, CESG.B's CAD (CI MSCI World ESG Impact Index ETF profiles) |
| CROP-U.TO | CA | Purpose Credit Opportunities Fund - U.S. Dollar Denominated ETF Non-Currency Hedged Units | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| DGR.TO | CA | CI U.S. Quality Dividend Growth Index ETF | hedged False → True | yes | issuer: CI: DGR's currency is CAD Hedged, DGR.B's CAD (CI U.S. Quality Dividend Growth Index ETF profiles) |
| ETHH-B.TO | CA | Purpose Ether CAD ETF Non-Currency Hedged | hedged True → False | yes | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| ETHH-U.TO | CA | Purpose Ether USD ETF Non-Currency Hedged | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| ETHO-B.TO | CA | Purpose Core Ether ETF CAD Non-Currency Hedged | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| ETHO-U.TO | CA | Purpose Core Ether ETF USD Non-Currency Hedged | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| ETHX.TO | CA | CI Galaxy Ethereum ETF (ETF C$ Hedged Series) | hedged False → True | no | name rule: 'C$ Hedged Series' is hedged to CAD |
| ETHY-B.TO | CA | Purpose Ether Yield ETF CAD ETF Non-Currency Hedged Units | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| ETHY-U.TO | CA | Purpose Ether Yield ETF - USD ETF Non-Currency Hedged Units | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| FCQH.TO | CA | Fidelity U.S. High Quality Currency Neutral ETF | hedged False → True | no | name rule: 'Currency Neutral' is hedged |
| FCVH.TO | CA | Fidelity U.S. Value Currency Neutral ETF | hedged False → True | yes | name rule: 'Currency Neutral' is hedged |
| FLX-B.TO | CA | Purpose Global Flexible Credit Fund - ETF Non-currency hedged CAD | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| FLX-U.TO | CA | Purpose Global Flexible Credit Fund - ETF Non-currency hedged USD | hedged True → False | no | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| HHL.TO | CA | Harvest Healthcare Leaders Income ETF | hedged False → True | yes | issuer: Harvest: Class A (HHL) is CAD-Hedged, HHL.B CAD-Unhedged (harvestportfolios.com/etf/hhl) |
| HUG.TO | CA | Global X Gold ETF | hedged False → True; derivatives (none) → futures; satellite_only False → True | yes | issuer: Global X: HUG tracks a rolling gold futures index and hedges its US dollar value to CAD (HUG product sheet, Oct 2026) |
| IQD.TO | CA | CI International Quality Dividend Growth Index ETF | hedged False → True | no | issuer: CI: IQD's currency is CAD Hedged, IQD.B non-hedged (CI International Quality Dividend Growth Index ETF profiles) |
| KILO-B.TO | CA | Purpose Gold Bullion Non-FX Hedged | hedged True → False | yes | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| KILO.TO | CA | Purpose Gold Bullion Fund | hedged False → True | yes | issuer: Purpose: KILO is the ETF (FX Hedged) series, KILO.B the non-currency hedged units (purposeinvest.com fund page) |
| SBT-B.TO | CA | Silver Bullion Trust ETF Non-Currency Hedged Units | hedged True → False | yes | name rule: 'Non-Currency' or 'Non-FX Hedged' means not hedged |
| SOLX.TO | CA | CI Galaxy Solana ETF C$ Hedged Series | hedged False → True | no | name rule: 'C$ Hedged Series' is hedged to CAD |
| TXF.TO | CA | CI Tech Giants Covered Call ETF Common Units | hedged False → True | yes | issuer: CI: TXF's currency is CAD Hedged, TXF.B unhedged (CI Tech Giants Covered Call ETF profiles) |
| VALT.TO | CA | CI Gold Bullion ETF | hedged False → True | yes | issuer: CI: VALT is the ETF C$ Hedged Series, VALT.B the C$ Unhedged Series (CI Gold Bullion ETF monthly profile, Aug 2026) |
| FCUH.TO | CA | Fidelity U.S. High Dividend Currency Neutral ETF | hedged False → True | no | name rule: 'Currency Neutral' is hedged |
| HFXI | US | NYLIM FTSE International Equity Currency Neutral ETF | hedged False → True | yes | name rule: 'Currency Neutral' is hedged |

Issuer documents behind the overrides (read on 9 Oct 2026):

- VALT: CI Gold Bullion ETF monthly profile (funds.cifinancial.com .../52496/CIGoldBullionFund_Monthly_Profile.pdf):
  "TSX TICKER : VALT ... Currency CAD Hedged"; CI press release of 22 Mar 2021 (VALT.B): "ETF C$ Hedged Series units
  currently trade under the ticker symbols ... VALT".
- HHL: harvestportfolios.com/etf/hhl, Key ETF Details: Class A (HHL) "CAD-Hedged", Class B (HHL.B) "CAD-Unhedged".
- BASE: Evolve BASE overview, Sep 2026: "ETF Ticker(s): BASE (CAD Hedged) BASE.B (CAD Unhedged)".
- KILO: purposeinvest.com/funds/purpose-gold-bullion-fund: "ETF (FX Hedged) (KILO)".
- HUG: Global X HUG product sheet (Oct 2026): "Seeks to hedge the U.S. dollar value of its portfolio to the Canadian
  dollar at all times"; it tracks the "Solactive Gold Front Month MD Rolling Futures Index ER".
- DGR, TXF, CESG, IQD: CI monthly profiles, each "Currency CAD Hedged" (their .B units: "Currency CAD" or
  non-hedged).
- FCVH and the other Fidelity Currency Neutral ETFs: Fidelity ETF prospectus, "uses derivative instruments, such as
  foreign currency forward contracts, to seek to hedge its U.S. dollar exposure to the Canadian dollar".
- Purpose Non-Currency Hedged units (BTCC.B, SBT.B and the rest): their ETF Facts and prospectus, e.g. BTCC.B
  "Canadian dollar denominated ETF non-currency hedged units".
