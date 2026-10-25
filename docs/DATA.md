# Data: sources, dictionary, refresh, licences

Snapshot in this repo: prices through 31 Aug 2026, listings and context fetched 28 Sep 2026. Rebuild everything on your own machine with `python -m robokit refresh`, then `python -m robokit bundle` for the web page. Everything under `data/v2/` is a local cache and is not in git; only the `web/data/` snapshot and the archived data of record in `data/replication/` are committed (see `data/README.md`).

## Files

| File | What it holds |
| --- | --- |
| `data/v2/raw/` | Raw payloads with fetch times: Nasdaq Trader files, TMX JSON, Yahoo screener CSVs, category maps, GPR and EPU spreadsheets, price chunks |
| `data/v2/universe.csv` (`.pkl`) | One row per listing with classification, statistics, eligibility and reasons (dictionary below) |
| `data/v2/close_monthly.pkl`, `volume_monthly.pkl` | Month-end adjusted close and volume, 7,792 series |
| `data/v2/usdcad_monthly.pkl` | CAD per USD, month end |
| `data/v2/context_monthly.pkl`, `context_meta.json` | Macro, geopolitics, policy uncertainty; per-source status |
| `data/v2/news.pkl` | GDELT tone, volume and headlines per topic |
| `web/data/core.json`, `ca.json`, `us.json` | The web bundle (returns as int16 in 0.5 bp units, 2000 onward) |

## `universe.csv` dictionary

| Column | Meaning |
| --- | --- |
| `yahoo`, `symbol`, `name`, `market`, `exchange`, `currency` | Identity. `market` CA = Canadian listing, US = US listing. `currency` is the trading currency. |
| `asset_class` | Equity, Fixed income, Cash, Real estate, Commodity, Multi-asset, Alternative, Crypto, Single stock |
| `region` | Canada, US, North America, International developed, Emerging markets, Global, Europe, Asia-Pacific, Japan, China |
| `theme`, `sector` | Name-based themes (several may apply); dominant look-through sector if 60% or more |
| `leverage`, `inverse` | Signed daily multiple (1 = none); inverse flag |
| `single_stock`, `cdr` | Built on one company; Canadian Depositary Receipt |
| `derivatives`, `strategy` | Options, futures, swaps; market-cap index, factor index, active, options-based, leveraged |
| `hedged`, `esg`, `crypto`, `target_date` | Flags |
| `issuer` | From the fund name or Yahoo fund family |
| `mer` | Net expense ratio as a fraction (0.0009 = 0.09%) |
| `aum` | Net assets in the trading currency |
| `inception`, `first_month`, `history_months` | Age of the fund and its usable monthly history |
| `vol_3y`, `vol_5y`, `ret_1y`, `ret_3y`, `ret_5y`, `ret_10y`, `max_drawdown` | From month-end total returns; annualised |
| `dollar_volume` | Average daily traded value, last 6 months (approximate) |
| `dividend_yield`, `pe`, `pb` | From Yahoo and TMX where published |
| `why` | Which classification rules fired |
| `eligible`, `excluded_because` | Optimizer eligibility and the plain-language reason when not eligible |
| `satellite_only` | Eligible but narrow or complex: crypto, alternatives, option-overlay and futures-based funds, and every stock fund that is not a broad index fund (broad needs a whole-market index name and no narrower theme; `robokit.universe.broad_equity`). Held as a capped own pick; it can stand in a core slot only if the slot's reference fund is itself narrow and the slot's rule admits it (`robokit.shelf.slot_members`) |

## Suppliers and failure modes (model governance)

| Supplier | Used for | If it fails |
| --- | --- | --- |
| Nasdaq Trader | US listing universe | Refresh stops at the listing step; the previous snapshot stays in use |
| TMX Money | Canadian listing and metadata | Yahoo still lists TSX and Cboe Canada funds; TMX-only fields go missing |
| Yahoo Finance (via yfinance) | Prices, fees, size, categories, US rates, VIX, FX | Chunks retry; failed chunks are listed in `prices_manifest_universe.json`. `scripts/v2_fetch_prices.py` resumes an interrupted download (`python -m robokit refresh` starts the price step fresh) |
| Bank of Canada Valet | Canadian rates and CPI | Risk-free rate falls back to the constant in `robokit/config.py`, and results say so |
| FRED | High-yield spread (best effort) | Flag shown as unavailable |
| Caldara-Iacoviello, Baker-Bloom-Davis | GPR and EPU | Flag shown as unavailable |
| GDELT | News | News card says it was not available at the last refresh |
| Anthropic (Claude) | Conversation only, never numbers | The page works without it; the MCP and CLI paths use the user's own account |

## Licences

| Tier | Sources | Allowed use |
| --- | --- | --- |
| Redistributable with attribution | Bank of Canada, Statistics Canada, SEC EDGAR, GDELT, GPR (CC BY), EPU (CC BY 4.0), public-domain FRED series | May be bundled |
| Conditions apply | Copyrighted FRED series (ICE spreads, VIX), Loughran-McDonald lexicon | Fetch locally; not bundled for public use |
| Personal or non-commercial only | Yahoo / yfinance, TMX Money, Nasdaq Trader, Cboe Canada web API | Fetch on the user's own machine; a public product needs a paid licence |

Details and quotes from each provider's terms: `docs/research/data-sources.md`.
