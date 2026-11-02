# Research and engineering review

Reviewed against the public repository at baseline commit `5d24a8e`.
The scope is predictive validity, reproducibility, and communication of evidence.
This is an internal project assessment, not an external peer-review endorsement.

## Findings and resolutions

| Finding | Consequence | Resolution |
| --- | --- | --- |
| Scoring grouped each model independently without enforcing sample alignment | Missing or duplicate forecasts could produce an unfair comparison | Validate model/origin uniqueness, full common coverage, identical outcomes and label status, finite forecasts, and available training labels before scoring |
| Data-age changes could turn an intended forecast into a nowcast | November 2025's August history targeted November, a month already in progress | Require target month to start after the origin; export observation age; record excluded origins |
| Nonnumeric source values were coerced to missing | A corrupted input could silently alter the research sample | Reject malformed dates and nonnumeric values explicitly |
| Only expanding estimation was shown | Conclusions might depend on retaining distant economic history | Add a fixed 80-labeled-origin rolling-window sensitivity on identical forecast origins |
| Selecting a model from the final leaderboard would use hindsight | A model-choice story could imply an untested deployable rule | Add an annual selector based only on matured prior out-of-sample losses, with a dated candidate-level audit and future-outcome perturbation tests |
| Aggregate MAE and one shock exclusion obscured error concentration | A few shocks could drive model rankings | Add contiguous calendar-block scores and each origin's contribution to absolute and squared errors |
| README values were manually copied | Refreshing data could leave misleading headline numbers | Generate the evidence block from artifacts and check freshness in CI |
| Runtime used an undeclared transitive dependency | Packaging depended on another library installing threadpoolctl | Declare threadpoolctl as a direct dependency |
| The numerical provenance did not identify the implementation | Artifacts could be mistaken for results from a different code revision | Record a deterministic package-source SHA-256 in run metadata and verify it during reproduction |
| CI used old mutable action tags | Action code could change without an explicit repository update | Pin current official action releases to verified commit SHAs |

## Interpretation after improvement

The original four candidate settings remain fixed. Tightening target eligibility
changes the common scoring sample and therefore its numerical results; this is
documented rather than presented as a performance improvement. The original
version can be recovered from Git history.

The selector, rolling-window comparison, and error diagnostics were conceived
after inspection of the first results. Past-only implementation prevents
observation-level leakage, but cannot remove researcher-level adaptation.
They are exploratory, not confirmatory evidence on an untouched dataset.

## Remaining limits

- Small quarterly sample, one indicator, one country.
- Archived vintages approximate information availability; they are not an
  intraday release-time database and may contain reconstructed history.
- No exogenous macro predictors, calibrated uncertainty intervals, or economic
  decision-loss function.
- No prospective deployment or demonstrated investment profitability.
- Pointwise HAC intervals are approximate and not multiplicity-adjusted.
- Calendar-block explanations are descriptive and not causal attribution.

A defensible next study would freeze an extension protocol before acquiring
additional vintage-aware predictors and evaluating genuinely new observations.
