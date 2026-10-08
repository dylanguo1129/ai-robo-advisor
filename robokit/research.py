"""Helpers for the pre-registered evaluation (scripts/run_v3_evaluation.py, docs/RESEARCH_LOG.md section 10).

Nothing here is used by the product. The engine side of the evaluation is ``engine.as_of`` (returns, rates and
exchange rates that stop at a past month) and the ``research`` switches of ``engine.build_portfolio`` (one component
changed at a time).
"""

from __future__ import annotations

import pandas as pd

from .engine import _load_all
from .shelf import PRIOR, SLEEVES, candidates


def default_sleeves(market: str) -> list[str]:
    """The reference mix's slots: every sleeve with a policy share, plus cash (as engine.select_funds)."""
    return [k for k, v in PRIOR[market].items() if v > 0] + [f"{market.lower()}_cash"]


def own_history_months(date) -> pd.Series:
    """Months of each fund's own monthly returns up to the end of ``date``'s month (no stand-ins)."""
    _, R, _, _ = _load_all()
    d = pd.Timestamp(date) + pd.offsets.MonthEnd(0)
    return R.loc[:d].notna().sum()


def pit_shelf(market: str, date, min_months: int = 36) -> tuple[dict, list[str], dict]:
    """Point-in-time shelf: for each default slot, the best-scoring fund (today's score: size, trading, fee) that
    already had ``min_months`` of its own returns at ``date``. A slot with no such fund is left out, and the engine
    spreads its policy share over the others. Returns (swaps, slots kept, fund per slot).

    Residual look-ahead, stated with the results: the score uses today's size, trading and fee, and funds that closed
    before today are not in the list (survivorship)."""
    U, _, _, _ = _load_all()
    months = own_history_months(date)
    swaps, kept, chosen = {}, [], {}
    for k in default_sleeves(market):
        c = candidates(U, SLEEVES[k])
        c = c[c.yahoo.map(lambda t: int(months.get(t, 0))) >= min_months]
        if c.empty:
            continue
        kept.append(k)
        chosen[k] = str(c.iloc[0].yahoo)
        swaps[k] = chosen[k]
    return swaps, kept, chosen
