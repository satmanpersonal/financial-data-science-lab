# Research brief: validating a macroeconomic forecast input

## Decision context

An unemployment forecast could be an input to macroeconomic scenario analysis
or a larger investment-research process. The relevant first question is whether
a proposed model improves forecast quality over an inexpensive, transparent
benchmark on data genuinely available at the decision time.

This project evaluates that first question. It does not estimate asset-return
responses to unemployment, optimize a portfolio, or establish trading value.
Those would require a separate hypothesis and downstream evaluation.

## Evidence chain

1. **Information set:** archived unemployment vintages, with explicit snapshot
   dates and observation ages.
2. **Forecast target:** level three observation months ahead, only when that
   target month has not started at the forecast origin.
3. **Benchmark and candidates:** persistence, autoregressive linear, ridge, and
   gradient boosting, using common chronological origins.
4. **Evaluation:** MAE, RMSE, bias, baseline-relative skill, and paired HAC intervals.
5. **Robustness:** rolling estimation, calendar-block scores, error concentration,
   and an audited past-loss selection rule.
6. **Reproduction:** source hash, fixed reference environment, numerical artifacts,
   adversarial timing tests, and remote Linux CI.

## Questions a reviewer can investigate directly

- **What was known at a forecast date?** Inspect `dataset.csv`, the source column,
  and `max_training_label_date` in `predictions.csv`.
- **Does complexity earn its cost?** Compare MAE skill and uncertainty against
  persistence, then inspect the temporal stability of that comparison.
- **What drives the average result?** Inspect `regime_metrics.csv` and
  `error_attribution.csv`; separate broad performance from a few extreme errors.
- **Could the selection rule have run then?** Verify each selection date against
  the latest validation origin and label date in `selection_audit.csv`.
- **Does using less history help?** Compare `rolling_metrics.csv` to the primary
  expanding-window results on identical origins.
- **What would invalidate the conclusion?** Revisit source reconstruction,
  publication latency, target definition, structural breaks, and sample precision.

## Research discipline and role relevance

BlackRock's public quantitative-investing guidance emphasizes Python, translating
statistical models into code, exploring data sources, critical thinking, and
explaining performance inconsistencies. This project provides inspectable
evidence of those practices at a modest scale; it does not demonstrate
large-scale production experience or satisfy every role requirement.

[Source: BlackRock quantitative investing](https://careers.blackrock.com/students-and-graduates-functions-quantitative-investing).

When discussing the work, explain the actual design choices and measured
limitations. Any application statement should reflect your own understanding
and contributions, including the use of AI assistance where relevant.
