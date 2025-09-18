import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import random
import json

Path("data").mkdir(exist_ok=True)

def gen_months(n_months=6, end_month=None):
    if end_month is None:
        end = datetime.now()
    else:
        end = pd.to_datetime(end_month + "-01")
    periods = pd.date_range(end=end, periods=n_months, freq="MS")
    return [d.strftime("%Y-%m") for d in periods]

# More varied services with different cost patterns
services = {
    "Compute": {"base_cost": 100, "volatility": 0.3},
    "Storage": {"base_cost": 50, "volatility": 0.1},
    "Database": {"base_cost": 200, "volatility": 0.15},
    "Networking": {"base_cost": 80, "volatility": 0.2},
    "Analytics": {"base_cost": 150, "volatility": 0.25},
    "AI/ML": {"base_cost": 300, "volatility": 0.4},
    "Containers": {"base_cost": 120, "volatility": 0.35}
}

resource_groups = ["rg-prod", "rg-dev", "rg-staging", "rg-test"]
accounts = ["prod-acct", "dev-acct", "shared-acct"]
regions = ["us-east-1", "eu-west-1", "ap-south-1", "us-west-2"]

def generate_seasonal_factor(month):
    # Add seasonal patterns (e.g., higher usage in certain months)
    month_num = int(month.split('-')[1])
    base = 1.0
    # Higher usage in summer months
    if month_num in [6, 7, 8]:
        base *= 1.2
    # Peak usage in end of year
    elif month_num in [11, 12]:
        base *= 1.3
    # Lower usage in beginning of year
    elif month_num in [1, 2]:
        base *= 0.8
    return base

def generate_growth_trend(month_index, n_months):
    # Simulate general growth trend
    return 1.0 + (month_index / n_months) * 0.15

def generate_rows(n_resources=60, n_months=6, end_month="2025-09"):
    months = gen_months(n_months, end_month)
    rows = []
    
    # Create resources with different characteristics
    resources = []
    for i in range(n_resources):
        service = random.choices(list(services.keys()), 
                               weights=[0.25, 0.2, 0.15, 0.15, 0.1, 0.1, 0.05])[0]
        rg = random.choice(resource_groups)
        account = random.choice(accounts)
        region = random.choice(regions)
        
        # Add resource lifecycle events
        start_month = random.randint(0, n_months//2)
        lifetime = random.randint(n_months//2, n_months)
        
        resources.append({
            "id": f"res-{i+1}",
            "service": service,
            "rg": rg,
            "account": account,
            "region": region,
            "start_month": start_month,
            "lifetime": lifetime
        })
    
    # Generate monthly data with patterns
    for month_idx, month in enumerate(months):
        for res in resources:
            # Skip if resource hasn't been created yet or has been deleted
            if month_idx < res["start_month"] or month_idx >= res["start_month"] + res["lifetime"]:
                continue
                
            service_info = services[res["service"]]
            
            # Calculate usage with multiple factors
            base_usage = service_info["base_cost"]
            seasonal = generate_seasonal_factor(month)
            growth = generate_growth_trend(month_idx, n_months)
            randomness = np.random.normal(1, service_info["volatility"])
            
            usage = max(0, base_usage * seasonal * growth * randomness)
            
            # Add some cost variation
            unit_cost = round(random.uniform(0.01, 2.0) * (1 + month_idx * 0.02), 4)  # Slight cost inflation
            cost = round(usage * unit_cost, 4)
            
            rows.append({
                "invoice_month": month,
                "account_id": res["account"],
                "subscription": "enterprise" if res["account"] == "prod-acct" else "basic",
                "service": res["service"],
                "resource_group": res["rg"],
                "resource_id": res["id"],
                "region": res["region"],
                "usage_qty": usage,
                "unit_cost": unit_cost,
                "cost": cost
            })
    
    df = pd.DataFrame(rows)
    return df, resources

def generate_resource_assignments():
    # Teams with different assignment patterns
    teams = ["team-A", "team-B", "team-C", "team-D"]
    envs = ["prod", "dev", "staging", "test"]
    
    assignments = {}
    
    for i in range(1, 61):
        resource_id = f"res-{i}"
        
        # Simulate some resources being unassigned (higher chance in dev/test)
        if random.random() < 0.2:  # 20% chance of being unassigned
            assignments[resource_id] = {
                "owner": None,
                "env": None,
                "tags": {}
            }
            continue
            
        # Assign owner and environment
        owner = random.choice(teams)
        env = random.choice(envs)
        
        # Add some tags
        tags = {
            "project": random.choice(["project-1", "project-2", "project-3"]),
            "department": random.choice(["engineering", "data", "research"]),
            "created_by": owner
        }
        
        assignments[resource_id] = {
            "owner": owner,
            "env": env,
            "tags": tags
        }
    
    return assignments

if __name__ == "__main__":
    # Generate billing data
    df, resources = generate_rows(n_resources=60, n_months=6, end_month="2025-09")
    df.to_csv("data/sample_billing.csv", index=False)
    print("Generated sample_billing.csv with", len(df), "rows")
    
    # Generate resource assignments
    assignments = generate_resource_assignments()
    
    # Save assignments to a JSON file for reference
    with open("data/resource_assignments.json", "w") as f:
        json.dump(assignments, f, indent=2)
    print("Generated resource_assignments.json")