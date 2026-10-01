"""Price data hygiene.

Everything downstream assumes *monthly simple total returns* on a common
calendar. The traps this module guards against are the ones that quietly
inflate or distort a back-test:

* using price returns instead of total returns (dividends matter a lot for
  bond, dividend and covered-call ETFs)  -> we use Yahoo's adjusted close;
* mixing ETFs with different history lengths  -> common window, minimum
  history, explicit report of what was dropped;
* stale or missing prints around holidays  -> month-end resampling with a
  bounded forward fill, then the return calculation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

MONTHS_PER_YEAR = 12


def download_prices(tickers: list[str], start: str, end: str, cache_path: str | None = None) -> pd.DataFrame:
    """Download adjusted daily closes with yfinance and optionally cache to CSV.

    ``auto_adjust=True`` returns dividend- and split-adjusted closes, i.e. a
    total-return price series. Tickers on the TSX end in ``.TO``.
    """
    import yfinance as yf  # imported lazily so the package works offline

    px = yf.download(list(tickers), start=start, end=end, auto_adjust=True, progress=False, threads=True)["Close"]
    if isinstance(px, pd.Series):
        px = px.to_frame(tickers[0])
    px.index = pd.to_datetime(px.index)
    px = px.sort_index()
    if cache_path:
        px.to_csv(cache_path)
    return px


def load_prices(path: str) -> pd.DataFrame:
    """Load a cached daily adjusted-close CSV written by :func:`download_prices`."""
    px = pd.read_csv(path, index_col=0, parse_dates=True)
    return px.sort_index()


@dataclass
class ReturnPanel:
    """Monthly returns plus a record of the hygiene decisions taken."""

    returns: pd.DataFrame
    dropped: dict[str, str] = field(default_factory=dict)
    window: tuple[pd.Timestamp, pd.Timestamp] | None = None

    @property
    def n_months(self) -> int:
        return len(self.returns)

    def summary(self) -> str:
        w = f"{self.window[0].date()} to {self.window[1].date()}" if self.window else "n/a"
        lines = [f"{self.returns.shape[1]} ETFs, {self.n_months} monthly observations, window {w}"]
        for t, why in self.dropped.items():
            lines.append(f"  dropped {t}: {why}")
        return "\n".join(lines)


def to_monthly_returns(
    prices: pd.DataFrame,
    min_months: int = 36,
    max_ffill_days: int = 5,
    start: str | None = None,
    end: str | None = None,
) -> ReturnPanel:
    """Convert daily adjusted closes into aligned monthly simple returns.

    Steps: bounded forward-fill of isolated gaps -> month-end price ->
    percentage change -> drop ETFs with fewer than ``min_months`` returns ->
    restrict every survivor to the common window so the covariance matrix is
    computed on the same months for every pair.
    """
    px = prices.copy()
    if start:
        px = px.loc[pd.Timestamp(start) :]
    if end:
        px = px.loc[: pd.Timestamp(end)]
    px = px.ffill(limit=max_ffill_days)

    monthly_px = px.resample("ME").last()
    rets = monthly_px.pct_change()

    dropped: dict[str, str] = {}
    keep = []
    for col in rets.columns:
        n = rets[col].notna().sum()
        if n < min_months:
            dropped[col] = f"only {n} monthly returns, minimum is {min_months}"
        else:
            keep.append(col)
    rets = rets[keep]

    # common window: first month where every survivor has a return
    first_valid = max(rets[c].first_valid_index() for c in keep)
    last_valid = min(rets[c].last_valid_index() for c in keep)
    rets = rets.loc[first_valid:last_valid]
    rets = rets.dropna(how="any")

    if len(rets) < min_months:
        raise ValueError(f"common window has only {len(rets)} months (< {min_months}); widen the date range or drop short-history ETFs")

    return ReturnPanel(returns=rets, dropped=dropped, window=(rets.index[0], rets.index[-1]))


def annualize_mean(monthly_mean: np.ndarray | pd.Series) -> np.ndarray | pd.Series:
    """Arithmetic annualization of a monthly mean return."""
    return monthly_mean * MONTHS_PER_YEAR


def annualize_cov(monthly_cov: np.ndarray | pd.DataFrame) -> np.ndarray | pd.DataFrame:
    return monthly_cov * MONTHS_PER_YEAR


def integrity_report(prices: pd.DataFrame, monthly: pd.DataFrame, jump: float = 0.30, stale_days: int = 5) -> pd.DataFrame:
    """Data-quality checks the back-testing protocol asks for before modelling
    ("Ensure data quality"; "Do not arbitrarily exclude outliers" -- we flag,
    we do not delete). One row per finding: ticker, date, kind, value.

    kinds: 'monthly_jump' (|monthly return| > jump), 'stale_price' (the same
    daily close repeated for >= stale_days trading days), 'missing_run'
    (a gap of >= stale_days trading days in the daily series).
    """
    rows = []
    for t in monthly.columns:
        big = monthly[t][monthly[t].abs() > jump]
        for d, v in big.items():
            rows.append({"ticker": t, "date": d.date(), "kind": "monthly_jump", "value": float(v)})
    for t in prices.columns:
        s = prices[t]
        same = (s == s.shift()).astype(int)
        run = same.groupby((same == 0).cumsum()).cumsum()
        stale = run[run >= stale_days - 1]
        if len(stale):
            rows.append({"ticker": t, "date": stale.index[0].date(), "kind": "stale_price", "value": int(stale.max() + 1)})
        gaps = s.isna().astype(int)
        gap_run = gaps.groupby((gaps == 0).cumsum()).cumsum()
        inner = gap_run.loc[s.first_valid_index() : s.last_valid_index()]
        if (inner >= stale_days).any():
            rows.append({"ticker": t, "date": inner[inner >= stale_days].index[0].date(), "kind": "missing_run", "value": int(inner.max())})
    return pd.DataFrame(rows, columns=["ticker", "date", "kind", "value"])


def max_drawdown(returns: pd.Series) -> float:
    """Maximum peak-to-trough drawdown of a simple-return series (negative number)."""
    wealth = (1 + returns).cumprod()
    peak = wealth.cummax()
    return float((wealth / peak - 1).min())
