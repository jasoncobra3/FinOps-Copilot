from fastapi import FastAPI, Query, HTTPException, Request
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import pandas as pd
from app.analytics import (
    unit_cost_changes, six_month_trend, top_n_cost_drivers,
    monthly_cost_by_owner, monthly_cost_by_env, owner_coverage,
    load_month_results, cache_month_results
)
from app.models import engine, resources
from pydantic import BaseModel
from app.rag_qa import answer as rag_answer
from app.recommendations import get_all_recommendations
from app.validators import validate_request

app = FastAPI(
    title="FinOps API",
    description="Cost management and optimization API with RAG-powered insights",
    version="1.0.0"
)

# No monitoring setup or middleware needed

@app.get("/kpi")
def get_kpis(
    month: str = Query(..., description="Month in YYYY-MM format"),
    refresh: bool = Query(False, description="Force refresh and rebuild cache")
):
    """
    Returns cost KPIs for a given month.
    Uses cache unless refresh=true is passed.
    """
    if not refresh:
        cached = load_month_results(month)
    else:
        cached = None

    if cached:
        owner_df, env_df, coverage = cached
    else:
        owner_df = monthly_cost_by_owner(month)
        env_df = monthly_cost_by_env(month)
        coverage = owner_coverage(month)
        cache_month_results(month)

    return {
        "month": month,
        "cost_by_owner": owner_df.to_dict(orient="records"),
        "cost_by_env": env_df.to_dict(orient="records"),
        "owner_coverage": coverage
    }
@app.get("/kpi/months")
def get_available_months():
    """
    Returns all distinct months present in the billing table
    (for use in frontend dropdowns)
    """
    try:
        df = pd.read_sql_query("SELECT DISTINCT invoice_month FROM billing", engine)
        if df.empty:
            return {"months": [], "message": "No billing data found in database"}
        months = sorted(df["invoice_month"].astype(str).tolist())
        return {"months": months}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching months: {str(e)}"
        )

@app.get("/kpi/top")
def get_top_cost_drivers(
    month: str = Query(..., description="Month in YYYY-MM format"),
    n: int = Query(10, description="Number of top cost drivers to return")
):
    """
    Returns Top N cost-driving resources for the given month.
    """
    df = top_n_cost_drivers(month, n)
    return {
        "month": month,
        "top_n": n,
        "results": df.to_dict(orient="records")
    }
    
@app.get("/kpi/unit-changes")
def get_unit_cost_changes(
    threshold: float = Query(0.2, description="Percentage threshold (e.g. 0.2 = 20%)")
):
    """
    Returns all resources whose unit cost changed more than the threshold
    between consecutive months.
    """
    df = unit_cost_changes(threshold)
    return {
        "threshold": threshold,
        "results": df.to_dict(orient="records")
    }
    
@app.get("/kpi/trend")
def get_six_month_trend(
    group_by: str = Query("owner", description="Group by 'owner' or 'env'")
):
    """
    Returns 6-month cost trend grouped by owner or env.
    """
    df = six_month_trend(group_by)
    # pivot table: months as index, group values as columns
    return {
        "group_by": group_by,
        "trend": df.reset_index().to_dict(orient="records")
    }
    
@app.get("/kpi/quality-checks")
def run_quality_checks():
    """
    Performs basic data quality checks.
    """
    import pandas as pd
    from app.models import engine

    billing = pd.read_sql_query("SELECT * FROM billing", engine)
    resources = pd.read_sql_query("SELECT * FROM resources", engine)

    issues = []

    # 1) Null checks
    nulls = billing[billing[["invoice_month","resource_id","cost"]].isnull().any(axis=1)]
    if not nulls.empty:
        issues.append({"type": "null_values", "count": len(nulls)})

    # 2) Negative cost
    neg = billing[billing["cost"] < 0]
    if not neg.empty:
        issues.append({"type": "negative_costs", "count": len(neg)})

    # 3) Duplicate resource_ids in resources
    dup = resources["resource_id"].duplicated().sum()
    if dup > 0:
        issues.append({"type": "duplicate_resource_ids", "count": int(dup)})

    return {"issues": issues or "No issues found"}

class AskRequest(BaseModel):
    question: str
    top_k: int = 5
    model: str | None = None   # optional Groq model override

@app.get("/recommendations")
def get_recommendations(
    usage_threshold: float = Query(0.1, description="Usage threshold for idle detection (0-1)"),
    cost_threshold: float = Query(100, description="Minimum monthly cost for recommendations ($)"),
    spike_threshold: float = Query(0.3, description="Unit cost increase threshold (e.g. 0.3 = 30%)")
):
    """
    Get cost optimization recommendations including:
    - Idle/underutilized resources
    - Resources with sudden unit cost increases
    - Resources missing tags causing unknown costs
    
    Returns estimated savings and specific actions for each recommendation.
    """
    try:
        return get_all_recommendations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask")
async def ask(req: AskRequest):
    try:
        # Validate and sanitize input
        try:
            validated_data = validate_request(req.dict())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Check if GROQ_API_KEY is set
        if not os.getenv("GROQ_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail="GROQ_API_KEY not set. Please set the environment variable with your Groq API key."
            )
            
        # Check if FAISS index exists
        if not os.path.exists("data/faiss/index.faiss") or not os.path.exists("data/faiss/meta.json"):
            raise HTTPException(
                status_code=500,
                detail="FAISS index not found. Please run 'python scripts/build_faiss_index.py' first."
            )
            
        res = await rag_answer(
            validated_data["question"],
            top_k=validated_data["top_k"],
            groq_model=validated_data.get("model")
        )
        
        if res.get("error"):
            raise HTTPException(status_code=500, detail=res["error"])
            
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
