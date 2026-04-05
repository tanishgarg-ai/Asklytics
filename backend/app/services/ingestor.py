import pandas as pd
from sqlalchemy import create_engine
from app.services.data_engine import get_or_create_session, get_schema

# TODO: validate supported dialects
def ingest_from_sql_source(workspace_id: str, connection_url: str) -> tuple[list[str], dict[str, list[dict]]]:
    """
    Uses SQLAlchemy to connect and reflect all tables from the source DB.
    Loads each table into the workspace's DuckDB instance via Pandas.
    Returns the list of ingested table names and the full schema.

    Args:
        workspace_id (str): The unique identifier for the workspace.
        connection_url (str): The database connection URL for SQLAlchemy.

    Returns:
        tuple[list[str], dict[str, list[dict]]]: A tuple containing a list of ingested table names 
            and a mapping of table names to their respective schema definitions.
    """
    source_engine = create_engine(connection_url)
    duck_conn = get_or_create_session(workspace_id)
    ingested_tables = []
    
    with source_engine.connect() as conn:
        from sqlalchemy import MetaData
        meta = MetaData()
        meta.reflect(bind=source_engine)
        
        for table_name, table in meta.tables.items():
            df = pd.read_sql_table(table_name, conn)
            duck_conn.register(f"temp_df_{table_name}", df)
            duck_conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM temp_df_{table_name}")
            duck_conn.unregister(f"temp_df_{table_name}")
            ingested_tables.append(table_name)
            
    schema_map = get_schema(workspace_id)
    return ingested_tables, schema_map
