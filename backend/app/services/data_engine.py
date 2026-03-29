import duckdb

SESSION_STORES: dict[str, duckdb.DuckDBPyConnection] = {}

def get_or_create_session(workspace_id: str) -> duckdb.DuckDBPyConnection:
    if workspace_id not in SESSION_STORES:
        SESSION_STORES[workspace_id] = duckdb.connect(database=':memory:')
    return SESSION_STORES[workspace_id]

def get_schema(workspace_id: str) -> dict[str, list[dict]]:
    conn = get_or_create_session(workspace_id)
    tables_result = conn.execute("SHOW TABLES").fetchall()
    tables = [row[0] for row in tables_result]
    
    schema = {}
    for table_name in tables:
        cols_result = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        schema[table_name] = [
            {"column": col[1], "type": col[2]} for col in cols_result
        ]
    return schema

def execute_query(workspace_id: str, sql: str) -> list[dict]:
    conn = get_or_create_session(workspace_id)
    result = conn.execute(sql)
    if result.description is None:
        return []
        
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()
    
    return [dict(zip(columns, row)) for row in rows]
