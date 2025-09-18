import os
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from typing import List

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/billing.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

REQUIRED_COLUMNS = [
    "invoice_month","account_id","subscription","service","resource_group",
    "resource_id","region","usage_qty","unit_cost","cost"
]

def read_input(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    if p.suffix.lower() in (".csv", ".txt"):
        df = pd.read_csv(p)
    elif p.suffix.lower() in (".json",):
        df = pd.read_json(p, lines=False)
    else:
        raise ValueError("Unsupported file type: " + p.suffix)
    return df

def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    ## Normalize column names
    df.columns = [c.strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df

def quality_checks(df: pd.DataFrame) -> List[str]:
    issues = []
    # 1. Checking Null Values
    nulls = df.isnull().sum()
    null_cols = nulls[nulls > 0].to_dict()
    if null_cols:
        issues.append(f"Nulls found: {null_cols}")
    # 2. Checking Negative costs
    if "cost" in df.columns and (df["cost"].dropna() < 0).any():
        issues.append("Negative values in 'cost' column.")
    # 3) Duplicate resource_id + invoice_month
    if df.duplicated(subset=["resource_id", "invoice_month"]).any():
        issues.append("Duplicate rows by (resource_id, invoice_month).")
    # 4) Cost mismatch: usage_qty * unit_cost vs cost (tolerance)
    if {"usage_qty","unit_cost","cost"}.issubset(df.columns):
        calc = (df["usage_qty"].fillna(0) * df["unit_cost"].fillna(0))
        # allowing small rounding differences
        mismatch = (~np.isclose(calc, df["cost"].fillna(0), rtol=1e-3, atol=1e-2))
        if mismatch.any():
            cnt = mismatch.sum()
            issues.append(f"{int(cnt)} rows where usage_qty * unit_cost != cost (possible data issue).")
    return issues

def ingest_file(path: str, if_exists: str = "append"):
    df = read_input(path)
    df = ensure_columns(df)
    # coerce numeric columns
    df["usage_qty"] = pd.to_numeric(df["usage_qty"], errors="coerce")
    df["unit_cost"] = pd.to_numeric(df["unit_cost"], errors="coerce")
    df["cost"] = pd.to_numeric(df["cost"], errors="coerce")
    issues = quality_checks(df)
    if issues:
        print("Data quality issues detected:")
        for i in issues:
            print("  -", i)
    else:
        print("No data-quality issues detected.")
    # Write to DB
    Path("data").mkdir(parents=True, exist_ok=True)
    df.to_sql("billing", engine, if_exists=if_exists, index=False)
    print(f"Ingested {len(df)} rows into 'billing' table (if_exists={if_exists}).")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest billing CSV/JSON into DB")
    parser.add_argument("--input", "-i", required=True, help="path to CSV or JSON file")
    args = parser.parse_args()
    ingest_file(args.input)
