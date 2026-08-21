from __future__ import annotations

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "python_results"


def collect_ab_context() -> dict:
    path = RESULTS_DIR / "ab_test_summary.csv"
    if not path.exists():
        return {"status": "not_found", "file": "ab_test_summary.csv"}

    row = pd.read_csv(path).iloc[0].to_dict()

    # Convert numpy scalars to native values.
    out = {}
    for k, v in row.items():
        if hasattr(v, "item"):
            try:
                v = v.item()
            except Exception:
                pass
        out[k] = v

    return {
        "experiment": "Checkout Redesign",
        "verified_result": out,
    }
