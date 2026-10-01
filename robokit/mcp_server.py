"""Robo-Kit as an MCP server: connect it to Claude Desktop, Claude Code or any MCP client.

The person's own Claude plan (or API key) runs the conversation and they pick
the model; this server supplies the numbers. Every tool is read-only and
deterministic; data is fetched on the person's own machine (see
docs/DATA.md for licences).

Run:
    python -m robokit.mcp_server                 # stdio (Claude Desktop, Claude Code)
    python -m robokit.mcp_server --http 8765     # streamable HTTP on 127.0.0.1:8765/mcp
"""

from __future__ import annotations

import argparse

from mcp.server.fastmcp import FastMCP

from . import tools
from .config import ROOT

AGENT_MD = (ROOT / "AGENT.md").read_text(encoding="utf-8") if (ROOT / "AGENT.md").exists() else ""

INSTRUCTIONS = (
    "Robo-Kit is a do-it-yourself ETF portfolio lab for Canadian (CAD) and US-listed ETFs. "
    "Follow the Robo-Kit guide rules (prompt 'robo_kit_guide', also in AGENT.md): disclose you are an AI at the start; "
    "every number and every ticker you mention must come from these tools; ask the self-check questions with their exact wording; "
    "the person chooses the level and the funds; never tell anyone what to buy or sell, never forecast markets, "
    "and treat news as context only."
)

mcp = FastMCP("robokit", instructions=INSTRUCTIONS)


@mcp.tool()
def get_questions() -> dict:
    """The fixed self-check questions (ids A0-D2) with answer options. Ask them one at a time with this exact wording."""
    return tools.get_questions()


@mcp.tool()
def scenario_cards(market: str = "CA", amount: float = 10000) -> dict:
    """Dollar ranges for the tolerance questions C1-C3 at levels 1-5, for the person's amount. market: 'CA' or 'US'."""
    return tools.scenario_cards(market, amount)


@mcp.tool()
def score_profile(answers: dict) -> dict:
    """Score self-check answers {item_id: option_value}. Returns the suggested level (lower of capacity and tolerance), gates, flags and the levels the person may choose."""
    return tools.score_profile(answers)


@mcp.tool()
def risk_ladder(market: str = "CA") -> dict:
    """Asset-class mixes of the reference portfolio at levels 1-5 side by side, with typical and bad-year ranges. The default, impersonal view."""
    return tools.risk_ladder(market)


@mcp.tool()
def reference_shelf(market: str = "CA", prefer_esg: bool = False, sort_by: str = "cost") -> dict:
    """For each asset class, the lowest-cost broad funds that fit its written rule, with runners-up. sort_by: 'cost', 'size' or 'history'."""
    return tools.reference_shelf(market, prefer_esg, sort_by)


@mcp.tool()
def search_etfs(
    query: str = "",
    market: str = "CA",
    asset_class: str | None = None,
    region: str | None = None,
    theme: str | None = None,
    max_mer: float | None = None,
    min_aum: float | None = None,
    min_history_months: int | None = None,
    eligible_only: bool = True,
    esg_only: bool = False,
    hedged: bool | None = None,
    sort_by: str = "mer",
    limit: int = 25,
) -> dict:
    """Neutral filter over every ETF in the chosen market. max_mer is a fraction (0.002 = 0.20%). sort_by: 'mer', 'aum', 'history', 'name'."""
    return tools.search_etfs(
        query, market, asset_class, region, theme, max_mer, min_aum, min_history_months, eligible_only, esg_only, hedged, sort_by, limit
    )


@mcp.tool()
def etf_profile(ticker: str) -> dict:
    """Facts for one ETF: fees, size, history, classification with reasons, trend, and why it is excluded if it is."""
    return tools.etf_profile(ticker)


@mcp.tool()
def compare_etfs(tickers: list[str]) -> dict:
    """Side-by-side facts for up to 6 ETFs and their 5-year correlation. No verdict."""
    return tools.compare_etfs(tickers)


@mcp.tool()
def build_portfolio(
    market: str = "CA",
    level: float = 3,
    swaps: dict | None = None,
    satellites: list[str] | None = None,
    exclude: list[str] | None = None,
    minimums: dict | None = None,
    prefer_esg: bool = False,
    hedge_us_equity: bool = False,
    max_weight: float = 0.5,
    views: list[dict] | None = None,
    amount: float = 10000,
    monthly_contribution: float = 0,
    years: int = 10,
    goal: float | None = None,
    fixed_weights: dict | None = None,
) -> dict:
    """What the model does with the chosen funds at the chosen level (1-5): weights with bands, dollars and units per fund,
    volatility, planning return after fees, fees in dollars, risk shares, crisis replays in dollars, projections, checks and
    ready-made explanation sentences. swaps: {sleeve: ticker}. satellites: extra tickers. fixed_weights: {ticker: share}
    reports the person's own weights instead of optimising. A negative monthly_contribution is a withdrawal.
    views: [{type:'relative', long, short, difference, confidence}] or [{type:'absolute', ticker, return, confidence}]."""
    return tools.build_portfolio_tool(
        market,
        level,
        swaps,
        satellites,
        exclude,
        minimums,
        prefer_esg,
        hedge_us_equity,
        max_weight,
        views,
        amount,
        monthly_contribution,
        years,
        goal,
        fixed_weights,
    )


@mcp.tool()
def compare_one_fund(market: str = "CA", stock_share: float = 0.6, amount: float = 10000, years: int = 10) -> dict:
    """The same report (volatility, one-year range in dollars, fees in dollars, crisis replays) for a single asset-allocation ETF
    whose stated stock share is closest to stock_share (0 to 1), on the same window. The do-it-yourself benchmark for any mix."""
    return tools.compare_one_fund(market, stock_share, amount, years)


@mcp.tool()
def plan_contribution(holdings: list, new_money: float, current: dict | None = None) -> dict:
    """Split new money across the funds of a mix (pass build_portfolio's holdings: ticker, weight, price) so the holdings move
    toward the target weights without selling anything. current: {ticker: dollars held now}. Returns buys in dollars and
    whole units, and how far the holdings sit from the mix before and after. Hypothetical, not an order."""
    return tools.plan_contribution(holdings, new_money, current)


@mcp.tool()
def market_context(market: str = "CA", include_news: bool = True) -> dict:
    """Risk flags (VIX, geopolitical risk, policy uncertainty, credit spreads, yield curves, FX) with percentiles and dates, plus a news digest. Context only."""
    return tools.market_context(market, include_news)


@mcp.tool()
def explain_term(term: str) -> dict:
    """A fixed plain-language definition (e.g. 'mer', 'volatility', 'leverage', 'hedged', 'tfsa_rrsp')."""
    return tools.explain_term(term)


@mcp.tool()
def backtest_summary(market: str = "CA", level: int = 3) -> dict:
    """The pre-registered walk-forward back-test at one level, after costs. Always hypothetical."""
    return tools.backtest_summary(market, level)


@mcp.tool()
def data_status() -> dict:
    """Engine version, data snapshot, price dates, sources and licences."""
    return tools.data_status()


@mcp.prompt()
def robo_kit_guide() -> str:
    """The full Robo-Kit guide rules (AGENT.md). Load this at the start of a session."""
    return AGENT_MD


@mcp.resource("robokit://agent")
def agent_md() -> str:
    """AGENT.md: how the Robo-Kit guide talks and what it may do."""
    return AGENT_MD


def main() -> None:
    ap = argparse.ArgumentParser(description="Robo-Kit MCP server")
    ap.add_argument("--http", type=int, default=None, help="serve streamable HTTP on this port (127.0.0.1) instead of stdio")
    a = ap.parse_args()
    if a.http:
        mcp.settings.port = a.http
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
