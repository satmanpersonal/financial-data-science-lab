# Data provenance and rights

**Publisher:** Federal Reserve Bank of Philadelphia, Real-Time Data Set for
Macroeconomists. Underlying unemployment observations originate from the US
Bureau of Labor Statistics.

- [Dataset overview](https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/real-time-data-set-for-macroeconomists)
- [Unemployment data and documentation](https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/ruc)
- [Source workbook](https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/real-time-data/data-files/xlsx/rucQvMd.xlsx)
- [Specific unemployment documentation](https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/real-time-data/data-files/RUC/specific_documentation_RUC.pdf)

The workbook stores monthly unemployment observations in percentage points,
seasonally adjusted, across quarterly historical vintages. A column such as
`RUC00Q1` represents the February 15, 2000 snapshot, not 2000:Q1 observation data.
The committed download manifest records the source URL, retrieval time, byte
count, and SHA-256 digest. The pipeline verifies this digest before evaluation.

The source is available without an API key. The archived workbook is retained
for reproducibility with full attribution; no endorsement or affiliation is
implied. The repository's MIT license applies to original code, not third-party
source data. Source materials remain subject to their publisher's terms.

## Updating

```console
macrocast fetch --refresh
macrocast run
```

Refresh explicitly replaces the workbook and its provenance manifest. Review
the data and report changes together. It changes the research snapshot and may
change historical results. Ordinary `macrocast run` never downloads data.

## Known limitations

- Quarterly snapshots are less granular than BLS releases and may already
  include revisions to a target's first release.
- Source documentation discusses historical deep-history reconstruction.
  Availability dating therefore follows the publisher's archived snapshots.
- Missing entries are not forward-filled; impossible rates and future-dated
  observations cause validation failure. Feature-history gaps exclude the affected
  origins, with an explicit audit in `reports/excluded_origins.csv`.
- The committed workbook lacks October 2025. This excludes three 2026 feature
  origins and leaves a forecast targeting October 2025 unscored. The report shows
  the most recent eligible historical origin rather than inventing a current forecast.
- This is a single-country, single-indicator benchmark with a modest sample.
