"""Aggregate Overture and reference features to census tracts with DuckDB.

Everything is pushed down into DuckDB so national-scale parquet files never
need to fit in memory: we filter by the state's bounding box, then do a
point-in-polygon join of feature centroids against tract polygons.
"""

from __future__ import annotations

import duckdb
import geopandas as gpd


def connect(s3_region: str = "us-west-2") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"SET s3_region='{s3_region}';")
    return con


def register_tracts(con: duckdb.DuckDBPyConnection, tracts: gpd.GeoDataFrame) -> tuple:
    """Register tract polygons (EPSG:4326) as a DuckDB table; return bbox."""
    t = tracts.to_crs("EPSG:4326")[["GEOID", "geometry"]].copy()
    t["wkb"] = t.geometry.to_wkb()
    con.register("tracts_df", t.drop(columns="geometry"))
    con.execute(
        "CREATE OR REPLACE TABLE tracts AS "
        "SELECT GEOID, ST_GeomFromWKB(wkb) AS geom FROM tracts_df"
    )
    return tuple(t.total_bounds)  # xmin, ymin, xmax, ymax


def overture_buildings_by_tract(con, buildings_path: str, bbox: tuple):
    """Per tract: building count and count per primary source dataset.

    Overture stores provenance in `sources` (a list of structs with a
    `dataset` field). We take the first listed source as the primary one.
    """
    xmin, ymin, xmax, ymax = bbox
    return con.execute(
        f"""
        WITH b AS (
            SELECT
                ST_Centroid(geometry) AS pt,
                sources[1].dataset AS src
            FROM read_parquet('{buildings_path}', hive_partitioning=1)
            WHERE bbox.xmin BETWEEN {xmin} AND {xmax}
              AND bbox.ymin BETWEEN {ymin} AND {ymax}
        )
        SELECT t.GEOID, b.src, COUNT(*) AS n
        FROM b JOIN tracts t ON ST_Within(b.pt, t.geom)
        GROUP BY t.GEOID, b.src
        """
    ).df()


def overture_places_by_tract(con, places_path: str, bbox: tuple):
    """Per tract: POI count and count per primary source dataset."""
    xmin, ymin, xmax, ymax = bbox
    return con.execute(
        f"""
        WITH p AS (
            SELECT geometry AS pt, sources[1].dataset AS src
            FROM read_parquet('{places_path}', hive_partitioning=1)
            WHERE bbox.xmin BETWEEN {xmin} AND {xmax}
              AND bbox.ymin BETWEEN {ymin} AND {ymax}
        )
        SELECT t.GEOID, p.src, COUNT(*) AS n
        FROM p JOIN tracts t ON ST_Within(p.pt, t.geom)
        GROUP BY t.GEOID, p.src
        """
    ).df()


def reference_buildings_by_tract(con, ref_path: str, bbox: tuple, geom_col: str = "geometry"):
    """Per tract: count of reference (USA Structures) buildings.

    The reference file's geometry column name and encoding may differ;
    inspect it first with `DESCRIBE SELECT * FROM read_parquet(...)`.
    """
    xmin, ymin, xmax, ymax = bbox
    return con.execute(
        f"""
        WITH r AS (
            SELECT ST_Centroid({geom_col}) AS pt
            FROM read_parquet('{ref_path}')
        ),
        rb AS (
            SELECT pt FROM r
            WHERE ST_X(pt) BETWEEN {xmin} AND {xmax}
              AND ST_Y(pt) BETWEEN {ymin} AND {ymax}
        )
        SELECT t.GEOID, COUNT(*) AS n_ref_buildings
        FROM rb JOIN tracts t ON ST_Within(rb.pt, t.geom)
        GROUP BY t.GEOID
        """
    ).df()
