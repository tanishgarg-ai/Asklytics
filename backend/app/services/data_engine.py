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
    
    import math
    def clean_val(v):
        if isinstance(v, float) and math.isnan(v):
            return None
        return v
        
    return [dict(zip(columns, (clean_val(v) for v in row))) for row in rows]

def execute_and_format_chart(workspace_id: str, sql: str, meta: dict) -> dict:
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
