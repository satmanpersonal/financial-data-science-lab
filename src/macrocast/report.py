"""Generate inspectable CSV evidence, a Markdown research note, and figures."""

import json
from importlib.metadata import version
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from macrocast.data import checksum
from macrocast.evaluate import MODELS, loss_comparison, score

COLORS = {
    "persistence": "#64748b",
    "ar_linear": "#d97706",
    "ridge": "#0f766e",
    "gradient_boosting": "#7c3aed",
}


def markdown_table(frame: pd.DataFrame) -> str:
    def cell(value):
        return f"{value:.3f}" if isinstance(value, float) else str(value)

    lines = [
        "| " + " | ".join(frame.columns) + " |",
        "| " + " | ".join(["---"] * len(frame.columns)) + " |",
    ]
    lines += [
        "| " + " | ".join(cell(v) for v in row) + " |"
        for row in frame.itertuples(index=False, name=None)
    ]
    return "\n".join(lines)


def write_report(
    dataset: pd.DataFrame, predictions: pd.DataFrame, raw_path: Path, output: Path
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    metrics = score(predictions)
    comparisons = loss_comparison(predictions)
    exclusions = pd.DataFrame(dataset.attrs.get("exclusions", []), columns=["origin", "reason"])
    exclusions.to_csv(output / "excluded_origins.csv", index=False)
    dataset.to_csv(output / "dataset.csv", index=False, float_format="%.10g")
    predictions.to_csv(output / "predictions.csv", index=False, float_format="%.10g")
    metrics.to_csv(output / "metrics.csv", index=False, float_format="%.10g")
    comparisons.to_csv(output / "loss_comparison.csv", index=False, float_format="%.10g")
    metadata = {
        "data_sha256": checksum(raw_path),
        "first_origin": str(dataset.origin.min().date()),
        "last_origin": str(dataset.origin.max().date()),
        "n_vintages": len(dataset),
        "source_vintages": dataset.attrs.get("source_vintages", len(dataset)),
        "latest_source_vintage": dataset.attrs.get("latest_source_vintage"),
        "excluded_origins": len(exclusions),
        "unknown_targets": int(dataset.target.isna().sum()),
        "evaluation_start": "2000-01-01",
        "late_evaluation_start": "2015-01-01",
        "minimum_training_rows": 80,
        "forecast_observation_horizon_months": 3,
        "label_policy": "first subsequent archived quarterly vintage containing target month",
        "seed": 42,
        "hyperparameter_selection": "fixed; no search on evaluation outcomes",
        "packages": {
            name: version(name)
            for name in ["numpy", "pandas", "scikit-learn", "statsmodels", "matplotlib", "openpyxl"]
        },
    }
    (output / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    latest = predictions.loc[predictions.origin == predictions.origin.max()]
    latest.to_csv(output / "latest_forecast.csv", index=False, float_format="%.10g")
    observed = predictions.dropna(subset=["actual"])
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), constrained_layout=True)
    truth = observed.loc[observed.model == "persistence"]
    axes[0].plot(truth.target_month, truth.actual, color="#111827", label="Observed target", lw=2)
    for model in MODELS:
        block = observed.loc[observed.model == model]
        axes[0].plot(
            block.target_month,
            block.prediction,
            label=model,
            color=COLORS[model],
            alpha=0.85,
            lw=1.2,
        )
    axes[0].set(title="Vintage-aware unemployment forecasts", ylabel="Unemployment rate (%)")
    axes[0].legend(ncol=3, frameon=False)
    for model in MODELS:
        block = observed.loc[observed.model == model].sort_values("origin")
        errors = (block.prediction - block.actual).abs()
        axes[1].plot(
            block.origin,
            errors.cumsum() / np.arange(1, len(errors) + 1),
            color=COLORS[model],
            label=model,
        )
    axes[1].set(
        title="Cumulative out-of-sample mean absolute error",
        ylabel="MAE (percentage points)",
        xlabel="Forecast snapshot date",
    )
    fig.savefig(output / "forecast_comparison.png", dpi=160)
    plt.close(fig)
    late = metrics.loc[metrics.period == "evaluation_2015_onward"].sort_values("mae")
    comparison_period = "2015 onward"
    if late.empty:
        late = metrics.loc[metrics.period == "all"].sort_values("mae")
        comparison_period = "all available evaluation origins (none from 2015 onward)"
    best = late.iloc[0]
    fig, ax = plt.subplots(figsize=(8, 4), constrained_layout=True)
    ax.barh(late.model, late.mae, color=[COLORS[m] for m in late.model])
    ax.invert_yaxis()
    ax.set(
        title=f"{comparison_period}: model comparison",
        xlabel="Mean absolute error (percentage points; lower is better)",
    )
    fig.savefig(output / "model_comparison.png", dpi=160)
    plt.close(fig)
    note = f"""# Research results

Generated from the committed snapshot. Data SHA-256: `{checksum(raw_path)}`.

## Question and design

Can lagged unemployment dynamics improve on a no-change forecast of the unemployment
rate three observation months ahead? One sample is a quarterly historical snapshot.
All models use identical forecast origins and targets. Feature values come exclusively
from the origin's archived vintage, with no historical backfilling from later snapshots.
Training labels must be observable by the forecast origin.

Origins span {dataset.origin.min().date()} to {dataset.origin.max().date()}.
Evaluation starts in 2000 after at least 80 labeled training origins. The 2015 onward
block is reported separately, with fixed hyperparameters and expanding refits.
This is a retrospective research demonstration, not a prospectively sealed holdout.

## Main comparison: {comparison_period}

{markdown_table(late[["model", "n", "mae", "rmse", "bias"]])}

Lowest observed MAE: **{best["model"]}**, **{best.mae:.3f} percentage points**.
This sample ranking is not evidence of durable superiority or investment profitability.

![Model comparison](model_comparison.png)

## All reported periods and shock sensitivity

{markdown_table(metrics)}

The 2020–2021 exclusion is a prespecified sensitivity view. The headline comparison
includes these shocks. Positive bias means overprediction. MAE, RMSE, and bias are
all in percentage points; the sample count is the number of quarterly forecast origins.

![Forecasts and cumulative error](forecast_comparison.png)

## Uncertainty in differences from persistence

{markdown_table(comparisons)}

Negative differences favor the alternative. These are pointwise 95% intervals for
mean paired absolute-loss differences, estimated with an intercept-only OLS and
HAC covariance (four quarterly lags, finite-sample correction, t reference).
They allow local serial correlation and heteroskedasticity under asymptotic conditions;
they do not establish stationarity or robustness to structural breaks. Small samples,
COVID outliers, and multiple comparisons limit inference. These are exploratory,
unadjusted intervals, not simultaneous intervals or model-selection guarantees.

## Latest archived-origin predictions

{markdown_table(latest[["origin", "target_month", "model", "prediction", "n_train"]])}

These are forecasts at the last included historical snapshot, not necessarily at the
present date. Unknown outcomes remain missing and are excluded from scoring.

## Missing-data audit

Latest source vintage: **{metadata["latest_source_vintage"]}**.
Excluded feature origins: **{len(exclusions)}**. Unobserved targets across all eligible
origins: **{metadata["unknown_targets"]}**. All models share the same exclusions.

{markdown_table(exclusions)}

The current workbook has a missing October 2025 observation. Origins whose 13-month
feature window crosses that gap are excluded; outcomes requiring that missing month
remain unknown. Consequently, the latest eligible forecast can precede the latest
source vintage. Missing values are never imputed or replaced by revised future data.

## Interpretation and limits

- Only unemployment history is used. This is an interpretable univariate benchmark,
  not a complete macroeconomic information set or a trading strategy.
- The target uses the first archived quarterly snapshot containing that target month.
  This is **not guaranteed to be the BLS initial-release value**.
- Snapshot dates are Feb/May/Aug/Nov 15, as documented by the publisher. This assumes
  the snapshot is available on that date; publication-time and latency simulation is
  outside scope. The horizon is three months from the last observation month, roughly
  2.5 months from the usual snapshot date to the target's release.
- About 60 years of quarterly snapshots provide few independent observations for ML.
  Nonlinearity may add variance; fitting a model successfully does not validate it.
- Historical data collection and seasonal-adjustment revisions may contain errors.
  This snapshot is reproducible; refreshing the upstream workbook can change results.
- No causal claims, calibrated prediction intervals, or investment returns are implied.

See [methodology](../docs/methodology.md), [data provenance](../docs/data.md),
and the exact [run metadata](run.json). Forecast rows include training counts and
the latest training-label date for independent leakage audits.
"""
    (output / "results.md").write_text(note, encoding="utf-8")
