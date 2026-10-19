"""Robo-Kit v2: a transparent, do-it-yourself ETF robo-advisor engine.

Layers
------
robokit.data       the data bridge: listings, metadata, prices, fundamentals,
                   macro, geopolitics and news, each stamped with source and date
robokit.classify   rule-based classification of every ETF (asset class, region,
                   theme, leverage, strategy, currency hedging, ...)
robokit.universe   eligibility rules, with a reason for every fund left out
robokit.profile    risk questionnaire -> tolerance, capacity -> target volatility
robokit.engine     portfolio construction on top of the ``optimizer`` package
robokit.signals    market-context flags (trend, macro, geopolitics, news tone);
                   context only, they never move the weights
robokit.views      optional Black-Litterman views with a bounded tilt
robokit.stress     historical scenario stress tests
robokit.projection bootstrap projections of future outcomes
robokit.explain    plain-language explanations generated from numbers, not by a model
robokit.tools      the tool contract shared by the MCP server, the CLI agent and the web page

Every number a user sees is computed here. Language models only ask questions,
call these tools and explain what the tools returned.
"""

__version__ = "3.3.0"
