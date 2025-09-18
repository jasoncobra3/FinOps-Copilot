import pytest
import pandas as pd
from app.recommendations import (
    find_idle_resources,
    find_cost_spikes,
    find_tagging_gaps,
    get_all_recommendations
)
from app.models import engine
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import sqlite3

# Test data setup
@pytest.fixture
def sample_billing_data():
    # Create test billing data
    data = {
        "invoice_month": ["2025-08", "2025-08", "2025-08", "2025-08"],
        "resource_id": ["res1", "res2", "res3", "res4"],
        "usage_qty": [10, 1, 5, 0],
        "unit_cost": [10, 20, 15, 30],
        "cost": [1000, 2000, 750, 500],
    }
    return pd.DataFrame(data)

@pytest.fixture
def sample_resources_data():
    # Create test resources data
    data = {
        "resource_id": ["res1", "res2", "res3", "res4"],
        "owner": ["team1", "unassigned", "team2", "unassigned"],
        "env": ["prod", "dev", "unassigned", "unassigned"],
        "tags_json": ["{}", "{}", "{}", "{}"]
    }
    return pd.DataFrame(data)

def test_find_idle_resources(sample_billing_data, sample_resources_data):
    # Create temporary test tables
    sample_billing_data.to_sql("billing", engine, if_exists="replace", index=False)
    sample_resources_data.to_sql("resources", engine, if_exists="replace", index=False)
    
    # Test idle resource detection
    recs = find_idle_resources(usage_threshold=0.2, cost_threshold=400)
    assert len(recs) > 0
    
    # Verify recommendation structure
    rec = recs[0]
    assert rec.type == "idle_resources"
    assert len(rec.resources) > 0
    assert rec.estimated_savings > 0
    assert len(rec.actions) > 0
    
    # Verify specific resource was caught
    idle_res = [r["resource_id"] for r in rec.resources]
    assert "res4" in idle_res  # Should catch resource with 0 usage

def test_find_cost_spikes(sample_billing_data, sample_resources_data):
    # Add historical data for spike detection
    historical = sample_billing_data.copy()
    historical["invoice_month"] = "2025-07"
    historical["unit_cost"] = historical["unit_cost"] * 0.5  # 50% lower costs
    
    # Combine current and historical
    combined = pd.concat([historical, sample_billing_data])
    combined.to_sql("billing", engine, if_exists="replace", index=False)
    sample_resources_data.to_sql("resources", engine, if_exists="replace", index=False)
    
    # Test spike detection
    recs = find_cost_spikes(threshold_pct=0.3)
    assert len(recs) > 0
    
    rec = recs[0]
    assert rec.type == "cost_spikes"
    assert len(rec.resources) > 0
    assert rec.estimated_savings > 0
    
    # All resources should show up as having spikes
    assert len(rec.resources) >= 4  

def test_find_tagging_gaps(sample_billing_data, sample_resources_data):
    # Setup test data
    sample_billing_data.to_sql("billing", engine, if_exists="replace", index=False)
    sample_resources_data.to_sql("resources", engine, if_exists="replace", index=False)
    
    # Test tagging gap detection
    recs = find_tagging_gaps()
    assert len(recs) > 0
    
    rec = recs[0]
    assert rec.type == "tagging_gaps"
    assert len(rec.resources) > 0
    assert rec.estimated_savings > 0
    
    # Verify untagged resources were caught
    untagged_res = [r["resource_id"] for r in rec.resources]
    assert "res2" in untagged_res
    assert "res4" in untagged_res

def test_get_all_recommendations(sample_billing_data, sample_resources_data):
    # Setup test data
    sample_billing_data.to_sql("billing", engine, if_exists="replace", index=False)
    sample_resources_data.to_sql("resources", engine, if_exists="replace", index=False)
    
    # Test getting all recommendations
    result = get_all_recommendations()
    
    assert "total_estimated_monthly_savings" in result
    assert "recommendations" in result
    assert len(result["recommendations"]) > 0
    
    # Verify each recommendation type is present
    rec_types = [r["type"] for r in result["recommendations"]]
    assert "idle_resources" in rec_types
    assert "tagging_gaps" in rec_types