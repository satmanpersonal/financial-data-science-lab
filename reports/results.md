# Research results

Generated from the committed snapshot. Data SHA-256: `d971e59d3ed5f1322a46631743508fb1ad5eee39bfbe12425a641a277fdd9b9a`.

## Question and design

Can lagged unemployment dynamics improve on a no-change forecast of the unemployment
rate three observation months ahead? One sample is a quarterly historical snapshot.
All models use identical forecast origins and targets. Feature values come exclusively
from the origin's archived vintage, with no historical backfilling from later snapshots.
Training labels must be observable by the forecast origin.

Origins span 1965-11-15 to 2025-11-15.
Evaluation starts in 2000 after at least 80 labeled training origins. The 2015 onward
block is reported separately, with fixed hyperparameters and expanding refits.
This is a retrospective research demonstration, not a prospectively sealed holdout.

## Main comparison: 2015 onward

| model | n | mae | rmse | bias |
| --- | --- | --- | --- | --- |
| persistence | 43 | 0.649 | 1.916 | 0.030 |
| gradient_boosting | 43 | 0.692 | 1.932 | 0.039 |
| ridge | 43 | 0.745 | 2.019 | -0.174 |
| ar_linear | 43 | 0.797 | 2.264 | 0.150 |

Lowest observed MAE: **persistence**, **0.649 percentage points**.
This sample ranking is not evidence of durable superiority or investment profitability.

![Model comparison](model_comparison.png)

## All reported periods and shock sensitivity

| period | model | n | mae | rmse | bias |
| --- | --- | --- | --- | --- | --- |
| all | ar_linear | 103 | 0.493 | 1.490 | 0.056 |
| all | gradient_boosting | 103 | 0.448 | 1.277 | -0.008 |
| all | persistence | 103 | 0.435 | 1.275 | -0.004 |
| all | ridge | 103 | 0.463 | 1.330 | -0.074 |
| development_2000_2014 | ar_linear | 60 | 0.275 | 0.366 | -0.011 |
| development_2000_2014 | gradient_boosting | 60 | 0.273 | 0.352 | -0.041 |
| development_2000_2014 | persistence | 60 | 0.282 | 0.399 | -0.028 |
| development_2000_2014 | ridge | 60 | 0.260 | 0.343 | -0.003 |
| evaluation_2015_onward | ar_linear | 43 | 0.797 | 2.264 | 0.150 |
| evaluation_2015_onward | gradient_boosting | 43 | 0.692 | 1.932 | 0.039 |
| evaluation_2015_onward | persistence | 43 | 0.649 | 1.916 | 0.030 |
| evaluation_2015_onward | ridge | 43 | 0.745 | 2.019 | -0.174 |
| excluding_2020_2021 | ar_linear | 95 | 0.242 | 0.322 | 0.003 |
| excluding_2020_2021 | gradient_boosting | 95 | 0.268 | 0.368 | 0.020 |
| excluding_2020_2021 | persistence | 95 | 0.242 | 0.343 | -0.000 |
| excluding_2020_2021 | ridge | 95 | 0.237 | 0.310 | 0.054 |

The 2020–2021 exclusion is a prespecified sensitivity view. The headline comparison
includes these shocks. Positive bias means overprediction. MAE, RMSE, and bias are
all in percentage points; the sample count is the number of quarterly forecast origins.

![Forecasts and cumulative error](forecast_comparison.png)

## Uncertainty in differences from persistence

| period | model | n | mae_difference_vs_persistence | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- |
| all | ar_linear | 103 | 0.058 | -0.049 | 0.164 |
| all | ridge | 103 | 0.028 | -0.051 | 0.106 |
| all | gradient_boosting | 103 | 0.013 | -0.050 | 0.076 |
| evaluation_2015_onward | ar_linear | 43 | 0.148 | -0.089 | 0.386 |
| evaluation_2015_onward | ridge | 43 | 0.096 | -0.070 | 0.262 |
| evaluation_2015_onward | gradient_boosting | 43 | 0.043 | -0.083 | 0.168 |

Negative differences favor the alternative. These are pointwise 95% intervals for
mean paired absolute-loss differences, estimated with an intercept-only OLS and
HAC covariance (four quarterly lags, finite-sample correction, t reference).
They allow local serial correlation and heteroskedasticity under asymptotic conditions;
they do not establish stationarity or robustness to structural breaks. Small samples,
COVID outliers, and multiple comparisons limit inference. These are exploratory,
unadjusted intervals, not simultaneous intervals or model-selection guarantees.

## Latest archived-origin predictions

| origin | target_month | model | prediction | n_train |
| --- | --- | --- | --- | --- |
| 2025-11-15 00:00:00 | 2025-11-01 00:00:00 | persistence | 4.300 | 239 |
| 2025-11-15 00:00:00 | 2025-11-01 00:00:00 | ar_linear | 4.289 | 239 |
| 2025-11-15 00:00:00 | 2025-11-01 00:00:00 | ridge | 4.513 | 239 |
| 2025-11-15 00:00:00 | 2025-11-01 00:00:00 | gradient_boosting | 4.458 | 239 |

These are forecasts at the last included historical snapshot, not necessarily at the
present date. Unknown outcomes remain missing and are excluded from scoring.

## Missing-data audit

Latest source vintage: **2026-08-15**.
Excluded feature origins: **3**. Unobserved targets across all eligible
origins: **1**. All models share the same exclusions.

| origin | reason |
| --- | --- |
| 2026-02-15 | Need 13 consecutive observed months; no imputation is allowed |
| 2026-05-15 | Need 13 consecutive observed months; no imputation is allowed |
| 2026-08-15 | Need 13 consecutive observed months; no imputation is allowed |

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
