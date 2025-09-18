"""
Tests for FastAPI endpoints related to recommendations
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
import pandas as pd
from app.models import engine

client = TestClient(app)

# Test data setup
@pytest.fixture(autouse=True)
def setup_test_data():
    """Setup test data before each test"""
    # Create test billing data
    billing_data = {
        "invoice_month": ["2025-08", "2025-08", "2025-08", "2025-08"],
        "resource_id": ["res1", "res2", "res3", "res4"],
        "usage_qty": [10, 1, 5, 0],
        "unit_cost": [10, 20, 15, 30],
        "cost": [1000, 2000, 750, 500],
    }
    resources_data = {
        "resource_id": ["res1", "res2", "res3", "res4"],
        "owner": ["team1", "unassigned", "team2", "unassigned"],
        "env": ["prod", "dev", "unassigned", "unassigned"],
        "tags_json": ["{}", "{}", "{}", "{}"]
    }
    
    # Create temporary test tables
    pd.DataFrame(billing_data).to_sql("billing", engine, if_exists="replace", index=False)
    pd.DataFrame(resources_data).to_sql("resources", engine, if_exists="replace", index=False)
    
    yield  # this allows the test to run with the test data
    
    # Cleanup (optional) - remove test data after tests
    # with engine.connect() as conn:
    #     conn.execute("DROP TABLE IF EXISTS billing")
    #     conn.execute("DROP TABLE IF EXISTS resources")

def test_get_recommendations_endpoint():
    """Test the /recommendations endpoint"""
    response = client.get("/recommendations")
    assert response.status_code == 200
    
    data = response.json()
    assert "total_estimated_monthly_savings" in data
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)
    
    # Verify we get all types of recommendations
    rec_types = {rec["type"] for rec in data["recommendations"]}
    assert "idle_resources" in rec_types
    assert "tagging_gaps" in rec_types
    
    # Verify recommendation structure
    for rec in data["recommendations"]:
        assert "type" in rec
        assert "resources" in rec
        assert "estimated_monthly_savings" in rec
        assert "recommended_actions" in rec

def test_get_recommendations_with_custom_thresholds():
    """Test the /recommendations endpoint with custom threshold parameters"""
    response = client.get("/recommendations", params={
        "usage_threshold": 0.05,  # 5% usage threshold
        "cost_threshold": 50,     # $50 minimum cost
        "spike_threshold": 0.5    # 50% cost increase threshold
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # With lower thresholds, we should get more recommendations
    assert len(data["recommendations"]) > 0
    
    # Verify the recommendations reflect our thresholds
    for rec in data["recommendations"]:
        if rec["type"] == "idle_resources":
            # Check that resources have usage below 5%
            for resource in rec["resources"]:
                assert resource.get("utilization", 0) <= 5  # 5%
                assert resource.get("current_monthly_cost", 0) >= 50

def test_get_recommendations_error_handling():
    """Test error handling in the recommendations endpoint"""
    # Test invalid threshold values
    response = client.get("/recommendations", params={
        "usage_threshold": -1,  # Invalid negative value
        "cost_threshold": 0,    # Invalid zero value
        "spike_threshold": 2    # Invalid threshold > 1
    })
    
    # Should still return 200 with default values used
    assert response.status_code == 200
    
    # Test with extremely high thresholds (should return empty recommendations)
    response = client.get("/recommendations", params={
        "usage_threshold": 0.99,
        "cost_threshold": 1000000,
        "spike_threshold": 0.99
    })
    
    assert response.status_code == 200
    data = response.json()
    # Should have structure but might be empty
    assert "recommendations" in data
    assert "total_estimated_monthly_savings" in data

def test_recommendations_data_validation():
    """Test that recommendations contain valid data"""
    response = client.get("/recommendations")
    assert response.status_code == 200
    data = response.json()
    
    # Validate savings values
    assert data["total_estimated_monthly_savings"] >= 0
    
    for rec in data["recommendations"]:
        assert rec["estimated_monthly_savings"] >= 0
        
        # Validate resource data
        for resource in rec["resources"]:
            if "current_monthly_cost" in resource:
                assert resource["current_monthly_cost"] >= 0
            if "potential_savings" in resource:
                assert resource["potential_savings"] >= 0
                # Savings shouldn't exceed current cost
                if "current_monthly_cost" in resource:
                    assert resource["potential_savings"] <= resource["current_monthly_cost"]

def test_recommendations_cache_behavior():
    """Test that recommendations are consistent with repeated calls"""
    # Make two consecutive calls
    response1 = client.get("/recommendations")
    response2 = client.get("/recommendations")
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    data1 = response1.json()
    data2 = response2.json()
    
    # Results should be identical for same data
    assert data1 == data2
    
    # Verify savings are consistent
    assert data1["total_estimated_monthly_savings"] == data2["total_estimated_monthly_savings"]