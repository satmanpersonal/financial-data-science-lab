# Financial Data Science Lab

[![Research checks](https://github.com/satmanpersonal/financial-data-science-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/satmanpersonal/financial-data-science-lab/actions/workflows/ci.yml)

**Can a more complex model forecast unemployment better than simply predicting no change?**

A reproducible Python research project using the Philadelphia Fed's historical
unemployment snapshots. Each forecast uses the data vintage available at that
date, and each training label must already have been observable. Persistence,
an autoregressive linear benchmark, ridge regression, and gradient boosting
are evaluated on the same expanding-window forecast origins.

**Finding:** persistence has the lowest observed MAE across the full evaluation
and the 2015 onward block. The paired uncertainty intervals include zero, so
the ranking does not establish a statistically decisive winner. Robustness
experiments examine changing economic history and selecting models from past losses.

![Out-of-sample model comparison](reports/model_comparison.png)

<!-- BEGIN GENERATED RESULTS -->
## Results at a glance

Forecast horizon: three months after the latest **observation month**, with
the target month required to start after the forecast origin. Errors are
percentage points; lower is better. MAE skill is dimensionless, relative to
persistence on identical origins; positive values favor the alternative.

| Model | MAE, 2000 onward | MAE, 2015 onward | MAE skill, 2015 onward |
| --- | ---: | ---: | ---: |
| Persistence | 0.437 | 0.660 | 0.0% |
| Autoregressive linear | 0.496 | 0.811 | -23.0% |
| Ridge | 0.467 | 0.762 | -15.6% |
| Gradient boosting | 0.452 | 0.707 | -7.2% |

There are **102 scored origins** from 2000 onward, including **42** from 2015 onward.
The workbook contains 244 vintages through 2026-08-15; 4 origins are excluded for incomplete or stale feature history.
Unknown targets among eligible origins: **1**. The latest eligible origin is **2025-08-15**.

This is a historical benchmark, not a current forecast service. Missing targets
are not silently scored or imputed. See the [exclusion audit](reports/excluded_origins.csv).

Read the [primary report](reports/results.md) and [robustness experiments](reports/robustness.md) for uncertainty, window sensitivity,
annual past-loss model selection, and error concentration. Sample rankings
do not establish durable predictive superiority.
<!-- END GENERATED RESULTS -->

## What the project demonstrates

- **Data engineering:** validated XLSX ingestion, an immutable source snapshot,
  attribution, a download manifest, and checksum verification.
- **Temporal research design:** features built from each origin's own vintage;
  training gated by actual archived label availability; no random train/test split.
- **Model comparison:** simple baselines alongside regularized linear and nonlinear
  models, with preprocessing fitted only on available training observations.
- **Statistical judgment:** common evaluation samples, MAE/RMSE/bias, explicit shock
  sensitivity, error concentration, and exploratory HAC intervals with their assumptions documented.
- **Model selection:** an annual past-loss selector with candidate-level availability
  audits, plus an 80-origin rolling estimation comparison. Both are labeled exploratory.
- **Engineering discipline:** packaged CLI, locked environment, regression tests,
  automated numerical reproduction, and GitHub Actions.

For a short explanation of the research decision and inspectable evidence, read the
[research brief](docs/research-brief.md). The [review log](docs/review.md) records
the weaknesses found, changes made, and remaining limits.

![Training-window sensitivity and sequential model selection](reports/research_diagnostics.png)

## Reproduce locally

Use Python **3.13** for the locked reference environment. No API key is needed.

```console
git clone https://github.com/satmanpersonal/financial-data-science-lab.git
cd financial-data-science-lab
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Install and run:

```console
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
python -m pip check
macrocast run
pytest -q
```

The evaluation uses the committed snapshot and makes no network requests.
Installation requires package downloads. For a new data snapshot, use
`macrocast fetch --refresh` and review the resulting changes.

To restrict the information set to older snapshots:

```console
macrocast run --as-of 2019-12-31 --output reports-2019
```

To verify numerical reproduction without replacing the committed report:

```console
macrocast run --output reproduced-reports
python scripts/check_reproduction.py reports reproduced-reports
python scripts/update_readme.py --check
ruff check .
ruff format --check .
```

CI performs the same checks on Linux. Numeric results are compared with
`rtol=1e-7, atol=1e-8`; rendered PNG bytes are not compared across platforms.

## Navigate the repository

| Path | Contents |
| --- | --- |
| [`src/macrocast/data.py`](src/macrocast/data.py) | Source retrieval, validation, provenance |
| [`src/macrocast/dataset.py`](src/macrocast/dataset.py) | Vintage features and label-availability clock |
| [`src/macrocast/evaluate.py`](src/macrocast/evaluate.py) | Models, expanding windows, metrics, HAC comparisons |
| [`reports/results.md`](reports/results.md) | Generated research note and figures |
| [`reports/predictions.csv`](reports/predictions.csv) | Forecast-level results and training audit fields |
| [`reports/excluded_origins.csv`](reports/excluded_origins.csv) | Missing-feature exclusions |
| [`reports/run.json`](reports/run.json) | Environment, snapshot hash, configuration |
| [`reports/robustness.md`](reports/robustness.md) | Rolling estimation, sequential selection, error attribution |
| [`reports/selection_audit.csv`](reports/selection_audit.csv) | Candidate scores and label-availability dates at each annual selection |
| [`docs/research-brief.md`](docs/research-brief.md) | Decision context and questions a reviewer can investigate |
| [`docs/review.md`](docs/review.md) | Review findings, resolutions, and evidence limits |
| [`docs/methodology.md`](docs/methodology.md) | Research design and limitations |
| [`docs/data.md`](docs/data.md) | Source documentation and update policy |
| [`tests/`](tests) | Leakage, availability, parser, metrics, and report checks |

## Limits and next experiments

The information set contains only lagged unemployment. The label is the first
archived quarterly snapshot containing the target, **not necessarily the original
BLS release**. Source snapshot dates approximate information availability without
intraday publication latency. The small quarterly sample and structural breaks
limit statistical inference. The 2015 onward block is retrospective, not a
prospectively sealed holdout.

Useful next experiments are adding release-timed employment and yield-curve
vintages and preregistering a hyperparameter-selection protocol. The current
annual selector chooses among fixed candidates; it does not tune their parameters.
Any extension should preserve the information clock and keep the simple baseline visible.

This is independent educational research with no BlackRock or Federal Reserve
affiliation. It models an economic indicator and makes no investment-return claims.
Original code is MIT licensed; source data is separately attributed in
[data provenance](docs/data.md).
