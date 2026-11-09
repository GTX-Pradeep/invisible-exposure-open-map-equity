"""Reference: USA Structures (FEMA/ORNL) building counts per 2020 census tract.

Uses the CENSUSCODE (15-digit block GEOID) column, so no spatial join is needed.
Validation-only: never enters the expectation model.
"""
import time
from pathlib import Path
import yaml
from coverage_risk.db import connect, source_coop_files, sql_list

cfg = yaml.safe_load(open("config/config.yaml"))
out = Path("data/processed/usa_structures_tract.parquet")
states = ",".join(f"'{s}'" for s in cfg["state_fips"])
con = connect()
files = sql_list(source_coop_files('wherobots', 'usa-structures/geoparquet/'))
t = time.time()
con.sql(f"""
COPY (
  SELECT substr(CENSUSCODE,1,11) AS GEOID,
         count(*)                                         AS ref_bldg,
         count(*) FILTER (WHERE OCC_CLS='Residential')    AS ref_res,
         count(*) FILTER (WHERE OCC_CLS IN ('Commercial','Industrial','Assembly','Education','Government')) AS ref_nonres,
         count(*) FILTER (WHERE OUTBLDG IS NOT NULL AND OUTBLDG NOT IN ('', '0', 'N'))  AS ref_outbldg,
         sum(SQMETERS)                                    AS ref_area_m2,
         min(IMAGE_DATE) AS ref_img_min, max(IMAGE_DATE) AS ref_img_max
  FROM read_parquet({files})
  WHERE substr(CENSUSCODE,1,2) IN ({states})
  GROUP BY 1
) TO '{out}' (FORMAT parquet)
""")
print(con.sql(f"SELECT substr(GEOID,1,2) st, count(*) tracts, sum(ref_bldg) bldg FROM '{out}' GROUP BY 1 ORDER BY 1").df())
print(f"{time.time()-t:.0f}s")
