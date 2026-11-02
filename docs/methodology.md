# Research protocol

## Question

Does additional model complexity improve a three-observation-month-ahead forecast
of the US seasonally adjusted unemployment rate relative to persistence?
The target is an economic indicator relevant to macroeconomic scenario analysis,
not an asset return. This project does not test an investment strategy.

## Information clock

1. Each origin is a Philadelphia Fed quarterly vintage dated February, May,
   August, or November 15, following the source documentation.
2. Construct features only from that vintage's unemployment history. Do not
   replace older observations with today's revised values.
3. Let `t` be the last observation month in that vintage. Forecast the level at
   `t + 3 months`. Usually a February vintage ends in January and predicts April.
   Require the target month to start strictly after the origin. Stale histories
   that would imply a nowcast or backcast are excluded and audited.
4. The target is the value in the **first subsequent archived quarterly vintage**
   containing that target month. The label-availability date is that vintage's date.
   It is not assumed to be the original BLS release value or release date.
5. At origin `s`, train only on earlier origins with `label_available <= s`.
   A label first appearing in the current snapshot may be used at that origin.

This approximates end-of-snapshot-date information, not intraday publication.
Export `data_age_months` to make unusual publication lags visible. Late publication
or source reconstruction errors are not modeled. Three months
is the observation horizon, not three months after the forecast's calendar date.
The typical January-to-April example predicts April's rate from February 15;
that rate is usually released in May.

## Feature specification

Use the latest unemployment rate; levels lagged 1, 3, 6, and 12 months;
3- and 12-month changes; and the sample standard deviation of the last 12
monthly changes. Require 13 consecutive observed months, rejecting gaps.
Origins with feature gaps are excluded and recorded in an audit CSV. The raw
vintages are still used to find labels available to other eligible origins.
No imputation, future exogenous variables, seasonal dummies, or revised
full-sample features are used.

## Models

| Model | Specification |
| --- | --- |
| Persistence | Predict the last observed level |
| Autoregressive linear benchmark | OLS of the future three-month change on an intercept and trailing three-month change |
| Ridge | Standardized eight-feature linear regression of future change; alpha = 10 |
| Gradient boosting | Histogram gradient boosting of future change; 100 iterations, 7 leaves, 12 minimum observations per leaf, learning rate 0.05, L2 = 10, seed 42 |

All learned models predict the change and add the current level back. Scaling is
fitted separately on each training window. Boosting has `early_stopping=False`
so no random validation split is introduced. Predictions are not clipped to
physical bounds; implausible predictions remain visible as model failures.
Hyperparameters are fixed and no evaluation-driven tuning is performed.

## Evaluation

- Expanding windows with at least 80 labeled quarterly training rows.
- Forecast origins from 2000 onward; refit at every origin.
- Report 2000–2014 and 2015 onward separately, alongside the full evaluation.
  These are retrospective evaluation blocks, not a sealed prospective holdout.
- Same origins and target vintages for all models; unknown outcomes remain NaN.
- Primary metric: MAE in percentage points. Also report RMSE and signed bias.
- MAE skill is `1 - model MAE / persistence MAE` on identical scored origins.
  Positive values improve on persistence; a zero-error baseline makes skill undefined.
- Reject duplicate forecasts, inconsistent targets, unequal model coverage,
  nonfinite predictions, and training labels dated after the forecast origin.
- Report 2020–2021 exclusion only as a named sensitivity; include shocks in
  the main results. This specification was chosen before running the comparison.
- Compare paired absolute-loss differences against persistence using an
  intercept-only statsmodels OLS with HAC covariance, four ordered forecast-origin lags,
  small-sample correction, and t-based pointwise 95% confidence intervals.

The inference assumes sufficient weak dependence and finite moments. Structural
breaks, a short evaluation sample, and shock outliers can undermine those
approximations. Intervals are exploratory and unadjusted for multiple comparisons.
Do not interpret a favorable mean or interval as proof of a profitable strategy.

## Reproduction and audit

`reports/dataset.csv` exposes every feature row and label-availability date.
`reports/predictions.csv` includes each origin's training count and maximum
training-label date. `reports/run.json` records package versions, the data hash,
and a package-source hash normalized across platform line endings.
Tests mutate future vintages and verify earlier predictions remain unchanged.

## Exploratory extensions after the initial results

The fixed settings above are unchanged. The following analyses were designed after
the first results were inspected; none creates a new confirmatory holdout.

- **Rolling estimation:** retain the most recent 80 observable labeled origins
  at every forecast date. Compare on the exact primary evaluation sample.
- **Sequential model selection:** from 2015 onward, choose among the four fixed
  candidates at the first eligible origin of each calendar year. Use MAE on the
  latest 20 prior out-of-sample forecast origins with labels known by that selection
  date. Require 12 validation origins; otherwise use persistence. Break exact ties
  in declared model order, persistence first. Freeze the choice until the next
  calendar year; each underlying model continues its normal refitting.
- **Error diagnostics:** decompose absolute and squared error by origin; report
  calendar blocks 2000–2014, 2015–2019, 2020–2021, and 2022 onward. These are
  descriptive blocks, not hindsight-defined switches in the forecasting algorithm.

The selector is a prequential model-selection experiment, not nested parameter
tuning. Its candidate predictions were each generated with past-only training,
and its own scoring window uses only matured past targets. An audit records the
latest validation origin and label date. Researcher-level adaptation remains,
so no additional significance claim is attached to the selector's result.

Possible extensions include carefully timed employment or yield-curve vintages,
a preregistered tuning protocol, and calibrated forecast intervals. Each should
preserve the same information clock.

## Implementation references

- [scikit-learn gradient boosting API](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html)
- [statsmodels robust covariance API](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html)
