"""Construct each feature row exclusively from its own historical snapshot."""

import numpy as np
import pandas as pd

FEATURES = ["level", "lag_1", "lag_3", "lag_6", "lag_12", "change_3", "change_12", "vol_12"]


def features(series: pd.Series) -> dict[str, float]:
    last = series.index.max()
    expected = pd.date_range(last - pd.DateOffset(months=12), last, freq="MS")
    window = series.reindex(expected)
    if window.isna().any():
        missing = ", ".join(window.index[window.isna()].strftime("%Y-%m"))
        raise ValueError(f"Need 13 consecutive observed months; missing: {missing}")
    if not np.isfinite(window).all():
        raise ValueError("Nonfinite values in feature history")
    level = float(window.iloc[-1])
    return {
        "level": level,
        "lag_1": float(window.iloc[-2]),
        "lag_3": float(window.iloc[-4]),
        "lag_6": float(window.iloc[-7]),
        "lag_12": float(window.iloc[-13]),
        "change_3": level - float(window.iloc[-4]),
        "change_12": level - float(window.iloc[-13]),
        "vol_12": float(window.diff().dropna().std(ddof=1)),
    }


def build_dataset(vintages: dict[pd.Timestamp, pd.Series]) -> pd.DataFrame:
    rows = []
    exclusions = []
    for origin, series in sorted(vintages.items()):
        latest = series.index.max()
        target_month = latest + pd.DateOffset(months=3)
        if target_month <= origin:
            exclusions.append(
                {
                    "origin": str(origin.date()),
                    "reason": f"Target month already started; latest observation: {latest:%Y-%m}",
                }
            )
            continue
        try:
            feature_values = features(series)
        except ValueError as error:
            exclusions.append({"origin": str(origin.date()), "reason": str(error)})
            continue
        row = {
            "origin": origin,
            "last_observation": latest,
            "target_month": target_month,
            "data_age_months": (origin.year - latest.year) * 12 + origin.month - latest.month,
            **feature_values,
            "target": np.nan,
            "label_available": pd.NaT,
        }
        # Evaluate against the first archived snapshot containing the target,
        # not today's revised series, and not an assumed BLS initial release.
        for future_origin, future in sorted(vintages.items()):
            if future_origin > origin and row["target_month"] in future.index:
                row["target"] = float(future.loc[row["target_month"]])
                row["label_available"] = future_origin
                break
        rows.append(row)
    if not rows:
        raise ValueError("No origins have complete feature history")
    dataset = pd.DataFrame(rows).sort_values("origin").reset_index(drop=True)
    dataset.attrs["exclusions"] = exclusions
    dataset.attrs["source_vintages"] = len(vintages)
    dataset.attrs["latest_source_vintage"] = str(max(vintages).date())
    return dataset


def training_rows(dataset: pd.DataFrame, origin: pd.Timestamp) -> pd.DataFrame:
    # A prior forecast's realized label may first become available today.
    return dataset.loc[
        (dataset.origin < origin) & (dataset.label_available <= origin) & dataset.target.notna()
    ].copy()
