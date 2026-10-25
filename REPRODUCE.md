# Reproducing our results

Every number in our reports can be recomputed from this repository, offline, and checked automatically against what
we published. The data the numbers came from is committed (`data/replication/`, 4.3 MB), so nothing is downloaded
and nothing depends on today's market prices.

| What | Command | Time | What you should see |
|---|---|---|---|
| The optimizer tables of both reports | `python scripts/replicate.py tables` | 2 minutes | every printed value matches |
| The data snapshot behind the web page | `python scripts/replicate.py snapshot` | 5 minutes | about 320,000 values identical |
| The registered evaluation, quick part | `python scripts/replicate.py evaluation` | a few minutes | 60 statistics and 3 monthly paths identical |
| The registered evaluation, in full | `python scripts/replicate.py evaluation --full` | hours | every value in `output/v3/results.json` |
| The test suite on the full data | `python scripts/replicate.py data`, then `python -m pytest -q` | 20 minutes | 662 passed |

Each command prints `PASS` or `FAIL` for every check and ends with "All checks passed." The same checks run on Linux
in GitHub Actions on every push (the "Reproduce" job in [.github/workflows/ci.yml](.github/workflows/ci.yml)).

## 0. Set up

You need git and Python 3.10 or newer (we test 3.10 and 3.12).

```bash
git clone https://github.com/dylanguo1129/ai-robo-advisor.git
cd ai-robo-advisor
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt && pip install -e . --no-deps
```

`requirements.txt` pins the numerical libraries the registered evaluation ran with (NumPy 2.2.6, pandas 2.3.3,
SciPy 1.15.3). Use a full clone: not `--depth 1` and not GitHub's "Download ZIP", because step 3 checks out the commit
the evaluation ran on. (With a ZIP, download that commit's code as well, as the script explains, and pass it with
`--code`.)

## 1. The optimizer tables

```bash
python scripts/replicate.py tables
```

This rebuilds the Canadian portfolios at levels 1 to 5 on the 10 default ETFs and checks them against the tables as
printed in the optimizer report (*Robo-Kit Portfolio Optimizer*, Tables 1, 4 and 7) and the team report (Tables A1,
A2 and A7): weights, λ, volatility targets and reached volatility, the asset mix, the typical and bad year, the 2008
replay, fees and the risk rating, 99 values in all. The expected values are in
[data/replication/report_tables.json](data/replication/report_tables.json).

It runs twice:

- **On the archived data** (what the reports were computed from): all 99 values match exactly.
- **On the committed web snapshot** (what a fresh clone, the command line and the web page use): the snapshot stores
  each monthly return to the nearest half basis point, as 16-bit integers, to fit the web page's size limit. Up to 16
  fund weights then differ from the printed table by 0.01 or 0.02 percentage points. Every λ, volatility, target and
  outcome still matches.

How the optimizer arrives at these numbers is explained in [optimizer/README.md](optimizer/README.md).

## 2. The data snapshot behind the web page

```bash
python scripts/replicate.py snapshot
```

This rebuilds `web/data/` (the snapshot the web page, the command line and the MCP server use) from the archived data
in a temporary folder, then compares it with the committed files. `ca.json`, `us.json` and `test_profiles.json` come
out byte for byte; `core.json` differs only in its build time. Your working copy is not changed.

## 3. The registered evaluation

The evidence in our reports (Section 6 of the optimizer report, Sections 5 and 6 of the paper) comes from one
pre-registered run of `scripts/run_v3_evaluation.py`: commit `ea426ad`, data snapshot `00a560f4a6d3`, 500 simulated
histories, results in [output/v3/results.json](output/v3/results.json) and monthly paths in `output/v3/*.csv`. The
code has changed since (for example, the projections now use 5,000 paths and one benchmark's yardstick was
corrected), so the replication runs **the registered commit's own code** on the archived data:

```bash
python scripts/replicate.py evaluation          # quick: a few minutes
python scripts/replicate.py evaluation --full   # the whole evaluation: hours
```

The script checks out commit `ea426ad` in a temporary git worktree and deletes it afterwards (`--keep` keeps it).

- **Quick** re-runs the confirmatory walk-forward for Canada (E1, January 2010 to August 2026) for Robo-Kit at the
  brief's three settings (levels 2, 3 and 4). It compares the 60 statistics in `results.json` and the three monthly
  return paths, which must be identical. `--workers N` sets the number of processes; the result does not depend on it.
- **Full** runs the whole registered script: the simulations (E3), the walk-forward tests in both markets (E1, E2) and
  the other stages (E4 to E8). It then compares every value of `results.json` (apart from its provenance block: time,
  run length, worker count) and every monthly path file. The registered run took 2 hours 19 minutes on 28 worker
  processes; on a laptop expect most of a day.

On October 25, 2026 we ran both on a clean checkout. The quick part matched value for value. The full run's
result is recorded in [docs/VERIFICATION.md](docs/VERIFICATION.md) (section 8.14).

The paper's numbers are filled in from `results.json`: after `python scripts/replicate.py data` (step 4),
`python scripts/paper/derive.py` writes every number the paper places to `docs/paper/build/paper_numbers.json` (a folder
git ignores), checking that the data is the snapshot the run used.

## 4. The test suite

```bash
python -m pytest -q                    # a fresh clone: 575 pass, 87 skipped (they need the full data)
python scripts/replicate.py data       # unpack the archived data into data/v2/ (git-ignored)
python -m pytest -q                    # now 662 pass
python -m pytest -m ui -q tests/ui     # optional: the 143 browser tests (needs: python -m playwright install chromium)
node web/test_robokit.mjs              # optional: the web page's engine reproduces Python (needs Node 18+)
```

After `replicate.py data`, the command line and the MCP server also use the full-precision data (`python -m robokit
status` reports `local` and `00a560f4a6d3`).

## What "the same" means

- **Same inputs.** The archive and every file in it are checked against SHA-256 hashes in
  [data/replication/MANIFEST.json](data/replication/MANIFEST.json) before anything runs.
- **Same randomness.** All random numbers come from fixed seeds: portfolio resampling seed 0, projections seed 7,
  stand-in back-fill seed 11, the evaluation's simulated histories `[20261008, world, replication]`.
- **Same results.** On the same libraries the results are identical, not just close. Numbers are compared with a
  tolerance of one part in a billion, in case another operating system rounds the last bits of a float differently;
  the checks report how many values were identical.
- **What may differ:** the time stamps (the snapshot's build time, the evaluation's run times) and, for the full
  evaluation, its provenance (commit, start time, worker count).
- **What will not reproduce:** `python -m robokit refresh` (or `make data`) downloads today's prices, which changes every
  number by design. Do not run it if you want to reproduce our results; if you did, `python scripts/replicate.py data
  --force` puts the archived data back.

## What is in `data/replication/`

| File | Contents |
|---|---|
| `robokit-data-00a560f4a6d3.tar.xz` | The data snapshot every published number came from (prices through August 31, 2026), unpacked by `replicate.py` |
| `MANIFEST.json` | SHA-256 of the archive and of each file, and what each file is |
| `report_tables.json` | The optimizer tables as printed in our reports |

The prices and fund data were fetched from public sources (Yahoo Finance, TMX, Nasdaq Trader, the Bank of Canada,
FRED, the GPR and EPU indices, GDELT) whose terms cover personal, non-commercial use; they are included so that a
reader can check our results. See [data/README.md](data/README.md).
