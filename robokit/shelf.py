"""The building-block shelf: one low-cost, broad ETF per asset-class sleeve.

This is how most robo-advisors are built (a handful of broad, cheap index
funds, one per asset class). What Robo-Kit adds is that the shelf is not a
black box:

* every sleeve is defined by a written rule (asset class, region, a name
  pattern, and what is excluded), not by a hand-picked ticker;
* the fund in each sleeve is chosen by a published score (low cost, large,
  liquid, long history), and the runners-up are listed so the user can swap;
* preferences change the pick in a visible way (ESG versions, currency-hedged
  versions);
* the prior weights ("the market portfolio" used to anchor expected returns)
  are written down here with their source, not buried in code.

Prior weights
-------------
Equity 60 / fixed income 35 / real estate 3 / gold 2 is the v1 policy prior
(docs/METHOD.md, robustness grid), a stand-in for the global multi-asset
market portfolio, which is roughly half equity and half bonds by value
(Doeswijk, Lam and Swinkels 2014/2020), tilted toward equity as retail
policy portfolios are. Within equity, the US market uses approximate global
market-cap shares (US about 62%, other developed 27%, emerging 11%); the
Canadian market keeps a home-bias share of 30% Canadian equity, in line with
the home-bias ranges discussed in Canadian robo-advisor methodologies. These
are anchors for expected returns, not the recommended portfolio: the
optimizer, the client's risk level and the constraints decide the weights.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

EXCL_FACTOR = r"dividend|low vol|min(?:imum)? vol|equal|momentum|value|quality|growth|factor|covered|buffer|enhanced|premium|yield|option|leaders|select|high beta|fundamental|multifactor|completion|sector|banks?\b|financial|energy|tech|small|mid[- ]?cap|esg|sustainab|climate|paris|responsible|clean|innovation|active|tactical|strategic|opportunit"


@dataclass(frozen=True)
class Sleeve:
    key: str
    market: str
    label: str
    plain: str  # one sentence for a first-time investor
    asset_class: str
    regions: tuple[str, ...]
    include: str  # name regex that must match
    exclude: str = EXCL_FACTOR
    prior: float = 0.0  # share of the policy prior (0 = optional sleeve)
    hedged: bool | None = None  # True: must be hedged, False: must not be, None: either
    role: str = "core"
    extra_filter: str = ""  # optional regex on name that must ALSO match


CA_SLEEVES = [
    Sleeve(
        "ca_equity",
        "CA",
        "Canadian stocks",
        "Hundreds of Canadian companies in one fund.",
        "Equity",
        ("Canada",),
        r"s&p/tsx composite|tsx capped composite|capped composite|s&p/tsx 60|tsx 60|canada all cap|all cap|msci canada|canadian equity index|canada index|broad market|composite index",
    ),
    Sleeve(
        "ca_us_equity",
        "CA",
        "US stocks",
        "The 500 largest US companies (or the whole US market), bought in Canadian dollars.",
        "Equity",
        ("US",),
        r"s&p 500|s&p500|total u\.?s\.?|u\.?s\.? total|crsp u\.?s|msci usa|total stock market|u\.?s\.? equity index|us equity index",
        hedged=False,
    ),
    Sleeve(
        "ca_intl_equity",
        "CA",
        "International stocks",
        "Large companies in Europe, Japan, Australia and other developed markets.",
        "Equity",
        ("International developed", "Global"),
        r"eafe|developed all cap ex|developed ex|international developed|international equity index|developed markets ex|msci eafe",
        hedged=False,
    ),
    Sleeve(
        "ca_em_equity",
        "CA",
        "Emerging-market stocks",
        "Companies in China, India, Taiwan, Brazil and other emerging economies.",
        "Equity",
        ("Emerging markets",),
        r"emerging markets?",
        exclude=EXCL_FACTOR + r"|bond|ex china|ex-china|china|india|asia",
    ),
    Sleeve(
        "ca_agg_bond",
        "CA",
        "Canadian bonds",
        "Loans to Canadian governments and companies; the steadier part of a portfolio.",
        "Fixed income",
        ("Canada",),
        r"aggregate|universe bond|canadian bond index|core canadian universe|canadian universe|total bond|core universe",
        exclude=r"short|long|corporate|real return|high yield|1-5|1-3|0-5|laddered|target|esg|enhanced|yield|discount|strip|federal|provincial|government|active|tactical|sustainab",
    ),
    Sleeve(
        "ca_short_bond",
        "CA",
        "Short-term Canadian bonds",
        "Bonds that mature within about five years, so prices move less when interest rates change.",
        "Fixed income",
        ("Canada",),
        r"short term bond|short-term bond|short term canadian|1-5 year|1-3 year|0-5 year|short term government|short term federal|short term universe",
        exclude=r"corporate|high yield|target|esg|enhanced|yield|discount|strip|laddered|real return|active|sustainab|floating|tips|inflation",
    ),
    Sleeve(
        "ca_global_bond",
        "CA",
        "Global bonds, hedged",
        "Bonds from the US and other countries with the currency risk removed.",
        "Fixed income",
        ("Global", "US", "International developed"),
        r"global aggregate|global bond|u\.?s\.? aggregate|us aggregate|global government bond|global ex-canada|global ex canada|international bond|u\.?s\.? bond index",
        exclude=r"high yield|esg|enhanced|yield|active|tactical|corporate|emerging|short|long|sustainab|flexible|income",
        hedged=True,
    ),
    Sleeve(
        "ca_reit",
        "CA",
        "Real estate (REITs)",
        "Companies that own apartments, offices, warehouses and malls.",
        "Real estate",
        ("Canada",),
        r"reit|real estate",
        exclude=r"covered|enhanced|yield|mortgage|active|income|premium",
    ),
    Sleeve(
        "ca_gold",
        "CA",
        "Gold",
        "Physical gold held in a vault; tends to hold up in some crises.",
        "Commodity",
        ("Global",),
        r"gold",
        exclude=r"miner|producer|covered|yield|enhanced|junior|equity|hedged|premium|daymax|mint|reserves|receipts",
    ),
    Sleeve(
        "ca_cash",
        "CA",
        "Cash (high-interest savings)",
        "Deposits at Canadian banks; almost no ups and downs.",
        "Cash",
        ("Canada",),
        r"high interest savings|savings|cash|money market|t-bill|treasury bill",
        exclude=r"usd|u\.s\.|us\b|enhanced|covered|flow|dividend|yield shares",
        role="cash",
    ),
    # Optional sleeves: not in the prior, available on the shelf.
    Sleeve(
        "ca_long_bond",
        "CA",
        "Long-term Canadian bonds",
        "Bonds that mature in 10+ years; more sensitive to interest rates.",
        "Fixed income",
        ("Canada",),
        r"long term bond|long-term bond|long federal|long term government|long provincial|15\+ year|long bond",
        exclude=r"corporate|high yield|target|esg|enhanced|yield|active|strip|real return",
    ),
    Sleeve(
        "ca_real_return",
        "CA",
        "Inflation-linked bonds",
        "Government bonds whose payments rise with inflation.",
        "Fixed income",
        ("Canada",),
        r"real return",
        exclude=r"active|enhanced|esg|sustainab",
    ),
    Sleeve(
        "ca_us_equity_hedged",
        "CA",
        "US stocks, hedged",
        "US stocks with the US-dollar swings removed.",
        "Equity",
        ("US",),
        r"s&p 500|s&p500|total u\.?s\.?|u\.?s\.? total|crsp u\.?s|msci usa|total stock market",
        hedged=True,
    ),
    Sleeve(
        "ca_high_yield",
        "CA",
        "High-yield bonds",
        "Loans to riskier companies; more income, more risk.",
        "Fixed income",
        ("US", "Global", "Canada"),
        r"high yield",
        exclude=r"esg|enhanced|active|short|floating|covered",
    ),
]

US_SLEEVES = [
    Sleeve(
        "us_equity",
        "US",
        "US stocks",
        "The whole US stock market, or its 500 largest companies, in one fund.",
        "Equity",
        ("US",),
        r"total stock market|total market|total u\.?s\.? stock|s&p 500|s&p500|crsp u\.?s\.? total|russell 3000|msci usa|broad market|core s&p total|portfolio s&p 500",
        exclude=EXCL_FACTOR + r"|leveraged|daily|2x|3x|high|ex-|ex\b|shariah|catholic|ethical",
    ),
    Sleeve(
        "us_intl_equity",
        "US",
        "International stocks",
        "Large companies in Europe, Japan and other developed markets.",
        "Equity",
        ("International developed", "Global"),
        r"developed markets|eafe|international equity|ftse developed|developed international|core msci international|total international|international stock|ex-us|ex us",
        exclude=EXCL_FACTOR + r"|emerging|bond|real estate|hedged|leveraged|small|world ex us small",
    ),
    Sleeve(
        "us_em_equity",
        "US",
        "Emerging-market stocks",
        "Companies in China, India, Taiwan, Brazil and other emerging economies.",
        "Equity",
        ("Emerging markets",),
        r"emerging markets?",
        exclude=EXCL_FACTOR + r"|bond|ex china|ex-china|china|india|asia|leveraged|debt|currency|local",
    ),
    Sleeve(
        "us_agg_bond",
        "US",
        "US bonds",
        "Loans to the US government and US companies; the steadier part of a portfolio.",
        "Fixed income",
        ("US",),
        r"aggregate|total bond|core bond|core u\.?s\.? aggregate|broad market bond|u\.?s\.? bond market|universal bond|core total",
        exclude=r"esg|enhanced|active|short|intermediate|long|municipal|muni|ultra|tips|corporate|mortgage|dynamic|plus|total return|opportunistic|flexible|high yield|international|global|sustainab|1-|0-|interest rate hedged|investment grade|equal",
    ),
    Sleeve(
        "us_short_treasury",
        "US",
        "Short-term US Treasuries",
        "US government bonds maturing in 1-3 years; small price moves.",
        "Fixed income",
        ("US",),
        r"1-3 year treasury|short treasury|short-term treasury|short term treasury|1-3 year u\.?s\.? treasury|treasury 1-3",
        exclude=r"inflation|tips|ultra|0-3 month|1-3 month|bill|floating|active|leveraged|daily|bear|inverse",
    ),
    Sleeve(
        "us_tips",
        "US",
        "Inflation-protected bonds (TIPS)",
        "US government bonds whose value rises with inflation.",
        "Fixed income",
        ("US",),
        r"\btips\b|inflation-protected|inflation protected",
        exclude=r"short|0-5|1-5|long|15\+|ladder|term|ibonds|active|leveraged|breakeven|interest rate hedged|enhanced",
    ),
    Sleeve(
        "us_intl_bond",
        "US",
        "International bonds, hedged",
        "Bonds from other developed countries with the currency risk removed.",
        "Fixed income",
        ("International developed", "Global"),
        r"international bond|global aggregate|ex-us aggregate|total international bond|ex-u\.s\.|international aggregate",
        exclude=r"emerging|high yield|active|local|corporate|treasury|inflation|esg|dynamic|unhedged",
        hedged=None,
    ),
    Sleeve(
        "us_reit",
        "US",
        "Real estate (REITs)",
        "Companies that own apartments, offices, warehouses and cell towers.",
        "Real estate",
        ("US",),
        r"real estate|reit",
        exclude=r"mortgage|covered|global|international|ex-us|premium|income|leveraged|daily|preferred|select sector|residential|office|industrial|data center|healthcare",
    ),
    Sleeve(
        "us_gold",
        "US",
        "Gold",
        "Physical gold held in a vault; tends to hold up in some crises.",
        "Commodity",
        ("Global",),
        r"gold",
        exclude=r"miner|producer|covered|yield|enhanced|junior|equity|leveraged|daily|2x|3x|bear|premium|strategy|option",
    ),
    Sleeve(
        "us_cash",
        "US",
        "Cash (Treasury bills)",
        "US government bills maturing in weeks; almost no ups and downs.",
        "Cash",
        ("US",),
        r"0-3 month|treasury bill|t-bill|1-3 month|ultra short-term treasury|ultra short treasury|3 month treasury",
        exclude=r"leveraged|daily|inverse|enhanced|option|covered",
        role="cash",
    ),
    # Optional sleeves
    Sleeve(
        "us_small_cap",
        "US",
        "US small companies",
        "Smaller US companies; more growth potential and more risk.",
        "Equity",
        ("US",),
        r"small[- ]?cap|russell 2000|smallcap",
        exclude=r"value|growth|momentum|quality|dividend|esg|leveraged|daily|2x|3x|bear|covered|premium|equal|international|emerging|core msci",
    ),
    Sleeve(
        "us_long_treasury",
        "US",
        "Long-term US Treasuries",
        "US government bonds maturing in 20+ years; move a lot with interest rates.",
        "Fixed income",
        ("US",),
        r"20\+ year treasury|long-term treasury|long treasury|extended duration treasury|20\+ yr",
        exclude=r"leveraged|daily|bear|inverse|3x|2x|premium|option|buywrite|covered|strips|zero",
    ),
    Sleeve(
        "us_corp_bond",
        "US",
        "US corporate bonds",
        "Loans to large US companies; a bit more income than government bonds.",
        "Fixed income",
        ("US",),
        r"investment grade corporate|corporate bond|ig corporate",
        exclude=r"short|long|intermediate|1-5|1-3|10\+|high yield|esg|active|ladder|target|term|interest rate hedged|leveraged|floating",
    ),
    Sleeve(
        "us_high_yield",
        "US",
        "High-yield bonds",
        "Loans to riskier companies; more income, more risk.",
        "Fixed income",
        ("US", "Global"),
        r"high yield",
        exclude=r"municipal|muni|esg|active|short|floating|interest rate hedged|leveraged|daily|emerging|europe",
    ),
]

PRIOR = {
    "CA": {
        "ca_equity": 0.18,
        "ca_us_equity": 0.27,
        "ca_intl_equity": 0.108,
        "ca_em_equity": 0.042,
        "ca_agg_bond": 0.22,
        "ca_short_bond": 0.06,
        "ca_global_bond": 0.07,
        "ca_reit": 0.03,
        "ca_gold": 0.02,
    },
    "US": {
        "us_equity": 0.372,
        "us_intl_equity": 0.162,
        "us_em_equity": 0.066,
        "us_agg_bond": 0.22,
        "us_short_treasury": 0.06,
        "us_tips": 0.04,
        "us_intl_bond": 0.03,
        "us_reit": 0.03,
        "us_gold": 0.02,
    },
}

# A sleeve that replaces another one takes over its policy share (the hedged US-equity
# sleeve holds the same stocks as the unhedged one, so it gets the same 27%).
PRIOR_ALIAS = {"ca_us_equity_hedged": "ca_us_equity"}


def prior_share(market: str, key: str) -> float:
    """Policy-prior share of a sleeve (0 for sleeves outside the reference mix)."""
    return PRIOR[market].get(key, PRIOR[market].get(PRIOR_ALIAS.get(key, ""), 0.0))


SLEEVES = {s.key: s for s in CA_SLEEVES + US_SLEEVES}


def sleeves_for(market: str) -> list[Sleeve]:
    return [s for s in CA_SLEEVES + US_SLEEVES if s.market == market]


def _z(x: pd.Series) -> pd.Series:
    x = x.astype(float)
    sd = x.std()
    return (x - x.mean()) / sd if sd and np.isfinite(sd) and sd > 0 else x * 0.0


SCORE = {"aum": 1.0, "volume": 0.5, "fee": -1.5, "history": 0.5, "esg": 0.75}  # the written ranking rule


def candidates(universe: pd.DataFrame, sleeve: Sleeve, prefer_esg: bool = False, coef: dict | None = None) -> pd.DataFrame:
    """Eligible funds that fit a sleeve, best first, with the score that ranked them. ``coef`` replaces the score's
    coefficients (evaluation only: the sensitivity of the shelf to its ranking rule)."""
    k = {**SCORE, **(coef or {})}
    u = universe[(universe.market == sleeve.market) & universe.eligible & (universe.asset_class == sleeve.asset_class)]
    u = u[u.region.isin(sleeve.regions)]
    name = u["name"].fillna("")
    m = name.str.contains(sleeve.include, flags=re.I, regex=True)
    excl = sleeve.exclude
    if prefer_esg:
        excl = re.sub(r"\|?esg|\|?sustainab|\|?climate|\|?paris|\|?responsible|\|?clean", "", excl)
    if excl:
        m &= ~name.str.contains(excl, flags=re.I, regex=True)
    if sleeve.hedged is True:
        m &= u["hedged"]
    elif sleeve.hedged is False:
        m &= ~u["hedged"]
    if sleeve.market == "CA":
        m &= u["currency"].eq("CAD")
    c = u[m].copy()
    if c.empty:
        return c
    hist = c["history_months"].clip(upper=180)
    mer = c["mer"].fillna(c["mer"].median() if c["mer"].notna().any() else 0.005)
    c["score"] = (
        k["aum"] * _z(np.log(c["aum"].fillna(1e6).clip(lower=1e6)))
        + k["volume"] * _z(np.log(c["dollar_volume"].fillna(1e3).clip(lower=1e3)))
        + k["fee"] * _z(mer)
        + k["history"] * _z(hist)
        + (k["esg"] if prefer_esg else 0.0) * c["esg"].astype(float)
    )
    return c.sort_values(["score", "history_months"], ascending=[False, False])


def slot_members(universe: pd.DataFrame, sleeve: Sleeve, prefer_esg: bool = False) -> list[str]:
    """The funds a swap may put in the slot: every fund the sleeve's own rule admits, hedged or not (hedging is the
    user's choice), and like for like with the slot's reference fund. Funds built on options or futures are left out,
    and when the reference fund is a broad fund, so is every fund labelled narrow (universe.satellite_only: a sector,
    factor, option-income or thematic fund the name rule let through). Two independent filters must both admit it."""
    ref = candidates(universe, sleeve, prefer_esg=prefer_esg)
    if ref.empty:  # a slot with no reference fund takes no swap (fail closed)
        return []
    c = candidates(universe, replace(sleeve, hedged=None), prefer_esg=prefer_esg)
    return list(like_for_like(c, ref.iloc[0])["yahoo"])


def like_for_like(c: pd.DataFrame, reference: pd.Series | None) -> pd.DataFrame:
    """The candidates that may stand in for ``reference``: none built on options or futures, and none labelled narrow
    when the reference fund is broad. The order (best first) is kept."""
    if c.empty:
        return c
    ok = ~c["derivatives"].fillna("").str.contains("options|futures")
    if reference is not None and not bool(reference["satellite_only"]):
        ok &= ~c["satellite_only"].astype(bool)
    return c[ok]


def build_shelf(
    universe: pd.DataFrame, market: str, prefer_esg: bool = False, n_alternatives: int = 4, coef: dict | None = None
) -> pd.DataFrame:
    """One row per sleeve: the chosen fund, its runners-up, and the prior weight."""
    rows = []
    for s in sleeves_for(market):
        c = candidates(universe, s, prefer_esg=prefer_esg, coef=coef)
        pick = c.iloc[0] if len(c) else None
        rows.append(
            {
                "sleeve": s.key,
                "label": s.label,
                "plain": s.plain,
                "asset_class": s.asset_class,
                "role": s.role,
                "prior": prior_share(market, s.key),
                "ticker": None if pick is None else pick["yahoo"],
                "fund": None if pick is None else pick["name"],
                "mer": None if pick is None else pick["mer"],
                "aum": None if pick is None else pick["aum"],
                "history_months": None if pick is None else int(pick["history_months"]),
                "n_candidates": int(len(c)),
                # the funds the page offers instead: like for like, so every one passes the swap gate
                "alternatives": [] if c.empty else list(like_for_like(c, pick)["yahoo"].iloc[1 : 1 + n_alternatives]),
            }
        )
    return pd.DataFrame(rows)
