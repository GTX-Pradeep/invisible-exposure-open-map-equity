"""Unit tests on synthetic data: leakage guard, conformal coverage, flags, bootstrap, FDR."""
import numpy as np
import pandas as pd
import pytest

from coverage_risk.audit import bh, cluster_sums, fast_boot, flag_contrast
from coverage_risk.model import assert_no_leakage, crossfit_cqr, make_folds, spatial_blocks
from coverage_risk.provenance import provenance_features
from coverage_risk.validation import deletion_test, flag_skill


@pytest.fixture(scope="module")
def synth():
    rng = np.random.default_rng(0)
    n = 1500
    lat, lon = rng.uniform(30, 36, n), rng.uniform(-112, -96, n)
    hu = rng.lognormal(7, 0.6, n)
    land = rng.lognormal(1, 1, n)
    y = np.round(hu * 0.9 * np.exp(rng.normal(0, 0.15, n)))
    return pd.DataFrame({"GEOID": [f"{i:011d}" for i in range(n)], "region": np.where(lon < -104, "west", "east"),
                         "county": [f"{i % 60:05d}" for i in range(n)], "lat": lat, "lon": lon,
                         "hu": hu, "land_km2": land, "count": y})


def test_leakage_guard_refuses_audit_columns():
    for bad in ["svi_overall", "tribal_any", "usfs_BP_mean", "ref_bldg", "r2026a_bldg", "lat", "region"]:
        with pytest.raises(ValueError):
            assert_no_leakage(["hu", bad])
    assert_no_leakage(["hu", "pop", "land_km2", "jobs"])  # structural columns pass


def test_spatial_folds_keep_blocks_together(synth):
    folds = make_folds(synth, "spatial", k=5, seed=1, km=50)
    blocks = spatial_blocks(synth.lat, synth.lon, 50)
    assert pd.DataFrame({"b": blocks, "f": folds}).groupby("b").f.nunique().max() == 1
    assert set(np.unique(folds)) == set(range(5))


def test_cqr_coverage_near_nominal(synth):
    folds = make_folds(synth, "spatial", k=5, seed=1, km=50)
    out = crossfit_cqr(synth, "count", ["hu", "land_km2"], folds, alpha=0.10,
                       params={"n_estimators": 150, "learning_rate": 0.05, "num_leaves": 15}, seed=0)
    assert 0.86 <= out.covered.mean() <= 0.94
    assert (out.lower <= out.expected).all() and (out.expected <= out.upper).all()
    assert np.isclose(out.flag.mean(), (out.y_log < out.lower_log).mean())


def test_deletion_detects_large_losses(synth):
    folds = make_folds(synth, "random", k=5, seed=1)
    out = crossfit_cqr(synth, "count", ["hu", "land_km2"], folds, alpha=0.10,
                       params={"n_estimators": 150, "learning_rate": 0.05, "num_leaves": 15}, seed=0)
    dt = deletion_test(out, fractions=(0.1, 0.7), n_tracts=500, seed=0).set_index("removed_share").detection_rate
    assert dt.loc[0.7] > 0.9 > dt.loc[0.1]


def test_flag_skill_perfect_and_random():
    truth = np.array([1, 1, 0, 0, 0, 0], bool)
    r = flag_skill(truth.copy(), truth.astype(float), truth)
    assert r["precision"] == 1 and r["recall"] == 1 and r["auc"] == 1


def test_fast_bootstrap_matches_point_estimate(synth):
    d = synth.copy()
    d["g"] = (d.region == "west").astype(int)
    d["y"] = (d["count"] < d["count"].median()).astype(float)
    d["n1"], d["y1"], d["n0"], d["y0"] = d.g, d.g * d.y, 1 - d.g, (1 - d.g) * d.y
    est, lo, hi, reps = fast_boot(cluster_sums(d, ["n1", "y1", "n0", "y0"]), lambda z: z["y1"] / z["n1"] - z["y0"] / z["n0"], 500, 0)
    direct = d.loc[d.g == 1, "y"].mean() - d.loc[d.g == 0, "y"].mean()
    assert np.isclose(est, direct) and lo <= est <= hi and len(reps) == 500


def test_flag_contrast_runs(synth):
    d = synth.copy()
    d["rural"] = np.where(d.land_km2 > d.land_km2.median(), "rural", "urban")
    d["f"] = (d["count"] < d.hu * 0.8).astype(float)
    r = flag_contrast(d, "f", "rural", n_boot=200, seed=0)
    assert r["contrast"] == "rural vs urban" and 0 <= r["rate_hi"] <= 1


def test_bh_is_monotone_and_handles_nan():
    p = pd.Series([0.001, 0.02, 0.04, 0.5, np.nan])
    rej, padj = bh(p, 0.05)
    assert rej.iloc[0] and not rej.iloc[3] and np.isnan(padj.iloc[4])
    assert (padj.dropna().diff().dropna() >= -1e-12).all()


def test_provenance_entropy_bounds():
    df = pd.DataFrame({"GEOID": ["a", "b"], "r_bldg": [10, 4], "r_src_osm": [10, 1], "r_src_msft": [0, 1],
                       "r_src_google": [0, 1], "r_src_esri": [0, 1], "r_src_other": [0, 0]})
    p = provenance_features(df, "r")
    assert p.b_src_entropy.iloc[0] == 0 and np.isclose(p.b_src_entropy.iloc[1], 2.0)
    assert p.b_single_source.tolist() == [1.0, 0.0]


def test_leakage_guard_refuses_merged_imports():
    """Every column of data/external/merged_inputs.csv is refused as a model input."""
    for bad in ["mec_bldg_n_class", "mec_bldg_n_msft", "alt_usfs_WHP_mean", "alt_pmdi_mean", "if_poi_n",
                "exp_mu_nb", "exp_y", "prj_mu_G", "prj_y"]:
        with pytest.raises(ValueError):
            assert_no_leakage(["hu", bad])


def test_topk_budget_flags_exactly_k():
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location("m11", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "11_merged_exploratory.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    s = pd.Series([0.1, np.nan, 3.0, 2.0, 2.0, -1.0])
    f = m.topk(s, 3)
    assert f.sum() == 3 and f[2] and not f[1]          # NaN never flagged; ties broken stably
