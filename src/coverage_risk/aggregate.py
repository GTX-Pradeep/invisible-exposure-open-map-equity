"""Count Overture buildings / POIs and their provenance per census tract with DuckDB.

Every feature is reduced to a representative point (bbox centre) and assigned to the
2020 census tract that contains it.  Footprint area is approximated from the planar
area in degrees scaled by cos(latitude) (error < 1% at tract scale); it is only used
to apply the 450 sq ft (41.8 m^2) threshold that matches the USA Structures reference.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from .db import connect, sql_list

M2_PER_DEG2 = 111_320.0**2
MIN_AREA_M2 = 41.8  # 450 sq ft, USA Structures inclusion threshold
CHALLENGE = Path("data/raw/challenge")


def load_tracts(regions: list[str]) -> gpd.GeoDataFrame:
    parts = []
    for r in regions:
        g = gpd.read_parquet(CHALLENGE / f"strata/{r}/{r}-census-tracts.parquet")
        sub = pd.read_csv(CHALLENGE / f"reference/{r}/{r}-sample-submission.csv", dtype={"GEOID": str})
        g = g[g.GEOID.isin(sub.GEOID)].copy()
        g["region"] = r
        parts.append(g[["GEOID", "region", "geometry"]])
    g = pd.concat(parts, ignore_index=True)
    return gpd.GeoDataFrame(g, geometry="geometry", crs=parts[0].crs).to_crs(4326)


def _register_tracts(con, tracts: gpd.GeoDataFrame) -> None:
    df = pd.DataFrame({"GEOID": tracts.GEOID, "wkb": tracts.geometry.to_wkb()})
    con.register("tracts_df", df)
    con.sql("CREATE OR REPLACE TABLE tracts AS SELECT GEOID, ST_GeomFromWKB(wkb) AS geom FROM tracts_df")


def bbox_filter(tracts: gpd.GeoDataFrame, xmin="bbox.xmin", xmax="bbox.xmax", ymin="bbox.ymin", ymax="bbox.ymax") -> str:
    """OR of per-region bounding boxes (row-group pruning)."""
    clauses = []
    for _, g in tracts.groupby("region"):
        x0, y0, x1, y1 = g.total_bounds
        clauses.append(f"({xmin} <= {x1} AND {xmax} >= {x0} AND {ymin} <= {y1} AND {ymax} >= {y0})")
    return "(" + " OR ".join(clauses) + ")"


def count_points(points_sql: str, tracts: gpd.GeoDataFrame, prefix: str, kind: str, con=None) -> pd.DataFrame:
    """points_sql must yield columns x, y, src (primary source dataset) and, for buildings, area_m2
    (plus optional n_src = number of source records and conf = confidence)."""
    con = con or connect()
    _register_tracts(con, tracts)
    con.sql(f"CREATE OR REPLACE TEMP TABLE pts AS {points_sql}")
    con.sql("""CREATE OR REPLACE TEMP TABLE pts_t AS
               SELECT t.GEOID, p.* FROM pts p JOIN tracts t ON ST_Contains(t.geom, ST_Point(p.x, p.y))""")
    if kind == "building":
        agg = f"""
          count(*) AS {prefix}_bldg,
          count(*) FILTER (WHERE area_m2 >= {MIN_AREA_M2}) AS {prefix}_bldg450,
          count(*) FILTER (WHERE src ILIKE '%OpenStreetMap%') AS {prefix}_src_osm,
          count(*) FILTER (WHERE src ILIKE '%Microsoft%')     AS {prefix}_src_msft,
          count(*) FILTER (WHERE src ILIKE '%Google%')        AS {prefix}_src_google,
          count(*) FILTER (WHERE src ILIKE '%Esri%')          AS {prefix}_src_esri,
          count(*) FILTER (WHERE src IS NULL OR NOT (src ILIKE '%OpenStreetMap%' OR src ILIKE '%Microsoft%' OR src ILIKE '%Google%' OR src ILIKE '%Esri%')) AS {prefix}_src_other,
          sum(area_m2) AS {prefix}_area_m2,
          median(area_m2) AS {prefix}_area_med
        """
    else:
        agg = f"""
          count(*) AS {prefix}_poi,
          count(*) FILTER (WHERE conf >= 0.5) AS {prefix}_poi_conf50,
          count(*) FILTER (WHERE src ILIKE '%meta%')       AS {prefix}_psrc_meta,
          count(*) FILTER (WHERE src ILIKE '%Microsoft%')  AS {prefix}_psrc_msft,
          count(*) FILTER (WHERE src ILIKE '%Foursquare%') AS {prefix}_psrc_fsq,
          count(*) FILTER (WHERE src ILIKE '%OpenStreetMap%') AS {prefix}_psrc_osm,
          count(*) FILTER (WHERE n_src >= 2) AS {prefix}_poi_multisrc
        """
    df = con.sql(f"SELECT GEOID, {agg} FROM pts_t GROUP BY GEOID").df()
    out = tracts[["GEOID"]].merge(df, on="GEOID", how="left")
    num = [c for c in out.columns if c != "GEOID"]
    zero_fill = [c for c in num if not c.endswith(("_area_med",))]
    out[zero_fill] = out[zero_fill].fillna(0)
    return out


# ---------------------------------------------------------------- source-specific point SQL
def area_expr(geom="geometry", lat="y") -> str:
    return f"ST_Area({geom}) * {M2_PER_DEG2} * cos(radians({lat}))"


def challenge_buildings_sql(regions: list[str]) -> str:
    files = sql_list([str(CHALLENGE / f"reference/{r}/{r}-overture-buildings.parquet") for r in regions])
    return f"""
      SELECT (bbox.xmin + bbox.xmax)/2 AS x, (bbox.ymin + bbox.ymax)/2 AS y,
             ST_Area(geometry) * {M2_PER_DEG2} * cos(radians((bbox.ymin + bbox.ymax)/2)) AS area_m2,
             sources[1].dataset AS src, len(sources) AS n_src
      FROM read_parquet({files})"""


def challenge_pois_sql(regions: list[str]) -> str:
    files = sql_list([str(CHALLENGE / f"reference/{r}/{r}-overture-pois.parquet") for r in regions])
    return f"""
      SELECT ST_X(geometry) AS x, ST_Y(geometry) AS y, confidence AS conf,
             sources[1].dataset AS src, len(sources) AS n_src
      FROM read_parquet({files})"""


def s3_buildings_sql(path: str, tracts) -> str:
    return f"""
      SELECT (bbox.xmin + bbox.xmax)/2 AS x, (bbox.ymin + bbox.ymax)/2 AS y,
             ST_Area(geometry) * {M2_PER_DEG2} * cos(radians((bbox.ymin + bbox.ymax)/2)) AS area_m2,
             sources[1].dataset AS src, len(sources) AS n_src
      FROM read_parquet('{path}')
      WHERE {bbox_filter(tracts)}"""


def s3_places_sql(path: str, tracts) -> str:
    return f"""
      SELECT (bbox.xmin + bbox.xmax)/2 AS x, (bbox.ymin + bbox.ymax)/2 AS y, confidence AS conf,
             sources[1].dataset AS src, len(sources) AS n_src
      FROM read_parquet('{path}')
      WHERE {bbox_filter(tracts)}"""


def legacy2023_buildings_sql(urls: list[str], tracts) -> str:
    """Overture 2023-07-26-alpha (cholmes GeoParquet copy): sources is a list of key/value maps."""
    src = "list_filter(sources.list[1].key_value, lambda kv: kv.key = 'dataset')[1].value"
    return f"""
      SELECT (bbox.minx + bbox.maxx)/2 AS x, (bbox.miny + bbox.maxy)/2 AS y,
             ST_Area(geometry) * {M2_PER_DEG2} * cos(radians((bbox.miny + bbox.maxy)/2)) AS area_m2,
             {src} AS src, len(sources.list) AS n_src
      FROM read_parquet({sql_list(urls)})
      WHERE {bbox_filter(tracts, 'bbox.minx', 'bbox.maxx', 'bbox.miny', 'bbox.maxy')}"""
