"""Compare cross-platform numeric results with a documented rounding tolerance."""

import json
import sys
from pathlib import Path

import pandas as pd


def main() -> None:
    reference, reproduced = map(Path, sys.argv[1:])
    for filename in [
        "dataset.csv",
        "predictions.csv",
        "metrics.csv",
        "loss_comparison.csv",
        "excluded_origins.csv",
    ]:
        pd.testing.assert_frame_equal(
            pd.read_csv(reference / filename),
            pd.read_csv(reproduced / filename),
            check_exact=False,
            rtol=1e-7,
            atol=1e-8,
        )
    before = json.loads((reference / "run.json").read_text())
    after = json.loads((reproduced / "run.json").read_text())
    assert before == after, "Source or environment metadata changed"
    print("All numeric research artifacts reproduce within rtol=1e-7, atol=1e-8")


if __name__ == "__main__":
    main()
