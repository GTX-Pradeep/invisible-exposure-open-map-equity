"""Uncertainty-aware open-map coverage risk and equity audit."""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path | None = None) -> dict:
    """Load config/config.yaml (or a given path)."""
    path = Path(path) if path else PROJECT_ROOT / "config" / "config.yaml"
    with open(path) as f:
        return yaml.safe_load(f)
