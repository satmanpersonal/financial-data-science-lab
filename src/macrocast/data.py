"""Download and validate Philadelphia Fed quarterly unemployment snapshots."""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

SOURCE_URL = (
    "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/"
    "real-time-data/data-files/xlsx/rucQvMd.xlsx"
)
SOURCE_PAGE = "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/ruc"


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_checksum() -> str:
    """Fingerprint package source independently of platform line endings and Git state."""
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode("utf-8") + b"\0")
        digest.update(path.read_text(encoding="utf-8").encode("utf-8") + b"\0")
    return digest.hexdigest()


def record_manifest(path: Path) -> None:
    manifest = {
        "source_url": SOURCE_URL,
        "source_page": SOURCE_PAGE,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": checksum(path),
        "bytes": path.stat().st_size,
        "units": "percentage points, seasonally adjusted",
        "publisher": "Federal Reserve Bank of Philadelphia; underlying series from BLS",
    }
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def download(path: Path, *, refresh: bool = False) -> None:
    """Refresh is explicit: an existing snapshot must never change silently."""
    if path.exists() and not refresh:
        return
    request = Request(SOURCE_URL, headers={"User-Agent": "macrocast-lab/0.1 research"})
    with urlopen(request, timeout=60) as response:
        payload = response.read()
    if not payload.startswith(b"PK"):
        raise ValueError("Source did not return an XLSX archive")
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate = path.with_suffix(".download.xlsx")
    candidate.write_bytes(payload)
    try:
        load_vintages(candidate)
        candidate.replace(path)
    finally:
        candidate.unlink(missing_ok=True)
    record_manifest(path)


def vintage_date(name: str) -> pd.Timestamp:
    match = re.fullmatch(r"RUC(\d{2}|\d{4})Q([1-4])", name.upper())
    if not match:
        raise ValueError(f"Unexpected vintage column: {name}")
    year = int(match[1])
    if year < 100:
        year += 1900 if year >= 65 else 2000
    # The publisher documents snapshots on Feb/May/Aug/Nov 15.
    return pd.Timestamp(year=year, month=3 * int(match[2]) - 1, day=15)


def load_vintages(path: Path) -> dict[pd.Timestamp, pd.Series]:
    raw = pd.read_excel(path, engine="openpyxl")
    month = (
        raw.iloc[:, 0]
        .astype(str)
        .str.strip()
        .str.replace(":M", "-", regex=False)
        .str.replace(":", "-", regex=False)
    )
    dates = pd.to_datetime(month, format="%Y-%m", errors="coerce")
    valid = dates.notna()
    nonempty_dates = raw.iloc[:, 0].notna()
    if (nonempty_dates & ~valid).any():
        raise ValueError("Unrecognized observation date in workbook")
    if dates[valid].duplicated().any():
        raise ValueError("Duplicate observation months")
    result = {}
    for column in raw.columns[1:]:
        if not re.fullmatch(r"RUC\d{2,4}Q[1-4]", str(column).upper()):
            continue
        origin = vintage_date(str(column))
        values = pd.to_numeric(raw.loc[valid, column], errors="coerce")
        if (raw.loc[valid, column].notna() & values.isna()).any():
            raise ValueError(f"Nonnumeric observation in {column}")
        series = pd.Series(values.to_numpy(), index=pd.DatetimeIndex(dates[valid])).dropna()
        # Blank/sentinel entries are missing, never forward-filled.
        series = series.loc[series > -900].sort_index()
        if series.empty:
            continue
        if not series.between(0, 100).all():
            raise ValueError(f"Invalid unemployment value in {column}")
        if series.index.max() >= origin.replace(day=1):
            raise ValueError(f"Vintage {column} contains a contemporaneous/future observation")
        result[origin] = series
    if not result:
        raise ValueError("No valid RUC vintage columns")
    return dict(sorted(result.items()))
