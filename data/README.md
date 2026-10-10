# Data

Robo-Kit never ships raw vendor data in git. Every dataset is fetched by code on your own machine, cached under
`data/v2/` (ignored by git), and turned into one small, dated **snapshot** that *is* committed:
`web/data/{core,ca,us}.json`. The web page, the MCP server and a fresh clone all run from that snapshot.

```
python -m robokit refresh   # network: fetch every source into data/v2/ (15-30 min; news is rate-limited)
python -m robokit bundle    # no network: rebuild web/data/*.json (+ web/test_profiles.json) from data/v2/
python -m robokit status    # shows data_source ("local" cache or committed "snapshot") and prices_through
```

Nothing refreshes by itself: there is no scheduler, and the published artifact cannot fetch data at runtime
(its sandbox blocks outside requests). To update the page, run `refresh` then `bundle`, run the tests, commit the
new snapshot and republish the artifact from `web/`.

## Sources

All v2 sources are fetched by `robokit/data/` (`listings.py`, `prices.py`, `context.py`), driven by
`robokit/refresh.py`. No API key and no manual download is needed.

| Source | What it provides | Code | Licence tier |
|---|---|---|---|
| Nasdaq Trader symbol directory (`nasdaqlisted.txt`, `otherlisted.txt`) | US-listed ETF list | `listings.fetch_us_listings` | Personal use |
| TMX Money (`app-money.tmx.com/graphql`, undocumented) | TSX ETF list and fund facts (AUM, inception, holdings, regions) | `listings.fetch_tmx_etfs` | Personal use |
| Yahoo Finance screener (via `yfinance`) | MER (`netExpenseRatio`), net assets, first trade date; the only source for Cboe Canada listings | `listings.fetch_yahoo_screener`, `fetch_yahoo_categories` | Personal use |
| Yahoo Finance prices (via `yfinance`, monthly, dividend-adjusted, full history) | Monthly total returns and volume for every candidate ETF; `CAD=X` exchange rate | `prices.download_monthly`, `usdcad_monthly` | Personal use |
| Bank of Canada Valet | Policy rate, 3-month T-bill (Canadian risk-free rate), 2y/10y yields, CPI | `context.boc_monthly` | Open |
| Yahoo indices `^IRX ^FVX ^TNX ^VIX` | US T-bill (US risk-free rate), 5y/10y yields, VIX | `context.yahoo_monthly` | Personal use |
| FRED `BAMLH0A0HYM2` | US high-yield credit spread | `context.fred_monthly` | Copyrighted series; context only |
| Caldara & Iacoviello GPR | Geopolitical risk indices (world, Canada, US) | `context.gpr_monthly` | CC BY |
| Baker, Bloom & Davis EPU | Economic policy uncertainty (US, Canada) | `context.epu_monthly` | CC BY 4.0 |
| GDELT DOC 2.0 | News tone, volume and a few headlines per topic | `context.build_news` | Open (rate limited) |
| Written into code | FP Canada 2026 planning assumptions (`robokit/cma.py`), the policy anchor (`robokit/shelf.py`), crisis windows (`robokit/stress.py`), proxy tickers (`robokit/history.py`) | – | Own work |

"Personal use" means the source's terms allow fetching for your own non-commercial use but not redistribution.
That is why raw payloads stay out of git, why this repository is **private**, and why the artifact should be shared
only with the team (never by public link). A public product would need licensed data
(see `docs/research/gap-public-data-licensing.md`).

## What is in git and what is not

| Path | Tracked | What it is |
|---|---|---|
| `web/data/core.json`, `ca.json`, `us.json` | yes | The dated snapshot: eligible funds and proxies, monthly returns since 2000 (int16, 0.5 bp steps), questions, glossary, planning assumptions, rates, FX, stress windows, market flags, back-test summary, reference cases. Written by `python -m robokit bundle`. |
| `web/test_profiles.json` | yes | 400 self-check answer sets scored by Python; the browser engine must reproduce them (`web/test_robokit.mjs`). Written by the bundle step. |
| `output/v2/backtest_v2_summary.json` | yes | Pre-registered back-test results embedded in the snapshot (`scripts/run_backtest_v2.py`). |
| `data/universe.csv`, `data/etf_info_yf.csv` | yes | v1 inputs: the hand-curated 20-ETF shortlist and its fund facts (used by `scripts/run_prototype.py`, `run_robustness.py`, `try_it.py`). |
| `data/v2/` | no | Local cache from `refresh`: raw payloads (`raw/`), price chunks, pickles (`close_monthly.pkl`, `universe.pkl`, ...), logs, the `universe.csv` dictionary (see `docs/DATA.md`). About 110 MB. |
| `data/prices_daily_adjclose.csv` | no | v1 daily prices for the 20 ETFs. Recreate with `python scripts/run_prototype.py --refresh`. |

## Snapshot currently committed

| Field (`web/data/core.json` → `meta`) | Value |
|---|---|
| Prices through | 2026-08-31 (month-end; the unfinished month is dropped) |
| Listings and macro context fetched | 2026-09-28 |
| Universe | 7,957 listings; 636 Canadian and 1,997 US ETFs pass the eligibility rules |
| Data snapshot id | `00a560f4a6d3` (hash of the return panel) |

## Known limitations

- **Survivorship:** the universe is built from today's listings, and Yahoo has no prices for delisted funds.
- **Unofficial endpoints:** TMX GraphQL and Yahoo (`yfinance`) are unofficial and can change or rate-limit without
  notice. A per-ticker rate-limit error inside a successful chunk is not recorded, so a few funds can silently lose
  their history.
- **MER coverage:** MER comes only from Yahoo; coverage is good for eligible funds (594/636 CA, 1,966/1,997 US) but
  Yahoo is not an authoritative Canadian MER source.
- **News:** GDELT rate-limits aggressively; when a refresh gets nothing, the previous snapshot's headlines are kept
  and labelled with their fetch date.
- **Rebuild only on a machine with the local cache:** running `bundle` without `data/v2/` (snapshot mode) re-reads
  the snapshot itself and drops the newest month of interest rates. Always `refresh` first.
