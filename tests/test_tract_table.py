"""The tract-table checks pass on the published table and catch the failures they exist for."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from coverage_risk.checks import check_tract_table

PUBLISHED = Path(__file__).resolve().parents[1] / "deliverables" / "dataset" / "tracts_model_table.csv"


@pytest.fixture(scope="module")
def table():
    if not PUBLISHED.exists():
        pytest.skip("published tract table not present")
    return pd.read_csv(PUBLISHED, dtype={"GEOID": str})


def test_published_table_passes(table):
    res = check_tract_table(table)
    assert res["n_tracts"] == 9794


@pytest.mark.parametrize("breakage", ["duplicate", "lost_zero", "missing_acs", "share_over_1", "sources_dont_add", "bldg450_too_big", "wrong_list"])
def test_checks_catch_breakage(table, breakage):
    d = table.copy()
    expected = None
    if breakage == "duplicate":
        d = pd.concat([d, d.head(1)])
    elif breakage == "lost_zero":              # GEOID read as a number: leading zero lost
        d.loc[0, "GEOID"] = d.loc[0, "GEOID"].lstrip("0") or "0"
    elif breakage == "missing_acs":
        d.loc[5, "hu"] = np.nan
    elif breakage == "share_over_1":
        d.loc[5, "sh_u1_det"] = 1.7
    elif breakage == "sources_dont_add":
        d.loc[5, "r2026a_src_osm"] += 3
    elif breakage == "bldg450_too_big":
        d.loc[5, "r2026a_bldg450"] = d.loc[5, "r2026a_bldg"] + 1
    elif breakage == "wrong_list":
        expected = list(d.GEOID[1:]) + ["99999999999"]
    with pytest.raises(AssertionError):
        check_tract_table(d, expected_geoids=expected)
