"""Compare cross-platform numeric results with a documented rounding tolerance."""

import json
import sys
from pathlib import Path

import pandas as pd

from macrocast.research import ARTIFACTS


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
    research = json.loads((reference / "research.json").read_text())
    assert research == json.loads((reproduced / "research.json").read_text()), (
        "Research specification changed"
    )
    for filename in ARTIFACTS:
        expected = research["status"] != "not_available_before_2015"
        assert (reference / filename).exists() == expected, f"Unexpected artifact state: {filename}"
        assert (reproduced / filename).exists() == expected, (
            f"Unexpected artifact state: {filename}"
        )
        if expected and filename.endswith(".csv"):
            pd.testing.assert_frame_equal(
                pd.read_csv(reference / filename),
                pd.read_csv(reproduced / filename),
                check_exact=False,
                rtol=1e-7,
                atol=1e-8,
            )
    print("All numeric research artifacts reproduce within rtol=1e-7, atol=1e-8")


if __name__ == "__main__":
    main()
