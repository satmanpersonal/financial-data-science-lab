import numpy as np
import pandas as pd
import pytest

from macrocast.data import load_vintages, vintage_date
from macrocast.dataset import FEATURES, build_dataset, features, training_rows
from macrocast.evaluate import predict


@pytest.mark.parametrize(
    "name, expected",
    [
        ("RUC65Q4", "1965-11-15"),
        ("RUC00Q1", "2000-02-15"),
        ("RUC2026Q3", "2026-08-15"),
    ],
)
def test_vintage_dates_match_publisher(name, expected):
    assert vintage_date(name) == pd.Timestamp(expected)


def test_future_revisions_cannot_change_past_features_or_predictions(vintages):
    original = build_dataset(vintages)
    origin = original.origin.iloc[85]
    mutated = {date: values + (20 if date > origin else 0) for date, values in vintages.items()}
    changed = build_dataset(mutated)
    pd.testing.assert_frame_equal(
        original.loc[original.origin <= origin, FEATURES],
        changed.loc[changed.origin <= origin, FEATURES],
    )
    train_before = training_rows(original, origin)
    train_after = training_rows(changed, origin)
    pd.testing.assert_frame_equal(train_before, train_after)
    row_before = original.loc[original.origin == origin]
    row_after = changed.loc[changed.origin == origin]
    assert predict(train_before, row_before) == predict(train_after, row_after)


def test_labels_use_first_future_snapshot_not_latest_revised_value(vintages):
    dataset = build_dataset(vintages)
    first = dataset.iloc[0]
    next_origin = sorted(vintages)[1]
    assert first.label_available == next_origin
    assert first.target == vintages[next_origin].loc[first.target_month]
    assert first.target != vintages[max(vintages)].loc[first.target_month]


def test_unobserved_targets_remain_unscored(vintages):
    dataset = build_dataset(vintages)
    assert np.isnan(dataset.iloc[-1].target)
    assert pd.isna(dataset.iloc[-1].label_available)


def test_training_excludes_labels_not_yet_observable(vintages):
    dataset = build_dataset(vintages)
    origin = dataset.origin.iloc[85]
    dataset.loc[84, "label_available"] = origin + pd.DateOffset(months=6)
    train = training_rows(dataset, origin)
    assert 84 not in train.index
    assert (train.origin < origin).all()
    assert (train.label_available <= origin).all()


def test_missing_month_is_rejected_instead_of_imputed(vintages):
    series = vintages[min(vintages)].copy()
    series = series.drop(series.index[-3])
    with pytest.raises(ValueError, match="consecutive"):
        features(series)


def test_feature_gaps_are_excluded_and_audited_but_labels_still_use_raw_vintages(vintages):
    last_origin = max(vintages)
    removed_month = vintages[last_origin].index[-3]
    vintages[last_origin] = vintages[last_origin].drop(removed_month)
    dataset = build_dataset(vintages)
    assert last_origin not in set(dataset.origin)
    assert dataset.attrs["exclusions"][0]["origin"] == str(last_origin.date())
    assert dataset.iloc[-1].label_available == last_origin


def test_snapshot_manifest_matches_committed_workbook():
    import json
    from pathlib import Path

    from macrocast.data import checksum

    raw = Path(__file__).resolve().parents[1] / "data/raw/rucQvMd.xlsx"
    manifest = json.loads(raw.with_suffix(".manifest.json").read_text())
    assert checksum(raw) == manifest["sha256"]
    vintages = load_vintages(raw)
    dataset = build_dataset(vintages)
    assert len(dataset) + len(dataset.attrs["exclusions"]) == len(vintages)
    assert (dataset.last_observation < dataset.origin).all()


def test_workbook_parser_drops_sentinels_and_rejects_future_observations(tmp_path):
    path = tmp_path / "source.xlsx"
    pd.DataFrame(
        {"DATE": ["1965:M11", "1965:M12", "1966:M1"], "RUC66Q1": [-999, 4.1, 4.0]}
    ).to_excel(path, index=False)
    series = load_vintages(path)[pd.Timestamp("1966-02-15")]
    assert len(series) == 2
    pd.DataFrame({"DATE": ["1966:M2"], "RUC66Q1": [4.0]}).to_excel(path, index=False)
    with pytest.raises(ValueError, match="future"):
        load_vintages(path)
