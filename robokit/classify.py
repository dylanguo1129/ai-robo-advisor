"""Rule-based classification of every ETF listing.

Why rules and not a model: every label must be explainable to a user ("this
fund is marked leveraged because its name says 2X and TMX files it under
Trading-Leveraged Equity"), reproducible, and testable. The rules read, in
order of trust:

1. hard evidence in the name (2X, Bear, Daily Inverse, Covered Call, Buffer,
   Target 2030, Bitcoin, Hedged to CAD, ...);
2. the provider's category (Yahoo / Morningstar category for US funds, TMX
   investment style for Canadian funds);
3. the look-through portfolio (TMX sector weights: the "Other" share is the
   non-equity part; region weights);
4. keywords for asset class, region and theme.

Each output row carries ``why`` notes naming the rule that fired, so the
interface can answer "why is this fund labelled X?".

Fields produced (the brief's list: asset class, theme, industry, currency,
volatility, leverage, strategy, rebalancing, cost):
  asset_class, region, theme, sector, leverage (signed multiple), inverse,
  single_stock, derivatives, strategy, hedged, currency, crypto, cdr,
  target_date, esg, issuer, mer, aum, inception, plus the ``why`` notes.
Volatility and rebalancing-related fields (history, turnover proxy) are added
from prices in ``robokit.universe``.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- vocabularies
ASSET_CLASSES = (
    "Equity",
    "Fixed income",
    "Cash",
    "Real estate",
    "Commodity",
    "Multi-asset",
    "Alternative",
    "Crypto",
    "Single stock",
)
REGIONS = (
    "Canada",
    "US",
    "North America",
    "International developed",
    "Emerging markets",
    "Global",
    "Europe",
    "Asia-Pacific",
    "Japan",
    "China",
    "Other single country",
)

ISSUERS = [
    (r"^ishares|\bishares\b|blackrock", "BlackRock iShares"),
    (r"^vanguard|\bvanguard\b", "Vanguard"),
    (r"^bmo\b|\bbmo\b", "BMO"),
    (r"^global x|horizons|^betapro", "Global X (Mirae)"),
    (r"^ci\b|\bci global|\bci canadian|\bci u\.?s|\bci munro|^ci ", "CI Global"),
    (r"^td\b|\btd q\b|^td ", "TD"),
    (r"^rbc\b|\brbc\b", "RBC"),
    (r"^fidelity\b|^ft vest|^fidelity", "Fidelity"),
    (r"^invesco\b", "Invesco"),
    (r"^mackenzie\b", "Mackenzie"),
    (r"^franklin\b", "Franklin Templeton"),
    (r"^desjardins\b", "Desjardins"),
    (r"^harvest\b", "Harvest"),
    (r"^hamilton\b", "Hamilton"),
    (r"^purpose\b", "Purpose"),
    (r"^evolve\b", "Evolve"),
    (r"^ninepoint\b", "Ninepoint"),
    (r"^manulife\b", "Manulife"),
    (r"^dynamic\b", "Dynamic (1832)"),
    (r"^nbi\b|national bank", "National Bank"),
    (r"^brompton\b", "Brompton"),
    (r"^first trust\b|^ft\b", "First Trust"),
    (r"^agf\b", "AGF"),
    (r"^wealthsimple\b", "Wealthsimple"),
    (r"^capital group\b", "Capital Group"),
    (r"^avantis\b", "Avantis"),
    (r"^cibc\b", "CIBC"),
    (r"^scotia\b", "Scotia"),
    (r"^savvylong\b", "SavvyLong"),
    (r"^mulvihill\b", "Mulvihill"),
    (r"^picton\b", "Picton Mahoney"),
    (r"^accelerate\b", "Accelerate"),
    (r"^spdr\b|state street", "State Street SPDR"),
    (r"^schwab\b", "Schwab"),
    (r"^proshares\b", "ProShares"),
    (r"^direxion\b", "Direxion"),
    (r"^ark\b", "ARK"),
    (r"^wisdomtree\b", "WisdomTree"),
    (r"^vaneck\b", "VanEck"),
    (r"^jpmorgan\b|^jp morgan", "JPMorgan"),
    (r"^dimensional\b", "Dimensional"),
    (r"^pimco\b", "PIMCO"),
    (r"^goldman sachs\b", "Goldman Sachs"),
    (r"^xtrackers\b", "DWS Xtrackers"),
    (r"^global x\b", "Global X"),
    (r"^yieldmax\b", "YieldMax"),
    (r"^defiance\b", "Defiance"),
    (r"^graniteshares\b", "GraniteShares"),
    (r"^innovator\b", "Innovator"),
    (r"^pacer\b", "Pacer"),
    (r"^amplify\b", "Amplify"),
    (r"^kraneshares\b", "KraneShares"),
    (r"^t-rex\b", "REX/T-REX"),
    (r"^rex\b", "REX/T-REX"),
    (r"^janus\b", "Janus Henderson"),
    (r"^american century\b", "American Century"),
    (r"^nuveen\b", "Nuveen"),
    (r"^columbia\b", "Columbia"),
    (r"^hartford\b", "Hartford"),
    (r"^victoryshares\b", "VictoryShares"),
    (r"^bondbloxx\b", "BondBloxx"),
    (r"^sprott\b", "Sprott"),
    (r"^3iq\b", "3iQ"),
    (r"^grayscale\b", "Grayscale"),
    (r"^bitwise\b", "Bitwise"),
]

# ---------------------------------------------------------------- name rules
_LEV = [
    # "2X", "-3x", "1.25x", "(-3X)", "2xLeveraged", "3×" (and "3?", the same sign garbled in a listing file):
    # the sign belongs to the number even after a bracket
    (
        r"(?<![\w.])(-?\d(?:\.\d+)?)\s*(?:(?:x|×)(?=$|[^a-z0-9]|leveraged|monthly)|\?(?=\s+(?:long|short|bull|bear|leveraged|inverse)\b))",
        None,
    ),
    (r"\bultrapro\s+short\b", -3.0),
    (r"\bultrapro\b", 3.0),
    (r"\bultrashort\b", -2.0),
    # "Ultra" is leverage only as a product line ("ProShares Ultra QQQ"), not in "Ultra-Short Income" or "Ultra Dividend"
    (r"\bultra\b(?![- ](short|low|dividend|buffer)\b)", 2.0),
    (r"\bdouble\s+short\b", -2.0),
    (r"\bdouble\s+long\b", 2.0),
    (r"\btriple\s+short\b", -3.0),
    (r"\btriple\s+long\b", 3.0),
]
BEAR = (
    r"\b(bear|inverse|(?<!ultra-)(?<!ultra )short\b(?!.?term|.?duration|.?maturity|er)|ultrashort|megashort|savvyshort)"
    r"|(?<![\w.])-\d(?:\.\d+)?\s*(?:(?:x|×)(?![a-z0-9])|\?(?=\s+(?:short|bear|inverse)\b))"
)
# words that make a name a geared or inverse daily product; a fund category alone does not ("Enhanced" funds borrow
# up to 1.25x and are not daily-reset, and some crypto funds are filed under "Trading-Leveraged")
GEARED_WORDS = r"\b(leverage|leveraged|bull|bear|inverse|ultra|ultrapro|ultrashort|megalong|megashort|savvylong|savvyshort)\b"
SINGLE_STOCK_HINT = (
    r"\b(yield shares|highshares|enhanced high income shares|option income strategy|yieldboost|"
    r"savvylong|daily target 2x|2x long|2x short|autocallable|growth & income etf|"
    r"\((aapl|msft|nvda|tsla|amzn|googl?|meta|amd|nflx|coin|pltr|mstr|hood|avgo|spcx|dol)\)|"
    r"enhanced yield shares|yield maximizer)\b"
)
COMPANY_SUFFIX = r"(\binc\.?$|, inc\.?$|\bcorporation$|\bcorp\.?$|\bplc$|\bag$|\bltd\.?$|\bn\.v\.$|\bs\.a\.$|\bholdings corporation$|\bco\.?$|\bcompany$|\bse$)"
FUND_WORDS = r"\b(etf|fund|portfolio|index|trust|shares|pool|series|units?|class|income|yield)\b"

CRYPTO = r"\b(bitcoin|ether(eum)?|solana|xrp|crypto|blockchain|digital asset|btc|eth)\b"
GOLD = r"\b(gold|silver|platinum|palladium|precious metals?|bullion)\b"
# a metal in the name means a bullion fund only when the fund is not about the companies that mine it
NOT_BULLION = r"\b(miners?|mining|producers?|royalt\w*|equity|equities|companies|stocks?|explorers?|juniors?)\b"
COMMODITY = (
    r"\b(commodit\w*|oil fund|crude oil|natural gas|brent|wti|agricultur\w* (?:fund|strategy)|grains|copper index|uranium futures)\b"
)
REAL_ESTATE = r"\b(reits?|real estate|property|properties)\b"
CASH = r"\b(high interest savings|savings etf|money market|cash management|t-?bill|treasury bill|premium cash|cash etf|ultra short|0-3 month|1-3 month treasury|ultrashort bond|floating rate note|short term discount)\b"
BOND = r"\b(bond|fixed income|treasury|treasuries|govt|government|aggregate|corporate(?! class)|municipal|muni|debt|income fund|credit|loan|tips|real return|inflation[- ]protected|inflation[- ]linked|mortgage|mbs|clo|preferred|fixed rate|ibonds|bulletshares|target 20\d\d|term tips|investment grade|high yield|junk|duration)\b"
BALANCED = r"\b(balanced|growth etf portfolio|conservative etf portfolio|conservative etf$|asset allocation|all-in-one|all equity etf portfolio|income etf portfolio|conservative income|growth portfolio|allocation etf|target date|retirement|multi-asset|monthly income)\b"
# one foreign country (not a home market); "ex China" or "ex-Japan" names a region without that country
SINGLE_COUNTRY = (
    r"(?<!ex )(?<!ex-)\b(argentina|australia|austria|belgium|brazil|chile|china|colombia|denmark|egypt|finland|france|germany"
    r"|greece|hong kong|india|indonesia|ireland|israel|italy|japan|south korea|korea|kuwait|malaysia|mexico|netherlands"
    r"|new zealand|nigeria|norway|pakistan|peru|philippines|poland|portugal|qatar|saudi arabia|saudi|singapore"
    r"|south africa|spain|sweden|switzerland|taiwan|thailand|turkey|uae|united arab emirates|united kingdom|uk|vietnam)\b"
)
ALTERNATIVE = r"\b(long/short|long-short|market neutral|managed futures|alternative|arbitrage|merger|hedge fund|tail risk|volatility|vix|trend|absolute return|multi-strategy|buffer|defined outcome|dual directional|accelerated)\b"

REGION_RULES = [
    # "All Country World ex Canada" is global stocks without Canada, not a Canadian fund
    (r"\b(all country|world|acwi|global)\b[^;]*\bex[- ]?canada\b", "Global"),
    (r"\bex[- ]?canada\b", "International developed"),
    (r"\btips\b|\btreasury inflation", "US"),
    (r"\bs&p/tsx|\btsx\b|\bcanadian\b|\bcanada\b|\bcdn\b|\bmaple\b", "Canada"),
    (
        r"\bemerging\b|\bem\b|\bbrics?\b|\bfrontier\b|\bindia\b|\bbrazil\b|\bmexico\b|\bvietnam\b|\bindonesia\b|\bsouth africa\b|\btaiwan\b|\bkorea\b|\bsaudi\b|\blatin america\b",
        "Emerging markets",
    ),
    (r"\bchin(?:a|ese)\b|\bhang seng\b|\bcsi\b|\bhong kong\b", "China"),
    (r"\bjapan\b|\bnikkei\b|\btopix\b", "Japan"),
    (
        r"\beurope\b|\beuropean\b|\beuro\b|\beurozone\b|\bstoxx\b|\bgermany\b|\bfrance\b|\buk\b|\bunited kingdom\b|\bswitzerland\b|\bitaly\b|\bspain\b|\bnetherlands\b|\bsweden\b",
        "Europe",
    ),
    (r"\basia\b|\bpacific\b|\baustralian?\b|\bsingapore\b", "Asia-Pacific"),
    (
        # "ex U.S.", "ex-US", "ex USA", "ex North Amer(ica)", "ex Nrth Amer": the name excludes the US
        r"\beafe\b|\binternational\b|\bdeveloped markets?\b|\bex[- ]?u\.?s\.?a?\b|\bex[- ]?n(?:o)?rth amer|\bintl\b|\bforeign\b|\bworld ex\b",
        "International developed",
    ),
    (r"\bglobal\b|\bworld\b|\ball[- ]world\b|\bacwi\b|\ball country\b", "Global"),
    (r"\bnorth american?\b", "North America"),
    (
        r"\bu\.?s\.?\b|\bus\b|\bamerican?\b|\bs&p 500\b|\bs&p500\b|\bnasdaq\b|\bdow\b|\brussell\b|\bnyse\b|\busa\b|\bunited states\b|\bcrsp\b|\btotal stock market\b",
        "US",
    ),
]

THEME_RULES = [
    (
        "Covered call / option income",
        r"\b(covered call|option income|premium yield|enhanced yield|yield maximizer|buywrite|option writing|income target|premium income|yieldboost|enhanced income|highshares|daymax)\b",
    ),
    # word stems take \w* so plurals and compounds match ("Pharmaceuticals", "Industrials", "Buffer20", "Cybersecurity")
    ("Buffer / defined outcome", r"\b(buffer\w*|defined outcome|dual directional|accelerated|autocallable|floor\d*)\b"),
    ("Dividend", r"\b(dividends?|high yield equity|aristocrats?|shareholder yield)\b"),
    ("Low volatility", r"\b(low vol|low volatility|minimum volatility|min vol|defensive)\b"),
    (
        "ESG / climate",
        r"\b(esg|sustainable|sustainability|climate|paris-aligned|low carbon|responsible|socially|fossil fuel free|clean|net zero|green bond)\b",
    ),
    (
        "Technology / AI",
        r"\b(technolog\w*|tech|artificial intelligence|ai|robotics|semiconductor\w*|cyber\w*|cloud|internet|software|innovation|digital|fintech|blockchain technologies|metaverse|5g|nasdaq-100|nasdaq 100)\b",
    ),
    ("Clean energy", r"\b(clean energy|solar|wind|renewable|hydrogen|battery|lithium|uranium|nuclear|electric vehicle|ev)\b"),
    ("Healthcare", r"\b(health\w*|biotech\w*|pharma\w*|medical|genomic\w*|longevity)\b"),
    ("Financials / banks", r"\b(banks?|financials?|insurance|lifeco|business development|bdcs?|capital markets|brokers?)\b"),
    ("Energy", r"\b(energy|oil|gas|pipelines?|midstream|mlps?)\b"),
    ("Materials / mining", r"\b(mining|miners|materials|metals|gold producers?|junior gold|steel)\b"),
    ("Infrastructure / utilities", r"\b(infrastructure|utilities|utility)\b"),
    ("Communication / media", r"\b(communication\w*|media|telecom\w*)\b"),
    ("Sector", r"\b(select sector|sector)\b"),
    ("Real estate", REAL_ESTATE),
    ("Consumer", r"\b(consumer|retail|staples|discretionary)\b"),
    ("Industrials", r"\b(industrial\w*|aerospace|defen[cs]e|transportation)\b"),
    (
        "Small / mid cap",
        r"\b(small[- ]?cap|mid[- ]?cap|smallcap|midcap|smcp|sm cap|smid|micro[- ]?cap|russell 2000|junior|extended market|completion)\b",
    ),
    ("Values screen", r"\b(sharia\w*|islamic|catholic|christian|biblical|faith\w*|ethical)\b"),
    ("Factor: value", r"\bvalue\b"),
    ("Factor: growth", r"\bgrowth\b(?! portfolio| etf portfolio| asset allocation)"),
    ("Factor: momentum", r"\bmomentum\b"),
    ("Factor: quality", r"\bquality\b"),
    (
        "Factor: other",
        r"\b(multi-?factor|factors?|rafi|fundamental\w*|profitability|alphadex|activebeta|moat|cash cows|smart beta|quant\w*|tilt\w*|targeted value|research enhanced|nxtgen|next gen|high beta|garp|revenue|diversified return|freedom)\b",
    ),
    ("Equal weight", r"\bequal[- ]weight\w*\b"),
    ("Single country", SINGLE_COUNTRY),
    (
        "Broad market",
        r"\b(total market|total stock|total international|total world|all[- ]cap|composite|s&p 500|s&p500|s&p 1500|tsx 60|tsx capped|msci world|msci eafe|msci acwi|acwi|msci usa|msci canada|msci emerging|ftse developed|ftse emerging|ftse canada|ftse all|developed world|developed markets|emerging markets|core s&p|core msci|total u\.s\.|all-world|all world|all country|all-country|broad market|market cap|russell 1000|russell 3000|crsp us|large[- ]cap|equity market|equity index|international equity|international stock|u\.s\. stock|us stock)\b",
    ),
]
# Index providers: a fund named after one tracks an index
INDEX_FAMILY = r"\b(msci|ftse|s&p|russell|nasdaq|dow jones|crsp|bloomberg|solactive|morningstar|stoxx|tsx)\b"
# Markers of a manager's own picks, beyond the word "active" (the strategy field)
ACTIVE_MARKERS = r"\b(active\w*|focus\w*|conviction|concentrated|research enhanced|congress\w*|unconstrained)\b"
# Currency hedging, read from the name: CAD-hedged units say "hedged", "hdg", "C$ Hedged Series" or "currency neutral"
# (Fidelity's word for hedged to CAD); "unhedged", "non-hedged" and "non-currency" or "non-FX hedged" units are not
# hedged. "Hedged Series" alone stays out: the US$ Hedged Series units trade in US dollars, not eligible in Canada.
HEDGED = (
    r"hedged(?! series)|\bhedge\b(?!d? fund)|cad-hedged|hedged to cad|\(cad hedged\)|usd hedged|cad-hd[dg]|\bhd[dg]\b"
    r"|c\$ hedged series|cad hedged series|currency neutral"
)
NOT_HEDGED = r"unhedged|un-hedged|non[- ]hedged|non[- ](?:fx|currency)[- ]hedged"
# Labels a fund's name cannot carry, from the issuer's own documents (3.0.2). A plain-named unit whose sibling says
# "Unhedged" is usually the hedged one, but only the issuer settles it, so every entry names its source; the source is
# shown in the fund's "why" note.
LABEL_OVERRIDES: dict[str, tuple[dict, str]] = {
    "VALT.TO": (
        {"hedged": True},
        "CI: VALT is the ETF C$ Hedged Series, VALT.B the C$ Unhedged Series (CI Gold Bullion ETF monthly profile, Aug 2026)",
    ),
    "HHL.TO": ({"hedged": True}, "Harvest: Class A (HHL) is CAD-Hedged, HHL.B CAD-Unhedged (harvestportfolios.com/etf/hhl)"),
    "BASE.TO": ({"hedged": True}, "Evolve: BASE (CAD Hedged), BASE.B (CAD Unhedged) (BASE fund overview, Sep 2026)"),
    "KILO.TO": (
        {"hedged": True},
        "Purpose: KILO is the ETF (FX Hedged) series, KILO.B the non-currency hedged units (purposeinvest.com fund page)",
    ),
    "HUG.TO": (
        {"hedged": True, "derivatives": "futures"},
        "Global X: HUG tracks a rolling gold futures index and hedges its US dollar value to CAD (HUG product sheet, Oct 2026)",
    ),
    "DGR.TO": ({"hedged": True}, "CI: DGR's currency is CAD Hedged, DGR.B's CAD (CI U.S. Quality Dividend Growth Index ETF profiles)"),
    "TXF.TO": ({"hedged": True}, "CI: TXF's currency is CAD Hedged, TXF.B unhedged (CI Tech Giants Covered Call ETF profiles)"),
    "CESG.NE": ({"hedged": True}, "CI: CESG's currency is CAD Hedged, CESG.B's CAD (CI MSCI World ESG Impact Index ETF profiles)"),
    "IQD.TO": (
        {"hedged": True},
        "CI: IQD's currency is CAD Hedged, IQD.B non-hedged (CI International Quality Dividend Growth Index ETF profiles)",
    ),
}


def _rx(p: str) -> re.Pattern:
    return re.compile(p, re.IGNORECASE)


_RX = {
    k: _rx(v)
    for k, v in dict(
        bear=BEAR,
        geared=GEARED_WORDS,
        single=SINGLE_STOCK_HINT,
        company=COMPANY_SUFFIX,
        fundwords=FUND_WORDS,
        crypto=CRYPTO,
        gold=GOLD,
        commodity=COMMODITY,
        realestate=REAL_ESTATE,
        cash=CASH,
        bond=BOND,
        balanced=BALANCED,
        alternative=ALTERNATIVE,
        notbullion=NOT_BULLION,
        activemarkers=ACTIVE_MARKERS,
        indexfamily=INDEX_FAMILY,
    ).items()
}
_REGION = [(_rx(p), r) for p, r in REGION_RULES]
_THEME = [(t, _rx(p)) for t, p in THEME_RULES]
_ISSUER = [(_rx(p), n) for p, n in ISSUERS]
_LEVRX = [(_rx(p), v) for p, v in _LEV]


def leverage_of(name: str) -> tuple[float, str | None]:
    """Signed leverage multiple read from the name; 1.0 when none is stated."""
    n = name or ""
    for rx, v in _LEVRX:
        m = rx.search(n)
        if m:
            mult = float(m.group(1)) if v is None else v
            if v is None and abs(mult) < 1.01:
                continue  # "1x" is not leverage
            if _RX["bear"].search(n) and mult > 0:
                mult = -mult
            return mult, f"name says '{m.group(0)}'"
    if _RX["bear"].search(n) and re.search(r"\b(daily|bear|inverse)\b", n, re.I):
        return -1.0, "name says bear/inverse"
    if re.search(
        r"^proshares short\b|^direxion daily .*\bbear\b|\bshort (s&p|qqq|dow|russell|20\+|7-10|high yield|msci|ftse|financials|real estate|oil|gold)|\b(gold|silver|oil) short\b",
        n,
        re.I,
    ):
        return -1.0, "name says it shorts an index (inverse fund)"
    return 1.0, None


def classify_row(r: pd.Series) -> dict:
    name = str(r.get("name") or r.get("shortName") or "")
    low = name.lower()
    style = str(r.get("tmx_investmentstyle") or "")
    ycat = str(r.get("yahoo_category") or "")
    why: list[str] = []
    out: dict = {}

    # ---- not an ETF at all: Canadian Depositary Receipts listed next to ETFs
    in_tmx = bool(r.get("in_tmx"))
    is_cdr = False
    if r.get("market") == "CA":
        if re.search(r"\bcdr\b", low):
            is_cdr = True
        elif not in_tmx and _RX["company"].search(name.strip()) and not _RX["fundwords"].search(name):
            is_cdr = True
    out["cdr"] = is_cdr
    if is_cdr:
        why.append("Canadian Depositary Receipt (a share of one company), not an ETF")

    # ---- leverage / inverse
    lev, lev_why = leverage_of(name)
    if "Leverage" in style or "Trading-Leveraged" in style or "Trading--Leveraged" in ycat or "Leveraged" in ycat:
        cat = f"category '{style or ycat}'"
        if abs(lev) == 1.0 and not _RX["geared"].search(name):
            why.append(f"{cat} says leveraged, but the name does not; kept at 1x")
        elif lev == 1.0:
            lev, lev_why = (2.0 if "Inverse" not in style + ycat else -2.0), cat
        elif lev == -1.0 and re.search(r"\bleveraged\b", name, re.I):
            lev, lev_why = -2.0, f"{cat} and an inverse fund named 'leveraged'"
    if "Inverse" in style or "Inverse" in ycat:
        lev = -abs(lev) if abs(lev) > 1 else -1.0
        lev_why = lev_why or f"category '{style or ycat}'"
    out["leverage"] = lev
    out["inverse"] = lev < 0
    if lev_why and lev != 1.0:
        why.append(f"leverage {lev:+g}x: {lev_why}")

    # ---- single-stock products (options or leverage on one company)
    single = bool(_RX["single"].search(name))
    if not single and abs(lev) != 1.0 and re.search(r"\b(long|short)\s+[A-Z]{2,5}\b", name):
        single = True
    out["single_stock"] = single and not is_cdr
    if out["single_stock"]:
        why.append("built on one company's shares (single-stock ETF)")

    # ---- asset class
    ac = None
    if is_cdr:
        ac = "Single stock"
    elif out["single_stock"]:
        ac = "Single stock"
    elif _RX["crypto"].search(name) and not re.search(r"blockchain technolog|blockchain & fintech|fintech", low):
        ac = "Crypto"
        why.append("crypto asset in the name")
    elif re.search(r"target-date|target date|retirement 20\d\d", low) or ycat.startswith("Target-Date"):
        ac = "Multi-asset"
        why.append("target-date fund")
    elif ycat in ("Real Estate", "Global Real Estate") or (_RX["realestate"].search(name) and not _RX["bond"].search(name)):
        ac = "Real estate"
        why.append("real estate in category or name")
    elif (
        (_RX["gold"].search(name) and not _RX["notbullion"].search(name) and not _RX["bond"].search(name) and not _holds_stocks(r))
        or ycat in ("Commodities Focused", "Commodities Broad Basket")
        or (
            _RX["commodity"].search(name)
            and not re.search(r"\b(producers?|miners?|equity|companies|stocks?|energy etf|covered call)\b", low)
        )
    ):
        ac = "Commodity"
        why.append("commodity or bullion fund")
    elif (
        _RX["cash"].search(name)
        or ycat in ("Ultrashort Bond", "Money Market - Taxable")
        or "Ultra short" in style
        or "Money Market" in style
    ):
        ac = "Cash"
        why.append("cash, T-bill or savings fund")
    elif (
        _RX["balanced"].search(name)
        or ycat.startswith("Allocation")
        or "Allocation" in style
        or "balanced" in style.lower()
        or "Target" in ycat
    ):
        ac = "Multi-asset"
        why.append("balanced / asset-allocation fund")
    elif (
        ycat
        in (
            "Long-Short Equity",
            "Multialternative",
            "Managed Futures",
            "Market Neutral",
            "Event Driven",
            "Macro Trading",
            "Relative Value Arbitrage",
            "Systematic Trend",
            "Equity Hedged",
            "Derivative Income",
            "Defined Outcome",
        )
        or style in ("Multi Alternative",)
        or (_RX["alternative"].search(name) and not re.search(r"covered call|enhanced yield|buffer", low) and not _RX["bond"].search(name))
    ):
        if ycat in ("Derivative Income", "Defined Outcome") or re.search(r"buffer|defined outcome|dual directional", low):
            ac = "Equity"
            why.append("equity with an options overlay")
        else:
            ac = "Alternative"
            why.append(f"alternative strategy ({ycat or style or 'name'})")
    elif (
        (_RX["bond"].search(name) and not re.search(r"\b(equity|stocks?)\b|dividend", low))  # "High Yield Equity Dividend" is stocks
        or any(k in ycat for k in ("Bond", "Muni", "Treasury", "Inflation-Protected", "Bank Loan", "Preferred", "Securitized", "Credit"))
        or any(k in style for k in ("Bond", "Quality", "Fixed Income", "High Yield"))
    ):
        ac = "Fixed income"
        why.append("bond fund (name or category)")
    else:
        ac = "Equity"
    # look-through override for equity: if TMX says almost nothing is in stocks, it is not an equity fund
    other = _share(r.get("tmx_sectors"), "Other")
    if ac == "Equity" and other is not None and other > 85 and not out["single_stock"]:
        ac = "Fixed income" if re.search(r"income|yield|bond|credit", low) else ac
    out["asset_class"] = ac

    # ---- region
    region = None
    region_name = re.sub(r"^\s*global x\b", "", name, flags=re.I)  # "Global X" is an issuer's brand, not a region
    for rx, reg in _REGION:
        if rx.search(region_name):
            region = reg
            break
    if region is None:
        reg_w = _top(r.get("tmx_regions"))
        if reg_w and reg_w[1] >= 80:
            region = {"United States": "US", "Canada": "Canada"}.get(reg_w[0], "Global")
            why.append(f"region from holdings: {reg_w[0]} {reg_w[1]:.0f}%")
    if region is None and region_name != name:
        # a Global X theme fund (uranium, lithium, robotics) whose name and holdings name no region: global, as
        # before; the listing-market fallback below would wrongly call every US-listed one a US fund
        region = "Global"
    if region is None:
        if "Foreign" in ycat or "International" in ycat:
            region = "International developed"
        elif "Emerging" in ycat or "Diversified Emerging" in ycat or "China" in ycat or "India" in ycat:
            region = "Emerging markets"
        elif "World" in ycat or "Global" in ycat:
            region = "Global"
        elif r.get("market") == "US" and ac in ("Equity", "Fixed income", "Cash", "Real estate"):
            region = "US"
        elif r.get("market") == "CA" and ac in ("Fixed income", "Cash"):
            region = "Canada"
        else:
            region = "Global" if ac not in ("Commodity", "Crypto") else "Global"
    if ac in ("Commodity", "Crypto"):
        region = "Global"
    elif ac == "Cash" and r.get("market") == "CA" and not re.search(r"\busd\b|u\.s\.|\bus\b", low):
        region = "Canada"
    out["region"] = region

    # ---- themes (several may apply) and dominant sector from look-through
    themes = [t for t, rx in _THEME if rx.search(name)]
    if style == "Option Writing" or ycat == "Derivative Income":
        themes.append("Covered call / option income")
    if ac != "Equity":  # "emerging markets" in a bond fund's name is not a broad stock market
        themes = [t for t in themes if t != "Broad market"]
    # "Broad market" needs the name of a whole-market index; an equity name with no theme is left unlabelled
    out["theme"] = "; ".join(dict.fromkeys(themes))
    top_sector = _top(r.get("tmx_sectors"), exclude=("Other",))
    out["sector"] = top_sector[0] if top_sector and top_sector[1] >= 60 else ("Diversified" if ac == "Equity" else "")

    # ---- derivatives and strategy
    derivs = []
    if lev != 1.0:
        derivs.append("leverage/inverse (swaps or futures)")
    if re.search(
        # "premium" is an option premium, not "Premium Money Market" or "Premium Cash"; "enhanced" alone is a manager's
        # word ("Fidelity Enhanced High Yield", "Research Enhanced"), and "Hedged Equity" is usually currency hedging
        r"covered call|option|overlay|buywrite|downside hedged|\bbox\b|tail risk|defined risk|\bswan\b|simplify|buffer|yield shares|highshares|enhanced (?:yield|income|dividend|premium)|premium(?! money| cash| t-bill)|defined outcome|autocallable|daymax|yieldboost",
        low,
    ):
        derivs.append("options")
    # a commodity fund that does not hold bullion holds futures (E7(e): HGER, COMB), unless it says it is physical
    if re.search(r"futures|managed futures|commodity index|vix", low) or (
        ac == "Commodity" and not _RX["gold"].search(name) and "physical" not in low
    ):
        derivs.append("futures")
    if re.search(r"\bswap\b|total return index|corporate class|\btri\b", low):
        derivs.append("swap-based")
    out["derivatives"] = "; ".join(derivs)
    if (
        re.search(r"\bactive\b|actively managed|activeetf|activ\b", low)
        or _RX["activemarkers"].search(name)
        or (
            "index" not in low
            and not _RX["indexfamily"].search(name)  # "iShares Russell 3000 Fund" tracks an index
            and re.search(r"\bfund\b|\bpool\b|opportunit|select|strategic|tactical|alpha", low)
        )
    ):
        strategy = "Active"
    elif re.search(r"low vol|momentum|quality|value|equal weight|dividend|factor|fundamental|multifactor|smart beta|quant", low):
        strategy = "Index: factor / smart beta"
    else:
        strategy = "Index: market cap"
    if derivs and "options" in derivs:
        strategy = "Options-based"
    if lev != 1.0:
        strategy = "Leveraged / inverse (daily reset)"
    out["strategy"] = strategy

    # ---- currency and hedging
    yh = str(r.get("yahoo") or "")
    trade_ccy = "USD" if (r.get("market") == "US" or re.search(r"-U\.(TO|NE)$", yh) or str(r.get("currency")) == "USD") else "CAD"
    out["currency"] = trade_ccy
    hedged = bool(re.search(HEDGED, low)) and not re.search(NOT_HEDGED, low)
    out["hedged"] = hedged
    fix = LABEL_OVERRIDES.get(yh)
    if fix:
        out.update(fix[0])
        why.append("label from the issuer: " + fix[1])

    out["crypto"] = ac == "Crypto"
    out["target_date"] = bool(re.search(r"target[- ]date|target 20\d\d|20\d\d\b.*(bond|maturity|target)|ibonds|bulletshares", low))
    out["esg"] = bool(re.search(r"\besg\b|sustainab|responsible|climate|paris|low carbon|fossil|net zero|socially", low)) or str(
        r.get("tmx_esg") or ""
    ).lower() in ("true", "yes", "1")

    # ---- issuer
    issuer = None
    fam = r.get("yahoo_family")
    for rx, nm in _ISSUER:
        if rx.search(name):
            issuer = nm
            break
    out["issuer"] = issuer or (fam if isinstance(fam, str) and fam else None) or "Other"
    out["why"] = " | ".join(why)
    return out


def _share(items, key: str) -> float | None:
    if not isinstance(items, list):
        return None
    for x in items:
        if x.get("name") == key:
            return float(x.get("percent") or 0)
    return 0.0


def _holds_stocks(r) -> bool:
    """TMX look-through says most of the fund is in company sectors (a gold-miners fund, not bullion)."""
    items = r.get("tmx_sectors")
    if not isinstance(items, list) or not items:
        return False
    return 100.0 - (_share(items, "Other") or 0.0) > 50.0


def _top(items, exclude: tuple = ()) -> tuple[str, float] | None:
    if not isinstance(items, list) or not items:
        return None
    xs = [(x.get("name"), float(x.get("percent") or 0)) for x in items if x.get("name") not in exclude]
    if not xs:
        return None
    return max(xs, key=lambda t: t[1])


def classify(listings: pd.DataFrame) -> pd.DataFrame:
    """Apply :func:`classify_row` to every listing and attach cost / size / age fields."""
    rows = [classify_row(r) for _, r in listings.iterrows()]
    c = pd.DataFrame(rows, index=listings.index)
    out = pd.concat([listings[["yahoo", "symbol", "name", "market", "exchange"]], c], axis=1)
    mer = pd.to_numeric(listings.get("netExpenseRatio"), errors="coerce")
    out["mer"] = mer / 100.0  # Yahoo reports percent; store as a fraction
    aum = pd.to_numeric(listings.get("netAssets"), errors="coerce")
    if "tmx_aum" in listings:
        aum = aum.fillna(pd.to_numeric(listings["tmx_aum"], errors="coerce"))
    out["aum"] = aum
    inc = pd.to_datetime(listings.get("first_trade"), errors="coerce")
    if "tmx_inceptiondate" in listings:
        inc = inc.fillna(pd.to_datetime(listings["tmx_inceptiondate"], errors="coerce"))
    out["inception"] = inc.dt.tz_localize(None) if hasattr(inc.dt, "tz") and inc.dt.tz is not None else inc
    out["dividend_yield"] = pd.to_numeric(listings.get("dividendYield"), errors="coerce") / 100.0
    if "tmx_distributionyeld" in listings:
        out["dividend_yield"] = out["dividend_yield"].fillna(pd.to_numeric(listings["tmx_distributionyeld"], errors="coerce") / 100.0)
    out["pe"] = pd.to_numeric(listings.get("trailingPE"), errors="coerce")
    if "tmx_pricetoearnings" in listings:
        out["pe"] = out["pe"].fillna(pd.to_numeric(listings["tmx_pricetoearnings"], errors="coerce"))
    out["pb"] = pd.to_numeric(listings.get("tmx_pricetobook"), errors="coerce") if "tmx_pricetobook" in listings else np.nan
    out["yahoo_category"] = listings.get("yahoo_category")
    out["tmx_style"] = listings.get("tmx_investmentstyle")
    return out
