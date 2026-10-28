"""Runs every query in sql/ against the CSVs with DuckDB and saves each result
to results/<query>.csv. Prints a short preview of each.

Usage: python scripts/run_analysis.py
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent


def connect() -> duckdb.DuckDBPyConnection:
    os.chdir(ROOT)  # the load script uses paths relative to the repo root
    con = duckdb.connect(str(ROOT / "revops.duckdb"))
    con.execute((ROOT / "sql" / "00_load.sql").read_text())
    return con


def main() -> None:
    con = connect()
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    for path in sorted((ROOT / "sql").glob("[0-9]*.sql")):
        if path.name.startswith("00_"):
            continue
        df = con.execute(path.read_text()).df()
        df.to_csv(out / f"{path.stem}.csv", index=False)
        print(f"\n=== {path.stem} ({len(df)} rows)")
        print(df.head(12).to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
