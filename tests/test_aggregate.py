"""Tract assignment (coverage_risk.aggregate.count_points) on a tiny hand-made map.

Two unit-square tracts side by side, A = [0,1]x[0,1] and B = [1,2]x[0,1]. Needs DuckDB's spatial extension;
skipped when it cannot be loaded (offline machine without the extension)."""
import duckdb
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from coverage_risk.aggregate import MIN_AREA_M2, count_points


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    for attempt in ("LOAD spatial", "INSTALL spatial"):
        try:
            c.sql(attempt)
            if attempt.startswith("INSTALL"):
                c.sql("LOAD spatial")
            return c
        except Exception:
            continue
    pytest.skip("DuckDB spatial extension not available")


@pytest.fixture
def tracts():
    return gpd.GeoDataFrame({"GEOID": ["00000000001", "00000000002"], "region": ["r", "r"]},
                            geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)], crs=4326)


def pts_sql(rows):
    vals = ", ".join(f"({x}, {y}, {a}, '{s}')" for x, y, a, s in rows)
    return f"SELECT * FROM (VALUES {vals}) t(x, y, area_m2, src)"


def test_points_inside_are_counted_once(con, tracts):
    rows = [(0.5, 0.5, 100, "OpenStreetMap"), (0.2, 0.8, 100, "Microsoft ML Buildings"), (1.5, 0.5, 100, "Esri Community Maps")]
    out = count_points(pts_sql(rows), tracts, "t", "building", con=con).set_index("GEOID")
    assert out.loc["00000000001", "t_bldg"] == 2 and out.loc["00000000002", "t_bldg"] == 1
    assert out.t_bldg.sum() == len(rows)                       # nothing counted twice


def test_outside_and_boundary_points_are_not_counted(con, tracts):
    # (3, 0.5) is outside both tracts; (1, 0.5) lies exactly on the shared edge: ST_Contains counts it in neither,
    # so a feature on a boundary is dropped, never double-counted.
    rows = [(0.5, 0.5, 100, "OpenStreetMap"), (3.0, 0.5, 100, "OpenStreetMap"), (1.0, 0.5, 100, "OpenStreetMap")]
    out = count_points(pts_sql(rows), tracts, "t", "building", con=con)
    assert out.t_bldg.sum() == 1


def test_size_filter_and_sources(con, tracts):
    rows = [(0.5, 0.5, MIN_AREA_M2 - 1, "Google Open Buildings"), (0.5, 0.6, MIN_AREA_M2, "Microsoft ML Buildings"),
            (0.5, 0.7, 500, "OpenStreetMap"), (0.5, 0.8, 50, "SomethingElse")]
    out = count_points(pts_sql(rows), tracts, "t", "building", con=con).set_index("GEOID").loc["00000000001"]
    assert out.t_bldg == 4 and out.t_bldg450 == 3              # 41.8 m2 is the inclusive threshold
    assert (out.t_src_google, out.t_src_msft, out.t_src_osm, out.t_src_other) == (1, 1, 1, 1)


def test_empty_tract_gets_zero_not_missing(con, tracts):
    out = count_points(pts_sql([(0.5, 0.5, 100, "OpenStreetMap")]), tracts, "t", "building", con=con).set_index("GEOID")
    assert out.loc["00000000002", "t_bldg"] == 0 and pd.isna(out.loc["00000000002", "t_area_med"])
