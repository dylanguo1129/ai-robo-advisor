"""Figures for the paper, from output/v3/results.json and the E1 monthly paths (output/v3/e1_*.csv).

    python scripts/paper/figures.py   -> docs/paper/img/*.png

Colour: the Okabe and Ito (2008) colour-blind-safe palette in a fixed order (a series keeps its colour in every
figure); one axis per chart; text in ink colours, never in a series colour; a legend whenever there are two or more
series; direct labels kept few.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "output" / "v3"
IMG = ROOT / "docs" / "paper" / "img"
INK, MUTED, GRID = "#1a1a1a", "#595959", "#d9d9d9"
COLOR = {  # Okabe-Ito, fixed by series
    "robokit": "#0072B2",
    "static_mix": "#E69F00",
    "textbook_60": "#D55E00",
    "erc_cash": "#009E73",
    "minvar_cash": "#CC79A7",
    "no_resample": "#56B4E9",
    "CA": "#0072B2",
    "US": "#D55E00",
    "constant_correlation": "#0072B2",
    "sample": "#E69F00",
}
LABEL = {
    "robokit": "Robo-Kit",
    "static_mix": "Static mix",
    "textbook_60": "Textbook (60 m)",
    "erc_cash": "Risk parity + cash",
    "minvar_cash": "Min variance + cash",
    "no_resample": "No resampling",
}

plt.rcParams.update(
    {
        "font.family": "Calibri",
        "font.size": 9,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "legend.frameon": False,
        "figure.dpi": 200,
        "savefig.bbox": "tight",
    }
)


def save(fig, name):
    IMG.mkdir(parents=True, exist_ok=True)
    fig.savefig(IMG / name, facecolor="white")
    plt.close(fig)


def risk_delivery(res):
    fig, ax = plt.subplots(figsize=(6.2, 2.8))
    ax.axhspan(0.80, 1.25, color="#f0f0f0", zorder=0)
    ax.axhline(1.0, color=MUTED, lw=0.8, ls="--")
    for k, m in enumerate(("CA", "US")):
        rd = res["E1"][m]["risk_delivery"]
        for L in (1, 2, 3, 4, 5):
            src = rd["primary"] if L in (2, 3, 4) else rd[f"level_{L}"]
            v = src[str(L)]
            x = L + (k - 0.5) * 0.22
            ax.plot([x, x], [v["lo"], v["hi"]], color=COLOR[m], lw=1.6)
            ax.plot(x, v["ratio"], "o", color=COLOR[m], ms=5, mec="white", mew=1.0, label=m if L == 1 else None)
    ax.set_xticks([1, 2, 3, 4, 5], [f"Level {L}" for L in (1, 2, 3, 4, 5)])
    ax.set_ylabel("Realised / target volatility")
    ax.legend(title=None, loc="upper left", ncol=2)
    ax.text(5.45, 1.235, "band for 'delivered'", ha="right", va="top", color=MUTED, fontsize=8)
    save(fig, "risk_delivery.png")


def sharpe_forest(res):
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.0), sharey=True)
    bench = ("static_mix", "textbook_60", "erc_cash", "minvar_cash")
    for ax, m in zip(axes, ("CA", "US")):
        comp = res["E1"][m]["comparisons"]
        y = 0
        ticks, labels = [], []
        for b in bench:
            for L in (2, 3, 4):
                c = comp.get(b, {}).get(str(L))
                if not c or "error" in c:
                    continue
                lo, hi = c["ci95_annual"]
                ax.plot([lo, hi], [y, y], color=COLOR[b], lw=1.6)
                ax.plot(c["sharpe_diff_annual"], y, "o", color=COLOR[b], ms=4.5, mec="white", mew=0.8)
                ticks.append(y)
                labels.append(f"{LABEL[b]}, L{L}")
                y -= 1
            y -= 0.6
        ax.axvline(0, color=MUTED, lw=0.8)
        ax.axvline(-0.10, color=MUTED, lw=0.8, ls=":")
        ax.set_title(m, color=INK, fontsize=10, loc="left")
        ax.set_xlabel("Robo-Kit minus benchmark, annual Sharpe (95% CI)")
        ax.set_yticks(ticks, labels)
    axes[0].text(-0.105, 0.5, "non-inferiority margin", rotation=90, color=MUTED, fontsize=7, ha="right", va="bottom")
    save(fig, "sharpe_differences.png")


def e3_losses(res):
    s = res["E3"]["summary"]
    methods = ["robokit", "no_resample", "textbook_60", "static_mix", "erc_cash", "minvar_cash"]
    fig, ax = plt.subplots(figsize=(6.2, 2.8))
    worlds = ("a", "b", "c")
    names = {"a": "World a (model right)", "b": "World b (model wrong)", "c": "World c (regimes)"}
    w = 0.13
    for j, m in enumerate(methods):
        vals = [s[wd]["3"]["180"][m]["loss_bp"] for wd in worlds]
        errs = [1.96 * s[wd]["3"]["180"][m]["loss_bp_se"] for wd in worlds]
        x = np.arange(3) + (j - (len(methods) - 1) / 2) * w
        ax.bar(x, vals, width=w * 0.9, color=COLOR[m], label=LABEL[m], edgecolor="white", linewidth=0.6)
        ax.errorbar(x, vals, yerr=errs, fmt="none", ecolor=INK, elinewidth=0.6, capsize=1.5)
    ax.set_xticks(range(3), [names[wd] for wd in worlds])
    ax.set_ylabel("Certainty-equivalent loss (bp a year)")
    ax.legend(ncol=3, loc="upper left", fontsize=7.5)
    save(fig, "e3_losses.png")


def qis_switch(res):
    q = res["E3"]["qis_switch"]["by_ratio"]
    fig, ax = plt.subplots(figsize=(6.2, 2.6))
    for name in ("constant_correlation", "sample"):
        r = sorted((float(k), v) for k, v in q[name].items())
        x = [a for a, _ in r]
        y = [100 * v["mean_rel"] for _, v in r]
        e = [196 * v["se"] for _, v in r]
        ax.errorbar(
            x,
            y,
            yerr=e,
            color=COLOR[name],
            marker="o",
            ms=4,
            lw=1.4,
            capsize=2,
            label="truth: constant correlation" if name == "constant_correlation" else "truth: sample covariance",
        )
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.axvline(res["E3"]["qis_switch"]["switch"], color=MUTED, lw=0.8, ls="--")
    ax.set_xlabel("N / T")
    ax.set_ylabel("QIS vs constant correlation,\ntrue variance difference (%)")
    ax.legend(loc="best")
    save(fig, "qis_switch.png")


def growth(market, level=3):
    fig, ax = plt.subplots(figsize=(6.2, 2.7))
    for s in ("robokit", "static_mix", "textbook_60", "minvar_cash"):
        f = RES / f"e1_{market}_{s}_L{level}.csv"
        if not f.exists():
            continue
        p = pd.read_csv(f, index_col=0, parse_dates=True)
        ax.plot(p.index, (1 + p["net"]).cumprod(), color=COLOR[s], lw=1.4 if s == "robokit" else 1.0, label=LABEL[s])
    ax.set_ylabel("Growth of 1, after costs")
    ax.legend(loc="upper left", ncol=2)
    save(fig, f"growth_{market}_L{level}.png")


def main():
    res = json.loads((RES / "results.json").read_text())
    risk_delivery(res)
    sharpe_forest(res)
    e3_losses(res)
    qis_switch(res)
    for m in ("CA", "US"):
        growth(m)
    print("figures written to", IMG)


if __name__ == "__main__":
    main()
