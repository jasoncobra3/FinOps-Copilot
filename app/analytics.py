# app/analytics.py
"""
Enrichment + KPI utilities for ai-cost-copilot.
Usage:
    python -m app.analytics enrich-check
    python -m app.analytics monthly-owner --month 2025-08
    python -m app.analytics monthly-env --month 2025-08
    python -m app.analytics owner-coverage --month 2025-08
    python -m app.analytics six-trend
    python -m app.analytics top-n --month 2025-08 --n 10
    python -m app.analytics unit-changes --threshold 0.20
    python -m app.analytics export-csvs --out data/exports
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import argparse
from pathlib import Path
import json
import pandas as pd
from app.models import engine

CACHE_DIR = Path("data/cache")

def load_tables():
    """Return billing_df, resources_df (resources_df may be empty if table missing)."""
    try:
        billing = pd.read_sql_query("SELECT * FROM billing", engine)
    except Exception as e:
        raise RuntimeError("Could not read billing table. Ensure billing was ingested. Error: " + str(e))
    try:
        resources = pd.read_sql_query("SELECT * FROM resources", engine)
    except Exception:
        # resources may not exist yet
        resources = pd.DataFrame(columns=["resource_id", "owner", "env", "tags_json"])
    return billing, resources

def normalize_resource_ids(df):
    """Normalize resource_id column to consistent string form."""
    if "resource_id" not in df.columns:
        return df
    df["resource_id"] = df["resource_id"].astype(str).str.strip()
    # convert empty strings to NaN then keep as NaN
    df.loc[df["resource_id"] == "nan", "resource_id"] = None
    return df

def enrich_billing():
    """Left join billing -> resources and fill missing owner/env with 'unassigned'."""
    billing, resources = load_tables()
    billing = normalize_resource_ids(billing)
    resources = normalize_resource_ids(resources)

    # ensure numeric columns
    for c in ["usage_qty", "unit_cost", "cost"]:
        if c in billing.columns:
            billing[c] = pd.to_numeric(billing[c], errors="coerce").fillna(0.0)

    # perform left join
    enriched = billing.merge(
        resources[["resource_id", "owner", "env", "tags_json"]],
        how="left",
        on="resource_id",
        validate="m:1"  # many billing rows -> one resource row
    )
    enriched["owner"] = enriched["owner"].fillna("unassigned")
    enriched["env"] = enriched["env"].fillna("unassigned")
    return enriched

def monthly_cost_by_owner(month):
    df = enrich_billing()
    dfm = df[df["invoice_month"].astype(str) == str(month)]
    res = dfm.groupby("owner", dropna=False)["cost"].sum().reset_index().sort_values("cost", ascending=False)
    return res

def monthly_cost_by_env(month):
    df = enrich_billing()
    dfm = df[df["invoice_month"].astype(str) == str(month)]
    res = dfm.groupby("env", dropna=False)["cost"].sum().reset_index().sort_values("cost", ascending=False)
    return res

def owner_coverage(month):
    df = enrich_billing()
    dfm = df[df["invoice_month"].astype(str) == str(month)]
    total_cost = dfm["cost"].sum()
    assigned_cost = dfm.loc[dfm["owner"] != "unassigned", "cost"].sum()
    coverage_pct = (assigned_cost / total_cost) if total_cost > 0 else 0.0
    return {
        "month": month,
        "total_cost": float(total_cost),
        "assigned_cost": float(assigned_cost),
        "coverage_pct": float(round(coverage_pct, 4))
    }

def six_month_trend(group_by="owner"):
    df = enrich_billing()
    months = sorted(df["invoice_month"].astype(str).unique())
    if len(months) == 0:
        return pd.DataFrame()
    last6 = months[-6:]
    sub = df[df["invoice_month"].astype(str).isin(last6)]
    agg = sub.groupby(["invoice_month", group_by])["cost"].sum().reset_index()
    pivot = agg.pivot(index="invoice_month", columns=group_by, values="cost").fillna(0).sort_index()
    return pivot

def top_n_cost_drivers(month, n=10):
    df = enrich_billing()
    dfm = df[df["invoice_month"].astype(str) == str(month)]
    agg = dfm.groupby(["resource_id", "service", "resource_group", "owner"], dropna=False)["cost"].sum().reset_index()
    agg = agg.sort_values("cost", ascending=False).head(n)
    return agg

def unit_cost_changes(threshold_pct=0.2):
    df = enrich_billing()
    # compute average unit_cost per resource per month
    if "unit_cost" not in df.columns:
        return pd.DataFrame()
    agg = df.groupby(["resource_id", "invoice_month"])["unit_cost"].mean().reset_index()
    agg = agg.sort_values(["resource_id", "invoice_month"])
    agg["prev_unit_cost"] = agg.groupby("resource_id")["unit_cost"].shift(1)
    agg = agg.dropna(subset=["prev_unit_cost"])
    # avoid divide-by-zero
    agg = agg[agg["prev_unit_cost"] != 0]
    agg["pct_change"] = (agg["unit_cost"] - agg["prev_unit_cost"]) / agg["prev_unit_cost"]
    flagged = agg[agg["pct_change"].abs() >= float(threshold_pct)].copy()
    # add readable columns
    flagged["pct_change"] = flagged["pct_change"].round(4)
    return flagged.sort_values("pct_change", ascending=False)

def export_csvs(out_dir="data/exports"):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    billing, _ = load_tables()
    months = sorted(billing["invoice_month"].astype(str).unique())
    if not months:
        print("No months found in billing table.")
        return
    latest = months[-1]
    # export monthly by owner and env for latest month
    by_owner = monthly_cost_by_owner(latest)
    by_env = monthly_cost_by_env(latest)
    by_owner.to_csv(Path(out_dir) / f"monthly_by_owner_{latest}.csv", index=False)
    by_env.to_csv(Path(out_dir) / f"monthly_by_env_{latest}.csv", index=False)
    # top resources
    top = top_n_cost_drivers(latest, n=50)
    top.to_csv(Path(out_dir) / f"top_resources_{latest}.csv", index=False)
    # unit changes
    changes = unit_cost_changes(0.2)
    changes.to_csv(Path(out_dir) / f"unit_cost_changes.csv", index=False)
    print("Exported CSVs to", out_dir)



def cache_month_results(month):
    """Compute KPIs and cache them as CSVs for reuse."""
    out_dir = CACHE_DIR / month
    out_dir.mkdir(parents=True, exist_ok=True)

    # compute
    owner_df = monthly_cost_by_owner(month)
    env_df = monthly_cost_by_env(month)
    coverage = owner_coverage(month)

    # save
    owner_df.to_csv(out_dir / "owner.csv", index=False)
    env_df.to_csv(out_dir / "env.csv", index=False)
    with open(out_dir / "coverage.json", "w") as f:
        json.dump(coverage, f)

def load_month_results(month):
    """Load KPIs from cache if present, else return None."""
    out_dir = CACHE_DIR / month
    owner_file = out_dir / "owner.csv"
    env_file = out_dir / "env.csv"
    cov_file = out_dir / "coverage.json"

    if owner_file.exists() and env_file.exists() and cov_file.exists():
        owner_df = pd.read_csv(owner_file)
        env_df = pd.read_csv(env_file)
        with open(cov_file) as f:
            coverage = json.load(f)
        return owner_df, env_df, coverage
    return None

def _cli():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("enrich-check")
    p1 = sub.add_parser("monthly-owner")
    p1.add_argument("--month", required=True)
    p2 = sub.add_parser("monthly-env")
    p2.add_argument("--month", required=True)
    p3 = sub.add_parser("owner-coverage")
    p3.add_argument("--month", required=True)
    p4 = sub.add_parser("six-trend")
    p4.add_argument("--group_by", default="owner")
    p5 = sub.add_parser("top-n")
    p5.add_argument("--month", required=True)
    p5.add_argument("--n", type=int, default=10)
    p6 = sub.add_parser("unit-changes")
    p6.add_argument("--threshold", type=float, default=0.2)
    p7 = sub.add_parser("export-csvs")
    p7.add_argument("--out", default="data/exports")

    args = parser.parse_args()
    if args.cmd == "enrich-check":
        billing, resources = load_tables()
        enriched = enrich_billing()
        print("billing rows:", len(billing))
        print("resources rows:", len(resources))
        print("enriched rows:", len(enriched))
        # totals check
        tot_before = billing["cost"].sum()
        tot_after = enriched["cost"].sum()
        print(f"total cost before join: {tot_before:.4f}")
        print(f"total cost after join:  {tot_after:.4f}")
        # show sample
        print("\nSample enriched rows:")
        print(enriched[["invoice_month","resource_id","owner","env","cost"]].head(10).to_string(index=False))
    elif args.cmd == "monthly-owner":
        df = monthly_cost_by_owner(args.month)
        print(df.to_string(index=False))
    elif args.cmd == "monthly-env":
        df = monthly_cost_by_env(args.month)
        print(df.to_string(index=False))
    elif args.cmd == "owner-coverage":
        out = owner_coverage(args.month)
        print(out)
    elif args.cmd == "six-trend":
        df = six_month_trend(args.group_by)
        print(df.to_string())
    elif args.cmd == "top-n":
        df = top_n_cost_drivers(args.month, args.n)
        print(df.to_string(index=False))
    elif args.cmd == "unit-changes":
        df = unit_cost_changes(args.threshold)
        print(df.to_string(index=False))
    elif args.cmd == "export-csvs":
        export_csvs(args.out)
    else:
        parser.print_help()

if __name__ == "__main__":
    _cli()
