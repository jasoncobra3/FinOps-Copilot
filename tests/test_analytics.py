import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import pandas as pd
from app.models import engine
from app.analytics import monthly_cost_by_owner

def test_monthly_cost_consistency():
    # choose a month that exists in your data
    test_month = "2025-08"

    # total directly from billing table
    billing = pd.read_sql_query(
        f"SELECT cost FROM billing WHERE invoice_month = '{test_month}'", engine
    )
    total_billing_cost = billing["cost"].sum()

    # total from analytics function
    owner_df = monthly_cost_by_owner(test_month)
    total_owner_cost = owner_df["cost"].sum()

    # they should be almost equal (allowing tiny float error)
    assert abs(total_billing_cost - total_owner_cost) < 1e-6, \
        f"Mismatch: billing={total_billing_cost}, owners={total_owner_cost}"
