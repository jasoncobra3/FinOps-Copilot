import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import random

Path("data").mkdir(exist_ok=True)

def gen_months(n_months=6, end_month=None):
    if end_month is None:
        end = datetime.now()
    else:
        end = pd.to_datetime(end_month + "-01")
    periods = pd.date_range(end=end, periods=n_months, freq="MS")
    return [d.strftime("%Y-%m") for d in periods]

services = ["Compute","Storage","Database","Networking"]
resource_groups = ["rg-a","rg-b","rg-c"]
accounts = ["acct-1","acct-2"]
regions = ["us-east-1","eu-west-1"]

def generate_rows(n_resources=60, n_months=6):
    months = gen_months(n_months)
    rows = []
    # create resources
    resources = [f"res-{i+1}" for i in range(n_resources)]
    for r in resources:
        service = random.choice(services)
        rg = random.choice(resource_groups)
        account = random.choice(accounts)
        region = random.choice(regions)
        # per month usage
        for m in months:
            usage = max(1, float(np.random.poisson(100) * (0.5 + random.random())))
            unit_cost = round(random.uniform(0.01, 2.0), 4)
            cost = round(usage * unit_cost, 4)
            rows.append({
                "invoice_month": m,
                "account_id": account,
                "subscription": "basic",
                "service": service,
                "resource_group": rg,
                "resource_id": r,
                "region": region,
                "usage_qty": usage,
                "unit_cost": unit_cost,
                "cost": cost
            })
    df = pd.DataFrame(rows)
    return df

if __name__ == "__main__":
    df = generate_rows(n_resources=100, n_months=6)
    df.to_csv("data/sample_billing.csv", index=False)
    print("Generated sample_billing.csv with", len(df), "rows")
