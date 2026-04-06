import pandas as pd
from sqlalchemy import create_engine, MetaData
import duckdb
import math

from app.services.data_engine import get_schema, get_or_create_session
from app.services.agent.nodes import data_prep_node
from app.services.agent.state import AsklyticState


# ---- Helper: Clean dataframe (IMPORTANT) ----
def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Drop unwanted Postgres auto-generated columns if they exist
    cols_to_drop = [c for c in df.columns if c in ("_cast", "_cast_dna")]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    # Replace NaN with None (fix JSON issue later)
    df = df.where(pd.notnull(df), None)

    # Convert datetime to string (JSON safe)
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)

    return df


# ---- Main ingestion function ----
def ingest_from_sql_source(workspace_id: str, connection_url: str) -> tuple[list[str], dict]:
    """
    Connects to source DB → loads into DuckDB → prepares data → returns schema
    """

    # Create source connection
    source_engine = create_engine(connection_url)

    # Create DuckDB session
    duck_conn = get_or_create_session(workspace_id)

    ingested_tables = []

    with source_engine.connect() as conn:
        meta = MetaData()
        meta.reflect(bind=source_engine)

        for table_name, table in meta.tables.items():
            if table_name in ("_cast", "_cast_dna"):
                continue
            try:
                # Load table into pandas
                df = pd.read_sql_table(table_name, conn)

                # Clean data (VERY IMPORTANT)
                df = clean_dataframe(df)

                # Register in DuckDB
                duck_conn.register(f"temp_df_{table_name}", df)

                # Create table in DuckDB
                duck_conn.execute(
                    f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM temp_df_{table_name}"
                )

                duck_conn.unregister(f"temp_df_{table_name}")

                ingested_tables.append(table_name)

            except Exception as e:
                print(f"[INGEST ERROR] Table {table_name}: {e}")

    # ---- Run Data Prep ----
    for table_name in list(ingested_tables):
        try:
            mock_state: AsklyticState = {
                "workspace_id": workspace_id,
                "current_table": table_name,
                "transformation_history": [],
                "row_count_history": [],
                "prep_status": "pending",
                "dataset_schema": get_schema(workspace_id)
            }

            data_prep_node(mock_state)

        except Exception as e:
            print(f"[DATA PREP ERROR] Table {table_name}: {e}")

    # ---- Final schema ----
    schema_map = get_schema(workspace_id)

    return ingested_tables, schema_map