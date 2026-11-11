#!/bin/bash
# Static public inputs: ACS (via features.fetch_acs), LODES, Business Patterns, ZCTA-tract relationship.
set -e
mkdir -p data/raw/lodes data/raw/cbp
for st in az ca nm ok tx wa; do curl -sSf -o data/raw/lodes/${st}_wac_S000_JT00_2022.csv.gz https://lehd.ces.census.gov/data/lodes/LODES8/$st/wac/${st}_wac_S000_JT00_2022.csv.gz; done
cd data/raw/cbp
curl -sSfO https://www2.census.gov/programs-surveys/cbp/datasets/2023/zbp23totals.zip && unzip -oq zbp23totals.zip
curl -sSfO https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23co.zip && unzip -oq cbp23co.zip
curl -sSfO https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_tract20_natl.txt
