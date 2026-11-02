"""Exploratory robustness and a sequential model-selection experiment.

These extensions were added after the original fixed-model results were observed.
They are not confirmatory tests or a hyperparameter optimization procedure.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from macrocast.evaluate import MODELS, score, validate_predictions, walk_forward
from macrocast.report import COLORS, markdown_table

ARTIFACTS = [
    "rolling_predictions.csv",
    "rolling_metrics.csv",
    "selection_predictions.csv",
    "selection_audit.csv",
    "selection_metrics.csv",
    "error_attribution.csv",
    "regime_metrics.csv",
    "research_diagnostics.png",
]


def sequential_selection(
    predictions: pd.DataFrame, start: str = "2015-01-01", lookback: int = 20
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Choose annually using only matured, prior out-of-sample forecast losses.

    Reuse the four fixed candidates' prequential forecasts. This is model selection,
    not nested hyperparameter tuning. Equal MAE is resolved in MODELS order, which
    puts persistence first. A minimum of 12 common scored origins is required.
    """
    validate_predictions(predictions)
    if lookback < 12:
        raise ValueError("Selection requires at least 12 validation origins")
    if "label_available" not in predictions:
        raise ValueError("Selection requires archived label-availability dates")
    selected_rows, audit = [], []
    selected, year, selection_date = "persistence", None, None
    for origin in sorted(
        predictions.loc[predictions.origin >= pd.Timestamp(start), "origin"].unique()
    ):
        origin = pd.Timestamp(origin)
        if year != origin.year:
            selection_date, year = origin, origin.year
            known = predictions.loc[
                (predictions.origin < origin)
                & (predictions.label_available <= origin)
                & predictions.actual.notna()
            ].copy()
            validation_dates = sorted(known.origin.unique())[-lookback:]
            known = known.loc[known.origin.isin(validation_dates)]
            enough = len(validation_dates) >= 12
            losses = (known.prediction - known.actual).abs().groupby(known.model).mean()
            selected = (
                min(MODELS, key=lambda model: float(losses[model])) if enough else "persistence"
            )
            for candidate in MODELS:
                audit.append(
                    {
                        "selection_date": origin,
                        "candidate": candidate,
                        "selected": candidate == selected,
                        "validation_n": len(validation_dates),
                        "validation_mae": float(losses[candidate]) if enough else np.nan,
                        "max_validation_origin": known.origin.max(),
                        "max_validation_label_date": known.label_available.max(),
                        "fallback": not enough,
                    }
                )
        chosen = (
            predictions.loc[(predictions.origin == origin) & (predictions.model == selected)]
            .iloc[0]
            .to_dict()
        )
        chosen.update(
            model="adaptive_selector", selected_candidate=selected, selection_date=selection_date
        )
        selected_rows.append(chosen)
    return pd.DataFrame(selected_rows), pd.DataFrame(audit)


def error_attribution(predictions: pd.DataFrame) -> pd.DataFrame:
    """Descriptive error concentration; no retroactive regime-based model choice."""
    validate_predictions(predictions)
    observed = predictions.dropna(subset=["actual"]).copy()
    observed["absolute_error"] = (observed.prediction - observed.actual).abs()
    observed["squared_error"] = (observed.prediction - observed.actual) ** 2
    observed["absolute_error_share"] = observed.absolute_error / observed.groupby(
        "model"
    ).absolute_error.transform("sum").replace(0, np.nan)
    observed["squared_error_share"] = observed.squared_error / observed.groupby(
        "model"
    ).squared_error.transform("sum").replace(0, np.nan)
    observed["error_rank"] = (
        observed.groupby("model").absolute_error.rank(method="first", ascending=False).astype(int)
    )
    return observed.sort_values(["model", "error_rank"])


def regime_scores(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, begin, end in [
        ("2000_2014", "2000-01-01", "2015-01-01"),
        ("2015_2019", "2015-01-01", "2020-01-01"),
        ("2020_2021", "2020-01-01", "2022-01-01"),
        ("2022_onward", "2022-01-01", "2100-01-01"),
    ]:
        block = predictions.loc[
            (predictions.origin >= pd.Timestamp(begin)) & (predictions.origin < pd.Timestamp(end))
        ]
        if block.actual.notna().any():
            metrics = score(block)
            metrics = (
                metrics.loc[metrics.period == "all"].assign(regime=name).drop(columns="period")
            )
            rows.append(metrics)
    return pd.concat(rows, ignore_index=True)


def write_research(dataset: pd.DataFrame, predictions: pd.DataFrame, output: Path) -> None:
    selected, audit = sequential_selection(predictions)
    # Older --as-of snapshots can predate the adaptive experiment entirely.
    if selected.empty:
        # Never leave a prior, later-dated experiment beside an older cutoff run.
        for filename in ARTIFACTS:
            (output / filename).unlink(missing_ok=True)
        (output / "research.json").write_text(
            json.dumps(
                {
                    "status": "not_available_before_2015",
                },
                indent=2,
            )
            + "\n"
        )
        (output / "robustness.md").write_text(
            "# Robustness experiments\n\nNo eligible origins from 2015 onward remain "
            "at this cutoff. The annual-selector experiment is unavailable.\n"
        )
        return
    rolling = walk_forward(dataset, window=80)
    rolling_metrics = score(rolling)
    rolling_metrics.to_csv(output / "rolling_metrics.csv", index=False, float_format="%.10g")
    rolling.to_csv(output / "rolling_predictions.csv", index=False, float_format="%.10g")
    selected.to_csv(output / "selection_predictions.csv", index=False, float_format="%.10g")
    audit.to_csv(output / "selection_audit.csv", index=False, float_format="%.10g")
    attribution = error_attribution(predictions)
    attribution.to_csv(output / "error_attribution.csv", index=False, float_format="%.10g")
    regimes = regime_scores(predictions)
    regimes.to_csv(output / "regime_metrics.csv", index=False, float_format="%.10g")
    observed_selector = selected.dropna(subset=["actual"])
    comparison = predictions.loc[predictions.origin.isin(observed_selector.origin)].copy()
    comparison = pd.concat([comparison, observed_selector], ignore_index=True)
    summary = []
    naive = comparison.loc[comparison.model == "persistence"]
    baseline_mae = (naive.prediction - naive.actual).abs().mean()
    for model, block in comparison.groupby("model"):
        error = block.prediction - block.actual
        summary.append(
            {
                "model": model,
                "n": len(block),
                "mae": error.abs().mean(),
                "rmse": np.sqrt((error**2).mean()),
                "mae_skill_vs_persistence": (
                    1 - error.abs().mean() / baseline_mae if baseline_mae > 0 else np.nan
                ),
            }
        )
    summary = pd.DataFrame(summary).sort_values("mae")
    summary.to_csv(output / "selection_metrics.csv", index=False, float_format="%.10g")
    count = audit.loc[audit.selected].groupby("candidate").size().to_dict()
    specification = {
        "status": "exploratory extension after inspection of original fixed-model results",
        "selector": {
            "start": "2015-01-01",
            "retune": "first eligible origin each calendar year",
            "lookback_origins": 20,
            "minimum_validation_origins": 12,
            "tie_break_order": MODELS,
            "validation_metric": "MAE",
            "fallback": "persistence",
            "selection_counts": count,
        },
        "rolling_window_labeled_origins": 80,
        "regime_boundaries": ["2000-01-01", "2015-01-01", "2020-01-01", "2022-01-01"],
    }
    (output / "research.json").write_text(json.dumps(specification, indent=2) + "\n")
    late_expanding = score(predictions).query("period == 'evaluation_2015_onward'")
    late_rolling = rolling_metrics.query("period == 'evaluation_2015_onward'")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    positions = np.arange(len(MODELS))
    for shift, label, frame, color in [
        (-0.18, "Expanding history", late_expanding, "#0f766e"),
        (0.18, "Latest 80 labeled origins", late_rolling, "#d97706"),
    ]:
        axes[0].barh(
            positions + shift,
            frame.set_index("model").loc[MODELS].mae,
            height=0.34,
            label=label,
            color=color,
        )
    axes[0].set(
        yticks=positions,
        yticklabels=MODELS,
        xlabel="MAE (percentage points)",
        title="2015 onward: training-window sensitivity",
    )
    axes[0].invert_yaxis()
    axes[0].legend(frameon=False, fontsize=8)
    colors = [COLORS.get(model, "#111827") for model in summary.model]
    axes[1].barh(summary.model, summary.mae, color=colors)
    axes[1].invert_yaxis()
    axes[1].set(xlabel="MAE (percentage points)", title="Annual past-loss model selection")
    fig.savefig(output / "research_diagnostics.png", dpi=160)
    plt.close(fig)
    top = attribution.loc[
        attribution.error_rank <= 3, ["model", "origin", "absolute_error", "squared_error_share"]
    ]
    shock = (
        attribution.loc[attribution.origin.dt.year.isin([2020, 2021])]
        .groupby("model")[["absolute_error_share", "squared_error_share"]]
        .sum()
        .reset_index()
    )
    note = f"""# Robustness and model-selection experiments

These analyses were added **after** the initial fixed-model results were observed.
They are exploratory. Their historical outcomes cannot become a new untouched holdout.
The fixed-model comparison remains the primary benchmark. Its eligibility policy
now excludes origins with an already-started target month, keeping future-month
forecasts separate from nowcasts. The original version is preserved in Git history.

## Training-window sensitivity

Compare expanding history with the latest 80 labeled origins (about 20 years).
Both use identical feature definitions, label-availability constraints, fixed model
settings, forecast origins and targets. A shorter history may adapt faster but has
higher estimation variance. No window length was chosen by maximizing evaluation performance.

{markdown_table(late_rolling[["model", "n", "mae", "rmse", "mae_skill_vs_persistence"]])}

## Annual model selection using only matured past forecasts

At the first eligible forecast origin of each calendar year from 2015 onward,
choose among the four fixed candidates by MAE on the latest 20 **prior** forecast
origins whose targets have become observable. Require 12 validation origins or
fall back to persistence; break exact ties in the declared model order, persistence
first. Freeze that choice for the year while the underlying candidates continue
their ordinary expanding-window refits. This reuses authentic historical
out-of-sample forecasts. It does not select hyperparameters or use random folds.

{markdown_table(summary)}

Positive MAE skill means improvement over persistence on the same origins.
Selection years per candidate: `{count}`. The audit records each candidate's validation
MAE, validation count, latest validation origin, and latest available label date.
Selection is past-only, but choosing this research question after viewing the
baseline results remains a researcher-level source of adaptation. No confirmatory
significance claim is attached to this additional comparison.

![Robustness diagnostics](research_diagnostics.png)

## Contiguous calendar blocks

{markdown_table(regimes)}

These are descriptive calendar blocks, not inferred economic regimes or a live
regime detector. Small denominators make rankings unstable. No hindsight-based
regime switches are used in the forecasts.

## What drives aggregate error?

Shares of each model's total absolute and squared forecast errors arising at
2020–2021 origins:

{markdown_table(shock)}

Largest three absolute-error origins per model:

{markdown_table(top)}

Concentration in a few shock origins limits how much can be learned from average
scores alone. Forecast-origin dates differ from target-month dates. Error shares
are descriptive contributions, not causal investment attribution.

## Practical interpretation

This benchmark can inform how to validate a macroeconomic input to scenario
analysis. It does not map unemployment forecasts into asset returns or portfolio
weights. Before using such an input in investment research, specify the decision,
release-time availability, downstream exposure, forecast uncertainty, transaction
costs where relevant, and a separate prospective evaluation.
"""
    (output / "robustness.md").write_text(note, encoding="utf-8")
