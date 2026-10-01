"""Fixed plain-language definitions.

Definitions live in code so they never drift between the web page, the chat
and the MCP server (docs/research/ux-conversation.md principle 4). Each is
short enough to read in one breath; the chat may add an example but should
quote the definition as written.
"""

from __future__ import annotations

TERMS = {
    "etf": ("ETF (exchange-traded fund)", "A basket of many investments you buy and sell like one share on a stock exchange."),
    "index_fund": ("Index fund", "A fund that copies a market index, such as the S&P 500, instead of picking investments."),
    "mer": (
        "MER (management expense ratio)",
        "The yearly fee a fund takes, as a percentage of what you hold. 0.20% is $20 a year per $10,000.",
    ),
    "volatility": ("Volatility", "How much the value swings up and down. Higher volatility means bigger ups and bigger downs."),
    "drawdown": ("Drawdown", "How far the value fell from its previous high before recovering."),
    "diversification": ("Diversification", "Spreading money across many investments so one bad result hurts less."),
    "asset_class": ("Asset class", "A family of investments that behave alike: stocks, bonds, cash, real estate, gold."),
    "bond": ("Bond", "A loan to a government or company that pays interest and returns the money at a set date."),
    "bond_prices_rates": (
        "Bond prices and interest rates",
        "When interest rates rise, existing bonds lose value, because new bonds pay more. Longer bonds move more.",
    ),
    "duration": ("Duration", "Roughly how much a bond fund's price moves when rates change by one point. Duration 7 means about 7%."),
    "yield": ("Yield", "The income an investment pays each year, as a percentage of its price."),
    "hedged": ("Currency-hedged", "The fund removes most of the effect of exchange-rate swings, for a small cost."),
    "leverage": (
        "Leveraged and inverse ETFs",
        "Funds that try to return 2x, 3x or -1x an index's move for one day. Held longer, results can differ a lot from 2x the index.",
    ),
    "rebalancing": ("Rebalancing", "Trading back to your target mix after markets have moved it."),
    "risk_tolerance": ("Risk tolerance", "How much ups and downs you are willing to live with."),
    "risk_capacity": ("Risk capacity", "How much loss your situation can absorb: time until you need the money, savings cushion, income."),
    "equilibrium_return": (
        "Equilibrium return",
        "The return each fund would need for today's market mix to be a sensible holding. Robo-Kit uses it instead of past returns, which are too noisy.",
    ),
    "resampling": (
        "Resampling",
        "Re-running the calculation on thousands of reshuffled histories and averaging, so one lucky period does not decide the mix.",
    ),
    "correlation": ("Correlation", "How much two investments move together, from -1 (opposite) to +1 (in lockstep)."),
    "sharpe": ("Sharpe ratio", "Return above cash per unit of volatility. Higher is better, all else equal."),
    "tracking_error": ("Tracking error", "How far a portfolio's returns tend to stray from a reference portfolio's, per year."),
    "spread": ("Bid-ask spread", "The gap between the price buyers offer and sellers ask. Thinly traded funds have wider gaps."),
    "aum": ("AUM (assets under management)", "How much money a fund holds in total. Very small funds are more likely to close."),
    "covered_call": ("Covered-call ETF", "A fund that sells options on its holdings for extra income, giving up part of the upside."),
    "reit": ("REIT", "A company that owns and rents out property, such as apartments, offices or warehouses."),
    "emerging_markets": (
        "Emerging markets",
        "Countries whose economies and markets are still developing, such as China, India and Brazil.",
    ),
    "inflation": ("Inflation", "The general rise in prices, which shrinks what each dollar buys."),
    "tbill_hisa": (
        "Cash ETF (T-bills or savings)",
        "A fund holding very short government bills or bank deposits. It barely moves and pays about the short-term interest rate.",
    ),
    "tfsa_rrsp": (
        "TFSA and RRSP (Canada)",
        "Tax-sheltered accounts. A TFSA shelters growth from tax; an RRSP gives a deduction now and taxes withdrawals. A tax professional can say which fits you.",
    ),
    "black_litterman": (
        "Black-Litterman",
        "A method that starts from the market's own implied returns and blends in a view only as much as you trust it.",
    ),
    "hypothetical": ("Hypothetical result", "A result the rules would have produced on past data. No one actually earned it."),
}


def define(term: str) -> dict:
    key = term.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "expense_ratio": "mer",
        "fee": "mer",
        "fees": "mer",
        "vol": "volatility",
        "risk": "volatility",
        "leveraged": "leverage",
        "inverse": "leverage",
        "reits": "reit",
        "sharpe_ratio": "sharpe",
        "hisa": "tbill_hisa",
        "cash": "tbill_hisa",
        "tfsa": "tfsa_rrsp",
        "rrsp": "tfsa_rrsp",
        "bl": "black_litterman",
    }
    key = aliases.get(key, key)
    if key not in TERMS:
        return {"found": False, "term": term, "known_terms": sorted(TERMS)}
    en_t, en_d = TERMS[key]
    return {"found": True, "key": key, "term": en_t, "definition": en_d, "en": {"term": en_t, "definition": en_d}}
