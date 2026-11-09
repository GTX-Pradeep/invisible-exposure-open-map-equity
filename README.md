# Invisible Exposure

**Reference-free, conformal auditing of open-map completeness and the climate-hazard exposure it hides.**

For 9,794 census tracts in five U.S. climate-hazard regions, this repository predicts how many
buildings and points of interest (POIs) Overture Maps *should* contain from neutral structural facts
(housing stock, population, land area, jobs). It gives every tract a 90% conformal range, flags tracts
where the map falls below that range, and converts the shortfall into hidden heat, wildfire and
drought exposure. It then audits, under a frozen pre-registration, who lives in the flagged tracts and
whether three Overture snapshots (2023 → 2026) closed the gaps.

Design rule: vulnerability, rurality, tribal and hazard variables **never enter the model**. They are
joined only in the audit (`src/coverage_risk/model.py::assert_no_leakage`).

## Reproduce

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .
# LaTeX (texlive + latexmk) is needed only to build paper/main.pdf
# DuckDB needs the httpfs + spatial extensions (auto-installed; see src/coverage_risk/db.py)
bash scripts/run_all.sh          # downloads public data, runs Phases 1-8 (~1.5 h on 4 cores)
```

| Step | Script | Output |
|---|---|---|
| Data | `scripts/fetch_challenge.sh`, `00b_usa_structures_counts.py`, `00c_poi_reference.py` | `data/raw/`, reference tables |
| 1 | `01_count_overture.py --release r2026a / r2026b / r2023` | per-tract counts + provenance |
| 2 | `02_build_tract_table.py` | `tracts_all.parquet`, `strata_audit.parquet` (kept apart) |
| 3 | `03_expectation_model.py` | expected count, 90% range, flag, shortfall |
| 4 | `04_validation.py` | CV schemes, flag skill vs references, deletion test |
| gate | `docs/preregistration.md` | completed and frozen 2026-11-09 before Phases 5–7 (original template: `docs/preregistration_original_2026-10-16.md`) |
| 5 | `05_provenance.py` | H4 |
| 6 | `06_audit.py`, `06b_fdr.py`, `06c_robustness.py`, `06d_original_hypotheses.py` | H1, H2, H5, BH-FDR, robustness, original-template tests |
| 7 | `07_catchup.py` | H3 |
| expl. | `09_exploratory.py` | E1 release regression, E2 absorption, E3 H3 sensitivity (not pre-registered) |
| 8 | `08_figures.py`, `10_paper_numbers.py`, `paper/` | figures, generated numbers/tables, manuscript |

All settings are in `config/config.yaml`. Data versions and licences are in `docs/data_sources.md`.
`data/` is not tracked. Result tables, figures and the manuscript PDF are committed, and every number
in the paper regenerates from the scripts above (`paper/numbers.tex` is generated, not typed).

## Headline results (Overture 2026-08 unless stated)

* Conformal 90% ranges reach 90.0% held-out coverage for buildings and POIs under spatial-block
  cross-fitting, but 84.6% under leave-one-region-out; within-region (Mondrian) calibration restores per-region coverage
  when some local calibration data exist.
* Only 1.9% of tracts fall below 80% of USA Structures. Building flags have 5.1x lift over chance,
  and 50% feature loss is detected in 96% of tracts.
* 2023 to 2026: rural and tribal building gaps closed faster (rural gap rate -9.9 pp vs urban).
* Release `2026-09-23.0` and later dropped about 179,000 footprints in 186 tracts (Bexar County, TX).
  The reference-free model flags 82% of them.
* Hidden wildfire exposure is 4.8x higher (rural vs urban), and drought 2.9x.
* Tract-level flags miss systematic rural and tribal gaps (absorption plus resolution); see paper Sec. 5.6.

## Layout

```
config/config.yaml       settings (regions, releases, model, CV, conformal)
src/coverage_risk/       db.py, aggregate.py, features.py, provenance.py, model.py, validation.py, audit.py
scripts/                 one numbered script per phase
docs/                    preregistration.md, data_sources.md
outputs/tables/          result tables (CSV/JSON) used in the paper
paper/                   manuscript (LaTeX) and figures
notebooks/               course notebook (Invisible_Exposure.ipynb)
deliverables/            course deliverables: documentation, IEEE report, one-pager, slides, video script, dataset
```

## Licence

Code: MIT. Derived tables inherit the licences of their inputs (see `docs/data_sources.md`).
