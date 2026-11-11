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
