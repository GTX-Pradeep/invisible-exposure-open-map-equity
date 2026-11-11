#!/bin/bash
set -e
export PYTHONPATH=src
mkdir -p data/raw/challenge data/processed outputs/tables outputs/figures
bash scripts/fetch_challenge.sh
bash scripts/fetch_inputs.sh
python -c "from coverage_risk.features import fetch_acs; fetch_acs()"
python scripts/00b_usa_structures_counts.py
python scripts/00c_poi_reference.py
for r in r2026a r2026b; do python scripts/01_count_overture.py --release $r; done
python scripts/01_count_overture.py --release r2023 --layer buildings
python scripts/02_build_tract_table.py
python scripts/13_data_dictionary.py   # docs/data_dictionary.md from the tract table
python scripts/03_expectation_model.py
python scripts/04_validation.py
python scripts/05_provenance.py
python scripts/06_audit.py
python scripts/07_catchup.py
python scripts/06b_fdr.py
python scripts/09_exploratory.py
# Optional: re-import companion data (needs ../MapEquityChallenge); the imported copies are committed under data/external/
if [ -d ../MapEquityChallenge ]; then python scripts/11a_import_merged.py; python scripts/11b_import_companion.py; fi
python scripts/11_merged_exploratory.py --part all
python scripts/06d_original_hypotheses.py
python scripts/06c_robustness.py
python scripts/08_figures.py
python scripts/10_paper_numbers.py
python scripts/12_merged_numbers.py
python scripts/14_reference_validation.py
(cd paper && latexmk -pdf -interaction=nonstopmode main.tex)
