"""Expanding-window evaluation and dependence-aware loss comparisons."""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from macrocast.dataset import FEATURES, training_rows

MODELS = ["persistence", "ar_linear", "ridge", "gradient_boosting"]


def validate_predictions(predictions: pd.DataFrame) -> None:
    """Fail closed if model comparisons would use different samples or outcomes."""
    required = {"origin", "model", "actual", "prediction"}
    if not required.issubset(predictions.columns) or predictions.empty:
        raise ValueError("Predictions require nonempty origin/model/actual/prediction columns")
    if predictions[["origin", "model"]].isna().any().any():
        raise ValueError("Origin and model identifiers cannot be missing")
    if predictions.duplicated(["origin", "model"]).any():
        raise ValueError("Duplicate model/origin predictions")
    if set(predictions.model) != set(MODELS):
        raise ValueError("Prediction models do not match the declared comparison")
    if not predictions.groupby("origin").model.nunique().eq(len(MODELS)).all():
        raise ValueError("Every model must cover identical forecast origins")
    if not np.isfinite(predictions.prediction).all():
        raise ValueError("Nonfinite forecast")
    if np.isinf(predictions.actual).any():
        raise ValueError("Infinite realized outcome")
    if predictions.groupby("origin").actual.nunique(dropna=False).gt(1).any():
        raise ValueError("Models disagree on realized outcomes or missing-label status")
    for field in ["target_month", "label_available", "last_observation"]:
        if (
            field in predictions
            and predictions.groupby("origin")[field].nunique(dropna=False).gt(1).any()
        ):
            raise ValueError(f"Models disagree on {field}")
    if (
        "max_training_label_date" in predictions
        and (predictions.max_training_label_date > predictions.origin).any()
    ):
        raise ValueError("Training includes a label unavailable at the forecast origin")


def predict(train: pd.DataFrame, row: pd.DataFrame) -> dict[str, float]:
    """Predict level changes for stable linear baselines; add today's level back."""
    y = train.target - train.level
    ar = sm.OLS(
        y.to_numpy(), sm.add_constant(train[["change_3"]], has_constant="add"), missing="raise"
    ).fit()
    ar_prediction = ar.predict(sm.add_constant(row[["change_3"]], has_constant="add"))
    ridge = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    ridge.fit(train[FEATURES], y)
    boosting = HistGradientBoostingRegressor(
        max_iter=100,
        max_leaf_nodes=7,
        min_samples_leaf=12,
        learning_rate=0.05,
        l2_regularization=10.0,
        early_stopping=False,
        random_state=42,
    )
    with threadpool_limits(limits=1):
        boosting.fit(train[FEATURES], y)
        nonlinear = float(boosting.predict(row[FEATURES])[0])
    level = float(row.level.iloc[0])
    return {
        "persistence": level,
        "ar_linear": level + float(ar_prediction.iloc[0]),
        "ridge": level + float(ridge.predict(row[FEATURES])[0]),
        "gradient_boosting": level + nonlinear,
    }


def walk_forward(
    dataset: pd.DataFrame, start: str = "2000-01-01", window: int | None = None
) -> pd.DataFrame:
    if window is not None and window < 80:
        raise ValueError("Rolling windows require at least 80 labeled origins")
    results = []
    for index, point in dataset.loc[dataset.origin >= pd.Timestamp(start)].iterrows():
        train = training_rows(dataset, point.origin)
        if window is not None:
            train = train.sort_values("origin").tail(window)
        if len(train) < 80:
            continue
        predictions = predict(train, dataset.loc[[index]])
        for model, prediction in predictions.items():
            results.append(
                {
                    "origin": point.origin,
                    "target_month": point.target_month,
                    "label_available": point.label_available,
                    "actual": point.target,
                    "model": model,
                    "prediction": prediction,
                    "n_train": len(train),
                    "max_training_label_date": train.label_available.max(),
                    "last_observation": point.last_observation,
                }
            )
    if not results:
        raise ValueError("No evaluation origins with at least 80 available training labels")
    return pd.DataFrame(results)


def score(predictions: pd.DataFrame) -> pd.DataFrame:
    validate_predictions(predictions)
    observed = predictions.dropna(subset=["actual"]).copy()
    observed["error"] = observed.prediction - observed.actual
    observed["period"] = np.where(
        observed.origin < pd.Timestamp("2015-01-01"),
        "development_2000_2014",
        "evaluation_2015_onward",
    )
    groups = [("all", observed)]
    groups += list(observed.groupby("period"))
    # Prespecified shock sensitivity; exclusion is never the headline result.
    groups.append(
        ("excluding_2020_2021", observed.loc[~observed.origin.dt.year.isin([2020, 2021])])
    )
    rows = []
    for period, block in groups:
        baseline = block.loc[block.model == "persistence", "error"].abs().mean()
        for model, subset in block.groupby("model"):
            rows.append(
                {
                    "period": period,
                    "model": model,
                    "n": len(subset),
                    "mae": float(subset.error.abs().mean()),
                    "rmse": float(np.sqrt((subset.error**2).mean())),
                    "bias": float(subset.error.mean()),
                    "mae_skill_vs_persistence": (
                        float(1 - subset.error.abs().mean() / baseline) if baseline > 0 else np.nan
                    ),
                }
            )
    return pd.DataFrame(rows)


def loss_comparison(predictions: pd.DataFrame) -> pd.DataFrame:
    """Pointwise HAC intervals, not an independence-based significance test."""
    validate_predictions(predictions)
    observed = predictions.dropna(subset=["actual"]).copy()
    observed["loss"] = (observed.prediction - observed.actual).abs()
    rows = []
    for period, block in [
        ("all", observed),
        ("evaluation_2015_onward", observed.loc[observed.origin >= pd.Timestamp("2015-01-01")]),
    ]:
        wide = block.pivot(index="origin", columns="model", values="loss").dropna()
        for model in MODELS[1:]:
            delta = wide[model] - wide.persistence
            if len(delta) < 8:
                continue
            fit = sm.OLS(delta.to_numpy(), np.ones((len(delta), 1))).fit(
                cov_type="HAC",
                cov_kwds={"maxlags": 4, "use_correction": True},
                use_t=True,
            )
            interval = fit.conf_int(alpha=0.05)[0]
            rows.append(
                {
                    "period": period,
                    "model": model,
                    "n": len(delta),
                    "mae_difference_vs_persistence": float(delta.mean()),
                    "ci95_low": float(interval[0]),
                    "ci95_high": float(interval[1]),
                }
            )
    return pd.DataFrame(rows)
