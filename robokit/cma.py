"""Long-run return assumptions used for projections and for the return figure shown to users.

Two different jobs, two different sources:

* The optimizer needs *relative* expected returns that are consistent with the
  covariance matrix, so that it does not chase noise. It uses equilibrium
  (reverse-optimised) returns (docs/METHOD.md). Their absolute level is set by
  the risk-aversion convention and is not meant to be read as a forecast.
* Projections and the "about X% a year" figure need a published, neutral
  planning assumption. For Canada that is the FP Canada / Institute of
  Financial Planning 2026 Projection Assumption Guidelines, the standard
  Canadian planners use: "Short term 2.4% Fixed income 3.2% Canadian equities
  6.3% U.S. equities 6.4% International developed-market equities 6.6%
  Emerging market equities 7.5%" (geometric, before fees; source opened
  28 Sep 2026, docs/research/methods-signals.md section 6.1).

For the US market no neutral equivalent was found (the research lane lists
this as a gap). Robo-Kit uses the same FP Canada equity assumptions (they are
asset-class returns, not Canadian-specific), and for US cash and bonds the
current Treasury yields, a common rule of thumb for what a bond fund earns
over roughly its duration. Every figure says which source it used.

Asset classes FP Canada does not cover get a stated Robo-Kit assumption:
real estate = the equity assumption of its region; gold and commodities =
the short-term rate (no premium assumed); crypto and alternatives = no
planning assumption, so the model's equilibrium return is used and flagged.
"""

from __future__ import annotations

FPC_2026 = {
    "short_term": 0.024,
    "fixed_income": 0.032,
    "canada_equity": 0.063,
    "us_equity": 0.064,
    "intl_equity": 0.066,
    "em_equity": 0.075,
}
FPC_SOURCE = "FP Canada / IFP 2026 Projection Assumption Guidelines (geometric, before fees)"


def _equity_key(region: str) -> str:
    return {
        "Canada": "canada_equity",
        "US": "us_equity",
        "North America": "us_equity",
        "Emerging markets": "em_equity",
        "China": "em_equity",
    }.get(region, "intl_equity")


def assumption(asset_class: str, region: str, market: str, us_rates: dict | None = None) -> tuple[float | None, str]:
    """Geometric annual return assumption before fees, and its source label. None = no assumption."""
    us_rates = us_rates or {}
    if asset_class == "Equity" or asset_class == "Multi-asset":
        k = _equity_key(region)
        if asset_class == "Multi-asset":
            return 0.6 * FPC_2026[k] + 0.4 * FPC_2026["fixed_income"], "Robo-Kit: 60% equity / 40% bonds of " + FPC_SOURCE
        return FPC_2026[k], FPC_SOURCE
    if asset_class == "Real estate":
        return FPC_2026[_equity_key(region)], "Robo-Kit assumption: same as equities of its region (" + FPC_SOURCE + ")"
    if asset_class == "Cash":
        if market == "US" and us_rates.get("bill") is not None:
            return us_rates["bill"], "US 13-week Treasury bill yield today"
        return FPC_2026["short_term"], FPC_SOURCE
    if asset_class == "Fixed income":
        if market == "US" and us_rates.get("note5") is not None:
            return us_rates["note5"], "US 5-year Treasury yield today (starting-yield rule of thumb)"
        return FPC_2026["fixed_income"], FPC_SOURCE
    if asset_class == "Commodity":
        base = us_rates.get("bill") if market == "US" and us_rates.get("bill") is not None else FPC_2026["short_term"]
        return base, "Robo-Kit assumption: short-term rate, no extra return assumed for gold or commodities"
    return None, "no planning assumption for this asset class; model estimate used"
