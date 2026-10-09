# E7(e): fund labels against the issuers' own descriptions, and the swap gate

Registered in RESEARCH_LOG section 10 (E7(e)): "a sample of 30 satellite-only and 30 core-eligible funds labelled
from their prospectus category (agreement with our classification)". Done 9 Oct 2026, after the registered run and
outside the evaluation script. The sample found a defect; the fix was then tested on a second, held-out sample.

## Method

- **Sample.** Funds drawn at random (numpy `default_rng`, fixed seed) from the eligible universe: 30 labelled
  satellite-only and 30 core-eligible. The lists are in `docs/research/e7e_taxonomy_sample1.csv` and
  `e7e_taxonomy_sample2.csv` with our labels and the lane's labels side by side.
- **Blind labelling.** A research lane (Cursor, Composer model; a model family other than the author's) received only
  ticker, name and listing country, in shuffled order, never our labels. For each fund it recorded, from the
  issuer's own fund page, fact sheet or prospectus: asset class, region, whether a stock fund tracks a broad
  market-capitalisation-weighted index with no sector, style, size, factor, dividend, equal-weight, ESG-screen or
  thematic tilt, any options overlay, futures, leverage, active management, the URL and a verbatim quote. It was
  told to write INSUFFICIENT EVIDENCE rather than guess. All 140 funds were labelled from the issuer's own page.
- **Scoring** (mechanical, `scripts/e7e_taxonomy_compare.py`). The lane's labels imply a satellite status by the
  engine's own rule: crypto or alternative, an options overlay, futures, leverage, or a stock fund that is not a
  broad index fund. Agreement is counted per fund.

## Sample 1 (seed 20261009): the labels as evaluated

| Group | Satellite status agrees | Asset class agrees |
|---|---|---|
| Satellite-only (30) | 30 / 30 | 29 / 30 |
| Core-eligible (30) | 10 / 30 | 28 / 30 |

Every disagreement ran the same way: a fund we called core that its issuer describes as narrow. Of the 18 stock
funds labelled core-eligible, only one (BKIE) tracks a broad market-cap index. The others were sector funds (FTXH
pharmaceuticals, IYJ industrials, XMA.TO materials), single-country funds (EWQ, EWL), factor and fundamental-weight
funds (MCLC.TO, PXF, DUHP, RWEM), a high-dividend fund (SPYD), a buffer fund (MAYW), actively managed or concentrated
funds (JIRE, DINT, JPEF, INCE, GOP) and business development companies (PBDC).

**Cause.** A stock fund whose name matched no theme rule was labelled "Broad market" by default, and a fund whose
name matched a narrow theme and a broad one ("S&P/TSX Capped Materials") counted as broad. Some name rules also
missed plurals ("Pharmaceuticals", "Industrials", "Buffer20").

**Consequence.** The swap gate accepted any eligible fund that was not labelled satellite-only and had the same
asset class and region as the slot's fund. So, before the fix, a user could replace the S&P 500 fund with a sector
fund, a high-dividend fund, a buffer fund, or a single-country fund whose region the rules had labelled "US"
(TUR, THD, EIS, QAT and others: single foreign countries the region rules did not recognise), and the gold fund with
a silver fund. The reference shelf itself was not affected: it is picked by each slot's own name rule, which does
not read these labels.

## The fix

1. **The gate is the slot's own rule** (`shelf.slot_members`): a swap must be a fund the rule that picked the
   reference fund admits (hedged or not; hedging is the user's choice), not built on options or futures, and, when
   the reference fund is broad, not labelled narrow. Two independent filters (the slot's name rule and the label)
   must both admit the fund. The page offers only such funds as alternatives, in both engines.
2. **Broad needs positive evidence** (`universe.broad_equity`): a stock fund is broad only if its name names a
   whole-market index, it carries no narrower theme (sector, style, size, factor, dividend, single country, options),
   it is not actively managed and it covers a broad region. A name the rules cannot place is not broad. An ESG screen
   of a broad index stays broad, because the ESG shelf holds such funds by design.
3. Name rules take word stems (plurals and compounds), and new themes: single country, communication, sector, other
   factor (fundamental weight, profitability, multifactor, high beta, GARP), and active markers.

**What the fix cannot change.** The labels changed are theme, strategy, derivatives and satellite-only; region and
asset class were not touched, and no slot's rule reads the changed labels. Rebuilding the universe with the new code
changes no other column, and every slot's candidate list (both markets, standard and ESG shelves) is identical
(`scripts/e7e_universe_diff.py`). Every point-in-time pick that E2 makes (each December 2000-2025, both markets) is
accepted by the new gate, so the registered E2 result does not depend on it (test
`test_the_point_in_time_shelf_is_never_refused_by_the_gate`).

## Sample 2 (seed 20261010, held out): the fixed labels

Drawn after the rule was frozen, from funds not in sample 1: 30 satellite-only, 30 core-eligible, and 20 more
core-eligible stock funds (the label the fix changed).

| Group | Satellite status agrees |
|---|---|
| Satellite-only (30) | 29 / 30 |
| Core-eligible (30) | 23 / 30 |
| Core-eligible stock funds, extra (20) | 11 / 20 |

- **Stock funds labelled narrow:** 25 of 26 are narrow by the issuer's description. The exception is BBCA, a broad
  Canada index fund listed in the US, whose name names no index; no US slot holds Canadian stocks, so the label
  changes nothing it can be used for.
- **Stock funds labelled broad:** 15 of 30 meet the brief's strict definition. Of the other 15, ten are broad indexes
  with an ESG or values screen (EFIV, CVLC, XESG.TO, USCL, XSEM.TO, WSRD.TO, EMCS, CATH, OAEM, OALC), which the lane
  was told to count as narrow and the product counts as broad, and three are large-cap indexes (VONE, QUU.TO,
  QCE.TO), which the lane called narrow although the brief named the S&P 500, also a large-cap index, as broad.
  Under the product's definition, 26 of 30 are broad. The four misses are two factor-tilted funds (VIDI, DFAI) and
  two actively managed screened funds (OAEM, OALC).
- **Other funds labelled core:** one miss, COMB, a futures-based commodity fund.

## After the held-out check

Three changes were made after sample 2 and are tested by unit tests only, not by a further sample:
- a commodity fund that does not hold bullion is labelled futures-based unless its name says physical (COMB in
  sample 2, HGER in sample 1; 26 eligible funds change to satellite-only, among them GSG, DBA, BNO and CPER; no
  slot holds such a fund, so the shelf and the gate's answers for the slots are unchanged);
- "equity index" counts as a broad index name (seven funds, all broad index funds: QCN.TO, TTP.TO, TPU.TO, SITU.NE,
  SRIU.NE, WSHR.NE, USPX; found because the page offered two of them as alternatives that the gate refused);
- "Premium Money Market" is not an option-income fund (five cash funds; found because the gate refused CMR.TO,
  which E2 holds in 2011-2023);
- "Enhanced" alone and "Hedged Equity" no longer mark a fund as options-based (an examiner's finding, below): FDHY
  (an actively managed high-yield fund) and DBEM (a currency-hedged emerging-markets index fund) were refused by
  slots whose rules admit them.

## Examination of the change

One examiner from another model family (Cursor's Composer; the other examiners' usage limits were reached), briefed as
a professor of finance, quantitative methods and numerical mathematics, received the diff, the changed modules, the
tests and four claims (the gate's rule, positive evidence for "broad", no change to the evaluated results, offered
alternatives always accepted), without the authors' reasoning.

| Finding | Ruling | Reason |
|---|---|---|
| A bond fund named "Enhanced" or "Opportunity" is tagged options-based and refused by a slot whose rule admits it | Partly true; fixed | The example is wrong ("Opportunity" does not contain "option"), but the defect is real: the list of slot candidates the tag excluded showed FDHY ("Enhanced") and DBEM ("Hedged Equity"). Both tags were narrowed; tests in tests/test_v3_swap_gate.py |
| Open question: a slot with no reference fund applies no narrow-fund filter | True; fixed | No slot is empty today, but the gate now refuses every swap into a slot with no reference fund (fail closed); test added |
| Open question: should "large cap" and "equity index" count as broad evidence? | Answered | A large-cap index is the kind of index the S&P 500 is; narrower themes in the same name still override it (sample 2: VONE, QUU.TO, QCE.TO) |
| Open question: swap-based (total-return swap) index funds are admitted | Answered, disclosed | They hold the slot's index through a swap; the slot rules admit them and the README lists it |
| Open question: is a name rule plus a label a sound test of a substitute, rather than holdings? | Answered, disclosed | Holdings data cover only part of the universe (TMX look-through, Canadian funds); the name rules are audited (top five per slot, this sample), and residual errors are listed below |

Residual found while ruling: HEGD (an options-based "hedged equity" fund) is now labelled broad; no slot's rule
admits it, so it cannot be swapped in.

Found while testing the fix, not by the examiner: the Python engine wrote swap notes in the order of the request and
the browser engine in the slots' order. The old gate never refused two swaps in one request, so the parity suite never
saw it; the new gate does, and the parity case failed. Python now follows the slots' order (robokit/engine.py
select_funds), and the parity suite (web/test_robokit.mjs) passes.

## Not fixed (disclosed)

Labels that feed the slots' own rules (region and asset class) were not changed after the run, because the
evaluated shelf depends on them. Known errors:
- some single-country funds carry region "US" or "Global" (TUR, THD, EIS, QAT, ECH, EPHE, EPOL; ARGT and GREK through
  the issuer name "Global X"); their satellite label is now right, and the gate refuses them in the US slot;
- WGMI (bitcoin miners) is labelled Crypto, LVHD (low-volatility dividend stocks) Alternative, CORN (corn futures)
  Equity, NREA.TO (real-asset stocks) Fixed income, FCG (natural-gas producers) Commodity;
- a preferred-share fund (TPRF.TO) is labelled Fixed income and an ultra-short bond fund (EMNT) Cash, where the
  issuers describe preferred shares and a bond fund.

They are listed for the next registered evaluation, where the rules feeding the shelf may change.
