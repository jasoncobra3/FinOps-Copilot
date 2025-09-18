"""
Main Streamlit application for FinOps Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
from typing import Dict, List, Any
import altair as alt

# Constants
API_URL = "http://localhost:8000"  # FastAPI backend URL

# Page Config
st.set_page_config(
    page_title="FinOps Assistant",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .stMetric {
        padding: 5px 0;
    }
    .stMetric:hover {
        opacity: 0.8;
    }
    .stAlert {
        border-radius: 4px;
    }
    div[data-testid="stExpander"] div[role="button"] p {
        font-size: 1.1em;
        font-weight: 600;
    }
    div.stChatMessage {
        background: transparent !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Helper Functions
def fetch_kpi_data(month: str) -> Dict:
    """Fetch KPI data from FastAPI backend"""
    try:
        response = requests.get(f"{API_URL}/kpi", params={"month": month})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching KPI data: {str(e)}")
        return None

def fetch_available_months() -> List[str]:
    """Fetch available billing months from backend"""
    try:
        response = requests.get(f"{API_URL}/kpi/months")
        response.raise_for_status()
        data = response.json()
        if "message" in data:
            st.warning(data["message"])
        return data.get("months", [])
    except requests.RequestException as e:
        st.error(f"Failed to connect to API: {str(e)}")
        st.info("Make sure the FastAPI server is running with: uvicorn app.main:app --reload")
        return []

def fetch_recommendations() -> Dict[str, Any]:
    """Fetch cost optimization recommendations"""
    try:
        response = requests.get(f"{API_URL}/recommendations")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching recommendations: {str(e)}")
        return None

def ask_question(question: str) -> Dict[str, Any]:
    """Send question to RAG QA system"""
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(f"{API_URL}/ask", json={"question": question}, headers=headers)
        if response.status_code == 500:
            st.error(f"Server error: {response.text}")
            if "GROQ_API_KEY not set" in response.text:
                st.info("To enable chat:")
                st.code("""
1. Get an API key from Groq (https://console.groq.com)
2. Create a .env file in the project root
3. Add: GROQ_API_KEY=your_api_key_here
4. Restart the FastAPI server
                """)
            return None
            
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error getting answer: {str(e)}")
        if "500 Server Error" in str(e):
            st.info("If this is your first time running the system, make sure to:")
            st.code("""
1. Set up the GROQ_API_KEY environment variable
2. Build the FAISS index: python scripts/build_faiss_index.py
3. Restart the FastAPI server
            """)
        return None

def plot_cost_by_owner(df: pd.DataFrame) -> go.Figure:
    """Create a bar chart of costs by owner"""
    fig = px.bar(
        df,
        x="owner",
        y="cost",
        title="Monthly Cost by Owner",
        labels={"owner": "Owner", "cost": "Cost ($)"}
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False,
        height=400
    )
    return fig

def plot_cost_by_env(df: pd.DataFrame) -> go.Figure:
    """Create a bar chart of costs by environment"""
    fig = px.bar(
        df,
        x="env",
        y="cost",
        title="Monthly Cost by Environment",
        labels={"env": "Environment", "cost": "Cost ($)"}
    )
    fig.update_layout(
        xaxis_tickangle=0,
        showlegend=False,
        height=400
    )
    return fig

# Sidebar for navigation
st.sidebar.title("FinOps Assistant")
page = st.sidebar.radio("Navigation", ["KPI Dashboard", "Cost Optimization", "Chat"])

if page == "KPI Dashboard":
    st.title("KPI Dashboard")
    
    # Month selector
    with st.spinner("Loading available months..."):
        months = fetch_available_months()
        
    if not months:
        st.error("No billing data available in the database. Please ensure data is ingested.")
        st.info("Try running: python scripts/generate_sample_data.py && python scripts/ingest.py -i data/sample_billing.csv")
    else:
        selected_month = st.selectbox(
            "Select Month",
            months,
            index=len(months)-1  # Default to latest month
        )
        
        # Fetch and display KPI data
        with st.spinner("Loading KPI data..."):
            kpi_data = fetch_kpi_data(selected_month)
            
        if kpi_data:
            # Create two columns for charts
            col1, col2 = st.columns(2)
            
            # Cost by owner
            with col1:
                df_owner = pd.DataFrame(kpi_data["cost_by_owner"])
                fig_owner = plot_cost_by_owner(df_owner)
                st.plotly_chart(fig_owner, use_container_width=True)
            
            # Cost by environment
            with col2:
                df_env = pd.DataFrame(kpi_data["cost_by_env"])
                fig_env = plot_cost_by_env(df_env)
                st.plotly_chart(fig_env, use_container_width=True)
            
            # Owner coverage metrics
            coverage = kpi_data.get("owner_coverage", {})
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            
            with metrics_col1:
                st.metric(
                    "Total Cost",
                    f"${coverage.get('total_cost', 0):,.2f}"
                )
            
            with metrics_col2:
                st.metric(
                    "Assigned Cost",
                    f"${coverage.get('assigned_cost', 0):,.2f}"
                )
            
            with metrics_col3:
                st.metric(
                    "Owner Coverage",
                    f"{coverage.get('coverage_pct', 0)*100:.1f}%"
                )

elif page == "Cost Optimization":
    st.title("Cost Optimization Recommendations")
    
    with st.spinner("Loading recommendations..."):
        recs = fetch_recommendations()
    
    if recs:
        # Show total potential savings
        st.metric(
            "Total Potential Monthly Savings",
            f"${recs['total_estimated_monthly_savings']:,.2f}"
        )
        
        # Display recommendations by type
        for rec in recs["recommendations"]:
            with st.expander(f"{rec['type'].replace('_', ' ').title()} ({len(rec['resources'])} items)"):
                # Show estimated savings for this category
                st.metric(
                    "Category Savings Potential",
                    f"${rec['estimated_monthly_savings']:,.2f}"
                )
                
                # Display recommended actions
                st.subheader("Recommended Actions")
                for action in rec["recommended_actions"]:
                    st.write(f"• {action}")
                
                # Display affected resources
                st.subheader("Affected Resources")
                df = pd.DataFrame(rec["resources"])
                st.dataframe(df)

elif page == "Chat":
    st.title("FinOps Assistant Chat")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your cloud costs..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant", avatar="💰"):
            with st.spinner("🤔 Analyzing your question..."):
                response = ask_question(prompt)
                
            if response:
                answer = response.get("answer", "I'm unable to answer that right now.")
                st.markdown(answer)
                
                # Show sources if available
                sources = response.get("sources", [])
                if sources:
                    with st.expander("🔍 View Sources", expanded=False):
                        for idx, src in enumerate(sources, 1):
                            st.markdown(f"**Source {idx}:**\n{src.get('text', '')}")
                            st.markdown("---")
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # Add helpful tips if available
                if "tips" in response and response["tips"]:
                    with st.expander("💡 Related FinOps Tips", expanded=False):
                        for tip in response["tips"]:
                            st.markdown(f"• {tip}")