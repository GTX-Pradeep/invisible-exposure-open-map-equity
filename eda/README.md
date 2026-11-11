# Exploratory data analysis

Read the notebooks in order. 00-02 look at the **raw files** (after `scripts/fetch_data.ps1`); 03 checks how the pipeline
combines them into the **tract table**, and 04 explores that table. Every notebook ends each section with a written takeaway and saves its tables to
`tables/` and figures to `figures/`, prefixed with the notebook number.

Audit groups (SVI, CVI, rurality, tribal, hazards) appear only as coverage (00), never against an outcome, in line with
`docs/preregistration.md`. Challenge data are read from `data/raw/challenge` (the junctions made by `fetch_data.ps1`) or,
where a junction cannot be followed, from `../MapEquityChallenge/data`.

| Notebook | Build step | Question | Main findings |
|---|---|---|---|
| `00_raw_inventory.ipynb` | 1. Get the data | What is on disk, what is used, is every study tract in every source? | 4.5 GB of challenge extracts, 2.4 GB used; all 9,794 tracts present in every source; one tract is in New Mexico; USA Structures and the 2026-10/2023 releases still to stream |
| `01_raw_overture.ipynb` | 2. Understand the raw data | Overture buildings and places: IDs, sources, attributes, sizes, geometry, categories | No duplicate IDs, valid geometries; use class filled for only 6-37% of buildings; 6.6-13.2% of buildings under 450 sq ft, mostly Google/Esri; EMS listed 2.5x more often as an alternate-only category than as primary |
| `02_raw_census_inputs.ipynb` | 2. Understand the raw data | ACS, LODES, Business Patterns and the ZCTA allocation | ACS complete and internally consistent; 101 tracts mostly group quarters; LODES aggregates exactly; POI reference is one or two ZCTAs scaled by land area |
| `03_aggregation_and_table_checks.ipynb` | 3-4. Assign features to tracts, build the tract table | Is anything lost, double-counted or mis-joined? Does a fresh run reproduce the published table? | 3 of 19.2M buildings and 62 of 2.0M places unassigned, all explained (tract boundaries, excluded tracts); every schema check passes; all 111 columns reproduced exactly; USA Structures imagery is 2006-2021 |
| `04_tract_table_eda.ipynb` | 5. EDA of the tract table | The assembled table: skew, edge cases, sources, map vs reference, releases | Counts match an independent pipeline (98-99% identical); 2 all-water tracts; 1.9% of tracts below 80% of USA Structures; the 2026-10 drop shows in Texas totals |

Execute from the repo root:

```
jupyter nbconvert --to notebook --execute --inplace eda/0*.ipynb
```

`01_raw_overture.ipynb` takes about a minute (it scans all 19 million buildings with DuckDB and measures areas on a
60,000-building sample per region). The others take seconds.
