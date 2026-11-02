"""Refresh the README's evidence block from generated results, or check freshness."""

import argparse
import json
from pathlib import Path

import pandas as pd

BEGIN = "<!-- BEGIN GENERATED RESULTS -->"
END = "<!-- END GENERATED RESULTS -->"


def render_results(reports: Path) -> str:
    metrics = pd.read_csv(reports / "metrics.csv")
    meta = json.loads((reports / "run.json").read_text())
    all_scores = metrics.query("period == 'all'").set_index("model")
    late = metrics.query("period == 'evaluation_2015_onward'").set_index("model")
    labels = {
        "persistence": "Persistence",
        "ar_linear": "Autoregressive linear",
        "ridge": "Ridge",
        "gradient_boosting": "Gradient boosting",
    }
    lines = [
        "## Results at a glance",
        "",
        "Forecast horizon: three months after the latest **observation month**, with",
        "the target month required to start after the forecast origin. Errors are",
        "percentage points; lower is better. MAE skill is dimensionless, relative to",
        "persistence on identical origins; positive values favor the alternative.",
        "",
        "| Model | MAE, 2000 onward | MAE, 2015 onward | MAE skill, 2015 onward |",
        "| --- | ---: | ---: | ---: |",
    ]
    for model, label in labels.items():
        lines.append(
            f"| {label} | {all_scores.loc[model, 'mae']:.3f} | "
            f"{late.loc[model, 'mae']:.3f} | "
            f"{late.loc[model, 'mae_skill_vs_persistence']:.1%} |"
        )
    lines += [
        "",
        f"There are **{int(all_scores.loc['persistence', 'n'])} scored origins** from 2000 "
        f"onward, including **{int(late.loc['persistence', 'n'])}** from 2015 onward.",
        f"The workbook contains {meta['source_vintages']} vintages through "
        f"{meta['latest_source_vintage']}; {meta['excluded_origins']} origins are excluded "
        "for incomplete or stale feature history.",
        f"Unknown targets among eligible origins: **{meta['unknown_targets']}**. "
        f"The latest eligible origin is **{meta['last_origin']}**.",
        "",
        "This is a historical benchmark, not a current forecast service. Missing targets",
        "are not silently scored or imputed. "
        "See the [exclusion audit](reports/excluded_origins.csv).",
        "",
        "Read the [primary report](reports/results.md) and "
        "[robustness experiments](reports/robustness.md) for uncertainty, window sensitivity,",
        "annual past-loss model selection, and error concentration. Sample rankings",
        "do not establish durable predictive superiority.",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError("README must contain exactly one generated-results marker pair")
    prefix, rest = text.split(BEGIN)
    _, suffix = rest.split(END)
    updated = prefix + BEGIN + "\n" + render_results(root / "reports") + "\n" + END + suffix
    if args.check:
        if updated != text:
            raise SystemExit("README results are stale; run python scripts/update_readme.py")
        print("README numerical evidence is current")
    else:
        readme.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
