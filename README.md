# Invisible Exposure: Open-Map Equity

**Uncertainty-aware estimation of open-map coverage gaps and their consequences for climate-risk assessment in vulnerable U.S. communities.**

Open maps such as Overture Maps are incomplete in uneven ways. Raw sparsity cannot tell genuinely empty land apart from places nobody has mapped. This project estimates *expected* map content per census tract from neutral structural variables, flags tracts where the observed map falls clearly below an uncertainty-aware expectation, translates those gaps into hidden climate-hazard exposure, and audits whether the gaps concentrate in socially and climate-vulnerable communities.

## Research questions

1. Can we estimate where open maps are incomplete, with honest uncertainty, without a perfect reference map?
2. How much wildfire, heat and drought exposure is missing from the map, and does it fall disproportionately on socially vulnerable, rural and tribal communities?
3. As Overture improves across releases, do vulnerable communities catch up?
4. Does dependence on a single data source predict where gaps are?

Hypotheses are pre-registered in [`docs/preregistration.md`](docs/preregistration.md).

## Method in brief

| Step | What | Where |
|---|---|---|
| 1 | Aggregate Overture buildings/POIs and source metadata to census tracts | `src/coverage_risk/aggregate.py` |
| 2 | Join ACS structural covariates (area, housing units, units-in-structure, population) | `src/coverage_risk/features.py` |
| 3 | Expectation model (structural variables only) + conformal intervals | `src/coverage_risk/model.py` |
| 4 | Random vs. spatial-block vs. leave-one-region-out validation | `src/coverage_risk/validation.py` |
| 5 | Provenance features (source count, entropy, single-source dependence) | `src/coverage_risk/provenance.py` |
| 6 | External validation against FEMA/ORNL USA Structures, Census CBP | `scripts/` |
| 7 | Hidden exposure + pre-registered equity audit | `src/coverage_risk/audit.py` |

**Design rule:** rurality, tribal status, SVI, CVI and hazard variables are **never** inputs to the expectation model. They are used only in the audit, so systematic disparities are not learned as "normal".

## Repository layout

```
config/       study settings (states, Overture release, paths)
data/raw/     downloaded inputs (git-ignored)
data/processed/  tract-level tables (git-ignored)
docs/         pre-registration, data sources, notes
notebooks/    exploration
outputs/      figures and tables
scripts/      runnable pipeline steps
src/coverage_risk/  reusable package code
```

## Setup

```bash
git clone https://github.com/<your-username>/invisible-exposure-open-map-equity.git
cd invisible-exposure-open-map-equity
```

Works on Linux, macOS, or Windows (WSL2 recommended on Windows). 16 GB RAM or more is recommended.

```bash
conda env create -f environment.yml
conda activate invisible-exposure
pip install -e .
```

## Quick start: feasibility check (one state)

```bash
python scripts/01_feasibility_check.py --state AZ
```

This counts Overture buildings, source mix and USA Structures buildings per tract for one state, joins ACS housing units, and writes `data/processed/feasibility_<STATE>.parquet` plus a comparison plot in `outputs/figures/`.

## Data

See [`docs/data_sources.md`](docs/data_sources.md) for every source, its license and the exact release used. Pin the Overture release in `config/config.yaml` so results are reproducible.

## License

Code: MIT (see `LICENSE`). Data retain their original licenses; Overture themes carry different licenses (some ODbL), so check attribution requirements before redistributing derived data.
