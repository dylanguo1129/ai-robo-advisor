"""Smoke test for the MCP surface (the server, the Claude Code plugin and the terminal agent all import it)."""

import asyncio

EXPECTED = {
    "get_questions",
    "score_profile",
    "scenario_cards",
    "risk_ladder",
    "reference_shelf",
    "search_etfs",
    "etf_profile",
    "compare_etfs",
    "build_portfolio",
    "compare_one_fund",
    "plan_contribution",
    "market_context",
    "explain_term",
    "backtest_summary",
    "data_status",
}


def test_mcp_server_lists_all_tools():
    from robokit.mcp_server import mcp

    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert names == EXPECTED


def test_explain_term_returns_the_documented_shape():
    from robokit import tools

    out = tools.explain_term("mer")
    assert out["found"] and set(out) == {"found", "key", "term", "definition", "en"}
