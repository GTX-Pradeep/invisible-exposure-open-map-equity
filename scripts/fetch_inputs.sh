#!/usr/bin/env bash
# Static public inputs: LODES 2022, Business Patterns 2023, ZCTA-tract relationship (ACS via features.fetch_acs).
# Cross-platform and idempotent: skips existing non-empty files and uses Python's built-in zipfile.
set -euo pipefail

mkdir -p data/raw/lodes data/raw/cbp
PY=$(command -v python3 || command -v python)

fetch() {
  local url="$1" out="$2"
  if [ -s "$out" ]; then
    echo "  exists: $out"
    return
  fi
  echo "  downloading $out"
  curl -sSfL --retry 3 -o "$out" "$url"
}

for st in az ca nm ok tx wa; do
  fetch "https://lehd.ces.census.gov/data/lodes/LODES8/$st/wac/${st}_wac_S000_JT00_2022.csv.gz" \
        "data/raw/lodes/${st}_wac_S000_JT00_2022.csv.gz"
done

fetch "https://www2.census.gov/programs-surveys/cbp/datasets/2023/zbp23totals.zip" "data/raw/cbp/zbp23totals.zip"
fetch "https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23co.zip"     "data/raw/cbp/cbp23co.zip"
fetch "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_tract20_natl.txt" \
      "data/raw/cbp/tab20_zcta520_tract20_natl.txt"

[ -s "data/raw/cbp/zbp23totals.txt" ] || "$PY" -m zipfile -e "data/raw/cbp/zbp23totals.zip" "data/raw/cbp"
[ -s "data/raw/cbp/cbp23co.txt" ]     || "$PY" -m zipfile -e "data/raw/cbp/cbp23co.zip"     "data/raw/cbp"
