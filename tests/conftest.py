import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def vintages():
    """Known synthetic history; revisions vary by vintage to expose backfill leaks."""
    result = {}
    months = pd.date_range("1948-01-01", "2021-12-01", freq="MS")
    baseline = pd.Series(5 + 0.7 * np.sin(np.arange(len(months)) / 15), index=months)
    for i in range(100):
        year, quarter = 1996 + i // 4, i % 4 + 1
        origin = pd.Timestamp(year=year, month=quarter * 3 - 1, day=15)
        result[origin] = baseline.loc[: origin.replace(day=1) - pd.DateOffset(months=1)] + i / 1000
    return result
