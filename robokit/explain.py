"""Plain-language explanations built only from computed numbers.

These sentences are what a first-time investor reads. They are generated
from the portfolio result by templates, so every figure in them is a figure
the engine computed; a language model may rephrase them in conversation but
never needs to invent a number.
"""

from __future__ import annotations


def _pct(x: float, d: int = 0) -> str:
    return f"{x * 100:.{d}f}%"


def _money(x: float, ccy: str) -> str:
    sym = "$" if ccy in ("CAD", "USD") else ""
    return f"{sym}{x:,.0f} {ccy}"


def explain_portfolio(p: dict) -> dict:
    s, r, ccy = p["stats"], p["risk"], p["currency"]
    hold = p["holdings"]
    pr = p.get("projection") or {}
    amt = pr.get("amount", 10_000)
    en = []

    mix = p["mix"]["asset_class"]
    parts_en = ", ".join(f"{_pct(v)} {k.lower()}" for k, v in mix.items() if v >= 0.005)
    en.append(f"The mix: {parts_en}, spread over {s['n_holdings']} funds.")

    if r.get("risk_share") is None:  # the person's own weights
        en.append(
            f"These are your own weights, not the model's. They swing about {_pct(s['volatility'], 1)} a year, like level {r['level']:g} of 5."
        )
    else:
        tv = r.get("target_vol")
        if tv is not None and abs(tv - s["volatility"]) >= 0.002:  # the target was not reached: say both
            en.append(
                f"Level {r['level']:g} of 5 ({r['label'].lower()}) aims for about {_pct(r['risk_share'])} of the stock market's ups and downs, "
                f"a volatility of about {_pct(tv, 1)} a year; with these funds the mix gets to about {_pct(s['volatility'], 1)}."
            )
        else:
            en.append(
                f"Level {r['level']:g} of 5 ({r['label'].lower()}) aims for about {_pct(r['risk_share'])} of the stock market's ups and downs. "
                f"For these funds that is a volatility of about {_pct(s['volatility'], 1)} a year."
            )

    one, val, mo = pr.get("one_year"), pr.get("one_year_value"), pr.get("monthly_contribution") or 0
    if one and val and mo:  # year-end values with the monthly adds or withdrawals, as the page's headline shows them
        flow_en = f"plus {_money(mo, ccy)} a month" if mo > 0 else f"with {_money(-mo, ccy)} a month taken out"
        en.append(
            f"In 8 years out of 10, {_money(amt, ccy)} {flow_en} might end the year between {_money(val['p10'], ccy)} and {_money(val['p90'], ccy)}. "
            f"In a bad year (about 1 in 20) it could end the year at about {_money(val['p5'], ccy)}. These are ranges, not promises."
        )
    elif one:
        en.append(
            f"In 8 years out of 10, {_money(amt, ccy)} might end the year between {_money(amt * (1 + one['p10']), ccy)} and {_money(amt * (1 + one['p90']), ccy)}. "
            f"In a bad year (about 1 in 20) it could fall to about {_money(amt * (1 + one['p5']), ccy)}. These are ranges, not promises."
        )

    en.append(
        f"Using published planning assumptions after fees, a middle outcome is about {_pct(s['planning_return'], 1)} a year over {pr.get('years', 10)} {'year' if pr.get('years', 10) == 1 else 'years'}; "
        f"cash pays about {_pct(s['risk_free'], 1)} today."
    )

    if s.get("weighted_mer") is not None:
        en.append(
            f"Fund fees average {_pct(s['weighted_mer'], 2)} a year: about {_money(s['fee_per_year'], ccy)} a year on {_money(amt, ccy)}."
        )

    top_risk = max(hold, key=lambda h: h["risk_share"])
    if round(top_risk["risk_share"] * 100) > round(top_risk["weight"] * 100) + 2:  # "but" only when the risk share is clearly larger
        en.append(
            f"{top_risk['symbol']} is {_pct(top_risk['weight'])} of the money but {_pct(top_risk['risk_share'])} of the risk: "
            "the fund that swings most drives most of the ups and downs."
        )
    else:
        en.append(
            f"{top_risk['symbol']} is {_pct(top_risk['weight'])} of the money and {_pct(top_risk['risk_share'])} of the risk: "
            "the largest source of ups and downs, in line with its size."
        )

    rows = [x for x in (p.get("stress") or []) if x.get("portfolio_return") is not None]
    worst = min(rows, key=lambda x: x["portfolio_return"], default=None)
    missing = [x for x in (p.get("stress") or []) if x.get("portfolio_return") is None]
    if worst:
        d = worst.get("dollars")
        en.append(
            f"Replaying the {worst['scenario']}, this mix would have fallen about {_pct(-worst['portfolio_return'])}"
            + (f" (about {_money(-d, ccy)} on {_money(amt, ccy)})" if d is not None and d < 0 else "")
            + " before recovering."
        )
    if missing:
        funds = sorted({t.replace(".TO", "").replace(".NE", "") for x in missing for t in x.get("not_estimable", [])})
        en.append(
            f"{', '.join(x['scenario'] for x in missing)}: not shown, because {', '.join(funds)} has no history or stand-in for that period."
        )

    per_fund = {}
    for h in hold:
        why_en = h.get("plain") or f"{h['asset_class']} fund you chose."
        per_fund[h["ticker"]] = {
            "en": f"{h['symbol']} ({_pct(h['weight'])}): {why_en}" + (f" Fee {_pct(h['mer'], 2)}." if h.get("mer") is not None else ""),
        }
    return {"en": en, "per_fund": per_fund}
