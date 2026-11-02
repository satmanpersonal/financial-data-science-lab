import numpy as np
import pandas as pd

from macrocast.dataset import build_dataset
from macrocast.evaluate import MODELS, loss_comparison, score, walk_forward
from macrocast.report import write_report


def test_walk_forward_scores_aligned_origins_and_auditable_training(vintages, tmp_path):
    dataset = build_dataset(vintages)
    predictions = walk_forward(dataset, start="1990-01-01")
    assert set(predictions.model) == set(MODELS)
    assert predictions.groupby("origin").size().eq(4).all()
    assert (predictions.max_training_label_date <= predictions.origin).all()
    assert predictions.n_train.min() >= 80
    assert np.isfinite(predictions.prediction).all()
    assert predictions.loc[predictions.origin == predictions.origin.max(), "actual"].isna().all()
    metrics = score(predictions)
    assert metrics.loc[metrics.period == "all", "n"].nunique() == 1
    assert (metrics.mae >= 0).all()
    source = tmp_path / "raw.xlsx"
    source.write_bytes(b"test provenance only")
    write_report(dataset, predictions, source, tmp_path / "report")
    assert (tmp_path / "report" / "results.md").exists()
    assert (tmp_path / "report" / "forecast_comparison.png").stat().st_size > 1000


def test_metrics_and_paired_loss_difference_have_expected_units():
    rows = []
    for origin in pd.date_range("2015-02-15", periods=12, freq="3MS"):
        for model in MODELS:
            rows.append(
                {
                    "origin": origin,
                    "actual": 5.0,
                    "model": model,
                    "prediction": 6.0 if model == "persistence" else 5.5,
                }
            )
    predictions = pd.DataFrame(rows)
    metrics = score(predictions)
    naive = metrics.loc[(metrics.model == "persistence") & (metrics.period == "all")].iloc[0]
    assert naive.mae == naive.rmse == naive.bias == 1.0
    comparison = loss_comparison(predictions)
    assert np.allclose(comparison.mae_difference_vs_persistence, -0.5)
