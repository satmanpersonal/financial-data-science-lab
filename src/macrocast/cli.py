"""Command line interface: fetch explicitly, evaluate offline by default."""

import argparse
import json
from pathlib import Path

import pandas as pd

from macrocast.data import checksum, download, load_vintages
from macrocast.dataset import build_dataset
from macrocast.evaluate import walk_forward
from macrocast.report import write_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch", help="Download source snapshot; refresh must be explicit")
    fetch.add_argument("--refresh", action="store_true")
    fetch.add_argument("--raw", type=Path, default=Path("data/raw/rucQvMd.xlsx"))
    run = sub.add_parser("run", help="Run expanding-window evaluation on the local snapshot")
    run.add_argument("--raw", type=Path, default=Path("data/raw/rucQvMd.xlsx"))
    run.add_argument("--output", type=Path, default=Path("reports"))
    run.add_argument("--as-of", default=None, help="Optional YYYY-MM-DD vintage cutoff")
    args = parser.parse_args()
    if args.command == "fetch":
        download(args.raw, refresh=args.refresh)
        print(f"Snapshot available: {args.raw}")
        return
    manifest = args.raw.with_suffix(".manifest.json")
    if not manifest.exists():
        raise ValueError("Missing provenance manifest: use 'macrocast fetch' for a new snapshot")
    if checksum(args.raw) != json.loads(manifest.read_text())["sha256"]:
        raise ValueError("Snapshot checksum differs from provenance manifest")
    vintages = load_vintages(args.raw)
    if args.as_of:
        cutoff = pd.Timestamp(args.as_of)
        vintages = {date: values for date, values in vintages.items() if date <= cutoff}
    if not vintages:
        raise ValueError("No vintages remain after cutoff")
    dataset = build_dataset(vintages)
    predictions = walk_forward(dataset)
    write_report(dataset, predictions, args.raw, args.output)
    print(f"Evaluated {predictions.origin.nunique()} origins; report: {args.output / 'results.md'}")


if __name__ == "__main__":
    main()
