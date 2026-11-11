# Data: what to download, from where, and in what order

Everything is public. About **6 GB is already on your disk** in `MapEquityChallenge/data/`; the rest is either a small
download or streamed from the cloud by the scripts. All URLs below are the ones the repo's own scripts use
(`scripts/fetch_challenge.sh`, `scripts/fetch_inputs.sh`, `coverage_risk.features.fetch_acs`, `scripts/00b`, `scripts/01`).

## Do this first (time-sensitive)

Overture deletes old releases from its S3 bucket after about 60 days. The **2026-10-21.0** release, used for the
catch-up (H3) and the San Antonio regression (E1, N1), will likely disappear in **late December 2026**.
Run step 4 (`01_count_overture.py --release r2026b`) well before that and keep `data/processed/` afterwards.

## Overview

| # | Dataset | Version | Used for | How you get it | Goes to |
|---|---|---|---|---|---|
| 1 | Bias Bounty challenge extracts: Overture buildings + places per region, sample submissions | Overture `2026-08-19.0` | map under audit (primary release) | **already local** (`MapEquityChallenge/data/reference`, 4.3 GB) | `data/raw/challenge/reference/` |
| 2 | Challenge strata: tract polygons, national census-tract table, strata table (SVI, CVI, RUCA, tribal, heat, wildfire, drought) | 2020 tracts | tract geometry, land area, audit groups | **already local** (`MapEquityChallenge/data/strata`, 1.6 GB) | `data/raw/challenge/strata/` |
| 3 | ACS 5-year Table-Based Summary File, tables B25001, B25002, B25024, B01003, B25034, B11001, B26001 | 2020-2024 | model inputs (housing, population, units in structure, year built, group quarters) | download (script) | `data/raw/acs/` |
| 4 | LEHD LODES 8 Workplace Area Characteristics, all jobs (S000/JT00), 6 states: az, ca, nm, ok, tx, wa | 2022 | model inputs (jobs by sector) | download | `data/raw/lodes/` |
| 5 | ZIP Business Patterns totals (`zbp23totals.zip`) | 2023 | POI reference (validation only) | download | `data/raw/cbp/` |
| 6 | County Business Patterns (`cbp23co.zip`) | 2023 | county POI reference (validation only) | download | `data/raw/cbp/` |
| 7 | ZCTA-to-tract relationship file (`tab20_zcta520_tract20_natl.txt`) | 2020 | allocate ZIP establishments to tracts | download | `data/raw/cbp/` |
| 8 | FEMA/ORNL USA Structures | v1 (GeoParquet mirror on Source Cooperative) | building reference (validation only) | **streamed** by `scripts/00b_usa_structures_counts.py` (only the 6 study states) | `data/processed/usa_structures_tract.parquet` |
| 9 | Overture buildings + places | `2026-10-21.0` | later snapshot (H3, E1) | **streamed** from `s3://overturemaps-us-west-2/release/2026-10-21.0/` by `scripts/01_count_overture.py --release r2026b` | `data/processed/` |
| 10 | Overture buildings (archived alpha, GeoParquet copy) | `2023-07-26-alpha.0` | earlier snapshot (H3) | **streamed** from `data.source.coop/cholmes/overture/geoparquet-country-quad-hive/country_iso=US/` by `01_count_overture.py --release r2023` | `data/processed/` |

Download links for 3-7:

* ACS: `https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-<table>.dat`
  (e.g. `acsdt5y2024-b25001.dat`). The script downloads each national file, keeps tract rows, saves a small parquet and deletes the `.dat`.
* LODES: `https://lehd.ces.census.gov/data/lodes/LODES8/<st>/wac/<st>_wac_S000_JT00_2022.csv.gz`
  for `<st>` in az, ca, nm, ok, tx, wa (nm because one study tract crosses into New Mexico).
* ZIP BP: `https://www2.census.gov/programs-surveys/cbp/datasets/2023/zbp23totals.zip` (unzip to `zbp23totals.txt`)
* County BP: `https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23co.zip` (unzip to `cbp23co.txt`)
* ZCTA-tract: `https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_tract20_natl.txt`

The two Business Patterns zips and the relationship file are the largest downloads; the ACS `.dat` files are national
and a few hundred MB each before the script reduces them. Licences and the independence check are in `docs/data_sources.md`.

## Quickest way: one script

```powershell
cd "C:\Users\prajw\OneDrive\Documents\5 sem\ada\invisible-exposure-open-map-equity"
powershell -ExecutionPolicy Bypass -File scripts\fetch_data.ps1            # links + small downloads + ACS
powershell -ExecutionPolicy Bypass -File scripts\fetch_data.ps1 -Stream    # also USA Structures and Overture counts
```

It does steps 0-4 below, skips anything already downloaded, and writes `data/raw/MANIFEST.csv` (size, SHA-256, date).

## Step by step on Windows (PowerShell)

Run from the repo folder: `cd "C:\Users\prajw\OneDrive\Documents\5 sem\ada\invisible-exposure-open-map-equity"`.

**0. Python environment** (once)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:PYTHONPATH = "src"
```

**1. Reuse the challenge data you already have** (no 6 GB copy; a junction is a link, so OneDrive does not sync it twice)

```powershell
mkdir data\raw\challenge -Force
cmd /c mklink /J "data\raw\challenge\reference" "..\MapEquityChallenge\data\reference"
cmd /c mklink /J "data\raw\challenge\strata"    "..\MapEquityChallenge\data\strata"
```

Skip `scripts/fetch_challenge.sh`; it would download the same files again.

**2. Small downloads** (replaces `scripts/fetch_inputs.sh`, which needs Git Bash)

```powershell
mkdir data\raw\lodes, data\raw\cbp -Force
foreach ($st in "az","ca","nm","ok","tx","wa") {
  curl.exe -sSfL -o "data\raw\lodes\$($st)_wac_S000_JT00_2022.csv.gz" "https://lehd.ces.census.gov/data/lodes/LODES8/$st/wac/$($st)_wac_S000_JT00_2022.csv.gz"
}
curl.exe -sSfL -o data\raw\cbp\zbp23totals.zip https://www2.census.gov/programs-surveys/cbp/datasets/2023/zbp23totals.zip
curl.exe -sSfL -o data\raw\cbp\cbp23co.zip     https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23co.zip
curl.exe -sSfL -o data\raw\cbp\tab20_zcta520_tract20_natl.txt https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_tract20_natl.txt
Expand-Archive data\raw\cbp\zbp23totals.zip -DestinationPath data\raw\cbp -Force
Expand-Archive data\raw\cbp\cbp23co.zip     -DestinationPath data\raw\cbp -Force
.\.venv\Scripts\python.exe -c "from coverage_risk.features import fetch_acs; fetch_acs()"
```

**3. References** (USA Structures is streamed; Business Patterns read from step 2)

```powershell
.\.venv\Scripts\python.exe scripts\00b_usa_structures_counts.py
.\.venv\Scripts\python.exe scripts\00c_poi_reference.py
```

**4. Count Overture per tract** (r2026a reads the local challenge files; r2026b and r2023 stream from the cloud)

```powershell
.\.venv\Scripts\python.exe scripts\01_count_overture.py --release r2026a
.\.venv\Scripts\python.exe scripts\01_count_overture.py --release r2026b
.\.venv\Scripts\python.exe scripts\01_count_overture.py --release r2023 --layer buildings
```

**5. The rest of the pipeline** (the same order as `scripts/run_all.sh`)

```powershell
foreach ($s in "02_build_tract_table","03_expectation_model","04_validation","05_provenance","06_audit","07_catchup",
               "06b_fdr","09_exploratory","11a_import_merged","11_merged_exploratory","06d_original_hypotheses","06c_robustness","08_figures",
               "10_paper_numbers","12_merged_numbers") {
  .\.venv\Scripts\python.exe "scripts\$s.py"; if ($LASTEXITCODE) { throw "$s failed" }
}
```

`11a` needs
`..\MapEquityChallenge` next to this folder (it is). DuckDB installs its `httpfs` and `spatial` extensions on first use,
so steps 3-4 need internet.

## Before a full rerun

* **Commit first.** A rerun rewrites `paper/numbers.tex` and the frozen result tables. Committing lets you diff the new
  numbers against the published ones; small changes (library versions, a re-streamed reference) are possible.
* The tract-table EDA (`eda/04_tract_table_eda.ipynb`) and N1-N5 need **none** of these downloads: they read the released tract
  tables in `deliverables/dataset/` and `data/external/merged_inputs.csv`.
