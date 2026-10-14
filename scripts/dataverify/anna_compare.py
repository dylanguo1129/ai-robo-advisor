"""Fund-by-fund comparison of our Canadian universe with the team data layer's dataset (Oct 10 export), which was
fetched and computed by separate code: MER, AUM, first price date, 1-year and 3-year returns, 3-year volatility.

    python -B scripts/dataverify/anna_compare.py <robokit_etf_dataset_YYYYMMDD.xlsx>  -> data/v2/dataverify/anna_compare.csv
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[2] / "data" / "v2" / "dataverify"
REPO = Path(__file__).resolve().parents[2]
X = Path(sys.argv[1])  # the data layer's dataset export (robokit_etf_dataset_YYYYMMDD.xlsx)

U = pd.read_pickle(REPO / "data" / "v2" / "universe.pkl")
ca = U[U.market == "CA"].copy()
# MER as Yahoo gave it to our screener, before the bridge filled blanks
ca["mer_ours"] = ca["mer"].where(~ca["why"].fillna("").str.contains("MER from the team's data layer"))
E = pd.read_excel(X, sheet_name="ETFs")
E = E.rename(columns={"yahoo_ticker": "yahoo"})
j = ca.merge(
    E[["yahoo", "mer", "aum", "inception_date", "first_price_date", "return_1y", "return_3y_ann", "vol_3y", "currency_hedged"]],
    on="yahoo",
    how="inner",
    suffixes=("", "_rk"),
)
print("our CA listings:", len(ca), "| in both:", len(j), "| eligible in both:", int(j.eligible.sum()))


def flag(series, name):
    j[name] = series
    return series


# MER (both from Yahoo profiles, fetched separately): agree within 0.02 percentage points
m = j.mer_ours.notna() & j.mer_rk.notna()
dm = (j.mer_ours - j.mer_rk).abs()
flag(m & (dm > 0.0002), "mer_disagree")
unit = m & ((j.mer_rk < 0.0005) | (j.mer_ours < 0.0005))
flag(unit, "mer_tiny")
print(
    f"\nMER: both {int(m.sum())}; within 0.02pp {int((m & (dm <= 0.0002)).sum())}; disagree {int(j.mer_disagree.sum())} "
    f"(eligible {int((j.mer_disagree & j.eligible).sum())}); one side under 0.05% {int(unit.sum())}"
)
# AUM: ours in trading currency, hers in CAD; CA units trade in CAD, so compare CAD units only
a = j.aum.notna() & j.aum_rk.notna() & (j.aum_rk > 0) & (j.currency == "CAD")
ra = j.aum / j.aum_rk
flag(a & ((ra < 0.67) | (ra > 1.5)), "aum_disagree")
print(
    f"AUM (CAD units): both {int(a.sum())}; within a factor of 1.5 {int((a & ~j.aum_disagree).sum())}; "
    f"disagree {int(j.aum_disagree.sum())} (eligible {int((j.aum_disagree & j.eligible).sum())})"
)
# first price: our first month against her first price date (and inception)
fp = pd.to_datetime(j.first_price_date, errors="coerce")
inc = pd.to_datetime(j.inception_date, errors="coerce")
ours_first = pd.to_datetime(j.first_month, errors="coerce")
late = ours_first.notna() & fp.notna() & ((ours_first - fp).dt.days > 62)
early = ours_first.notna() & inc.notna() & ((inc - ours_first).dt.days > 62)
flag(late, "history_later_than_hers")
flag(early, "history_before_inception")
print(
    f"history: our first month more than 2 months after her first price: {int(late.sum())} (eligible {int((late & j.eligible).sum())}); "
    f"our first month more than 2 months before inception: {int(early.sum())} (eligible {int((early & j.eligible).sum())})"
)
# returns and volatility: different windows (ours to Aug 31 from monthly; hers to Oct 9 from daily), so gross errors only
r1 = j.ret_1y.notna() & j.return_1y.notna()
flag(r1 & ((j.ret_1y - j.return_1y).abs() > 0.15), "ret1y_gross")
v3 = j.vol_3y.notna() & j.vol_3y_rk.notna() if "vol_3y_rk" in j else None
if v3 is None:
    j["vol_3y_rk"] = np.nan
v3 = j.vol_3y.notna() & j.vol_3y_rk.notna()
rv = j.vol_3y / j.vol_3y_rk
flag(v3 & ((rv < 0.6) | (rv > 1.6)), "vol3y_gross")
r3 = j.ret_3y.notna() & j.return_3y_ann.notna()
flag(r3 & ((j.ret_3y - j.return_3y_ann).abs() > 0.06), "ret3y_gross")
print(
    f"1-year return: both {int(r1.sum())}, corr {j.loc[r1, ['ret_1y', 'return_1y']].corr().iloc[0, 1]:.3f}, off by >15pp {int(j.ret1y_gross.sum())} (eligible {int((j.ret1y_gross & j.eligible).sum())})"
)
print(
    f"3-year return: both {int(r3.sum())}, corr {j.loc[r3, ['ret_3y', 'return_3y_ann']].corr().iloc[0, 1]:.3f}, off by >6pp a year {int(j.ret3y_gross.sum())} (eligible {int((j.ret3y_gross & j.eligible).sum())})"
)
print(
    f"3-year volatility: both {int(v3.sum())}, corr {j.loc[v3, ['vol_3y', 'vol_3y_rk']].corr().iloc[0, 1]:.3f}, ratio outside 0.6-1.6 {int(j.vol3y_gross.sum())} (eligible {int((j.vol3y_gross & j.eligible).sum())})"
)
cols = [
    "yahoo",
    "name",
    "eligible",
    "mer_ours",
    "mer_rk",
    "aum",
    "aum_rk",
    "first_month",
    "first_price_date",
    "inception_date",
    "ret_1y",
    "return_1y",
    "ret_3y",
    "return_3y_ann",
    "vol_3y",
    "vol_3y_rk",
    "mer_disagree",
    "mer_tiny",
    "aum_disagree",
    "history_later_than_hers",
    "history_before_inception",
    "ret1y_gross",
    "ret3y_gross",
    "vol3y_gross",
]
OUT.mkdir(parents=True, exist_ok=True)
j[cols].to_csv(OUT / "anna_compare.csv", index=False)
any_flag = j[
    ["mer_disagree", "aum_disagree", "history_later_than_hers", "history_before_inception", "ret1y_gross", "ret3y_gross", "vol3y_gross"]
].any(axis=1)
print(f"\nfunds with any flag: {int(any_flag.sum())}; eligible with any flag: {int((any_flag & j.eligible).sum())}")
