
"""
scripts/seed_resources.py
Generate synthetic metadata for all distinct resource_id values found in the billing table
and insert them into the resources table (skips already present resource_ids).
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import argparse
import random
import json
import pandas as pd
from app import models

def main(force: bool = False):
    engine = models.engine
    resources_table = models.resources

    # Read distinct resource_ids from billing
    try:
        df = pd.read_sql("SELECT DISTINCT resource_id FROM billing", engine)
    except Exception as e:
        print("ERROR: Could not read billing table. Make sure you ingested billing data first.")
        print("Exception:", e)
        return

    resource_ids = df['resource_id'].dropna().astype(str).tolist()
    if not resource_ids:
        print("No resource_id found in billing table. Nothing to seed.")
        return

    # Read existing resources to avoid duplicates
    try:
        existing_df = pd.read_sql("SELECT resource_id FROM resources", engine)
        existing_ids = set(existing_df['resource_id'].astype(str).tolist()) if not existing_df.empty else set()
    except Exception:
        existing_ids = set()

    # Choose owners / envs / tags pools
    owners = ["team-A", "team-B", "team-C", "team-D"]
    envs = ["dev", "staging", "prod" ]
    projects = ["proj-alpha", "proj-beta", "proj-gamma", "infra", "platform"]

    rows = []
    for rid in resource_ids:
        if (rid in existing_ids) and (not force):
            continue
        owner = random.choice(owners)
        # bias env towards dev (more dev resources usually)
        env = random.choices(envs, weights=[0.5, 0.2, 0.3])[0]
        tags = {
            "project": random.choice(projects),
            "critical": random.choice(["yes", "no"])
        }
        rows.append({
            "resource_id": rid,
            "owner": owner,
            "env": env,
            "tags_json": json.dumps(tags)
        })

    if not rows:
        print("No new resources to insert. Use --force to re-seed existing ones.")
        return

    # Insert rows in a single transaction
    with engine.begin() as conn:
        conn.execute(resources_table.insert(), rows)

    print(f"Inserted {len(rows)} resources into 'resources' table (force={force}).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic resources metadata")
    parser.add_argument("--force", action="store_true", help="Insert even if resource_id already exists (overwrites by inserting duplicates if schema allows)")
    args = parser.parse_args()
    main(force=args.force)
