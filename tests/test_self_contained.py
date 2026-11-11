"""The repository must reproduce its own paper without the sibling MapEquityChallenge folder."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPANION = ["layer_predictability.csv", "highway_transfer.csv", "provenance_beyond_counts.csv", "mapequity_risk.csv", "sources.json"]


def test_companion_copies_are_committed():
    for f in COMPANION:
        assert (ROOT / "data/external/companion" / f).exists(), f
    assert (ROOT / "data/external/merged_inputs.csv").exists()


def test_number_scripts_do_not_read_the_sibling_folder():
    for script in ["scripts/12_merged_numbers.py", "scripts/14_reference_validation.py", "scripts/11_merged_exploratory.py",
                   "scripts/16_relative_rmse.py", "scripts/17_review_checks.py"]:
        text = (ROOT / script).read_text()
        assert "MapEquityChallenge" not in text and "mapequity_root" not in text, script
