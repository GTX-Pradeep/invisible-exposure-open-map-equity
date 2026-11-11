<<<<<<< HEAD
"""The analysis steps after the import scripts must run from the repository alone (no sibling project)."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_numbers_and_exploratory_scripts_do_not_read_sibling_project():
    for name in ["11_merged_exploratory.py", "12_merged_numbers.py", "15_review_checks.py", "16_relative_rmse.py"]:
        code = "\n".join(l for l in (ROOT / "scripts" / name).read_text().splitlines() if not l.lstrip().startswith("#"))
        assert "mapequity_root" not in code and "../" not in code, name


def test_inputs_for_later_steps_present():
    assert (ROOT / "data/external/merged_inputs.csv").exists()
    for name in ["11_merged_exploratory.py", "12_merged_numbers.py", "15_review_checks.py", "16_relative_rmse.py"]:
        code = (ROOT / "scripts" / name).read_text()
        assert "data/external/companion" not in code and "mapequity_root" not in code, name
=======
"""The repository must reproduce its own paper without the sibling MapEquityChallenge folder."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPANION = ["layer_predictability.csv", "highway_transfer.csv", "provenance_beyond_counts.csv", "mapequity_risk.csv", "sources.json"]


def test_companion_copies_are_committed():
    for f in COMPANION:
        assert (ROOT / "data/external/companion" / f).exists(), f
    assert (ROOT / "data/external/merged_inputs.csv").exists()


def test_number_scripts_do_not_read_the_sibling_folder():
    for script in ["scripts/12_merged_numbers.py", "scripts/14_reference_validation.py", "scripts/11_merged_exploratory.py"]:
        text = (ROOT / script).read_text()
        assert "MapEquityChallenge" not in text and "mapequity_root" not in text, script
>>>>>>> 9550b1c9c0451fb1f8f9d3b7b6e530418447aa19
