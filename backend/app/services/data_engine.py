import duckdb

SESSION_STORES: dict[str, duckdb.DuckDBPyConnection] = {}

def get_or_create_session(workspace_id: str) -> duckdb.DuckDBPyConnection:
    """
    Retrieves an existing or creates a new DuckDB connection for a specific workspace.

    Args:
        workspace_id (str): The unique identifier for the workspace.

    Returns:
        duckdb.DuckDBPyConnection: The managed DuckDB connection object.
    """
    if workspace_id not in SESSION_STORES:
        SESSION_STORES[workspace_id] = duckdb.connect(database=':memory:')
    return SESSION_STORES[workspace_id]

def get_schema(workspace_id: str) -> dict[str, list[dict]]:
    """
    Retrieves the table schema currently loaded into the DuckDB instance for a workspace.

    Args:
        workspace_id (str): The unique identifier for the workspace.

    Returns:
        dict[str, list[dict]]: A dictionary mapping each table name to a list of its columns, 
            where each column is represented as a dict with 'column' and 'type' keys.
    """
    conn = get_or_create_session(workspace_id)
    tables_result = conn.execute("SHOW TABLES").fetchall()
    tables = [row[0] for row in tables_result]
    
    schema = {}
    for table_name in tables:
        if table_name.endswith("_cast") or table_name.endswith("_cast_dna"):
            continue
        cols_result = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        schema[table_name] = [
            {"column": col[1], "type": col[2]} for col in cols_result
        ]
    return schema

def execute_query(workspace_id: str, sql: str) -> list[dict]:
    """
    Executes a SQL query against the workspace's DuckDB instance.

    Args:
        workspace_id (str): The unique identifier for the workspace.
        sql (str): The SQL statement to securely execute.

    Returns:
        list[dict]: A list of rows represented as dictionaries mapping column names to row values.
    """
    conn = get_or_create_session(workspace_id)
    result = conn.execute(sql)
    if result.description is None:
        return []
        
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()
    
    import math
    def clean_val(v):
        if isinstance(v, float) and math.isnan(v):
            return None
        return v
        
    return [dict(zip(columns, (clean_val(v) for v in row))) for row in rows]

def execute_and_format_chart(workspace_id: str, sql: str, meta: dict) -> dict:
    """
    Executes a query and formats the result into a Plotly-compatible JSON payload.

    Args:
        workspace_id (str): The unique identifier for the workspace.
        sql (str): The SQL statement used to retrieve data.
        meta (dict): Dictionary specifying chart parameters like 'chart_type', 'title', 
            'x_column', and 'y_column'.

    Returns:
        dict: A dictionary structure compatible with Plotly.js to render a chart.

    Raises:
        ValueError: If the SQL string is empty, or if the executed SQL returns no data.
    """
    if not sql:
        raise ValueError("Empty SQL provided.")
    rows = execute_query(workspace_id, sql)
    if not rows:
        raise ValueError(f"No data returned for SQL: {sql}")
        
    x_col = meta.get("x_column")
    y_col = meta.get("y_column")
    
    if not rows[0].get(x_col):
        x_col = list(rows[0].keys())[0] if rows[0] else None
    if not rows[0].get(y_col):
        y_col = list(rows[0].keys())[1] if len(rows[0].keys()) > 1 else x_col
        
    x_data = [row.get(x_col) for row in rows]
    y_data = [row.get(y_col) for row in rows]
    
    payload = {
        "data": [{
            "type": meta.get("chart_type", "bar"),
            "x": x_data,
            "y": y_data,
        }],
        "layout": {
            "title": meta.get("title", ""),
            "xaxis": { "title": x_col },
            "yaxis": { "title": y_col },
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": { "color": "#ffffff" },
            "margin": {"b": 40, "l": 40, "r": 20, "t": 50}
        },
        "_sql": sql,
        "_meta": meta
    }
    
    if payload["data"][0]["type"] == "pie":
        payload["data"][0]["labels"] = payload["data"][0].pop("x")
        payload["data"][0]["values"] = payload["data"][0].pop("y")
        
    return payload
