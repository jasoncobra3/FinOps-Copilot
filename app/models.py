import os
from sqlalchemy import (
    MetaData, Table, Column, String, Float, Text, create_engine
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/billing.db")


connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
metadata = MetaData()

billing = Table(
    "billing",
    metadata,
    Column("invoice_month", String, nullable=False),  # YYYY-MM
    Column("account_id", String),
    Column("subscription", String),
    Column("service", String),
    Column("resource_group", String),
    Column("resource_id", String),
    Column("region", String),
    Column("usage_qty", Float),
    Column("unit_cost", Float),
    Column("cost", Float),
)

resources = Table(
    "resources",
    metadata,
    Column("resource_id", String, primary_key=True),
    Column("owner", String),
    Column("env", String),
    Column("tags_json", Text),
)

def create_tables():
    metadata.create_all(engine)
    print("Tables created (if not existing). DB:", DATABASE_URL)

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    create_tables()
