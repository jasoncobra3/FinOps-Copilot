# 🌩️ AI-driven Cloud Cost Copilot (FinOps Assistant)

---

## 📌 Overview
**The FinOps Assistant is an AI-driven cloud cost analytics platform designed to help organizations monitor, analyze, and optimize their cloud spending.**
It provides:
- End-to-end pipeline: ETL → KPIs → RAG → Recommendations → API → UI
- KPI dashboards to analyze cost trends
- Natural-language Q&A over your cost data and FinOps documentation
- Actionable recommendations to reduce costs
  
---

## 🧩 Features

- Cost Analysis — Monthly spend trends, top cost drivers, cost anomalies
- RAG Q&A — Ask natural questions like “Why did compute cost increase in May?”
- Recommendations — Detect idle resources, tagging gaps, sudden spikes
- UI + API — Interactive Streamlit dashboard + FastAPI backend
- Evaluation Suite — Measure retrieval quality (Recall@k) + answer quality

---

## 🧠 Architecture
 ![](docs/Assets/Screenshot_9.png) 

 ---

 ## 🗂️ Directory Structure
 
 ```
├── app/
│   ├── main.py             # FastAPI backend entrypoint
│   ├── models.py            # SQLAlchemy schema (billing, resources)
│   ├── analytics.py         # KPI & trend calculations
│   ├── rag.py               # RAG pipeline setup (retriever + LLM)
│   ├── etl.py               # ETL piepline to validate data
|   ├── reccomendations.py   # Suggestions Generation
|   ├── rag_qa.py            # LangChain QA chain logic
│   └── validators.py        # input validation, prompt-injection guard 
|                        
├── docs/                     # Project documentation
│   ├── finops.md             # Refernce Docs for LLM
│   ├── PRD.pdf               # Product requirement Document
│   ├── Technical Design doc.pdf
│   ├── Assets/              
|
├── UI/
│   └── app.py                # Streamlit frontend dashboard
├── scripts/
│   ├── ingest_billing.py
│   ├── seed _resources.py
│   ├── build_faiss_index.py
│   ├── update_assignments.py
|   ├── manage_data.py
│   └── ...
|
├── tests/                    # Testing Files for evaluation
│   ├── conftest.py
│   ├── evaluate_rag.py
│   ├── test_analytics.py
│   ├── test_reccomendations.py
|   ├── test_reccomendations_api.py
│   └── rag_eval_results.json
|
|
├── data/                     # SQLite DB (billing.db) & Data Files
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
└── README.md

```
---

## ⚙️ Tech Stack

| Layer         | Technology                                                    | Purpose                       |
| ------------- | ------------------------------------------------------------- | ----------------------------- |
| ETL & DB      |Python, SQLAlchemy, SQLite                                     | Data ingestion + schema       |
| Analytics     |     Pandas, SQL                                               | KPI & cost trend calculations |
| RAG Pipeline  | sentence-transformers, FAISS, LangChain, Groq LLM             | Natural-language Q\&A         |
| API Layer     |    FastAPI                                                    | Serve KPIs and Q\&A endpoints |
| Frontend      |             Streamlit                                         | Interactive dashboard UI      |
| Deployment    | Docker, Docker Compose                                        | Containerization              |
| Observability | LangSmith                                                     | Logging + traces              |
| Security      | Prompt-injection guards, keyword filters                      | Secure LLM input              |


---

## 🧪 Setup & Running Locally

