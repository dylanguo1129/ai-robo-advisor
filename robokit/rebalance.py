"""From what the person holds to a list of orders (v3 Track C1). web/robokit.js ``rebalance`` is the same algorithm.

The rules, in the order they run:

1. Cash flows first. New money buys the funds furthest below target, in proportion to how far below they are; a
   withdrawal sells the funds furthest above target the same way. Vanguard (2010): "Rebalance with portfolio cash
   flows"; Betterment, Wealthfront and Wealthsimple describe the same practice. Because the targets are set on the
   account after the flow, the gaps (or excesses) always add up to at least the flow, so nothing else is sold to
   invest new money and nothing below target is sold to pay a withdrawal.
2. Tolerance bands with a destination. After the flow, a fund is out of band when it is more than
   ``min(band_abs, band_rel x target)`` from its target (2 points, or a quarter of a small target, so a 2% position
   cannot double before it is touched). An out-of-band fund is traded back to ``destination`` of its band (7/8, from
   Vanguard's 2024 "threshold of 200 bps and a destination of 175 bps"), not to the target: with proportional costs
   the optimal policy trades to the edge of the no-trade region (Donohue and Yip 2003). The other side of those
   trades is spread over the funds still inside their bands, by the same rule as a cash flow. A fund held but not in
   the mix has a target and a band of zero, so it is sold.
3. Whole units. Buys round down and sells round up (never more than held). Trades under ``min_trade`` dollars are
   skipped unless a withdrawal needs them. The cash must cover the orders and their estimated cost; if it does not,
   buys are trimmed one unit at a time (the most overweight fund first), then sells added.
4. Residual cash. One unit at a time goes to the fund furthest below target whose unit price and cost fit, while
   buying it brings that fund closer to target, keeping ``cash_reserve`` in cash.
5. Cost and liquidity. The estimated cost is ``cost_bps`` of the amount traded. When average daily dollar volumes
   are given, each order is shown as a share of its fund's volume and flagged above ``adv_limit``.

Nothing here decides the mix: the targets come from ``build_portfolio``.
"""

from __future__ import annotations

import math

from .errors import RoboKitInputError

BAND_ABS = 0.02
BAND_REL = 0.25
DESTINATION = 0.875  # 175 / 200
MIN_TRADE = 50.0
COST_BPS = 10.0
ADV_LIMIT = 0.01


def _num(x, name: str, lo: float | None = None, lo_open: bool = False) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise RoboKitInputError(f"{name} must be a finite number.", {"field": name})
    x = float(x)
    if lo is not None and (x <= lo if lo_open else x < lo):
        raise RoboKitInputError(f"{name} must be {'above' if lo_open else 'at least'} {lo:g}.", {"field": name})
    return x


def _spread(amount: float, value: list[float], goal: list[float], idx: list[int], target: list[float]) -> list[float]:
    """Dollar trades over the funds in ``idx`` that add up to ``amount`` (buy when positive, sell when negative):
    first in proportion to each fund's distance from its goal on the needed side; any remainder by target weight
    (buys) or by what is left after the excess (sells), so a sell never exceeds the holding."""
    out = [0.0] * len(value)
    if amount == 0 or not idx:
        return out
    if amount > 0:
        gap = {i: max(0.0, goal[i] - value[i]) for i in idx}
        g = sum(gap.values())
        if g >= amount:
            for i in idx:
                out[i] = amount * gap[i] / g
        else:
            rest, tw = amount - g, sum(target[i] for i in idx)
            for i in idx:
                out[i] = gap[i] + rest * (target[i] / tw if tw > 0 else 1.0 / len(idx))
        return out
    need = -amount
    exc = {i: max(0.0, value[i] - goal[i]) for i in idx}
    e = sum(exc.values())
    if e >= need:
        for i in idx:
            out[i] = -need * exc[i] / e
    else:
        left = {i: value[i] - exc[i] for i in idx}
        lw, rest = sum(left.values()), need - e
        for i in idx:
            out[i] = -(exc[i] + (rest * left[i] / lw if lw > 0 else 0.0))
    return out


def _shift_into(x: list[float], a: list[float], lo: list[float], hi: list[float], total: float) -> list[float]:
    """v_i = clip(x_i - tau a_i, lo_i, hi_i) with sum v = total (the projection of x onto the box and the budget in the
    metric weighted by 1/a). The sum falls as tau rises, piecewise linearly between the breakpoints (x - hi)/a and
    (x - lo)/a, so tau is found exactly: the same method as optimizer/solver.py project_weighted_capped_simplex."""
    n = len(x)

    def g(tau: float) -> float:
        return sum(min(hi[i], max(lo[i], x[i] - tau * a[i])) for i in range(n))

    bp = sorted({(x[i] - hi[i]) / a[i] for i in range(n)} | {(x[i] - lo[i]) / a[i] for i in range(n)})
    if total >= g(bp[0]) - 1e-15:
        tau = bp[0]
    elif total <= g(bp[-1]) + 1e-15:
        tau = bp[-1]
    else:
        k, m = 0, len(bp) - 1  # g(bp[k]) > total > g(bp[m])
        while m - k > 1:
            mid = (k + m) // 2
            if g(bp[mid]) >= total:
                k = mid
            else:
                m = mid
        gk, gm = g(bp[k]), g(bp[m])
        tau = bp[k] if gk == gm else bp[k] + (gk - total) * (bp[m] - bp[k]) / (gk - gm)
    return [min(hi[i], max(lo[i], x[i] - tau * a[i])) for i in range(n)]


def rebalance(
    targets: dict,
    units: dict | None = None,
    prices: dict | None = None,
    cash: float = 0.0,
    flow: float = 0.0,
    band_abs: float = BAND_ABS,
    band_rel: float = BAND_REL,
    destination: float = DESTINATION,
    min_trade: float = MIN_TRADE,
    cash_reserve: float = 0.0,
    whole_units: bool = True,
    cost_bps: float = COST_BPS,
    adv: dict | None = None,
    adv_limit: float = ADV_LIMIT,
    band_trades: bool = True,
) -> dict:
    """Orders that take the account from ``units`` (fund -> units held) and ``cash`` to the ``targets`` (fund ->
    weight, adding to 1), after a cash ``flow`` (new money positive, a withdrawal negative). ``prices`` gives a price
    for every fund in either. Returns the orders, the weights before and after, and the cost. With ``band_trades``
    False only the cash flow trades: a calendar rule between its dates, when no fund is rebalanced for drift (a fund
    whose target is zero has a band of zero, so any band would sell it)."""
    units = dict(units or {})
    prices = dict(prices or {})
    if not isinstance(targets, dict) or not targets:
        raise RoboKitInputError("targets must name at least one fund with its weight.", {"field": "targets"})
    tick = list(targets) + [t for t in units if t not in targets]
    t_w = [_num(targets.get(t, 0.0), f"targets[{t}]", 0.0) for t in tick]
    if abs(sum(t_w) - 1.0) > 1e-6:
        raise RoboKitInputError(f"The target weights add up to {sum(t_w):.4f}, not 1.", {"field": "targets"})
    held = [_num(units.get(t, 0.0), f"units[{t}]", 0.0) for t in tick]
    if any(t not in prices for t in tick):
        missing = [t for t in tick if t not in prices]
        raise RoboKitInputError("A price is needed for every fund: " + ", ".join(missing) + ".", {"field": "prices", "missing": missing})
    px = [_num(prices[t], f"prices[{t}]", 0.0, lo_open=True) for t in tick]
    cash = _num(cash, "cash", 0.0)
    flow = _num(flow, "flow")
    band_abs, band_rel = _num(band_abs, "band_abs", 0.0), _num(band_rel, "band_rel", 0.0)
    destination = _num(destination, "destination", 0.0)
    if destination > 1:
        raise RoboKitInputError(
            "destination is a share of the band, from 0 (back to target) to 1 (back to the band edge).", {"field": "destination"}
        )
    min_trade, cash_reserve = _num(min_trade, "min_trade", 0.0), _num(cash_reserve, "cash_reserve", 0.0)
    cost_bps, adv_limit = _num(cost_bps, "cost_bps", 0.0), _num(adv_limit, "adv_limit", 0.0, lo_open=True)

    n = len(tick)
    value = [u * p for u, p in zip(held, px)]
    held_value = sum(value)
    avail = cash + flow  # cash on hand after the flow
    invest = held_value + avail - cash_reserve  # the money the targets apply to
    if invest <= 0:
        raise RoboKitInputError(
            "The withdrawal and the cash kept aside are larger than the account.",
            {"field": "flow", "account": round(held_value + cash, 2)},
        )
    goal = [w * invest for w in t_w]
    everyone = list(range(n))

    # 1. the cash flow (to or from the cash kept aside)
    flow_trade = _spread(avail - cash_reserve, value, goal, everyone, t_w)
    v1 = [v + d for v, d in zip(value, flow_trade)]

    # 2. bands, after the flow
    w1 = [v / invest for v in v1]
    band = [min(band_abs, band_rel * w) for w in t_w]
    out = [band_trades and abs(w1[i] - t_w[i]) > band[i] + 1e-12 for i in range(n)]
    band_trade = [0.0] * n
    if any(out):
        # out-of-band funds end within destination x band of target; funds inside their band may move through their
        # target but never past the destination edge on the far side, nor further out than they are. Every interval
        # contains the target, so a mix inside all of them exists; take the one closest to w1 (weighted by target).
        lo = [t_w[i] - destination * band[i] if out[i] else min(w1[i], t_w[i] - destination * band[i]) for i in range(n)]
        hi = [t_w[i] + destination * band[i] if out[i] else max(w1[i], t_w[i] + destination * band[i]) for i in range(n)]
        w2 = _shift_into(w1, [max(w, 1e-12) for w in t_w], lo, hi, 1.0)
        band_trade = [(w2[i] - w1[i]) * invest for i in range(n)]
    trade = [f + b for f, b in zip(flow_trade, band_trade)]

    # 3. whole units, minimum trade
    def to_units(i: int, dollars: float) -> float:
        if not whole_units:
            return round(dollars / px[i], 6) if dollars > 0 else -min(held[i], round(-dollars / px[i], 6))
        if dollars > 0:
            return float(math.floor(dollars / px[i] + 1e-9))
        return -float(min(held[i], math.ceil(-dollars / px[i] - 1e-9)))

    q = [to_units(i, trade[i]) if abs(trade[i]) > 1e-9 else 0.0 for i in range(n)]
    needed_sell = [flow < 0 and flow_trade[i] < 0 and q[i] < 0 for i in range(n)]  # sells that pay a withdrawal
    reason = [[] for _ in range(n)]
    for i in range(n):
        if q[i] and abs(q[i] * px[i]) < min_trade and not needed_sell[i]:
            q[i] = 0.0
            reason[i].append("under the minimum trade")

    rate = cost_bps / 1e4

    def cash_after() -> float:  # after the orders and their estimated cost
        return avail - sum(q[i] * px[i] for i in range(n)) - rate * sum(abs(q[i]) * px[i] for i in range(n))

    def dev(i: int) -> float:  # dollars above target after the orders
        return (held[i] + q[i]) * px[i] - goal[i]

    for _ in range(10 * n + int(sum(abs(x) for x in q)) + 1):  # trim buys, then sell, until the cash covers the orders
        if cash_after() >= cash_reserve - 1e-9:
            break
        buys = [i for i in range(n) if q[i] > 0]
        if buys:
            i = max(buys, key=lambda k: (dev(k), -k))
            q[i] -= 1.0 if whole_units else min(q[i], (cash_reserve - cash_after()) / (px[i] * (1 + rate)))
        else:
            sellable = [i for i in range(n) if held[i] + q[i] > 0]
            if not sellable:
                break
            i = max(sellable, key=lambda k: (dev(k), -k))
            q[i] -= 1.0 if whole_units else min(held[i] + q[i], (cash_reserve - cash_after()) / (px[i] * (1 - rate)))
    if cash_after() < cash_reserve - 1e-6:
        raise RoboKitInputError("The holdings cannot be sold for enough cash to pay the withdrawal.", {"field": "flow"})

    # 4. residual cash, one unit at a time, while it brings a fund closer to target
    if whole_units:
        for _ in range(100_000):
            spare = cash_after() - cash_reserve
            ok = [
                i
                for i in range(n)
                if t_w[i] > 0 and px[i] * (1 + rate) <= spare + 1e-9 and -dev(i) >= px[i] / 2 and (q[i] > 0 or px[i] >= min_trade)
            ]
            if not ok:
                break
            i = max(ok, key=lambda k: (-dev(k), -k))
            q[i] += 1.0
            if "residual cash" not in reason[i]:
                reason[i].append("residual cash")

    # report
    after_units = [held[i] + q[i] for i in range(n)]
    after_value = [after_units[i] * px[i] for i in range(n)]
    total_after = sum(after_value)
    c_after = cash_after()
    gross = sum(abs(q[i]) * px[i] for i in range(n))
    account = held_value + avail
    rows = []
    for i in range(n):
        if q[i] > 0 and flow_trade[i] > 0:
            reason[i].insert(0, "new money")
        if q[i] < 0 and flow_trade[i] < 0 and flow < 0:
            reason[i].insert(0, "withdrawal")
        if q[i] and out[i]:
            reason[i].insert(0, "not in the mix" if t_w[i] == 0 else "outside its band")
        if q[i] and not reason[i]:
            reason[i].append("balances the other orders")
        dollars = q[i] * px[i]
        row = {
            "ticker": tick[i],
            "target": round(t_w[i], 6),
            "band": round(band[i], 6),
            "units_before": held[i],
            "weight_before": round(value[i] / held_value, 6) if held_value > 0 else None,
            "action": "buy" if q[i] > 0 else "sell" if q[i] < 0 else "hold",
            "units": abs(q[i]),
            "price": px[i],
            "amount": round(abs(dollars), 2),
            "units_after": after_units[i],
            "weight_after": round(after_value[i] / total_after, 6) if total_after > 0 else None,
            "out_of_band_after_flow": out[i],
            "reason": reason[i] if q[i] else [r for r in reason[i] if r == "under the minimum trade"],
        }
        if adv and tick[i] in adv and q[i]:
            vol = _num(adv[tick[i]], f"adv[{tick[i]}]", 0.0, lo_open=True)
            row["share_of_daily_volume"] = round(abs(dollars) / vol, 6)
            row["liquidity_flag"] = abs(dollars) / vol > adv_limit
        rows.append(row)

    def drift(ws):
        return sum(abs(w - t) for w, t in zip(ws, t_w)) / 2

    before_w = [v / held_value for v in value] if held_value > 0 else None
    after_w = [v / total_after for v in after_value] if total_after > 0 else None
    notes = []
    if not any(out):
        notes.append(
            "No fund is outside its band, so only the cash flow is traded." if flow else "No fund is outside its band: nothing to trade."
        )
    skipped = [tick[i] for i in range(n) if "under the minimum trade" in reason[i] and not q[i]]
    if skipped:
        notes.append(f"Skipped because each order would be under {min_trade:,.0f}: " + ", ".join(skipped) + ".")
    flagged = [r["ticker"] for r in rows if r.get("liquidity_flag")]
    if flagged:
        notes.append(
            f"Large against daily trading volume (over {adv_limit:.0%}): "
            + ", ".join(flagged)
            + ". Consider splitting the order over several days."
        )
    return {
        "rows": rows,
        "cash_before": round(cash, 2),
        "flow": round(flow, 2),
        "cash_after": round(c_after, 2),
        "cash_reserve": round(cash_reserve, 2),
        "traded": round(gross, 2),
        "turnover": round(gross / 2 / account, 6) if account > 0 else 0.0,
        "estimated_cost": round(gross * cost_bps / 1e4, 2),
        "drift_before": None if before_w is None else round(drift(before_w), 6),
        "drift_after": None if after_w is None else round(drift(after_w), 6),
        "largest_gap_after": None if after_w is None else round(max(abs(w - t) for w, t in zip(after_w, t_w)), 6),
        "notes": notes,
        "rule": (
            f"cash flows first; bands of min({band_abs:.0%}, {band_rel:.0%} of target), traded back to {destination:.0%} of the band; "
            f"whole units, orders under {min_trade:,.0f} skipped; residual cash to the fund furthest below target"
        ),
    }
