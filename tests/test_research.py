import numpy as np
import pandas as pd
import pytest

from macrocast.dataset import build_dataset
from macrocast.evaluate import MODELS, score, walk_forward
from macrocast.research import error_attribution, sequential_selection, write_research


@pytest.fixture
def forecasts():
    rows = []
    for origin in pd.date_range("2010-02-15", periods=40, freq=pd.DateOffset(months=3)):
        for model, offset in zip(MODELS, [0.3, 0.1, 0.2, 0.4], strict=True):
            rows.append(
                {
                    "origin": origin,
                    "model": model,
                    "actual": 5.0,
                    "prediction": 5.0 + offset,
                    "label_available": origin + pd.DateOffset(months=3),
                }
            )
    return pd.DataFrame(rows)


def test_selector_uses_only_matured_prior_validation_labels_and_freezes_annually(forecasts):
    selected, audit = sequential_selection(forecasts)
    assert selected.selected_candidate.eq("ar_linear").all()
    assert (audit.max_validation_origin < audit.selection_date).all()
    assert (audit.max_validation_label_date <= audit.selection_date).all()
    assert audit.validation_n.eq(20).all()
    assert selected.groupby(selected.origin.dt.year).selection_date.nunique().eq(1).all()


def test_changing_current_and_future_outcomes_cannot_change_current_selection(forecasts):
    cutoff = pd.Timestamp("2017-02-15")
    original, audit = sequential_selection(forecasts)
    changed = forecasts.copy()
    changed.loc[changed.origin >= cutoff, "actual"] = 50.0
    modified, altered_audit = sequential_selection(changed)
    pd.testing.assert_frame_equal(
        audit.loc[audit.selection_date <= cutoff],
        altered_audit.loc[altered_audit.selection_date <= cutoff],
    )
    in_year = original.origin.dt.year == 2017
    assert original.loc[in_year, "selected_candidate"].equals(
        modified.loc[in_year, "selected_candidate"]
    )


def test_unreleased_validation_outcomes_do_not_affect_selection(forecasts):
    cutoff = pd.Timestamp("2015-02-15")
    late = forecasts.origin >= pd.Timestamp("2014-01-01")
    forecasts.loc[late, "label_available"] = pd.Timestamp("2030-01-01")
    _, audit = sequential_selection(forecasts)
    changed = forecasts.copy()
    changed.loc[late, "actual"] = -200.0
    _, altered = sequential_selection(changed)
    pd.testing.assert_frame_equal(audit, altered)
    assert audit.loc[audit.selection_date == cutoff, "max_validation_label_date"].max() < cutoff


def test_ties_and_insufficient_validation_fall_back_to_persistence(forecasts):
    forecasts["prediction"] = 5.1
    selected, _ = sequential_selection(forecasts)
    assert selected.selected_candidate.eq("persistence").all()
    selected, audit = sequential_selection(forecasts, start="2011-01-01")
    assert selected.iloc[0].selected_candidate == "persistence"
    assert audit.iloc[0].fallback
    with pytest.raises(ValueError, match="12 validation"):
        sequential_selection(forecasts, lookback=3)


@pytest.mark.parametrize(
    "corruption, message",
    [
        ("missing_model", "identical forecast origins"),
        ("duplicate", "Duplicate"),
        ("different_outcome", "disagree on realized"),
        ("different_missingness", "disagree on realized"),
        ("infinite", "Nonfinite"),
    ],
)
def test_scoring_rejects_invalid_model_comparisons(forecasts, corruption, message):
    if corruption == "missing_model":
        forecasts = forecasts.drop(index=0)
    elif corruption == "duplicate":
        forecasts = pd.concat([forecasts, forecasts.iloc[[0]]], ignore_index=True)
    elif corruption == "different_outcome":
        forecasts.loc[0, "actual"] = 99.0
    elif corruption == "different_missingness":
        forecasts.loc[0, "actual"] = np.nan
    else:
        forecasts.loc[0, "prediction"] = np.inf
    with pytest.raises(ValueError, match=message):
        score(forecasts)


def test_error_contributions_sum_to_one_and_skill_uses_common_baseline(forecasts):
    attribution = error_attribution(forecasts)
    assert np.allclose(attribution.groupby("model").absolute_error_share.sum(), 1.0)
    assert np.allclose(attribution.groupby("model").squared_error_share.sum(), 1.0)
    metrics = score(forecasts).query("period == 'all'").set_index("model")
    assert metrics.loc["ar_linear", "mae_skill_vs_persistence"] == pytest.approx(2 / 3)


def test_rolling_estimation_uses_only_latest_80_available_labels(vintages):
    dataset = build_dataset(vintages)
    predictions = walk_forward(dataset, start=str(dataset.origin.iloc[-1].date()), window=80)
    assert predictions.n_train.eq(80).all()
    assert (predictions.max_training_label_date <= predictions.origin).all()
    with pytest.raises(ValueError, match="at least 80"):
        walk_forward(dataset, window=40)


def test_older_cutoff_cannot_retain_later_research_artifacts(forecasts, tmp_path):
    (tmp_path / "rolling_metrics.csv").write_text("stale later-dated results")
    (tmp_path / "user_notes.txt").write_text("retain unrelated files")
    historical = forecasts.loc[forecasts.origin < pd.Timestamp("2015-01-01")]
    write_research(pd.DataFrame(), historical, tmp_path)
    assert not (tmp_path / "rolling_metrics.csv").exists()
    assert (tmp_path / "user_notes.txt").exists()
    assert "not_available_before_2015" in (tmp_path / "research.json").read_text()
